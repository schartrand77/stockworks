"""Database utilities for the StockWorks inventory service."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

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


def create_db_engine():
    database_url = _build_database_url()
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
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
