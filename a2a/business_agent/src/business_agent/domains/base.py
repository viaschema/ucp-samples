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

"""Base interface for UCP domain modules.

Each UCP extension (shopping, appointments, lending, etc.) is encapsulated
as a DomainModule. This pattern allows new extensions to be added without
modifying the core agent assembly or executor logic.

To add a new domain:
    1. Create a new file in this package (e.g., ``insurance.py``)
    2. Subclass ``DomainModule`` and implement the required properties
    3. Register the module in ``domains/__init__.py``
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from pydantic import BaseModel


class DomainModule(ABC):
    """Base class for a UCP domain extension.

    Each domain module encapsulates:
    - Its UCP capability URI
    - The agent tools it provides
    - Agent instruction text for its workflow
    - An optional Pydantic mixin for the dynamic checkout type
    - The A2A response data keys it produces
    """

    @property
    @abstractmethod
    def capability_uri(self) -> str:
        """The UCP capability URI (e.g., ``com.viaschema.appointment``)."""
        ...

    @property
    @abstractmethod
    def tools(self) -> list[Callable]:
        """Tool functions this domain provides to the agent."""
        ...

    @property
    @abstractmethod
    def agent_instructions(self) -> str:
        """Agent instruction text describing this domain's workflow."""
        ...

    @property
    def checkout_mixin(self) -> type[BaseModel] | None:
        """Optional Pydantic mixin to compose into the dynamic checkout type.

        Return ``None`` if this domain does not extend the checkout schema.
        """
        return None

    @property
    def response_data_keys(self) -> list[str]:
        """A2A response data keys this domain produces.

        Used by the ``after_tool_callback`` to detect structured UCP
        responses and store them in session state for the executor.
        """
        return []

    def initialize_checkout_fields(
        self, checkout: Any, ucp_metadata: dict
    ) -> None:
        """Initialize domain-specific fields on a newly created checkout.

        Called by the store when ``create_empty_checkout`` builds a new
        checkout object. Override this to set default values for your
        domain's checkout extension fields.
        """
