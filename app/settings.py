"""Runtime integration settings for StockWorks."""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from sqlmodel import Session, select

from .models import AppSetting


ALLOWED_SETTINGS: dict[str, dict[str, Any]] = {
    "PRINTLAB_BASE_URL": {"category": "printlab", "secret": False, "label": "PrintLab URL"},
    "PRINTLAB_API_KEY": {"category": "printlab", "secret": True, "label": "PrintLab API key"},
    "PRINTLAB_API_AUTH_HEADER": {"category": "printlab", "secret": False, "label": "PrintLab auth header"},
    "PRINTLAB_BEARER_TOKEN": {"category": "printlab", "secret": True, "label": "PrintLab bearer token"},
    "PRINTLAB_USERNAME": {"category": "printlab", "secret": False, "label": "PrintLab username"},
    "PRINTLAB_PASSWORD": {"category": "printlab", "secret": True, "label": "PrintLab password"},
    "ORDERWORKS_BASE_URL": {"category": "orderworks", "secret": False, "label": "OrderWorks URL"},
    "ORDERWORKS_ADMIN_USERNAME": {"category": "orderworks", "secret": False, "label": "OrderWorks admin username"},
    "ORDERWORKS_ADMIN_PASSWORD": {"category": "orderworks", "secret": True, "label": "OrderWorks admin password"},
    "SMTP_HOST": {"category": "digest", "secret": False, "label": "SMTP host"},
    "SMTP_PORT": {"category": "digest", "secret": False, "label": "SMTP port"},
    "SMTP_USERNAME": {"category": "digest", "secret": False, "label": "SMTP username"},
    "SMTP_PASSWORD": {"category": "digest", "secret": True, "label": "SMTP password"},
    "SMTP_USE_TLS": {"category": "digest", "secret": False, "label": "Use TLS"},
    "LOW_STOCK_DIGEST_FROM": {"category": "digest", "secret": False, "label": "Digest sender"},
    "LOW_STOCK_DIGEST_RECIPIENTS": {"category": "digest", "secret": False, "label": "Digest recipients"},
}


def mask_secret(value: str | None) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 4:
        return "****"
    return f"{'*' * 8}{text[-4:]}"


def validate_settings_payload(payload: Mapping[str, object]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for key, value in payload.items():
        normalized_key = str(key or "").strip()
        if normalized_key not in ALLOWED_SETTINGS:
            raise ValueError(f"Unsupported runtime setting: {normalized_key}")
        if value is None:
            parsed[normalized_key] = ""
        else:
            parsed[normalized_key] = str(value).strip()
    return parsed


def load_runtime_settings(session: Session) -> dict[str, str]:
    rows = session.exec(select(AppSetting)).all()
    return {row.key: row.value or "" for row in rows if row.key in ALLOWED_SETTINGS}


def get_effective_setting(
    key: str,
    stored: Mapping[str, str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    if stored is not None:
        value = str(stored.get(key) or "").strip()
        if value:
            return value
    source = env if env is not None else os.environ
    return str(source.get(key) or "").strip()


def effective_settings_map(stored: Mapping[str, str]) -> dict[str, str]:
    return {key: get_effective_setting(key, stored) for key in ALLOWED_SETTINGS}


def redact_settings(stored: Mapping[str, str]) -> dict[str, dict[str, object]]:
    payload: dict[str, dict[str, object]] = {}
    for key, definition in ALLOWED_SETTINGS.items():
        secret = bool(definition["secret"])
        stored_value = str(stored.get(key) or "").strip()
        env_value = get_effective_setting(key, {})
        effective_value = stored_value or env_value
        payload[key] = {
            "key": key,
            "category": definition["category"],
            "label": definition["label"],
            "secret": secret,
            "configured": bool(effective_value),
            "source": "stored" if stored_value else ("env" if env_value else "missing"),
            "value": mask_secret(effective_value) if secret else effective_value,
        }
    return payload
