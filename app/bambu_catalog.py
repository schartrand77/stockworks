"""Built-in Bambu Lab material catalog entries."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BambuMaterialColor:
    color: str
    hex_code: str


BAMBU_PETG_HF_COLORS = [
    BambuMaterialColor("Yellow", "#FFD00B"),
    BambuMaterialColor("Orange", "#F75403"),
    BambuMaterialColor("Green", "#00AE42"),
    BambuMaterialColor("Red", "#EB3A3A"),
    BambuMaterialColor("Blue", "#002E96"),
    BambuMaterialColor("Black", "#000000"),
    BambuMaterialColor("White", "#FFFFFF"),
    BambuMaterialColor("Cream", "#F9DFB9"),
    BambuMaterialColor("Lime Green", "#6EE53C"),
    BambuMaterialColor("Forest Green", "#39541A"),
    BambuMaterialColor("Lake Blue", "#1F79E5"),
    BambuMaterialColor("Peanut Brown", "#875718"),
    BambuMaterialColor("Gray", "#ADB1B2"),
    BambuMaterialColor("Dark Gray", "#515151"),
]


BAMBU_PETG_HF_FILAMENT_TYPE = "PETG HF"
BAMBU_PETG_HF_CATEGORY = "HF"
BAMBU_PETG_HF_SUPPLIER = "Bambu Lab"
BAMBU_PETG_HF_SPOOL_WEIGHT_GRAMS = 1000
BAMBU_PETG_HF_PRICE_PER_GRAM = 19.99 / BAMBU_PETG_HF_SPOOL_WEIGHT_GRAMS
