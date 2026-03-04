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

from .payment_processor import MockPaymentProcessor
from .store import ServiceStore

store = ServiceStore()
mpp = MockPaymentProcessor()
