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

"""Tests for appointment booking functionality."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from business_agent.models.appointment_types import (
    Address,
    AppointmentRequest,
    AppointmentSlotRequest,
    AvailabilitySlot,
    Booking,
    Customer,
    Location,
    LocationSummary,
    ServiceVariation,
    StaffResponse,
    StaffSummaryResponse,
)
from business_agent.square_client import SquareServiceClient
from business_agent.store import ServiceStore


# ---------- Fixtures ----------


@pytest.fixture
def mock_square_client():
    """Create a mock Square client."""
    with patch("business_agent.store.SquareServiceClient") as mock_cls:
        mock_client = MagicMock(spec=SquareServiceClient)
        mock_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_location():
    """Create a sample Location object."""
    return Location(
        id="loc_123",
        name="Downtown Salon",
        address=Address(
            address_line_1="123 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94105",
            country="US",
        ),
        timezone="America/Los_Angeles",
        status="active",
    )


@pytest.fixture
def sample_staff():
    """Create a sample StaffResponse object."""
    return StaffResponse(
        id="staff_123",
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="555-1234",
        locations=[LocationSummary(id="loc_123", name="Downtown Salon")],
    )


@pytest.fixture
def sample_service():
    """Create a sample ServiceVariation object."""
    return ServiceVariation(
        id="svc_123",
        service_id="item_123",
        name="Haircut - Standard",
        description="A standard haircut",
        display_price="$50.00",
        price=50.0,
        duration_seconds=1800,  # 30 minutes
    )


@pytest.fixture
def sample_availability_slot(sample_staff):
    """Create a sample AvailabilitySlot object."""
    start = datetime.now(timezone.utc) + timedelta(days=1)
    return AvailabilitySlot(
        start_time=start,
        end_time=start + timedelta(minutes=30),
        staff=StaffSummaryResponse(
            id=sample_staff.id,
            name=f"{sample_staff.first_name} {sample_staff.last_name}",
            first_name=sample_staff.first_name,
            last_name=sample_staff.last_name,
            available_at=[LocationSummary(id="loc_123", name="Downtown Salon")],
        ),
        location=LocationSummary(id="loc_123", name="Downtown Salon"),
    )


@pytest.fixture
def sample_booking(sample_location):
    """Create a sample Booking object."""
    start = datetime.now(timezone.utc) + timedelta(days=1)
    return Booking(
        id="booking_123",
        location=sample_location,
        customer=Customer(
            id="cust_123",
            first_name="John",
            last_name="Smith",
            email="john@example.com",
            phone="555-5678",
        ),
        start_time=start,
        duration_minutes=30,
        segments=[],
    )


@pytest.fixture
def mock_ucp_metadata():
    """Create mock UCP metadata."""
    from ucp_sdk.models._internal import Response
    from ucp_sdk.models.schemas.ucp import ResponseCheckout

    return ResponseCheckout(
        version="2026-01-11",
        capabilities=[
            Response(name="dev.ucp.shopping.checkout", version="2026-01-11"),
            Response(name="com.viaschema.appointment", version="2026-01-11"),
        ],
    )


# ---------- ServiceStore Tests ----------


class TestServiceStore:
    """Tests for ServiceStore class."""

    def test_init_without_token(self):
        """Test initialization without Square token."""
        with patch.dict("os.environ", {"SQUARE_ACCESS_TOKEN": ""}):
            store = ServiceStore(square_token="")
            assert store.square is None

    def test_init_with_token(self, mock_square_client):
        """Test initialization with Square token."""
        store = ServiceStore(square_token="test_token")
        assert store.square is not None

    def test_search_services(self, mock_square_client, sample_service):
        """Test searching for services returns ServiceVariation list."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.list_service_variations.return_value = [sample_service]

        results = store.search_services("haircut")

        assert len(results) == 1
        assert results[0].id == sample_service.id
        assert results[0].name == sample_service.name
        mock_square_client.list_service_variations.assert_called_once_with("haircut")

    def test_list_locations(self, mock_square_client, sample_location):
        """Test listing locations."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.list_locations.return_value = [sample_location]

        results = store.list_locations()

        assert len(results) == 1
        assert results[0].id == sample_location.id
        mock_square_client.list_locations.assert_called_once()

    def test_list_staff(self, mock_square_client, sample_staff):
        """Test listing staff members."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.list_staff.return_value = [sample_staff]

        results = store.list_staff()

        assert len(results) == 1
        assert results[0].id == sample_staff.id
        mock_square_client.list_staff.assert_called_once()

    def test_search_availability(self, mock_square_client, sample_availability_slot):
        """Test searching for available slots."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.search_availability.return_value = [sample_availability_slot]

        start = date.today()
        end = date.today() + timedelta(days=7)
        results = store.search_availability(start, end)

        assert len(results) == 1
        mock_square_client.search_availability.assert_called_once()

    def test_add_service_to_checkout(
        self, mock_square_client, mock_ucp_metadata, sample_service
    ):
        """Test adding a service creates checkout."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.get_service_variation.return_value = sample_service

        checkout = store.add_to_checkout(
            metadata=mock_ucp_metadata,
            service_variation_id=sample_service.id,
            quantity=1,
        )

        assert checkout is not None
        assert len(checkout.line_items) == 1
        assert checkout.line_items[0].item.id == sample_service.id

    def test_add_service_with_appointment(
        self,
        mock_square_client,
        mock_ucp_metadata,
        sample_service,
        sample_location,
    ):
        """Test adding a service with appointment details creates slot."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.get_service_variation.return_value = sample_service
        mock_square_client.get_location.return_value = sample_location

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        checkout = store.add_to_checkout(
            metadata=mock_ucp_metadata,
            service_variation_id=sample_service.id,
            quantity=1,
            location_id=sample_location.id,
            start_time=start_time,
        )

        assert checkout is not None
        assert checkout.appointment is not None
        assert len(checkout.appointment.slots) == 1
        assert checkout.appointment.slots[0].location.id == sample_location.id

    def test_remove_from_checkout(
        self, mock_square_client, mock_ucp_metadata, sample_service
    ):
        """Test removing a service from checkout."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.get_service_variation.return_value = sample_service

        # Add service first
        checkout = store.add_to_checkout(
            metadata=mock_ucp_metadata,
            service_variation_id=sample_service.id,
            quantity=1,
        )
        line_item_id = checkout.line_items[0].id

        # Remove it
        updated = store.remove_from_checkout(checkout.id, line_item_id)

        assert len(updated.line_items) == 0

    def test_update_checkout_quantity(
        self, mock_square_client, mock_ucp_metadata, sample_service
    ):
        """Test updating quantity of a line item."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.get_service_variation.return_value = sample_service

        checkout = store.add_to_checkout(
            metadata=mock_ucp_metadata,
            service_variation_id=sample_service.id,
            quantity=1,
        )
        line_item_id = checkout.line_items[0].id

        updated = store.update_checkout(
            checkout_id=checkout.id,
            line_item_id=line_item_id,
            quantity=2,
        )

        assert updated.line_items[0].quantity == 2

    def test_set_appointment(
        self,
        mock_square_client,
        mock_ucp_metadata,
        sample_service,
        sample_location,
    ):
        """Test set_appointment applies AppointmentRequest to checkout."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.get_service_variation.return_value = sample_service
        mock_square_client.get_location.return_value = sample_location

        # Add service without appointment
        checkout = store.add_to_checkout(
            metadata=mock_ucp_metadata,
            service_variation_id=sample_service.id,
            quantity=1,
        )
        line_item_id = checkout.line_items[0].id

        # Set appointment
        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        appointment = AppointmentRequest(
            slots=[
                AppointmentSlotRequest(
                    line_item_ids=[line_item_id],
                    location_id=sample_location.id,
                    start_time=start_time,
                )
            ]
        )

        updated = store.set_appointment(checkout.id, appointment)

        assert updated.appointment is not None
        assert len(updated.appointment.slots) == 1
        assert line_item_id in updated.appointment.slots[0].line_item_ids

    def test_get_bookings(self, mock_square_client, sample_booking):
        """Test getting existing bookings."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.get_bookings.return_value = [sample_booking]

        results = store.get_bookings()

        assert len(results) == 1
        assert results[0].id == sample_booking.id
        mock_square_client.get_bookings.assert_called_once()

    def test_cancel_booking(self, mock_square_client):
        """Test cancelling a booking."""
        store = ServiceStore(square_token="test_token")
        store.square = mock_square_client
        mock_square_client.cancel_booking.return_value = "Booking cancelled"

        result = store.cancel_booking("booking_123")

        assert "cancelled" in result.lower()
        mock_square_client.cancel_booking.assert_called_once_with("booking_123")


# ---------- SquareServiceClient Tests ----------


class TestSquareClient:
    """Tests for SquareServiceClient class."""

    @patch("business_agent.square_client.Square")
    def test_init_sandbox(self, mock_square_cls):
        """Test client initialization in sandbox mode."""
        _ = SquareServiceClient(token="test_token", sandbox=True)
        mock_square_cls.assert_called_once()

    @patch("business_agent.square_client.Square")
    def test_list_locations_empty(self, mock_square_cls):
        """Test listing locations when empty."""
        mock_square = MagicMock()
        mock_square.locations.list.return_value = MagicMock(errors=None, locations=[])
        mock_square_cls.return_value = mock_square

        client = SquareServiceClient(token="test_token")
        results = client.list_locations()

        assert results == []

    @patch("business_agent.square_client.Square")
    def test_list_locations_with_filter(self, mock_square_cls):
        """Test listing locations with query filter."""
        # Create address mock
        mock_address = MagicMock()
        mock_address.address_line1 = "123 Main St"
        mock_address.address_line2 = None
        mock_address.locality = "San Francisco"
        mock_address.administrative_district_level1 = "CA"
        mock_address.postal_code = "94105"
        mock_address.country = "US"

        # Create location mock - using configure_mock for 'name' attribute
        mock_location = MagicMock()
        mock_location.id = "loc_1"
        mock_location.configure_mock(name="Downtown Location")
        mock_location.address = mock_address
        mock_location.coordinates = None
        mock_location.timezone = "America/Los_Angeles"
        mock_location.status = "ACTIVE"
        mock_location.description = None

        mock_square = MagicMock()
        mock_square.locations.list.return_value = MagicMock(
            errors=None, locations=[mock_location]
        )
        mock_square_cls.return_value = mock_square

        client = SquareServiceClient(token="test_token")
        results = client.list_locations(query="downtown")

        assert len(results) == 1
        assert results[0].name == "Downtown Location"


# ---------- Agent Tools Tests ----------


class TestAgentTools:
    """Tests for agent tool functions."""

    def test_search_shopping_catalog_returns_services(
        self, mock_square_client, sample_service
    ):
        """Test catalog search returns service variations."""
        from business_agent.agent import search_shopping_catalog, store

        store.square = mock_square_client
        mock_square_client.list_service_variations.return_value = [sample_service]

        mock_context = MagicMock()
        result = search_shopping_catalog(mock_context, "haircut")

        assert "a2a.service_results" in result
        assert len(result["a2a.service_results"]) == 1

    def test_add_to_checkout_service_only(
        self, mock_square_client, mock_ucp_metadata, sample_service
    ):
        """Test add_to_checkout adds service without appointment."""
        from business_agent.agent import add_to_checkout, store
        from business_agent.constants import ADK_UCP_METADATA_STATE

        store.square = mock_square_client
        mock_square_client.get_service_variation.return_value = sample_service

        mock_context = MagicMock()
        mock_context.state = {ADK_UCP_METADATA_STATE: mock_ucp_metadata}

        result = add_to_checkout(
            mock_context,
            service_variation_id=sample_service.id,
        )

        assert result["status"] == "success"
        assert "a2a.ucp.checkout" in result

    def test_add_to_checkout_with_appointment(
        self,
        mock_square_client,
        mock_ucp_metadata,
        sample_service,
        sample_location,
    ):
        """Test add_to_checkout with location_id, start_time creates slot."""
        from business_agent.agent import add_to_checkout, store
        from business_agent.constants import ADK_UCP_METADATA_STATE

        store.square = mock_square_client
        mock_square_client.get_service_variation.return_value = sample_service
        mock_square_client.get_location.return_value = sample_location

        mock_context = MagicMock()
        mock_context.state = {ADK_UCP_METADATA_STATE: mock_ucp_metadata}

        start_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        result = add_to_checkout(
            mock_context,
            service_variation_id=sample_service.id,
            location_id=sample_location.id,
            start_time=start_time,
        )

        assert result["status"] == "success"
        checkout_data = result["a2a.ucp.checkout"]
        assert checkout_data.get("appointment") is not None

    def test_list_locations_tool(self, mock_square_client, sample_location):
        """Test list_locations tool."""
        from business_agent.agent import list_locations, store

        store.square = mock_square_client
        mock_square_client.list_locations.return_value = [sample_location]

        mock_context = MagicMock()
        result = list_locations(mock_context)

        assert "a2a.locations" in result
        assert len(result["a2a.locations"]) == 1

    def test_list_staff_tool(self, mock_square_client, sample_staff):
        """Test list_staff tool."""
        from business_agent.agent import list_staff, store

        store.square = mock_square_client
        mock_square_client.list_staff.return_value = [sample_staff]

        mock_context = MagicMock()
        result = list_staff(mock_context)

        assert "a2a.staff" in result
        assert len(result["a2a.staff"]) == 1

    def test_search_availability_tool(
        self, mock_square_client, sample_availability_slot
    ):
        """Test search_availability tool."""
        from business_agent.agent import search_availability, store

        store.square = mock_square_client
        mock_square_client.search_availability.return_value = [sample_availability_slot]

        mock_context = MagicMock()
        today = date.today()
        result = search_availability(
            mock_context,
            start_date=today.isoformat(),
            end_date=(today + timedelta(days=7)).isoformat(),
        )

        assert "a2a.availability_slots" in result
        assert len(result["a2a.availability_slots"]) == 1

    def test_get_bookings_tool(self, mock_square_client, sample_booking):
        """Test get_bookings tool."""
        from business_agent.agent import get_bookings, store

        store.square = mock_square_client
        mock_square_client.get_bookings.return_value = [sample_booking]

        mock_context = MagicMock()
        result = get_bookings(mock_context)

        assert "a2a.bookings" in result
        assert len(result["a2a.bookings"]) == 1

    def test_cancel_booking_tool(self, mock_square_client):
        """Test cancel_booking tool."""
        from business_agent.agent import cancel_booking, store

        store.square = mock_square_client
        mock_square_client.cancel_booking.return_value = "Booking cancelled"

        mock_context = MagicMock()
        result = cancel_booking(mock_context, "booking_123")

        assert result["status"] == "success"
        assert "cancelled" in result["message"].lower()


# ---------- Integration Tests ----------


class TestWorkflowIntegration:
    """Integration tests for full booking workflow."""

    def test_full_booking_workflow(
        self,
        mock_square_client,
        mock_ucp_metadata,
        sample_service,
        sample_location,
        sample_booking,
    ):
        """Test full workflow: search -> add -> schedule -> complete."""
        from business_agent.agent import (
            add_to_checkout,
            search_shopping_catalog,
            set_appointment,
            store,
        )
        from business_agent.constants import (
            ADK_UCP_METADATA_STATE,
            ADK_USER_CHECKOUT_ID,
        )

        store.square = mock_square_client
        mock_square_client.list_service_variations.return_value = [sample_service]
        mock_square_client.get_service_variation.return_value = sample_service
        mock_square_client.get_location.return_value = sample_location
        mock_square_client.create_booking.return_value = sample_booking

        mock_context = MagicMock()
        mock_context.state = {ADK_UCP_METADATA_STATE: mock_ucp_metadata}

        # Step 1: Search for services
        search_result = search_shopping_catalog(mock_context, "haircut")
        assert "a2a.service_results" in search_result
        assert len(search_result["a2a.service_results"]) > 0

        # Step 2: Add service to checkout
        add_result = add_to_checkout(
            mock_context,
            service_variation_id=sample_service.id,
        )
        assert add_result["status"] == "success"

        # Update context with checkout ID
        checkout_data = add_result["a2a.ucp.checkout"]
        mock_context.state[ADK_USER_CHECKOUT_ID] = checkout_data["id"]

        # Step 3: Set appointment
        line_item_id = checkout_data["line_items"][0]["id"]
        start_time = datetime.now(timezone.utc) + timedelta(days=1)

        appt_result = set_appointment(
            mock_context,
            slots=[
                {
                    "line_item_ids": [line_item_id],
                    "location_id": sample_location.id,
                    "start_time": start_time.isoformat(),
                }
            ],
        )
        assert appt_result["status"] == "success"
        checkout_data = appt_result["a2a.ucp.checkout"]
        assert checkout_data.get("appointment") is not None
        assert len(checkout_data["appointment"]["slots"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
