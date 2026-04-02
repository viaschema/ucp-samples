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

"""Loan provider and lending checkout management.

Separates loan offer generation (per-lender) from PII storage (PII provider).
Each lender is represented by a MockLoanProvider that resolves PII via a token
and generates mock offers. The LoanProviderRegistry coordinates all providers.
The LendingCheckoutManager owns the lending business logic on checkouts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

from .models.lending_fields import (
    CAR_LOAN_PII_FIELDS,
    NON_PII_FIELDS_BY_LOAN_TYPE,
    PERSONAL_LOAN_PII_FIELDS,
    PII_FIELDS_BY_LOAN_TYPE,
)
from .models.lending_types import (
    Lender,
    LendingResponse,
    LoanOffer,
    LoanType,
    resolve_lending_handler,
    resolve_pii_handlers,
)

if TYPE_CHECKING:
    from .pii_provider import PIIProvider
    from .store import ServiceStore

# Mock lender directory
LENDER_LIST: list[Lender] = [
    Lender(
        lender_name="SoFi",
        loan_types_offered=[LoanType.PERSONAL, LoanType.CAR],
        description="Optimized for high-FICO borrowers with competitive rates",
        platform_id="sofi",
    ),
    Lender(
        lender_name="LendingClub",
        loan_types_offered=[LoanType.PERSONAL],
        description="Peer-to-peer lending platform for personal loans",
        platform_id="lendingclub",
    ),
    Lender(
        lender_name="Capital One Auto",
        loan_types_offered=[LoanType.CAR],
        description="Specialized auto financing with flexible terms",
        platform_id="capitalone_auto",
    ),
    Lender(
        lender_name="Upstart",
        loan_types_offered=[LoanType.PERSONAL, LoanType.CAR],
        description="AI-powered lending with consideration for education and employment",
        platform_id="upstart",
    ),
    Lender(
        lender_name="LightStream",
        loan_types_offered=[LoanType.PERSONAL, LoanType.CAR],
        description="Low rates for borrowers with excellent credit",
        platform_id="lightstream",
    ),
    Lender(
        lender_name="MoneyTree",
        loan_types_offered=[LoanType.PERSONAL],
        description="Loan approval guaranteed for smaller amounts",
        platform_id="moneytree",
    ),
]


class MockLoanProvider:
    """A single lender that generates loan offers via a lender API.

    Delegates PII delivery to the PII provider's forward_pii() method.
    The lending provider never sees raw PII or aliases — it just says
    "send this token's PII to this URL" and gets offers back.
    """

    def __init__(
        self,
        lender: Lender,
        pii_provider: PIIProvider,
        lender_api_base: str = "http://localhost:10999/lender-api",
    ) -> None:
        self.lender = lender
        self._pii_provider = pii_provider
        self._lender_api_base = lender_api_base

    def generate_offers(
        self,
        pii_token: str,
        non_pii_info: dict[str, Any],
        loan_type: str,
    ) -> list[LoanOffer]:
        """Generate loan offers by forwarding PII to the lender API.

        The PII provider handles the delivery — this method never sees
        raw PII or aliases. It just provides the token, the destination
        URL, and the non-PII data to include.

        Args:
            pii_token: Opaque PII token from the provider.
            non_pii_info: Non-PII application data (loan amount, etc.).
            loan_type: The loan type being applied for.

        Returns:
            List of LoanOffer objects from this lender.
        """
        logger.info(
            "generate_offers: lender=%s platform_id=%s",
            self.lender.lender_name,
            self.lender.platform_id,
        )

        url = f"{self._lender_api_base}/{self.lender.platform_id}/apply"
        result = self._pii_provider.forward_pii(
            token=pii_token,
            platform_id=self.lender.platform_id,
            url=url,
            extra_data={
                "loan_type": loan_type,
                "lender_name": self.lender.lender_name,
                **non_pii_info,
            },
        )

        if result is None:
            logger.warning(
                "generate_offers: forward_pii returned None for lender=%s",
                self.lender.lender_name,
            )
            return []

        offers_data = result.get("offers", [])
        return [LoanOffer(**o) for o in offers_data]


class LoanProviderRegistry:
    """Coordinates all loan providers.

    Creates one MockLoanProvider per lender and provides methods
    for lender search and aggregated offer generation.
    """

    def __init__(
        self,
        pii_provider: PIIProvider,
        lender_api_base: str = "http://localhost:10999/lender-api",
    ) -> None:
        self._pii_provider = pii_provider
        self._providers: list[MockLoanProvider] = [
            MockLoanProvider(lender, pii_provider, lender_api_base)
            for lender in LENDER_LIST
        ]

    def get_required_pii_fields(self, loan_type: str) -> list[str]:
        """Return the PII fields required for a given loan type."""
        return list(PII_FIELDS_BY_LOAN_TYPE.get(loan_type, PERSONAL_LOAN_PII_FIELDS))

    def get_required_non_pii_fields(self, loan_type: str) -> list[str]:
        """Return the non-PII fields required for a given loan type."""
        return list(
            NON_PII_FIELDS_BY_LOAN_TYPE.get(
                loan_type, NON_PII_FIELDS_BY_LOAN_TYPE[LoanType.PERSONAL]
            )
        )

    def get_lenders(
        self,
        loan_type: str | None = None,
        query: str | None = None,
    ) -> list[Lender]:
        """List available lenders, optionally filtered.

        Args:
            loan_type: Filter by loan type.
            query: Fuzzy search on lender name or description.

        Returns:
            List of matching Lender objects.
        """
        results = [p.lender for p in self._providers]

        if loan_type:
            results = [
                lender for lender in results if loan_type in lender.loan_types_offered
            ]

        if query:
            query_lower = query.lower()
            filtered = [
                lender
                for lender in results
                if query_lower in lender.lender_name.lower()
                or query_lower in lender.description.lower()
            ]
            return filtered if filtered else results

        return results

    def apply_for_all_lenders(
        self,
        pii_tokens: dict[str, str],
        loan_type: str,
        non_pii_info: dict[str, Any],
    ) -> list[LoanOffer]:
        """Query ALL eligible lenders and return aggregated offers sorted by rate.

        Each lender receives only the token minted for its platform.

        Args:
            pii_tokens: Dict of platform_id -> opaque PII token.
            loan_type: The loan type to apply for.
            non_pii_info: Non-PII application data (loan amount, etc.).

        Returns:
            List of LoanOffer objects sorted by rate (lowest first).
        """
        all_offers: list[LoanOffer] = []

        for provider in self._providers:
            if loan_type in provider.lender.loan_types_offered:
                token = pii_tokens.get(provider.lender.platform_id)
                if token:
                    offers = provider.generate_offers(token, non_pii_info, loan_type)
                    all_offers.extend(offers)

        all_offers.sort(key=lambda o: o.rate)
        return all_offers


class LendingCheckoutManager:
    """Manages the lending business logic on checkouts.

    Owns the start_lending flow: sets PII handlers, required fields,
    eligible lenders, and lending status on the checkout object.
    Uses the store for checkout I/O and the pii_provider / loan_registry
    for lending-specific data.
    """

    def __init__(
        self,
        store: ServiceStore,
        pii_provider: PIIProvider,
        loan_registry: LoanProviderRegistry,
        ucp_metadata: dict[str, Any],
    ) -> None:
        self._store = store
        self._pii_provider = pii_provider
        self._loan_registry = loan_registry
        self._ucp_metadata = ucp_metadata

    def start_lending(
        self,
        checkout_id: str,
        loan_type: str,
        user_email: str | None = None,
    ):
        """Initialize the lending flow on a checkout.

        Sets PII handlers, required fields, and lending status.

        Args:
            checkout_id: Checkout ID.
            loan_type: The loan type (personal or car).
            user_email: Optional user email for PII status check.

        Returns:
            Updated checkout with lending info.

        Raises:
            ValueError: If checkout not found.
        """
        checkout = self._store.get_checkout(checkout_id)
        if checkout is None:
            raise ValueError(f"Checkout with ID {checkout_id} not found")

        pii_handlers = resolve_pii_handlers(self._ucp_metadata)
        lending_handler = resolve_lending_handler(self._ucp_metadata)
        required_pii = self._loan_registry.get_required_pii_fields(loan_type)
        required_non_pii = self._loan_registry.get_required_non_pii_fields(loan_type)
        missing_pii = (
            self._pii_provider.get_missing_fields(user_email, required_pii)
            if user_email
            else required_pii
        )
        lenders = self._loan_registry.get_lenders(loan_type=loan_type)

        status = "pii_missing" if missing_pii else "consent_needed"

        checkout.lending = LendingResponse(
            loan_type=loan_type,
            handlers=pii_handlers,
            lending_handler=lending_handler,
            lenders=lenders,
            status=status,
            required_pii_fields=required_pii,
            required_non_pii_fields=required_non_pii,
            missing_pii_fields=missing_pii if missing_pii else None,
        )

        self._store.save_checkout(checkout_id, checkout)
        return checkout
