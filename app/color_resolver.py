"""Color normalization helpers."""
from __future__ import annotations

import re
from typing import Optional

_HEX_RE = re.compile(r"^[0-9a-fA-F]{6}$")


def normalize_hex(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip()
    if normalized.lower().startswith("0x"):
        normalized = normalized[2:]
    if normalized.startswith("#"):
        normalized = normalized[1:]
    if len(normalized) == 3:
        normalized = "".join(char * 2 for char in normalized)
    if not _HEX_RE.fullmatch(normalized):
        return None
    return f"#{normalized.upper()}"


def resolve_material_color_hex(
    brand: Optional[str],
    color_name: Optional[str],
    color_hex: Optional[str],
) -> Optional[str]:
    return normalize_hex(color_hex)
