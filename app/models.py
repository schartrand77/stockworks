"""SQLModel models for the StockWorks domain."""
import json
from datetime import datetime
from typing import Any, List, Optional

from pydantic import field_validator
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel


class AppSetting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    category: str = Field(index=True)
    value: Optional[str] = None
    secret: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MaterialBase(SQLModel):
    name: str = Field(index=True)
    brand: Optional[str] = None
    filament_type: str
    category: Optional[str] = Field(default=None, index=True, description="Finishes like basic, matte, silk, cf, etc.")
    color: str
    color_hex: Optional[str] = Field(default=None, description="Hex code for UI color swatches")
    color_hexes: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Up to 4 hex colors used to render a segmented color swatch.",
    )
    supplier: Optional[str] = None
    price_per_gram: float = Field(gt=0, description="Base material cost per gram")
    spool_weight_grams: int = Field(gt=0, description="Total grams per spool")
    barcode: Optional[str] = Field(default=None, description="UPC/EAN/SKU barcode reference")
    refill_barcode: Optional[str] = Field(default=None, description="Alternate barcode reference (e.g., refill)")
    notes: Optional[str] = None


class Material(MaterialBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_items: List["InventoryItem"] = Relationship(back_populates="material")
    cost_history: List["MaterialCostHistory"] = Relationship(back_populates="material")


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(SQLModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    filament_type: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    color_hex: Optional[str] = None
    color_hexes: Optional[List[str]] = None
    supplier: Optional[str] = None
    price_per_gram: Optional[float] = Field(default=None, gt=0)
    spool_weight_grams: Optional[int] = Field(default=None, gt=0)
    barcode: Optional[str] = None
    refill_barcode: Optional[str] = None
    notes: Optional[str] = None


class MaterialRead(MaterialBase):
    id: int
    color_hexes: List[str] = Field(default_factory=list)

    @field_validator("color_hexes", mode="before")
    @classmethod
    def normalize_color_hexes(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped or stripped.lower() == "null":
                return []
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return []
            return parsed if isinstance(parsed, list) else []
        return value or []


class MaterialCostHistoryBase(SQLModel):
    material_id: int = Field(foreign_key="material.id")
    unit_cost_per_gram: float = Field(gt=0, description="Recorded material cost per gram")
    vendor: Optional[str] = None
    reference: Optional[str] = Field(default=None, description="PO, invoice, or receipt reference")
    note: Optional[str] = None


class MaterialCostHistory(MaterialCostHistoryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

    material: Optional[Material] = Relationship(back_populates="cost_history")


class MaterialCostHistoryCreate(MaterialCostHistoryBase):
    pass


class MaterialCostHistoryRead(MaterialCostHistoryBase):
    id: int
    recorded_at: datetime


class InventoryItemBase(SQLModel):
    location: str = Field(index=True)
    quantity_grams: float = Field(ge=0, description="Current stock level in grams")
    reorder_level: float = Field(ge=0, description="Threshold where replenishment is required")
    spool_serial: Optional[str] = Field(default=None, description="ID marked on the spool")
    unit_cost_override: Optional[float] = Field(default=None, ge=0)


class InventoryItem(InventoryItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    material_id: int = Field(foreign_key="material.id", index=True)

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


class InboundInvoiceBase(SQLModel):
    vendor: str = Field(index=True)
    invoice_number: str = Field(index=True)
    order_number: Optional[str] = Field(default=None, index=True)
    invoice_date: Optional[str] = None
    delivery_date: Optional[str] = None
    payment_date: Optional[str] = None
    source_filename: Optional[str] = None
    invoice_file_path: Optional[str] = None
    packing_slip_filename: Optional[str] = None
    packing_slip_file_path: Optional[str] = None
    status: str = Field(default="pending_packing_slip", index=True)
    expected_location: str = Field(default="Receiving")
    reorder_level: float = Field(default=0, ge=0)
    verification_note: Optional[str] = None
    total_expected_grams: float = Field(default=0, ge=0)
    total_received_grams: float = Field(default=0, ge=0)


class InboundInvoice(InboundInvoiceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    packing_slip_uploaded_at: Optional[datetime] = Field(default=None, index=True)
    verified_at: Optional[datetime] = Field(default=None, index=True)

    lines: List["InboundInvoiceLine"] = Relationship(back_populates="invoice")
    audit_events: List["InboundReceiptAuditEvent"] = Relationship(back_populates="invoice")


class InboundInvoiceLineBase(SQLModel):
    invoice_id: int = Field(foreign_key="inboundinvoice.id")
    material_id: Optional[int] = Field(default=None, foreign_key="material.id")
    sku: str = Field(index=True)
    product_name: str
    filament_type: str
    category: Optional[str] = None
    color: str
    variant_code: Optional[str] = None
    package_type: str
    spool_weight_grams: int = Field(gt=0)
    expected_quantity: int = Field(ge=0)
    received_quantity: int = Field(default=0, ge=0)
    unit_cost_per_gram: float = Field(gt=0)
    items_subtotal: float = Field(ge=0)
    tax_name: Optional[str] = None
    tax_amount: float = Field(default=0, ge=0)
    status: str = Field(default="pending", index=True)
    note: Optional[str] = None


class InboundInvoiceLine(InboundInvoiceLineBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    invoice: Optional[InboundInvoice] = Relationship(back_populates="lines")
    material: Optional[Material] = Relationship()


class InboundInvoiceLineRead(InboundInvoiceLineBase):
    id: int


class InboundInvoiceRead(InboundInvoiceBase):
    id: int
    uploaded_at: datetime
    packing_slip_uploaded_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    lines: List[InboundInvoiceLineRead] = Field(default_factory=list)


class InboundReceiptAuditEventBase(SQLModel):
    invoice_id: int = Field(foreign_key="inboundinvoice.id", index=True)
    event_type: str = Field(index=True)
    actor_username: str = Field(index=True)
    actor_role: str = Field(index=True)
    summary: str
    details_json: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON, nullable=True))


class InboundReceiptAuditEvent(InboundReceiptAuditEventBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    invoice: Optional[InboundInvoice] = Relationship(back_populates="audit_events")


class InboundReceiptAuditEventRead(InboundReceiptAuditEventBase):
    id: int
    created_at: datetime


class InboundInvoiceVerifyLine(SQLModel):
    line_id: int
    received_quantity: int = Field(ge=0)


class InboundInvoiceVerifyRequest(SQLModel):
    location: Optional[str] = None
    note: Optional[str] = None
    lines: List[InboundInvoiceVerifyLine]


class StockMovementBase(SQLModel):
    movement_type: str = Field(description="incoming, outgoing, or adjustment")
    change_grams: float = Field(description="Positive for inbound, negative for outbound")
    reference: Optional[str] = Field(default=None, description="Job number or PO reference")
    note: Optional[str] = None


class StockMovement(StockMovementBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_item_id: int = Field(foreign_key="inventoryitem.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

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


class HardwareItemBase(SQLModel):
    name: str = Field(index=True)
    category: Optional[str] = Field(default=None, index=True, description="E.g. magnets, inserts, screws")
    merch_color: Optional[str] = Field(default=None, description="Merch color variant")
    merch_size: Optional[str] = Field(default=None, description="Merch size variant")
    merch_style: Optional[str] = Field(default=None, description="Merch style or fit")
    merch_sku: Optional[str] = Field(default=None, description="Merch SKU/variant code")
    supplier: Optional[str] = None
    manufacturer_part_number: Optional[str] = Field(default=None, description="Vendor or manufacturer reference")
    unit_of_measure: str = Field(default="piece", description="e.g. piece, set, pack")
    unit_cost: float = Field(default=0, ge=0)
    bin_location: Optional[str] = Field(default=None, description="Storage location reference")
    reorder_level: float = Field(default=0, ge=0)
    quantity_on_hand: float = Field(default=0, ge=0)
    notes: Optional[str] = None


class HardwareItem(HardwareItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    makerworks_product_template_id: Optional[str] = Field(default=None, index=True)
    movements: List["HardwareMovement"] = Relationship(back_populates="hardware_item")


class HardwareItemCreate(HardwareItemBase):
    pass


class HardwareItemUpdate(SQLModel):
    name: Optional[str] = None
    category: Optional[str] = None
    merch_color: Optional[str] = None
    merch_size: Optional[str] = None
    merch_style: Optional[str] = None
    merch_sku: Optional[str] = None
    supplier: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    unit_of_measure: Optional[str] = None
    unit_cost: Optional[float] = Field(default=None, ge=0)
    bin_location: Optional[str] = None
    reorder_level: Optional[float] = Field(default=None, ge=0)
    quantity_on_hand: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None


class HardwareItemRead(HardwareItemBase):
    id: int
    makerworks_product_template_id: Optional[str] = None


class HardwareMovementBase(SQLModel):
    movement_type: str = Field(description="incoming, outgoing, or adjustment")
    change_units: float = Field(description="Positive for inbound, negative for outbound")
    reference: Optional[str] = Field(default=None, description="PO, job, or ticket reference")
    note: Optional[str] = None


class HardwareMovement(HardwareMovementBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hardware_item_id: int = Field(foreign_key="hardwareitem.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    hardware_item: Optional[HardwareItem] = Relationship(back_populates="movements")


class HardwareMovementCreate(HardwareMovementBase):
    hardware_item_id: int


class HardwareMovementRead(HardwareMovementBase):
    id: int
    hardware_item_id: int
    created_at: datetime


class PrintModelBase(SQLModel):
    name: str = Field(index=True)
    category: Optional[str] = Field(default=None, index=True, description="Model grouping such as toys, props, terrain")
    sku: Optional[str] = Field(default=None, description="Internal SKU or listing ID")
    designer: Optional[str] = Field(default=None, description="Designer or source")
    platform: Optional[str] = Field(default=None, description="Marketplace or store listing")
    file_location: Optional[str] = Field(default=None, description="Path or URL to model file")
    version: Optional[str] = Field(default=None, description="Model version or revision")
    unit_price: float = Field(default=0, ge=0, description="Default sale price per unit")
    quantity_on_hand: float = Field(default=0, ge=0, description="Current number of finished units in stock")
    active: bool = Field(default=True)
    notes: Optional[str] = None


class PrintModel(PrintModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    makerworks_product_template_id: Optional[str] = Field(default=None, index=True)
    sales: List["PrintModelSale"] = Relationship(back_populates="model")
    movements: List["PrintModelMovement"] = Relationship(back_populates="model")


class PrintModelCreate(PrintModelBase):
    pass


class PrintModelUpdate(SQLModel):
    name: Optional[str] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    designer: Optional[str] = None
    platform: Optional[str] = None
    file_location: Optional[str] = None
    version: Optional[str] = None
    unit_price: Optional[float] = Field(default=None, ge=0)
    quantity_on_hand: Optional[float] = Field(default=None, ge=0)
    active: Optional[bool] = None
    notes: Optional[str] = None


class PrintModelRead(PrintModelBase):
    id: int
    makerworks_product_template_id: Optional[str] = None
    total_sold: int = 0
    total_revenue: float = 0


class PrintModelSaleBase(SQLModel):
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    currency: str = Field(default="USD")
    channel: Optional[str] = Field(default=None, description="Store/marketplace")
    reference: Optional[str] = Field(default=None, description="Order ID or invoice")
    note: Optional[str] = None


class PrintModelSale(PrintModelSaleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: int = Field(foreign_key="printmodel.id", index=True)
    sold_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    model: Optional[PrintModel] = Relationship(back_populates="sales")


class PrintModelSaleCreate(PrintModelSaleBase):
    model_id: int


class PrintModelSaleRead(PrintModelSaleBase):
    id: int
    model_id: int
    sold_at: datetime


class PrintModelMovementBase(SQLModel):
    movement_type: str = Field(description="incoming, outgoing, adjustment, or sale")
    change_units: float = Field(description="Positive for inbound, negative for outbound")
    reference: Optional[str] = Field(default=None, description="PO, job, or order reference")
    note: Optional[str] = None


class PrintModelMovement(PrintModelMovementBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: int = Field(foreign_key="printmodel.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    model: Optional[PrintModel] = Relationship(back_populates="movements")


class PrintModelMovementCreate(PrintModelMovementBase):
    model_id: int


class PrintModelMovementRead(PrintModelMovementBase):
    id: int
    model_id: int
    created_at: datetime


class PaginatedMaterialsRead(SQLModel):
    items: List[MaterialRead]
    total: int
    limit: int
    offset: int


class PaginatedInventoryRead(SQLModel):
    items: List[InventoryItemRead]
    total: int
    limit: int
    offset: int


class PaginatedHardwareRead(SQLModel):
    items: List[HardwareItemRead]
    total: int
    limit: int
    offset: int


class PaginatedModelsRead(SQLModel):
    items: List[PrintModelRead]
    total: int
    limit: int
    offset: int
