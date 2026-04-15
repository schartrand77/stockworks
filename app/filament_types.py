"""Filament type catalogs for supported printers."""

BAMBU_X1C_FILAMENT_TYPES = [
    "ABS",
    "ASA",
    "PC",
    "PC FR",
    "PLA Aero",
    "PLA Basic",
    "PLA Glow",
    "PLA Marble",
    "PLA Matte",
    "PLA Metal",
    "PLA Silk",
    "PLA Sparkle",
    "PLA Tough",
    "PLA Transparent",
    "PLA-CF",
    "PETG Basic",
    "PETG HF",
    "PETG Translucent",
    "PETG-CF",
    "PA-CF",
    "PA6-CF",
    "PA6-GF",
    "PAHT-CF",
    "PVA",
    "Support for PA/PET",
    "Support for PLA",
    "Support G",
    "Support W",
    "TPU 95A",
    "TPU 95A HF",
]


def bambu_x1c_filament_types() -> list[str]:
    """Return a copy of the supported Bambu X1C filament types list."""
    return list(BAMBU_X1C_FILAMENT_TYPES)
