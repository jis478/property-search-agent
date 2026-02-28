"""Pydantic models for the property agent."""
from pydantic import BaseModel


class PropertyListing(BaseModel):
    """Represents a single property listing extracted from domain.com.au.

    Required fields: address, listing_url.
    All other fields are optional — listings with missing price, bedrooms, etc.
    are still valid and included in results.
    """

    address: str
    listing_url: str
    price: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    property_type: str | None = None

    def is_valid(self) -> bool:
        """Return True if the listing has both address and listing_url set (non-empty)."""
        return bool(self.address and self.listing_url)
