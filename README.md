# StockWorks Inventory App - Simple User Manual

StockWorks keeps track of materials for a 3D-printing shop. You can record filament spools, small hardware (screws, inserts, magnets), and every stock movement. It also shows a live list of jobs from MakerWorks/OrderWorks so the production team and inventory team stay in sync.

## What you need to know
- StockWorks runs in a web browser.
- Your data is stored in one place on this computer (a small database file).
- You can use the web app, and there is also an optional desktop app.

## Open StockWorks
If StockWorks is already running, open your browser and go to:
`http://localhost:8000/`

If it is not running yet, ask whoever set it up to start it. You do not need to install anything yourself unless you are the admin.

## Main screens (plain language)
- **Dashboard**: quick view of what is low or needs attention.
- **Filament**: list of spools, colors, and remaining weight.
- **Hardware**: bins of screws, inserts, magnets, and other non-filament items.
- **Movements**: every add/remove action so you can see what changed and when.
- **Quotes**: tools for creating a quote from materials.
- **Orders**: job list pulled from MakerWorks/OrderWorks when integration is on.

## MakerWorks and OrderWorks integration
StockWorks can show the job queue from MakerWorks/OrderWorks so you can see what is coming and plan inventory.

### How it works (two options)
1) **Direct database link (best option)**
   - StockWorks reads the job list directly from the MakerWorks database.
   - This is automatic once the admin points StockWorks to the same database that OrderWorks uses.
   - When this is set, the **Orders** tab fills in on its own.

2) **OrderWorks login (backup option)**
   - If StockWorks cannot reach the MakerWorks database, it can log into OrderWorks and read jobs through the OrderWorks API.
   - This requires an OrderWorks admin username and password set up by the admin.

### What you will see
- The **Orders** tab shows the live job list.
- Each order can include a link that opens the same job in OrderWorks (if the admin provided the OrderWorks web address).
- If you do not have access to MakerWorks/OrderWorks, the Orders tab will explain what is missing.

### When to contact the admin
Ask your admin if:
- The Orders tab is empty or shows a message about missing access.
- Order links do not open.
- You believe the job list is not up to date.

## Optional desktop app
Some teams prefer a desktop window instead of a browser. It uses the same data as the web app.

If your admin enabled it, they can start it with:
`python -m app.gui`

## For the admin (short notes)
If you are the person who sets up StockWorks:
- Web app runs at `http://localhost:8000/`.
- Data lives in `stockworks/data/` by default.
- Orders integration needs either:
  - `DATABASE_URL` pointing to the MakerWorks database, or
  - OrderWorks login credentials and base URL for API access.

If you need the detailed technical setup steps, check earlier versions of this README or the project documentation.
