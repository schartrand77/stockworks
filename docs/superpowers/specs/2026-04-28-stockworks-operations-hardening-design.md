# StockWorks Operations Hardening Design

## Scope

This work applies to the root StockWorks FastAPI app only. OrderWorks is legacy and should not receive new feature work or new dependencies from these changes.

The first pass adds operational features without introducing a full user-management system:

- Receipt audit trail.
- Low-stock digest email through SMTP.
- Batch barcode label printing for newly received inventory.
- CSV import/export for materials and hardware.
- Env-configured admin and shop-floor roles.

## Approach

Use the existing StockWorks architecture: SQLModel models, FastAPI routes in `app/api.py`, the single-page UI in `app/templates/index.html` and `app/static/app.js`, and incremental schema patch helpers in `app/db.py`.

New functionality should be small and explicit. Avoid a broad refactor of `app/api.py`, but extract focused helpers for SMTP email, CSV parsing, receipt audit logging, and authorization checks when that reduces risk.

## Authentication And Roles

StockWorks keeps env-based credentials for this pass.

Admin credentials remain:

- `ADMIN_USERNAME`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

Add shop-floor credentials:

- `SHOP_USERNAME`
- `SHOP_EMAIL`
- `SHOP_PASSWORD`

Authenticated sessions should include:

- `authenticated: true`
- `username`
- `role`, either `admin` or `shop`

Basic auth should also resolve to an actor with username and role. Existing API clients using admin basic auth should continue to work.

Admin permissions:

- Full access to all existing and new StockWorks actions.

Shop permissions:

- View dashboards, reports, materials, inventory, receipts, hardware, models, movements, orders, settings needed for scanning and printing.
- Log inventory, hardware, and model movements.
- Upload invoice PDFs and packing slips.
- Verify receipts.
- Print barcode labels.
- Export CSVs.
- Send low-stock digest only if the SMTP config is present.

Shop restrictions:

- Cannot create, edit, or delete materials.
- Cannot create, edit, or delete hardware catalog records.
- Cannot create, edit, or delete models.
- Cannot delete inventory records.
- Cannot run MakerWorks merch sync or writeback actions.

The UI should hide or disable restricted destructive/catalog controls for shop users, but backend route checks are the source of truth.

## Receipt Audit Trail

Add an `InboundReceiptAuditEvent` table tied to `InboundInvoice`.

Fields:

- `id`
- `invoice_id`
- `event_type`
- `actor_username`
- `actor_role`
- `created_at`
- `summary`
- `details_json`

Event types:

- `invoice_uploaded`
- `packing_slip_uploaded`
- `receipt_verified`
- `line_quantity_changed`

Audit behavior:

- Uploading an invoice logs `invoice_uploaded` with source filename, invoice number, expected location, and line count.
- Uploading a packing slip logs `packing_slip_uploaded` with source filename.
- Verifying a receipt logs `receipt_verified` with total expected grams, total received grams, location, and note.
- During verification, each line whose `received_quantity` changes logs `line_quantity_changed` with SKU, product name, previous quantity, new quantity, and expected quantity.

Expose audit events through `GET /inbound-invoices/{invoice_id}/audit`. Also include recent audit events in the receipt detail UI so users can answer who did what and when without opening the database.

## Low-Stock SMTP Digest

Add SMTP configuration through env:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `LOW_STOCK_DIGEST_FROM`
- `LOW_STOCK_DIGEST_RECIPIENTS`

Add a digest service that:

- Finds inventory items where `quantity_grams <= reorder_level` and `reorder_level > 0`.
- Finds hardware items where `quantity_on_hand <= reorder_level` and `reorder_level > 0`.
- Builds a plain-text and simple HTML email.
- Sends to all comma-separated recipients.

Add endpoint:

- `POST /reports/low-stock-digest/send`

The endpoint returns:

- recipient count
- filament low-stock count
- hardware low-stock count
- sent timestamp

If SMTP is not configured, return a clear `503` response. The reports/settings UI should add a "Send low-stock digest" button and show the result.

Scheduled sending is intentionally not part of this first pass. The digest builder should be reusable so scheduling can be added later.

## Batch Barcode Labels

Use the existing Code128 barcode renderer for individual material barcode images.

