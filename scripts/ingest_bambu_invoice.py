"""Parse and optionally ingest Bambu Lab invoice PDFs into StockWorks."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

from pypdf import PdfReader
from sqlmodel import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import session_scope
from app.models import InventoryItem, Material, MaterialCostHistory, StockMovement
from app.normalization import normalize_sku

BRAND_NAME = "Bambu Lab"
DEFAULT_SUPPLIER = "Bambu Lab CA"


@dataclass
class BambuInvoiceLine:
    product_name: str
    filament_type: str
    category: Optional[str]
    color: str
    sku: str
    variant_code: Optional[str]
    package_type: str
    weight_grams: int
    quantity: int
    unit_price_excl_tax: float
    product_discount: float
    tax_name: str
    tax_amount: float
    items_subtotal: float
    unit_cost_per_gram: float
    total_grams: int


@dataclass
class BambuInvoice:
    invoice_number: str
    order_number: str
    invoice_date: str
    delivery_date: Optional[str]
    payment_date: Optional[str]
    supplier: str
    grand_total: Optional[float]
    lines: list[BambuInvoiceLine]


PRICE_LINE_PATTERN = re.compile(
    r"(?P<qty>\d+)\s+\$(?P<price>\d+\.\d{2})\s+\$(?P<discount>\d+\.\d{2})\s+"
    r"(?P<tax>[A-Z]+(?:\(\d+%\))?)\s+\$(?P<tax_amount>\d+\.\d{2})\s+\$(?P<subtotal>\d+\.\d{2})"
)


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def parse_invoice_text(text: str) -> BambuInvoice:
    invoice_number = _extract_required(text, r"Invoice Number:\s*([A-Z0-9]+)")
    order_number = _extract_required(text, r"Order Number:\s*([A-Za-z0-9]+)")
    invoice_date = _extract_required(text, r"Invoice Date:\s*([0-9-]+)")
    delivery_date = _extract_optional(text, r"Delivery Date:\s*([0-9-]+)")
    payment_date = _extract_optional(text, r"Payment Date:\s*([0-9-]+)")
    grand_total_raw = _extract_optional(text, r"Grand total\s+\$([0-9]+\.[0-9]{2})")
    lines = parse_invoice_lines(text)
    if not lines:
        raise ValueError("No Bambu invoice line items were detected in the PDF text.")
    return BambuInvoice(
        invoice_number=invoice_number,
        order_number=order_number,
        invoice_date=invoice_date,
        delivery_date=delivery_date,
        payment_date=payment_date,
        supplier=_extract_optional(text, r"(Bambu Lab CA)") or DEFAULT_SUPPLIER,
        grand_total=float(grand_total_raw) if grand_total_raw else None,
        lines=lines,
    )


def parse_invoice_lines(text: str) -> list[BambuInvoiceLine]:
    raw_lines = [_clean_spaces(line) for line in text.splitlines()]
    lines: list[BambuInvoiceLine] = []
    idx = 0
    while idx < len(raw_lines):
        line = raw_lines[idx]
        if not line or line.startswith("Items Qty") or line == "INVOICE":
            idx += 1
            continue
        if not _looks_like_product_line(line):
            idx += 1
            continue

        product_name = line
        idx += 1
        sku_parts: list[str] = []
        while idx < len(raw_lines) and raw_lines[idx].startswith("SKU:"):
            sku_parts.append(raw_lines[idx][4:].strip())
            idx += 1
        while idx < len(raw_lines) and raw_lines[idx] and not raw_lines[idx].startswith("Variant:"):
            sku_parts.append(raw_lines[idx])
            idx += 1
        if idx >= len(raw_lines) or not raw_lines[idx].startswith("Variant:"):
            continue

        variant_parts = [raw_lines[idx][8:].strip()]
        idx += 1
        while idx < len(raw_lines):
            current = raw_lines[idx]
            if not current:
                idx += 1
                continue
            if PRICE_LINE_PATTERN.fullmatch(current):
                break
            if current == "INVOICE":
                break
            variant_parts.append(current)
            idx += 1
        if idx >= len(raw_lines):
            break
        price_match = PRICE_LINE_PATTERN.fullmatch(raw_lines[idx])
        if not price_match:
            continue

        sku = normalize_sku("".join(sku_parts)) or _clean_spaces(" ".join(sku_parts))
        variant = _clean_spaces(" ".join(variant_parts))
        qty = int(price_match.group("qty"))
        price = float(price_match.group("price"))
        discount = float(price_match.group("discount"))
        tax_name = _clean_spaces(price_match.group("tax"))
        tax_amount = float(price_match.group("tax_amount"))
        subtotal = float(price_match.group("subtotal"))
        filament_type, category = _split_product_name(product_name)
        color, variant_code, package_type, weight_grams = _parse_variant(variant)
        total_grams = weight_grams * qty
        unit_cost_per_gram = round(subtotal / total_grams, 6)
        lines.append(
            BambuInvoiceLine(
                product_name=product_name,
                filament_type=filament_type,
                category=category,
                color=color,
                sku=sku,
                variant_code=variant_code,
                package_type=package_type,
                weight_grams=weight_grams,
                quantity=qty,
                unit_price_excl_tax=price,
                product_discount=discount,
                tax_name=tax_name,
                tax_amount=tax_amount,
                items_subtotal=subtotal,
                unit_cost_per_gram=unit_cost_per_gram,
                total_grams=total_grams,
            )
        )
        idx += 1
    return lines


def ingest_invoice(invoice: BambuInvoice, *, location: str, reorder_level: float, dry_run: bool) -> dict:
    summary = {
        "invoice_number": invoice.invoice_number,
        "order_number": invoice.order_number,
        "invoice_date": invoice.invoice_date,
        "location": location,
        "dry_run": dry_run,
        "materials_created": 0,
        "materials_updated": 0,
        "inventory_items_created": 0,
        "cost_history_created": 0,
        "movements_created": 0,
        "lines": [],
    }
    with session_scope() as session:
        for line in invoice.lines:
            material, created = _get_or_create_material(session, invoice, line, dry_run=dry_run)
            if created:
                summary["materials_created"] += 1
            else:
                summary["materials_updated"] += 1
            inventory_item, inventory_created = _get_or_create_inventory_item(
                session,
                material=material,
                location=location,
                reorder_level=reorder_level,
                dry_run=dry_run,
            )
            if inventory_created:
                summary["inventory_items_created"] += 1
            if _ensure_cost_history(session, material=material, invoice=invoice, line=line, dry_run=dry_run):
                summary["cost_history_created"] += 1
            if _ensure_stock_movement(session, inventory_item=inventory_item, invoice=invoice, line=line, dry_run=dry_run):
                summary["movements_created"] += 1
            summary["lines"].append(
                {
                    "sku": line.sku,
                    "color": line.color,
                    "package_type": line.package_type,
                    "quantity": line.quantity,
                    "grams_added": line.total_grams,
                    "unit_cost_per_gram": line.unit_cost_per_gram,
                    "material_id": material.id,
                    "inventory_item_id": inventory_item.id,
                    "created_material": created,
                    "created_inventory_item": inventory_created,
                }
            )
        if dry_run:
            session.rollback()
    return summary


def _get_or_create_material(session, invoice: BambuInvoice, line: BambuInvoiceLine, *, dry_run: bool) -> tuple[Material, bool]:
    material = _find_existing_material(session, line)
    created = material is None
    if material is None:
        material = Material(
            name=line.sku,
            brand=BRAND_NAME,
            filament_type=line.filament_type,
            category=line.category,
            color=line.color,
            supplier=invoice.supplier or DEFAULT_SUPPLIER,
            price_per_gram=line.unit_cost_per_gram,
            spool_weight_grams=line.weight_grams,
            notes=f"Imported from Bambu invoice {invoice.invoice_number}",
        )
        if line.package_type.lower() == "refill":
            material.refill_barcode = line.sku
        else:
            material.barcode = line.sku
        session.add(material)
        session.flush()
        return material, True

    changed = False
    if material.brand != BRAND_NAME:
        material.brand = BRAND_NAME
        changed = True
    if material.supplier != invoice.supplier:
        material.supplier = invoice.supplier
        changed = True
    if material.filament_type != line.filament_type:
        material.filament_type = line.filament_type
        changed = True
    if material.category != line.category:
        material.category = line.category
        changed = True
    if material.color != line.color:
        material.color = line.color
        changed = True
    if material.spool_weight_grams != line.weight_grams:
        material.spool_weight_grams = line.weight_grams
        changed = True
    if material.price_per_gram != line.unit_cost_per_gram:
        material.price_per_gram = line.unit_cost_per_gram
        changed = True
    if line.package_type.lower() == "refill":
        if material.refill_barcode != line.sku:
            material.refill_barcode = line.sku
            changed = True
    else:
        if material.barcode != line.sku:
            material.barcode = line.sku
            changed = True
    if changed and not dry_run:
        session.add(material)
        session.flush()
    return material, False


def _find_existing_material(session, line: BambuInvoiceLine) -> Optional[Material]:
    sku_statement = select(Material).where((Material.barcode == line.sku) | (Material.refill_barcode == line.sku))
    material = session.exec(sku_statement).first()
    if material:
        return material
    statement = select(Material).where(
        Material.brand == BRAND_NAME,
        Material.filament_type == line.filament_type,
        Material.category == line.category,
        Material.color == line.color,
    )
    return session.exec(statement).first()


def _get_or_create_inventory_item(session, *, material: Material, location: str, reorder_level: float, dry_run: bool) -> tuple[InventoryItem, bool]:
    statement = select(InventoryItem).where(InventoryItem.material_id == material.id, InventoryItem.location == location)
    item = session.exec(statement).first()
    if item:
        return item, False
    item = InventoryItem(
        material_id=material.id,
        location=location,
        quantity_grams=0,
        reorder_level=reorder_level,
        spool_serial=None,
        unit_cost_override=None,
    )
    session.add(item)
    session.flush()
    return item, True


def _ensure_cost_history(session, *, material: Material, invoice: BambuInvoice, line: BambuInvoiceLine, dry_run: bool) -> bool:
    note = _cost_history_note(invoice, line)
    statement = select(MaterialCostHistory).where(
        MaterialCostHistory.material_id == material.id,
        MaterialCostHistory.reference == invoice.invoice_number,
        MaterialCostHistory.note == note,
    )
    if session.exec(statement).first():
        return False
    entry = MaterialCostHistory(
        material_id=material.id,
        unit_cost_per_gram=line.unit_cost_per_gram,
        vendor=invoice.supplier,
        reference=invoice.invoice_number,
        note=note,
    )
    session.add(entry)
    if not dry_run:
        session.flush()
    return True


def _ensure_stock_movement(session, *, inventory_item: InventoryItem, invoice: BambuInvoice, line: BambuInvoiceLine, dry_run: bool) -> bool:
    note = _movement_note(invoice, line)
    statement = select(StockMovement).where(
        StockMovement.inventory_item_id == inventory_item.id,
        StockMovement.movement_type == "incoming",
        StockMovement.change_grams == line.total_grams,
        StockMovement.reference == invoice.invoice_number,
        StockMovement.note == note,
    )
    if session.exec(statement).first():
        return False
    movement = StockMovement(
        inventory_item_id=inventory_item.id,
        movement_type="incoming",
        change_grams=line.total_grams,
        reference=invoice.invoice_number,
        note=note,
    )
    session.add(movement)
    inventory_item.quantity_grams += line.total_grams
    session.add(inventory_item)
    if not dry_run:
        session.flush()
    return True


def _split_product_name(product_name: str) -> tuple[str, Optional[str]]:
    parts = product_name.split(" ", 1)
    filament_type = parts[0].strip().upper()
    category = parts[1].strip() if len(parts) > 1 else None
    return filament_type, category


def _looks_like_product_line(value: str) -> bool:
    upper = value.upper()
    return bool(value) and not upper.startswith(("SKU:", "VARIANT:", "INVOICE", "ORDER NUMBER:", "INVOICE NUMBER:"))


def _parse_variant(variant: str) -> tuple[str, Optional[str], str, int]:
    parts = [part.strip() for part in variant.split("/") if part.strip()]
    if len(parts) < 3:
        raise ValueError(f"Unexpected Bambu variant format: {variant!r}")
    color_part = parts[0]
    package_type = parts[1]
    weight_part = parts[2]
    code_match = re.search(r"\((\d+)\)", color_part)
    variant_code = code_match.group(1) if code_match else None
    color = re.sub(r"\s*\(\d+\)\s*", "", color_part).strip()
    weight_grams = _parse_weight_grams(weight_part)
    return color, variant_code, package_type, weight_grams


def _parse_weight_grams(value: str) -> int:
    normalized = value.strip().lower()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*kg", normalized)
    if not match:
        raise ValueError(f"Unsupported Bambu invoice weight value: {value!r}")
    return int(round(float(match.group(1)) * 1000))


def _extract_required(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Unable to find required invoice field for pattern: {pattern}")
    return match.group(1).strip()


def _extract_optional(text: str, pattern: str) -> Optional[str]:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def _clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _cost_history_note(invoice: BambuInvoice, line: BambuInvoiceLine) -> str:
    return f"Bambu import {line.package_type.lower()} {line.sku} order {invoice.order_number}"


def _movement_note(invoice: BambuInvoice, line: BambuInvoiceLine) -> str:
    return f"Bambu invoice {invoice.order_number}: {line.quantity} x {line.product_name} {line.color} ({line.package_type})"


def _serialize_invoice(invoice: BambuInvoice) -> dict:
    data = asdict(invoice)
    data["lines"] = [asdict(line) for line in invoice.lines]
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse and optionally ingest a Bambu Lab invoice PDF into StockWorks.")
    parser.add_argument("pdf", help="Path to the Bambu invoice PDF")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write parsed materials, cost history, and incoming stock movements into the database.",
    )
    parser.add_argument(
        "--location",
        default="Receiving",
        help="Inventory location to receive the imported stock into when using --apply.",
    )
    parser.add_argument(
        "--reorder-level",
        type=float,
        default=0,
        help="Reorder level to use for new inventory items created by the import.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the parsed invoice and ingestion summary as JSON.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.exists():
        raise SystemExit(f"Invoice PDF not found: {pdf_path}")
    text = extract_pdf_text(pdf_path)
    invoice = parse_invoice_text(text)
    summary = ingest_invoice(
        invoice,
        location=args.location.strip() or "Receiving",
        reorder_level=max(args.reorder_level, 0),
        dry_run=not args.apply,
    )
    payload = {
        "invoice": _serialize_invoice(invoice),
        "summary": summary,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return
    print(f"Invoice {invoice.invoice_number} for order {invoice.order_number} ({invoice.invoice_date})")
    for line in invoice.lines:
        print(
            f"- {line.quantity} x {line.product_name} | {line.color} | {line.package_type} | "
            f"{line.sku} | {line.total_grams}g | ${line.items_subtotal:.2f} pretax"
        )
    print(
        f"Dry run: {summary['dry_run']} | materials created: {summary['materials_created']} | "
        f"materials updated: {summary['materials_updated']} | inventory items created: {summary['inventory_items_created']} | "
        f"cost history created: {summary['cost_history_created']} | movements created: {summary['movements_created']}"
    )


if __name__ == "__main__":
    main()
