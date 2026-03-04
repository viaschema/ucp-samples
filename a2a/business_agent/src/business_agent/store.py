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

"""Service Store for appointment booking using Square backend.

The store manages core checkout lifecycle (create, line items, totals,
payment, order). Domain-specific logic (appointment slots, lending
initialization) is delegated to the ``AppointmentManager`` and the
``DomainRegistry.initialize_checkout`` hook respectively.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import AnyUrl
from ucp_sdk.models.schemas.shopping.payment_resp import PaymentResponse
from ucp_sdk.models.schemas.shopping.types.item_resp import ItemResponse as Item
from ucp_sdk.models.schemas.shopping.types.line_item_resp import (
    LineItemResponse as LineItem,
)
from ucp_sdk.models.schemas.shopping.types.order_confirmation import (
    OrderConfirmation,
)
from ucp_sdk.models.schemas.shopping.types.total_resp import (
    TotalResponse as Total,
)
from ucp_sdk.models.schemas.ucp import ResponseCheckout as UcpMetadata

from .appointment_manager import AppointmentManager
from .constants import SQUARE_ACCESS_TOKEN, SQUARE_SANDBOX
from .helpers import get_checkout_type
from .models.appointment_types import (
    AppointmentCheckoutResponse,
    AppointmentRequest,
    AvailabilitySlot,
    Booking,
    Location,
    ServiceVariation,
    StaffResponse,
)
from .square_client import SquareServiceClient


DEFAULT_CURRENCY = "USD"
logger = logging.getLogger(__name__)


class ServiceStore:
    """Service Store for appointment booking using Square backend.

    Uses Square API for service catalog, availability, and bookings.
    Maintains local checkout state. Delegates appointment-slot logic
    to ``AppointmentManager``.
    """

    def __init__(self, square_token: str | None = None, sandbox: bool | None = None):
        """Initialize the service store.

        Args:
            square_token: Square API access token. If None, uses env var.
            sandbox: Whether to use sandbox environment. If None, uses env var.
        """
        token = square_token or SQUARE_ACCESS_TOKEN
        is_sandbox = sandbox if sandbox is not None else SQUARE_SANDBOX

        if token:
            self.square = SquareServiceClient(token=token, sandbox=is_sandbox)
        else:
            self.square = None
            logger.warning(
                "No Square access token provided. Square features will be disabled."
            )

        self._checkouts: dict[str, AppointmentCheckoutResponse] = {}
        self._orders: dict[str, AppointmentCheckoutResponse] = {}
        self._service_cache: dict[str, ServiceVariation] = {}
        self._initialize_ucp_metadata()

        # Appointment slot management is delegated to AppointmentManager
        self.appointments = AppointmentManager(
            square_client=self.square,
            service_resolver=self.get_service_variation,
        )

    def _initialize_ucp_metadata(self):
        """Load UCP metadata from data/ucp.json."""
        base_path = Path(__file__).parent
        ucp_path = base_path / "data" / "ucp.json"
        with ucp_path.open() as f:
            self._ucp_metadata = json.load(f)

    @property
    def ucp_metadata(self) -> dict:
        """Return the loaded UCP metadata."""
        return self._ucp_metadata

    def save_checkout(
        self, checkout_id: str, checkout: AppointmentCheckoutResponse
    ) -> None:
        """Save a checkout object by ID.

        Args:
            checkout_id: Checkout ID.
            checkout: The checkout object to save.
        """
        self._checkouts[checkout_id] = checkout

    def create_empty_checkout(
        self, metadata: UcpMetadata
    ) -> tuple[str, AppointmentCheckoutResponse]:
        """Create an empty checkout with all extension fields initialized.

        Domain-specific fields (appointment, lending, etc.) are initialized
        via the domain registry's ``initialize_checkout`` hook so that new
        domains don't require changes to this method.

        Args:
            metadata: UCP metadata object.

        Returns:
            Tuple of (checkout_id, checkout).
        """
        checkout_type = get_checkout_type(metadata)
        checkout_id = str(uuid4())
        checkout = checkout_type(
            id=checkout_id,
            ucp=metadata,
            line_items=[],
            currency=DEFAULT_CURRENCY,
            totals=[],
            status="incomplete",
            links=[],
            payment=PaymentResponse(handlers=self._ucp_metadata["payment"]["handlers"]),
        )

        # Let each registered domain initialize its fields
        from .agent import domain_registry

        active_caps = {c.name for c in metadata.capabilities}
        domain_registry.initialize_checkout(checkout, self._ucp_metadata, active_caps)

        self._checkouts[checkout_id] = checkout
        return checkout_id, checkout

    # ---------- Service Catalog Operations ----------

    def search_services(self, query: str) -> list[ServiceVariation]:
        """Search the service catalog for services that match the query.

        Args:
            query: Search query for services.

        Returns:
            List of ServiceVariation objects matching the query.
        """
        if not self.square:
            return []

        variations = self.square.list_service_variations(query)

        for v in variations:
            self._service_cache[v.id] = v

        return variations

    def get_service_variation(self, service_variation_id: str) -> ServiceVariation:
        """Get a service variation by ID.

        Args:
            service_variation_id: The service variation ID.

        Returns:
            The ServiceVariation object.
        """
        if service_variation_id in self._service_cache:
            return self._service_cache[service_variation_id]

        if not self.square:
            raise ValueError("Square client not configured")

        variation = self.square.get_service_variation(service_variation_id)
        self._service_cache[service_variation_id] = variation
        return variation

    # ---------- Location and Staff Operations ----------

    def list_locations(self, query: str | None = None) -> list[Location]:
        """List available locations for booking.

        Args:
            query: Optional fuzzy search query.

        Returns:
            List of Location objects.
        """
        if not self.square:
            return []
        return self.square.list_locations(query)

    def list_staff(self, query: str | None = None) -> list[StaffResponse]:
        """List available staff members.

        Args:
            query: Optional fuzzy search query.

        Returns:
            List of StaffResponse objects.
        """
        if not self.square:
            return []
        return self.square.list_staff(query)

    # ---------- Availability Operations ----------

    def search_availability(
        self,
        start_date: date,
        end_date: date,
        location_id: str,
        staff_id: str | None = None,
        service_variation_id: str | None = None,
    ) -> list[AvailabilitySlot]:
        """Search for available appointment slots.

        Args:
            start_date: Start date for search range.
            end_date: End date for search range.
            location_id: Optional location filter.
            staff_id: Optional staff filter.
            service_variation_id: Optional service filter.

        Returns:
            List of AvailabilitySlot objects.
        """
        if not self.square:
            return []
        return self.square.search_availability(
            start_date=start_date,
            end_date=end_date,
            location_id=location_id,
            staff_id=staff_id,
            service_variation_id=service_variation_id,
        )

    # ---------- Checkout Operations ----------

    def _get_line_item(self, service: ServiceVariation, quantity: int) -> LineItem:
        """Create a line item for a service variation.

        Args:
            service: ServiceVariation object.
            quantity: Quantity (usually 1 for services).

        Returns:
            LineItem object.
        """
        unit_price = int((service.price or 0) * 100)

        return LineItem(
            id=uuid4().hex,
            item=Item(
                id=service.id,
                price=unit_price,
                title=service.name,
                image_url=None,
            ),
            quantity=quantity,
            totals=[],
        )

    def add_to_checkout(
        self,
        metadata: UcpMetadata,
        service_variation_id: str,
        quantity: int = 1,
        checkout_id: str | None = None,
        location_id: str | None = None,
        staff_id: str | None = None,
        start_time: datetime | None = None,
        notes: str | None = None,
    ) -> AppointmentCheckoutResponse:
        """Add a service to checkout with optional appointment details.

        Args:
            metadata: UCP metadata object.
            service_variation_id: Service variation ID to add.
            quantity: Quantity (usually 1 for services).
            checkout_id: Existing checkout ID, or None to create new.
            location_id: Optional location for appointment.
            staff_id: Optional staff member for appointment.
            start_time: Optional start time for appointment.
            notes: Optional customer notes.

        Returns:
            AppointmentCheckoutResponse object.
        """
        service = self.get_service_variation(service_variation_id)

        if not checkout_id:
            checkout_id, checkout = self.create_empty_checkout(metadata)
        else:
            checkout = self._checkouts.get(checkout_id)
            if not checkout:
                raise ValueError(f"Checkout with ID {checkout_id} not found")

        found = False
        new_line_item_id = None
        for line_item in checkout.line_items:
            if line_item.item.id == service_variation_id:
                line_item.quantity += quantity
                new_line_item_id = line_item.id
                found = True
                break

        if not found:
            line_item = self._get_line_item(service, quantity)
            checkout.line_items.append(line_item)
            new_line_item_id = line_item.id

        # Delegate appointment slot creation to AppointmentManager
        if location_id and start_time and new_line_item_id:
            self.appointments.add_or_update_slot(
                checkout=checkout,
                line_item_id=new_line_item_id,
                location_id=location_id,
                staff_id=staff_id,
                start_time=start_time,
                notes=notes,
                service=service,
            )

        self._recalculate_checkout(checkout)
        self._checkouts[checkout_id] = checkout
        return checkout

    def get_checkout(self, checkout_id: str) -> AppointmentCheckoutResponse | None:
        """Retrieve a checkout by ID.

        Args:
            checkout_id: Checkout ID.

        Returns:
            AppointmentCheckoutResponse or None if not found.
        """
        return self._checkouts.get(checkout_id)

    def remove_from_checkout(
        self, checkout_id: str, line_item_id: str
    ) -> AppointmentCheckoutResponse:
        """Remove a line item and its appointment slot from checkout.

        Args:
            checkout_id: Checkout ID.
            line_item_id: Line item ID to remove.

        Returns:
            Updated AppointmentCheckoutResponse.
        """
        checkout = self.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout with ID {checkout_id} not found")

        checkout.line_items = [
            li for li in checkout.line_items if li.id != line_item_id
        ]

        # Delegate to AppointmentManager
        self.appointments.remove_slots_for_line_item(checkout, line_item_id)

        self._recalculate_checkout(checkout)
        self._checkouts[checkout_id] = checkout
        return checkout

    def update_checkout(
        self,
        checkout_id: str,
        line_item_id: str,
        quantity: int | None = None,
        location_id: str | None = None,
        staff_id: str | None = None,
        start_time: datetime | None = None,
        notes: str | None = None,
    ) -> AppointmentCheckoutResponse:
        """Update a line item's quantity and/or appointment details.

        Args:
            checkout_id: Checkout ID.
            line_item_id: Line item ID to update.
            quantity: New quantity (optional).
            location_id: New location ID (optional).
            staff_id: New staff ID (optional).
            start_time: New start time (optional).
            notes: New notes (optional).

        Returns:
            Updated AppointmentCheckoutResponse.
        """
        checkout = self.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout with ID {checkout_id} not found")

        line_item = None
        for li in checkout.line_items:
            if li.id == line_item_id:
                if quantity is not None:
                    li.quantity = quantity
                line_item = li
                break

        if not line_item:
            raise ValueError(f"Line item {line_item_id} not found")

        # Delegate appointment update to AppointmentManager
        if location_id and start_time:
            service = self.get_service_variation(line_item.item.id)
            self.appointments.add_or_update_slot(
                checkout=checkout,
                line_item_id=line_item_id,
                location_id=location_id,
                staff_id=staff_id,
                start_time=start_time,
                notes=notes,
                service=service,
            )

        self._recalculate_checkout(checkout)
        self._checkouts[checkout_id] = checkout
        return checkout

    def set_appointment(
        self, checkout_id: str, appointment: AppointmentRequest
    ) -> AppointmentCheckoutResponse:
        """Apply appointment slots from AppointmentRequest to checkout.

        Args:
            checkout_id: Checkout ID.
            appointment: AppointmentRequest with slots to apply.

        Returns:
            Updated AppointmentCheckoutResponse.
        """
        checkout = self.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout with ID {checkout_id} not found")

        # Delegate to AppointmentManager
        self.appointments.apply_appointment_request(checkout, appointment)

        self._recalculate_checkout(checkout)
        self._checkouts[checkout_id] = checkout
        return checkout

    def _recalculate_checkout(self, checkout: AppointmentCheckoutResponse) -> None:
        """Recalculate the checkout totals."""
        checkout.status = "incomplete"

        items_base_amount = 0
        items_discount = 0

        for line_item in checkout.line_items:
            item = line_item.item
            unit_price = item.price
            base_amount = unit_price * line_item.quantity
            discount = 0
            line_item.totals = [
                Total(
                    type="items_discount",
                    display_text="Items Discount",
                    amount=discount,
                ),
                Total(
                    type="subtotal",
                    display_text="Subtotal",
                    amount=base_amount - discount,
                ),
                Total(
                    type="total",
                    display_text="Total",
                    amount=base_amount - discount,
                ),
            ]

            items_base_amount += base_amount
            items_discount += discount

        subtotal = items_base_amount - items_discount

        totals = [
            Total(
                type="items_discount",
                display_text="Items Discount",
                amount=items_discount,
            ),
            Total(
                type="subtotal",
                display_text="Subtotal",
                amount=items_base_amount - items_discount,
            ),
            Total(type="discount", display_text="Discount", amount=0),
        ]

        tax = round(subtotal * 0.1)
        totals.append(Total(type="tax", display_text="Tax", amount=tax))

        final_total = subtotal + tax
        totals.append(Total(type="total", display_text="Total", amount=final_total))
        checkout.totals = totals
        checkout.continue_url = AnyUrl(f"https://example.com/checkout?id={checkout.id}")

    def start_payment(self, checkout_id: str) -> AppointmentCheckoutResponse | str:
        """Start the payment process for the checkout.

        Args:
            checkout_id: Checkout ID.

        Returns:
            AppointmentCheckoutResponse or error message string.
        """
        checkout = self.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout with ID {checkout_id} not found")

        if checkout.status == "ready_for_complete":
            return checkout

        messages = []
        if checkout.buyer is None:
            messages.append("Provide a buyer email address")

        # Delegate appointment validation to AppointmentManager
        messages.extend(self.appointments.validate_appointments(checkout))

        if messages:
            return "\n".join(messages)

        self._recalculate_checkout(checkout)
        checkout.status = "ready_for_complete"
        self._checkouts[checkout_id] = checkout
        return checkout

    def place_order(
        self,
        checkout_id: str,
        customer_email: str | None = None,
        customer_first_name: str | None = None,
        customer_last_name: str | None = None,
        customer_phone: str | None = None,
    ) -> AppointmentCheckoutResponse:
        """Complete checkout and create Square bookings.

        Args:
            checkout_id: Checkout ID.
            customer_email: Customer email for bookings.
            customer_first_name: Customer first name.
            customer_last_name: Customer last name.
            customer_phone: Customer phone.

        Returns:
            Completed AppointmentCheckoutResponse with order confirmation.
        """
        checkout = self.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout with ID {checkout_id} not found")

        # Create Square bookings for each appointment slot
        booking_ids = []
        if self.square and checkout.appointment and checkout.appointment.slots:
            for slot in checkout.appointment.slots:
                for li_id in slot.line_item_ids:
                    for li in checkout.line_items:
                        if li.id == li_id:
                            service_variation_id = li.item.id

                            selected_option = None
                            for opt in slot.options or []:
                                if opt.id == slot.selected_option_id:
                                    selected_option = opt
                                    break

                            if selected_option:
                                try:
                                    booking = self.square.create_booking(
                                        location_id=slot.location.id,
                                        start_time=selected_option.start_time,
                                        service_variation_id=service_variation_id,
                                        customer_first_name=customer_first_name,
                                        customer_last_name=customer_last_name,
                                        customer_email=customer_email,
                                        customer_phone=customer_phone,
                                        customer_notes=slot.notes,
                                        staff_id=selected_option.staff_id,
                                    )
                                    booking_ids.append(booking.id)
                                except Exception as e:
                                    logger.error(f"Failed to create booking: {e}")
                            break

        order_id = f"ORD-{checkout_id}"

        checkout.status = "completed"
        checkout.order = OrderConfirmation(
            id=order_id,
            permalink_url=f"https://example.com/order?id={order_id}",
        )

        self._orders[order_id] = checkout
        del self._checkouts[checkout_id]
        return checkout

    # ---------- Booking Operations ----------

    def get_bookings(self, query: str | None = None) -> list[Booking]:
        """Get existing bookings.

        Args:
            query: Optional fuzzy search query.

        Returns:
            List of Booking objects.
        """
        if not self.square:
            return []
        return self.square.get_bookings(query)

    def cancel_booking(self, booking_id: str) -> str:
        """Cancel an existing booking.

        Args:
            booking_id: Booking ID to cancel.

        Returns:
            Confirmation message.
        """
        if not self.square:
            raise ValueError("Square client not configured")
        return self.square.cancel_booking(booking_id)


# Backwards compatibility alias
RetailStore = ServiceStore
