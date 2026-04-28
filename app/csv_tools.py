"""CSV import/export helpers for StockWorks catalog records."""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from typing import Any


MATERIAL_COLUMNS = [
    "name",
    "brand",
    "filament_type",
    "category",
    "color",
    "color_hex",
    "color_hexes",
    "supplier",
    "price_per_gram",
    "spool_weight_grams",
    "barcode",
    "refill_barcode",
    "notes",
]
HARDWARE_COLUMNS = [
    "name",
    "category",
    "merch_color",
    "merch_size",
    "merch_style",
    "merch_sku",
    "supplier",
    "manufacturer_part_number",
    "unit_of_measure",
    "unit_cost",
    "bin_location",
    "reorder_level",
    "quantity_on_hand",
    "notes",
]


@dataclass
class CsvParseResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)


def _decode_csv(content: bytes) -> str:
    return content.decode("utf-8-sig")


def _parse_float(value: str, field_name: str, row_number: int, errors: list[dict[str, Any]]) -> float | None:
    try:
        return float((value or "0").strip() or "0")
    except ValueError:
        errors.append({"row": row_number, "field": field_name, "error": "Must be a number."})
        return None


def _parse_int(value: str, field_name: str, row_number: int, errors: list[dict[str, Any]]) -> int | None:
    parsed = _parse_float(value, field_name, row_number, errors)
    return int(parsed) if parsed is not None else None


def parse_material_csv(content: bytes) -> CsvParseResult:
    return _parse_csv(
        content,
        MATERIAL_COLUMNS,
        {"name", "filament_type", "color"},
        {"price_per_gram": "float", "spool_weight_grams": "int"},
    )


def parse_hardware_csv(content: bytes) -> CsvParseResult:
    return _parse_csv(
        content,
        HARDWARE_COLUMNS,
        {"name"},
        {"unit_cost": "float", "reorder_level": "float", "quantity_on_hand": "float"},
    )


def _parse_csv(
    content: bytes,
    columns: list[str],
    required: set[str],
    numeric: dict[str, str],
) -> CsvParseResult:
    result = CsvParseResult()
    try:
        text = _decode_csv(content)
    except UnicodeDecodeError:
        result.errors.append({"row": 0, "field": "file", "error": "CSV must be UTF-8."})
        return result
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        result.errors.append({"row": 0, "field": "header", "error": "CSV header row is required."})
        return result
    missing = [column for column in required if column not in reader.fieldnames]
    if missing:
        result.errors.append(
            {"row": 0, "field": "header", "error": f"Missing required columns: {', '.join(sorted(missing))}."}
        )
        return result
    for row_number, row in enumerate(reader, start=2):
        row_errors: list[dict[str, Any]] = []
        parsed = {column: (row.get(column) or "").strip() for column in columns}
        for column in required:
            if not parsed.get(column):
                row_errors.append({"row": row_number, "field": column, "error": "Required field is missing."})
        for column, kind in numeric.items():
            if kind == "int":
                parsed_value = _parse_int(parsed.get(column, ""), column, row_number, row_errors)
            else:
                parsed_value = _parse_float(parsed.get(column, ""), column, row_number, row_errors)
            if parsed_value is not None:
                parsed[column] = parsed_value
        if "color_hexes" in parsed and parsed["color_hexes"]:
            try:
                parsed["color_hexes"] = json.loads(parsed["color_hexes"])
            except json.JSONDecodeError:
                parsed["color_hexes"] = [part.strip() for part in str(parsed["color_hexes"]).split("|") if part.strip()]
        if row_errors:
            result.errors.extend(row_errors)
        else:
            result.rows.append(parsed)
    return result


def export_material_rows(materials: list[Any]) -> str:
    return _export_rows(MATERIAL_COLUMNS, materials)


def export_hardware_rows(items: list[Any]) -> str:
    return _export_rows(HARDWARE_COLUMNS, items)


def _export_rows(columns: list[str], items: list[Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for item in items:
        row = {}
        for column in columns:
            value = getattr(item, column, "")
            if isinstance(value, list):
                value = json.dumps(value)
            row[column] = "" if value is None else value
        writer.writerow(row)
    return output.getvalue()
