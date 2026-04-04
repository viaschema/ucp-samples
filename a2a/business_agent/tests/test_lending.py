# Copyright 2026 UCP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for lending functionality: MockPIIProvider, LoanProviderRegistry, and capability negotiation."""

from __future__ import annotations

import json
import re
from unittest.mock import MagicMock

import httpx
import pytest

from business_agent.lender_api import _generate_mock_offers

from business_agent.constants import (
    UCP_LENDING_EXTENSION,
)
from business_agent.models.lending_types import (
    Lender,
    LendingResponse,
    LoanOffer,
    PIICredential,
    PIIInstrument,
)
from business_agent.loan_provider import (
    CAR_LOAN_PII_FIELDS,
    PERSONAL_LOAN_PII_FIELDS,
    LoanProviderRegistry,
    MockLoanProvider,
)
from business_agent.pii_provider import (
    MockPIIProvider,
    TokenEntry,
    create_pii_vault_routes,
)


# ---------- Fixtures ----------


@pytest.fixture
def pii_provider():
    """Create a fresh MockPIIProvider instance (pre-seeded with foo@example.com)."""
    return MockPIIProvider()


@pytest.fixture
def empty_pii_provider():
    """Create a MockPIIProvider with no pre-seeded data."""
    provider = MockPIIProvider()
    provider._stored_pii = {}
    return provider


@pytest.fixture
def pii_provider_with_user(pii_provider):
    """Create a MockPIIProvider with a pre-stored user."""
    pii_provider.store_pii(
        "alice@example.com",
        {
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "phone_number": "+15559999000",
            "address": {
                "street_address": "789 Oak Ave",
                "address_locality": "Portland",
                "address_region": "OR",
                "postal_code": "97201",
                "address_country": "US",
            },
            "date_of_birth": "1985-05-20",
            "annual_income": "95000",
            "living_situation": "mortgage",
        },
    )
    return pii_provider


@pytest.fixture
def sample_pii_instrument(pii_provider_with_user):
    """Create a valid PIIInstrument with a real token."""
    token = pii_provider_with_user.issue_token("alice@example.com")
    return PIIInstrument(
        id="pii_profile_1",
        handler_id="vgs_pii_provider",
        handler_name="vgs.pii.provider",
        fields_stored=list(
            pii_provider_with_user.get_stored_fields("alice@example.com")
        ),
        loan_type="personal",
        credential=PIICredential(type="token", token=token),
    )


def _mock_lender_transport(request: httpx.Request) -> httpx.Response:
    """In-process mock transport that handles lender API calls without HTTP."""
    match = re.search(r"/lender-api/([^/]+)/apply", str(request.url))
    if not match:
        return httpx.Response(404)
    lender_id = match.group(1)
    body = json.loads(request.content)
    loan_type = body.get("loan_type", "personal")
    loan_amount = float(body.get("loan_amount_requested", body.get("car_value", 10000)))
    offers = _generate_mock_offers(
        lender_id, loan_amount, loan_type, body.get("lender_name")
    )
    return httpx.Response(
        200,
        json={"offers": [o.model_dump(mode="json") for o in offers]},
    )


@pytest.fixture
def loan_registry(pii_provider, monkeypatch):
    """Create a LoanProviderRegistry backed by the test pii_provider.

    Patches httpx.post to use a mock transport so tests don't need a running server.
    """
    mock_client = httpx.Client(transport=httpx.MockTransport(_mock_lender_transport))
    monkeypatch.setattr(httpx, "post", mock_client.post)
    return LoanProviderRegistry(pii_provider)


@pytest.fixture
def pii_token(pii_provider):
    """Issue a PII token for the pre-seeded foo@example.com user (default platform)."""
    return pii_provider.issue_token("foo@example.com")


@pytest.fixture
def pii_tokens(pii_provider):
    """Issue platform-scoped PII tokens for all lenders for the pre-seeded user."""
    from business_agent.loan_provider import LENDER_LIST

    return {
        lender.platform_id: pii_provider.issue_token(
            "foo@example.com", lender.platform_id
        )
        for lender in LENDER_LIST
    }


@pytest.fixture
def mock_tool_context():
    """Create a mock ToolContext for testing agent tools."""
    ctx = MagicMock()
    ctx.state = {}
    return ctx


# ---------- Test MockPIIProvider ----------


