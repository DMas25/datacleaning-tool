from __future__ import annotations

import io
import logging
import os
import traceback
import urllib.parse

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger(__name__)

VALID_DOMAINS = {
    "finance", "logistics", "retail", "trade",
    "healthcare", "consultant", "sme", "hospitality",
}


@router.post("/webhooks/s3", tags=["Webhooks"])
async def s3_webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    secret = os.environ.get("SUPABASE_STORAGE_WEBHOOK_SECRET")
    if secret:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {secret}":
            return JSONResponse({"status": "unauthorized"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        logger.warning("s3_webhook: failed to parse request body")
        return JSONResponse({"status": "ok"}, status_code=200)

    if body.get("type") != "INSERT" or body.get("schema") != "storage":
        return JSONResponse({"status": "ok"}, status_code=200)

    key = body.get("record", {}).get("name", "")
    if key:
        background_tasks.add_task(_process_record, key)

    return JSONResponse({"status": "ok"}, status_code=200)


def _process_record(raw_key: str) -> None:
    from api.s3_client import download_object_as_bytes, upload_bytes

    key = urllib.parse.unquote_plus(raw_key)

    try:
        if not key.startswith("uploads/"):
            return

        parts = key.split("/")
        if len(parts) < 3:
            return
        domain = parts[1]

        if domain not in VALID_DOMAINS:
            return

        bytes_data = download_object_as_bytes(key)
        df = pd.read_csv(io.BytesIO(bytes_data))

        result = _run_cleaner(domain, df)

        cleaned_bytes = result.cleaned_df.to_csv(index=False).encode("utf-8")
        output_key = "cleaned/" + key[len("uploads/"):]
        upload_bytes(output_key, cleaned_bytes)
        logger.info("Cleaned %s -> %s", key, output_key)

    except Exception:
        tb = traceback.format_exc()
        error_key = f"errors/{key}.error.txt"
        try:
            from api.s3_client import upload_bytes
            upload_bytes(error_key, tb.encode("utf-8"))
        except Exception as upload_exc:
            logger.error("Failed to upload error file for %s: %s", key, upload_exc)
        logger.error("Error processing %s:\n%s", key, tb)


def _run_cleaner(domain: str, df: pd.DataFrame):
    if domain == "finance":
        from core.finance_cleaner import apply_finance_cleaning
        return apply_finance_cleaning(df)
    if domain == "logistics":
        from core.logistics_cleaner import apply_logistics_cleaning
        return apply_logistics_cleaning(df)
    if domain == "retail":
        from core.retail_cleaner import apply_retail_cleaning
        return apply_retail_cleaning(df)
    if domain == "trade":
        from core.trade_cleaner import apply_trade_cleaning
        return apply_trade_cleaning(df)
    if domain == "healthcare":
        from core.healthcare_cleaner import apply_healthcare_cleaning
        return apply_healthcare_cleaning(df)
    if domain == "consultant":
        from core.consultant_cleaner import apply_consultant_cleaning
        return apply_consultant_cleaning(df)
    if domain == "sme":
        from core.sme_cleaner import apply_sme_cleaning
        return apply_sme_cleaning(df)
    if domain == "hospitality":
        from core.hospitality_cleaner import apply_hospitality_cleaning
        return apply_hospitality_cleaning(df)
    raise ValueError(f"Unknown domain: {domain}")
