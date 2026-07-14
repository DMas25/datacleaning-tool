"""
LemonSqueezy webhook receiver — FastAPI.

Run alongside the Streamlit app (separate process):

    uvicorn services.webhook_server:app --host 0.0.0.0 --port 8001

Then expose port 8001 publicly (ngrok, Render, Railway, etc.) and set your
LemonSqueezy webhook URL to:

    https://<your-domain>/lemonsqueezy/webhook

Required secret in .streamlit/secrets.toml:

    [lemonsqueezy]
    webhook_secret = "your-signing-secret-from-ls-dashboard"

Or set the environment variable LEMONSQUEEZY_WEBHOOK_SECRET.

Events handled:
  - order_created
  - subscription_created
  - subscription_updated
  - subscription_cancelled

On each successful payment event the handler:
  1. Extracts customer email + plan from the payload
  2. Generates a licence key (or reuses the existing one for the email)
  3. Writes to the local SQLite database
  4. The Streamlit app reads from the same DB when the user enters their key
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from services.licence_manager_pg import (
    cancel_subscription,
    log_webhook_event,
    upsert_subscription,
)
from services.lifecycle_emails import render_licence_key_email
from services.transactional_email import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger("coltradata.webhook")

app = FastAPI(title="ColtraDataAI Webhook Server", docs_url=None, redoc_url=None)

# ── Resend config ─────────────────────────────────────────────────────────────
def _resend_cfg() -> dict:
    """Read Resend config from env var or secrets.toml."""
    api_key = os.environ.get("RESEND_API_KEY", "")
    app_url = os.environ.get("APP_URL", "")
    if not api_key:
        try:
            import tomllib
            p = Path(".streamlit/secrets.toml")
            if p.exists():
                data = tomllib.loads(p.read_text())
                te = data.get("transactional_email", {})
                api_key = te.get("resend_api_key", "")
                app_url = app_url or te.get("app_url", "")
        except Exception:
            pass
    return {
        "resend_api_key": api_key,
        "from_name": "ColtraDataAi",
        "from_email": "support@coltradata.com",
        "app_url": app_url,
    }


# ── Plan map ──────────────────────────────────────────────────────────────────
# Maps LemonSqueezy product/variant names → internal plan keys.
# Edit to match your exact LemonSqueezy product and variant names.
PLAN_MAP: dict[str, str] = {
    "Starter":      "starter",
    "starter":      "starter",
    "Professional": "professional",
    "Pro":          "professional",
    "professional": "professional",
    "Premium":      "premium",
    "premium":      "premium",
    "Enterprise":   "enterprise",
    "enterprise":   "enterprise",
}


# ── Signature verification ────────────────────────────────────────────────────
def _webhook_secret() -> str:
    """Read webhook secret from env or secrets.toml."""
    secret = os.environ.get("LEMONSQUEEZY_WEBHOOK_SECRET", "")
    if secret:
        return secret
    try:
        import tomllib
        p = Path(".streamlit/secrets.toml")
        if p.exists():
            data = tomllib.loads(p.read_text())
            return data.get("lemonsqueezy", {}).get("webhook_secret", "")
    except Exception:
        pass
    return ""


def verify_signature(raw_body: bytes, signature_header: str) -> None:
    """Raise HTTP 401 if the HMAC-SHA256 signature does not match.

    LemonSqueezy sends the digest as a plain hex string in X-Signature.
    """
    secret = _webhook_secret()
    if not secret:
        log.warning("webhook_secret not configured — signature verification skipped")
        return

    expected = hmac.new(
        secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()

    provided = (signature_header or "").strip()
    if not hmac.compare_digest(expected, provided):
        log.warning("Webhook signature mismatch — request rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )


# ── Payload extraction ────────────────────────────────────────────────────────
def _extract(payload: dict) -> dict:
    """Pull the fields we need from a LemonSqueezy webhook payload."""
    data  = payload.get("data", {})
    attrs = data.get("attributes", {})
    meta  = payload.get("meta", {})

    # Email — present on order and subscription objects
    email = (
        attrs.get("user_email")
        or attrs.get("customer_email")
        or meta.get("custom_data", {}).get("email")
        or ""
    )

    subscription_id = str(data.get("id", ""))
    order_id        = str(attrs.get("order_id") or "")

    # Product / variant name — carried in first_order_item on orders
    first_item   = attrs.get("first_order_item") or {}
    product_name = (
        first_item.get("product_name")
        or attrs.get("product_name")
        or meta.get("product_name")
        or ""
    )
    variant_name = (
        first_item.get("variant_name")
        or attrs.get("variant_name")
        or meta.get("variant_name")
        or ""
    )

    plan_key = PLAN_MAP.get(variant_name) or PLAN_MAP.get(product_name) or "free"

    return {
        "email":           email.lower().strip(),
        "plan":            plan_key,
        "subscription_id": subscription_id,
        "order_id":        order_id,
        "product_name":    product_name,
        "variant_name":    variant_name,
        "ls_status":       attrs.get("status", "active"),
    }


# ── Event handlers ────────────────────────────────────────────────────────────
def _handle_order_created(payload: dict) -> str:
    f = _extract(payload)
    if not f["email"]:
        return "skipped — no email in payload"
    key = upsert_subscription(
        email=f["email"],
        plan=f["plan"],
        order_id=f["order_id"],
        status="active",
    )
    log.info("order_created  email=%s  plan=%s  key=%s", f["email"], f["plan"], key)
    cfg = _resend_cfg()
    subject, body = render_licence_key_email(key=key, plan=f["plan"], app_url=cfg["app_url"])
    sent = send_email(cfg, f["email"], subject, body)
    log.info("licence key email sent=%s to %s", sent, f["email"])
    return f"activated {f['plan']} for {f['email']} (key={key}, email_sent={sent})"


def _handle_subscription_created(payload: dict) -> str:
    f = _extract(payload)
    if not f["email"]:
        return "skipped — no email in payload"
    key = upsert_subscription(
        email=f["email"],
        plan=f["plan"],
        subscription_id=f["subscription_id"],
        order_id=f["order_id"],
        status="active",
    )
    log.info(
        "subscription_created  email=%s  plan=%s  sub_id=%s  key=%s",
        f["email"], f["plan"], f["subscription_id"], key,
    )
    cfg = _resend_cfg()
    subject, body = render_licence_key_email(key=key, plan=f["plan"], app_url=cfg["app_url"])
    sent = send_email(cfg, f["email"], subject, body)
    log.info("licence key email sent=%s to %s", sent, f["email"])
    return f"subscription created {f['plan']} for {f['email']} (email_sent={sent})"


def _handle_subscription_updated(payload: dict) -> str:
    f = _extract(payload)
    if not f["email"]:
        return "skipped — no email in payload"

    ls_status = f["ls_status"]
    internal  = "active" if ls_status in ("active", "on_trial") else "inactive"

    key = upsert_subscription(
        email=f["email"],
        plan=f["plan"] if internal == "active" else "free",
        subscription_id=f["subscription_id"],
        order_id=f["order_id"],
        status=internal,
    )
    log.info(
        "subscription_updated  email=%s  plan=%s  ls_status=%s  internal=%s",
        f["email"], f["plan"], ls_status, internal,
    )
    return f"updated to {f['plan']} ({internal}) for {f['email']}"


def _handle_subscription_cancelled(payload: dict) -> str:
    sub_id = str(payload.get("data", {}).get("id", ""))
    found  = cancel_subscription(sub_id)
    log.info("subscription_cancelled  sub_id=%s  found=%s", sub_id, found)
    return f"cancelled sub_id={sub_id} found={found}"


_HANDLERS: dict[str, Any] = {
    "order_created":          _handle_order_created,
    "subscription_created":   _handle_subscription_created,
    "subscription_updated":   _handle_subscription_updated,
    "subscription_cancelled": _handle_subscription_cancelled,
}


# ── Webhook endpoint ──────────────────────────────────────────────────────────
@app.post("/lemonsqueezy/webhook")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: str = Header(default="", alias="X-Signature"),
) -> JSONResponse:
    raw = await request.body()
    verify_signature(raw, x_signature)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = payload.get("meta", {}).get("event_name", "unknown")
    log_webhook_event(event_type, raw.decode("utf-8", errors="replace"))

    handler = _HANDLERS.get(event_type)
    if handler is None:
        log.info("Unhandled event: %s", event_type)
        return JSONResponse({"status": "ignored", "event": event_type})

    try:
        detail = handler(payload)
    except Exception as exc:
        log.exception("Error in handler for %s: %s", event_type, exc)
        raise HTTPException(status_code=500, detail="Internal processing error")

    return JSONResponse({"status": "ok", "event": event_type, "detail": detail})


@app.get("/health")
def health() -> dict:
    """
    Real HTTP health check (Streamlit itself can't expose arbitrary
    routes, so this lives on the webhook server's FastAPI app instead).
    Merges in core.health_check's fault-log-derived status so the same
    "ok / degraded / safe_mode" signal app.py's safe mode gate uses is
    visible to external uptime monitors too.
    """
    from core.health_check import get_health_status

    app_health = get_health_status()
    return {"service": "ColtraDataAI webhook", **app_health}


# ── Sample payload (for testing) ──────────────────────────────────────────────
SAMPLE_ORDER_PAYLOAD = {
    "meta": {
        "event_name": "order_created",
        "custom_data": {}
    },
    "data": {
        "id": "sub_123456",
        "attributes": {
            "user_email": "customer@example.com",
            "order_id": "ord_789",
            "status": "active",
            "first_order_item": {
                "product_name": "ColtraDataAI",
                "variant_name": "Professional"
            }
        }
    }
}


# ── Local dev entry-point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("services.webhook_server:app", host="0.0.0.0", port=port, reload=False)
