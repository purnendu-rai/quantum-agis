"""QUANTUM-AGIS FastAPI application entry point.

Creates the ASGI app, wires CORS, mounts all API routers and the WebSocket
endpoint. Run locally with:

    uvicorn app.main:app --reload --port 8000

or serve the whole stack with the root ``docker-compose.yml``.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import websocket
from app.api.routes import attacks, dashboard, health, logs, verification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")


@contextlib.asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup/shutdown hooks: init simulation service and background tasks."""
    from app.services.simulation_service import simulation_service

    # Start the background signature-generation loop
    task = asyncio.create_task(simulation_service.start_background_loop())
    logger.info("QUANTUM-AGIS started [env=%s]", settings.ENVIRONMENT)
    yield
    # Graceful shutdown
    simulation_service.stop()
    task.cancel()
    from app.api.websocket import shutdown as shutdown_broadcaster

    shutdown_broadcaster()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    logger.info("QUANTUM-AGIS shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=(
        "Quantum-inspired Agentic Governance & Intrusion Shield — "
        "layered quantum-secured verification and threat detection API."
    ),
    debug=settings.DEBUG,
    docs_url="/docs" if (settings.DEBUG and not settings.is_production) else None,
    redoc_url="/redoc" if (settings.DEBUG and not settings.is_production) else None,
    openapi_url="/openapi.json" if (settings.DEBUG and not settings.is_production) else None,
    lifespan=_lifespan,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add defensive HTTP security headers to all API responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers with the prefixes the spec requires
app.include_router(health.router, prefix="/api")
app.include_router(verification.router, prefix="/api")
app.include_router(attacks.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(websocket.router)
