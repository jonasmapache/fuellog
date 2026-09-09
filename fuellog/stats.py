"""Per-vehicle key figures for the dashboard and tiles."""
from collections import OrderedDict

from .estimation import compute_avg_consumption_l_100km


def vehicle_stats(vehicle, entries) -> dict:
    """entries: chronologically sorted list of FuelEntry for this vehicle
    (already run through the estimation pipeline, i.e. gaps filled where
    possible)."""
    entries = sorted(entries, key=lambda e: (e.date, e.id or 0))
    fuel_entries = [e for e in entries if e.entry_type == "fuel"]

    avg_consumption = compute_avg_consumption_l_100km(entries)

    # Prefer the capacity set on the vehicle; otherwise fall back to the largest
    # full-tank fill-up we have seen, so the range still shows up right after an
    # import even if nobody has entered the exact tank size yet.
    tank_capacity = vehicle.tank_capacity_l
    tank_capacity_estimated = False
    if not tank_capacity:
        full_fills = [e.liters for e in fuel_entries if e.full_tank and e.liters]
        if full_fills:
            tank_capacity = max(full_fills)
            tank_capacity_estimated = True

    range_km = None
    if avg_consumption and tank_capacity:
        range_km = round(tank_capacity / avg_consumption * 100)

    odo_known = [e.odometer_km for e in entries if e.odometer_km is not None]
    total_distance = None
    if len(odo_known) >= 2:
        total_distance = max(odo_known) - min(odo_known)

    total_spent = round(sum(e.total_cost for e in fuel_entries if e.total_cost), 2)
    total_liters = round(sum(e.liters for e in fuel_entries if e.liters), 2)

    cost_per_km = None
    if total_distance and total_distance > 0:
        cost_per_km = round(total_spent / total_distance, 3)

    avg_price_per_liter = None
    priced = [e.price_per_liter for e in fuel_entries if e.price_per_liter]
    if priced:
        avg_price_per_liter = round(sum(priced) / len(priced), 3)

    # Monthly spending trend
    monthly = OrderedDict()
    for e in fuel_entries:
        if e.total_cost is None:
            continue
        key = e.date.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + e.total_cost
    monthly_trend = [{"label": k, "total": round(v, 2)} for k, v in monthly.items()]

    last_entry = fuel_entries[-1] if fuel_entries else None
    has_estimates = any(e.estimated_fields for e in entries)

    return {
        "avg_consumption": avg_consumption,
        "range_km": range_km,
        "range_km_estimated": tank_capacity_estimated,
        "total_distance": total_distance,
        "total_spent": total_spent,
        "total_liters": total_liters,
        "cost_per_km": cost_per_km,
        "avg_price_per_liter": avg_price_per_liter,
        "monthly_trend": monthly_trend,
        "last_entry": last_entry,
        "entry_count": len(fuel_entries),
        "has_estimates": has_estimates,
    }
