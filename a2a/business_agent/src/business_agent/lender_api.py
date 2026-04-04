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

"""Mock lender API endpoints.

Simulates real lender APIs that receive PII (or VGS-enriched data)
and return loan offers. In production these would be external services;
here they're co-located for demo purposes.

With VGS outbound routes, the backend sends VGS aliases to these endpoints
through the VGS forward proxy. VGS enriches (detokenizes) the aliases
in transit, so these endpoints receive real PII values — the backend
never sees the raw data.
"""

from __future__ import annotations

import logging
import random
import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .models.lending_types import LoanOffer, LoanType

logger = logging.getLogger(__name__)


def _generate_mock_offers(
    lender_id: str,
    loan_amount: float,
    loan_type: str,
    lender_name: str | None = None,
) -> list[LoanOffer]:
    """Generate 1-3 random loan offers for a lender."""
    offers: list[LoanOffer] = []
    num_offers = random.randint(1, 3)

    for _ in range(num_offers):
        rate = round(random.uniform(5.99, 15.99), 2)
        term_months = random.choice([24, 36, 48, 60, 72])
        monthly_rate = rate / 100 / 12
        monthly_payment = round(
            loan_amount
            * (monthly_rate * (1 + monthly_rate) ** term_months)
            / ((1 + monthly_rate) ** term_months - 1),
            2,
        )

        offers.append(
            LoanOffer(
                lender_name=lender_name or lender_id,
                rate=rate,
                amount=loan_amount,
                term_months=term_months,
                monthly_payment=monthly_payment,
                continue_url=f"https://{lender_id}.example.com/apply/{uuid.uuid4()}",
            )
        )

    return offers


def create_lender_api_routes() -> list[Route]:
    """Create Starlette routes for mock lender API endpoints."""

    async def lender_apply_handler(request: Request) -> JSONResponse:
        """Mock lender API — receives PII + loan details, returns offers.

        In VGS mode, the PII fields arrive as real values (enriched by
        the outbound route). In mock mode, they arrive as raw values
        from the MockPIIProvider.
        """
        lender_id = request.path_params["lender_id"]
        body = await request.json()

        logger.info(
            "Lender API: POST /lender-api/%s/apply — received fields=%s",
            lender_id,
            sorted(body.keys()),
        )

        loan_type = body.get("loan_type", LoanType.PERSONAL)
        loan_amount = float(body.get("loan_amount_requested", 10000))
        if loan_type == LoanType.CAR:
            loan_amount = float(body.get("car_value", 25000))

        offers = _generate_mock_offers(
            lender_id, loan_amount, loan_type, body.get("lender_name")
        )

        return JSONResponse(
            {"offers": [offer.model_dump(mode="json") for offer in offers]}
        )

    return [
        Route(
            "/lender-api/{lender_id}/apply",
            lender_apply_handler,
            methods=["POST"],
        ),
    ]
