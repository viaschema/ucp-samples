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

"""Mock PII Provider simulating a trusted third-party PII vault.

Analogous to MockPaymentProcessor but for PII storage and retrieval.
The agent never sees raw PII - only opaque tokens that reference
stored PII in this provider.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, NamedTuple

from a2a.types import Task, TaskState, TaskStatus

from .models.lending_types import PIIConsent, PIIInstrument

TOKEN_TTL_SECONDS = 3600  # 1 hour


class TokenEntry(NamedTuple):
    """Immutable record for an issued PII token."""

    email: str
    platform_id: str
    created_at: float
    allowed_fields: frozenset[str]


class MockPIIProvider:
    """Mock PII Provider simulating Merchant Agent to PII Provider Agent calls.

    Analogous to MockPaymentProcessor but for PII storage and retrieval.
    Manages per-user PII storage, token issuance, and mock loan offer generation.
    """

    def __init__(self) -> None:
        # Per-user PII storage: email -> {field_name: value}
        # Pre-seeded with a demo user so the default flow demonstrates Path A
        # (consent) without requiring collection first.
        self._stored_pii: dict[str, dict[str, Any]] = {
            "foo@example.com": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "foo@example.com",
                "phone_number": "+15551234567",
                "address": {
                    "street_address": "123 Main St",
                    "address_locality": "San Francisco",
                    "address_region": "CA",
                    "postal_code": "94102",
                    "address_country": "US",
                },
                "date_of_birth": "1990-01-15",
                "annual_income": "85000",
                "living_situation": "rent",
                "monthly_housing_payment": "2500",
                "employment_status": "employed",
                "employer_address": {
                    "street_address": "456 Market St",
                    "address_locality": "San Francisco",
                    "address_region": "CA",
                    "postal_code": "94105",
                    "address_country": "US",
                },
                "employer_phone_number": "+15555678901",
            },
        }
        # Token -> TokenEntry mapping for validation and field-level access control
        self._tokens: dict[str, TokenEntry] = {}
        # Consent records: consent_id -> PIIConsent
        self._consents: dict[str, PIIConsent] = {}

    def get_stored_fields(self, user_email: str) -> list[str]:
        """Return which PII fields are already stored for a user."""
        user_pii = self._stored_pii.get(user_email, {})
        return list(user_pii.keys())

    def get_missing_fields(
        self, user_email: str, required_fields: list[str]
    ) -> list[str]:
        """Return required PII fields not yet stored for the user.

        Args:
            user_email: User's email address.
            required_fields: List of required field names.

        Returns:
            Sorted list of missing field names.
        """
        stored = set(self.get_stored_fields(user_email))
        return sorted(set(required_fields) - stored)

    def store_pii(self, user_email: str, pii_data: dict[str, Any]) -> dict:
        """Store PII fields for a user. Can be called incrementally.

        Validates the incoming data against the BorrowerPII model so that
        field names and types are checked, while still supporting partial
        (incremental) updates — unset fields default to None and are excluded.

        Args:
            user_email: User's email address.
            pii_data: Dictionary of PII field name -> value.

        Returns:
            Dict with status and list of all stored field names.
        """
        from .models.lending_fields import BorrowerPII

        validated = BorrowerPII.model_validate(pii_data)
        update = validated.model_dump(exclude_none=True)

        if user_email not in self._stored_pii:
            self._stored_pii[user_email] = {}
        self._stored_pii[user_email].update(update)
        return {
            "status": "stored",
            "fields_stored": list(self._stored_pii[user_email].keys()),
        }

    def process_pii(self, pii_instrument: PIIInstrument) -> Task:
        """Validate a PII token. Mirrors MockPaymentProcessor.process_payment().

        Also verifies platform_id if present on the instrument.

        Args:
            pii_instrument: The PII instrument containing the token.

        Returns:
            Task with completed status if token is valid.
        """
        token = pii_instrument.credential.token
        entry = self._tokens.get(token)
        if entry is None:
            return Task(
                context_id="pii_validation",
                id=str(uuid.uuid4()),
                status=TaskStatus(state=TaskState.failed),
            )

        if time.time() - entry.created_at > TOKEN_TTL_SECONDS:
            return Task(
                context_id="pii_validation",
                id=str(uuid.uuid4()),
                status=TaskStatus(state=TaskState.failed),
            )
        if (
            pii_instrument.platform_id
            and entry.platform_id != pii_instrument.platform_id
        ):
            return Task(
                context_id="pii_validation",
                id=str(uuid.uuid4()),
                status=TaskStatus(state=TaskState.failed),
            )

        return Task(
            context_id="pii_validation",
            id=str(uuid.uuid4()),
            status=TaskStatus(state=TaskState.completed),
        )

    def issue_token(
        self,
        user_email: str,
        platform_id: str = "_default",
        fields: list[str] | None = None,
    ) -> str:
        """Issue a field-scoped, platform-scoped PII token for a user.

        Args:
            user_email: User's email address.
            platform_id: The platform this token is scoped to.
            fields: Subset of PII fields this token grants access to.
                    If None, grants access to all currently stored fields.

        Returns:
            An opaque token string.
        """
        token = f"pii_token_{uuid.uuid4()}"
        allowed = (
            frozenset(fields)
            if fields
            else frozenset(self.get_stored_fields(user_email))
        )
        self._tokens[token] = TokenEntry(user_email, platform_id, time.time(), allowed)
        return token

    def resolve_token(self, token: str, platform_id: str) -> dict[str, Any] | None:
        """Resolve a PII token to the stored PII data it grants access to.

        Verifies platform scope, TTL, and filters returned data to only
        the fields declared when the token was issued.

        Args:
            token: The opaque PII token.
            platform_id: The platform attempting to resolve this token.

        Returns:
            Dict of PII field name -> value (only the allowed subset),
            or None if token is invalid, expired, or platform mismatch.
        """
        entry = self._tokens.get(token)
        if entry is None:
            return None
        if entry.platform_id != platform_id:
            return None
        if time.time() - entry.created_at > TOKEN_TTL_SECONDS:
            return None
        all_pii = self._stored_pii.get(entry.email)
        if all_pii is None:
            return None
        return {k: v for k, v in all_pii.items() if k in entry.allowed_fields}


    def issue_consent(
        self, user_email: str, consent: PIIConsent
    ) -> tuple[str, list[PIIInstrument]]:
        """Process a formal PIIConsent: validate, record, and mint tokens.

        Args:
            user_email: User's email address.
            consent: The formal consent object from the frontend.

        Returns:
            Tuple of (consent_id, list of PIIInstruments with platform-scoped tokens).

        Raises:
            ValueError: If consent is invalid (empty platforms, no fields, etc.).
        """
        if not consent.platform_ids:
            raise ValueError("platform_ids must not be empty")
        if not consent.fields_consented:
            raise ValueError("fields_consented must not be empty")

        consent_id = f"consent_{uuid.uuid4()}"
        self._consents[consent_id] = consent

        instruments: list[PIIInstrument] = []
        from .models.lending_types import PIICredential

        for platform_id in consent.platform_ids:
            token = self.issue_token(
                user_email, platform_id, fields=consent.fields_consented
            )
            token_entry = self._tokens[token]
            instruments.append(
                PIIInstrument(
                    id=consent.pii_method_id,
                    handler_id=consent.handler_id,
                    handler_name="example.pii.provider",
                    fields_stored=sorted(token_entry.allowed_fields),
                    loan_type=consent.loan_type,
                    platform_id=platform_id,
                    credential=PIICredential(type="token", token=token),
                )
            )

        return consent_id, instruments


def create_pii_vault_routes(provider: MockPIIProvider) -> list:
    """Create Starlette routes for PII vault HTTP endpoints.

    Args:
        provider: The MockPIIProvider instance to use.

    Returns:
        List of Starlette Route objects.
    """
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def pii_store_handler(request: Request) -> JSONResponse:
        """Store PII fields for a user in the mock PII vault."""
        body = await request.json()
        result = provider.store_pii(body["email"], body["pii_data"])
        return JSONResponse(result)

    async def pii_stored_fields_handler(request: Request) -> JSONResponse:
        """Return stored PII field names for a user."""
        body = await request.json()
        fields = provider.get_stored_fields(body["email"])
        return JSONResponse(
            {
                "pii_methods": [
                    {
                        "id": "pii_profile_1",
                        "fields_stored": fields,
                        "loan_type": "all",
                    }
                ]
            }
        )

    async def pii_consent_handler(request: Request) -> JSONResponse:
        """Accept a formal PIIConsent, record it, and return platform-scoped tokens."""
        body = await request.json()
        email = body["email"]
        consent = PIIConsent.model_validate(body["consent"])
        try:
            consent_id, instruments = provider.issue_consent(email, consent)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse(
            {
                "consent_id": consent_id,
                "instruments": [
                    inst.model_dump(mode="json") for inst in instruments
                ],
            }
        )

    return [
        Route("/pii/store", pii_store_handler, methods=["POST"]),
        Route("/pii/stored-fields", pii_stored_fields_handler, methods=["POST"]),
        Route("/pii/consent", pii_consent_handler, methods=["POST"]),
    ]
