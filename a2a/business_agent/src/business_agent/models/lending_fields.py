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

"""Typed PII field definitions for the lending capability.

Reuses UCP canonical Buyer and PostalAddress types for standard identity
fields, and adds finance-specific typed fields for loan applications.
Models can generate JSON schemas via ``model_json_schema()`` for use in
documentation, validation, and schema negotiation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from ucp_sdk.models.schemas.shopping.types.buyer import Buyer
from ucp_sdk.models.schemas.shopping.types.postal_address import PostalAddress

from .lending_types import LoanType


class FinanceProfile(BaseModel):
    """Finance-specific PII fields for loan applications.

    These fields have no equivalent in the UCP core Buyer model and are
    specific to lending workflows.
    """

    model_config = ConfigDict(extra="allow")

    date_of_birth: str | None = Field(
        default=None, description="Date of birth (ISO 8601, e.g. 1990-01-15)"
    )
    annual_income: str | None = Field(
        default=None, description="Annual income in dollars"
    )
    living_situation: str | None = Field(
        default=None,
        description="Housing status: rent, fully_own, or mortgage",
    )
    monthly_housing_payment: str | None = Field(
        default=None, description="Monthly housing cost in dollars"
    )
    employment_status: str | None = Field(
        default=None,
        description="Employment status: employed, self_employed, unemployed, or retired",
    )
    employer_phone_number: str | None = Field(
        default=None, description="Employer phone number (E.164)"
    )
    employer_address: PostalAddress | None = Field(
        default=None, description="Employer postal address"
    )


class BorrowerPII(Buyer, FinanceProfile):
    """Complete borrower PII model for lending applications.

    Composes UCP canonical Buyer fields with finance-specific fields.

    From Buyer (UCP canonical):
        first_name, last_name, full_name, email, phone_number

    From FinanceProfile (lending-specific):
        date_of_birth, annual_income, living_situation,
        monthly_housing_payment, employment_status,
        employer_phone_number, employer_address

    Own field:
        address — borrower's postal address (UCP PostalAddress)
    """

    model_config = ConfigDict(extra="allow")

    address: PostalAddress | None = Field(
        default=None, description="Borrower postal address"
    )


# ---------------------------------------------------------------------------
# Field-list constants used by loan_provider and pii_provider.
#
# Field names match the model attribute names above, which in turn align
# with UCP canonical naming (phone_number, not phone).
# ---------------------------------------------------------------------------

PERSONAL_LOAN_PII_FIELDS: list[str] = [
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "address",
    "date_of_birth",
    "annual_income",
    "living_situation",
]

CAR_LOAN_PII_FIELDS: list[str] = [
    *PERSONAL_LOAN_PII_FIELDS,
    "monthly_housing_payment",
    "employment_status",
    "employer_address",
    "employer_phone_number",
]

PII_FIELDS_BY_LOAN_TYPE: dict[str, list[str]] = {
    LoanType.PERSONAL: PERSONAL_LOAN_PII_FIELDS,
    LoanType.CAR: CAR_LOAN_PII_FIELDS,
}

NON_PII_FIELDS_BY_LOAN_TYPE: dict[str, list[str]] = {
    LoanType.PERSONAL: ["loan_amount_requested", "desired_monthly_payment"],
    LoanType.CAR: ["car_brand", "vin", "car_value", "desired_monthly_payment"],
}
