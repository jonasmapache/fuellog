"""CSV export of every fuel entry (portable backup / migration format)."""
import csv
import io

from sqlalchemy.orm import Session

from .models import FuelEntry, Vehicle

CSV_COLUMNS = [
    "vehicle", "date", "entry_type", "odometer_km", "liters", "price_per_liter",
    "total_cost", "fuel_type", "full_tank", "station", "station_address",
    "station_lat", "station_lon", "notes",
]


def _num(value) -> str:
    return "" if value is None else f"{value:g}"


def export_csv(db: Session) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)

    entries = (
        db.query(FuelEntry)
        .join(Vehicle)
        .order_by(Vehicle.name, FuelEntry.date, FuelEntry.id)
        .all()
    )
    for e in entries:
        st = e.station
        writer.writerow([
            e.vehicle.name,
            e.date.isoformat(),
            e.entry_type,
            _num(e.odometer_km),
            _num(e.liters),
            _num(e.price_per_liter),
            _num(e.total_cost),
            e.fuel_type or "",
            "1" if e.full_tank else "0",
            st.name if st else "",
            (st.address or "") if st else "",
            _num(st.lat) if st else "",
            _num(st.lon) if st else "",
            (e.notes or "").replace("\r", " ").replace("\n", " ").strip(),
        ])
    return buf.getvalue()