Add batch label support for receipt lines after verification:

- Endpoint: `GET /inbound-invoices/{invoice_id}/barcode-labels`
- Returns print-friendly HTML, or JSON label data if the existing client print-window pattern is easier to reuse.

Labels should include:

- Material name
- Filament type and color
- SKU or barcode value
- Spool weight
- Invoice number
- Received location
- One label per received spool/unit when quantity is reasonable.

Cap generated labels to a safe limit, default 250, with env override:

- `STOCKWORKS_MAX_BATCH_LABELS`

If a receipt is not verified, the endpoint should return `400` explaining labels are available after verification.

The receipt UI should show "Print received labels" for verified receipts. The print window should use stable dimensions suitable for common small labels and avoid layout shifts.

## CSV Import And Export

Add CSV export endpoints:

- `GET /materials.csv`
- `GET /hardware.csv`

Add CSV import endpoints:

- `POST /materials/import`
- `POST /hardware/import`

CSV formats should be explicit and stable.

Materials columns:

- `name`
- `brand`
- `filament_type`
- `category`
- `color`
- `color_hex`
- `color_hexes`
- `supplier`
- `price_per_gram`
- `spool_weight_grams`
- `barcode`
- `refill_barcode`
- `notes`

Hardware columns:

- `name`
- `category`
- `merch_color`
- `merch_size`
- `merch_style`
- `merch_sku`
- `supplier`
- `manufacturer_part_number`
- `unit_of_measure`
- `unit_cost`
- `bin_location`
- `reorder_level`
- `quantity_on_hand`
- `notes`

Import behavior:

- Accept UTF-8 CSV uploads only.
- Limit upload size using the existing `STOCKWORKS_MAX_UPLOAD_BYTES`.
- Validate required fields and numeric values.
- Upsert materials by normalized `barcode` when present, else by case-insensitive `name`.
- Upsert hardware by normalized `merch_sku` when present, else by case-insensitive `name`.
- Return a summary: created count, updated count, skipped count, and row errors.
- Do not partially fail the request for row-level validation errors; process valid rows and return errors for invalid rows.

UI behavior:

- Materials and hardware screens get Export CSV and Import CSV controls.
- Import result summaries appear in the existing message/toast pattern.

## Data Flow

Receipt upload:

1. User uploads invoice.
2. Upload is validated and parsed.
3. Invoice and lines are created.
4. Audit event records actor and upload details.

Receipt verification:

1. User enters received quantities.
2. Backend compares previous and new line quantities.
3. Inventory and movements are updated.
4. Audit events record line changes and final verification.
5. UI refreshes receipt detail and enables batch label printing.

Low-stock digest:

1. User clicks send.
2. Backend checks SMTP config.
3. Backend queries low-stock filament and hardware.
4. Backend sends email and returns summary.

CSV import:

1. User uploads CSV.
2. Backend validates size, content type, headers, and row values.
3. Backend upserts valid rows and returns row-level errors.
4. UI reports the summary.

## Error Handling

- Role failures return `403`.
- Missing SMTP configuration returns `503`.
- CSV header or file encoding errors return `400`.
- CSV row validation errors return `200` with row error details if at least the file was readable.
- Batch labels for unverified receipts return `400`.
- Audit logging should happen in the same transaction as the action where possible. If the action commits, the audit event should commit.

## Testing

Use TDD for each behavior.

Test coverage should include:

- Admin and shop credential resolution.
- Shop role blocked from catalog/destructive writes.
- Shop role allowed to upload/verify receipts and log movements.
- Receipt audit events written for upload, packing slip upload, verification, and line quantity changes.
- Low-stock digest builder includes filament and hardware entries.
- SMTP sender handles missing configuration.
- CSV export includes expected columns.
- CSV import creates, updates, and reports row-level errors.
- Batch barcode label endpoint rejects unverified receipts and returns expected labels for verified receipts.

For the existing app, keep tests focused on helper functions and FastAPI route behavior where practical. The final verification must include Python compile checks and targeted tests.

## Out Of Scope

- Scheduled digest sending.
- Database-backed user management.
- Password reset or invite flows.
- OrderWorks changes.
- Full UI redesign.
- Multi-tenant permissions.
