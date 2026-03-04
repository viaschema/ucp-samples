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

"""Lending domain module — lender search, PII management, and loan applications."""

from __future__ import annotations

from ..constants import UCP_LENDING_EXTENSION
from ..lending_tools import (
    get_pii_requirements,
    search_lenders,
    start_lending,
    submit_loan_application,
)
from ..models.lending_types import LendingCheckout, LendingResponse, PIIHandler
from .base import DomainModule


class LendingDomain(DomainModule):
    """Lending domain — lender search, PII collection, and loan applications."""

    @property
    def capability_uri(self) -> str:
        return UCP_LENDING_EXTENSION

    @property
    def tools(self) -> list:
        return [
            search_lenders,
            get_pii_requirements,
            start_lending,
            submit_loan_application,
        ]

    @property
    def agent_instructions(self) -> str:
        return (
            "Loan application workflow:\n"
            "1. Search available lenders (search_lenders) with optional "
            "loan_type filter\n"
            "2. Start the lending flow (start_lending) with the desired "
            "loan type\n"
            "3. The frontend collects PII directly via the PII vault — "
            "the agent never handles raw PII data\n"
            "4. Once PII is complete, the frontend handles PII token "
            "authorization\n"
            "5. Submit the loan application (submit_loan_application) to "
            "get offers from ALL eligible lenders sorted by rate"
        )

    @property
    def checkout_mixin(self) -> type:
        return LendingCheckout

    @property
    def response_data_keys(self) -> list[str]:
        return [
            "a2a.ucp.lending.lenders",
            "a2a.ucp.lending.loan_offers",
        ]

    def initialize_checkout_fields(self, checkout, ucp_metadata: dict) -> None:
        if hasattr(checkout, "lending"):
            pii_handlers = [
                PIIHandler(**h)
                for h in ucp_metadata.get("pii", {}).get("handlers", [])
            ]
            checkout.lending = LendingResponse(handlers=pii_handlers)
