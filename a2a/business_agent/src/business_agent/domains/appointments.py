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

"""Appointment domain module — location, staff, availability, and booking tools."""

from __future__ import annotations

import logging
from datetime import date, datetime

from google.adk.tools.tool_context import ToolContext

from ..constants import (
    ADK_USER_CHECKOUT_ID,
    UCP_APPOINTMENT_EXTENSION,
    UCP_CHECKOUT_KEY,
)
from ..dependencies import store
from ..models.appointment_types import (
    AppointmentCheckout,
    AppointmentRequest,
    AppointmentResponse,
    AppointmentSlotRequest,
)
from .base import DomainModule


def _create_error_response(message: str) -> dict:
    return {"message": message, "status": "error"}


# ---------- Location and Staff Tools ----------


def list_locations(tool_context: ToolContext, query: str | None = None) -> dict:
    """List available locations where services can be booked.

    Args:
        tool_context: The tool context for the current request.
        query: Optional search query to filter locations by name or address.

    Returns:
        dict: Returns list of locations.
    """
    try:
        locations = store.list_locations(query)
        return {"a2a.locations": [loc.model_dump(mode="json") for loc in locations]}
    except Exception:
        logging.exception("There was an error listing locations.")
        return _create_error_response(
            "Sorry, there was an error listing locations, please try again later."
        )


def list_staff(tool_context: ToolContext, query: str | None = None) -> dict:
    """List available staff members who can provide services.

    Args:
        tool_context: The tool context for the current request.
        query: Optional search query to filter staff by name.

    Returns:
        dict: Returns list of staff members.
    """
    try:
        staff = store.list_staff(query)
        return {"a2a.staff": [s.model_dump(mode="json") for s in staff]}
    except Exception:
        logging.exception("There was an error listing staff.")
        return _create_error_response(
            "Sorry, there was an error listing staff, please try again later."
        )


# ---------- Availability Tool ----------


def search_availability(
    tool_context: ToolContext,
    start_date: str,
    end_date: str,
    location_id: str,
    staff_id: str | None = None,
    service_variation_id: str | None = None,
) -> dict:
    """Search for available appointment slots within a date range.

    A location_id is required. Use list_locations first to get one.

    Args:
        tool_context: The tool context for the current request.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        location_id: Location ID to search availability at (required).
        staff_id: Optional staff ID to filter by.
        service_variation_id: Optional service variation ID to filter by.

    Returns:
        dict: Returns list of available time slots.
    """
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        # Square API requires dates in the future — clamp if the LLM
        # resolved a relative phrase (e.g. "next Monday") to a past date.
        today = date.today()
        if start < today:
            start = today
        if end < today:
            end = today

        slots = store.search_availability(
            start_date=start,
            end_date=end,
            location_id=location_id,
            staff_id=staff_id,
            service_variation_id=service_variation_id,
        )
        return {"a2a.availability_slots": [s.model_dump(mode="json") for s in slots]}
    except Exception as exc:
        logging.exception("There was an error searching availability.")
        detail = str(exc)
        if "future" in detail.lower():
            return _create_error_response(
                "The requested dates must be in the future. "
                f"Today is {date.today().isoformat()}. "
                "Please try again with a future date range."
            )
        return _create_error_response(
            "Sorry, there was an error searching availability, please try again later."
        )


# ---------- Appointment Tools ----------


def set_appointment(
    tool_context: ToolContext,
    slots: list[dict],
) -> dict:
    """Set appointment details for multiple line items at once.

    Args:
        tool_context: The tool context for the current request.
        slots: List of appointment slot configurations. Each slot should have:
            - line_item_ids: List of line item IDs this slot applies to
            - location_id: Location ID for the appointment
            - start_time: Start time in ISO 8601 format
            - staff_id: Optional staff member ID
            - notes: Optional customer notes

    Returns:
        dict: Returns the checkout response.
    """
    checkout_id = tool_context.state.get(ADK_USER_CHECKOUT_ID)

    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    try:
        parsed_slots = []
        for slot_data in slots:
            start_time_str = slot_data.get("start_time", "")
            parsed_start_time = datetime.fromisoformat(
                start_time_str.replace("Z", "+00:00")
            )
            parsed_slots.append(
                AppointmentSlotRequest(
                    id=slot_data.get("id"),
                    line_item_ids=slot_data.get("line_item_ids", []),
                    location_id=slot_data.get("location_id", ""),
                    staff_id=slot_data.get("staff_id"),
                    start_time=parsed_start_time,
                    notes=slot_data.get("notes"),
                )
            )

        appointment = AppointmentRequest(slots=parsed_slots)
        checkout = store.set_appointment(checkout_id, appointment)

        return {
            UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
            "status": "success",
        }
    except ValueError:
        logging.exception(
            "There was an error setting appointment details, please retry later."
        )
        return _create_error_response(
            "There was an error setting appointment details, please retry later."
        )


# ---------- Booking Management Tools ----------


def get_bookings(tool_context: ToolContext, query: str | None = None) -> dict:
    """Get existing bookings.

    Args:
        tool_context: The tool context for the current request.
        query: Optional search query to filter bookings.

    Returns:
        dict: Returns list of bookings.
    """
    try:
        bookings = store.get_bookings(query)
        return {"a2a.bookings": [b.model_dump(mode="json") for b in bookings]}
    except Exception:
        logging.exception("There was an error getting bookings.")
        return _create_error_response(
            "Sorry, there was an error getting bookings, please try again later."
        )


def cancel_booking(tool_context: ToolContext, booking_id: str) -> dict:
    """Cancel an existing booking.

    Args:
        tool_context: The tool context for the current request.
        booking_id: The ID of the booking to cancel.

    Returns:
        dict: Returns confirmation message.
    """
    try:
        result = store.cancel_booking(booking_id)
        return {"message": result, "status": "success"}
    except Exception:
        logging.exception("There was an error cancelling the booking.")
        return _create_error_response(
            "Sorry, there was an error cancelling the booking, please try again later."
        )


class AppointmentDomain(DomainModule):
    """Appointment domain — locations, staff, availability, and bookings."""

    @property
    def capability_uri(self) -> str:
        return UCP_APPOINTMENT_EXTENSION

    @property
    def tools(self) -> list:
        return [
            list_locations,
            list_staff,
            search_availability,
            set_appointment,
            get_bookings,
            cancel_booking,
        ]

    @property
    def agent_instructions(self) -> str:
        today = date.today().isoformat()
        return (
            "Appointment booking workflow:\n"
            f"IMPORTANT: Today's date is {today}. When the user says "
            "relative dates like 'next Monday' or 'this Friday', "
            "resolve them to actual YYYY-MM-DD dates that are in the "
            "future (on or after today). Never use past dates.\n"
            "1. List available locations (list_locations)\n"
            "2. Check staff availability (list_staff)\n"
            "3. Find available appointment times (search_availability)\n"
            "4. Add the service to checkout with appointment details "
            "(add_to_checkout with location_id, staff_id, start_time)\n"
            "5. Or use set_appointment to schedule appointments for "
            "multiple services at once\n"
            "6. Use get_bookings and cancel_booking to manage existing bookings"
        )

    @property
    def checkout_mixin(self) -> type:
        return AppointmentCheckout

    @property
    def response_data_keys(self) -> list[str]:
        return [
            "a2a.locations",
            "a2a.staff",
            "a2a.availability_slots",
            "a2a.bookings",
        ]

    def initialize_checkout_fields(self, checkout, ucp_metadata: dict) -> None:
        if hasattr(checkout, "appointment"):
            checkout.appointment = AppointmentResponse(slots=[])
