# StockWorks - Everyday User Manual

StockWorks is a simple tool for keeping track of materials in a 3D printing shop. It helps you see what you have, what is running low, and what jobs are coming in from MakerWorks.

If you can use a web page, you can use StockWorks.

## Suite demo walkthrough

StockWorks participates in the MakerWorks suite demo as the inventory and material-intelligence app. The walkthrough uses synthetic sample data to show inventory levels, material reservations, hardware/merch stock, reporting, and incoming MakerWorks demand.

The screenshots below are safe public demo captures. They do not contain real customer records, private inventory counts, production URLs, or secrets.

### Inventory planning

![StockWorks inventory with synthetic sample stock](docs/assets/suite-screenshots/stockworks-02-inventory.png)

### Material transactions

![StockWorks movement history with synthetic transactions](docs/assets/suite-screenshots/stockworks-04-movements.png)

### Hardware and reports

![StockWorks hardware and merch inventory](docs/assets/suite-screenshots/stockworks-03-hardware.png)

![StockWorks synthetic reporting dashboard](docs/assets/suite-screenshots/stockworks-06-reports.png)

## Quick start
1) Open a web browser.
2) Go to `http://localhost:8000/`
3) The main screen opens right away.


## What StockWorks can do
- **Track filament spools**: color, material, remaining weight.
- **Track hardware**: screws, inserts, magnets, and other parts.
- **Sync merch from MakerWorks**: import merch templates, then keep quantity/catalog updates synced with MakerWorks.
- **Show stock changes**: every add and remove is recorded.
- **Create quotes**: build a material list and price estimate.
- **Show incoming jobs**: live orders from MakerWorks.

## The main screens (what they mean)
- **Dashboard**: a quick summary of items that need attention.
- **Filament**: all spools and their remaining amounts.
- **Hardware**: all non-filament items and quantities.
- **Movements**: a history of changes so you can see who did what and when.
- **Quotes**: tools for pricing and estimating materials.
- **Orders**: the live job queue from MakerWorks.

## Barcode scanning on mobile
StockWorks can scan barcodes using your phone or tablet camera.

How it works:
- Open StockWorks on your mobile browser.
- In the Materials, Inventory, or Stock Movements forms, tap the barcode scan button.
- Grant camera access when prompted.
- Point the camera at the barcode; the value fills in automatically.

Notes:
- Camera scanning requires HTTPS (or localhost).

## Screenshots
These pictures show what the main screens look like.

### Inventory
![StockWorks inventory screen](public/screenshots/swinventory.png)

### Materials
![StockWorks materials screen](public/screenshots/swmaterials.png)

### Reports
![StockWorks reports screen](public/screenshots/swreports.png)

## Using the Orders screen
The Orders screen shows the job list so production and inventory stay in sync.

### How StockWorks gets the orders
StockWorks reads the job list directly from the MakerWorks Postgres database.
This is automatic once `DATABASE_URL` points at the MakerWorks database.


### What you will see in Orders
- A list of current jobs.
- If something is missing, you will see a message explaining what is needed.

## Unraid MakerWorks database setup
When StockWorks runs on Unraid with MakerWorks, put the StockWorks container on the
same Docker network as the MakerWorks Postgres container. Use the Postgres
container name in the URL, not `localhost`.

For the common MakerWorks database container named `postgres`, set:

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/makerworks?schema=public
STOCKWORKS_DB_SCHEMA=
```

`DATABASE_URL` points StockWorks at the MakerWorks Postgres database. The
`?schema=public` value means StockWorks uses the existing `public` schema for its
own inventory tables and can also read MakerWorks public tables.

If your StockWorks inventory tables were previously created in another schema,
set `STOCKWORKS_DB_SCHEMA` to that schema. For example, if an older install used
a legacy schema name:

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/makerworks?schema=legacy_schema_name
STOCKWORKS_DB_SCHEMA=legacy_schema_name
```

For current MakerWorks/StockWorks installs, prefer `public` unless you confirm
your existing StockWorks rows are in another schema. `STOCKWORKS_DB_SCHEMA`
controls where StockWorks-owned tables such as `material`, `inventoryitem`, and
`hardwareitem` live.

To check where existing StockWorks tables are before reinstalling, run this in
the MakerWorks Postgres database:

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_name IN (
  'material',
  'inventoryitem',
  'stockmovement',
  'hardwareitem',
  'hardwaremovement',
  'printmodel',
  'printmodelsale',
  'printmodelmovement',
  'jobs'
)
ORDER BY table_schema, table_name;
```

Use the schema that contains the current StockWorks data. If multiple schemas
have StockWorks tables, compare row counts:

```sql
SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
WHERE relname IN (
  'material',
  'inventoryitem',
  'stockmovement',
  'hardwareitem',
  'hardwaremovement',
  'printmodel',
  'printmodelsale',
  'printmodelmovement'
)
ORDER BY schemaname, relname;
```

Also set a real session secret. StockWorks will not start if `SECRET_KEY` is
shorter than 32 characters:

```env
SECRET_KEY=replace-with-a-random-32-plus-character-secret
```

## PrintLab filament sync (loaded trays)
StockWorks can also read loaded AMS trays from PrintLab so you can quickly see what filament is currently mounted.

Set these variables if you want that integration:
- `PRINTLAB_BASE_URL` (required for PrintLab sync)
- `PRINTLAB_API_KEY` (optional, if PrintLab API auth is enabled)
- `PRINTLAB_BEARER_TOKEN` (optional bearer auth token)
- `PRINTLAB_API_AUTH_HEADER` (defaults to `X-API-Key`)

The loaded tray list appears in **Settings > PrintLab**.

## MakerWorks merch sync
If MakerWorks merch has been enabled, open **Hardware** and click **Sync MakerWorks merch**.

What this does:
- Pulls merch templates from MakerWorks `ProductTemplate`.
- Creates or updates matching Hardware records in StockWorks.
- Sets category to `merch` and maps quantity/reorder fields when those columns exist in MakerWorks.
- Writes merch quantity changes (and merch item edits) back to MakerWorks `ProductTemplate` for linked merch items.
- For merch variants (same item/style/color with different sizes), StockWorks writes all sibling variant quantities so MakerWorks size availability stays accurate (e.g., only `L` in stock means other sizes are sold out).
- New merch created in StockWorks is also created in MakerWorks `ProductTemplate` automatically (catalog image remains unset until added in MakerWorks).

You can manage merch directly in the **Merch** tab (add, edit, delete) and use the dedicated inventory search bar.
Merch records support variant details such as category, color, size, style, and SKU.

## Simple tips
- Use Dashboard first if you only have a minute.
- Use Movements to answer "what changed today?"
- Use Quotes to quickly estimate material needs.

## For your admin (short, plain notes)
If you set up StockWorks:
- Open the app at `http://localhost:8000/`
- Data is stored in `stockworks/data/`
- Orders integration needs a MakerWorks database link