class TestMockPIIProvider:
    """Tests for MockPIIProvider methods."""

    def test_get_stored_fields_empty_for_new_user(self, pii_provider):
        """Test that a new user has no stored fields."""
        fields = pii_provider.get_stored_fields("new@example.com")
        assert fields == []

    def test_get_stored_fields_after_store(self, pii_provider):
        """Test that stored fields are returned correctly after storing PII."""
        pii_provider.store_pii(
            "test@example.com", {"first_name": "Test", "email": "test@example.com"}
        )
        fields = pii_provider.get_stored_fields("test@example.com")
        assert "first_name" in fields
        assert "email" in fields
        assert len(fields) == 2

    def test_get_missing_fields_all_missing_for_new_user(self, pii_provider):
        """Test that all required fields are missing for a new user."""
        missing = pii_provider.get_missing_fields(
            "new@example.com", PERSONAL_LOAN_PII_FIELDS
        )
        assert sorted(missing) == sorted(PERSONAL_LOAN_PII_FIELDS)

    def test_get_missing_fields_none_when_all_stored(self, pii_provider_with_user):
        """Test that no fields are missing when all required fields are stored."""
        missing = pii_provider_with_user.get_missing_fields(
            "alice@example.com", PERSONAL_LOAN_PII_FIELDS
        )
        assert missing == []

    def test_get_missing_fields_partial(self, pii_provider):
        """Test partial PII storage leaves remaining fields as missing."""
        pii_provider.store_pii(
            "partial@example.com",
            {
                "first_name": "Partial",
                "last_name": "User",
            },
        )
        missing = pii_provider.get_missing_fields(
            "partial@example.com", PERSONAL_LOAN_PII_FIELDS
        )
        assert "first_name" not in missing
        assert "last_name" not in missing
        assert "email" in missing
        assert "annual_income" in missing

    def test_store_pii_creates_new_user(self, pii_provider):
        """Test storing PII for a brand new user."""
        result = pii_provider.store_pii(
            "brand_new@example.com",
            {
                "first_name": "Brand",
                "last_name": "New",
            },
        )
        assert result["status"] == "stored"
        assert "first_name" in result["fields_stored"]
        assert "last_name" in result["fields_stored"]

    def test_store_pii_incremental(self, pii_provider):
        """Test that PII can be stored incrementally."""
        pii_provider.store_pii("inc@example.com", {"first_name": "Inc"})
        result = pii_provider.store_pii("inc@example.com", {"last_name": "Mental"})
        assert "first_name" in result["fields_stored"]
        assert "last_name" in result["fields_stored"]

    def test_store_pii_overwrites_existing_fields(self, pii_provider):
        """Test that re-storing a field overwrites the old value."""
        pii_provider.store_pii("over@example.com", {"first_name": "Old"})
        pii_provider.store_pii("over@example.com", {"first_name": "New"})
        assert pii_provider._stored_pii["over@example.com"]["first_name"] == "New"

    def test_issue_token(self, pii_provider):
        """Test that tokens are issued and can be tracked."""
        token = pii_provider.issue_token("user@example.com")
        assert token.startswith("pii_token_")
        assert token in pii_provider._tokens
        entry = pii_provider._tokens[token]
        assert isinstance(entry, TokenEntry)
        assert entry.email == "user@example.com"
        assert entry.platform_id == "_default"
        assert isinstance(entry.created_at, float)
        assert isinstance(entry.allowed_fields, frozenset)

    def test_issue_token_with_platform(self, pii_provider):
        """Test that tokens issued with a platform_id store the platform."""
        token = pii_provider.issue_token("user@example.com", "sofi")
        assert token.startswith("pii_token_")
        entry = pii_provider._tokens[token]
        assert isinstance(entry, TokenEntry)
        assert entry.email == "user@example.com"
        assert entry.platform_id == "sofi"
        assert isinstance(entry.created_at, float)
        assert isinstance(entry.allowed_fields, frozenset)

    def test_process_pii_valid_token(self, pii_provider):
        """Test PII validation with a valid token."""
        token = pii_provider.issue_token("user@example.com")
        instrument = PIIInstrument(
            id="p1",
            handler_id="h1",
            handler_name="test",
            fields_stored=["first_name"],
            loan_type="personal",
            credential=PIICredential(type="token", token=token),
        )
        task = pii_provider.process_pii(instrument)
        assert task.status.state.value == "completed"

    def test_process_pii_invalid_token(self, pii_provider):
        """Test PII validation with an invalid token."""
        instrument = PIIInstrument(
            id="p1",
            handler_id="h1",
            handler_name="test",
            fields_stored=["first_name"],
            loan_type="personal",
            credential=PIICredential(type="token", token="bogus_token"),
        )
        task = pii_provider.process_pii(instrument)
        assert task.status.state.value == "failed"

    def test_store_pii_with_structured_address(self, pii_provider):
        """Test that store_pii accepts and stores structured PostalAddress."""
        result = pii_provider.store_pii(
            "addr@example.com",
            {
                "first_name": "Addr",
                "address": {
                    "street_address": "10 Structured Ave",
                    "address_locality": "Typesville",
                    "address_region": "NY",
                    "postal_code": "10001",
                    "address_country": "US",
                },
            },
        )
        assert result["status"] == "stored"
        assert "address" in result["fields_stored"]
        stored_addr = pii_provider._stored_pii["addr@example.com"]["address"]
        assert stored_addr["street_address"] == "10 Structured Ave"
        assert stored_addr["address_locality"] == "Typesville"

    def test_store_pii_validates_via_borrower_model(self, pii_provider):
        """Test that store_pii validates input through BorrowerPII model."""
        # Valid partial update should work
        result = pii_provider.store_pii(
            "valid@example.com",
            {"first_name": "Valid", "annual_income": "100000"},
        )
        assert result["status"] == "stored"
        assert "first_name" in result["fields_stored"]
        assert "annual_income" in result["fields_stored"]


# ---------- Test Lender Search ----------


