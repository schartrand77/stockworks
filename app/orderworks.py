"""OrderWorks integration helpers."""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

ORDERWORKS_SESSION_REFRESH_SECONDS = 60 * 60 * 6  # refresh every 6 hours


class OrderWorksIntegrationError(Exception):
    """Base error for integration failures."""


class OrderWorksNotConfiguredError(OrderWorksIntegrationError):
    """Raised when the integration is not configured."""


class OrderWorksAuthenticationError(OrderWorksIntegrationError):
    """Raised when authentication with OrderWorks fails."""


class OrderWorksDatabaseUnavailableError(OrderWorksIntegrationError):
    """Raised when OrderWorks tables cannot be queried via the shared database."""


class OrderWorksClient:
    """Simple client for communicating with the OrderWorks admin API."""

    def __init__(self, base_url: Optional[str], username: Optional[str], password: Optional[str], timeout: float = 20.0):
        self.base_url = (base_url or "").rstrip("/")
        self.username = (username or "").strip()
        self.password = (password or "").strip()
        self._timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._session_expires_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.username and self.password)

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            if not self.base_url:
                raise OrderWorksNotConfiguredError("OrderWorks base URL is not configured.")
            self._client = httpx.Client(base_url=self.base_url, timeout=self._timeout, follow_redirects=False)
        return self._client

    def _session_valid(self) -> bool:
        return self._session_expires_at > time.time()

    def _login(self, force: bool = False) -> None:
        if not self.is_configured:
            raise OrderWorksNotConfiguredError("OrderWorks integration is not configured.")
        with self._lock:
            if self._session_valid() and not force:
                return
            client = self._get_client()
            client.cookies.clear()
            try:
                response = client.post(
                    "/api/auth/login",
                    json={"username": self.username, "password": self.password},
                )
            except httpx.HTTPError as exc:
                raise OrderWorksIntegrationError(f"Failed to contact OrderWorks during login: {exc}") from exc
            if response.status_code == 401:
                raise OrderWorksAuthenticationError("OrderWorks credentials were rejected.")
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise OrderWorksIntegrationError(f"OrderWorks login failed: {exc}") from exc
            if "orderworks_admin_session" not in client.cookies:
                raise OrderWorksIntegrationError("OrderWorks login did not return a session cookie.")
            self._session_expires_at = time.time() + ORDERWORKS_SESSION_REFRESH_SECONDS

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self.is_configured:
            raise OrderWorksNotConfiguredError("OrderWorks integration is not configured.")
        self._login()
        client = self._get_client()
        try:
            response = client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise OrderWorksIntegrationError(f"Failed to contact OrderWorks: {exc}") from exc
        if response.status_code == 401:
            self._login(force=True)
            try:
                response = client.request(method, path, **kwargs)
            except httpx.HTTPError as exc:
                raise OrderWorksIntegrationError(f"Failed to contact OrderWorks after refreshing the session: {exc}") from exc
        return response

    def list_jobs(self, params: Optional[Dict[str, Any]] = None) -> Any:
        response = self._request("GET", "/api/jobs", params=params or {})
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OrderWorksIntegrationError(f"OrderWorks request failed: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise OrderWorksIntegrationError("OrderWorks returned invalid JSON.") from exc
        jobs = data.get("jobs")
        if not isinstance(jobs, list):
            raise OrderWorksIntegrationError("OrderWorks response did not include jobs.")
        return jobs


_ORDERWORKS_CLIENT: Optional[OrderWorksClient] = None


def get_orderworks_client() -> OrderWorksClient:
    global _ORDERWORKS_CLIENT
    if _ORDERWORKS_CLIENT is None:
        _ORDERWORKS_CLIENT = OrderWorksClient(
            base_url=os.environ.get("ORDERWORKS_BASE_URL"),
            username=os.environ.get("ORDERWORKS_ADMIN_USERNAME"),
            password=os.environ.get("ORDERWORKS_ADMIN_PASSWORD"),
        )
    return _ORDERWORKS_CLIENT


@dataclass(frozen=True)
class ColumnMapping:
    names: Sequence[str]
    alias: str
    required: bool = False


_ORDERWORKS_JOB_TABLE = "orderworks.jobs"
_ORDERWORKS_JOB_COLUMNS: List[ColumnMapping] = [
    ColumnMapping(("id",), "id", required=True),
    ColumnMapping(("payment_intent_id", "paymentIntentId"), "paymentIntentId"),
    ColumnMapping(("total_cents", "totalCents"), "totalCents"),
    ColumnMapping(("currency",), "currency"),
    ColumnMapping(("line_items", "lineItems"), "lineItems"),
    ColumnMapping(("shipping",), "shipping"),
    ColumnMapping(("metadata",), "metadata"),
    ColumnMapping(("user_id", "userId"), "userId"),
    ColumnMapping(("customer_email", "customerEmail"), "customerEmail"),
    ColumnMapping(("makerworks_created_at",), "makerworksCreatedAt"),
    ColumnMapping(("makerworks_updated_at",), "makerworksUpdatedAt"),
    ColumnMapping(("status",), "status"),
    ColumnMapping(("notes",), "notes"),
    ColumnMapping(("payment_method", "paymentMethod"), "paymentMethod"),
    ColumnMapping(("payment_status", "paymentStatus"), "paymentStatus"),
    ColumnMapping(("fulfillment_status", "fulfillmentStatus"), "fulfillmentStatus"),
    ColumnMapping(("fulfilled_at", "fulfilledAt"), "fulfilledAt"),
    ColumnMapping(("queue_position", "queuePosition"), "queuePosition"),
    ColumnMapping(("created_at", "createdAt"), "createdAt"),
    ColumnMapping(("updated_at", "updatedAt"), "updatedAt"),
]


def _quote_identifier(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def _split_table_identifier(identifier: str) -> tuple[Optional[str], str]:
    if "." in identifier:
        schema, table = identifier.split(".", 1)
        return schema, table
    return None, identifier


def _quote_table(schema: Optional[str], table: str) -> str:
    quoted_table = _quote_identifier(table)
    if schema:
        return f"{_quote_identifier(schema)}.{quoted_table}"
    return quoted_table


def _fetch_available_columns(session: Session, schema: Optional[str], table: str) -> set[str]:
    connection = session.connection()
    dialect_name = connection.dialect.name
    columns: set[str] = set()
    if dialect_name == "sqlite":
        result = connection.exec_driver_sql(f"PRAGMA table_info({table})")
        columns = {row[1] for row in result}
    else:
        params = {"table": table}
        predicate = "table_name = :table"
        if schema:
            params["schema"] = schema
            predicate += " AND table_schema = :schema"
        query = text(f"SELECT column_name FROM information_schema.columns WHERE {predicate}")
        result = connection.execute(query, params)
        columns = {row[0] for row in result}
    return columns


def _match_column(available: Iterable[str], candidate: str) -> Optional[str]:
    for existing in available:
        if existing == candidate or existing.lower() == candidate.lower():
            return existing
    return None


def _find_matching_column(available: set[str], candidates: Sequence[str]) -> Optional[str]:
    for candidate in candidates:
        match = _match_column(available, candidate)
        if match:
            return match
    return None


def _build_jobs_query(session: Session) -> text:
    schema, table = _split_table_identifier(_ORDERWORKS_JOB_TABLE)
    available_columns = _fetch_available_columns(session, schema, table)
    select_parts: List[str] = []
    column_expr_map: Dict[str, Optional[str]] = {}

    for mapping in _ORDERWORKS_JOB_COLUMNS:
        alias_sql = _quote_identifier(mapping.alias)
        matched_column = _find_matching_column(available_columns, mapping.names)
        if not matched_column:
            if mapping.required:
                readable = ", ".join(mapping.names)
                raise OrderWorksDatabaseUnavailableError(
                    f"OrderWorks table {_ORDERWORKS_JOB_TABLE} is missing required column(s): {readable}."
                )
            select_parts.append(f"NULL AS {alias_sql}")
            column_expr_map[mapping.alias] = None
            continue
        column_expr = _quote_identifier(matched_column)
        select_parts.append(f"{column_expr} AS {alias_sql}")
        column_expr_map[mapping.alias] = column_expr

    order_aliases = ("makerworksCreatedAt", "createdAt", "id")
    order_fragments: List[str] = []
    for alias in order_aliases:
        column_expr = column_expr_map.get(alias)
        if column_expr:
            direction = "DESC"
            order_fragments.append(f"{column_expr} {direction}")
    if not order_fragments:
        order_fragments.append(f"{_quote_identifier('id')} DESC")

    columns_sql = ",\n        ".join(select_parts)
    table_sql = _quote_table(schema, table)
    order_sql = ", ".join(order_fragments)
    sql = (
        "SELECT\n        "
        + columns_sql
        + f"\n    FROM {table_sql}\n    ORDER BY {order_sql}\n    LIMIT :limit"
    )
    return text(sql)


def list_orderworks_jobs_via_database(session: Session, limit: int = 200) -> List[Dict[str, Any]]:
    """Return OrderWorks jobs directly from the shared MakerWorks/Postgres database."""

    try:
        query = _build_jobs_query(session)
        result = session.exec(query.bindparams(limit=limit))
    except SQLAlchemyError as exc:
        raise OrderWorksDatabaseUnavailableError(
            f"Unable to query OrderWorks tables via the configured database: {exc}"
        ) from exc
    rows = result.mappings().all()
    return [dict(row) for row in rows]
