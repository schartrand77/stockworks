"""Low-stock digest email helpers for StockWorks."""
from __future__ import annotations

import html
import os
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Mapping


@dataclass(frozen=True)
class LowStockEntry:
    name: str
    location: str
    quantity: float
    reorder_level: float
    unit: str


@dataclass(frozen=True)
class DigestContent:
    subject: str
    text: str
    html: str


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    use_tls: bool
    sender: str
    recipients: list[str]


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def smtp_config_from_env(env: Mapping[str, str] | None = None) -> SmtpConfig | None:
    source = env if env is not None else os.environ
    host = (source.get("SMTP_HOST") or "").strip()
    sender = (source.get("LOW_STOCK_DIGEST_FROM") or "").strip()
    recipients = [item.strip() for item in (source.get("LOW_STOCK_DIGEST_RECIPIENTS") or "").split(",") if item.strip()]
    if not host or not sender or not recipients:
        return None
    try:
        port = int((source.get("SMTP_PORT") or "587").strip())
    except ValueError:
        port = 587
    username = (source.get("SMTP_USERNAME") or "").strip() or None
    password = (source.get("SMTP_PASSWORD") or "").strip() or None
    return SmtpConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        use_tls=_truthy(source.get("SMTP_USE_TLS") or "1"),
        sender=sender,
        recipients=recipients,
    )


def build_low_stock_digest(
    *,
    filament: list[LowStockEntry],
    hardware: list[LowStockEntry],
    generated_at: datetime | None = None,
) -> DigestContent:
    timestamp = (generated_at or datetime.now(UTC)).strftime("%Y-%m-%d %H:%M UTC")
    subject = f"StockWorks low-stock digest: {len(filament)} filament, {len(hardware)} hardware"
    text_lines = [subject, f"Generated: {timestamp}", ""]
    text_lines.extend(_text_section("Filament", filament))
    text_lines.append("")
    text_lines.extend(_text_section("Hardware", hardware))
    html_body = (
        "<h1>StockWorks low-stock digest</h1>"
        f"<p>Generated: {html.escape(timestamp)}</p>"
        f"{_html_section('Filament', filament)}"
        f"{_html_section('Hardware', hardware)}"
    )
    return DigestContent(subject=subject, text="\n".join(text_lines), html=html_body)


def _text_section(title: str, entries: list[LowStockEntry]) -> list[str]:
    lines = [f"{title}:"]
    if not entries:
        lines.append("  None below reorder level.")
        return lines
    for entry in entries:
        lines.append(
            f"  - {entry.name} ({entry.location}): {entry.quantity:g} {entry.unit} on hand; "
            f"reorder at {entry.reorder_level:g} {entry.unit}"
        )
    return lines


def _html_section(title: str, entries: list[LowStockEntry]) -> str:
    if not entries:
        return f"<h2>{html.escape(title)}</h2><p>None below reorder level.</p>"
    rows = []
    for entry in entries:
        rows.append(
            "<tr>"
            f"<td>{html.escape(entry.name)}</td>"
            f"<td>{html.escape(entry.location)}</td>"
            f"<td>{entry.quantity:g} {html.escape(entry.unit)}</td>"
            f"<td>{entry.reorder_level:g} {html.escape(entry.unit)}</td>"
            "</tr>"
        )
    return (
        f"<h2>{html.escape(title)}</h2>"
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<thead><tr><th>Name</th><th>Location</th><th>On hand</th><th>Reorder</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def send_digest_email(config: SmtpConfig, digest: DigestContent) -> None:
    message = EmailMessage()
    message["Subject"] = digest.subject
    message["From"] = config.sender
    message["To"] = ", ".join(config.recipients)
    message.set_content(digest.text)
    message.add_alternative(digest.html, subtype="html")
    with smtplib.SMTP(config.host, config.port, timeout=20) as smtp:
        if config.use_tls:
            smtp.starttls()
        if config.username and config.password:
            smtp.login(config.username, config.password)
        smtp.send_message(message)
