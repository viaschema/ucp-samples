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

"""VGS-backed PII Provider.

Extends BasePIIProvider with VGS vault storage. PII values are tokenized
via VGS Aliases API (redact) and only revealed (detokenized) when lenders
need actual data. The agent never sees raw PII — only opaque VGS aliases.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
import vgs

from .models.lending_fields import BorrowerPII
from .pii_provider import BasePIIProvider

logger = logging.getLogger(__name__)

# All valid BorrowerPII top-level field names (used for name-only validation).
_KNOWN_PII_FIELDS: frozenset[str] = frozenset(BorrowerPII.model_fields.keys())

# Demo user PII for seeding on startup.
_DEMO_PII: dict[str, Any] = {
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
}


_ADDRESS_PREFIXES = ("address_", "employer_address_")


def _flatten_pii(pii_data: dict[str, Any]) -> dict[str, str]:
    """Flatten nested address dicts to underscore-separated keys."""
    flat: dict[str, str] = {}
    for key, value in pii_data.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat[f"{key}_{sub_key}"] = str(sub_value)
        else:
            flat[key] = str(value)
    return flat


def _unflatten_pii(flat: dict[str, str]) -> dict[str, Any]:
    """Reconstruct nested address dicts from flat underscore-separated keys."""
    result: dict[str, Any] = {}
    for key, value in flat.items():
        matched = False
        for prefix in _ADDRESS_PREFIXES:
            if key.startswith(prefix):
                parent = prefix.rstrip("_")
                child = key[len(prefix) :]
                result.setdefault(parent, {})[child] = value
                matched = True
                break
        if not matched:
            result[key] = value
    return result


def _top_level_field(key: str) -> str:
    """Return the top-level field name from a possibly flattened key."""
    for prefix in _ADDRESS_PREFIXES:
        if key.startswith(prefix):
            return prefix.rstrip("_")
    return key


class VGSPIIProvider(BasePIIProvider):
    """VGS-backed PII provider.

    Extends BasePIIProvider (which provides token/consent machinery)
    with VGS vault storage. Only the storage-specific methods are
    implemented here.
    """

    def __init__(
        self,
        vault_id: str,
        username: str,
        password: str,
        environment: str = "sandbox",
        handler_names: dict[str, str] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        super().__init__(handler_names)
        config = vgs.VGSConfiguration(
            vault_id=vault_id,
            username=username,
            password=password,
            environment=environment,
        )
        self._aliases_api = vgs.Aliases(config)
        self._vault_id = vault_id
        self._http_client = http_client or httpx.Client()

        # Per-user alias storage: email → {flat_field_name: vgs_alias}
        self._stored_aliases: dict[str, dict[str, str]] = {}

        self._seed_demo_user()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_demo_user(self) -> None:
        """Pre-populate the demo user via VGS redact."""
        try:
            self.store_pii_raw("foo@example.com", _DEMO_PII)
            logger.info(
                "VGS: Seeded demo user foo@example.com with %d aliases",
                len(self._stored_aliases.get("foo@example.com", {})),
            )
        except Exception:
            logger.exception(
                "VGS: Failed to seed demo user — "
                "the consent-only demo flow will not work"
            )

    # ------------------------------------------------------------------
    # Storage (abstract method implementations)
    # ------------------------------------------------------------------

    def store_pii_raw(self, user_email: str, pii_data: dict[str, Any]) -> dict:
        """Tokenize raw PII values via VGS and store the resulting aliases."""
        flat = _flatten_pii(pii_data)
        redact_items = [
            {
                "value": value,
                "classifiers": [key],
                "format": "UUID",
                "storage": "PERSISTENT",
            }
            for key, value in flat.items()
        ]

        result = self._aliases_api.redact(redact_items)

        if user_email not in self._stored_aliases:
            self._stored_aliases[user_email] = {}

        for item, key in zip(result, flat.keys()):
            alias = item["aliases"][0]["alias"]
            self._stored_aliases[user_email][key] = alias

        return {
            "status": "stored",
            "fields_stored": self._top_level_fields(user_email),
        }

    def store_pii(self, user_email: str, pii_data: dict[str, Any]) -> dict:
        """Store PII data — aliases from VGS route or raw values (fallback)."""
        flat = _flatten_pii(pii_data)

        for key in flat:
            top = _top_level_field(key)
            if top not in _KNOWN_PII_FIELDS:
                logger.warning("VGS store_pii: ignoring unknown field %r", top)

        sample_values = list(flat.values())[:3]
        already_tokenized = all(v.startswith("tok_") for v in sample_values if v)

        if already_tokenized:
            if user_email not in self._stored_aliases:
                self._stored_aliases[user_email] = {}
            self._stored_aliases[user_email].update(flat)
        else:
            return self.store_pii_raw(user_email, pii_data)

        return {
            "status": "stored",
            "fields_stored": self._top_level_fields(user_email),
        }

    def _top_level_fields(self, user_email: str) -> list[str]:
        aliases = self._stored_aliases.get(user_email, {})
        return sorted({_top_level_field(k) for k in aliases})

    def get_stored_fields(self, user_email: str) -> list[str]:
        return self._top_level_fields(user_email)

    def get_missing_fields(
        self, user_email: str, required_fields: list[str]
    ) -> list[str]:
        stored = set(self.get_stored_fields(user_email))
        return sorted(set(required_fields) - stored)

    # ------------------------------------------------------------------
    # Token resolution (storage-specific)
    # ------------------------------------------------------------------

    def resolve_token(self, token: str, platform_id: str) -> dict[str, Any] | None:
        """Resolve a PII token by revealing VGS aliases."""
        entry = self._validate_token(token, platform_id)
        if entry is None:
            return None

        user_aliases = self._stored_aliases.get(entry.email)
        if user_aliases is None:
            return None

        aliases_to_reveal: list[str] = []
        alias_to_key: dict[str, str] = {}
        raw_values: dict[str, str] = {}

        for key, value in user_aliases.items():
            top = _top_level_field(key)
            if top not in entry.allowed_fields:
                continue
            if isinstance(value, str) and value.startswith("tok_"):
                aliases_to_reveal.append(value)
                alias_to_key[value] = key
            else:
                raw_values[key] = value

        flat_result: dict[str, str] = dict(raw_values)

        if aliases_to_reveal:
            try:
                revealed = self._aliases_api.reveal(aliases_to_reveal)
            except Exception:
                logger.exception(
                    "VGS: Failed to reveal aliases for token %s", token[:20]
                )
                return None

            for alias, data in revealed.items():
                key = alias_to_key.get(alias)
                if key:
                    flat_result[key] = data["value"]

        if not flat_result:
            return None

        return _unflatten_pii(flat_result)

    def forward_pii(
        self,
        token: str,
        platform_id: str,
        url: str,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Send PII aliases to a URL via VGS outbound proxy."""
        entry = self._validate_token(token, platform_id)
        if entry is None:
            return None

        user_aliases = self._stored_aliases.get(entry.email)
        if user_aliases is None:
            return None

        filtered = {
            k: v
            for k, v in user_aliases.items()
            if _top_level_field(k) in entry.allowed_fields
        }
        if not filtered:
            return None

        payload: dict[str, Any] = {**_unflatten_pii(filtered)}
        if extra_data:
            payload.update(extra_data)

        try:
            response = self._http_client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            logger.exception("forward_pii: HTTP error sending to %s", url)
            return None
