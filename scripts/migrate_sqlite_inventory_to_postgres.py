#!/usr/bin/env python3
"""Copy StockWorks inventory data from SQLite into the configured Postgres schema."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import psycopg2
from psycopg2.extras import execute_values


@dataclass
class PostgresConfig:
    dsn: str
    schema: Optional[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate StockWorks material/inventory/stock movement records from SQLite to Postgres."
    )
    parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Path to the source SQLite database. Defaults to $STOCKWORKS_DATA_DIR/$STOCKWORKS_DB_FILENAME.",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="Target Postgres URL. Defaults to $DATABASE_URL.",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Delete existing Postgres StockWorks data before importing.",
    )
    return parser.parse_args()


def resolve_sqlite_path(explicit_path: Optional[str]) -> str:
    if explicit_path:
        return explicit_path
    data_dir = os.environ.get("STOCKWORKS_DATA_DIR", "/data")
    filename = os.environ.get("STOCKWORKS_DB_FILENAME", "app.db")
    return os.path.join(data_dir, filename)


def strip_schema_parameter(database_url: str) -> PostgresConfig:
    parsed = urlparse(database_url)
    schema = None
    filtered_query: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key == "schema" and schema is None:
            schema = value
        else:
            filtered_query.append((key, value))
    dsn = urlunparse(parsed._replace(query=urlencode(filtered_query, doseq=True)))
    return PostgresConfig(dsn=dsn, schema=(schema or None))


def fetch_rows(conn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    return conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()


def sqlite_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def ensure_postgres_ready(pg_conn, schema: str) -> None:
    with pg_conn.cursor() as cur:
        cur.execute(f'SET search_path TO "{schema}"')


def read_target_counts(pg_conn) -> dict[str, int]:
    counts: dict[str, int] = {}
    with pg_conn.cursor() as cur:
        for table in ("material", "materialcosthistory", "inventoryitem", "stockmovement"):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = int(cur.fetchone()[0])
    return counts


def truncate_target(pg_conn) -> None:
    with pg_conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE stockmovement, inventoryitem, materialcosthistory, material RESTART IDENTITY CASCADE")


def insert_materials(pg_conn, rows: Iterable[sqlite3.Row]) -> int:
    payload = [
        (
            row["id"],
            row["name"],
            row["brand"],
            row["filament_type"],
            row["category"],
            row["color"],
            None,
            row["supplier"],
            row["price_per_gram"],
            row["spool_weight_grams"],
            row["barcode"],
            None,
            row["notes"],
            None,
        )
        for row in rows
    ]
    if not payload:
        return 0
    with pg_conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO material (
                id, name, brand, filament_type, category, color, color_hex, supplier,
                price_per_gram, spool_weight_grams, barcode, refill_barcode, notes, color_hexes
            ) VALUES %s
            ON CONFLICT (id) DO NOTHING
            """,
            payload,
        )
    return len(payload)


def insert_material_history(pg_conn, material_rows: Iterable[sqlite3.Row], has_legacy_history: bool) -> int:
    payload = []
    for row in material_rows:
        if has_legacy_history:
            payload.append(
                (
                    row["material_id"],
                    row["unit_cost_per_gram"],
                    row["vendor"],
                    row["reference"],
                    row["note"],
                    row["recorded_at"],
                )
            )
        else:
            payload.append(
                (
                    row["id"],
                    row["price_per_gram"],
                    row["supplier"],
                    "sqlite_migration",
                    "Backfilled from legacy SQLite material data",
                    "2026-03-01 00:00:00",
                )
            )
    if not payload:
        return 0
    with pg_conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO materialcosthistory (
                material_id, unit_cost_per_gram, vendor, reference, note, recorded_at
            ) VALUES %s
            """,
            payload,
        )
    return len(payload)


def insert_inventory(pg_conn, rows: Iterable[sqlite3.Row]) -> int:
    payload = [
        (
            row["id"],
            row["location"],
            row["quantity_grams"],
            row["reorder_level"],
            row["spool_serial"],
            row["unit_cost_override"],
            row["material_id"],
        )
        for row in rows
    ]
    if not payload:
        return 0
    with pg_conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO inventoryitem (
                id, location, quantity_grams, reorder_level, spool_serial, unit_cost_override, material_id
            ) VALUES %s
            ON CONFLICT (id) DO NOTHING
            """,
            payload,
        )
    return len(payload)


