"""Barcode helpers for StockWorks."""
from __future__ import annotations

from io import BytesIO

from barcode import Code128
from barcode.writer import ImageWriter


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
