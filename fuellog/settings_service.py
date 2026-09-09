"""Cached access to the single ``AppSettings`` row.

Templates and request handlers read settings on nearly every request, so the
row is cached as an immutable snapshot and only reloaded after a write.
"""
import threading
from dataclasses import dataclass

from sqlalchemy.orm import Session

from .config import DEFAULT_LANGUAGE
from .models import AppSettings

_lock = threading.Lock()
_cache: "SettingsSnapshot | None" = None


@dataclass(frozen=True)
class SettingsSnapshot:
    default_language: str
    timezone: str
    currency_code: str
    currency_symbol: str
    currency_position: str
    default_fuel_type: str
    geocoding_enabled: bool
    nominatim_url: str
    tile_url: str
    tile_attribution: str


def _to_snapshot(row: AppSettings) -> SettingsSnapshot:
    return SettingsSnapshot(
        default_language=row.default_language,
        timezone=row.timezone,
        currency_code=row.currency_code,
        currency_symbol=row.currency_symbol,
        currency_position=row.currency_position,
        default_fuel_type=row.default_fuel_type,
        geocoding_enabled=row.geocoding_enabled,
        nominatim_url=row.nominatim_url,
        tile_url=row.tile_url,
        tile_attribution=row.tile_attribution,
    )


def _load_row(db: Session) -> AppSettings:
    row = db.get(AppSettings, 1)
    if row is None:
        row = AppSettings(id=1, default_language=DEFAULT_LANGUAGE)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_settings(db: Session) -> SettingsSnapshot:
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is None:
            _cache = _to_snapshot(_load_row(db))
        return _cache


def update_settings(db: Session, **fields) -> SettingsSnapshot:
    global _cache
    row = _load_row(db)
    for key, value in fields.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    with _lock:
        _cache = _to_snapshot(row)
    return _cache


def invalidate() -> None:
    global _cache
    with _lock:
        _cache = None
