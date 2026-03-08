"""
HEMS FastAPI application entrypoint.

Startup sequence:
  1. Load config.yaml
  2. Initialise SQLite database (create tables if needed)
  3. Import all integration plugins (triggers @register decorators)
  4. Start APScheduler (first poll runs within 5 seconds)

All API routes are mounted under /api/v1.
WebSocket lives at /ws/live.
"""

from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import config as cfg
from backend import scheduler
from backend.api import routes_config, routes_forecast, routes_history, routes_pricing, routes_status
from backend.api.websocket import router as ws_router
from backend.database import init_db

# ---------------------------------------------------------------------------
# Logging — structured JSON in production, pretty in dev
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HEMS",
    description="Home Energy Management System",
    version="0.1.0",
)

# Allow the frontend dev server (Vite default port 5173) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(routes_status.router, prefix="/api/v1", tags=["status"])
app.include_router(routes_history.router, prefix="/api/v1", tags=["history"])
app.include_router(routes_config.router, prefix="/api/v1", tags=["config"])
app.include_router(routes_pricing.router, prefix="/api/v1", tags=["pricing"])
app.include_router(routes_forecast.router, prefix="/api/v1", tags=["forecast"])
app.include_router(ws_router, tags=["websocket"])


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    """Initialise everything on FastAPI startup."""
    # 1. Load config
    conf = cfg.load()

    # 2. Init database
    init_db()

    # 3. Import all integrations (self-register via @register)
    _import_integrations()

    # 4. Start scheduler
    scheduler.start(conf)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Clean shutdown."""
    scheduler.stop()


def _import_integrations() -> None:
    """Import all integration modules so their @register decorators fire."""
    import backend.integrations.enphase          # noqa: F401
    import backend.integrations.homewizard_p1    # noqa: F401
    import backend.integrations.homewizard_socket  # noqa: F401
    import backend.integrations.shelly           # noqa: F401
    import backend.integrations.alfen_eve        # noqa: F401
    import backend.integrations.weheat           # noqa: F401
