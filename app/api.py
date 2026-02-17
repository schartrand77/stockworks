"""FastAPI application implementing inventory control for a 3D printing service."""
from __future__ import annotations

import mimetypes
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, func, select
from starlette.middleware.sessions import SessionMiddleware

from .barcodes import render_barcode_png
from .bambu_view import (
    BambuViewAuthenticationError,
    BambuViewIntegrationError,
    BambuViewNotConfiguredError,
    get_bambu_view_client,
)
from .color_resolver import normalize_hex
from .db import get_session, init_db
from .filament_types import bambu_x1c_filament_types
from .normalization import normalize_barcode, normalize_sku
from .orderworks import (
    OrderWorksAuthenticationError,
    OrderWorksDatabaseUnavailableError,
    OrderWorksIntegrationError,
    OrderWorksNotConfiguredError,
    get_orderworks_client,
    list_orderworks_jobs_via_database,
)
from .models import (
    HardwareItem,
    HardwareItemCreate,
    HardwareItemRead,
    HardwareItemUpdate,
    HardwareMovement,
    HardwareMovementCreate,
    HardwareMovementRead,
    InventoryItem,
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    Material,
    MaterialCreate,
    MaterialRead,
    MaterialUpdate,
    PaginatedHardwareRead,
    PaginatedInventoryRead,
    PaginatedMaterialsRead,
    PaginatedModelsRead,
    MaterialCostHistory,
    MaterialCostHistoryCreate,
    MaterialCostHistoryRead,
    PricingBreakdown,
    PricingRequest,
    PricingResponse,
    PrintModel,
    PrintModelCreate,
    PrintModelRead,
    PrintModelSale,
    PrintModelSaleCreate,
    PrintModelSaleRead,
    PrintModelUpdate,
    StockMovement,
    StockMovementCreate,
    StockMovementRead,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
PUBLIC_DIR = BASE_DIR.parent / "public"
MANIFEST_FILE = STATIC_DIR / "site.webmanifest"
SERVICE_WORKER_FILE = STATIC_DIR / "sw.js"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

mimetypes.add_type("application/manifest+json", ".webmanifest")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")
SECRET_KEY = os.environ.get("SECRET_KEY", "please-change-me")
SESSION_COOKIE = "stockworks-session"

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be configured via SECRET_KEY environment variable.")

app = FastAPI(title="StockWorks", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie=SESSION_COOKIE,
    same_site="lax",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _static_file_response(path: Path, media_type: str) -> FileResponse:
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path.name} not found")
    return FileResponse(path, media_type=media_type)


@app.get("/sw.js", include_in_schema=False)
@app.get("/service-worker.js", include_in_schema=False)
def service_worker() -> FileResponse:
    """Serve the PWA service worker at the root scope."""
    return _static_file_response(SERVICE_WORKER_FILE, media_type="application/javascript")


@app.get("/manifest.webmanifest", include_in_schema=False)
def web_manifest() -> FileResponse:
    """Expose the web manifest at the root for install prompts."""
    return _static_file_response(MANIFEST_FILE, media_type="application/manifest+json")


@app.get("/public/{asset_path:path}", include_in_schema=False)
def public_assets(asset_path: str) -> FileResponse:
    """Serve files from the repository-level public directory, even when not mounted."""
    target = PUBLIC_DIR / asset_path
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public asset not found")
    media_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(target, media_type=media_type or "application/octet-stream")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _is_authenticated(request: Request) -> bool:
    return bool(request.session.get("authenticated"))


def require_auth(request: Request) -> bool:
    if not _is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return True


def _credentials_valid(username: str, password: str) -> bool:
    return secrets.compare_digest(username.strip(), ADMIN_USERNAME) and secrets.compare_digest(password, ADMIN_PASSWORD)


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    """Serve the HTML shell for the single-page UI."""
    if not _is_authenticated(request):
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if _is_authenticated(request):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "username": ""})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if _credentials_valid(username, password):
        request.session["authenticated"] = True
        request.session["username"] = ADMIN_USERNAME
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    context = {"request": request, "error": "Invalid username or password.", "username": username}
    return templates.TemplateResponse("login.html", context, status_code=status.HTTP_401_UNAUTHORIZED)


