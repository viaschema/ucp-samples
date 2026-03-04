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

"""AppointmentManager — appointment slot logic extracted from ServiceStore.

This class owns all appointment-slot CRUD operations on a checkout.
ServiceStore delegates to it, keeping the checkout core free of
appointment-specific knowledge.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from ucp_sdk.models.schemas.shopping.types.retail_location_resp import (
    RetailLocationResponse,
)

from .models.appointment_types import (
    AppointmentCheckoutResponse,
    AppointmentOptionResponse,
    AppointmentRequest,
    AppointmentResponse,
    AppointmentSlotResponse,
    ServiceVariation,
)

logger = logging.getLogger(__name__)


class AppointmentManager:
    """Manages appointment slots on checkout objects.

    Needs access to a Square client (optional) for location lookups
    and a service-variation resolver for duration calculation.
    """

    def __init__(self, square_client=None, service_resolver=None):
        """Initialize the appointment manager.

        Args:
            square_client: Optional SquareServiceClient for location lookups.
            service_resolver: Callable(service_variation_id) -> ServiceVariation.
        """
        self.square = square_client
        self._resolve_service = service_resolver

    def add_or_update_slot(
        self,
        checkout: AppointmentCheckoutResponse,
        line_item_id: str,
        location_id: str,
        staff_id: str | None,
        start_time,
        notes: str | None,
        service: ServiceVariation,
    ) -> None:
        """Add or update an appointment slot for a line item."""
        if not checkout.appointment:
            checkout.appointment = AppointmentResponse(slots=[])
        if not checkout.appointment.slots:
            checkout.appointment.slots = []

        existing_slot = None
        for slot in checkout.appointment.slots:
            if line_item_id in slot.line_item_ids:
                existing_slot = slot
                break

        location_resp = self._resolve_location(location_id)
        duration_minutes = service.duration_seconds // 60
        end_time = start_time

        option = AppointmentOptionResponse(
            id=uuid4().hex,
            start_time=start_time,
            end_time=end_time,
            staff_id=staff_id,
            duration_minutes=duration_minutes,
        )

        if existing_slot:
            existing_slot.location = location_resp
            existing_slot.options = [option]
            existing_slot.selected_option_id = option.id
            existing_slot.notes = notes
        else:
            slot = AppointmentSlotResponse(
                id=uuid4().hex,
                line_item_ids=[line_item_id],
                location=location_resp,
                options=[option],
                selected_option_id=option.id,
                notes=notes,
            )
            checkout.appointment.slots.append(slot)

    def remove_slots_for_line_item(
        self,
        checkout: AppointmentCheckoutResponse,
        line_item_id: str,
    ) -> None:
        """Remove appointment slots associated with a line item."""
        if checkout.appointment and checkout.appointment.slots:
            checkout.appointment.slots = [
                slot
                for slot in checkout.appointment.slots
                if line_item_id not in slot.line_item_ids
            ]

    def apply_appointment_request(
        self,
        checkout: AppointmentCheckoutResponse,
        appointment: AppointmentRequest,
    ) -> None:
        """Apply appointment slots from an AppointmentRequest to checkout."""
        if not checkout.appointment:
            checkout.appointment = AppointmentResponse(slots=[])
        if not checkout.appointment.slots:
            checkout.appointment.slots = []

        for slot_req in appointment.slots or []:
            location_resp = self._resolve_location(slot_req.location_id)

            duration_minutes = 60
            if slot_req.line_item_ids and self._resolve_service:
                for li in checkout.line_items:
                    if li.id in slot_req.line_item_ids:
                        try:
                            service = self._resolve_service(li.item.id)
                            duration_minutes = service.duration_seconds // 60
                        except Exception:
                            pass
                        break

            option = AppointmentOptionResponse(
                id=uuid4().hex,
                start_time=slot_req.start_time,
                staff_id=slot_req.staff_id,
                duration_minutes=duration_minutes,
            )

            existing_slot = None
            if slot_req.id:
                for slot in checkout.appointment.slots:
                    if slot.id == slot_req.id:
                        existing_slot = slot
                        break

            if existing_slot:
                existing_slot.line_item_ids = slot_req.line_item_ids
                existing_slot.location = location_resp
                existing_slot.options = [option]
                existing_slot.selected_option_id = option.id
                existing_slot.notes = slot_req.notes
            else:
                slot = AppointmentSlotResponse(
                    id=slot_req.id or uuid4().hex,
                    line_item_ids=slot_req.line_item_ids,
                    location=location_resp,
                    options=[option],
                    selected_option_id=option.id,
                    notes=slot_req.notes,
                )
                checkout.appointment.slots.append(slot)

    def validate_appointments(
        self, checkout: AppointmentCheckoutResponse
    ) -> list[str]:
        """Return validation messages for appointment completeness."""
        messages = []
        if checkout.appointment and checkout.appointment.slots:
            scheduled_items = set()
            for slot in checkout.appointment.slots:
                scheduled_items.update(slot.line_item_ids)

            unscheduled = [
                li for li in checkout.line_items if li.id not in scheduled_items
            ]
            if unscheduled:
                messages.append("Some services don't have appointments scheduled")
        elif checkout.line_items:
            messages.append("No appointments scheduled for services")
        return messages

    def _resolve_location(self, location_id: str) -> RetailLocationResponse:
        """Look up location info from Square or return a stub."""
        if self.square:
            try:
                loc = self.square.get_location(location_id)
                return RetailLocationResponse(id=loc.id, name=loc.name)
            except Exception:
                pass
        return RetailLocationResponse(id=location_id, name="")
