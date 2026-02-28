"""Tests for parse_listings_from_message in agent/url_builder.py."""
import json
import pytest
from agent.url_builder import parse_listings_from_message
from agent.models import PropertyListing


class TestParseListingsFromMessage:
    """Tests for the parse_listings_from_message function."""

    def _make_message(self, listings, bot_detected=False):
        return json.dumps({"bot_detected": bot_detected, "listings": listings})

    def test_valid_json_returns_list_of_property_listings(self):
        data = {
            "bot_detected": False,
            "listings": [
                {
                    "address": "1 Smith St, Richmond VIC 3121",
                    "listing_url": "https://www.domain.com.au/1234",
                    "price": "$500/week",
                    "bedrooms": 2,
                    "bathrooms": 1,
                    "property_type": "apartment",
                }
            ],
        }
        result = parse_listings_from_message(json.dumps(data))
        assert len(result) == 1
        assert isinstance(result[0], PropertyListing)
        assert result[0].address == "1 Smith St, Richmond VIC 3121"
        assert result[0].listing_url == "https://www.domain.com.au/1234"
        assert result[0].price == "$500/week"
        assert result[0].bedrooms == 2
        assert result[0].bathrooms == 1
        assert result[0].property_type == "apartment"

    def test_json_with_code_fences_stripped(self):
        listing = {
            "address": "2 Jones Ave, Fitzroy VIC",
            "listing_url": "https://www.domain.com.au/5678",
        }
        raw = json.dumps({"bot_detected": False, "listings": [listing]})
        fenced = f"```json\n{raw}\n```"
        result = parse_listings_from_message(fenced)
        assert len(result) == 1
        assert result[0].address == "2 Jones Ave, Fitzroy VIC"

    def test_json_with_plain_code_fences_stripped(self):
        listing = {
            "address": "3 Main Rd, Collingwood VIC",
            "listing_url": "https://www.domain.com.au/9012",
        }
        raw = json.dumps({"bot_detected": False, "listings": [listing]})
        fenced = f"```\n{raw}\n```"
        result = parse_listings_from_message(fenced)
        assert len(result) == 1

    def test_bot_detected_true_with_empty_listings_raises(self):
        from agent.exceptions import BotDetectedError
        data = {"bot_detected": True, "listings": []}
        with pytest.raises(BotDetectedError):
            parse_listings_from_message(json.dumps(data))

    def test_bot_detected_true_with_listings_returns_partial(self):
        """Partial results contract: bot_detected=True + non-empty listings -> return listings, not raise."""
        data = {
            "bot_detected": True,
            "listings": [
                {
                    "address": "5 Park St, South Yarra VIC",
                    "listing_url": "https://www.domain.com.au/partial1",
                }
            ],
        }
        result = parse_listings_from_message(json.dumps(data))
        assert len(result) == 1
        assert result[0].address == "5 Park St, South Yarra VIC"

    def test_listing_missing_address_and_url_excluded(self):
        data = {
            "bot_detected": False,
            "listings": [
                {
                    "address": "Valid Address",
                    "listing_url": "https://www.domain.com.au/valid",
                },
                {
                    "price": "$400/week",  # no address, no listing_url
                },
            ],
        }
        result = parse_listings_from_message(json.dumps(data))
        assert len(result) == 1
        assert result[0].address == "Valid Address"

    def test_listing_missing_optional_fields_allowed(self):
        data = {
            "bot_detected": False,
            "listings": [
                {
                    "address": "6 Oak St, Carlton VIC",
                    "listing_url": "https://www.domain.com.au/6789",
                    "price": None,
                    "bedrooms": None,
                    "bathrooms": None,
                    "property_type": None,
                }
            ],
        }
        result = parse_listings_from_message(json.dumps(data))
        assert len(result) == 1
        assert result[0].price is None
        assert result[0].bedrooms is None

    def test_completely_unparseable_returns_empty_list(self):
        result = parse_listings_from_message("this is not json at all !!!")
        assert result == []

    def test_multimodal_content_list_with_text_blocks(self):
        """Content passed as a list of blocks (multimodal) — extract 'text' blocks."""
        listing = {
            "address": "7 Elm St, Prahran VIC",
            "listing_url": "https://www.domain.com.au/multimodal",
        }
        inner = json.dumps({"bot_detected": False, "listings": [listing]})
        content = [
            {"type": "text", "text": inner},
        ]
        result = parse_listings_from_message(content)
        assert len(result) == 1
        assert result[0].address == "7 Elm St, Prahran VIC"

    def test_multimodal_with_non_text_blocks_ignored(self):
        """Non-text blocks in multimodal content are ignored."""
        listing = {
            "address": "8 Birch Lane, Hawthorn VIC",
            "listing_url": "https://www.domain.com.au/mixed",
        }
        inner = json.dumps({"bot_detected": False, "listings": [listing]})
        content = [
            {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
            {"type": "text", "text": inner},
        ]
        result = parse_listings_from_message(content)
        assert len(result) == 1

    def test_malformed_json_regex_fallback(self):
        """Recoverable JSON embedded in text should be found via regex."""
        listing = {
            "address": "9 Maple Ave, Brunswick VIC",
            "listing_url": "https://www.domain.com.au/fallback",
        }
        inner = json.dumps({"bot_detected": False, "listings": [listing]})
        text = f"Here are the results: {inner}\n\nEnd of results."
        result = parse_listings_from_message(text)
        assert len(result) == 1
        assert result[0].address == "9 Maple Ave, Brunswick VIC"

    def test_empty_listings_array_returns_empty_list(self):
        data = {"bot_detected": False, "listings": []}
        result = parse_listings_from_message(json.dumps(data))
        assert result == []


class TestPropertyListingModel:
    """Tests for the PropertyListing Pydantic model."""

    def test_valid_model_with_required_fields(self):
        listing = PropertyListing(
            address="10 Pine St, Northcote VIC",
            listing_url="https://www.domain.com.au/10",
        )
        assert listing.address == "10 Pine St, Northcote VIC"
        assert listing.listing_url == "https://www.domain.com.au/10"
        assert listing.price is None
        assert listing.bedrooms is None
        assert listing.bathrooms is None
        assert listing.property_type is None

    def test_valid_model_with_all_fields(self):
        listing = PropertyListing(
            address="11 Gum St, Thornbury VIC",
            listing_url="https://www.domain.com.au/11",
            price="$600/week",
            bedrooms=3,
            bathrooms=2,
            property_type="house",
        )
        assert listing.bedrooms == 3
        assert listing.bathrooms == 2
        assert listing.price == "$600/week"
        assert listing.property_type == "house"

    def test_is_valid_returns_true_when_address_and_url_present(self):
        listing = PropertyListing(
            address="12 Cedar Rd, Ivanhoe VIC",
            listing_url="https://www.domain.com.au/12",
        )
        assert listing.is_valid() is True

    def test_is_valid_returns_false_when_address_empty(self):
        listing = PropertyListing(address="", listing_url="https://www.domain.com.au/13")
        assert listing.is_valid() is False

    def test_is_valid_returns_false_when_url_empty(self):
        listing = PropertyListing(address="13 Wattle St, Preston VIC", listing_url="")
        assert listing.is_valid() is False
