# fuellog

A small self-hosted web app for tracking the fuel consumption and running
costs of your household's vehicles. Log a fill-up in a few taps on your phone
and get average consumption, range, cost per kilometre and a monthly spending
chart per vehicle.

Runs as a single Docker container. All data lives in one SQLite file, so a
backup is just a file copy.

<!-- Add screenshots to docs/screenshots/ and link them here. -->

## Features

- **Vehicle tiles** on the home screen with live key figures per car
- **Dashboard** per vehicle: average consumption (L/100 km), range on a full
  tank, cost per km, total spent, average price per litre, monthly spending chart
- **Guided fill-up entry** – a step-by-step form on mobile, a flat form when editing
- **Automatic estimates** for missing values, clearly marked and correctable:
  - exact derivation of litres / price / amount when two of the three are known (`Σ`)
  - approximation of a missing odometer reading or litre amount from neighbouring
    readings and the average consumption (`≈`)
- **Odometer-only entries** for readings taken without a fill-up (improves accuracy)
- **Station autocomplete** from your own history, optionally enriched with
  OpenStreetMap suggestions and a minimap
- **CSV import & export** for backups and migrating existing spreadsheets
- **English and German** UI, **configurable currency**, **light/dark mode**
- **Multi-user**: one admin account created on first launch, more users addable;
  everyone shares the same vehicles

## Quick start (Docker Compose)

```yaml
services:
  fuellog:
    image: ghcr.io/jonasmapache/fuellog:latest
    container_name: fuellog
    restart: unless-stopped
    ports:
      - "8562:8000"
    environment:
      - TZ=Europe/Berlin
    volumes:
      - ./data:/data
```

```bash
docker compose up -d
```

Open `http://<host>:8562`, create the administrator account, add a vehicle and
log your first fill-up. That's it – no environment variables are required.

## Unraid

**Community Applications template:** add
`https://raw.githubusercontent.com/jonasmapache/fuellog/main/unraid/fuellog.xml`
as a template repository (Settings → Community Applications), or import
[`unraid/fuellog.xml`](unraid/fuellog.xml) manually. Map `/data` to
`/mnt/user/appdata/fuellog` and set the WebUI port.

**Compose Manager:** paste the compose file above. Compose Manager stores the
stack outside `/mnt/user/appdata`, so prefer an **absolute** volume path:

```yaml
    volumes:
      - /mnt/user/appdata/fuellog/data:/data
```

### Reverse proxy

Point a proxy host (e.g. Nginx Proxy Manager) at the container on port `8000`.
No WebSocket support is required. If you always serve over HTTPS, set
`SESSION_HTTPS_ONLY=true` so the session cookie is marked `Secure`.

## Configuration

Everything except the data volume is optional.

| Variable             | Default              | Purpose |
|----------------------|----------------------|---------|
| `TZ`                 | `UTC`                | Container timezone; also the default "today" on the entry form (can be overridden in Settings). |
| `APP_DEFAULT_LANG`   | `en`                 | Fallback UI language (`en` / `de`) until one is chosen in Settings. |
| `SECRET_KEY`         | *(generated)*        | Session signing key. If unset, a random key is generated once and stored at `/data/secret_key`. |
| `SESSION_HTTPS_ONLY` | `false`              | Mark the session cookie `Secure` (set when always behind HTTPS). |
| `DATA_DIR`           | `/data`              | Where the database, photos and secret key live. |
| `DATABASE_URL`       | `sqlite:///<DATA_DIR>/fuellog.db` | Override to use an external database (SQLite is the tested path). |
| `MAX_PHOTO_BYTES`    | `5242880`            | Upload size cap for vehicle photos. |

More options – language, currency symbol/position, timezone, default fuel type,
OpenStreetMap endpoints and the geocoding on/off switch – live on the in-app
**Settings** page (admin only).

## CSV format

Import and export use the same columns (see
[`docs/sample-import.csv`](docs/sample-import.csv)):

```
vehicle,date,entry_type,odometer_km,liters,price_per_liter,total_cost,fuel_type,full_tank,station,station_address,station_lat,station_lon,notes
```

- Only `vehicle` and `date` are required. `date` accepts `YYYY-MM-DD` (and a few
  common alternatives).
- `entry_type` is `fuel` or `odometer_only`; if omitted it is inferred.
- `full_tank` accepts `1/0`, `true/false`, `yes/no`.
- Numbers accept `.` or `,` as the decimal separator.
- Vehicles are matched by name and created if missing. Rows matching an existing
  entry (same vehicle + date + odometer + litres) are skipped.

## Backup

Copy the `/data` directory (or `data/` next to your compose file). It contains:

```
fuellog.db            SQLite database (everything)
vehicle_photos/       uploaded vehicle photos
secret_key            generated session key
```

## Development

```bash
python -m venv .venv && . .venv/Scripts/activate   # or .venv/bin/activate
pip install -r requirements.txt
export DATA_DIR=$PWD/.devdata
alembic upgrade head
uvicorn fuellog.main:app --reload
```

The stack is FastAPI + Jinja2 + SQLAlchemy + SQLite, server-rendered, with
Leaflet and Chart.js vendored under `fuellog/static/vendor/` (no front-end
build step). Schema changes go through Alembic (`alembic revision --autogenerate`).

## License

MIT – see [LICENSE](LICENSE).
