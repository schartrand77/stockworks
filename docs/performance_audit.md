# StockWorks performance and memory audit

Date: 2026-02-17
Scope: `app/` backend (FastAPI + SQLModel) and `app/static/app.js` frontend runtime behavior.

## Executive summary

StockWorks is functionally solid, but there are several high-impact opportunities to reduce CPU time, payload size, and browser memory churn:

1. **Frontend refresh fan-out causes repeated report recomputation** (high impact): `refreshAll()` calls 6 loaders concurrently, and each loader calls `renderReports()` again. This multiplies DOM work and chart rendering during each refresh.
2. **Large-list endpoints return unbounded rows** (high impact): `/materials`, `/inventory`, `/hardware`, and `/models` currently return full tables, which scales poorly as records grow.
3. **Potential N+1 relationship loading for inventory/material reads** (medium-high): response models include nested objects, but list queries do not use eager loading options.
4. **Frequent full-table filtering/sorting in browser** (medium): filtering and sorting are repeated on each render for each tab, which is expensive at larger data volumes.
5. **Schema/index hygiene can improve query latency** (medium): fields commonly used for sort/search/filter are not consistently indexed.

---

## Findings and targeted improvements

## 1) Frontend report rendering is duplicated during refresh

### Evidence
- `refreshAll()` runs multiple loaders in parallel. Each loader (`loadMaterials`, `loadInventory`, `loadModels`, `loadHardware`) calls `renderReports()` internally. This can trigger multiple report redraws per single refresh action.

### Recommendation
- Add a `suppressReports` option to each loader, then run a single `renderReports()` once all data loads complete.
- If charts are expensive, debounce report rendering (e.g., 100–200 ms trailing).

### Expected impact
- Less UI jank and lower browser CPU on refresh.
- Reduced short-lived memory allocations from repeated DOM string rebuilds.

## 2) Unbounded list APIs will degrade with dataset growth

### Evidence
- List endpoints return all rows (`/materials`, `/inventory`, `/hardware`, `/models`) with no pagination/limit parameters.

### Recommendation
- Add `limit`, `offset`, and optional `search` query parameters on list endpoints.
- Return envelope metadata: `{items, total, limit, offset}`.
- Keep server-side sorting stable by indexed columns.

### Expected impact
- Faster initial loads and lower network transfer.
- Lower memory use on both API worker and browser for large datasets.

## 3) Relationship loading strategy may create N+1 behavior

### Evidence
- `InventoryItemRead` includes nested `material` while list query is `select(InventoryItem)` with no eager loading hint.

### Recommendation
- Use SQLAlchemy loader options (`selectinload(InventoryItem.material)`) for list endpoints that serialize nested relations.
- For heavy list views, create lightweight DTOs that avoid nested object serialization unless requested.

### Expected impact
- Fewer DB round trips under relational serialization.
- Lower endpoint tail latency at medium-large inventory size.

## 4) Browser performs repeated full-array filter/sort and table HTML regeneration

### Evidence
- Filtering and sorting helpers repeatedly scan full arrays before every render.
- Table rendering uses `innerHTML` string replacement for whole table bodies.

### Recommendation
- Cache derived view-models keyed by filter/sort/pagination state.
- Use incremental row patching for common updates (single-item edit/delete) instead of full rebuild.
- For very large tables (>2k rows), add viewport virtualization.

### Expected impact
- Reduced main-thread work, better responsiveness, and less GC pressure.

## 5) DB tuning/indexing opportunities

### Evidence
- Commonly queried columns (name/category/sort fields, movement timestamp foreign keys) are not all explicitly indexed.
- SQLite mode does not set WAL or other read/write performance PRAGMAs.

### Recommendation
- Add indexes for hot paths, e.g.:
  - `material(name)`
  - `inventoryitem(material_id, location)`
  - `stockmovement(inventory_item_id, created_at)`
  - `hardwareitem(category, name)`
  - `hardwaremovement(hardware_item_id, created_at)`
  - `printmodelsale(model_id, sold_at)`
- In SQLite deployments, set:
  - `PRAGMA journal_mode=WAL`
  - `PRAGMA synchronous=NORMAL`
  - `PRAGMA temp_store=MEMORY`

### Expected impact
- Faster sort/filter and movement-history queries.
- Better concurrent read/write behavior on SQLite.

---

## Suggested feature upgrades (performance-oriented)

1. **Background sync pipeline for integrations**
   - Move OrderWorks/Bambu sync to scheduled background tasks with cached snapshots.
   - API/UI reads from local cache table to avoid blocking user requests on external services.

2. **Materialized reporting tables**
   - Precompute daily usage, low-stock alerts, and model sales summaries.
   - Incrementally update via movement/sales inserts.

3. **HTTP caching and conditional requests**
   - Add `ETag`/`Last-Modified` support on list endpoints.
   - Client can skip payload transfer when unchanged.

4. **Observability baseline**
   - Add request timing middleware and slow-query logging.
   - Emit p50/p95 per endpoint and DB query counts to logs.

5. **Scale-ready API contracts**
   - Introduce cursor pagination for movements and jobs endpoints.
   - Add selective field expansion (`?include=material`) to control payload size.

---

## Quick-win implementation order

1. Single-pass `renderReports()` in frontend refresh path.
2. Pagination on all list endpoints + UI paging integration.
3. Eager loading and lightweight response models for list views.
4. Add indexes/migrations for movement and name/category fields.
5. Background cached sync for external integrations.

