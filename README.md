# StockWorks Inventory App

StockWorks is now a standalone desktop application for managing filament materials, tracking inventory per spool/location, logging movements, and producing quick price quotes. A FastAPI backend is still provided for automation or integrations, but the primary experience is a Tkinter GUI.

## Features
- Visual material catalog with supplier/brand metadata and free-form notes.
- Inventory editor that keeps quantities, reorder points, and spool metadata in sync with a persistent SQLite database.
- Movement logging (incoming, outgoing, adjustments) with immediate impact on quantity and a built-in audit trail.
- Quote builder that calculates price breakdowns based on material usage, machine time, labor, and margin.
- Optional FastAPI service (via Docker or uvicorn) to integrate with other systems.

## Desktop App (default experience)
1. Create/activate a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate        # Windows PowerShell
   # source .venv/bin/activate     # macOS/Linux
   pip install -r requirements.txt
   ```
2. Launch the GUI:
   ```bash
   python -m app.main
   ```
   The app stores data at `stockworks/data/app.db` by default so your changes persist between sessions.

## Optional FastAPI service
If you still need the HTTP API (for integrations or remote access) you can run the same backend the GUI uses.

### Docker Compose (recommended)
From the repository root (the directory that contains `docker-compose.yml`), run:
```bash
docker compose up --build
```
The compose file builds the image, maps port `8000`, and mounts `stockworks/data/` as a persistent SQLite volume. Stop it with `docker compose down`.

Override configuration with standard environment variables (for example `DATABASE_URL`) by adding them to a `.env` file or passing `-e` flags when running `docker compose`.

### Manual Docker build/run
1. Build the image:
   ```bash
   docker build -t stockworks .
   ```
2. Run the container:
   ```bash
   docker run -p 8000:8000 -v $(pwd)/stockworks/data:/app/data stockworks
   ```
   Mounting the `stockworks/data/` directory keeps the SQLite database persistent on the host.

### Local uvicorn
```bash
uvicorn app.api:app --reload
```
Interactive docs remain available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Configuration
- `DATABASE_URL`: optional custom database URL. Defaults to `sqlite:///data/app.db`.
- GUI and API read the same configuration and share the same database file.

Run tests or formatting tools of your choice as needed.
