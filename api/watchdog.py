from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

_BOOT_TIME: datetime = datetime.now(timezone.utc)
_CHECK_INTERVAL = 300       # seconds between Supabase health checks
_ALERT_COOLDOWN = 3600      # seconds before a repeat alert is sent
_FAILURE_THRESHOLD = 3      # consecutive failures before circuit opens
_RECOVERY_TIMEOUT = 120     # seconds before circuit moves to half-open

_DOMAIN_CLEANERS = [
    "finance", "logistics", "retail", "trade",
    "healthcare", "consultant", "sme", "hospitality",
]
_REQUIRED_ENV = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
_OPTIONAL_ENV = ["RESEND_API_KEY", "ANTHROPIC_API_KEY"]


class CircuitState(Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing fast - Supabase unreachable
    HALF_OPEN = "half_open"  # Testing recovery after timeout


@dataclass
class _CircuitBreaker:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    consecutive_successes: int = 0
    last_failure: datetime | None = None
    last_check: datetime | None = None
    last_alert: datetime | None = None

    def record_success(self) -> None:
        self.consecutive_successes += 1
        if self.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            if self.consecutive_successes >= 2:
                prev = self.state
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Watchdog: Supabase circuit CLOSED (recovered from %s).", prev.value)
        else:
            self.failure_count = 0

    def record_failure(self) -> None:
        self.consecutive_successes = 0
        self.failure_count += 1
        self.last_failure = datetime.now(timezone.utc)
        if self.failure_count >= _FAILURE_THRESHOLD and self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            logger.warning(
                "Watchdog: Supabase circuit OPEN after %d consecutive failures.",
                self.failure_count,
            )

    def can_attempt(self) -> bool:
        """Returns True if a Supabase call should be attempted."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN and self.last_failure:
            elapsed = (datetime.now(timezone.utc) - self.last_failure).total_seconds()
            if elapsed >= _RECOVERY_TIMEOUT:
                self.state = CircuitState.HALF_OPEN
                self.consecutive_successes = 0
                logger.info("Watchdog: Supabase circuit HALF_OPEN - allowing recovery probe.")
                return True
            return False
        return True  # HALF_OPEN: allow one probe through


# Shared singleton - imported by auth.py to check before Supabase calls
supabase_breaker = _CircuitBreaker()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ping_supabase() -> bool:
    """Lightweight Supabase table probe - runs in a thread executor."""
    try:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
        if not url or not key:
            return False
        req = urllib.request.Request(
            f"{url}/rest/v1/api_keys?select=id&limit=1",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as exc:
        logger.debug("Watchdog: Supabase ping failed: %s", exc)
        return False


def _send_alert(subject: str, body: str) -> None:
    """Send alert email via Resend - never raises so the watchdog loop is unaffected."""
    try:
        resend_key = os.environ.get("RESEND_API_KEY", "").strip()
        admin_email = os.environ.get("ADMIN_EMAIL", "support@coltradata.com").strip()
        if not resend_key:
            logger.warning("Watchdog: RESEND_API_KEY not set - alert email suppressed.")
            return
        payload = json.dumps({
            "from": "ColtraDataAi Watchdog <watchdog@coltradata.com>",
            "to": [admin_email],
            "subject": subject,
            "text": body,
        }).encode()
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {resend_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Watchdog: alert email sent (HTTP %d).", resp.status)
    except Exception as exc:
        logger.warning("Watchdog: could not send alert email: %s", exc)


# ---------------------------------------------------------------------------
# Background watchdog loop
# ---------------------------------------------------------------------------

async def _run_check(loop: asyncio.AbstractEventLoop) -> None:
    """One Supabase health check cycle."""
    supabase_breaker.last_check = datetime.now(timezone.utc)
    ok = await loop.run_in_executor(None, _ping_supabase)

    if ok:
        was_degraded = supabase_breaker.state != CircuitState.CLOSED
        supabase_breaker.record_success()
        if was_degraded:
            logger.info("Watchdog: Supabase connectivity restored.")
    else:
        supabase_breaker.record_failure()
        logger.warning(
            "Watchdog: Supabase check FAILED (failures: %d, circuit: %s).",
            supabase_breaker.failure_count,
            supabase_breaker.state.value,
        )

        if supabase_breaker.state == CircuitState.OPEN:
            now = datetime.now(timezone.utc)
            since_last_alert = (
                (now - supabase_breaker.last_alert).total_seconds()
                if supabase_breaker.last_alert else _ALERT_COOLDOWN + 1
            )
            if since_last_alert >= _ALERT_COOLDOWN:
                supabase_breaker.last_alert = now
                loop.run_in_executor(None, _send_alert,
                    "ColtraDataAi API Alert - Supabase connectivity fault",
                    (
                        "The ColtraDataAi API watchdog has detected a sustained Supabase connectivity fault.\n\n"
                        f"Consecutive failures: {supabase_breaker.failure_count}\n"
                        f"Circuit state: {supabase_breaker.state.value}\n"
                        f"First failure: {supabase_breaker.last_failure.isoformat() if supabase_breaker.last_failure else 'unknown'}\n\n"
                        "All incoming API authentication requests are currently returning 503. "
                        "This fault is NOT caused by a subscription or payment lapse.\n\n"
                        "Recommended checks:\n"
                        "  1. Supabase status: https://status.supabase.com\n"
                        "  2. Render env vars: confirm SUPABASE_URL and SUPABASE_ANON_KEY are set in the Render dashboard\n"
                        "  3. Supabase project: confirm the project is not paused (free-tier projects pause after inactivity)\n\n"
                        f"The watchdog will retry automatically every {_RECOVERY_TIMEOUT}s and "
                        f"will send a follow-up alert in {_ALERT_COOLDOWN // 3600}h if the fault persists."
                    ),
                )


async def background_watchdog() -> None:
    """
    Async background task - registered in FastAPI lifespan (api/main.py).
    Monitors Supabase connectivity, manages the circuit breaker state,
    and sends alert emails via Resend on sustained faults.
    """
    logger.info("Watchdog: started. Check interval: %ds, failure threshold: %d.", _CHECK_INTERVAL, _FAILURE_THRESHOLD)
    loop = asyncio.get_running_loop()
    # Delay first check so the app fully initialises before probing
    await asyncio.sleep(30)
    while True:
        try:
            await _run_check(loop)
        except asyncio.CancelledError:
            logger.info("Watchdog: background task cancelled cleanly.")
            raise
        except Exception as exc:
            logger.error("Watchdog: unexpected error in check loop: %s", exc)
        await asyncio.sleep(_CHECK_INTERVAL)


# ---------------------------------------------------------------------------
# Health state - consumed by /health/detail endpoint
# ---------------------------------------------------------------------------

def health_state() -> dict:
    """
    Returns a full dependency snapshot for the /health/detail endpoint.
    Checks Supabase circuit state, cleaner importability, and env var presence.
    """
    uptime = int((datetime.now(timezone.utc) - _BOOT_TIME).total_seconds())

    cleaner_status: dict[str, str] = {}
    for domain in _DOMAIN_CLEANERS:
        try:
            importlib.import_module(f"core.{domain}_cleaner")
            cleaner_status[domain] = "ok"
        except Exception:
            cleaner_status[domain] = "failed"

    breaker = supabase_breaker
    supabase_status = (
        "ok" if breaker.state == CircuitState.CLOSED
        else "degraded" if breaker.state == CircuitState.HALF_OPEN
        else "down"
    )

    all_env = _REQUIRED_ENV + _OPTIONAL_ENV
    env_status = {
        var: ("present" if os.environ.get(var) else "missing")
        for var in all_env
    }
    required_env_ok = all(env_status[v] == "present" for v in _REQUIRED_ENV)
    cleaners_ok = all(v == "ok" for v in cleaner_status.values())

    if supabase_status == "down" or not required_env_ok:
        overall = "critical"
    elif supabase_status == "degraded" or not cleaners_ok:
        overall = "degraded"
    else:
        overall = "ok"

    return {
        "status": overall,
        "uptime_seconds": uptime,
        "checks": {
            "supabase": supabase_status,
            "circuit_breaker": breaker.state.value,
            "cleaners": cleaner_status,
            "env": env_status,
        },
        "last_supabase_check": breaker.last_check.isoformat() if breaker.last_check else None,
        "last_failure": breaker.last_failure.isoformat() if breaker.last_failure else None,
        "failure_count": breaker.failure_count,
    }
