# StockWorks Inventory App

StockWorks is a browser-based inventory tool for 3D-printing studios. It combines filament/material management, spool-level inventory tracking, stock movement logging, and a quote builder inside a single-page interface served by FastAPI. A desktop (Tkinter) client is still available for operators who prefer an offline UI, and the underlying REST API remains open for automation.

## Highlights
- **Web UI at `http://localhost:8000/`** - manage filament, hardware, movements, and quotes visually with no external tooling.
- **Persistent data** in `stockworks/data/` locally (or the directory you mount to `/data` inside the container) so every surface points to the same SQLite database.
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
3. Open [http://localhost:8000/](http://localhost:8000/) to use the GUI; the dashboard now covers filament spools, hardware bins, movement logs, and quoting - all powered by the same API.

### Docker Compose (alternative runtime)
From the repository root (the directory that contains `docker-compose.yml`), run:
```bash
docker compose up --build
```
The compose file builds the image, maps port `8000`, and mounts `stockworks/data/` to `/data` so your SQLite database persists between container restarts. Stop it with `docker compose down`. Override configuration with standard environment variables (`PUID`, `PGID`, `STOCKWORKS_DATA_DIR`, `DATABASE_URL`, etc.) via `.env` or `-e` flags.

### Manual Docker build/run
```bash
docker build -t stockworks ./stockworks
docker run \
  -p 8000:8000 \
  -e PUID=$(id -u) \
  -e PGID=$(id -g) \
  -v $(pwd)/stockworks/data:/data \
  stockworks
```

### Container configuration
The container understands the following environment settings:

- `PUID` / `PGID` - Linux user and group IDs used to run the process (defaults to `1000`/`1000`). Set these to match your Unraid user so `/data` permissions stay correct.
- `TZ` - Timezone string such as `UTC`, `America/New_York`, etc. Used for log timestamps.
- `STOCKWORKS_DATA_DIR` - Directory inside the container for SQLite storage. Defaults to `/data` in Docker (and `./data` when running natively).
- `STOCKWORKS_DB_FILENAME` - Name of the SQLite file within the data directory (default `app.db`).
- `DATABASE_URL` - Optional override if you want to use PostgreSQL/MySQL instead of SQLite. When omitted we build `sqlite:///<STOCKWORKS_DATA_DIR>/<STOCKWORKS_DB_FILENAME>`.

## Desktop GUI (optional)
The Tkinter client is still available if you prefer a native desktop workflow:
```bash
python -m app.gui
```
It reads and writes the same SQLite database as the web version, so you can mix and match.

## Deploy on Unraid
StockWorks now follows the Unraid-friendly conventions (`/data`, `PUID`/`PGID`, `TZ`) and ships with a community-app style template in `deploy/unraid/stockworks.xml`.

1. Clone this repository on your workstation (or onto the Unraid server) and build/push the image you want the array to pull. A local build looks like `docker build -t stockworks ./stockworks`. Push it to your registry if you prefer to pull from another machine.
2. Copy `deploy/unraid/stockworks.xml` into `/boot/config/plugins/dockerMan/templates-user/` on Unraid (or import it via the Docker tab). Update the `<Repository>` field in the template if you pushed the image under a different tag.
3. In the Unraid UI go to the **Docker** tab, click **Add Container**, and pick the StockWorks template.
4. Point the `/data` container path at the share you want to persist the SQLite database (for example `/mnt/user/appdata/stockworks`). Adjust `PUID`, `PGID`, and `TZ` if necessary.
5. Apply the template. The web UI will be available at `http://SERVER_IP:8000/` and the OpenAPI docs at `http://SERVER_IP:8000/docs`.

## API & configuration
- Base URL: `http://localhost:8000`
- Docs/Playground: `http://localhost:8000/docs`
- Environment variables: `DATABASE_URL`, `STOCKWORKS_DATA_DIR`, `STOCKWORKS_DB_FILENAME`, `PUID`, `PGID`, `TZ` (see above).

Run tests or formatting tools of your choice as needed.
