#!/usr/bin/env python3
"""Copy StockWorks-owned tables from one Postgres schema to another.

Defaults to a dry run from ``orderworks`` to ``public`` because that is the
recovery path for installs that accidentally stored StockWorks data in the
OrderWorks schema.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

try:
    import psycopg2 as pg_driver
except ModuleNotFoundError:  # pragma: no cover - fallback for environments using psycopg 3
    import psycopg as pg_driver


STOCKWORKS_TABLES = (
    "material",
    "materialcosthistory",
    "inventoryitem",
    "stockmovement",
    "hardwareitem",
    "hardwaremovement",
    "printmodel",
    "printmodelsale",
    "printmodelmovement",
)


@dataclass(frozen=True)
class PostgresConfig:
    dsn: str
    schema: Optional[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy StockWorks tables between Postgres schemas in the same database. "
            "Defaults to dry-run."
        )
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="Postgres URL. Defaults to $DATABASE_URL.",
    )
    parser.add_argument(
        "--source-schema",
        default="orderworks",
        help="Schema to copy StockWorks data from. Default: orderworks.",
    )
    parser.add_argument(
        "--target-schema",
        default="public",
        help="Schema to copy StockWorks data to. Default: public.",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=list(STOCKWORKS_TABLES),
        help="Subset of StockWorks tables to migrate.",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Delete target rows before copying. Recommended only when target is known empty or disposable.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the migration. Without this flag the script reports what it would do.",
    )
    return parser.parse_args()


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


def quote_ident(value: str) -> str:
    if not value:
        raise ValueError("Identifier cannot be empty.")
    return f'"{value.replace("\"", "\"\"")}"'


def normalize_tables(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    allowed = set(STOCKWORKS_TABLES)
    for value in values:
        table = str(value or "").strip().lower()
        if not table:
            continue
        if table not in allowed:
            raise SystemExit(
                f"Unsupported table: {value!r}. Allowed values: {', '.join(STOCKWORKS_TABLES)}"
            )
        if table in seen:
            continue
        seen.add(table)
        normalized.append(table)
    if not normalized:
        raise SystemExit("At least one table must be selected.")
    return normalized


def fetch_existing_tables(conn, schema: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            """,
            (schema,),
        )
        return {row[0] for row in cur.fetchall()}


def fetch_columns(conn, schema: str, table: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return [row[0] for row in cur.fetchall()]


def fetch_counts(conn, schema: str, tables: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {quote_ident(schema)}.{quote_ident(table)}")
            counts[table] = int(cur.fetchone()[0])
    return counts


def reset_sequence(conn, schema: str, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pg_get_serial_sequence(%s, 'id')
            """,
            (f"{schema}.{table}",),
        )
        sequence_name = cur.fetchone()[0]
        if not sequence_name:
            return
        cur.execute(
            f"""
            SELECT setval(
                %s,
                COALESCE((SELECT MAX(id) FROM {quote_ident(schema)}.{quote_ident(table)}), 1),
                true
            )
            """,
            (sequence_name,),
        )


def truncate_tables(conn, schema: str, tables: Iterable[str]) -> None:
    table_list = ", ".join(f"{quote_ident(schema)}.{quote_ident(table)}" for table in reversed(list(tables)))
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE")


def copy_table(conn, source_schema: str, target_schema: str, table: str) -> int:
    source_columns = fetch_columns(conn, source_schema, table)
    target_columns = fetch_columns(conn, target_schema, table)
    common_columns = [column for column in target_columns if column in set(source_columns)]
    if not common_columns:
        raise SystemExit(
            f"No common columns found for {source_schema}.{table} -> {target_schema}.{table}."
        )
    column_sql = ", ".join(quote_ident(column) for column in common_columns)
    update_columns = [column for column in common_columns if column != "id"]
    update_sql = ", ".join(
        f"{quote_ident(column)} = EXCLUDED.{quote_ident(column)}" for column in update_columns
    )
    statement = f"""
        INSERT INTO {quote_ident(target_schema)}.{quote_ident(table)} ({column_sql})
        SELECT {column_sql}
        FROM {quote_ident(source_schema)}.{quote_ident(table)}
        ON CONFLICT ({quote_ident('id')}) DO {"UPDATE SET " + update_sql if update_columns else "NOTHING"}
    """
    with conn.cursor() as cur:
        cur.execute(statement)
        return cur.rowcount


def main() -> int:
    args = parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL must be provided via --database-url or environment.")

    tables = normalize_tables(args.tables)
    source_schema = str(args.source_schema or "").strip() or "orderworks"
    target_schema = str(args.target_schema or "").strip() or "public"
    if source_schema == target_schema:
        raise SystemExit("Source and target schemas must be different.")

    pg_config = strip_schema_parameter(args.database_url)
    conn = pg_driver.connect(pg_config.dsn)
    conn.autocommit = False
    try:
        source_tables = fetch_existing_tables(conn, source_schema)
        target_tables = fetch_existing_tables(conn, target_schema)

        missing_source = [table for table in tables if table not in source_tables]
        missing_target = [table for table in tables if table not in target_tables]
        if missing_source:
            raise SystemExit(
                f"Source schema {source_schema!r} is missing tables: {', '.join(missing_source)}"
            )
        if missing_target:
            raise SystemExit(
                f"Target schema {target_schema!r} is missing tables: {', '.join(missing_target)}"
            )

        source_counts = fetch_counts(conn, source_schema, tables)
        target_counts = fetch_counts(conn, target_schema, tables)

        if not args.apply:
            print(
                json.dumps(
                    {
                        "mode": "dry-run",
                        "database_schema_parameter": pg_config.schema,
                        "source_schema": source_schema,
                        "target_schema": target_schema,
                        "tables": tables,
                        "truncate_target": bool(args.truncate_target),
                        "source_counts": source_counts,
                        "target_counts": target_counts,
                        "note": (
                            "Re-run with --apply to perform the copy. "
                            "Add --truncate-target only if you want the target tables cleared first."
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            conn.rollback()
            return 0

        if args.truncate_target:
            truncate_tables(conn, target_schema, tables)

        copied_counts: dict[str, int] = {}
        for table in tables:
            copied_counts[table] = copy_table(conn, source_schema, target_schema, table)

        for table in tables:
            reset_sequence(conn, target_schema, table)

        final_target_counts = fetch_counts(conn, target_schema, tables)
        conn.commit()
        print(
            json.dumps(
                {
                    "mode": "apply",
                    "source_schema": source_schema,
                    "target_schema": target_schema,
                    "tables": tables,
                    "truncate_target": bool(args.truncate_target),
                    "source_counts": source_counts,
                    "target_counts_before": target_counts,
                    "rows_copied_or_updated": copied_counts,
                    "target_counts_after": final_target_counts,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
