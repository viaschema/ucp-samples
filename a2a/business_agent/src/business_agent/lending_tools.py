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

"""Lending tool functions for the service booking agent.

Contains all lending-related ADK tools: search_lenders, get_pii_requirements,
start_lending, and submit_loan_application.
"""

from __future__ import annotations

import logging
from typing import Any

from a2a.types import TaskState
from google.adk.tools.tool_context import ToolContext

from .constants import (
    ADK_PII_STATE,
    ADK_UCP_METADATA_STATE,
    ADK_USER_CHECKOUT_ID,
    UCP_CHECKOUT_KEY,
    UCP_LOAN_APPLICATION_KEY,
    UCP_PII_DATA_KEY,
)
from .dependencies import store
from .loan_provider import LendingCheckoutManager, LoanProviderRegistry
from .models.lending_types import PIIInstrument
from .pii_provider import MockPIIProvider

pii_provider = MockPIIProvider()
loan_registry = LoanProviderRegistry(pii_provider)
lending_manager = LendingCheckoutManager(
    store, pii_provider, loan_registry, store.ucp_metadata
)


def _create_error_response(message: str) -> dict:
    return {"message": message, "status": "error"}


def search_lenders(
    tool_context: ToolContext,
    loan_type: str | None = None,
    query: str | None = None,
) -> dict:
    """Search for available lenders, optionally filtered by loan type or name.

    Args:
        tool_context: The tool context for the current request.
        loan_type: Optional filter by loan type ('personal' or 'car').
        query: Optional search query to filter lenders by name or description.

    Returns:
        dict: Returns list of available lenders.
    """
    try:
        lenders = loan_registry.get_lenders(loan_type=loan_type, query=query)
        return {
            "a2a.ucp.lending.lenders": [
                lender.model_dump(mode="json") for lender in lenders
            ]
        }
    except Exception:
        logging.exception("There was an error searching lenders.")
        return _create_error_response(
            "Sorry, there was an error searching lenders, please try again later."
        )


def get_pii_requirements(tool_context: ToolContext, loan_type: str) -> dict:
    """Get the PII and non-PII fields required for a loan application.

    Args:
        tool_context: The tool context for the current request.
        loan_type: The loan type ('personal' or 'car').

    Returns:
        dict: Returns required PII fields, non-PII fields, and any missing fields.
    """
    try:
        user_email = tool_context.state.get("customer_email")
        required_pii = loan_registry.get_required_pii_fields(loan_type)
        required_non_pii = loan_registry.get_required_non_pii_fields(loan_type)
        missing_pii = (
            pii_provider.get_missing_fields(user_email, required_pii)
            if user_email
            else required_pii
        )
        return {
            "required_pii_fields": required_pii,
            "required_non_pii_fields": required_non_pii,
            "missing_pii_fields": missing_pii,
            "status": "success",
        }
    except Exception:
        logging.exception("There was an error getting PII requirements.")
        return _create_error_response(
            "Sorry, there was an error getting loan requirements."
        )


def start_lending(tool_context: ToolContext, loan_type: str) -> dict:
    """Start the lending flow by setting up PII requirements on the checkout.

    This initializes the lending extension on the checkout with PII handlers,
    required fields, and available lenders. The frontend uses this information
    to drive the PII collection or consent flow.

    Args:
        tool_context: The tool context for the current request.
        loan_type: The loan type ('personal' or 'car').

    Returns:
        dict: Returns the checkout with lending info.
    """
    checkout_id = tool_context.state.get(ADK_USER_CHECKOUT_ID)
    ucp_metadata = tool_context.state.get(ADK_UCP_METADATA_STATE)

    if not ucp_metadata:
        return _create_error_response("There was an error creating UCP metadata")

    try:
        # Create a checkout if one doesn't exist
        if not checkout_id:
            checkout_id, _ = store.create_empty_checkout(ucp_metadata)
            tool_context.state[ADK_USER_CHECKOUT_ID] = checkout_id

        user_email = tool_context.state.get("customer_email")
        checkout = lending_manager.start_lending(checkout_id, loan_type, user_email)

        return {
            UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
            "status": "success",
        }
    except ValueError:
        logging.exception("There was an error starting the lending flow.")
        return _create_error_response(
            "There was an error starting the lending flow, please retry later."
        )


async def submit_loan_application(tool_context: ToolContext) -> dict:
    """Submit a loan application using stored PII and get offers from all lenders.

    Reads the PII token from state (set via frontend PII consent flow),
    validates it, then queries ALL eligible lenders for the loan type
    and returns aggregated offers sorted by rate.

    Args:
        tool_context: The tool context for the current request.

    Returns:
        dict: Returns loan offers sorted by rate from all eligible lenders.
    """
    checkout_id = tool_context.state.get(ADK_USER_CHECKOUT_ID)

    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    checkout = store.get_checkout(checkout_id)
    if checkout is None:
        return _create_error_response("Checkout not found for the current session.")

    if not checkout.lending or not checkout.lending.loan_type:
        return _create_error_response(
            "Lending has not been started. Use start_lending first."
        )

    pii_state: dict[str, Any] | None = tool_context.state.get(ADK_PII_STATE)

    if pii_state is None:
        return {
            "message": (
                "PII data is missing. Please authorize PII sharing "
                "to complete the loan application."
            ),
            "status": "requires_more_info",
        }

    try:
        # Extract PII instruments (may be a single instrument or a list)
        pii_data = pii_state.get(UCP_PII_DATA_KEY)
        if isinstance(pii_data, PIIInstrument):
            pii_instruments = [pii_data]
        elif isinstance(pii_data, list):
            pii_instruments = pii_data
        else:
            pii_instruments = []

        if not pii_instruments:
            return _create_error_response(
                "PII token is missing. Please authorize PII sharing."
            )

        # Validate each instrument
        for instrument in pii_instruments:
            task = pii_provider.process_pii(instrument)
            if task.status is not None and task.status.state != TaskState.completed:
                return _create_error_response(
                    "PII token validation failed. Please re-authorize."
                )

        # Build platform_id -> token map
        pii_tokens: dict[str, str] = {}
        for inst in pii_instruments:
            if inst.platform_id:
                pii_tokens[inst.platform_id] = inst.credential.token
            else:
                # Legacy single-token fallback: apply to all lenders
                if checkout.lending and checkout.lending.lenders:
                    for lender in checkout.lending.lenders:
                        pii_tokens[lender.platform_id] = inst.credential.token

        # Get non-PII data from the state
        non_pii_info = pii_state.get(UCP_LOAN_APPLICATION_KEY, {})

        # Query ALL eligible lenders and get aggregated offers
        loan_type = checkout.lending.loan_type
        offers = loan_registry.apply_for_all_lenders(
            pii_tokens, loan_type, non_pii_info
        )

        # Update checkout with offers
        checkout.lending.offers = offers
        checkout.lending.status = "offers_received"
        store.save_checkout(checkout_id, checkout)

        return {
            "a2a.ucp.lending.loan_offers": [
                offer.model_dump(mode="json") for offer in offers
            ],
            UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
            "status": "success",
        }
    except Exception:
        logging.exception("There was an error submitting the loan application.")
        return _create_error_response(
            "Sorry, there was an error processing your loan application."
        )
