"""IANA timezone list for the settings dropdown."""
from functools import lru_cache

try:
    from zoneinfo import available_timezones
except ImportError:  # pragma: no cover
    available_timezones = None

_EXCLUDE_PREFIXES = ("Etc/", "SystemV/", "US/", "Canada/", "Brazil/", "Chile/", "Mexico/")


@lru_cache(maxsize=1)
def timezone_choices() -> list[str]:
    """Sorted list of Region/City timezone names, plus UTC first."""
    if available_timezones is None:
        return ["UTC"]
    names = sorted(
        tz for tz in available_timezones()
        if "/" in tz and not tz.startswith(_EXCLUDE_PREFIXES)
    )
    return ["UTC", *names]


def timezone_options(current: str) -> list[str]:
    """The choice list, guaranteeing the currently stored value is present."""
    choices = timezone_choices()
    if current and current not in choices:
        return [current, *choices]
    return choices
