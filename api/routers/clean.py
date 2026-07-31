from __future__ import annotations

import importlib
import io
import json
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import verify_api_key
from api.models import CleanResponse
from api.usage import log_usage

router = APIRouter()

_DOMAINS: dict[str, tuple[str, str]] = {
    "finance":     ("core.finance_cleaner",     "apply_finance_cleaning"),
    "logistics":   ("core.logistics_cleaner",   "apply_logistics_cleaning"),
    "retail":      ("core.retail_cleaner",      "apply_retail_cleaning"),
    "trade":       ("core.trade_cleaner",       "apply_trade_cleaning"),
    "healthcare":  ("core.healthcare_cleaner",  "apply_healthcare_cleaning"),
    "consultant":  ("core.consultant_cleaner",  "apply_consultant_cleaning"),
    "sme":         ("core.sme_cleaner",         "apply_sme_cleaning"),
    "hospitality": ("core.hospitality_cleaner", "apply_hospitality_cleaning"),
}


async def _parse_request(request: Request) -> tuple[pd.DataFrame, str]:
    """Return (DataFrame, input_format) from either CSV multipart or JSON body."""
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            raise HTTPException(status_code=422, detail="Multipart request must include a 'file' field.")
        content = await upload.read()
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not parse CSV: {exc}")
        return df, "csv"

    body = await request.body()
    if not body:
        raise HTTPException(status_code=422, detail="Request body is empty.")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}")

    rows = payload if isinstance(payload, list) else payload.get("rows")
    if not isinstance(rows, list):
        raise HTTPException(
            status_code=422,
            detail="JSON body must be a list of records or {\"rows\": [...]}.",
        )
    return pd.DataFrame(rows), "json"


@router.post("/clean/{domain}", response_model=CleanResponse, summary="Clean a dataset")
async def clean_domain(
    domain: str,
    request: Request,
    api_key_record: dict = Depends(verify_api_key),
) -> CleanResponse:
    """
    Clean a dataset for the given **domain**.

    Supported domains: `finance`, `logistics`, `retail`, `trade`,
    `healthcare`, `consultant`, `sme`, `hospitality`.

    **CSV upload** — send `multipart/form-data` with a `file` field.

    **JSON** — send `application/json` as either a list of records
    `[{...}, ...]` or `{"rows": [{...}, ...]}`.
    """
    if domain not in _DOMAINS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown domain '{domain}'. Valid: {', '.join(_DOMAINS)}.",
        )

    df, input_format = await _parse_request(request)

    if df.empty:
        raise HTTPException(status_code=422, detail="Uploaded data contains no rows.")

    module_path, func_name = _DOMAINS[domain]
    module = importlib.import_module(module_path)
    clean_fn = getattr(module, func_name)

    try:
        result = clean_fn(df)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cleaning failed: {exc}")

    rows_processed = len(result.cleaned_df)
    log_usage(api_key_record["id"], domain, rows_processed, input_format)

    cleaned_data: list[dict[str, Any]] = (
        result.cleaned_df.where(result.cleaned_df.notna(), None).to_dict(orient="records")
    )

    return CleanResponse(
        domain=domain,
        rows_processed=rows_processed,
        cleaned_data=cleaned_data,
        metrics=result.metrics,
        issues=result.issues,
    )
