#!/usr/bin/env python3
"""Remove non-filament inventory rows that leaked into StockWorks filament inventory."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from sqlmodel import select

from app.db import session_scope
from app.models import InventoryItem, Material, MaterialCostHistory, StockMovement


DEFAULT_LOCATIONS = ("model", "models", "merch", "hardware")


@dataclass
class CandidateRow:
    inventory_id: int
    material_id: int
    material_name: str
    location: str
    quantity_grams: float
    reorder_level: float
    movement_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Clean up non-filament inventory rows stored in reserved locations like "
            "'models', 'merch', or 'hardware'. Defaults to dry-run."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete matching rows. Without this flag the script only reports what it would delete.",
    )
    parser.add_argument(
        "--delete-orphan-materials",
        action="store_true",
        help=(
            "After deleting matching inventory rows, also delete materials that no longer have any "
            "inventory rows. Related cost history is deleted with those materials."
        ),
    )
    parser.add_argument(
        "--locations",
        nargs="+",
        default=list(DEFAULT_LOCATIONS),
        help="Reserved non-filament inventory locations to target.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_locations = {value.strip().lower() for value in args.locations if value.strip()}
    if not target_locations:
        raise SystemExit("At least one location must be provided.")

    with session_scope() as session:
        inventory_rows = session.exec(
            select(InventoryItem, Material)
            .join(Material, InventoryItem.material_id == Material.id)
            .order_by(InventoryItem.id)
        ).all()

        candidates: list[tuple[InventoryItem, Material, list[StockMovement]]] = []
        for inventory_item, material in inventory_rows:
            location = (inventory_item.location or "").strip().lower()
            if location not in target_locations:
                continue
            movements = session.exec(
                select(StockMovement).where(StockMovement.inventory_item_id == inventory_item.id)
            ).all()
            candidates.append((inventory_item, material, movements))

        preview = [
            CandidateRow(
                inventory_id=int(inventory_item.id or 0),
                material_id=int(material.id or 0),
                material_name=material.name,
                location=inventory_item.location,
                quantity_grams=float(inventory_item.quantity_grams or 0),
                reorder_level=float(inventory_item.reorder_level or 0),
                movement_count=len(movements),
            )
            for inventory_item, material, movements in candidates
        ]

        if not args.apply:
            print(
                json.dumps(
                    {
                        "mode": "dry-run",
                        "target_locations": sorted(target_locations),
                        "inventory_rows_to_delete": len(preview),
                        "inventory_preview": [asdict(row) for row in preview],
                        "note": (
                            "Re-run with --apply to delete these inventory rows. "
                            "Add --delete-orphan-materials to also remove materials left with no inventory."
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        deleted_movements = 0
        deleted_inventory = 0
        material_ids_to_check = {material.id for _, material, _ in candidates if material.id is not None}

        for inventory_item, _material, movements in candidates:
            for movement in movements:
                session.delete(movement)
                deleted_movements += 1
            session.delete(inventory_item)
            deleted_inventory += 1

        deleted_materials = 0
        deleted_cost_history = 0
        orphan_material_ids: list[int] = []

        if args.delete_orphan_materials:
            for material_id in sorted(material_ids_to_check):
                if material_id is None:
                    continue
                remaining_inventory = session.exec(
                    select(InventoryItem).where(InventoryItem.material_id == material_id)
                ).first()
                if remaining_inventory is not None:
                    continue
                orphan_material_ids.append(int(material_id))
                cost_history_rows = session.exec(
                    select(MaterialCostHistory).where(MaterialCostHistory.material_id == material_id)
                ).all()
                for entry in cost_history_rows:
                    session.delete(entry)
                    deleted_cost_history += 1
                material = session.get(Material, material_id)
                if material is not None:
                    session.delete(material)
                    deleted_materials += 1

        print(
            json.dumps(
                {
                    "mode": "apply",
                    "target_locations": sorted(target_locations),
                    "deleted_inventory_rows": deleted_inventory,
                    "deleted_stock_movements": deleted_movements,
                    "deleted_materials": deleted_materials,
                    "deleted_material_cost_history_rows": deleted_cost_history,
                    "orphan_material_ids_deleted": orphan_material_ids,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
