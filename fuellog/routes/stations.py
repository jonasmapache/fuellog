"""Station autocomplete: local history first, then optional OSM lookup."""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..auth import require_user
from ..database import get_db
from ..geocode import search_address
from ..models import Station, User
from ..settings_service import get_settings

router = APIRouter()


@router.get("/api/stations/search")
async def search(
    request: Request,
    q: str = Query("", min_length=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    q = q.strip()
    if len(q) < 2:
        return JSONResponse([])

    local = (
        db.query(Station)
        .filter(Station.name.ilike(f"%{q}%"))
        .order_by(Station.usage_count.desc())
        .limit(8)
        .all()
    )
    results = [
        {"name": s.name, "address": s.address, "lat": s.lat, "lon": s.lon, "source": "local"}
        for s in local
    ]

    settings = get_settings(db)
    if settings.geocoding_enabled and len(q) >= 3:
        seen = {r["name"].lower() for r in results}
        for r in await search_address(q, settings.nominatim_url, limit=5):
            if r["name"].lower() in seen:
                continue
            results.append({
                "name": r["name"],
                "address": r["display_name"],
                "lat": r["lat"],
                "lon": r["lon"],
                "source": "osm",
            })

    return JSONResponse(results[:10])
