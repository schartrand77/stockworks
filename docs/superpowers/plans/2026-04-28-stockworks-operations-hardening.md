# StockWorks Operations Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add StockWorks-only receipt audit logging, SMTP low-stock digests, batch barcode labels, CSV import/export, and env-based shop-floor role support.

**Architecture:** Keep the current FastAPI and SQLModel app structure. Add focused helper modules for roles, CSV, and email; extend `app/api.py` only at route boundaries; add the audit model to `app/models.py`; use `app/db.py` startup schema creation for new tables.

**Tech Stack:** Python 3, FastAPI, SQLModel, Jinja2/static JavaScript, standard library `csv`, `smtplib`, `email.message`, `unittest`.

---

### Task 1: Test Harness And Helper Tests

**Files:**
- Create: `tests/test_stockworks_operations.py`

- [ ] **Step 1: Write failing tests for helper modules**

Create `tests/test_stockworks_operations.py` with tests importing planned modules:

```python
import os
import unittest

from app.authz import Actor, resolve_actor, role_can
from app.csv_tools import export_material_rows, parse_material_csv
from app.email_digest import LowStockEntry, build_low_stock_digest, smtp_config_from_env


class AuthzTests(unittest.TestCase):
    def test_resolves_shop_actor_from_credentials(self):
        actor = resolve_actor(
            "floor",
            "floor-password",
            admin_username="admin",
            admin_email="",
            admin_password="admin-password",
            shop_username="floor",
            shop_email="floor@example.com",
            shop_password="floor-password",
        )
        self.assertEqual(actor, Actor(username="floor", role="shop"))

    def test_shop_cannot_delete_materials(self):
        self.assertFalse(role_can("shop", "materials:delete"))
        self.assertTrue(role_can("admin", "materials:delete"))


class CsvToolTests(unittest.TestCase):
    def test_parse_material_csv_reports_row_errors_and_valid_rows(self):
        content = "name,filament_type,color,price_per_gram,spool_weight_grams\nPLA,PLA,Black,0.02,1000\nBad,PLA,Red,nope,1000\n"
        result = parse_material_csv(content.encode("utf-8"))
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.errors[0]["row"], 3)

    def test_export_material_rows_includes_expected_header(self):
        csv_text = export_material_rows([])
        self.assertTrue(csv_text.startswith("name,brand,filament_type,category,color"))


class EmailDigestTests(unittest.TestCase):
    def test_digest_contains_filament_and_hardware(self):
        digest = build_low_stock_digest(
            filament=[
                LowStockEntry(name="PLA Black", location="Rack A", quantity=100, reorder_level=500, unit="g"),
            ],
            hardware=[
                LowStockEntry(name="M3 Inserts", location="Bin 1", quantity=4, reorder_level=20, unit="piece"),
            ],
        )
        self.assertIn("PLA Black", digest.text)
        self.assertIn("M3 Inserts", digest.html)

    def test_smtp_config_requires_core_values(self):
        env = {"SMTP_HOST": "smtp.example.com", "LOW_STOCK_DIGEST_RECIPIENTS": "ops@example.com"}
        self.assertIsNone(smtp_config_from_env(env))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify they fail because modules do not exist**

Run: `python -m unittest tests.test_stockworks_operations -v`

Expected: fail with `ModuleNotFoundError` for `app.authz`.

### Task 2: Role Helper

**Files:**
- Create: `app/authz.py`

- [ ] **Step 1: Implement role helper**

Create `app/authz.py`:

```python
from __future__ import annotations

import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    username: str
    role: str


ADMIN_ACTIONS = {"*"}
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
```

- [ ] **Step 2: Run helper tests**

Run: `python -m unittest tests.test_stockworks_operations -v`

Expected: remaining failures for missing `app.csv_tools` or `app.email_digest`.

### Task 3: CSV Helper

**Files:**
- Create: `app/csv_tools.py`

- [ ] **Step 1: Implement CSV helper**

Create `app/csv_tools.py` with:

```python
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from typing import Any