class TestLenderSearch:
    """Tests for lender search and filtering via LoanProviderRegistry."""

    def test_get_all_lenders(self, loan_registry):
        """Test that all lenders are returned when no filter is applied."""
        lenders = loan_registry.get_lenders()
        assert len(lenders) >= 5
        names = [lndr.lender_name for lndr in lenders]
        assert "SoFi" in names
        assert "LendingClub" in names

    def test_get_lenders_filter_personal(self, loan_registry):
        """Test filtering lenders by personal loan type."""
        lenders = loan_registry.get_lenders(loan_type="personal")
        for lender in lenders:
            assert "personal" in lender.loan_types_offered
        # Capital One Auto should NOT be in personal results
        names = [lndr.lender_name for lndr in lenders]
        assert "Capital One Auto" not in names

    def test_get_lenders_filter_car(self, loan_registry):
        """Test filtering lenders by car loan type."""
        lenders = loan_registry.get_lenders(loan_type="car")
        for lender in lenders:
            assert "car" in lender.loan_types_offered
        names = [lndr.lender_name for lndr in lenders]
        assert "Capital One Auto" in names
        # LendingClub (personal only) should NOT be in car results
        assert "LendingClub" not in names

    def test_get_lenders_query(self, loan_registry):
        """Test fuzzy search by lender name."""
        lenders = loan_registry.get_lenders(query="sofi")
        assert len(lenders) >= 1
        assert lenders[0].lender_name == "SoFi"

    def test_get_lenders_query_no_match_returns_all(self, loan_registry):
        """Test that a non-matching query still returns the full list."""
        all_lenders = loan_registry.get_lenders()
        lenders = loan_registry.get_lenders(query="nonexistent_xyz_lender")
        assert len(lenders) == len(all_lenders)


# ---------- Test Multi-Lender Offers ----------


class TestMultiLenderOffers:
    """Tests for LoanProviderRegistry.apply_for_all_lenders with platform-scoped tokens."""

    def test_offers_come_from_multiple_lenders(self, loan_registry, pii_tokens):
        """Test that offers are generated from multiple different lenders."""
        offers = loan_registry.apply_for_all_lenders(
            pii_tokens,
            "personal",
            {
                "loan_amount_requested": 15000,
            },
        )
        assert len(offers) > 0
        lender_names = {o.lender_name for o in offers}
        assert len(lender_names) >= 2, (
            f"Expected offers from multiple lenders, got: {lender_names}"
        )

    def test_offers_sorted_by_rate(self, loan_registry, pii_tokens):
        """Test that offers are returned sorted by rate ascending."""
        offers = loan_registry.apply_for_all_lenders(
            pii_tokens,
            "personal",
            {
                "loan_amount_requested": 20000,
            },
        )
        rates = [o.rate for o in offers]
        assert rates == sorted(rates), "Offers should be sorted by rate ascending"

    def test_offers_have_valid_fields(self, loan_registry, pii_tokens):
        """Test that each offer has all required fields populated."""
        offers = loan_registry.apply_for_all_lenders(
            pii_tokens,
            "personal",
            {
                "loan_amount_requested": 10000,
            },
        )
        for offer in offers:
            assert isinstance(offer, LoanOffer)
            assert offer.lender_name
            assert offer.rate > 0
            assert offer.amount > 0
            assert offer.term_months > 0
            assert offer.monthly_payment > 0
            assert offer.continue_url.startswith("https://")

    def test_car_offers_use_car_value(self, loan_registry, pii_tokens):
        """Test that car loan offers use car_value for the amount."""
        car_value = 35000
        offers = loan_registry.apply_for_all_lenders(
            pii_tokens,
            "car",
            {
                "car_value": car_value,
            },
        )
        for offer in offers:
            assert offer.amount == car_value

    def test_car_offers_only_from_car_lenders(self, loan_registry, pii_tokens):
        """Test that car loan offers only come from lenders that support car loans."""
        offers = loan_registry.apply_for_all_lenders(
            pii_tokens, "car", {"car_value": 25000}
        )
        car_lenders = loan_registry.get_lenders(loan_type="car")
        car_lender_names = {lndr.lender_name for lndr in car_lenders}
        for offer in offers:
            assert offer.lender_name in car_lender_names

    def test_monthly_payment_reasonable(self, loan_registry, pii_tokens):
        """Test that monthly payments are mathematically reasonable."""
        loan_amount = 10000
        offers = loan_registry.apply_for_all_lenders(
            pii_tokens,
            "personal",
            {
                "loan_amount_requested": loan_amount,
            },
        )
        for offer in offers:
            # Monthly payment should be at least loan/term (zero-interest) and
            # less than the full loan amount
            min_payment = loan_amount / offer.term_months
            assert offer.monthly_payment >= min_payment * 0.95, (
                f"Monthly payment {offer.monthly_payment} too low for "
                f"${loan_amount} over {offer.term_months} months"
            )
            assert offer.monthly_payment < loan_amount, (
                f"Monthly payment {offer.monthly_payment} shouldn't exceed loan amount"
            )

    def test_lender_only_gets_own_token(self, loan_registry, pii_provider):
        """Test that each lender only receives its own platform-scoped token."""
        # Issue token only for sofi
        sofi_token = pii_provider.issue_token("foo@example.com", "sofi")
        partial_tokens = {"sofi": sofi_token}
        offers = loan_registry.apply_for_all_lenders(
            partial_tokens,
            "personal",
            {
                "loan_amount_requested": 10000,
            },
        )
        # Only SoFi should produce offers since no other lender has a token
        lender_names = {o.lender_name for o in offers}
        assert lender_names == {"SoFi"}


