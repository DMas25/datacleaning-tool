from __future__ import annotations

import sys
import os

# Ensure project root is on the path so `core.*` and `services.*` resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import clean

app = FastAPI(
    title="ColtraDataAi Enterprise API",
    description=(
        "Programmatic access to ColtraDataAi's domain-specific data cleaners. "
        "Authenticate with `Authorization: Bearer <your_api_key>`."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(clean.router, prefix="/v1", tags=["Cleaning"])


@app.get("/health", tags=["System"])
def health() -> dict:
    return {"status": "ok", "service": "ColtraDataAi Enterprise API"}


@app.get("/v1/domains", tags=["System"])
def list_domains() -> dict:
    """List all supported cleaning domains."""
    return {
        "domains": [
            "finance", "logistics", "retail", "trade",
            "healthcare", "consultant", "sme", "hospitality",
        ]
    }
