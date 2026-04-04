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

"""Shared singleton dependencies for the business agent.

Centralizes creation of ServiceStore and MockPaymentProcessor to avoid
circular imports between agent.py and lending_tools.py.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .payment_processor import MockPaymentProcessor
from .store import ServiceStore

if TYPE_CHECKING:
    from .loan_provider import LendingCheckoutManager, LoanProviderRegistry
    from .pii_provider import PIIProvider

store = ServiceStore()
mpp = MockPaymentProcessor()


def create_lending_dependencies() -> (
    tuple[PIIProvider, LoanProviderRegistry, LendingCheckoutManager]
):
    """Create lending dependencies based on environment configuration.

    Reads PII_PROVIDER, VGS_* env vars, and store.ucp_metadata at call
    time (not import time), making the module safe to import without
    side effects.
    """
    import httpx

    from .loan_provider import LendingCheckoutManager, LoanProviderRegistry

    ucp_meta = store.ucp_metadata
    handler_names: dict[str, str] = {
        h["id"]: h["name"]
        for h in ucp_meta.get("pii", {}).get("handlers", [])
    }

    if os.environ.get("PII_PROVIDER") == "mock":
        from .pii_provider import MockPIIProvider

        provider: PIIProvider = MockPIIProvider(handler_names=handler_names)
    else:
        from .vgs_pii_provider import VGSPIIProvider

        vault_id = os.environ.get("VGS_VAULT_ID", "")
        username = os.environ.get("VGS_USERNAME", "")
        password = os.environ.get("VGS_PASSWORD", "")
        environment = os.environ.get("VGS_ENVIRONMENT", "sandbox")

        http_client: httpx.Client | None = None
        if vault_id and username and password:
            proxy_url = (
                f"https://{username}:{password}"
                f"@{vault_id}.{environment}.verygoodproxy.com:8443"
            )
            http_client = httpx.Client(
                proxy=proxy_url,
                verify=environment != "sandbox",
            )

        provider = VGSPIIProvider(
            vault_id=vault_id,
            username=username,
            password=password,
            environment=environment,
            handler_names=handler_names,
            http_client=http_client,
        )

    # In VGS mode, lender API calls go through the VGS outbound proxy
    # which can't reach localhost — use the public URL from LENDER_API_BASE.
    lender_api_base = os.environ.get(
        "LENDER_API_BASE", "http://localhost:10999/lender-api"
    )

    registry = LoanProviderRegistry(provider, lender_api_base=lender_api_base)
    manager = LendingCheckoutManager(store, provider, registry, ucp_meta)
    return provider, registry, manager
