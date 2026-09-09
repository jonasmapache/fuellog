"""Estimation and derivation logic for incomplete fuel entries.

Two kinds of "not directly entered" values are distinguished:

1. Exact derivation (``computed_fields``): if exactly one of
   liters / price-per-liter / total-cost is missing, it is computed exactly
   from the other two (total = liters * price, etc.). Mathematically exact,
   flagged only for transparency.

2. Estimate (``estimated_fields``): a missing odometer reading is
   approximated from the previous/next known reading and the computed
   average consumption. This is a genuine approximation.

All functions operate on a chronologically sorted list of ``FuelEntry``
objects belonging to a *single* vehicle and mutate them in place.
"""
from datetime import date


def _round2(x):
    return round(x, 2) if x is not None else None


def fill_exact_derivations(entries):
    """Fill liters/price/total when exactly one of the three is missing."""
    for e in entries:
        if e.entry_type != "fuel":
            continue
        computed = set(e.computed_fields or [])
        vals = [e.liters, e.price_per_liter, e.total_cost]
        missing = [v is None for v in vals]
        if sum(missing) != 1:
            continue
        if e.liters is None and e.price_per_liter and e.total_cost is not None:
            e.liters = _round2(e.total_cost / e.price_per_liter)
            computed.add("liters")
        elif e.total_cost is None and e.liters is not None and e.price_per_liter is not None:
            e.total_cost = _round2(e.liters * e.price_per_liter)
            computed.add("total_cost")
        elif e.price_per_liter is None and e.liters and e.total_cost is not None:
            e.price_per_liter = round(e.total_cost / e.liters, 3)
            computed.add("price_per_liter")
        e.computed_fields = sorted(computed)


def compute_avg_consumption_l_100km(entries) -> float | None:
    """Average consumption via the "segment method": walk chronologically,
    accumulate liters since the last full tank with a known odometer reading,
    and close a segment at the next full tank with a known reading.
    Only real (non-estimated) odometer readings are used as segment
    boundaries so the estimate never feeds back into itself.
    """
    total_liters = 0.0
    total_km = 0.0
    last_full_odo = None
    liters_since = 0.0
    any_partial_since = False

    for e in entries:
        if e.odometer_km is None:
            continue
        odo_is_real = "odometer_km" not in (e.estimated_fields or [])

        if e.entry_type == "fuel" and e.liters is not None:
            liters_since += e.liters
            if not e.full_tank:
                any_partial_since = True

        if e.full_tank and odo_is_real:
            if last_full_odo is not None and liters_since > 0:
                distance = e.odometer_km - last_full_odo
                if distance > 0:
                    total_liters += liters_since
                    total_km += distance
            last_full_odo = e.odometer_km
            liters_since = 0.0
            any_partial_since = False
        elif odo_is_real and last_full_odo is None:
            # first known point at all as a start anchor, if no full tank
            # has been seen yet
            last_full_odo = e.odometer_km
            liters_since = 0.0

    if total_km <= 0:
        return None
    return round(total_liters / total_km * 100, 2)


def _interpolate_by_date(prev_date: date, prev_val: float, next_date: date, next_val: float, target_date: date) -> float:
    span = (next_date - prev_date).days
    if span <= 0:
        return (prev_val + next_val) / 2
    frac = (target_date - prev_date).days / span
    frac = max(0.0, min(1.0, frac))
    return prev_val + frac * (next_val - prev_val)


def estimate_missing_odometers(entries, avg_consumption: float | None):
    """Estimate missing odometer readings from neighbours and the average
    consumption. Works in place; assumes a chronologically sorted list.
    """
    # Real (non-estimated) readings as stable anchors for the upper bound.
    real_indices = [i for i, e in enumerate(entries) if e.odometer_km is not None and "odometer_km" not in (e.estimated_fields or [])]

    prev_val = None
    prev_date = None

    for i, e in enumerate(entries):
        if e.odometer_km is not None:
            prev_val = e.odometer_km
            prev_date = e.date
            continue

        # find the next real anchor after i
        next_val = next_date = None
        for j in real_indices:
            if j > i:
                next_val = entries[j].odometer_km
                next_date = entries[j].date
                break

        candidate = None
        est = set(e.estimated_fields or [])

        liters_for_this = e.liters if e.entry_type == "fuel" else None

        if avg_consumption and liters_for_this and prev_val is not None:
            distance_guess = liters_for_this / avg_consumption * 100
            candidate = prev_val + distance_guess
            if next_val is not None and candidate >= next_val:
                candidate = _interpolate_by_date(prev_date, prev_val, next_date, next_val, e.date)
        elif prev_val is not None and next_val is not None:
            candidate = _interpolate_by_date(prev_date, prev_val, next_date, next_val, e.date)
        elif prev_val is not None:
            candidate = prev_val  # rough lower bound, no better info available

        if candidate is not None:
            e.odometer_km = round(candidate)
            est.add("odometer_km")
            e.estimated_fields = sorted(est)
            prev_val = e.odometer_km
            prev_date = e.date


def estimate_missing_liters(entries, avg_consumption: float | None):
    """Estimate a missing liter amount from the distance driven since the
    previous known odometer reading and the average consumption (e.g. when
    only the price and the odometer are known, but neither liters nor total).
    """
    if not avg_consumption:
        return
    prev_odo = None
    for e in entries:
        if e.odometer_km is None:
            continue
        if e.entry_type == "fuel" and e.liters is None and prev_odo is not None:
            distance = e.odometer_km - prev_odo
            if distance > 0:
                est = set(e.estimated_fields or [])
                e.liters = round(distance / 100 * avg_consumption, 2)
                est.add("liters")
                e.estimated_fields = sorted(est)
        prev_odo = e.odometer_km


def recompute_vehicle(entries):
    """Run the full estimation pipeline for one vehicle (a chronologically
    sorted list of ``FuelEntry`` objects) and return the final average
    consumption.
    """
    entries = sorted(entries, key=lambda e: (e.date, e.id or 0))
    fill_exact_derivations(entries)
    bootstrap_avg = compute_avg_consumption_l_100km(entries)
    estimate_missing_odometers(entries, bootstrap_avg)
    estimate_missing_liters(entries, bootstrap_avg)
    # Liters may have just been estimated -> derive the total from it if the
    # price per liter is known.
    fill_exact_derivations(entries)
    final_avg = compute_avg_consumption_l_100km(entries)
    return final_avg
