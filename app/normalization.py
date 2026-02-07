"""Normalization helpers for SKU and barcode values."""
from __future__ import annotations

import re
from typing import Optional

_BARCODE_STRIP_RE = re.compile(r"[\s\-]+")
_SKU_INVALID_RE = re.compile(r"[^A-Z0-9._-]+")
_SKU_DASH_RE = re.compile(r"-{2,}")


def normalize_barcode(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    normalized = _BARCODE_STRIP_RE.sub("", raw).upper()
    return normalized or None


def normalize_sku(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw = re.sub(r"\s+", "-", raw)
    raw = raw.upper()
    raw = _SKU_INVALID_RE.sub("", raw)
    raw = _SKU_DASH_RE.sub("-", raw).strip("-")
    return raw or None
