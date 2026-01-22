"""Barcode helpers for StockWorks."""
from __future__ import annotations

import os
import secrets
from io import BytesIO

from barcode import Code128
from barcode.writer import ImageWriter
from sqlmodel import Session, select

from .models import Material

BARCODE_PREFIX = os.environ.get("STOCKWORKS_BARCODE_PREFIX", "SWM")
BARCODE_DIGITS = int(os.environ.get("STOCKWORKS_BARCODE_DIGITS", "8"))


def generate_material_barcode(session: Session) -> str:
    """Generate a unique barcode value for a material."""
    prefix = BARCODE_PREFIX.strip().upper()
    digits = max(4, BARCODE_DIGITS)
    while True:
        suffix = "".join(secrets.choice("0123456789") for _ in range(digits))
        candidate = f"{prefix}{suffix}"
        exists = session.exec(select(Material).where(Material.barcode == candidate)).first()
        if not exists:
            return candidate


def render_barcode_png(value: str) -> bytes:
    """Render a Code128 barcode PNG for the given value."""
    barcode = Code128(value, writer=ImageWriter())
    buffer = BytesIO()
    barcode.write(
        buffer,
        options={
            "module_width": 0.2,
            "module_height": 15,
            "font_size": 10,
            "text_distance": 2,
            "quiet_zone": 2,
        },
    )
    return buffer.getvalue()
