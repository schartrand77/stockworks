"""FastAPI application implementing inventory control for a 3D printing service."""
from __future__ import annotations

import mimetypes
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from .db import get_session, init_db
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
    PricingBreakdown,
    PricingRequest,
    PricingResponse,
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
    material = Material.from_orm(payload)
    session.add(material)
    session.commit()
    session.refresh(material)
    return material


@app.get("/materials", response_model=List[MaterialRead])
def list_materials(session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    materials = session.exec(select(Material).order_by(Material.name)).all()
    return materials


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
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(material, key, value)
    session.add(material)
    session.commit()
    session.refresh(material)
    return material


@app.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(material_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    session.delete(material)
    session.commit()
    return None


# Inventory endpoints
@app.post("/inventory", response_model=InventoryItemRead, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: InventoryItemCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    _ensure_material_exists(session, payload.material_id)
    inventory_item = InventoryItem.from_orm(payload)
    session.add(inventory_item)
    session.commit()
    session.refresh(inventory_item)
    return inventory_item


@app.get("/inventory", response_model=List[InventoryItemRead])
def list_inventory_items(session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    items = session.exec(select(InventoryItem)).all()
    return items


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


@app.get("/hardware", response_model=List[HardwareItemRead])
def list_hardware_items(session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    statement = select(HardwareItem).order_by(HardwareItem.name)
    return session.exec(statement).all()


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


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


def _ensure_material_exists(session: Session, material_id: int) -> None:
    if not session.get(Material, material_id):
        raise HTTPException(status_code=404, detail="Material not found")


def _ensure_inventory_exists(session: Session, item_id: int) -> None:
    if not session.get(InventoryItem, item_id):
        raise HTTPException(status_code=404, detail="Inventory item not found")


def _ensure_hardware_exists(session: Session, hardware_id: int) -> None:
    if not session.get(HardwareItem, hardware_id):
        raise HTTPException(status_code=404, detail="Hardware item not found")
