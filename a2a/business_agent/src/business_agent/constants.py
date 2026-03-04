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

"""UCP constants and configuration.

Constants are organized into namespaced classes per domain so that new
UCP extensions can add their own keys without risk of collision.
Flat module-level aliases are kept for backward compatibility.
"""

import os


# ---------------------------------------------------------------------------
# Environment / Square configuration
# ---------------------------------------------------------------------------

SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN", "")
SQUARE_SANDBOX = os.getenv("SQUARE_SANDBOX", "true").lower() == "true"


# ---------------------------------------------------------------------------
# Namespaced state-key classes (preferred for new code)
# ---------------------------------------------------------------------------


class CoreKeys:
    """State keys shared across all domains."""

    UCP_METADATA = "__ucp_metadata__"
    EXTENSIONS = "__session_extensions__"
    LATEST_TOOL_RESULT = "temp:LATEST_TOOL_RESULT"
    CHECKOUT_ID = "user:checkout_id"


class ShoppingKeys:
    """State and response keys for the shopping/checkout domain."""

    PAYMENT_STATE = "__payment_data__"
    CHECKOUT = "a2a.ucp.checkout"
    PAYMENT_DATA = "a2a.ucp.checkout.payment_data"
    RISK_SIGNALS = "a2a.ucp.checkout.risk_signals"


class LendingKeys:
    """State and response keys for the lending domain."""

    PII_STATE = "__pii_data__"
    PII_DATA = "a2a.ucp.checkout.pii_data"
    PII_COLLECTION = "a2a.ucp.checkout.pii_collection"
    LOAN_APPLICATION = "a2a.ucp.checkout.loan_application"


# ---------------------------------------------------------------------------
# Flat aliases (backward compatibility — existing code uses these)
# ---------------------------------------------------------------------------

# Core
ADK_USER_CHECKOUT_ID = CoreKeys.CHECKOUT_ID
ADK_UCP_METADATA_STATE = CoreKeys.UCP_METADATA
ADK_EXTENSIONS_STATE_KEY = CoreKeys.EXTENSIONS
ADK_LATEST_TOOL_RESULT = CoreKeys.LATEST_TOOL_RESULT

# Shopping
ADK_PAYMENT_STATE = ShoppingKeys.PAYMENT_STATE
UCP_CHECKOUT_KEY = ShoppingKeys.CHECKOUT
UCP_PAYMENT_DATA_KEY = ShoppingKeys.PAYMENT_DATA
UCP_RISK_SIGNALS_KEY = ShoppingKeys.RISK_SIGNALS

# Lending
ADK_PII_STATE = LendingKeys.PII_STATE
UCP_PII_DATA_KEY = LendingKeys.PII_DATA
UCP_PII_COLLECTION_KEY = LendingKeys.PII_COLLECTION
UCP_LOAN_APPLICATION_KEY = LendingKeys.LOAN_APPLICATION


# ---------------------------------------------------------------------------
# Extension URIs and protocol constants
# ---------------------------------------------------------------------------

A2A_UCP_EXTENSION_URL = "https://ucp.dev/specification/reference?v=2026-01-11"

UCP_AGENT_HEADER = "UCP-Agent"
UCP_FULFILLMENT_EXTENSION = "dev.ucp.shopping.fulfillment"
UCP_BUYER_CONSENT_EXTENSION = "dev.ucp.shopping.buyer_consent"
UCP_DISCOUNT_EXTENSION = "dev.ucp.shopping.discount"

UCP_APPOINTMENT_EXTENSION = "com.viaschema.appointment"
UCP_LENDING_EXTENSION = "com.viaschema.lending"
