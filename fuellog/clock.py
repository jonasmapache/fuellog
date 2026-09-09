"""Timezone-aware 'today' for form defaults."""
from datetime import date, datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


def today_in(tz_name: str) -> date:
    if ZoneInfo is not None and tz_name:
        try:
            return datetime.now(ZoneInfo(tz_name)).date()
        except Exception:
            pass
    return date.today()
