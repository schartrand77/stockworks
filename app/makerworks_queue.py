"""MakerWorks production queue integration helpers."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session


class MakerWorksQueueError(Exception):
    """Raised when MakerWorks production queue tables cannot be queried."""


QUEUE_STATUSES = {"queued", "printing", "post_process", "failed", "completed"}


def _table_name(session: Session, table: str) -> str:
    dialect_name = session.connection().dialect.name
    if dialect_name == "sqlite":
        return f'"{table}"'
    return f'public."{table}"'


def _parse_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _read_submission(metadata: Any) -> dict[str, Any]:
    submission = _parse_metadata(metadata).get("lastPrintLabSubmission")
    return submission if isinstance(submission, dict) else {}


def _read_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _order_label(order_number: Any) -> str:
    try:
        number = int(order_number)
    except (TypeError, ValueError):
        return "Draft order"
    return f"MW-{number:05d}"


def _normalize_status(order_status: Any, printlab_status: Any) -> str:
    status = (_read_string(printlab_status) or _read_string(order_status) or "unknown").lower()
    if status == "started":
        return "printing"
    if status == "cancelled":
        return "canceled"
    return status


def _fetch_order_rows(session: Session, limit: int) -> list[dict[str, Any]]:
    orders_table = _table_name(session, "PrintOrder")
    printers_table = _table_name(session, "Printer")
    query = text(
        f"""
        SELECT
            o."id" AS "id",
            o."orderNumber" AS "orderNumber",
            o."status" AS "orderStatus",
            o."customerEmail" AS "customerEmail",
            o."customerName" AS "customerName",
            o."paymentMethod" AS "paymentMethod",
            o."paymentStatus" AS "paymentStatus",
            o."totalCents" AS "totalCents",
            o."currency" AS "currency",
            o."metadata" AS "metadata",
            o."createdAt" AS "createdAt",
            o."updatedAt" AS "updatedAt",
            p."name" AS "printerName"
        FROM {orders_table} o
        LEFT JOIN {printers_table} p ON p."id" = o."printerId"
        ORDER BY
            CASE LOWER(o."status")
                WHEN 'queued' THEN 0
                WHEN 'printing' THEN 1
                WHEN 'post_process' THEN 2
                WHEN 'failed' THEN 3
                WHEN 'completed' THEN 4
                ELSE 5
            END,
            o."createdAt" ASC
        LIMIT :limit
        """
    )
    result = session.exec(query.bindparams(limit=limit))
    rows = [dict(row) for row in result.mappings().all()]
    return [
        row
        for row in rows
        if _normalize_status(row.get("orderStatus"), _read_submission(row.get("metadata")).get("status")) in QUEUE_STATUSES
    ]


def _fetch_line_items(session: Session, order_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not order_ids:
        return {}
    items_table = _table_name(session, "PrintOrderItem")
    query = (
        text(
            f"""
            SELECT
                "orderId" AS "orderId",
                "modelTitle" AS "modelTitle",
                "material" AS "material",
                "quantity" AS "quantity",
                "totalCents" AS "totalCents"
            FROM {items_table}
            WHERE "orderId" IN :order_ids
            """
        )
        .bindparams(bindparam("order_ids", expanding=True))
    )
    result = session.execute(query, {"order_ids": order_ids})
    items_by_order: dict[str, list[dict[str, Any]]] = {order_id: [] for order_id in order_ids}
    for row in result.mappings().all():
        item = dict(row)
        order_id = str(item.pop("orderId"))
        items_by_order.setdefault(order_id, []).append(item)
    return items_by_order


def list_makerworks_production_jobs(session: Session, limit: int = 200) -> List[Dict[str, Any]]:
    """Return queued/completed MakerWorks production jobs with PrintLab handoff state."""

    try:
        order_rows = _fetch_order_rows(session, limit)
        line_items = _fetch_line_items(session, [str(row["id"]) for row in order_rows])
    except SQLAlchemyError as exc:
        raise MakerWorksQueueError(f"Unable to query MakerWorks production queue via the configured database: {exc}") from exc

    jobs: list[dict[str, Any]] = []
    for index, row in enumerate(order_rows, start=1):
        submission = _read_submission(row.get("metadata"))
        printlab_status = _read_string(submission.get("status"))
        printlab_printer_name = _read_string(submission.get("printerName"))
        status = _normalize_status(row.get("orderStatus"), printlab_status)
        job_id = str(row["id"])
        jobs.append(
            {
                "id": job_id,
                "orderNumber": row.get("orderNumber"),
                "orderLabel": _order_label(row.get("orderNumber")),
                "status": status,
                "createdAt": row.get("createdAt"),
                "updatedAt": row.get("updatedAt"),
                "customerEmail": row.get("customerEmail"),
                "customerName": row.get("customerName"),
                "paymentMethod": row.get("paymentMethod"),
                "paymentStatus": row.get("paymentStatus"),
                "totalCents": row.get("totalCents"),
                "currency": row.get("currency"),
                "lineItems": line_items.get(job_id, []),
                "printLabStatus": printlab_status,
                "printLabPrinterName": printlab_printer_name,
                "printLabJobId": _read_string(submission.get("printLabJobId")),
                "printLabError": _read_string(submission.get("error")),
                "printerName": row.get("printerName") or printlab_printer_name,
                "queuePosition": index,
            }
        )
    return jobs