def insert_movements(pg_conn, rows: Iterable[sqlite3.Row]) -> int:
    payload = [
        (
            row["id"],
            row["movement_type"],
            row["change_grams"],
            row["reference"],
            row["note"],
            row["inventory_item_id"],
            row["created_at"],
        )
        for row in rows
    ]
    if not payload:
        return 0
    with pg_conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO stockmovement (
                id, movement_type, change_grams, reference, note, inventory_item_id, created_at
            ) VALUES %s
            ON CONFLICT (id) DO NOTHING
            """,
            payload,
        )
    return len(payload)


def reset_sequences(pg_conn) -> None:
    with pg_conn.cursor() as cur:
        cur.execute("SELECT setval(pg_get_serial_sequence('material', 'id'), COALESCE((SELECT MAX(id) FROM material), 1), true)")
        cur.execute(
            "SELECT setval(pg_get_serial_sequence('materialcosthistory', 'id'), COALESCE((SELECT MAX(id) FROM materialcosthistory), 1), true)"
        )
        cur.execute(
            "SELECT setval(pg_get_serial_sequence('inventoryitem', 'id'), COALESCE((SELECT MAX(id) FROM inventoryitem), 1), true)"
        )
        cur.execute(
            "SELECT setval(pg_get_serial_sequence('stockmovement', 'id'), COALESCE((SELECT MAX(id) FROM stockmovement), 1), true)"
        )


def main() -> int:
    args = parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL must be provided via --database-url or environment.")

    sqlite_path = resolve_sqlite_path(args.sqlite_path)
    pg_config = strip_schema_parameter(args.database_url)
    schema = (pg_config.schema or "public").strip() or "public"

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    if not sqlite_table_exists(sqlite_conn, "material"):
        raise SystemExit(f"SQLite source table missing: material ({sqlite_path})")
    if not sqlite_table_exists(sqlite_conn, "inventoryitem"):
        raise SystemExit(f"SQLite source table missing: inventoryitem ({sqlite_path})")
    if not sqlite_table_exists(sqlite_conn, "stockmovement"):
        raise SystemExit(f"SQLite source table missing: stockmovement ({sqlite_path})")

    material_rows = fetch_rows(sqlite_conn, "material")
    inventory_rows = fetch_rows(sqlite_conn, "inventoryitem")
    movement_rows = fetch_rows(sqlite_conn, "stockmovement")

    legacy_history_rows: list[sqlite3.Row] = []
    has_legacy_history = sqlite_table_exists(sqlite_conn, "materialcosthistory")
    if has_legacy_history:
        legacy_history_rows = fetch_rows(sqlite_conn, "materialcosthistory")

    pg_conn = psycopg2.connect(pg_config.dsn)
    try:
        ensure_postgres_ready(pg_conn, schema)
        before_counts = read_target_counts(pg_conn)
        if args.truncate_target:
            truncate_target(pg_conn)
        else:
            non_empty = {table: count for table, count in before_counts.items() if count}
            if non_empty:
                raise SystemExit(
                    f"Target schema {schema!r} is not empty: {json.dumps(non_empty, sort_keys=True)}. "
                    "Re-run with --truncate-target if replacement is intended."
                )

        inserted_materials = insert_materials(pg_conn, material_rows)
        inserted_history = insert_material_history(
            pg_conn,
            legacy_history_rows if has_legacy_history else material_rows,
            has_legacy_history,
        )
        inserted_inventory = insert_inventory(pg_conn, inventory_rows)
        inserted_movements = insert_movements(pg_conn, movement_rows)
        reset_sequences(pg_conn)
        pg_conn.commit()

        after_counts = read_target_counts(pg_conn)
        print(
            json.dumps(
                {
                    "sqlite_path": sqlite_path,
                    "schema": schema,
                    "inserted": {
                        "material": inserted_materials,
                        "materialcosthistory": inserted_history,
                        "inventoryitem": inserted_inventory,
                        "stockmovement": inserted_movements,
                    },
                    "target_counts": after_counts,
                },
                indent=2,
                sort_keys=True,
            )
        )
    finally:
        pg_conn.close()
        sqlite_conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
