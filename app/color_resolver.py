"""Color normalization and brand-specific color helpers."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, Optional

from .db import _resolve_data_dir

_HEX_RE = re.compile(r"^[0-9a-fA-F]{6}$")
_BAMBU_BRANDS = {"bambu lab", "bambulab", "bambu"}

_COLOR_MAP_PATH = Path(
    os.environ.get("BAMBU_COLOR_MAP_PATH", str(_resolve_data_dir() / "bambu-colors.json"))
).resolve()
_COLOR_CACHE: Optional[Dict[str, Dict[str, str]]] = None
_COLOR_CACHE_MTIME: Optional[float] = None


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


def is_bambu_brand(brand: Optional[str]) -> bool:
    if not brand:
        return False
    return brand.strip().lower() in _BAMBU_BRANDS


def resolve_material_color_hex(
    brand: Optional[str],
    color_name: Optional[str],
    color_hex: Optional[str],
) -> Optional[str]:
    normalized_hex = normalize_hex(color_hex) or normalize_hex(color_name)
    if not is_bambu_brand(brand):
        return normalized_hex

    mapping = load_bambu_color_map()
    if mapping:
        if color_name:
            key = color_name.strip().lower()
            mapped = mapping["by_name"].get(key)
            if mapped:
                return mapped
        if normalized_hex:
            mapped = mapping["by_bambu_hex"].get(normalized_hex)
            if mapped:
                return mapped
    return normalized_hex


def load_bambu_color_map() -> Optional[Dict[str, Dict[str, str]]]:
    global _COLOR_CACHE, _COLOR_CACHE_MTIME
    if not _COLOR_MAP_PATH.exists():
        return None
    mtime = _COLOR_MAP_PATH.stat().st_mtime
    if _COLOR_CACHE is not None and _COLOR_CACHE_MTIME == mtime:
        return _COLOR_CACHE

    try:
        data = json.loads(_COLOR_MAP_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    items = _extract_color_items(data)
    by_name: Dict[str, str] = {}
    by_bambu_hex: Dict[str, str] = {}
    for entry in items:
        if not isinstance(entry, dict):
            continue
        name = _pick_first(entry, ["name", "color", "label", "title", "color_name"])
        real_hex = normalize_hex(_pick_first(entry, ["real_hex", "hex", "color_hex", "realHex", "colorHex"]))
        bambu_hex = normalize_hex(_pick_first(entry, ["bambu_hex", "bambuHex", "bambu_color", "bambuColor"]))
        if name and real_hex:
            by_name[name.strip().lower()] = real_hex
        if bambu_hex and real_hex:
            by_bambu_hex[bambu_hex] = real_hex

    _COLOR_CACHE = {"by_name": by_name, "by_bambu_hex": by_bambu_hex}
    _COLOR_CACHE_MTIME = mtime
    return _COLOR_CACHE


def _extract_color_items(data: object) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("colors", "items", "filaments", "data"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return candidate
    return []


def _pick_first(entry: dict, keys: list[str]) -> Optional[str]:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None