# ---------- Test Resolve Token ----------


class TestResolveToken:
    """Tests for MockPIIProvider.resolve_token with platform scoping."""

    def test_resolve_valid_token(self, pii_provider):
        """Test that a valid token resolves to the user's PII data."""
        token = pii_provider.issue_token("foo@example.com", "testplatform")
        data = pii_provider.resolve_token(token, "testplatform")
        assert data is not None
        assert data["first_name"] == "John"
        assert data["email"] == "foo@example.com"
        assert data["annual_income"] == "85000"

    def test_resolve_invalid_token(self, pii_provider):
        """Test that an invalid token returns None."""
        assert pii_provider.resolve_token("bogus_token", "any") is None

    def test_resolve_token_for_unknown_user(self, pii_provider):
        """Test resolving a token when the user has no stored PII."""
        import time

        pii_provider._tokens["manual_token"] = TokenEntry(
            email="ghost@example.com",
            platform_id="testplatform",
            created_at=time.time(),
            allowed_fields=frozenset(["first_name"]),
        )
        assert pii_provider.resolve_token("manual_token", "testplatform") is None

    def test_resolve_token_wrong_platform(self, pii_provider):
        """Test that a token minted for one platform cannot be used by another."""
        token = pii_provider.issue_token("foo@example.com", "sofi")
        assert pii_provider.resolve_token(token, "sofi") is not None
        assert pii_provider.resolve_token(token, "lendingclub") is None

    def test_resolve_token_expired(self, pii_provider, monkeypatch):
        """Test that an expired token returns None."""
        import time as time_mod

        token = pii_provider.issue_token("foo@example.com", "sofi")
        # Token should work before expiry
        assert pii_provider.resolve_token(token, "sofi") is not None

        # Advance time past the 1-hour TTL
        frozen = time_mod.time() + 3601
        monkeypatch.setattr("business_agent.pii_provider.time.time", lambda: frozen)
        assert pii_provider.resolve_token(token, "sofi") is None

    def test_process_pii_expired_token(self, pii_provider, monkeypatch):
        """Test that process_pii fails for an expired token."""
        import time as time_mod

        token = pii_provider.issue_token("foo@example.com", "sofi")
        instrument = PIIInstrument(
            id="test",
            handler_id="vgs_pii_provider",
            handler_name="vgs.pii.provider",
            credential=PIICredential(type="token", token=token),
            platform_id="sofi",
        )
        # Token should validate before expiry
        task = pii_provider.process_pii(instrument)
        assert task.status.state.value == "completed"

        # Advance time past the 1-hour TTL
        frozen = time_mod.time() + 3601
        monkeypatch.setattr("business_agent.pii_provider.time.time", lambda: frozen)
        task = pii_provider.process_pii(instrument)
        assert task.status.state.value == "failed"

    def test_resolve_token_returns_only_scoped_fields(self, pii_provider):
        """Test that resolve_token returns only the fields the token was scoped to."""
        token = pii_provider.issue_token(
            "foo@example.com", "testplatform", fields=["first_name", "email"]
        )
        data = pii_provider.resolve_token(token, "testplatform")
        assert data is not None
        assert set(data.keys()) == {"first_name", "email"}
        assert data["first_name"] == "John"
        assert data["email"] == "foo@example.com"

    def test_resolve_token_no_fields_returns_all_stored(self, pii_provider):
        """Test that a token issued without fields returns all stored fields."""
        token = pii_provider.issue_token("foo@example.com", "testplatform")
        data = pii_provider.resolve_token(token, "testplatform")
        assert data is not None
        # foo@example.com has 12 stored fields
        assert len(data) == 12
        assert "first_name" in data
        assert "employer_phone_number" in data

    def test_resolve_token_ignores_nonexistent_fields(self, pii_provider):
        """Test that requesting nonexistent fields doesn't cause errors."""
        token = pii_provider.issue_token(
            "foo@example.com", "testplatform", fields=["first_name", "nonexistent"]
        )
        data = pii_provider.resolve_token(token, "testplatform")
        assert data is not None
        # Only first_name is in stored PII; nonexistent is silently ignored
        assert set(data.keys()) == {"first_name"}


# ---------- Test Loan Provider Registry ----------


