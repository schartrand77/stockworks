"""Database utilities for the StockWorks inventory service."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Tuple

from sqlmodel import Session, SQLModel, create_engine
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


def create_db_engine():
    database_url = _build_database_url()
    database_url, schema = _strip_schema_parameter(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    if schema and not database_url.startswith("sqlite"):
        schema_option = f"-c search_path={schema}"
        existing_options = connect_args.get("options")
        connect_args["options"] = f"{existing_options} {schema_option}".strip() if existing_options else schema_option
    return create_engine(database_url, connect_args=connect_args)


engine = create_db_engine()


def init_db() -> None:
    """Create database tables if they don't exist yet and ensure schema patches are applied."""
    SQLModel.metadata.create_all(engine)
    _ensure_material_columns()


@contextmanager
def session_scope() -> Iterator[Session]:
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
    with Session(engine) as session:
        yield session


def _ensure_material_columns() -> None:
    """Add newly introduced columns to the materials table for existing SQLite deployments."""
    backend = engine.url.get_backend_name()
    if backend != "sqlite":
        return
    desired_columns = {
        "category": "TEXT",
        "barcode": "TEXT",
    }
    with engine.begin() as conn:
        pragma_rows = conn.exec_driver_sql("PRAGMA table_info(material)").fetchall()
        existing_columns = {row[1] for row in pragma_rows}
        for column, ddl in desired_columns.items():
            if column not in existing_columns:
                conn.exec_driver_sql(f"ALTER TABLE material ADD COLUMN {column} {ddl}")
