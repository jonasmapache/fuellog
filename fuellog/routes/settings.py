"""Instance settings, user management and CSV import/export (admin only)."""
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auth import hash_password, require_admin
from ..database import get_db
from ..exporter import export_csv
from ..i18n import LANGUAGES
from ..importer import ImportError_, import_csv
from ..models import User
from ..security import csrf_protect
from ..settings_service import update_settings
from ..templating import flash_text, render
from .vehicles import FUEL_TYPES, _vehicles_ordered

router = APIRouter(prefix="/settings", dependencies=[Depends(csrf_protect)])


def _view(request: Request, db: Session, user: User, *, notice: str | None = None,
          error: str | None = None, **msg_kwargs):
    ctx = {
        "users": db.query(User).order_by(User.id).all(),
        "vehicles": _vehicles_ordered(db),
        "fuel_types": FUEL_TYPES,
        "available_languages": LANGUAGES,
        "notice": flash_text(request, db, notice, **msg_kwargs) if notice else None,
        "error": flash_text(request, db, error, **msg_kwargs) if error else None,
    }
    return render(request, db, "settings.html", user=user, **ctx)


@router.get("")
def settings_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    return _view(request, db, user)


@router.post("")
def save_settings(
    request: Request,
    default_language: str = Form("en"),
    timezone: str = Form("UTC"),
    default_fuel_type: str = Form("E10"),
    currency_code: str = Form("EUR"),
    currency_symbol: str = Form("€"),
    currency_position: str = Form("after"),
    geocoding_enabled: str = Form(""),
    nominatim_url: str = Form(""),
    tile_url: str = Form(""),
    tile_attribution: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    update_settings(
        db,
        default_language=default_language if default_language in LANGUAGES else "en",
        timezone=timezone.strip() or "UTC",
        default_fuel_type=default_fuel_type.strip() or "E10",
        currency_code=currency_code.strip() or "EUR",
        currency_symbol=currency_symbol.strip() or "€",
        currency_position="before" if currency_position == "before" else "after",
        geocoding_enabled=(geocoding_enabled == "on"),
        nominatim_url=nominatim_url.strip() or "https://nominatim.openstreetmap.org/search",
        tile_url=tile_url.strip() or "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        tile_attribution=tile_attribution.strip() or "&copy; OpenStreetMap contributors",
    )
    return _view(request, db, user, notice="settings.saved")


@router.post("/users/add")
def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    is_admin: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    username = username.strip()
    if not username or len(password) < 8:
        return _view(request, db, user, error="setup.error_short")
    if db.query(User).filter(User.username == username).first():
        return _view(request, db, user, error="settings.users.error_username_taken")
    db.add(User(username=username, password_hash=hash_password(password), is_admin=(is_admin == "on")))
    db.commit()
    return _view(request, db, user, notice="settings.saved")


@router.post("/users/{user_id}/password")
def reset_password(
    user_id: int,
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = db.get(User, user_id)
    if target and len(password) >= 8:
        target.password_hash = hash_password(password)
        db.commit()
        return _view(request, db, user, notice="settings.saved")
    return _view(request, db, user, error="setup.error_short")


@router.post("/users/{user_id}/delete")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = db.get(User, user_id)
    if target is None:
        return _view(request, db, user)
    admin_count = db.query(User).filter(User.is_admin.is_(True)).count()
    if target.is_admin and admin_count <= 1:
        return _view(request, db, user, error="settings.users.error_last_admin")
    db.delete(target)
    db.commit()
    return _view(request, db, user, notice="settings.saved")


@router.get("/export")
def export_data(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    csv_text = export_csv(db)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="fuellog-export.csv"'},
    )


@router.post("/import")
async def import_data(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
    try:
        result = import_csv(db, text)
    except ImportError_ as exc:
        return _view(request, db, user, error="settings.data.import_error", detail=str(exc))
    return _view(
        request, db, user,
        notice="settings.data.import_result",
        created=result.created,
        skipped=result.skipped,
    )
