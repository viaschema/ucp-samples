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

"""Shopping domain module — core checkout, payment, and catalog tools."""

from __future__ import annotations

import logging
from typing import Any

from a2a.types import TaskState
from a2a.utils import get_message_text
from google.adk.tools.tool_context import ToolContext
from ucp_sdk.models.schemas.shopping.types.buyer import Buyer

from ..constants import (
    ADK_EXTENSIONS_STATE_KEY,
    ADK_PAYMENT_STATE,
    ADK_UCP_METADATA_STATE,
    ADK_USER_CHECKOUT_ID,
    UCP_CHECKOUT_KEY,
    UCP_PAYMENT_DATA_KEY,
    UCP_RISK_SIGNALS_KEY,
)
from ..dependencies import mpp, store
from .base import DomainModule


def _create_error_response(message: str) -> dict:
    return {"message": message, "status": "error"}


# ---------- Catalog Tools ----------


def search_shopping_catalog(tool_context: ToolContext, query: str) -> dict:
    """Search the service catalog for services that match the given query.

    Args:
        tool_context: The tool context for the current request.
        query: Query for performing service search.

    Returns:
        dict: Returns the response from the tool with service results.
    """
    try:
        services = store.search_services(query)
        return {"a2a.service_results": [s.model_dump(mode="json") for s in services]}
    except Exception:
        logging.exception("There was an error searching the service catalog.")
        return _create_error_response(
            "Sorry, there was an error searching the service catalog, "
            "please try again later."
        )


# ---------- Checkout Tools ----------


def add_to_checkout(
    tool_context: ToolContext,
    service_variation_id: str,
    quantity: int = 1,
    location_id: str | None = None,
    staff_id: str | None = None,
    start_time: str | None = None,
    notes: str | None = None,
) -> dict:
    """Add a service to the checkout session with optional appointment details.

    Args:
        tool_context: The tool context for the current request.
        service_variation_id: Service variation ID to add.
        quantity: Quantity (default 1).
        location_id: Optional location ID for the appointment.
        staff_id: Optional staff ID for the appointment.
        start_time: Optional start time in ISO 8601 format (e.g., 2024-01-15T10:00:00Z).
        notes: Optional notes for the appointment.

    Returns:
        dict: Returns the checkout response.
    """
    from datetime import datetime

    checkout_id = tool_context.state.get(ADK_USER_CHECKOUT_ID)
    ucp_metadata = tool_context.state.get(ADK_UCP_METADATA_STATE)

    if not ucp_metadata:
        return _create_error_response("There was an error creating UCP metadata")

    try:
        parsed_start_time = None
        if start_time:
            parsed_start_time = datetime.fromisoformat(
                start_time.replace("Z", "+00:00")
            )

        checkout = store.add_to_checkout(
            metadata=ucp_metadata,
            service_variation_id=service_variation_id,
            quantity=quantity,
            checkout_id=checkout_id,
            location_id=location_id,
            staff_id=staff_id,
            start_time=parsed_start_time,
            notes=notes,
        )

        if not checkout_id:
            tool_context.state[ADK_USER_CHECKOUT_ID] = checkout.id

        return {
            UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
            "status": "success",
        }
    except ValueError:
        logging.exception(
            "There was an error adding item to checkout, please retry later."
        )
        return _create_error_response(
            "There was an error adding item to checkout, please retry later."
        )


def remove_from_checkout(tool_context: ToolContext, line_item_id: str) -> dict:
    """Remove a service and its appointment slot from the checkout session.

    Args:
        tool_context: The tool context for the current request.
        line_item_id: Line item ID to remove.

    Returns:
        dict: Returns the checkout response.
    """
    checkout_id = _get_current_checkout_id(tool_context)

    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    try:
        checkout = store.remove_from_checkout(checkout_id, line_item_id)
        return {
            UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
            "status": "success",
        }
    except ValueError:
        logging.exception(
            "There was an error removing item from checkout, please retry later."
        )
        return _create_error_response(
            "There was an error removing item from checkout, please retry later."
        )