class TestLoanProviderRegistry:
    """Tests for LoanProviderRegistry and MockLoanProvider."""

    def test_get_required_pii_fields_personal(self, loan_registry):
        """Test getting required PII fields for personal loans."""
        fields = loan_registry.get_required_pii_fields("personal")
        assert fields == PERSONAL_LOAN_PII_FIELDS
        assert "first_name" in fields
        assert "annual_income" in fields

    def test_get_required_pii_fields_car(self, loan_registry):
        """Test getting required PII fields for car loans (superset of personal)."""
        fields = loan_registry.get_required_pii_fields("car")
        assert fields == CAR_LOAN_PII_FIELDS
        # Car loan includes all personal fields plus extras
        for pf in PERSONAL_LOAN_PII_FIELDS:
            assert pf in fields
        assert "employer_address" in fields
        assert "employer_phone_number" in fields
        assert "monthly_housing_payment" in fields
        assert "employment_status" in fields

    def test_get_required_pii_fields_unknown_defaults_to_personal(self, loan_registry):
        """Test that an unknown loan type falls back to personal loan fields."""
        fields = loan_registry.get_required_pii_fields("mortgage")
        assert fields == PERSONAL_LOAN_PII_FIELDS

    def test_get_required_non_pii_fields_personal(self, loan_registry):
        """Test non-PII fields for personal loans."""
        fields = loan_registry.get_required_non_pii_fields("personal")
        assert "loan_amount_requested" in fields
        assert "desired_monthly_payment" in fields

    def test_get_required_non_pii_fields_car(self, loan_registry):
        """Test non-PII fields for car loans."""
        fields = loan_registry.get_required_non_pii_fields("car")
        assert "car_brand" in fields
        assert "vin" in fields
        assert "car_value" in fields

    def test_registry_creates_providers_for_all_lenders(self, loan_registry):
        """Test that the registry has one provider per lender."""
        from business_agent.loan_provider import LENDER_LIST

        assert len(loan_registry._providers) == len(LENDER_LIST)

    def test_single_provider_generates_offers(self, pii_provider, monkeypatch):
        """Test that a single MockLoanProvider generates offers correctly."""
        mock_client = httpx.Client(transport=httpx.MockTransport(_mock_lender_transport))
        monkeypatch.setattr(httpx, "post", mock_client.post)
        lender = Lender(
            lender_name="TestBank",
            loan_types_offered=["personal"],
            description="A test lender",
            platform_id="testbank",
        )
        provider = MockLoanProvider(lender, pii_provider)
        token = pii_provider.issue_token("foo@example.com", "testbank")
        offers = provider.generate_offers(
            token, {"loan_amount_requested": 10000}, "personal"
        )
        assert len(offers) >= 1
        for offer in offers:
            assert offer.lender_name == "TestBank"
            assert offer.amount == 10000

    def test_single_provider_wrong_platform_returns_empty(self, pii_provider):
        """Test that a token minted for a different platform produces no offers."""
        lender = Lender(
            lender_name="TestBank",
            loan_types_offered=["personal"],
            description="A test lender",
            platform_id="testbank",
        )
        provider = MockLoanProvider(lender, pii_provider)
        # Issue token for a different platform
        token = pii_provider.issue_token("foo@example.com", "otherbank")
        offers = provider.generate_offers(
            token, {"loan_amount_requested": 10000}, "personal"
        )
        assert offers == []

    def test_single_provider_invalid_token_returns_empty(self, pii_provider):
        """Test that an invalid token produces no offers."""
        lender = Lender(
            lender_name="TestBank",
            loan_types_offered=["personal"],
            description="A test lender",
            platform_id="testbank",
        )
        provider = MockLoanProvider(lender, pii_provider)
        offers = provider.generate_offers(
            "bad_token", {"loan_amount_requested": 10000}, "personal"
        )
        assert offers == []

    def test_apply_for_all_invalid_token_returns_empty(self, loan_registry):
        """Test that apply_for_all_lenders with invalid tokens returns no offers."""
        offers = loan_registry.apply_for_all_lenders(
            {"sofi": "invalid_token", "lendingclub": "invalid_token"},
            "personal",
            {"loan_amount_requested": 10000},
        )
        assert offers == []


# ---------- Test PII Collection Flow ----------


