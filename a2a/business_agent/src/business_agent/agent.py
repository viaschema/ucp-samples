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

"""Agent assembly — builds the root ADK agent from registered domain modules.

This file is the single place where domain modules are registered and the
root agent is composed. To add a new UCP domain:

    1. Create a new ``DomainModule`` subclass (e.g., ``domains/insurance.py``)
    2. Import and register it in the ``_build_registry()`` function below
    3. That's it — tools, instructions, checkout mixins, and response keys
       are picked up automatically.
"""

from __future__ import annotations

from typing import Any

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from .a2a_extensions import UcpExtension
from .constants import (
    ADK_EXTENSIONS_STATE_KEY,
    ADK_LATEST_TOOL_RESULT,
    UCP_CHECKOUT_KEY,
)
from .dependencies import store  # noqa: F401 — re-exported for test compat
from .domains import DomainRegistry
from .domains.appointments import (
    AppointmentDomain,
    cancel_booking,  # noqa: F401
    get_bookings,  # noqa: F401
    list_locations,  # noqa: F401
    list_staff,  # noqa: F401
    search_availability,  # noqa: F401
    set_appointment,  # noqa: F401
)
from .domains.lending import LendingDomain
from .domains.shopping import (
    ShoppingDomain,
    add_to_checkout,  # noqa: F401
    complete_checkout,  # noqa: F401
    get_checkout,  # noqa: F401
    remove_from_checkout,  # noqa: F401
    search_shopping_catalog,  # noqa: F401
    start_payment,  # noqa: F401
    update_checkout,  # noqa: F401
    update_customer_details,  # noqa: F401
)


# ---------------------------------------------------------------------------
# Domain registry assembly
# ---------------------------------------------------------------------------


def _build_registry() -> DomainRegistry:
    """Build and return the domain registry with all UCP extensions.

    To add a new domain, import its DomainModule subclass and register it
    here. The registry aggregates tools, instructions, and response keys
    so the root agent picks them up automatically.
    """
    registry = DomainRegistry()
    registry.register(ShoppingDomain())
    registry.register(AppointmentDomain())
    registry.register(LendingDomain())
    return registry


domain_registry = _build_registry()


# ---------------------------------------------------------------------------
# After-tool and after-agent callbacks
# ---------------------------------------------------------------------------


def after_tool_modifier(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict,
) -> dict | None:
    """Store structured UCP responses in session state for the executor."""
    extensions = tool_context.state.get(ADK_EXTENSIONS_STATE_KEY, [])

    # Collect all response keys from registered domains + checkout key
    ucp_response_keys = [UCP_CHECKOUT_KEY] + domain_registry.all_response_data_keys

    if UcpExtension.URI in extensions and any(
        key in tool_response for key in ucp_response_keys
    ):
        tool_context.state[ADK_LATEST_TOOL_RESULT] = tool_response

    return None


def modify_output_after_agent(
    callback_context: CallbackContext,
) -> types.Content | None:
    """Emit the latest tool result as the agent's structured output."""
    latest_result = callback_context.state.get(ADK_LATEST_TOOL_RESULT)
    if latest_result:
        return types.Content(
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        response={"result": latest_result}
                    )
                )
            ],
            role="model",
        )

    return None


# ---------------------------------------------------------------------------
# Root agent definition
# ---------------------------------------------------------------------------


root_agent = Agent(
    name="service_booking_agent",
    model="gemini-3-flash-preview",
    description="Agent to help with service booking, appointments, and loans",
    instruction=domain_registry.combined_instructions,
    tools=domain_registry.all_tools,
    after_tool_callback=after_tool_modifier,
    after_agent_callback=modify_output_after_agent,
)