def update_checkout(
    tool_context: ToolContext,
    line_item_id: str,
    quantity: int | None = None,
    location_id: str | None = None,
    staff_id: str | None = None,
    start_time: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update a line item's quantity and/or appointment details.

    Args:
        tool_context: The tool context for the current request.
        line_item_id: Line item ID to update.
        quantity: New quantity (optional).
        location_id: New location ID for the appointment (optional).
        staff_id: New staff ID for the appointment (optional).
        start_time: New start time in ISO 8601 format (optional).
        notes: New notes for the appointment (optional).

    Returns:
        dict: Returns the checkout response.
    """
    from datetime import datetime

    checkout_id = _get_current_checkout_id(tool_context)

    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    try:
        parsed_start_time = None
        if start_time:
            parsed_start_time = datetime.fromisoformat(
                start_time.replace("Z", "+00:00")
            )

        checkout = store.update_checkout(
            checkout_id=checkout_id,
            line_item_id=line_item_id,
            quantity=quantity,
            location_id=location_id,
            staff_id=staff_id,
            start_time=parsed_start_time,
            notes=notes,
        )
        return {
            UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
            "status": "success",
        }
    except ValueError:
        logging.exception(
            "There was an error updating the checkout, please retry later."
        )
        return _create_error_response(
            "There was an error updating the checkout, please retry later."
        )


def get_checkout(tool_context: ToolContext) -> dict:
    """Retrieve the current checkout session.

    Args:
        tool_context: The tool context for the current request.

    Returns:
        dict: Returns the checkout response.
    """
    checkout_id = _get_current_checkout_id(tool_context)

    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    checkout = store.get_checkout(checkout_id)
    if checkout is None:
        return _create_error_response("Checkout not found with the given ID.")

    return {
        UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
        "status": "success",
    }


def update_customer_details(
    tool_context: ToolContext,
    email: str,
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
) -> dict:
    """Update customer details for the checkout.

    Args:
        tool_context: The tool context for the current request.
        email: Customer email address.
        first_name: Customer first name.
        last_name: Customer last name.
        phone: Customer phone number.

    Returns:
        dict: Returns the checkout response.
    """
    checkout_id = _get_current_checkout_id(tool_context)

    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    checkout = store.get_checkout(checkout_id)
    if checkout is None:
        return _create_error_response("Checkout not found with the given ID.")

    checkout.buyer = Buyer(email=email)

    tool_context.state["customer_first_name"] = first_name
    tool_context.state["customer_last_name"] = last_name
    tool_context.state["customer_phone"] = phone
    tool_context.state["customer_email"] = email

    return start_payment(tool_context)


def start_payment(tool_context: ToolContext) -> dict:
    """Ask for required information to proceed with the payment.

    Args:
        tool_context: The tool context for the current request.

    Returns:
        dict: Checkout object or error message.
    """
    checkout_id = _get_current_checkout_id(tool_context)

    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    result = store.start_payment(checkout_id)
    if isinstance(result, str):
        return {"message": result, "status": "requires_more_info"}
    else:
        tool_context.actions.skip_summarization = True
        return {
            UCP_CHECKOUT_KEY: result.model_dump(mode="json"),
            "status": "success",
        }


async def complete_checkout(tool_context: ToolContext) -> dict:
    """Process the payment and create bookings to complete checkout.

    Args:
        tool_context: The tool context for the current request.

    Returns:
        dict: Returns the checkout response with order confirmation.
    """
    checkout_id = _get_current_checkout_id(tool_context)

    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    checkout = store.get_checkout(checkout_id)

    if checkout is None:
        return _create_error_response("Checkout not found for the current session.")

    payment_data: dict[str, Any] = tool_context.state.get(ADK_PAYMENT_STATE)

    if payment_data is None:
        return {
            "message": (
                "Payment Data is missing. Click 'Confirm Purchase' "
                "to complete the purchase."
            ),
            "status": "requires_more_info",
        }

    try:
        task = mpp.process_payment(
            payment_data[UCP_PAYMENT_DATA_KEY],
            payment_data[UCP_RISK_SIGNALS_KEY],
        )

        if task is None:
            return _create_error_response("Failed to receive a valid response from MPP")

        if task.status is not None and task.status.state == TaskState.completed:
            payment_instrument = payment_data.get(UCP_PAYMENT_DATA_KEY)
            checkout.payment.selected_instrument_id = payment_instrument.root.id
            checkout.payment.instruments = [payment_instrument]

            customer_email = tool_context.state.get("customer_email")
            customer_first_name = tool_context.state.get("customer_first_name")
            customer_last_name = tool_context.state.get("customer_last_name")
            customer_phone = tool_context.state.get("customer_phone")

            response = store.place_order(
                checkout_id,
                customer_email=customer_email,
                customer_first_name=customer_first_name,
                customer_last_name=customer_last_name,
                customer_phone=customer_phone,
            )

            tool_context.state[ADK_USER_CHECKOUT_ID] = None

            return {
                UCP_CHECKOUT_KEY: response.model_dump(mode="json"),
                "status": "success",
            }
        else:
            return _create_error_response(
                get_message_text(task.status.message)  # type: ignore
            )
    except Exception:
        logging.exception("There was an error completing the checkout.")
        return _create_error_response(
            "Sorry, there was an error completing the checkout, please try again."
        )


def _get_current_checkout_id(tool_context: ToolContext) -> str | None:
    """Return the current checkout ID from the tool context state."""
    return tool_context.state.get(ADK_USER_CHECKOUT_ID)


class ShoppingDomain(DomainModule):
    """Core shopping/checkout domain — catalog, checkout, and payment."""

    @property
    def capability_uri(self) -> str:
        return "dev.ucp.shopping.checkout"

    @property
    def tools(self) -> list:
        return [
            search_shopping_catalog,
            add_to_checkout,
            remove_from_checkout,
            update_checkout,
            get_checkout,
            update_customer_details,
            start_payment,
            complete_checkout,
        ]

    @property
    def agent_instructions(self) -> str:
        return (
            "Shopping and checkout workflow:\n"
            "1. Search for services the user wants (search_shopping_catalog)\n"
            "2. Add items to checkout (add_to_checkout)\n"
            "3. Collect customer details (update_customer_details)\n"
            "4. Complete the checkout to confirm (complete_checkout)"
        )

    @property
    def response_data_keys(self) -> list[str]:
        return [UCP_CHECKOUT_KEY, "a2a.service_results"]
