"""Database utilities for the StockWorks inventory service."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Tuple

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_SCHEMA: Optional[str] = None


def _resolve_data_dir() -> Path:
    """Return the directory that stores the SQLite database."""
    configured_dir = os.environ.get("STOCKWORKS_DATA_DIR")
    if configured_dir:
        path = Path(configured_dir)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path
    return PROJECT_ROOT / "data"


DEFAULT_SQLITE_PATH = (_resolve_data_dir() / os.environ.get("STOCKWORKS_DB_FILENAME", "app.db")).resolve()


def _build_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_SQLITE_PATH}"


def _strip_schema_parameter(database_url: str) -> Tuple[str, Optional[str]]:
    """Remove ?schema=<name> from DATABASE_URL so psycopg2 accepts the DSN."""
    parsed = urlparse(database_url)
    if not parsed.query:
        return database_url, None

    schema = None
    filtered_query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key == "schema" and schema is None:
            schema = value
        else:
            filtered_query.append((key, value))

    if schema is None:
        return database_url, None

    new_query = urlencode(filtered_query, doseq=True)
    return urlunparse(parsed._replace(query=new_query)), schema


def _configure_sqlite_connection(db_engine, database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        return

    @event.listens_for(db_engine, "connect")
    def _set_sqlite_runtime_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()


def create_db_engine():
    global DB_SCHEMA
    database_url = _build_database_url()
    database_url, schema = _strip_schema_parameter(database_url)
    DB_SCHEMA = schema
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    if schema and not database_url.startswith("sqlite"):
        schema_option = f"-c search_path={schema}"
        existing_options = connect_args.get("options")
        connect_args["options"] = f"{existing_options} {schema_option}".strip() if existing_options else schema_option
    engine = create_engine(database_url, connect_args=connect_args)
    _configure_sqlite_connection(engine, database_url)
    return engine


engine = create_db_engine()
_DB_READY = False


def init_db() -> None:
    """Create database tables if they don't exist yet and ensure schema patches are applied."""
    global _DB_READY
    _ensure_schema_exists()
    SQLModel.metadata.create_all(engine)
    _ensure_sqlite_pragmas()
    _ensure_performance_indexes()
    _ensure_material_columns()
    _ensure_hardware_columns()
    _ensure_print_model_columns()
    _DB_READY = True


def ensure_db_ready() -> None:
    """Guarantee the database schema is initialized before handling requests."""
    global _DB_READY
    if _DB_READY:
        return
    init_db()


@contextmanager
def session_scope() -> Iterator[Session]:
    ensure_db_ready()
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    ensure_db_ready()
    with Session(engine) as session:
        yield session


def _ensure_material_columns() -> None:
    desired_columns = {
        "category": "TEXT",
        "barcode": "TEXT",
        "refill_barcode": "TEXT",
        "color_hex": "TEXT",
    }
    backend = engine.url.get_backend_name()
    with engine.begin() as conn:
        if backend == "sqlite":
            pragma_rows = conn.exec_driver_sql("PRAGMA table_info(material)").fetchall()
            existing_columns = {row[1] for row in pragma_rows}
            for column, ddl in desired_columns.items():
                if column not in existing_columns:
                    conn.exec_driver_sql(f"ALTER TABLE material ADD COLUMN {column} {ddl}")
            return
        if backend.startswith("postgres"):
            schema = (DB_SCHEMA or "public").strip() or "public"
            quoted_schema = engine.dialect.identifier_preparer.quote(schema)
            table_name = f"{quoted_schema}.material"
            for column, ddl in desired_columns.items():
                conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column} {ddl}")


def _ensure_schema_exists() -> None:
    """Create the configured Postgres schema if it is missing."""
    backend = engine.url.get_backend_name()
    if backend == "sqlite" or not DB_SCHEMA:
        return
    schema = DB_SCHEMA.strip()
    if not schema:
        return
    with engine.begin() as conn:
        quoted_schema = engine.dialect.identifier_preparer.quote(schema)
        conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}")


