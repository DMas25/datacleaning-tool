from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware import TimeoutMiddleware
from api.routers import clean, webhooks
from api.routers import s3_presign
from api.routers import s3_webhook
from api.watchdog import background_watchdog, health_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_REQUIRED_ENV = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "LEMONSQUEEZY_WEBHOOK_SECRET",
    "LEMONSQUEEZY_API_VARIANT_ID",
    "RESEND_API_KEY",
]


def _startup_validate() -> None:
    """Fail fast before accepting traffic if critical env vars are absent."""
    missing = [v for v in _REQUIRED_ENV if not os.environ.get(v)]
    if missing:
        msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.critical("Startup validation FAILED - %s", msg)
        raise RuntimeError(msg)
    logger.info("Startup validation passed.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _startup_validate()
    task = asyncio.create_task(background_watchdog())
    logger.info("Watchdog background task registered.")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Watchdog background task stopped.")


app = FastAPI(
    title="ColtraDataAi Enterprise API",
    description=(
        "Programmatic access to ColtraDataAi's domain-specific data cleaners. "
        "Authenticate with `Authorization: Bearer <your_api_key>`."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Timeout middleware must be added before CORS so stuck requests are cut off
# regardless of origin, and before the router so all /v1/ endpoints are covered.
app.add_middleware(TimeoutMiddleware, timeout=30)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(clean.router, prefix="/v1", tags=["Cleaning"])
app.include_router(webhooks.router, tags=["Webhooks"])
app.include_router(s3_webhook.router, tags=["Webhooks"])
app.include_router(s3_presign.router)


@app.get("/health", tags=["System"])
def health() -> dict:
    """Lightweight liveness check - no authentication required. Used by the keep-alive pinger."""
    return {"status": "ok", "service": "ColtraDataAi Enterprise API"}


@app.get("/health/detail", tags=["System"])
def health_detail() -> dict:
    """
    Full dependency readiness check.
    Reports Supabase circuit breaker state, domain cleaner availability,
    and environment variable presence. No authentication required.
    Use this endpoint in monitoring dashboards and alerting rules.
    """
    return health_state()


@app.get("/v1/domains", tags=["System"])
def list_domains() -> dict:
    """List all supported cleaning domains."""
    return {
        "domains": [
            "finance", "logistics", "retail", "trade",
            "healthcare", "consultant", "sme", "hospitality",
        ]
    }
