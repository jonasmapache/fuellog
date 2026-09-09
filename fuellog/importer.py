"""CSV import of fuel entries.

Format: see ``exporter.CSV_COLUMNS``. Only ``vehicle`` and ``date`` are
required; everything else may be blank. Vehicles are matched by name and
created on demand. Rows that duplicate an existing entry
(same vehicle + date + odometer + liters) are skipped.
"""
import csv
import io
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from .estimation import recompute_vehicle
from .models import FuelEntry, Station, Vehicle
from .parsing import parse_date, parse_decimal

_TRUE = {"1", "true", "yes", "y", "x", "wahr", "ja"}
_FALSE = {"0", "false", "no", "n", "falsch", "nein"}


@dataclass
class ImportResult:
    created: int = 0
    skipped: int = 0
    vehicles_created: list[str] = field(default_factory=list)


class ImportError_(ValueError):
    """Raised for a structurally invalid file."""


def _parse_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    s = str(value).strip().lower()
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    return default


def _get_or_create_vehicle(db: Session, cache: dict, name: str, result: ImportResult) -> Vehicle:
    key = name.strip().lower()
    if key in cache:
        return cache[key]
    vehicle = db.query(Vehicle).filter(Vehicle.name == name.strip()).first()
    if vehicle is None:
        vehicle = Vehicle(name=name.strip(), sort_order=-(db.query(Vehicle).count()))
        db.add(vehicle)
        db.flush()
        result.vehicles_created.append(vehicle.name)
    cache[key] = vehicle
    return vehicle


def _get_or_create_station(db: Session, cache: dict, name: str, address, lat, lon) -> Station | None:
    name = (name or "").strip()
    if not name:
        return None
    key = name.lower()
    if key in cache:
        return cache[key]
    station = db.query(Station).filter(Station.name == name).first()
    if station is None:
        station = Station(
            name=name,
            address=(str(address).strip() or None) if address else None,
            lat=parse_decimal(lat),
            lon=parse_decimal(lon),
        )
        db.add(station)
        db.flush()
    cache[key] = station
    return station


def import_csv(db: Session, text: str) -> ImportResult:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ImportError_("empty file")
    fields = {(f or "").strip().lower() for f in reader.fieldnames}
    if "vehicle" not in fields or "date" not in fields:
        raise ImportError_("missing required columns 'vehicle' and 'date'")

    result = ImportResult()
    vehicle_cache: dict[str, Vehicle] = {}
    station_cache: dict[str, Station] = {}
    touched: set[int] = set()

    for raw in reader:
        row = {(k or "").strip().lower(): v for k, v in raw.items()}
        vehicle_name = (row.get("vehicle") or "").strip()
        entry_date = parse_date(row.get("date"))
        if not vehicle_name or entry_date is None:
            result.skipped += 1
            continue

        vehicle = _get_or_create_vehicle(db, vehicle_cache, vehicle_name, result)

        liters = parse_decimal(row.get("liters"))
        price = parse_decimal(row.get("price_per_liter"))
        total = parse_decimal(row.get("total_cost"))
        odo = parse_decimal(row.get("odometer_km"))

        entry_type = (row.get("entry_type") or "").strip().lower()
        if entry_type not in {"fuel", "odometer_only"}:
            entry_type = "odometer_only" if (liters is None and price is None and total is None) else "fuel"
        if entry_type == "odometer_only":
            liters = price = total = None

        exists = (
            db.query(FuelEntry.id)
            .filter(
                FuelEntry.vehicle_id == vehicle.id,
                FuelEntry.date == entry_date,
                FuelEntry.odometer_km == odo,
                FuelEntry.liters == liters,
            )
            .first()
        )
        if exists:
            result.skipped += 1
            continue

        station = _get_or_create_station(
            db, station_cache,
            row.get("station"), row.get("station_address"),
            row.get("station_lat"), row.get("station_lon"),
        )

        db.add(FuelEntry(
            vehicle_id=vehicle.id,
            entry_type=entry_type,
            date=entry_date,
            liters=liters,
            price_per_liter=price,
            total_cost=total,
            odometer_km=odo,
            fuel_type=(row.get("fuel_type") or "").strip() or None,
            full_tank=_parse_bool(row.get("full_tank"), default=True),
            station_id=station.id if station else None,
            notes=(row.get("notes") or "").strip() or None,
        ))
        result.created += 1
        touched.add(vehicle.id)

    db.flush()
    for vehicle_id in touched:
        entries = db.query(FuelEntry).filter(FuelEntry.vehicle_id == vehicle_id).all()
        recompute_vehicle(entries)

    # Rough tank-size estimate for vehicles created during this import, so the
    # range figure works out of the box (still editable in the vehicle settings).
    created_names = set(result.vehicles_created)
    for vehicle in vehicle_cache.values():
        if vehicle.name not in created_names or vehicle.tank_capacity_l:
            continue
        fills = [
            e.liters for e in vehicle.entries
            if e.entry_type == "fuel" and e.full_tank and e.liters
        ]
        if fills:
            vehicle.tank_capacity_l = round(max(fills) * 1.1)

    db.commit()
    return result
