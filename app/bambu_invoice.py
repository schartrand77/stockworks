"""Helpers for parsing Bambu invoice PDFs and storing uploaded documents."""
from __future__ import annotations

import os
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

from .normalization import normalize_sku

DEFAULT_SUPPLIER = "Bambu Lab CA"
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
PDF_MAGIC_BYTES = b"%PDF-"


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


def parse_invoice_pdf(pdf_path: Path) -> BambuInvoice:
    return parse_invoice_text(extract_pdf_text(pdf_path))


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


def resolve_upload_dir(project_root: Path) -> Path:
    configured_dir = os.environ.get("STOCKWORKS_DATA_DIR")
    if configured_dir:
        base_dir = Path(configured_dir)
        if not base_dir.is_absolute():
            base_dir = project_root / base_dir
    else:
        base_dir = project_root / "data"
    return base_dir / "inbound_invoices"


def _resolve_max_upload_bytes() -> int:
    raw_value = (os.environ.get("STOCKWORKS_MAX_UPLOAD_BYTES") or "").strip()
    if not raw_value:
        return DEFAULT_MAX_UPLOAD_BYTES
    try:
        max_bytes = int(raw_value)
    except ValueError as exc:
        raise ValueError("STOCKWORKS_MAX_UPLOAD_BYTES must be an integer.") from exc
    if max_bytes < 1024:
        raise ValueError("STOCKWORKS_MAX_UPLOAD_BYTES must be at least 1024 bytes.")
    return max_bytes


def _validate_pdf_upload(upload, max_bytes: int) -> None:
    upload.file.seek(0)
    header = upload.file.read(len(PDF_MAGIC_BYTES))
    if header != PDF_MAGIC_BYTES:
        raise ValueError("Uploaded file is not a valid PDF.")

    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    if size <= 0:
        raise ValueError("Uploaded PDF is empty.")
    if size > max_bytes:
        raise ValueError(f"Uploaded PDF exceeds the {max_bytes} byte size limit.")
    upload.file.seek(0)


def store_upload(upload, destination_dir: Path, prefix: str, max_bytes: int | None = None) -> tuple[str, str]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    original_name = Path(getattr(upload, "filename", "") or f"{prefix}.pdf").name
    suffix = Path(original_name).suffix or ".pdf"
    if suffix.lower() != ".pdf":
        raise ValueError("Uploaded file must use a .pdf extension.")
    _validate_pdf_upload(upload, max_bytes or _resolve_max_upload_bytes())
    stored_name = f"{prefix}-{uuid.uuid4().hex}{suffix}"
    target = destination_dir / stored_name
    with target.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)
    upload.file.seek(0)
    return original_name, str(target)


def _split_product_name(product_name: str) -> tuple[str, Optional[str]]:
    parts = product_name.split(" ", 1)
    filament_type = parts[0].strip().upper()
    category = parts[1].strip() if len(parts) > 1 else None
    return filament_type, category


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


def _looks_like_product_line(value: str) -> bool:
    upper = value.upper()
    return bool(value) and not upper.startswith(("SKU:", "VARIANT:", "INVOICE", "ORDER NUMBER:", "INVOICE NUMBER:"))