@app.get("/filament-types/bambu-x1c")
def list_bambu_x1c_filament_types(_: bool = Depends(require_auth)) -> dict[str, list[str]]:
    return {"filament_types": bambu_x1c_filament_types()}


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


# Material endpoints
@app.post("/materials", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: MaterialCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    data = payload.dict()
    data["color_hex"] = normalize_hex(data.get("color_hex"))
    data["barcode"] = normalize_barcode(data.get("barcode"))
    data["refill_barcode"] = normalize_barcode(data.get("refill_barcode"))
    data["name"] = _ensure_unique_material_name(session, data["name"])
    material = Material(**data)
    session.add(material)
    session.commit()
    session.refresh(material)
    history = MaterialCostHistory(
        material_id=material.id,
        unit_cost_per_gram=material.price_per_gram,
        vendor=material.supplier,
        reference="material_create",
        note="Initial material cost",
    )
    session.add(history)
    session.commit()
    return material


@app.get("/materials", response_model=PaginatedMaterialsRead)
def list_materials(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Material.name.ilike(pattern),
                Material.brand.ilike(pattern),
                Material.category.ilike(pattern),
                Material.color.ilike(pattern),
                Material.supplier.ilike(pattern),
                Material.filament_type.ilike(pattern),
            )
        )
    statement = select(Material).order_by(Material.name).offset(offset).limit(limit)
    if filters:
        statement = statement.where(*filters)
    total_statement = select(func.count()).select_from(Material)
    if filters:
        total_statement = total_statement.where(*filters)
    materials = session.exec(statement).all()
    total = session.exec(total_statement).one()
    return PaginatedMaterialsRead(items=materials, total=total, limit=limit, offset=offset)


