"""URL builder and listing parser for domain.com.au.

build_search_url: constructs a domain.com.au /rent/ search URL from suburb and filters.
parse_listings_from_message: extracts List[PropertyListing] from an LLM message (JSON or multimodal).
"""
import json
import re
from urllib.parse import urlencode

from agent.models import PropertyListing


# Mapping from colloquial property type names to domain.com.au ptype query values.
PROPERTY_TYPE_MAP: dict[str, str] = {
    "apartment": "apartment-unit-flat",
    "unit": "apartment-unit-flat",
    "flat": "apartment-unit-flat",
    "house": "house",
    "townhouse": "townhouse",
    "studio": "studio",
}


def build_search_url(
    suburb: str,
    page: int = 1,
    bedrooms_min: int | None = None,
    bathrooms_min: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    property_type: str | None = None,
) -> str:
    """Construct a domain.com.au rental search URL.

    Args:
        suburb: Suburb name (e.g. "richmond-vic" or "Richmond VIC 3121").
                Spaces are converted to hyphens and the string is lower-cased.
        page: Page number (default 1).
        bedrooms_min: Minimum bedrooms; omitted from URL when None.
        bathrooms_min: Minimum bathrooms; omitted from URL when None.
        price_min: Minimum weekly rent; used as "0" when price_max is given but price_min is not.
        price_max: Maximum weekly rent; omitted when None.
        property_type: One of the PROPERTY_TYPE_MAP keys (e.g. "apartment", "house").
                       Omitted when None or unmapped.

    Returns:
        A fully-qualified domain.com.au rental search URL.
    """
    slug = suburb.lower().replace(" ", "-")
    base = f"https://www.domain.com.au/rent/{slug}/"

    params: dict[str, str | int] = {}

    if bedrooms_min is not None:
        params["bedrooms"] = f"{bedrooms_min}-any"

    if bathrooms_min is not None:
        params["bathrooms"] = f"{bathrooms_min}-any"

    if price_max is not None:
        effective_min = price_min if price_min is not None else 0
        params["price"] = f"{effective_min}-{price_max}"
    elif price_min is not None:
        params["price"] = f"{price_min}-any"

    if property_type is not None:
        ptype = PROPERTY_TYPE_MAP.get(property_type.lower())
        if ptype:
            params["ptype"] = ptype

    params["page"] = page

    return f"{base}?{urlencode(params)}"


def parse_listings_from_message(content: str | list) -> list[PropertyListing]:
    """Extract property listings from an LLM message.

    Handles:
    - Plain JSON string
    - JSON wrapped in markdown code fences (```json ... ```)
    - List of content blocks (multimodal — extracts 'text' blocks)
    - JSON embedded in surrounding text (regex fallback)

    Partial-results contract:
    - bot_detected=false -> return List[PropertyListing]
    - bot_detected=true AND listings non-empty -> return collected listings (partial, NOT raise)
    - bot_detected=true AND listings empty -> raise BotDetectedError

    Args:
        content: Either a string (plain JSON or markdown-fenced) or a list of
                 content blocks (multimodal format with 'type' and 'text' keys).

    Returns:
        List of valid PropertyListing instances. Listings missing both address
        and listing_url are excluded.

    Raises:
        BotDetectedError: When bot_detected is True and no listings were collected.
    """
    # Deferred import to avoid ImportError if agent/exceptions.py doesn't exist at import time.
    from agent.exceptions import BotDetectedError  # noqa: PLC0415

    # Handle multimodal content (list of blocks).
    if isinstance(content, list):
        text_parts = [
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text" and "text" in block
        ]
        text = "\n".join(text_parts)
    else:
        text = content

    # Strip markdown code fences.
    text = re.sub(r"```(?:json)?\s*", "", text).strip()

    # Attempt direct JSON parse.
    data = None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: find the first {...} block in the text via regex.
    if data is None:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except (json.JSONDecodeError, ValueError):
                pass

    if data is None:
        return []

    bot_detected = data.get("bot_detected", False)
    raw_listings = data.get("listings", [])

    # Parse raw listings into PropertyListing models; skip invalid entries.
    parsed: list[PropertyListing] = []
    for item in raw_listings:
        if not isinstance(item, dict):
            continue
        try:
            listing = PropertyListing(**item)
        except Exception:
            continue
        if listing.is_valid():
            parsed.append(listing)

    # Partial-results contract: only raise if bot detected AND no listings collected.
    if bot_detected and not parsed:
        raise BotDetectedError("Bot detection triggered with no listings collected.")

    return parsed
