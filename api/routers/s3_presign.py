from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import verify_api_key
from api.s3_client import generate_presigned_download_url, generate_presigned_upload_url

router = APIRouter(prefix="/v1/s3", tags=["S3 Automation"])

VALID_DOMAINS = {
    "finance", "logistics", "retail", "trade",
    "healthcare", "consultant", "sme", "hospitality",
}


class PresignUploadRequest(BaseModel):
    domain: str
    filename: str


@router.post("/presign-upload")
async def presign_upload(
    body: PresignUploadRequest,
    api_key_record: dict = Depends(verify_api_key),
):
    if body.domain not in VALID_DOMAINS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid domain '{body.domain}'. Valid domains: {', '.join(sorted(VALID_DOMAINS))}.",
        )

    api_key_id = api_key_record["id"]
    key = f"uploads/{body.domain}/{api_key_id}/{uuid4()}/{body.filename}"
    upload_url = generate_presigned_upload_url(key)

    return {"upload_url": upload_url, "s3_key": key, "expires_in": 3600}


@router.get("/download")
async def presign_download(
    s3_key: str,
    api_key_record: dict = Depends(verify_api_key),
):
    if not s3_key.startswith("cleaned/"):
        raise HTTPException(
            status_code=403,
            detail="Access denied. Only keys under 'cleaned/' may be downloaded.",
        )

    download_url = generate_presigned_download_url(s3_key)

    return {"download_url": download_url, "expires_in": 3600}
