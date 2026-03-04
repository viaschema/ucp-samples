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

"""Domain module registry for UCP extensions.

The ``DomainRegistry`` collects all registered domain modules and provides
aggregate access to tools, instructions, checkout mixins, and response keys.
This is the single entry-point for the agent assembly in ``agent.py``.
"""

from __future__ import annotations

from typing import Any, Callable

from .base import DomainModule

__all__ = [
    "DomainModule",
    "DomainRegistry",
]


class DomainRegistry:
    """Central registry of UCP domain modules.

    Usage::

        from .domains import DomainRegistry
        from .domains.shopping import ShoppingDomain
        from .domains.appointments import AppointmentDomain
        from .domains.lending import LendingDomain

        registry = DomainRegistry()
        registry.register(ShoppingDomain())
        registry.register(AppointmentDomain())
        registry.register(LendingDomain())

        # Use in agent assembly:
        root_agent = Agent(
            tools=registry.all_tools,
            instruction=registry.combined_instructions,
        )
    """

    def __init__(self) -> None:
        self._domains: list[DomainModule] = []

    def register(self, domain: DomainModule) -> None:
        """Register a domain module."""
        self._domains.append(domain)

    @property
    def domains(self) -> list[DomainModule]:
        """All registered domain modules."""
        return list(self._domains)

    @property
    def all_tools(self) -> list[Callable]:
        """Flat list of all tools across registered domains."""
        return [tool for domain in self._domains for tool in domain.tools]

    @property
    def combined_instructions(self) -> str:
        """Combined agent instruction text from all domains."""
        parts = [
            "You are a helpful agent. You can help users with the following:\n"
        ]
        for domain in self._domains:
            parts.append(domain.agent_instructions)
        parts.append(
            "Always confirm details with the user before completing "
            "any transaction or booking."
        )
        return "\n\n".join(parts)

    @property
    def all_response_data_keys(self) -> list[str]:
        """All A2A response data keys across registered domains."""
        return [key for domain in self._domains for key in domain.response_data_keys]

    def get_checkout_mixins(
        self, active_capabilities: set[str]
    ) -> list[type]:
        """Return checkout Pydantic mixins for the given active capabilities."""
        mixins = []
        for domain in self._domains:
            if (
                domain.capability_uri in active_capabilities
                and domain.checkout_mixin is not None
            ):
                mixins.append(domain.checkout_mixin)
        return mixins

    def initialize_checkout(
        self,
        checkout: Any,
        ucp_metadata: dict,
        active_capabilities: set[str],
    ) -> None:
        """Initialize domain-specific fields on a new checkout."""
        for domain in self._domains:
            if domain.capability_uri in active_capabilities:
                domain.initialize_checkout_fields(checkout, ucp_metadata)