MATERIAL_COLUMNS = [
    "name", "brand", "filament_type", "category", "color", "color_hex", "color_hexes",
    "supplier", "price_per_gram", "spool_weight_grams", "barcode", "refill_barcode", "notes",
]
HARDWARE_COLUMNS = [
    "name", "category", "merch_color", "merch_size", "merch_style", "merch_sku",
    "supplier", "manufacturer_part_number", "unit_of_measure", "unit_cost",
    "bin_location", "reorder_level", "quantity_on_hand", "notes",
]


@dataclass
class CsvParseResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)


def _decode_csv(content: bytes) -> str:
    return content.decode("utf-8-sig")


def _parse_float(value: str, field_name: str, row_number: int, errors: list[dict[str, Any]]) -> float | None:
    try:
        return float((value or "0").strip() or "0")
    except ValueError:
        errors.append({"row": row_number, "field": field_name, "error": "Must be a number."})
        return None


def _parse_int(value: str, field_name: str, row_number: int, errors: list[dict[str, Any]]) -> int | None:
    parsed = _parse_float(value, field_name, row_number, errors)
    return int(parsed) if parsed is not None else None


def parse_material_csv(content: bytes) -> CsvParseResult:
    return _parse_csv(content, MATERIAL_COLUMNS, {"name", "filament_type", "color"}, {"price_per_gram": "float", "spool_weight_grams": "int"})


def parse_hardware_csv(content: bytes) -> CsvParseResult:
    return _parse_csv(content, HARDWARE_COLUMNS, {"name"}, {"unit_cost": "float", "reorder_level": "float", "quantity_on_hand": "float"})


def _parse_csv(content: bytes, columns: list[str], required: set[str], numeric: dict[str, str]) -> CsvParseResult:
    result = CsvParseResult()
    try:
        text = _decode_csv(content)
    except UnicodeDecodeError:
        result.errors.append({"row": 0, "field": "file", "error": "CSV must be UTF-8."})
        return result
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        result.errors.append({"row": 0, "field": "header", "error": "CSV header row is required."})
        return result
    missing = [column for column in required if column not in reader.fieldnames]
    if missing:
        result.errors.append({"row": 0, "field": "header", "error": f"Missing required columns: {', '.join(sorted(missing))}."})
        return result
    for row_number, row in enumerate(reader, start=2):
        row_errors: list[dict[str, Any]] = []
        parsed = {column: (row.get(column) or "").strip() for column in columns}
        for column in required:
            if not parsed.get(column):
                row_errors.append({"row": row_number, "field": column, "error": "Required field is missing."})
        for column, kind in numeric.items():
            if kind == "int":
                parsed_value = _parse_int(parsed.get(column, ""), column, row_number, row_errors)
            else:
                parsed_value = _parse_float(parsed.get(column, ""), column, row_number, row_errors)
            if parsed_value is not None:
                parsed[column] = parsed_value
        if "color_hexes" in parsed and parsed["color_hexes"]:
            try:
                parsed["color_hexes"] = json.loads(parsed["color_hexes"])
            except json.JSONDecodeError:
                parsed["color_hexes"] = [part.strip() for part in str(parsed["color_hexes"]).split("|") if part.strip()]
        if row_errors:
            result.errors.extend(row_errors)
        else:
            result.rows.append(parsed)
    return result


def export_material_rows(materials: list[Any]) -> str:
    return _export_rows(MATERIAL_COLUMNS, materials)


def export_hardware_rows(items: list[Any]) -> str:
    return _export_rows(HARDWARE_COLUMNS, items)


