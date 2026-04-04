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

"""UCP."""

import asyncio
import functools
import json
import logging
import os

from pathlib import Path
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
import click
from dotenv import load_dotenv

# load_dotenv() MUST run before importing agent/store modules, because
# constants.py reads SQUARE_ACCESS_TOKEN at import time.  If the env
# var isn't set yet the Square client is initialised with an empty token
# and all service-catalog searches silently return [].
load_dotenv()

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
import uvicorn

from .agent import root_agent as business_agent
from .agent_executor import ADKAgentExecutor
from .dependencies import create_lending_dependencies
from .lender_api import create_lender_api_routes
from .lending_tools import init_lending
from .pii_provider import create_pii_vault_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def make_sync(func):
    """Wrap an async function to run synchronously.

    Args:
        func: The async function to wrap.





    Returns:
        The wrapped synchronous function.


    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def _create_lending_routes(registry) -> list:
    """Create routes for lending handler discovery endpoints."""
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def lenders_handler(request: Request) -> JSONResponse:
        """Return available lenders, optionally filtered by loan_type."""
        loan_type = request.query_params.get("loan_type")
        lenders = registry.get_lenders(loan_type=loan_type)
        return JSONResponse(
            {"lenders": [lender.model_dump(mode="json") for lender in lenders]}
        )

    async def collect_config_handler(request: Request) -> JSONResponse:
        """Return VGS Collect JS config (vault ID + environment)."""
        return JSONResponse(
            {
                "vgs_vault_id": os.getenv("VGS_VAULT_ID", ""),
                "vgs_environment": os.getenv("VGS_ENVIRONMENT", "sandbox"),
            }
        )

    return [
        Route("/lending/lenders", lenders_handler, methods=["GET"]),
        Route("/lending/collect-config", collect_config_handler, methods=["GET"]),
    ]


@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10999)
@make_sync
async def run(host, port):
    """Run the A2A business agent server.

    Args:
        host: The host to bind to.
        port: The port to listen on.

    """
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY must be set")
        exit(1)

    base_path = Path(__file__).parent
    card_path = base_path / "data" / "agent_card.json"
    with card_path.open(encoding="utf-8") as f:
        data = json.load(f)
    agent_card = AgentCard.model_validate(data)

    # Initialize lending dependencies (reads env vars + ucp_metadata now, not at import time)
    pii_provider, loan_registry, lending_mgr = create_lending_dependencies()
    init_lending(pii_provider, loan_registry, lending_mgr)

    task_store = InMemoryTaskStore()

    request_handler = DefaultRequestHandler(
        agent_executor=ADKAgentExecutor(
            agent=business_agent,
            extensions=agent_card.capabilities.extensions or [],
        ),
        task_store=task_store,
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    routes = a2a_app.routes()
    routes.extend(
        [
            Route(
                "/.well-known/ucp",
                lambda _: FileResponse(base_path / "data" / "ucp.json"),
            ),
            Mount(
                "/images",
                app=StaticFiles(directory=str(base_path / "data" / "images")),
                name="images",
            ),
            *create_pii_vault_routes(pii_provider),
            *_create_lending_routes(loan_registry),
            *create_lender_api_routes(),
        ]
    )
    # Allow requests from VGS Collect JS (sandbox and live reverse proxy origins).
    vgs_vault_id = os.getenv("VGS_VAULT_ID", "")
    cors_origins = [
        f"https://{vgs_vault_id}.sandbox.verygoodproxy.com",
        f"https://{vgs_vault_id}.live.verygoodproxy.com",
        "http://localhost:5173",  # Vite dev server
    ]
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
        ),
    ]
    app = Starlette(routes=routes, middleware=middleware)

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    run()
