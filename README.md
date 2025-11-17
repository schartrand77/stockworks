# StockWorks Inventory Service

StockWorks is a FastAPI-powered backend used to control inventory, stock movements, and quoting for a 3D printing service. It exposes endpoints for managing raw materials, tracking spool inventory, logging every movement, and generating customer-facing price estimates.

## Features
- CRUD endpoints for filament materials with cost and supplier metadata.
- Inventory management for each spool/location with reorder levels and custom cost overrides.
- Stock movement tracking (incoming, outgoing, adjustments) that automatically updates on-hand quantities.
- Quoting endpoint that combines material cost, machine time, labor, and margin into a detailed breakdown.
- Dockerized for repeatable deployments.

## Getting Started
### Option A: Docker Compose (recommended)
```bash
docker compose up --build
```
The compose file builds the image, maps port `8000`, and mounts `data/` as a persistent SQLite volume. Stop it with `docker compose down`.

Override configuration with standard environment variables (for example `DATABASE_URL`) by adding them to a `.env` file or passing `-e` flags when running `docker compose`.

### Option B: Manual Docker build/run
1. Build the image:
   ```bash
   docker build -t stockworks .
   ```
2. Run the container:
   ```bash
   docker run -p 8000:8000 -v $(pwd)/data:/app/data stockworks
   ```
   Mounting the `data/` directory keeps the SQLite database persistent on the host.

### Explore the API
The FastAPI docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

Example requests using `curl`:
```bash
# Create a material
curl -X POST http://localhost:8000/materials \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "PLA - Black",
    "filament_type": "PLA",
    "color": "Black",
    "price_per_gram": 0.05,
    "spool_weight_grams": 1000
  }'

# Create an inventory spool based on that material (material_id=1)
curl -X POST http://localhost:8000/inventory \
  -H 'Content-Type: application/json' \
  -d '{
    "material_id": 1,
    "location": "Rack A - Bin 1",
    "quantity_grams": 750,
    "reorder_level": 200
  }'

# Log a movement (consuming 50 g for a job)
curl -X POST http://localhost:8000/movements \
  -H 'Content-Type: application/json' \
  -d '{
    "inventory_item_id": 1,
    "movement_type": "outgoing",
    "change_grams": -50,
    "reference": "JOB-1001"
  }'

# Request a quote
curl -X POST http://localhost:8000/pricing/quote \
  -H 'Content-Type: application/json' \
  -d '{
    "material_id": 1,
    "weight_grams": 120,
    "print_time_hours": 6,
    "machine_hour_rate": 12,
    "labor_cost": 8,
    "margin_pct": 35
  }'
```

## Configuration
- `DATABASE_URL`: optional custom database URL. Defaults to `sqlite:///data/app.db`.
- All endpoints accept and return JSON payloads documented via the `/docs` OpenAPI schema.

## Development
Install dependencies and launch the server locally:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run tests or formatting tools of your choice as needed.