class TestPIICollectionFlow:
    """End-to-end test for PII collection: new user -> store -> token -> validate."""

    def test_full_pii_collection_flow(self, pii_provider):
        """Test the complete PII collection flow for a brand new user."""
        email = "newuser@example.com"

        # Step 1: New user has all fields missing
        missing = pii_provider.get_missing_fields(email, PERSONAL_LOAN_PII_FIELDS)
        assert len(missing) == len(PERSONAL_LOAN_PII_FIELDS)

        # Step 2: Collect and store all required PII
        pii_data = {
            "first_name": "New",
            "last_name": "User",
            "email": email,
            "phone_number": "+15550001000",
            "address": {
                "street_address": "100 Test Blvd",
                "address_locality": "Testville",
                "address_region": "CA",
                "postal_code": "90000",
                "address_country": "US",
            },
            "date_of_birth": "1992-03-10",
            "annual_income": "72000",
            "living_situation": "rent",
        }
        result = pii_provider.store_pii(email, pii_data)
        assert result["status"] == "stored"
        assert len(result["fields_stored"]) == len(pii_data)

        # Step 3: Verify no fields are missing now
        missing_after = pii_provider.get_missing_fields(email, PERSONAL_LOAN_PII_FIELDS)
        assert missing_after == []

        # Step 4: Issue a token
        token = pii_provider.issue_token(email)
        assert token.startswith("pii_token_")

        # Step 5: Validate the token
        instrument = PIIInstrument(
            id="test_profile",
            handler_id="vgs_pii_provider",
            handler_name="vgs.pii.provider",
            fields_stored=list(pii_data.keys()),
            loan_type="personal",
            credential=PIICredential(type="token", token=token),
        )
        task = pii_provider.process_pii(instrument)
        assert task.status.state.value == "completed"

    def test_incremental_collection(self, pii_provider):
        """Test collecting PII in multiple steps."""
        email = "step@example.com"

        # Store first batch
        pii_provider.store_pii(
            email,
            {
                "first_name": "Step",
                "last_name": "User",
                "email": email,
                "phone_number": "+15551111000",
            },
        )
        missing = pii_provider.get_missing_fields(email, PERSONAL_LOAN_PII_FIELDS)
        assert "first_name" not in missing
        assert "address" in missing  # Still missing

        # Store second batch
        pii_provider.store_pii(
            email,
            {
                "address": {
                    "street_address": "200 Step St",
                    "address_locality": "Stepville",
                    "address_region": "CA",
                    "postal_code": "90001",
                },
                "date_of_birth": "1990-01-01",
                "annual_income": "60000",
                "living_situation": "fully_own",
            },
        )
        missing = pii_provider.get_missing_fields(email, PERSONAL_LOAN_PII_FIELDS)
        assert missing == []


    def test_incremental_collection_across_loan_types(self, pii_provider):
        """Test that switching from personal to car loan only requires the delta fields.

        Personal loan needs 8 fields. Car loan needs those 8 + 4 more.
        After storing personal loan PII, starting a car loan should report
        only the 4 additional fields as missing.
        """
        email = "crossloan@example.com"

        # Store all personal loan PII
        pii_provider.store_pii(
            email,
            {
                "first_name": "Cross",
                "last_name": "Loan",
                "email": email,
                "phone_number": "+15559990000",
                "address": {
                    "street_address": "300 Cross St",
                    "address_locality": "Loanville",
                    "address_region": "CA",
                    "postal_code": "90002",
                    "address_country": "US",
                },
                "date_of_birth": "1988-06-15",
                "annual_income": "95000",
                "living_situation": "mortgage",
            },
        )

        # Personal loan: all fields present
        missing_personal = pii_provider.get_missing_fields(
            email, PERSONAL_LOAN_PII_FIELDS
        )
        assert missing_personal == []

        # Car loan: only the 4 additional fields should be missing
        missing_car = pii_provider.get_missing_fields(email, CAR_LOAN_PII_FIELDS)
        assert sorted(missing_car) == sorted([
            "monthly_housing_payment",
            "employment_status",
            "employer_address",
            "employer_phone_number",
        ])

        # Store the car-specific fields
        pii_provider.store_pii(
            email,
            {
                "monthly_housing_payment": "2800",
                "employment_status": "employed",
                "employer_address": {
                    "street_address": "500 Work Ave",
                    "address_locality": "Worktown",
                    "address_region": "CA",
                    "postal_code": "90003",
                    "address_country": "US",
                },
                "employer_phone_number": "+15558887777",
            },
        )

        # Now car loan should have all fields
        missing_car_after = pii_provider.get_missing_fields(
            email, CAR_LOAN_PII_FIELDS
        )
        assert missing_car_after == []


# ---------- Test Capability Negotiation ----------


class TestCapabilityNegotiation:
    """Tests for lending capability negotiation."""

    def test_lending_extension_constant(self):
        """Test that the lending extension URL constant is correct."""
        assert UCP_LENDING_EXTENSION == "com.viaschema.lending"

    def test_type_generator_includes_lending(self):
        """Test that type_generator includes LendingCheckout when lending is active."""
        from ucp_sdk.models.schemas.capability import Response as CapResponse
        from ucp_sdk.models.schemas.ucp import ResponseCheckout

        from business_agent.helpers.type_generator import get_checkout_type

        ucp_metadata = ResponseCheckout(
            version="2026-01-11",
            capabilities=[
                CapResponse(name="dev.ucp.shopping.checkout"),
                CapResponse(name="com.viaschema.lending"),
            ],
        )
        checkout_type = get_checkout_type(ucp_metadata)
        # Should have 'lending' field from LendingCheckout
        assert "lending" in checkout_type.model_fields

    def test_type_generator_excludes_lending(self):
        """Test that type_generator excludes lending field when capability is absent."""
        from ucp_sdk.models.schemas.capability import Response as CapResponse
        from ucp_sdk.models.schemas.ucp import ResponseCheckout

        from business_agent.helpers.type_generator import get_checkout_type

        ucp_metadata = ResponseCheckout(
            version="2026-01-11",
            capabilities=[
                CapResponse(name="dev.ucp.shopping.checkout"),
            ],
        )
        checkout_type = get_checkout_type(ucp_metadata)
        # Should NOT have 'lending' field
        assert "lending" not in checkout_type.model_fields

    def test_lending_response_model(self):
        """Test LendingResponse model instantiation."""
        response = LendingResponse(
            loan_type="personal",
            status="consent_needed",
            handlers=[],
            required_pii_fields=["first_name", "last_name"],
            required_non_pii_fields=["loan_amount_requested"],
        )
        assert response.loan_type == "personal"
        assert response.status == "consent_needed"
        assert response.missing_pii_fields is None

    def test_lending_response_with_missing_fields(self):
        """Test LendingResponse model with missing PII fields."""
        response = LendingResponse(
            loan_type="car",
            status="pii_missing",
            handlers=[],
            required_pii_fields=CAR_LOAN_PII_FIELDS,
            missing_pii_fields=["address", "annual_income"],
        )
        assert response.status == "pii_missing"
        assert len(response.missing_pii_fields) == 2


