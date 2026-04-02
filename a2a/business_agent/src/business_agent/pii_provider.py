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

"""PII Provider: protocol, base class, mock implementation, and HTTP routes.

The agent never sees raw PII — only opaque tokens that reference
stored PII in the provider. BasePIIProvider implements the shared
token/consent machinery; subclasses implement storage-specific logic.
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, NamedTuple, Protocol

from a2a.types import Task, TaskState, TaskStatus

logger = logging.getLogger(__name__)

from .models.lending_types import PIIConsent, PIICredential, PIIInstrument


class PIIProvider(Protocol):
    """Protocol for PII storage and token management.

    Both MockPIIProvider and VGSPIIProvider implement this interface.
    """

    def get_stored_fields(self, user_email: str) -> list[str]: ...
    def get_missing_fields(
        self, user_email: str, required_fields: list[str]
    ) -> list[str]: ...
    def store_pii(self, user_email: str, pii_data: dict[str, Any]) -> dict: ...
    def process_pii(self, pii_instrument: PIIInstrument) -> Task: ...
    def issue_token(
        self,
        user_email: str,
        platform_id: str = "_default",
        fields: list[str] | None = None,
    ) -> str: ...
    def resolve_token(self, token: str, platform_id: str) -> dict[str, Any] | None: ...
    def forward_pii(
        self,
        token: str,
        platform_id: str,
        url: str,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None: ...
    def issue_consent(
        self, user_email: str, consent: PIIConsent
    ) -> tuple[str, list[PIIInstrument]]: ...


TOKEN_TTL_SECONDS = 3600  # 1 hour


class TokenEntry(NamedTuple):
    """Immutable record for an issued PII token."""

    email: str
    platform_id: str
    created_at: float
    allowed_fields: frozenset[str]


# ---------------------------------------------------------------------------
# Base class with shared token/consent logic
# ---------------------------------------------------------------------------


class BasePIIProvider(ABC):
    """Base class implementing token issuance, validation, and consent.

    Subclasses implement storage-specific methods (get_stored_fields,
    store_pii, resolve_token, forward_pii). The token and consent
    machinery is identical across all providers.
    """

    def __init__(self, handler_names: dict[str, str] | None = None) -> None:
        self._handler_names = handler_names or {}
        self._tokens: dict[str, TokenEntry] = {}
        self._consents: dict[str, PIIConsent] = {}

    # -- Abstract: subclasses implement these --

    @abstractmethod
    def get_stored_fields(self, user_email: str) -> list[str]: ...

    @abstractmethod
    def get_missing_fields(
        self, user_email: str, required_fields: list[str]
    ) -> list[str]: ...

    @abstractmethod
    def store_pii(self, user_email: str, pii_data: dict[str, Any]) -> dict: ...

    @abstractmethod
    def resolve_token(
        self, token: str, platform_id: str
    ) -> dict[str, Any] | None: ...

    @abstractmethod
    def forward_pii(
        self,
        token: str,
        platform_id: str,
        url: str,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None: ...

    # -- Shared implementations --

    def _validate_token(self, token: str, platform_id: str | None = None) -> TokenEntry | None:
        """Validate a token and return its entry, or None if invalid."""
        entry = self._tokens.get(token)
        if entry is None:
            return None
        if time.time() - entry.created_at > TOKEN_TTL_SECONDS:
            return None
        if platform_id and entry.platform_id != platform_id:
            return None
        return entry

    def process_pii(self, pii_instrument: PIIInstrument) -> Task:
        """Validate a PII token."""
        entry = self._validate_token(
            pii_instrument.credential.token, pii_instrument.platform_id
        )
        state = TaskState.completed if entry else TaskState.failed
        return Task(
            context_id="pii_validation",
            id=str(uuid.uuid4()),
            status=TaskStatus(state=state),
        )

    def issue_token(
        self,
        user_email: str,
        platform_id: str = "_default",
        fields: list[str] | None = None,
    ) -> str:
        """Issue a field-scoped, platform-scoped PII token for a user."""
        token = f"pii_token_{uuid.uuid4()}"
        allowed = (
            frozenset(fields)
            if fields
            else frozenset(self.get_stored_fields(user_email))
        )
        self._tokens[token] = TokenEntry(user_email, platform_id, time.time(), allowed)
        return token

    def issue_consent(
        self, user_email: str, consent: PIIConsent
    ) -> tuple[str, list[PIIInstrument]]:
        """Process a formal PIIConsent: validate, record, and mint tokens."""
        if not consent.platform_ids:
            raise ValueError("platform_ids must not be empty")
        if not consent.fields_consented:
            raise ValueError("fields_consented must not be empty")

        consent_id = f"consent_{uuid.uuid4()}"
        self._consents[consent_id] = consent

        instruments: list[PIIInstrument] = []
        for platform_id in consent.platform_ids:
            token = self.issue_token(
                user_email, platform_id, fields=consent.fields_consented
            )
            token_entry = self._tokens[token]
            instruments.append(
                PIIInstrument(
                    id=consent.pii_method_id,
                    handler_id=consent.handler_id,
                    handler_name=self._handler_names.get(
                        consent.handler_id, consent.handler_id
                    ),
                    fields_stored=sorted(token_entry.allowed_fields),
                    loan_type=consent.loan_type,
                    platform_id=platform_id,
                    credential=PIICredential(type="token", token=token),
                )
            )

        return consent_id, instruments


# ---------------------------------------------------------------------------
# Mock implementation (in-memory storage)
# ---------------------------------------------------------------------------


class MockPIIProvider(BasePIIProvider):
    """Mock PII Provider with in-memory storage.

    Pre-seeded with a demo user so the consent-only flow works out of the box.
    """

    def __init__(self, handler_names: dict[str, str] | None = None) -> None:
        super().__init__(handler_names)
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

    def get_stored_fields(self, user_email: str) -> list[str]:
        return list(self._stored_pii.get(user_email, {}).keys())

    def get_missing_fields(
        self, user_email: str, required_fields: list[str]
    ) -> list[str]:
        stored = set(self.get_stored_fields(user_email))
        return sorted(set(required_fields) - stored)

    def store_pii(self, user_email: str, pii_data: dict[str, Any]) -> dict:
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

    def resolve_token(self, token: str, platform_id: str) -> dict[str, Any] | None:
        entry = self._validate_token(token, platform_id)
        if entry is None:
            return None
        all_pii = self._stored_pii.get(entry.email)
        if all_pii is None:
            return None
        return {k: v for k, v in all_pii.items() if k in entry.allowed_fields}

    def forward_pii(
        self,
        token: str,
        platform_id: str,
        url: str,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        import httpx

        pii_data = self.resolve_token(token, platform_id)
        if pii_data is None:
            return None

        payload: dict[str, Any] = {**pii_data}
        if extra_data:
            payload.update(extra_data)

        try:
            response = httpx.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            logger.exception("forward_pii: HTTP error sending to %s", url)
            return None


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------


def create_pii_vault_routes(provider: PIIProvider) -> list:
    """Create Starlette routes for PII vault HTTP endpoints."""
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def pii_store_handler(request: Request) -> JSONResponse:
        body = await request.json()
        email = body["email"]
        pii_data = body["pii_data"]
        logger.info("POST /pii/store — email=%s pii_data=%s", email, pii_data)
        result = provider.store_pii(email, pii_data)
        result["email"] = email
        logger.info("POST /pii/store — result=%s", result)
        return JSONResponse(result)

    async def pii_stored_fields_handler(request: Request) -> JSONResponse:
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
                "instruments": [inst.model_dump(mode="json") for inst in instruments],
            }
        )

    return [
        Route("/pii/store", pii_store_handler, methods=["POST"]),
        Route("/pii/stored-fields", pii_stored_fields_handler, methods=["POST"]),
        Route("/pii/consent", pii_consent_handler, methods=["POST"]),
    ]
