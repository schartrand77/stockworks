# StockWorks - Everyday User Manual

StockWorks is a simple tool for keeping track of materials in a 3D printing shop. It helps you see what you have, what is running low, and what jobs are coming in from MakerWorks and OrderWorks.

If you can use a web page, you can use StockWorks.

## Quick start
1) Open a web browser.
2) Go to `http://localhost:8000/`
3) The main screen opens right away.

If nothing opens, ask your admin to start StockWorks.

## What StockWorks can do
- **Track filament spools**: color, material, remaining weight.
- **Track hardware**: screws, inserts, magnets, and other parts.
- **Show stock changes**: every add and remove is recorded.
- **Create quotes**: build a material list and price estimate.
- **Show incoming jobs**: live orders from MakerWorks and OrderWorks.

## The main screens (what they mean)
- **Dashboard**: a quick summary of items that need attention.
- **Filament**: all spools and their remaining amounts.
- **Hardware**: all non-filament items and quantities.
- **Movements**: a history of changes so you can see who did what and when.
- **Quotes**: tools for pricing and estimating materials.
- **Orders**: the live job queue from MakerWorks and OrderWorks.

## Barcode scanning on mobile
StockWorks can scan barcodes using your phone or tablet camera.

How it works:
- Open StockWorks on your mobile browser.
- In the Materials or Inventory forms, tap the barcode scan button.
- Grant camera access when prompted.
- Point the camera at the barcode; the value fills in automatically.

Notes:
- Camera scanning requires HTTPS (or localhost). If it does not open the camera, ask your admin to enable HTTPS.
- If your device does not support scanning, you can still type the barcode manually.

## Screenshots
These pictures show what the main screens look like.

### Inventory
![StockWorks inventory screen](public/screenshots/swinventory.png)

### Materials
![StockWorks materials screen](public/screenshots/swmaterials.png)

### Reports
![StockWorks reports screen](public/screenshots/swreports.png)

## Using the Orders screen (MakerWorks and OrderWorks)
The Orders screen shows the job list so production and inventory stay in sync.

### How StockWorks gets the orders
There are two ways your admin can connect StockWorks:

1) **Direct database link (best option)**
   - StockWorks reads the job list directly from the MakerWorks database.
   - This is automatic once it is connected.
   - The Orders screen fills in on its own.

2) **OrderWorks login (backup option)**
   - If the database connection is not available, StockWorks can log in to OrderWorks.
   - It uses an admin username and password set by your admin.

You do not need to choose these options yourself. The admin sets this up once.

### What you will see in Orders
- A list of current jobs.
- Each job may include a link to open the same order in OrderWorks.
- If something is missing, you will see a message explaining what is needed.

### If the Orders list looks wrong
Ask your admin if:
- The Orders list is empty.
- The link to OrderWorks does not open.
- The list looks out of date.

## Optional desktop window
Some teams prefer a desktop window instead of a browser tab. It is the same StockWorks, just in its own window.

If you want this, ask your admin to enable it.

## Simple tips
- Use Dashboard first if you only have a minute.
- Use Movements to answer "what changed today?"
- Use Quotes to quickly estimate material needs.

## For your admin (short, plain notes)
If you set up StockWorks:
- Open the app at `http://localhost:8000/`
- Data is stored in `stockworks/data/`
- Orders integration needs either:
  - A MakerWorks database link, or
  - OrderWorks login details and the OrderWorks web address

If you need full technical setup steps, ask the development team for the full admin guide.