# ---------- Test Pre-seeded Data ----------


class TestPreSeededData:
    """Tests for pre-seeded demo user data."""

    def test_pre_seeded_user_has_data(self, pii_provider):
        """Test that foo@example.com is pre-seeded with PII."""
        fields = pii_provider.get_stored_fields("foo@example.com")
        assert "first_name" in fields
        assert "last_name" in fields
        assert "email" in fields
        assert "annual_income" in fields
        assert len(fields) >= 8

    def test_pre_seeded_user_no_missing_personal_fields(self, pii_provider):
        """Test that foo@example.com has no missing personal loan fields."""
        missing = pii_provider.get_missing_fields(
            "foo@example.com", PERSONAL_LOAN_PII_FIELDS
        )
        assert missing == []

    def test_pre_seeded_user_no_missing_car_fields(self, pii_provider):
        """Test that foo@example.com has no missing car loan fields."""
        missing = pii_provider.get_missing_fields(
            "foo@example.com", CAR_LOAN_PII_FIELDS
        )
        assert missing == []


# ---------- Test PII Vault HTTP Endpoints ----------


class TestPIIVaultEndpoints:
    """Tests for PII vault HTTP endpoints (store, stored-fields, token)."""

    @pytest.fixture
    def vault_client(self, empty_pii_provider):
        """Create a Starlette TestClient with PII vault routes."""
        from starlette.applications import Starlette
        from starlette.testclient import TestClient

        app = Starlette(routes=create_pii_vault_routes(empty_pii_provider))
        return TestClient(app), empty_pii_provider

    def test_pii_store_endpoint(self, vault_client):
        """Test POST /pii/store stores PII and returns stored fields."""
        client, provider = vault_client
        response = client.post(
            "/pii/store",
            json={
                "email": "test@example.com",
                "pii_data": {"first_name": "Test", "last_name": "User"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stored"
        assert "first_name" in data["fields_stored"]
        assert "last_name" in data["fields_stored"]

    def test_pii_stored_fields_endpoint_with_data(self, vault_client):
        """Test POST /pii/stored-fields returns fields for a user with data."""
        client, provider = vault_client
        # Store some data first
        provider.store_pii(
            "user@example.com",
            {
                "first_name": "John",
                "email": "user@example.com",
            },
        )

        response = client.post(
            "/pii/stored-fields",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["pii_methods"]) == 1
        method = data["pii_methods"][0]
        assert method["id"] == "pii_profile_1"
        assert "first_name" in method["fields_stored"]
        assert "email" in method["fields_stored"]
        assert method["loan_type"] == "all"

    def test_pii_stored_fields_endpoint_empty_user(self, vault_client):
        """Test POST /pii/stored-fields returns empty for unknown user."""
        client, _ = vault_client
        response = client.post(
            "/pii/stored-fields",
            json={"email": "unknown@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        method = data["pii_methods"][0]
        assert method["fields_stored"] == []

    def _make_consent(self, **overrides) -> dict:
        """Helper to build a valid PIIConsent payload."""
        defaults = {
            "pii_method_id": "pii_profile_1",
            "handler_id": "vgs_pii_provider",
            "fields_consented": ["first_name"],
            "loan_type": "personal",
            "platform_ids": ["sofi"],
            "consented_at": "2026-01-15T12:00:00Z",
        }
        defaults.update(overrides)
        return defaults

    def test_pii_consent_endpoint(self, vault_client):
        """Test POST /pii/consent returns consent_id and PIIInstruments."""
        client, provider = vault_client
        provider.store_pii("user@example.com", {"first_name": "John"})

        response = client.post(
            "/pii/consent",
            json={
                "email": "user@example.com",
                "consent": self._make_consent(
                    platform_ids=["sofi", "lendingclub"],
                ),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["consent_id"].startswith("consent_")

        instruments = data["instruments"]
        assert len(instruments) == 2

        platform_ids = {i["platform_id"] for i in instruments}
        assert platform_ids == {"sofi", "lendingclub"}

        for inst in instruments:
            assert inst["id"] == "pii_profile_1"
            assert inst["handler_id"] == "vgs_pii_provider"
            assert inst["handler_name"] == "vgs_pii_provider"
            assert "first_name" in inst["fields_stored"]
            assert inst["loan_type"] == "personal"
            assert inst["credential"]["type"] == "token"
            assert inst["credential"]["token"].startswith("pii_token_")

    def test_pii_consent_token_validates_on_backend(self, vault_client):
        """Test that tokens from /pii/consent pass process_pii validation."""
        client, provider = vault_client
        provider.store_pii("user@example.com", {"first_name": "John"})

        response = client.post(
            "/pii/consent",
            json={
                "email": "user@example.com",
                "consent": self._make_consent(platform_ids=["sofi"]),
            },
        )
        instrument_data = response.json()["instruments"][0]

        instrument = PIIInstrument(
            id=instrument_data["id"],
            handler_id=instrument_data["handler_id"],
            handler_name=instrument_data["handler_name"],
            fields_stored=instrument_data["fields_stored"],
            loan_type=instrument_data["loan_type"],
            platform_id=instrument_data["platform_id"],
            credential=PIICredential(
                type=instrument_data["credential"]["type"],
                token=instrument_data["credential"]["token"],
            ),
        )
        task = provider.process_pii(instrument)
        assert task.status.state.value == "completed"

    def test_full_vault_round_trip(self, vault_client):
        """Test the full round-trip: store → stored-fields → consent → validate."""
        client, provider = vault_client
        email = "roundtrip@example.com"

        # Step 1: Store PII
        store_resp = client.post(
            "/pii/store",
            json={
                "email": email,
                "pii_data": {
                    "first_name": "Round",
                    "last_name": "Trip",
                    "email": email,
                    "phone_number": "+15550000000",
                    "address": {
                        "street_address": "1 Test Lane",
                        "address_locality": "Testtown",
                        "address_region": "TX",
                        "postal_code": "75001",
                        "address_country": "US",
                    },
                    "date_of_birth": "1990-01-01",
                    "annual_income": "50000",
                    "living_situation": "rent",
                },
            },
        )
        assert store_resp.status_code == 200
        assert store_resp.json()["status"] == "stored"

        # Step 2: Verify stored fields
        fields_resp = client.post(
            "/pii/stored-fields",
            json={"email": email},
        )
        stored = fields_resp.json()["pii_methods"][0]["fields_stored"]
        assert len(stored) == 8

        # Step 3: Submit consent and get tokens
        consent_resp = client.post(
            "/pii/consent",
            json={
                "email": email,
                "consent": self._make_consent(
                    fields_consented=sorted(stored),
                    platform_ids=["sofi"],
                ),
            },
        )
        assert consent_resp.status_code == 200
        consent_data = consent_resp.json()
        assert consent_data["consent_id"].startswith("consent_")

        instrument_data = consent_data["instruments"][0]
        token = instrument_data["credential"]["token"]
        assert token.startswith("pii_token_")

        # Step 4: Validate token
        instrument = PIIInstrument(
            id=instrument_data["id"],
            handler_id=instrument_data["handler_id"],
            handler_name=instrument_data["handler_name"],
            fields_stored=instrument_data["fields_stored"],
            loan_type=instrument_data["loan_type"],
            platform_id=instrument_data["platform_id"],
            credential=PIICredential(
                type=instrument_data["credential"]["type"],
                token=token,
            ),
        )
        task = provider.process_pii(instrument)
        assert task.status.state.value == "completed"

    def test_pii_consent_cross_platform_rejection(self, vault_client):
        """Test that platform-scoped tokens only resolve for their platform."""
        client, provider = vault_client
        provider.store_pii("user@example.com", {"first_name": "John"})

        response = client.post(
            "/pii/consent",
            json={
                "email": "user@example.com",
                "consent": self._make_consent(
                    platform_ids=["sofi", "lendingclub"],
                ),
            },
        )
        instruments = response.json()["instruments"]
        sofi_token = next(i for i in instruments if i["platform_id"] == "sofi")[
            "credential"
        ]["token"]

        # Token minted for sofi should resolve for sofi
        data = provider.resolve_token(sofi_token, "sofi")
        assert data is not None

        # Token minted for sofi should NOT resolve for lendingclub
        data = provider.resolve_token(sofi_token, "lendingclub")
        assert data is None

    def test_pii_consent_scopes_tokens_to_consented_fields(self, vault_client):
        """Test that /pii/consent scopes tokens to only the consented fields."""
        client, provider = vault_client
        provider.store_pii(
            "user@example.com",
            {"first_name": "John", "last_name": "Doe", "email": "user@example.com"},
        )

        response = client.post(
            "/pii/consent",
            json={
                "email": "user@example.com",
                "consent": self._make_consent(
                    fields_consented=["first_name", "email"],
                    platform_ids=["sofi", "lendingclub"],
                ),
            },
        )
        assert response.status_code == 200
        instruments = response.json()["instruments"]
        assert len(instruments) == 2

        for inst in instruments:
            assert sorted(inst["fields_stored"]) == ["email", "first_name"]
            token = inst["credential"]["token"]
            data = provider.resolve_token(token, inst["platform_id"])
            assert set(data.keys()) == {"first_name", "email"}

    def test_pii_consent_records_consent(self, vault_client):
        """Test that /pii/consent records the consent internally."""
        client, provider = vault_client
        provider.store_pii("user@example.com", {"first_name": "John"})

        consent_payload = self._make_consent(
            platform_ids=["sofi"],
            fields_consented=["first_name"],
        )
        response = client.post(
            "/pii/consent",
            json={"email": "user@example.com", "consent": consent_payload},
        )
        consent_id = response.json()["consent_id"]

        assert consent_id in provider._consents
        recorded = provider._consents[consent_id]
        assert recorded.pii_method_id == "pii_profile_1"
        assert recorded.fields_consented == ["first_name"]
        assert recorded.platform_ids == ["sofi"]

    def test_pii_consent_rejects_empty_platforms(self, vault_client):
        """Test that /pii/consent rejects consent with no platform_ids."""
        client, provider = vault_client
        provider.store_pii("user@example.com", {"first_name": "John"})

        response = client.post(
            "/pii/consent",
            json={
                "email": "user@example.com",
                "consent": self._make_consent(platform_ids=[]),
            },
        )
        assert response.status_code == 400
        assert "platform_ids" in response.json()["error"]
