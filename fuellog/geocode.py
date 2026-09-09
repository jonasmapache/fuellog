"""Address / POI lookup via a Nominatim-compatible endpoint.

The endpoint URL comes from AppSettings so self-hosters can point at their
own instance. Failures return an empty list so entry logging keeps working
offline.
"""
import httpx

USER_AGENT = "fuellog-selfhosted (+https://github.com/jonasmapache/fuellog)"


async def search_address(query: str, nominatim_url: str, limit: int = 5) -> list[dict]:
    if not query or len(query.strip()) < 3 or not nominatim_url:
        return []
    params = {
        "format": "jsonv2",
        "q": query,
        "addressdetails": 1,
        "limit": limit,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(nominatim_url, params=params, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []

    results = []
    for item in data:
        try:
            results.append({
                "display_name": item.get("display_name"),
                "name": item.get("name") or (item.get("display_name", "").split(",")[0]),
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return results
