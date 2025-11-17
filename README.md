# StockWorks Inventory App

StockWorks is a browser-based inventory tool for 3D-printing studios. It combines filament/material management, spool-level inventory tracking, stock movement logging, and a quote builder inside a single-page interface served by FastAPI. A desktop (Tkinter) client is still available for operators who prefer an offline UI, and the underlying REST API remains open for automation.

## Highlights
- **Web UI at `http://localhost:8000/`** – manage filament, hardware, movements, and quotes visually with no external tooling.
- **Persistent data** in `stockworks/data/app.db` (SQLite) that is shared across the web UI, API, and optional desktop client.
- **Hardware coverage** for magnets, heat-set inserts, screws, and any other non-filament consumables, including movement history.
- **Full REST API** for integrations, automation, or bulk operations. Swagger docs live at `/docs`.
- **Optional desktop GUI** (`python -m app.gui`) built with Tkinter for teams that want a native-feeling app.

## Run the web application
1. Create/activate a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate        # Windows PowerShell
   # source .venv/bin/activate     # macOS/Linux
   pip install -r requirements.txt
   ```
2. Launch the FastAPI app (which now serves the SPA and the REST endpoints):
   ```bash
   uvicorn app.api:app --reload
   ```
3. Open [http://localhost:8000/](http://localhost:8000/) to use the GUI; the dashboard now covers filament spools, hardware bins, movement logs, and quoting – all powered by the same API.

### Docker Compose (alternative runtime)
From the repository root (the directory that contains `docker-compose.yml`), run:
```bash
docker compose up --build
```
The compose file builds the image, maps port `8000`, and mounts `stockworks/data/` as a persistent SQLite volume. Stop it with `docker compose down`. Override configuration with standard environment variables (for example `DATABASE_URL`) via `.env` or `-e` flags.

### Manual Docker build/run
```bash
docker build -t stockworks .
docker run -p 8000:8000 -v $(pwd)/stockworks/data:/app/data stockworks
```

## Desktop GUI (optional)
The Tkinter client is still available if you prefer a native desktop workflow:
```bash
python -m app.gui
```
It reads and writes the same SQLite database as the web version, so you can mix and match.

## API & configuration
- Base URL: `http://localhost:8000`
- Docs/Playground: `http://localhost:8000/docs`
- `DATABASE_URL`: optional override. Defaults to `sqlite:///data/app.db`.

Run tests or formatting tools of your choice as needed.