def _export_rows(columns: list[str], items: list[Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for item in items:
        row = {}
        for column in columns:
            value = getattr(item, column, "")
            if isinstance(value, list):
                value = json.dumps(value)
            row[column] = "" if value is None else value
        writer.writerow(row)
    return output.getvalue()
```

- [ ] **Step 2: Run helper tests**

Run: `python -m unittest tests.test_stockworks_operations -v`

Expected: remaining failures for missing `app.email_digest`.

### Task 4: Email Digest Helper

**Files:**
- Create: `app/email_digest.py`

- [ ] **Step 1: Implement digest helper**

Create `app/email_digest.py` with dataclasses for `LowStockEntry`, `DigestContent`, `SmtpConfig`, `build_low_stock_digest`, `smtp_config_from_env`, and `send_digest_email`.

- [ ] **Step 2: Run helper tests**

Run: `python -m unittest tests.test_stockworks_operations -v`

Expected: all helper tests pass.

### Task 5: Models And API Integration

**Files:**
- Modify: `app/models.py`
- Modify: `app/api.py`
- Modify: `app/db.py`

- [ ] **Step 1: Add `InboundReceiptAuditEvent` SQLModel and read model**

Add model fields from the spec and relation to `InboundInvoice`.

- [ ] **Step 2: Integrate actors and authorization**

Import `Actor`, `resolve_actor`, `role_can`; add `SHOP_*` env config; update login/basic auth to store or resolve role; add dependencies `require_admin`, `require_permission(action)`, and actor dependency.

- [ ] **Step 3: Restrict shop-role catalog/destructive routes**

Apply admin-only dependencies to material create/update/delete/cost-history write, hardware create/update/delete, model create/update/delete, inventory delete, and MakerWorks merch sync/writeback routes.

- [ ] **Step 4: Add receipt audit logging**

Log events in invoice upload, packing slip upload, and verification routes; add `GET /inbound-invoices/{invoice_id}/audit`.

- [ ] **Step 5: Add low-stock digest route**

Query low-stock `InventoryItem` joined to `Material` and low-stock `HardwareItem`, build digest, send SMTP, return counts.

- [ ] **Step 6: Add CSV routes**

Add `GET /materials.csv`, `GET /hardware.csv`, `POST /materials/import`, and `POST /hardware/import`.

- [ ] **Step 7: Add batch barcode labels route**

Add `GET /inbound-invoices/{invoice_id}/barcode-labels` returning print-friendly HTML with one label per received unit up to `STOCKWORKS_MAX_BATCH_LABELS`.

- [ ] **Step 8: Run route compile check**

Run: `python -m compileall app scripts`

Expected: exit 0.

### Task 6: UI Integration

**Files:**
- Modify: `app/templates/index.html`
- Modify: `app/static/app.js`
- Modify: `app/static/styles.css`
- Modify: `.env.example`

- [ ] **Step 1: Expose role to UI**

Add `data-user-role="{{ user_role or 'admin' }}"` to the body or a meta tag and use JS to hide admin-only controls for shop users.

- [ ] **Step 2: Add receipt audit and label controls**

Add a receipt audit block and "Print received labels" button; JS fetches audit events and opens `/inbound-invoices/{id}/barcode-labels` in a print window.

- [ ] **Step 3: Add CSV controls**

Add export/import buttons to Materials and Hardware sections; JS uploads CSV with `uploadApi` and reports summary.

- [ ] **Step 4: Add low-stock digest button**

Add "Send low-stock digest" in Reports or Settings; JS posts to `/reports/low-stock-digest/send`.

- [ ] **Step 5: Document env vars**

Update `.env.example` with `SHOP_*`, SMTP digest vars, and `STOCKWORKS_MAX_BATCH_LABELS`.

### Task 7: Final Verification

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run helper tests**

Run: `python -m unittest tests.test_stockworks_operations -v`

Expected: all tests pass.

- [ ] **Step 2: Run compile check**

Run with env: `ADMIN_PASSWORD=ChangeMePassword123! SECRET_KEY=12345678901234567890123456789012 python -m compileall app scripts`

Expected: exit 0.

- [ ] **Step 3: Run git status and diff review**

Run: `git status --short` and `git diff --stat`

Expected: only intentional StockWorks files changed; `orderworks/` remains untouched and untracked from prior state.
