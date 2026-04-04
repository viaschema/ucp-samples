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

"""Lending types for UCP.

This module provides types for the com.viaschema.lending capability,
which extends checkout to support loan applications with PII collection,
multi-lender comparison, and offer generation. Similar to the payment
pattern, PII is handled via tokens from a trusted third-party provider.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from ucp_sdk.models.schemas.shopping.checkout_resp import (
    CheckoutResponse,
)


class LoanType(str, enum.Enum):
    """Supported loan types."""

    PERSONAL = "personal"
    CAR = "car"


class Lender(BaseModel):
    """A lending institution that offers loans."""

    lender_name: str = Field(description="Display name of the lender")
    loan_types_offered: list[str] = Field(description="Loan types this lender supports")
    description: str = Field(description="Short description of the lender")
    platform_id: str = Field(description="Unique platform identifier")


class LoanOffer(BaseModel):
    """A loan offer from a lender."""

    lender_name: str = Field(description="Name of the lender making the offer")
    rate: float = Field(description="Annual interest rate (APR)")
    amount: float = Field(description="Loan amount")
    term_months: int = Field(description="Loan term in months")
    monthly_payment: float = Field(description="Estimated monthly payment")
    continue_url: str = Field(description="URL to continue the application")


class PIICredential(BaseModel):
    """Credential containing an opaque PII token."""

    type: str = Field(description="Credential type, e.g. 'token'")
    token: str = Field(description="Opaque PII token from the provider")


class PIIConsent(BaseModel):
    """Formal consent record authorizing PII sharing with lender platforms.

    The frontend builds this when the user confirms which fields to share
    and with which lenders. It is sent to the PII vault, which validates it,
    records it, and mints platform-scoped tokens in return.
    """

    pii_method_id: str = Field(description="PII profile the user selected")
    handler_id: str = Field(description="PII handler being used")
    fields_consented: list[str] = Field(
        description="Exact PII fields the user authorized for sharing"
    )
    loan_type: str = Field(description="Loan purpose: personal or car")
    platform_ids: list[str] = Field(
        description="Lender platform IDs authorized to receive PII"
    )
    consented_at: str = Field(
        description="ISO 8601 timestamp of when consent was given"
    )


class PIIInstrument(BaseModel):
    """A PII instrument containing a token from a trusted PII provider.

    Mirrors PaymentInstrument: the agent never sees raw PII,
    only this token-based reference.
    """

    id: str = Field(description="PII profile identifier")
    handler_id: str = Field(description="PII handler identifier")
    handler_name: str = Field(description="PII handler name")
    credential: PIICredential = Field(description="Token credential")
    fields_stored: list[str] = Field(
        default_factory=list, description="PII fields available via this token"
    )
    loan_type: str = Field(
        default="all", description="Loan type this PII profile covers"
    )
    platform_id: str | None = Field(
        default=None, description="Platform this token was minted for"
    )


class PIIHandler(BaseModel):
    """A PII handler from the merchant's UCP profile.

    Represents a trusted third-party PII provider that can collect
    and store user PII on behalf of the merchant (e.g. VGS, OneTrust).
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Handler identifier")
    name: str = Field(description="Handler name")
    version: str | None = Field(default=None, description="Handler version")
    spec: str | None = Field(default=None, description="Handler spec URL")
    config_schema: str | None = Field(
        default=None, description="Handler config schema URL"
    )
    config: dict[str, Any] | None = Field(
        default=None, description="Handler configuration"
    )


class LendingHandler(BaseModel):
    """A lending handler from the merchant's UCP profile.

    Represents a lending marketplace that provides lenders and manages
    loan applications. References PII handler(s) it works with.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Handler identifier")
    name: str = Field(description="Handler name")
    version: str | None = Field(default=None, description="Handler version")
    supported_loan_types: list[str] | None = Field(
        default=None, description="Loan types this handler supports"
    )


class LendingResponse(BaseModel):
    """Container for lending state on a checkout.

    Tracks the lending workflow from PII collection through
    offer comparison.
    """

    model_config = ConfigDict(extra="allow")

    loan_type: str | None = Field(
        default=None, description="Selected loan type (personal or car)"
    )
    handlers: list[PIIHandler] | None = Field(
        default=None, description="Available PII handlers from merchant profile"
    )
    lending_handler: LendingHandler | None = Field(
        default=None, description="The lending handler managing this flow"
    )
    lenders: list[Lender] | None = Field(
        default=None, description="Available lenders for the loan type"
    )
    offers: list[LoanOffer] | None = Field(
        default=None, description="Loan offers sorted by rate (ascending)"
    )
    status: str | None = Field(
        default=None,
        description=(
            "Lending workflow status: consent_needed, pii_missing, offers_received"
        ),
    )
    required_pii_fields: list[str] | None = Field(
        default=None, description="PII fields required for the loan type"
    )
    required_non_pii_fields: list[str] | None = Field(
        default=None, description="Non-PII fields required for the loan type"
    )
    missing_pii_fields: list[str] | None = Field(
        default=None,
        description="PII fields that still need to be collected",
    )


# ---------------------------------------------------------------------------
# Handler resolution helpers — single source of truth for parsing ucp_metadata
# ---------------------------------------------------------------------------


def resolve_pii_handlers(ucp_metadata: dict) -> list[PIIHandler]:
    """Resolve PII handlers from UCP metadata."""
    return [
        PIIHandler(**h)
        for h in ucp_metadata.get("pii", {}).get("handlers", [])
    ]


def resolve_lending_handler(ucp_metadata: dict) -> LendingHandler | None:
    """Resolve the active lending handler from UCP metadata.

    Currently supports exactly one lending handler. Raises ValueError
    if multiple are configured (not yet supported).
    """
    handlers_raw = ucp_metadata.get("lending", {}).get("handlers", [])
    if not handlers_raw:
        return None
    if len(handlers_raw) > 1:
        raise ValueError(
            f"Multiple lending handlers not yet supported "
            f"(found {len(handlers_raw)}). Use exactly one."
        )
    return LendingHandler(**handlers_raw[0])


# Checkout extension types


class LendingCheckoutResponse(CheckoutResponse):
    """Checkout extended with lending details."""

    model_config = ConfigDict(extra="allow")

    lending: LendingResponse | None = None
    """Lending application details."""


# Aliases for convenience
LendingCheckout = LendingCheckoutResponse
