"""Authorization helpers for StockWorks env-based roles."""
from __future__ import annotations

import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    username: str
    role: str


SHOP_ACTIONS = {
    "read",
    "inventory:create",
    "inventory:update",
    "movements:create",
    "hardware_movements:create",
    "model_movements:create",
    "model_sales:create",
    "receipts:write",
    "labels:print",
    "csv:export",
    "digest:send",
}


def _matches(identifier: str, username: str, email: str | None) -> bool:
    normalized = identifier.strip().lower()
    allowed = [username.strip().lower()]
    if email:
        allowed.append(email.strip().lower())
    return any(secrets.compare_digest(normalized, item) for item in allowed if item)


def resolve_actor(
    username: str,
    password: str,
    *,
    admin_username: str,
    admin_email: str | None,
    admin_password: str,
    shop_username: str | None = None,
    shop_email: str | None = None,
    shop_password: str | None = None,
) -> Actor | None:
    if _matches(username, admin_username, admin_email) and (
        secrets.compare_digest(password, admin_password) or secrets.compare_digest(password.strip(), admin_password)
    ):
        return Actor(username=admin_username, role="admin")
    if shop_username and shop_password and _matches(username, shop_username, shop_email) and (
        secrets.compare_digest(password, shop_password) or secrets.compare_digest(password.strip(), shop_password)
    ):
        return Actor(username=shop_username, role="shop")
    return None


def role_can(role: str, action: str) -> bool:
    if role == "admin":
        return True
    if role == "shop":
        return action in SHOP_ACTIONS
    return False
