from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CleanResponse(BaseModel):
    domain: str
    rows_processed: int
    cleaned_data: list[dict[str, Any]]
    metrics: dict[str, Any]
    issues: list[dict[str, Any]]


class ApiKeyInfo(BaseModel):
    id: str
    label: str
    email: str
    created_at: str
    last_used_at: str | None
