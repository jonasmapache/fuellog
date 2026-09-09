"""Vehicle list (home), dashboard, create / edit / delete."""
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import require_admin, require_user
from ..database import get_db
from ..models import User, Vehicle
from ..parsing import parse_decimal
from ..photos import delete_vehicle_photo, save_vehicle_photo
from ..security import csrf_protect
from ..stats import vehicle_stats
from ..templating import render

router = APIRouter(dependencies=[Depends(csrf_protect)])

FUEL_TYPES = ["E5", "E10", "Super Plus", "Diesel", "LPG", "CNG", "Other"]


def _vehicles_ordered(db: Session) -> list[Vehicle]:
    return db.query(Vehicle).order_by(Vehicle.sort_order.desc(), Vehicle.id).all()


@router.get("/")
def index(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    tiles = []
    for v in _vehicles_ordered(db):
        entries = sorted(v.entries, key=lambda e: (e.date, e.id))
        tiles.append({"vehicle": v, "stats": vehicle_stats(v, entries)})
    return render(request, db, "index.html", user=user, tiles=tiles)


@router.get("/vehicles/new")
def new_form(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return render(request, db, "vehicle_form.html", user=user, vehicle=None)


@router.post("/vehicles/new")
async def new_submit(
    request: Request,
    name: str = Form(...),
    brand_model: str = Form(""),
    color: str = Form("#2563eb"),
    tank_capacity_l: str = Form(""),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    vehicle = Vehicle(
        name=name.strip(),
        brand_model=brand_model.strip() or None,
        color=color or "#2563eb",
        tank_capacity_l=parse_decimal(tank_capacity_l),
        sort_order=-db.query(Vehicle).count(),
    )
    db.add(vehicle)
    db.flush()
    await save_vehicle_photo(vehicle, photo)
    db.commit()
    return RedirectResponse(url=f"/vehicles/{vehicle.id}", status_code=303)


@router.get("/vehicles/{vehicle_id}")
def dashboard(vehicle_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return RedirectResponse(url="/", status_code=303)
    entries = sorted(vehicle.entries, key=lambda e: (e.date, e.id))
    stats = vehicle_stats(vehicle, entries)
    recent = list(reversed(entries))[:15]
    return render(request, db, "vehicle_dashboard.html", user=user, vehicle=vehicle, stats=stats, recent=recent)


@router.get("/vehicles/{vehicle_id}/settings")
def edit_form(vehicle_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return RedirectResponse(url="/", status_code=303)
    return render(request, db, "vehicle_form.html", user=user, vehicle=vehicle)


@router.post("/vehicles/{vehicle_id}/settings")
async def edit_submit(
    vehicle_id: int,
    request: Request,
    name: str = Form(...),
    brand_model: str = Form(""),
    color: str = Form("#2563eb"),
    tank_capacity_l: str = Form(""),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return RedirectResponse(url="/", status_code=303)
    vehicle.name = name.strip()
    vehicle.brand_model = brand_model.strip() or None
    vehicle.color = color or vehicle.color
    vehicle.tank_capacity_l = parse_decimal(tank_capacity_l)
    await save_vehicle_photo(vehicle, photo)
    db.commit()
    return RedirectResponse(url=f"/vehicles/{vehicle.id}", status_code=303)


@router.post("/vehicles/{vehicle_id}/delete")
def delete_vehicle(
    vehicle_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is not None:
        delete_vehicle_photo(vehicle)
        db.delete(vehicle)
        db.commit()
    return RedirectResponse(url="/", status_code=303)
