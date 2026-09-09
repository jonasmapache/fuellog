"""Create / edit / delete a fuel entry (or odometer-only reading)."""
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import require_user
from ..clock import today_in
from ..database import get_db
from ..estimation import recompute_vehicle
from ..models import FuelEntry, Station, User, Vehicle
from ..parsing import parse_decimal
from ..security import csrf_protect
from ..settings_service import get_settings
from ..templating import render
from .vehicles import FUEL_TYPES

router = APIRouter(dependencies=[Depends(csrf_protect)])


def _entry_form_ctx(request: Request, db: Session, vehicle: Vehicle, entry: FuelEntry | None):
    settings = get_settings(db)
    stations = db.query(Station).order_by(Station.usage_count.desc()).limit(200).all()
    return {
        "vehicle": vehicle,
        "entry": entry,
        "today": today_in(settings.timezone).isoformat(),
        "fuel_types": FUEL_TYPES,
        "default_fuel_type": settings.default_fuel_type,
        "stations_json": [
            {"name": s.name, "address": s.address, "lat": s.lat, "lon": s.lon}
            for s in stations
        ],
    }


def _resolve_station(db: Session, name: str, lat: str, lon: str, address: str,
                     previous_station_id: int | None) -> Station | None:
    name = (name or "").strip()
    if not name:
        return None
    station = db.query(Station).filter(Station.name == name).first()
    if station is None:
        station = Station(
            name=name,
            address=(address or "").strip() or None,
            lat=parse_decimal(lat),
            lon=parse_decimal(lon),
        )
        db.add(station)
        db.flush()
    elif station.lat is None and lat:
        station.lat = parse_decimal(lat)
        station.lon = parse_decimal(lon)
        if address:
            station.address = address
    # only count a genuinely new association, not every re-save of an entry
    if station.id != previous_station_id:
        station.usage_count = (station.usage_count or 0) + 1
    return station


def _apply_common_fields(entry: FuelEntry, *, entry_type, date_, liters, price, total,
                         odometer, fuel_type, full_tank, station, notes):
    entry.entry_type = entry_type
    entry.date = datetime.strptime(date_, "%Y-%m-%d").date()
    entry.odometer_km = parse_decimal(odometer)
    entry.fuel_type = fuel_type or None
    entry.station_id = station.id if station else None
    entry.notes = notes.strip() or None
    if entry_type == "odometer_only":
        entry.liters = entry.price_per_liter = entry.total_cost = None
        entry.full_tank = False
    else:
        entry.liters = parse_decimal(liters)
        entry.price_per_liter = parse_decimal(price)
        entry.total_cost = parse_decimal(total)
        entry.full_tank = (full_tank == "on")


def _recompute(db: Session, vehicle_id: int):
    entries = db.query(FuelEntry).filter(FuelEntry.vehicle_id == vehicle_id).all()
    recompute_vehicle(entries)


@router.get("/vehicles/{vehicle_id}/entry/new")
def new_form(vehicle_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return RedirectResponse(url="/", status_code=303)
    return render(request, db, "entry_form.html", user=user, **_entry_form_ctx(request, db, vehicle, None))


@router.get("/vehicles/{vehicle_id}/entry/{entry_id}/edit")
def edit_form(vehicle_id: int, entry_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    vehicle = db.get(Vehicle, vehicle_id)
    entry = db.get(FuelEntry, entry_id)
    if vehicle is None or entry is None or entry.vehicle_id != vehicle.id:
        return RedirectResponse(url="/", status_code=303)
    return render(request, db, "entry_form.html", user=user, **_entry_form_ctx(request, db, vehicle, entry))


@router.post("/vehicles/{vehicle_id}/entry/new")
def new_submit(
    vehicle_id: int,
    request: Request,
    entry_type: str = Form("fuel"),
    date: str = Form(...),
    liters: str = Form(""),
    price_per_liter: str = Form(""),
    total_cost: str = Form(""),
    odometer_km: str = Form(""),
    fuel_type: str = Form(""),
    full_tank: str = Form(""),
    station_name: str = Form(""),
    station_address: str = Form(""),
    station_lat: str = Form(""),
    station_lon: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return RedirectResponse(url="/", status_code=303)

    entry_type = "odometer_only" if entry_type == "odometer_only" else "fuel"
    station = _resolve_station(db, station_name, station_lat, station_lon, station_address, None)

    entry = FuelEntry(vehicle_id=vehicle.id)
    _apply_common_fields(
        entry, entry_type=entry_type, date_=date, liters=liters, price=price_per_liter,
        total=total_cost, odometer=odometer_km, fuel_type=fuel_type, full_tank=full_tank,
        station=station, notes=notes,
    )
    db.add(entry)
    db.flush()
    _recompute(db, vehicle.id)
    db.commit()
    return RedirectResponse(url=f"/vehicles/{vehicle.id}", status_code=303)


@router.post("/vehicles/{vehicle_id}/entry/{entry_id}/edit")
def edit_submit(
    vehicle_id: int,
    entry_id: int,
    request: Request,
    entry_type: str = Form("fuel"),
    date: str = Form(...),
    liters: str = Form(""),
    price_per_liter: str = Form(""),
    total_cost: str = Form(""),
    odometer_km: str = Form(""),
    fuel_type: str = Form(""),
    full_tank: str = Form(""),
    station_name: str = Form(""),
    station_address: str = Form(""),
    station_lat: str = Form(""),
    station_lon: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    vehicle = db.get(Vehicle, vehicle_id)
    entry = db.get(FuelEntry, entry_id)
    if vehicle is None or entry is None or entry.vehicle_id != vehicle.id:
        return RedirectResponse(url="/", status_code=303)

    entry_type = "odometer_only" if entry_type == "odometer_only" else "fuel"
    station = _resolve_station(db, station_name, station_lat, station_lon, station_address, entry.station_id)
    _apply_common_fields(
        entry, entry_type=entry_type, date_=date, liters=liters, price=price_per_liter,
        total=total_cost, odometer=odometer_km, fuel_type=fuel_type, full_tank=full_tank,
        station=station, notes=notes,
    )

    # Fields the user actually filled in now count as real input, not an
    # estimate/derivation. Left blank -> recompute_vehicle re-estimates them.
    manually_filled = {
        name for name, raw in (
            ("liters", liters), ("total_cost", total_cost),
            ("price_per_liter", price_per_liter), ("odometer_km", odometer_km),
        ) if (raw or "").strip()
    }
    entry.estimated_fields = [f for f in (entry.estimated_fields or []) if f not in manually_filled]
    entry.computed_fields = [f for f in (entry.computed_fields or []) if f not in manually_filled]

    db.flush()
    _recompute(db, vehicle.id)
    db.commit()
    return RedirectResponse(url=f"/vehicles/{vehicle.id}", status_code=303)


@router.post("/vehicles/{vehicle_id}/entry/{entry_id}/delete")
def delete_entry(vehicle_id: int, entry_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    entry = db.get(FuelEntry, entry_id)
    if entry and entry.vehicle_id == vehicle_id:
        db.delete(entry)
        db.flush()
        _recompute(db, vehicle_id)
        db.commit()
    return RedirectResponse(url=f"/vehicles/{vehicle_id}", status_code=303)
