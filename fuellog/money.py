"""Currency formatting driven by the AppSettings row."""


def format_money(value, settings, *, decimals: int = 2) -> str:
    """Format a numeric amount with the configured currency symbol/position.

    ``settings`` is an ``AppSettings`` instance (or anything exposing
    ``currency_symbol`` / ``currency_position``).
    """
    if value is None:
        return "–"
    symbol = getattr(settings, "currency_symbol", "€") or ""
    position = getattr(settings, "currency_position", "after")
    amount = f"{float(value):,.{decimals}f}"
    if position == "before":
        return f"{symbol}{amount}"
    return f"{amount} {symbol}".strip()
