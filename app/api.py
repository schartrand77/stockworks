"""FastAPI application implementing inventory control for a 3D printing service."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from .db import get_session, init_db
from .models import (
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
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="StockWorks", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    """Serve the HTML shell for the single-page UI."""
    return templates.TemplateResponse("index.html", {"request": request})


# Material endpoints
@app.post("/materials", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(payload: MaterialCreate, session: Session = Depends(get_session)):
    material = Material.from_orm(payload)
    session.add(material)
    session.commit()
    session.refresh(material)
    return material


@app.get("/materials", response_model=List[MaterialRead])
def list_materials(session: Session = Depends(get_session)):
    materials = session.exec(select(Material).order_by(Material.name)).all()
    return materials


@app.get("/materials/{material_id}", response_model=MaterialRead)
def get_material(material_id: int, session: Session = Depends(get_session)):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@app.put("/materials/{material_id}", response_model=MaterialRead)
def update_material(material_id: int, payload: MaterialUpdate, session: Session = Depends(get_session)):
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
def delete_material(material_id: int, session: Session = Depends(get_session)):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    session.delete(material)
    session.commit()
    return None


# Inventory endpoints
@app.post("/inventory", response_model=InventoryItemRead, status_code=status.HTTP_201_CREATED)
def create_inventory_item(payload: InventoryItemCreate, session: Session = Depends(get_session)):
    _ensure_material_exists(session, payload.material_id)
    inventory_item = InventoryItem.from_orm(payload)
    session.add(inventory_item)
    session.commit()
    session.refresh(inventory_item)
    return inventory_item


@app.get("/inventory", response_model=List[InventoryItemRead])
def list_inventory_items(session: Session = Depends(get_session)):
    items = session.exec(select(InventoryItem)).all()
    return items


@app.get("/inventory/{item_id}", response_model=InventoryItemRead)
def get_inventory_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@app.put("/inventory/{item_id}", response_model=InventoryItemRead)
def update_inventory_item(item_id: int, payload: InventoryItemUpdate, session: Session = Depends(get_session)):
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
def delete_inventory_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    session.delete(item)
    session.commit()
    return None


# Stock movement endpoints
@app.post("/movements", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def create_stock_movement(payload: StockMovementCreate, session: Session = Depends(get_session)):
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
def list_movements(item_id: int, session: Session = Depends(get_session)):
    _ensure_inventory_exists(session, item_id)
    statement = select(StockMovement).where(StockMovement.inventory_item_id == item_id).order_by(
        StockMovement.created_at.desc()
    )
    movements = session.exec(statement).all()
    return movements


# Pricing endpoint
@app.post("/pricing/quote", response_model=PricingResponse)
def calculate_quote(payload: PricingRequest, session: Session = Depends(get_session)):
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


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


def _ensure_material_exists(session: Session, material_id: int) -> None:
    if not session.get(Material, material_id):
        raise HTTPException(status_code=404, detail="Material not found")


def _ensure_inventory_exists(session: Session, item_id: int) -> None:
    if not session.get(InventoryItem, item_id):
        raise HTTPException(status_code=404, detail="Inventory item not found")
