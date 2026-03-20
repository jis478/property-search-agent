"""Enrich property listings with walking distance to school.

Uses Google Geocoding API and Distance Matrix API (mode=walking) to:
- Geocode school and property addresses
- Compute walking distance in meters
- Filter listings by max_distance_meters
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.models import PropertyListing  # noqa: F401

logger = logging.getLogger(__name__)


def _geocode(api_key: str, address: str) -> tuple[float, float] | None:
    """Geocode an address to (lat, lng). Returns None on failure."""
    import urllib.parse
    import urllib.request

    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={urllib.parse.quote(address)}&key={api_key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read().decode()
    except Exception as e:
        logger.warning("Geocoding failed for %r: %s", address[:50], e)
        return None

    import json

    j = json.loads(data)
    status = j.get("status", "")
    if status != "OK" or not j.get("results"):
        logger.warning("Geocode failed: address=%r status=%r error=%s",
            address[:60], status, j.get("error_message", ""))
        return None
    loc = j["results"][0]["geometry"]["location"]
    return (loc["lat"], loc["lng"])


def _walking_distance_meters(api_key: str, origin: str, destination: str) -> float | None:
    """Get walking distance in meters. Returns None on failure."""
    import urllib.parse
    import urllib.request

    params = {
        "origins": origin,
        "destinations": destination,
        "mode": "walking",
        "key": api_key,
    }
    qs = urllib.parse.urlencode(params)
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read().decode()
    except Exception as e:
        logger.warning("Distance Matrix failed: %s", e)
        return None

    import json

    j = json.loads(data)
    status = j.get("status", "")
    if status != "OK":
        logger.warning("Distance Matrix failed: origin=%r dest=%r status=%r error=%s",
            origin[:40], destination[:40], status, j.get("error_message", ""))
        return None
    rows = j.get("rows") or []
    if not rows:
        return None
    elements = rows[0].get("elements") or []
    if not elements:
        return None
    elem = elements[0]
    if elem.get("status") != "OK":
        return None
    dist = elem.get("distance", {}).get("value")  # meters
    if dist is None:
        return None
    return float(dist)


def enrich_listings_with_school_distance(
    listings: list,
    school_address: str,
    max_distance_meters: int | float,
    api_key: str,
) -> list:
    """Filter listings by walking distance to school and add distance_to_school.

    Args:
        listings: List of PropertyListing objects (or dicts with 'address').
        school_address: School address for origin.
        max_distance_meters: Max walking distance in meters; filter listings beyond this.
        api_key: Google Maps API key.

    Returns:
        List of PropertyListing (or dicts) with distance_to_school set, filtered
        to only those within max_distance_meters. If geocoding fails for school,
        returns original listings with distance_to_school=None (no filter).
    """
    if not api_key or not school_address or max_distance_meters <= 0:
        logger.debug("enrichment skipped: api_key=%s school=%s max_dist=%s",
            bool(api_key), bool(school_address), max_distance_meters)
        return list(listings)

    logger.info("enrichment start: school=%r max=%sm listings=%d",
        school_address[:60], max_distance_meters, len(listings))
    school_coords = _geocode(api_key, school_address)
    if school_coords is None:
        logger.warning("Could not geocode school %r; skipping enrichment", school_address[:50])
        return list(listings)

    enriched: list = []
    for item in listings:
        if hasattr(item, "address"):
            addr = item.address
            is_pydantic = True
        else:
            addr = (item or {}).get("address", "")
            is_pydantic = False

        if not addr:
            continue

        dist = _walking_distance_meters(api_key, school_address, addr)
        if dist is None:
            continue
        if dist > max_distance_meters:
            continue

        if is_pydantic:
            copy = item.model_copy(update={"distance_to_school": round(dist, 0)})
        else:
            copy = dict(item)
            copy["distance_to_school"] = round(dist, 0)
        enriched.append(copy)

    logger.info("enrichment done: %d within %sm, %d filtered out",
        len(enriched), max_distance_meters, len(listings) - len(enriched))
    return enriched