def _ensure_hardware_columns() -> None:
    desired_columns = {
        "makerworks_product_template_id": "TEXT",
        "merch_color": "TEXT",
        "merch_size": "TEXT",
        "merch_style": "TEXT",
        "merch_sku": "TEXT",
    }
    backend = engine.url.get_backend_name()
    with engine.begin() as conn:
        if backend == "sqlite":
            pragma_rows = conn.exec_driver_sql("PRAGMA table_info(hardwareitem)").fetchall()
            existing_columns = {row[1] for row in pragma_rows}
            for column, ddl in desired_columns.items():
                if column not in existing_columns:
                    conn.exec_driver_sql(f"ALTER TABLE hardwareitem ADD COLUMN {column} {ddl}")
            return
        if backend.startswith("postgres"):
            schema = (DB_SCHEMA or "public").strip() or "public"
            quoted_schema = engine.dialect.identifier_preparer.quote(schema)
            table_name = f"{quoted_schema}.hardwareitem"
            for column, ddl in desired_columns.items():
                conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column} {ddl}")


def _ensure_print_model_columns() -> None:
    desired_columns = {
        "quantity_on_hand": "FLOAT DEFAULT 0",
        "makerworks_product_template_id": "TEXT",
    }
    backend = engine.url.get_backend_name()
    with engine.begin() as conn:
        if backend == "sqlite":
            pragma_rows = conn.exec_driver_sql("PRAGMA table_info(printmodel)").fetchall()
            existing_columns = {row[1] for row in pragma_rows}
            for column, ddl in desired_columns.items():
                if column not in existing_columns:
                    conn.exec_driver_sql(f"ALTER TABLE printmodel ADD COLUMN {column} {ddl}")
            return
        if backend.startswith("postgres"):
            schema = (DB_SCHEMA or "public").strip() or "public"
            quoted_schema = engine.dialect.identifier_preparer.quote(schema)
            table_name = f"{quoted_schema}.printmodel"
            for column, ddl in desired_columns.items():
                conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column} {ddl}")


def _ensure_sqlite_pragmas() -> None:
    backend = engine.url.get_backend_name()
    if backend != "sqlite":
        return
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")


def _ensure_performance_indexes() -> None:
    backend = engine.url.get_backend_name()
    if backend == "sqlite":
        statements = [
            "CREATE INDEX IF NOT EXISTS ix_material_name ON material (name)",
            "CREATE INDEX IF NOT EXISTS ix_material_category ON material (category)",
            "CREATE INDEX IF NOT EXISTS ix_inventoryitem_material_location ON inventoryitem (material_id, location)",
            "CREATE INDEX IF NOT EXISTS ix_stockmovement_item_created ON stockmovement (inventory_item_id, created_at)",
            "CREATE INDEX IF NOT EXISTS ix_hardwareitem_category_name ON hardwareitem (category, name)",
            "CREATE INDEX IF NOT EXISTS ix_hardwaremovement_item_created ON hardwaremovement (hardware_item_id, created_at)",
            "CREATE INDEX IF NOT EXISTS ix_printmodelsale_model_sold ON printmodelsale (model_id, sold_at)",
            "CREATE INDEX IF NOT EXISTS ix_printmodelmovement_model_created ON printmodelmovement (model_id, created_at)",
        ]
        with engine.begin() as conn:
            for statement in statements:
                conn.exec_driver_sql(statement)
        return
    if backend.startswith("postgres"):
        schema = (DB_SCHEMA or "public").strip() or "public"
        quoted_schema = engine.dialect.identifier_preparer.quote(schema)
        statements = [
            f"CREATE INDEX IF NOT EXISTS ix_material_name ON {quoted_schema}.material (name)",
            f"CREATE INDEX IF NOT EXISTS ix_material_category ON {quoted_schema}.material (category)",
            f"CREATE INDEX IF NOT EXISTS ix_inventoryitem_material_location ON {quoted_schema}.inventoryitem (material_id, location)",
            f"CREATE INDEX IF NOT EXISTS ix_stockmovement_item_created ON {quoted_schema}.stockmovement (inventory_item_id, created_at)",
            f"CREATE INDEX IF NOT EXISTS ix_hardwareitem_category_name ON {quoted_schema}.hardwareitem (category, name)",
            f"CREATE INDEX IF NOT EXISTS ix_hardwaremovement_item_created ON {quoted_schema}.hardwaremovement (hardware_item_id, created_at)",
            f"CREATE INDEX IF NOT EXISTS ix_printmodelsale_model_sold ON {quoted_schema}.printmodelsale (model_id, sold_at)",
            f"CREATE INDEX IF NOT EXISTS ix_printmodelmovement_model_created ON {quoted_schema}.printmodelmovement (model_id, created_at)",
        ]
        with engine.begin() as conn:
            for statement in statements:
                conn.exec_driver_sql(statement)
