"""Tests for build_search_url in agent/url_builder.py."""
from agent.url_builder import build_search_url, PROPERTY_TYPE_MAP


class TestBuildSearchUrl:
    """Tests for the build_search_url function."""

    def test_basic_suburb_returns_valid_url(self):
        url = build_search_url("richmond-vic")
        assert url == "https://www.domain.com.au/rent/richmond-vic/?page=1"

    def test_bedrooms_min_in_url(self):
        url = build_search_url("richmond-vic", bedrooms_min=2)
        assert "bedrooms=2-any" in url

    def test_bathrooms_min_in_url(self):
        url = build_search_url("richmond-vic", bathrooms_min=1)
        assert "bathrooms=1-any" in url

    def test_price_min_and_max(self):
        url = build_search_url("richmond-vic", price_min=500, price_max=2000)
        assert "price=500-2000" in url

    def test_property_type_apartment(self):
        url = build_search_url("richmond-vic", property_type="apartment")
        assert "ptype=apartment-unit-flat" in url

    def test_property_type_house(self):
        url = build_search_url("richmond-vic", property_type="house")
        assert "ptype=house" in url

    def test_suburb_with_spaces_slugified(self):
        url = build_search_url("Richmond VIC 3121", page=2)
        assert "richmond-vic-3121" in url
        assert "page=2" in url

    def test_bedrooms_min_none_omits_param(self):
        url = build_search_url("richmond-vic", bedrooms_min=None)
        assert "bedrooms" not in url

    def test_price_max_only_uses_zero_min(self):
        url = build_search_url("richmond-vic", price_max=2000)
        assert "price=0-2000" in url

    def test_no_optional_params_minimal_url(self):
        url = build_search_url("richmond-vic")
        assert "bedrooms" not in url
        assert "bathrooms" not in url
        assert "price" not in url
        assert "ptype" not in url
        assert "page=1" in url

    def test_page_2_in_url(self):
        url = build_search_url("richmond-vic", page=2)
        assert "page=2" in url

    def test_property_type_map_contains_expected_keys(self):
        assert "apartment" in PROPERTY_TYPE_MAP
        assert "unit" in PROPERTY_TYPE_MAP
        assert "flat" in PROPERTY_TYPE_MAP
        assert "house" in PROPERTY_TYPE_MAP
        assert "townhouse" in PROPERTY_TYPE_MAP
        assert "studio" in PROPERTY_TYPE_MAP

    def test_property_type_apartment_unit_flat_mapping(self):
        assert PROPERTY_TYPE_MAP["apartment"] == "apartment-unit-flat"
        assert PROPERTY_TYPE_MAP["unit"] == "apartment-unit-flat"
        assert PROPERTY_TYPE_MAP["flat"] == "apartment-unit-flat"

    def test_url_starts_with_domain(self):
        url = build_search_url("bondi-beach-nsw")
        assert url.startswith("https://www.domain.com.au/rent/")