@app.get("/materials/{material_id}", response_model=MaterialRead)
def get_material(material_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@app.put("/materials/{material_id}", response_model=MaterialRead)
def update_material(
    material_id: int,
    payload: MaterialUpdate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    previous_price = material.price_per_gram
    previous_supplier = material.supplier
    update_data = payload.dict(exclude_unset=True)
    if {"brand", "color", "color_hex"} & update_data.keys():
        color_hex = update_data.get("color_hex", material.color_hex)
        update_data["color_hex"] = normalize_hex(color_hex)
    if "barcode" in update_data:
        update_data["barcode"] = normalize_barcode(update_data.get("barcode"))
    if "refill_barcode" in update_data:
        update_data["refill_barcode"] = normalize_barcode(update_data.get("refill_barcode"))
    for key, value in update_data.items():
        setattr(material, key, value)
    session.add(material)
    session.commit()
    session.refresh(material)
    if payload.price_per_gram is not None and payload.price_per_gram != previous_price:
        history = MaterialCostHistory(
            material_id=material.id,
            unit_cost_per_gram=material.price_per_gram,
            vendor=payload.supplier if payload.supplier is not None else previous_supplier,
            reference="material_update",
            note="Price updated",
        )
        session.add(history)
        session.commit()
    return material


@app.get("/materials/{material_id}/cost-history", response_model=List[MaterialCostHistoryRead])
def list_material_cost_history(
    material_id: int,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    if not session.get(Material, material_id):
        raise HTTPException(status_code=404, detail="Material not found")
    statement = select(MaterialCostHistory).where(MaterialCostHistory.material_id == material_id).order_by(
        MaterialCostHistory.recorded_at.desc()
    )
    return session.exec(statement).all()


@app.post("/materials/{material_id}/cost-history", response_model=MaterialCostHistoryRead, status_code=status.HTTP_201_CREATED)
def create_material_cost_history(
    material_id: int,
    payload: MaterialCostHistoryCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    if material_id != payload.material_id:
        raise HTTPException(status_code=400, detail="Material ID mismatch")
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    entry = MaterialCostHistory.from_orm(payload)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@app.get("/materials/{material_id}/barcode")
def get_material_barcode(
    material_id: int,
    value: str | None = None,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    selected_value = normalize_barcode(value) if value is not None else None
    available_values = {normalize_barcode(material.barcode), normalize_barcode(material.refill_barcode)}
    available_values.discard(None)
    if selected_value and selected_value not in available_values:
        raise HTTPException(status_code=400, detail="Barcode value does not match this material")
    barcode_to_render = selected_value or normalize_barcode(material.barcode) or normalize_barcode(material.refill_barcode)
    if not barcode_to_render:
        raise HTTPException(status_code=404, detail="Material barcode not set")
    png_bytes = render_barcode_png(barcode_to_render)
    headers = {"Cache-Control": "no-store"}
    return Response(content=png_bytes, media_type="image/png", headers=headers)


@app.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(material_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    try:
        _delete_material_dependencies(session, material_id)
        session.delete(material)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Material cannot be deleted because related records still reference it.",
        )
    return None


# Inventory endpoints
@app.post("/inventory", response_model=InventoryItemRead, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: InventoryItemCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    _ensure_material_exists(session, payload.material_id)
    data = payload.dict()
    data["spool_serial"] = normalize_barcode(data.get("spool_serial"))
    inventory_item = InventoryItem(**data)
    session.add(inventory_item)
    session.commit()
    session.refresh(inventory_item)
    return inventory_item


@app.get("/inventory", response_model=PaginatedInventoryRead)
def list_inventory_items(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                InventoryItem.location.ilike(pattern),
                InventoryItem.spool_serial.ilike(pattern),
                Material.name.ilike(pattern),
                Material.color.ilike(pattern),
            )
        )
    statement = (
        select(InventoryItem)
        .join(Material, InventoryItem.material_id == Material.id, isouter=True)
        .options(selectinload(InventoryItem.material))
        .order_by(InventoryItem.id)
        .offset(offset)
        .limit(limit)
    )
    if filters:
        statement = statement.where(*filters)
    total_statement = select(func.count()).select_from(InventoryItem).join(
        Material, InventoryItem.material_id == Material.id, isouter=True
    )
    if filters:
        total_statement = total_statement.where(*filters)
    items = session.exec(statement).all()
    total = session.exec(total_statement).one()
    return PaginatedInventoryRead(items=items, total=total, limit=limit, offset=offset)


@app.get("/inventory/{item_id}", response_model=InventoryItemRead)
def get_inventory_item(item_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@app.put("/inventory/{item_id}", response_model=InventoryItemRead)
def update_inventory_item(
    item_id: int,
    payload: InventoryItemUpdate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    update_data = payload.dict(exclude_unset=True)
    if "material_id" in update_data:
        _ensure_material_exists(session, update_data["material_id"])
    if "spool_serial" in update_data:
        update_data["spool_serial"] = normalize_barcode(update_data.get("spool_serial"))
    for key, value in update_data.items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@app.delete("/inventory/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(item_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    session.delete(item)
    session.commit()
    return None


# Stock movement endpoints
@app.post("/movements", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def create_stock_movement(
    payload: StockMovementCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    item = session.get(InventoryItem, payload.inventory_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    new_qty = item.quantity_grams + payload.change_grams
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Stock level cannot be negative")

    movement = StockMovement.from_orm(payload)
    item.quantity_grams = new_qty
    session.add(movement)
    session.add(item)
    session.commit()
    session.refresh(movement)
    return movement


@app.get("/inventory/{item_id}/movements", response_model=List[StockMovementRead])
def list_movements(item_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    _ensure_inventory_exists(session, item_id)
    statement = select(StockMovement).where(StockMovement.inventory_item_id == item_id).order_by(
        StockMovement.created_at.desc()
    )
    movements = session.exec(statement).all()
    return movements


# Hardware endpoints
@app.post("/hardware", response_model=HardwareItemRead, status_code=status.HTTP_201_CREATED)
def create_hardware_item(
    payload: HardwareItemCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    item = HardwareItem.from_orm(payload)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@app.get("/hardware", response_model=PaginatedHardwareRead)
def list_hardware_items(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                HardwareItem.name.ilike(pattern),
                HardwareItem.category.ilike(pattern),
                HardwareItem.supplier.ilike(pattern),
                HardwareItem.manufacturer_part_number.ilike(pattern),
                HardwareItem.bin_location.ilike(pattern),
            )
        )
    statement = select(HardwareItem).order_by(HardwareItem.name).offset(offset).limit(limit)
    if filters:
        statement = statement.where(*filters)
    total_statement = select(func.count()).select_from(HardwareItem)
    if filters:
        total_statement = total_statement.where(*filters)
    items = session.exec(statement).all()
    total = session.exec(total_statement).one()
    return PaginatedHardwareRead(items=items, total=total, limit=limit, offset=offset)


@app.get("/hardware/{hardware_id}", response_model=HardwareItemRead)
def get_hardware_item(hardware_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    item = session.get(HardwareItem, hardware_id)
    if not item:
        raise HTTPException(status_code=404, detail="Hardware item not found")
    return item


@app.put("/hardware/{hardware_id}", response_model=HardwareItemRead)
def update_hardware_item(
    hardware_id: int,
    payload: HardwareItemUpdate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    item = session.get(HardwareItem, hardware_id)
    if not item:
        raise HTTPException(status_code=404, detail="Hardware item not found")
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@app.delete("/hardware/{hardware_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hardware_item(hardware_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    item = session.get(HardwareItem, hardware_id)
    if not item:
        raise HTTPException(status_code=404, detail="Hardware item not found")
    session.delete(item)
    session.commit()
    return None


@app.post("/hardware/movements", response_model=HardwareMovementRead, status_code=status.HTTP_201_CREATED)
def create_hardware_movement(
    payload: HardwareMovementCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    item = session.get(HardwareItem, payload.hardware_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Hardware item not found")
    new_qty = item.quantity_on_hand + payload.change_units
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Stock level cannot be negative")
    movement = HardwareMovement.from_orm(payload)
    item.quantity_on_hand = new_qty
    session.add(item)
    session.add(movement)
    session.commit()
    session.refresh(movement)
    return movement


@app.get("/hardware/{hardware_id}/movements", response_model=List[HardwareMovementRead])
def list_hardware_movements(hardware_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    _ensure_hardware_exists(session, hardware_id)
    statement = select(HardwareMovement).where(HardwareMovement.hardware_item_id == hardware_id).order_by(
        HardwareMovement.created_at.desc()
    )
    return session.exec(statement).all()


@app.post("/makerworks/merch/sync")
def sync_makerworks_merch_inventory(
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    return _sync_makerworks_merch_to_hardware(session)


# 3D model endpoints
@app.post("/models", response_model=PrintModelRead, status_code=status.HTTP_201_CREATED)
def create_print_model(
    payload: PrintModelCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    data = payload.dict()
    data["sku"] = normalize_sku(data.get("sku"))
    model = PrintModel(**data)
    session.add(model)
    session.flush()
    _sync_model_to_makerworks_product_template(session, model)
    session.commit()
    session.refresh(model)
    return _model_read_with_totals(session, model)


@app.get("/models", response_model=PaginatedModelsRead)
def list_print_models(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                PrintModel.name.ilike(pattern),
                PrintModel.category.ilike(pattern),
                PrintModel.sku.ilike(pattern),
                PrintModel.designer.ilike(pattern),
                PrintModel.platform.ilike(pattern),
            )
        )
    statement = select(PrintModel).order_by(PrintModel.name).offset(offset).limit(limit)
    if filters:
        statement = statement.where(*filters)
    models = session.exec(statement).all()
    total_statement = select(func.count()).select_from(PrintModel)
    if filters:
        total_statement = total_statement.where(*filters)
    total = session.exec(total_statement).one()
    totals = _model_sales_summary(session, [model.id for model in models if model.id])
    return PaginatedModelsRead(
        items=[_model_read_with_totals(session, model, totals) for model in models],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/models/{model_id}", response_model=PrintModelRead)
def get_print_model(model_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    model = session.get(PrintModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return _model_read_with_totals(session, model)


@app.put("/models/{model_id}", response_model=PrintModelRead)
def update_print_model(
    model_id: int,
    payload: PrintModelUpdate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    model = session.get(PrintModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    update_data = payload.dict(exclude_unset=True)
    if "sku" in update_data:
        update_data["sku"] = normalize_sku(update_data.get("sku"))
    for key, value in update_data.items():
        setattr(model, key, value)
    session.add(model)
    session.commit()
    session.refresh(model)
    return _model_read_with_totals(session, model)


@app.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_print_model(model_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    model = session.get(PrintModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    sales = session.exec(select(PrintModelSale).where(PrintModelSale.model_id == model_id)).all()
    for sale in sales:
        session.delete(sale)
    session.delete(model)
    session.commit()
    return None


@app.post("/models/sales", response_model=PrintModelSaleRead, status_code=status.HTTP_201_CREATED)
def create_print_model_sale(
    payload: PrintModelSaleCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    _ensure_model_exists(session, payload.model_id)
    sale = PrintModelSale.from_orm(payload)
    session.add(sale)
    session.commit()
    session.refresh(sale)
    return sale


@app.get("/models/{model_id}/sales", response_model=List[PrintModelSaleRead])
def list_print_model_sales(model_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    _ensure_model_exists(session, model_id)
    statement = select(PrintModelSale).where(PrintModelSale.model_id == model_id).order_by(
        PrintModelSale.sold_at.desc()
    )
    return session.exec(statement).all()


# Pricing endpoint
@app.post("/pricing/quote", response_model=PricingResponse)
def calculate_quote(
    payload: PricingRequest,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    material = session.get(Material, payload.material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found for quote")

    material_cost = payload.weight_grams * material.price_per_gram
    machine_cost = payload.print_time_hours * payload.machine_hour_rate
    subtotal = material_cost + machine_cost + payload.labor_cost
    margin_amount = subtotal * (payload.margin_pct / 100)
    total_price = subtotal + margin_amount

    breakdown = PricingBreakdown(
        material_cost=round(material_cost, 2),
        machine_cost=round(machine_cost, 2),
        labor_cost=round(payload.labor_cost, 2),
        subtotal=round(subtotal, 2),
        margin_amount=round(margin_amount, 2),
        total_price=round(total_price, 2),
    )

    return PricingResponse(pricing=breakdown, material_snapshot=MaterialRead.from_orm(material))


@app.get("/orderworks/jobs")
def fetch_orderworks_jobs(
    _: bool = Depends(require_auth),
    session: Session = Depends(get_session),
):
    base_url_override = os.environ.get("ORDERWORKS_BASE_URL", "")
    try:
        jobs = list_orderworks_jobs_via_database(session)
    except OrderWorksDatabaseUnavailableError as db_error:
        client = get_orderworks_client()
        if not client.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{db_error}. Provide ORDERWORKS_* credentials for HTTP fallback or verify DATABASE_URL.",
            )
        try:
            jobs = client.list_jobs()
        except OrderWorksNotConfiguredError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OrderWorks integration is not configured.",
            )
        except OrderWorksAuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
        except OrderWorksIntegrationError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
        return {"jobs": jobs, "base_url": client.base_url}
    return {"jobs": jobs, "base_url": base_url_override}


@app.get("/bambu-view/filaments")
def fetch_bambu_view_filaments(_: bool = Depends(require_auth)):
    client = get_bambu_view_client()
    if not client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bambu View integration is not configured. Set BAMBU_VIEW_BASE_URL.",
        )
    try:
        fleet = client.fetch_fleet()
    except BambuViewNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bambu View integration is not configured.",
        )
    except BambuViewAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except BambuViewIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    printers = []
    loaded_count = 0
    for printer in fleet:
        if not isinstance(printer, dict):
            continue
        ams = printer.get("ams") if isinstance(printer.get("ams"), dict) else {}
        trays = ams.get("trays") if isinstance(ams.get("trays"), list) else []
        loaded_trays = [_normalize_loaded_tray(item) for item in trays if _is_loaded_tray(item)]
        loaded_count += len(loaded_trays)
        printers.append(
            {
                "printer_id": str(printer.get("printer_id") or ""),
                "printer_name": str(printer.get("printer_name") or printer.get("printer_id") or "Printer"),
                "ams_slots": ams.get("slots"),
                "ams_units": ams.get("units"),
                "loaded_trays": loaded_trays,
            }
        )
    return {"printers": printers, "loaded_count": loaded_count, "base_url": client.base_url}


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


def _ensure_material_exists(session: Session, material_id: int) -> None:
    if not session.get(Material, material_id):
        raise HTTPException(status_code=404, detail="Material not found")


def _is_loaded_tray(tray: object) -> bool:
    if not isinstance(tray, dict):
        return False
    material = str(tray.get("material") or tray.get("tray_type") or "").strip()
    name = str(tray.get("name") or tray.get("tray_id_name") or "").strip()
    state_value = str(tray.get("state") or tray.get("tray_state") or "").strip().lower()
    if material or name:
        return True
    if state_value in {"loaded", "ready", "available", "installed"}:
        return True
    if state_value in {"", "none", "empty"}:
        return False
    return False


def _normalize_loaded_tray(tray: object) -> dict[str, object]:
    if not isinstance(tray, dict):
        return {"id": "", "unit": None, "slot": None, "material": "", "name": "", "color": "", "state": ""}
    return {
        "id": str(tray.get("id") or ""),
        "unit": tray.get("unit"),
        "slot": tray.get("slot"),
        "material": str(tray.get("material") or tray.get("tray_type") or "").strip(),
        "name": str(tray.get("name") or tray.get("tray_id_name") or "").strip(),
        "color": str(tray.get("color") or "").strip(),
        "state": str(tray.get("state") or tray.get("tray_state") or "").strip(),
    }


def _delete_material_dependencies(session: Session, material_id: int) -> None:
    inventory_items = session.exec(select(InventoryItem).where(InventoryItem.material_id == material_id)).all()
    inventory_ids = [item.id for item in inventory_items if item.id is not None]

    if inventory_ids:
        movements = session.exec(
            select(StockMovement).where(StockMovement.inventory_item_id.in_(inventory_ids))
        ).all()
        for movement in movements:
            session.delete(movement)

    for item in inventory_items:
        session.delete(item)

    cost_history_entries = session.exec(
        select(MaterialCostHistory).where(MaterialCostHistory.material_id == material_id)
    ).all()
    for entry in cost_history_entries:
        session.delete(entry)


def _ensure_unique_material_name(session: Session, name: str) -> str:
    base = (name or "").strip()
    if not base:
        return base
    normalized = base.lower()
    exists = session.exec(select(Material).where(func.lower(Material.name) == normalized)).first()
    if not exists:
        return base
    suffix = 1
    while True:
        candidate = f"{base} {suffix}"
        candidate_exists = session.exec(
            select(Material).where(func.lower(Material.name) == candidate.lower())
        ).first()
        if not candidate_exists:
            return candidate
        suffix += 1


def _ensure_inventory_exists(session: Session, item_id: int) -> None:
    if not session.get(InventoryItem, item_id):
        raise HTTPException(status_code=404, detail="Inventory item not found")


def _ensure_hardware_exists(session: Session, hardware_id: int) -> None:
    if not session.get(HardwareItem, hardware_id):
        raise HTTPException(status_code=404, detail="Hardware item not found")


def _ensure_model_exists(session: Session, model_id: int) -> None:
    if not session.get(PrintModel, model_id):
        raise HTTPException(status_code=404, detail="Model not found")


def _model_sales_summary(session: Session, model_ids: List[int]) -> dict[int, tuple[int, float]]:
    if not model_ids:
        return {}
    statement = (
        select(
            PrintModelSale.model_id,
            func.sum(PrintModelSale.quantity),
            func.sum(PrintModelSale.quantity * PrintModelSale.unit_price),
        )
        .where(PrintModelSale.model_id.in_(model_ids))
        .group_by(PrintModelSale.model_id)
    )
    rows = session.exec(statement).all()
    summary: dict[int, tuple[int, float]] = {}
    for model_id, total_units, total_revenue in rows:
        summary[int(model_id)] = (int(total_units or 0), float(total_revenue or 0))
    return summary


def _model_read_with_totals(
    session: Session,
    model: PrintModel,
    summary: dict[int, tuple[int, float]] | None = None,
) -> PrintModelRead:
    data = PrintModelRead.from_orm(model)
    if model.id is None:
        return data
    totals = summary.get(model.id) if summary is not None else _model_sales_summary(session, [model.id])
    if isinstance(totals, dict):
        totals = totals.get(model.id)
    if totals:
        data.total_sold = int(totals[0] or 0)
        data.total_revenue = float(totals[1] or 0)
    return data


def _sync_model_to_makerworks_product_template(session: Session, model: PrintModel) -> None:
    if model.id is None:
        return
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    conn = session.connection()
    exists = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'ProductTemplate'
            """
        )
    ).first()
    if not exists:
        return

    description = (model.notes or "").strip() or (model.category or "").strip() or None
    now = datetime.utcnow()
    existing = conn.execute(
        text(
            """
            SELECT "id"
            FROM public."ProductTemplate"
            WHERE "stockworksInventoryItemId" = :model_id
            LIMIT 1
            """
        ),
        {"model_id": model.id},
    ).first()

    try:
        if existing:
            conn.execute(
                text(
                    """
                    UPDATE public."ProductTemplate"
                    SET "title" = :title,
                        "description" = :description,
                        "isActive" = :is_active,
                        "updatedAt" = :updated_at
                    WHERE "id" = :product_id
                    """
                ),
                {
                    "title": model.name,
                    "description": description,
                    "is_active": bool(model.active),
                    "updated_at": now,
                    "product_id": existing[0],
                },
            )
            return

        conn.execute(
            text(
                """
                INSERT INTO public."ProductTemplate" (
                    "id",
                    "title",
                    "description",
                    "isActive",
                    "createdAt",
                    "updatedAt",
                    "stockworksInventoryItemId"
                ) VALUES (
                    :id,
                    :title,
                    :description,
                    :is_active,
                    :created_at,
                    :updated_at,
                    :stockworks_inventory_item_id
                )
                """
            ),
            {
                "id": f"stockworks-model-{model.id}",
                "title": model.name,
                "description": description,
                "is_active": bool(model.active),
                "created_at": now,
                "updated_at": now,
                "stockworks_inventory_item_id": model.id,
            },
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to sync model to MakerWorks ProductTemplate: {exc}",
        ) from exc


def _sync_makerworks_merch_to_hardware(session: Session) -> dict[str, Any]:
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MakerWorks merch sync requires a shared PostgreSQL database connection.",
        )

    conn = session.connection()
    table_exists = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'ProductTemplate'
            """
        )
    ).first()
    if not table_exists:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='MakerWorks table public."ProductTemplate" was not found.',
        )

    available_columns = _fetch_table_columns(conn, "public", "ProductTemplate")
    id_column = _find_matching_column(available_columns, ["id"])
    title_column = _find_matching_column(available_columns, ["title", "name"])
    description_column = _find_matching_column(available_columns, ["description", "details"])
    active_column = _find_matching_column(available_columns, ["isActive", "active", "enabled"])
    stockworks_link_column = _find_matching_column(
        available_columns, ["stockworksInventoryItemId", "stockworks_inventory_item_id"]
    )
    quantity_column = _find_matching_column(
        available_columns,
        [
            "quantityOnHand",
            "stockOnHand",
            "inventoryQuantity",
            "inventoryCount",
            "availableQuantity",
            "onHand",
            "stock",
        ],
    )
    reorder_column = _find_matching_column(available_columns, ["reorderLevel", "reorderPoint", "restockThreshold"])
    unit_column = _find_matching_column(available_columns, ["unitOfMeasure", "uom", "unit"])

    if not id_column or not title_column:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='MakerWorks ProductTemplate is missing required merch columns ("id" and/or "title").',
        )

    select_parts = [
        f'{_quote_identifier(id_column)} AS "makerworks_id"',
        f'{_quote_identifier(title_column)} AS "title"',
    ]
    if description_column:
        select_parts.append(f'{_quote_identifier(description_column)} AS "description"')
    else:
        select_parts.append('NULL AS "description"')
    if active_column:
        select_parts.append(f'{_quote_identifier(active_column)} AS "is_active"')
    else:
        select_parts.append('TRUE AS "is_active"')
    if stockworks_link_column:
        select_parts.append(f'{_quote_identifier(stockworks_link_column)} AS "stockworks_inventory_item_id"')
    else:
        select_parts.append('NULL AS "stockworks_inventory_item_id"')
    if quantity_column:
        select_parts.append(f'{_quote_identifier(quantity_column)} AS "quantity_on_hand"')
    else:
        select_parts.append('NULL AS "quantity_on_hand"')
    if reorder_column:
        select_parts.append(f'{_quote_identifier(reorder_column)} AS "reorder_level"')
    else:
        select_parts.append('NULL AS "reorder_level"')
    if unit_column:
        select_parts.append(f'{_quote_identifier(unit_column)} AS "unit_of_measure"')
    else:
        select_parts.append('NULL AS "unit_of_measure"')

    where_fragments = []
    if stockworks_link_column:
        quoted_link = _quote_identifier(stockworks_link_column)
        where_fragments.append(f"({quoted_link} IS NULL OR {quoted_link}::text = '')")
    if active_column:
        quoted_active = _quote_identifier(active_column)
        where_fragments.append(f"COALESCE({quoted_active}, TRUE) = TRUE")
    where_sql = f"WHERE {' AND '.join(where_fragments)}" if where_fragments else ""
    select_sql = ", ".join(select_parts)
    query = text(
        f'SELECT {select_sql} FROM public."ProductTemplate" {where_sql} ORDER BY {_quote_identifier(title_column)} ASC'
    )

    rows = conn.execute(query).mappings().all()
    linked_items = session.exec(
        select(HardwareItem).where(HardwareItem.makerworks_product_template_id.is_not(None))
    ).all()
    unlinked_merch_items = session.exec(
        select(HardwareItem).where(HardwareItem.makerworks_product_template_id.is_(None))
    ).all()
    linked_by_template_id = {
        str(item.makerworks_product_template_id): item
        for item in linked_items
        if item.makerworks_product_template_id
    }
    unlinked_merch_by_name = {
        (item.name or "").strip().lower(): item
        for item in unlinked_merch_items
        if (item.category or "").strip().lower() == "merch" and (item.name or "").strip()
    }

    created = 0
    updated = 0
    skipped = 0
    source_count = len(rows)
    synced_ids: set[str] = set()

    for row in rows:
        makerworks_id = str(row.get("makerworks_id") or "").strip()
        title = str(row.get("title") or "").strip()
        if not makerworks_id or not title:
            skipped += 1
            continue
        synced_ids.add(makerworks_id)
        item = linked_by_template_id.get(makerworks_id)
        if item is None:
            item = unlinked_merch_by_name.get(title.lower())
        quantity_on_hand = _coerce_non_negative_number(row.get("quantity_on_hand"))
        reorder_level = _coerce_non_negative_number(row.get("reorder_level"))
        unit_of_measure = str(row.get("unit_of_measure") or "").strip() or "piece"
        description = str(row.get("description") or "").strip() or None
        category = "merch"

        if item:
            item.name = title
            item.category = category
            item.makerworks_product_template_id = makerworks_id
            item.unit_of_measure = unit_of_measure
            if quantity_on_hand is not None:
                item.quantity_on_hand = quantity_on_hand
            if reorder_level is not None:
                item.reorder_level = reorder_level
            if description and not item.notes:
                item.notes = description
            session.add(item)
            updated += 1
            continue

        created_item = HardwareItem(
            name=title,
            category=category,
            unit_of_measure=unit_of_measure,
            quantity_on_hand=quantity_on_hand if quantity_on_hand is not None else 0,
            reorder_level=reorder_level if reorder_level is not None else 0,
            notes=description,
            makerworks_product_template_id=makerworks_id,
        )
        session.add(created_item)
        created += 1

    session.commit()

    return {
        "source_count": source_count,
        "synced_count": len(synced_ids),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "quantity_source_column": quantity_column,
        "reorder_source_column": reorder_column,
        "unit_source_column": unit_column,
    }


def _fetch_table_columns(connection: Any, schema: str, table: str) -> set[str]:
    result = connection.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            """
        ),
        {"schema": schema, "table": table},
    )
    return {str(row[0]) for row in result}


def _find_matching_column(available: set[str], candidates: list[str]) -> Optional[str]:
    lowered = {column.lower(): column for column in available}
    for candidate in candidates:
        found = lowered.get(candidate.lower())
        if found:
            return found
    return None


def _quote_identifier(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def _coerce_non_negative_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return 0.0
    return number
