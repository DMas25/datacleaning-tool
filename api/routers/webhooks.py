from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os

import resend
from fastapi import APIRouter, HTTPException, Request
from supabase import create_client

from api.auth import generate_api_key

router = APIRouter()
logger = logging.getLogger(__name__)


def _verify_signature(raw_body: bytes, signature: str) -> bool:
    secret = os.environ.get("LEMONSQUEEZY_WEBHOOK_SECRET", "")
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _supabase_client():
    url = os.environ["SUPABASE_URL"].strip()
    svc_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip()
    return create_client(url, svc_key)


def _insert_api_key(email: str, label: str, key_hash: str) -> None:
    _supabase_client().table("api_keys").insert({
        "key_hash": key_hash,
        "email": email,
        "label": label,
        "is_active": True,
    }).execute()


def _deactivate_api_key(email: str) -> None:
    _supabase_client().table("api_keys").update({
        "is_active": False,
    }).eq("email", email).execute()


def _send_key_email(to_email: str, name: str, raw_key: str) -> None:
    resend.api_key = os.environ["RESEND_API_KEY"]
    resend.Emails.send({
        "from": "ColtraDataAi <noreply@coltradata.com>",
        "to": [to_email],
        "subject": "Your ColtraDataAi Enterprise API Key",
        "html": f"""
<p>Hi {name},</p>
<p>Thank you for subscribing to the ColtraDataAi Enterprise API.</p>
<p>Your API key is:</p>
<pre style="background:#f4f4f4;padding:12px;border-radius:4px;font-size:14px;font-family:monospace;">{raw_key}</pre>
<p>Include it in every request as a Bearer token:</p>
<pre style="background:#f4f4f4;padding:12px;border-radius:4px;font-size:14px;font-family:monospace;">Authorization: Bearer {raw_key}</pre>
<p>Full API documentation: <a href="https://coltradata-api.onrender.com/docs">coltradata-api.onrender.com/docs</a></p>
<p>Keep this key secure. If you need to rotate it, contact support@coltradata.com.</p>
<p>The ColtraDataAi Team</p>
""",
    })


@router.post("/webhooks/lemonsqueezy", tags=["Webhooks"])
async def lemonsqueezy_webhook(request: Request) -> dict:
    """
    Receives LemonSqueezy order/subscription events.
    On a matching Enterprise API purchase: generates an API key,
    stores the hash in Supabase, and emails the raw key to the customer.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Signature", "")

    if not _verify_signature(raw_body, signature):
        logger.warning("Webhook rejected: invalid signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    payload = json.loads(raw_body)
    event = payload.get("meta", {}).get("event_name", "")

    if event not in ("order_created", "subscription_created", "subscription_cancelled"):
        return {"status": "ignored", "event": event}

    target_variant_id = str(os.environ.get("LEMONSQUEEZY_API_VARIANT_ID", ""))
    data_attrs = payload.get("data", {}).get("attributes", {})

    if event == "order_created":
        variant_id = str(data_attrs.get("first_order_item", {}).get("variant_id", ""))
    else:
        variant_id = str(data_attrs.get("variant_id", ""))

    if variant_id != target_variant_id:
        return {"status": "ignored", "reason": "variant_id mismatch"}

    email = data_attrs.get("user_email", "")
    name = data_attrs.get("user_name", "Customer")

    if not email:
        logger.error("Webhook %s received with no user_email", event)
        raise HTTPException(status_code=422, detail="No user email in payload.")

    if event == "subscription_cancelled":
        try:
            _deactivate_api_key(email)
        except Exception as exc:
            logger.error("Failed to deactivate API key for %s: %s", email, exc)
            raise HTTPException(status_code=500, detail="Failed to deactivate API key.") from exc
        logger.info("API key deactivated for %s", email)
        return {"status": "ok", "action": "key_deactivated"}

    raw_key, key_hash = generate_api_key()
    label = f"Enterprise API - {name}"

    try:
        _insert_api_key(email, label, key_hash)
    except Exception as exc:
        logger.error("Failed to insert API key for %s: %s", email, exc)
        raise HTTPException(status_code=500, detail="Failed to provision API key.") from exc

    try:
        _send_key_email(email, name, raw_key)
    except Exception as exc:
        # Key is in Supabase — return 200 so LemonSqueezy does not retry and create duplicates.
        # Resend failure can be resolved by manually forwarding the key.
        logger.error("API key created but email failed for %s: %s", email, exc)
        return {"status": "partial", "note": "key_provisioned_email_failed", "email": email}

    logger.info("API key provisioned for %s via %s", email, event)
    return {"status": "ok"}
