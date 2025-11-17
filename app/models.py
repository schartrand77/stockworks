"""SQLModel models for the StockWorks domain."""
from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class MaterialBase(SQLModel):
    name: str
    filament_type: str
    color: str
    supplier: Optional[str] = None
    brand: Optional[str] = None
    price_per_gram: float = Field(gt=0, description="Base material cost per gram")
    spool_weight_grams: int = Field(gt=0, description="Total grams per spool")
    notes: Optional[str] = None


class Material(MaterialBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_items: List["InventoryItem"] = Relationship(back_populates="material")


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(SQLModel):
    name: Optional[str] = None
    filament_type: Optional[str] = None
    color: Optional[str] = None
    supplier: Optional[str] = None
    brand: Optional[str] = None
    price_per_gram: Optional[float] = Field(default=None, gt=0)
    spool_weight_grams: Optional[int] = Field(default=None, gt=0)
    notes: Optional[str] = None


class MaterialRead(MaterialBase):
    id: int


class InventoryItemBase(SQLModel):
    location: str
    quantity_grams: float = Field(ge=0, description="Current stock level in grams")
    reorder_level: float = Field(ge=0, description="Threshold where replenishment is required")
    spool_serial: Optional[str] = Field(default=None, description="ID marked on the spool")
    unit_cost_override: Optional[float] = Field(default=None, ge=0)


class InventoryItem(InventoryItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    material_id: int = Field(foreign_key="material.id")

    material: Optional[Material] = Relationship(back_populates="inventory_items")
    movements: List["StockMovement"] = Relationship(back_populates="inventory_item")


class InventoryItemCreate(InventoryItemBase):
    material_id: int


class InventoryItemUpdate(SQLModel):
    location: Optional[str] = None
    quantity_grams: Optional[float] = Field(default=None, ge=0)
    reorder_level: Optional[float] = Field(default=None, ge=0)
    spool_serial: Optional[str] = None
    unit_cost_override: Optional[float] = Field(default=None, ge=0)
    material_id: Optional[int] = None


class InventoryItemRead(InventoryItemBase):
    id: int
    material_id: int
    material: Optional[MaterialRead]


class StockMovementBase(SQLModel):
    movement_type: str = Field(description="incoming, outgoing, or adjustment")
    change_grams: float = Field(description="Positive for inbound, negative for outbound")
    reference: Optional[str] = Field(default=None, description="Job number or PO reference")
    note: Optional[str] = None


class StockMovement(StockMovementBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_item_id: int = Field(foreign_key="inventoryitem.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    inventory_item: Optional[InventoryItem] = Relationship(back_populates="movements")


class StockMovementCreate(StockMovementBase):
    inventory_item_id: int


class StockMovementRead(StockMovementBase):
    id: int
    inventory_item_id: int
    created_at: datetime


class PricingRequest(SQLModel):
    material_id: int
    weight_grams: float = Field(gt=0)
    print_time_hours: float = Field(gt=0)
    machine_hour_rate: float = Field(gt=0, description="Hourly cost to run the printer")
    labor_cost: float = Field(ge=0)
    margin_pct: float = Field(ge=0, description="Markup percentage applied to costs")


class PricingBreakdown(SQLModel):
    material_cost: float
    machine_cost: float
    labor_cost: float
    subtotal: float
    margin_amount: float
    total_price: float


class PricingResponse(SQLModel):
    pricing: PricingBreakdown
    material_snapshot: MaterialRead
