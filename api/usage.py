from __future__ import annotations

from datetime import datetime, timezone


def log_usage(api_key_id: str, domain: str, rows: int, input_format: str) -> None:
    """Fire-and-forget usage log — never raises so the calling request is unaffected."""
    try:
        from services.supabase_client import get_supabase_client
        client = get_supabase_client()
        client.table("api_usage_log").insert({
            "api_key_id": api_key_id,
            "domain": domain,
            "rows_processed": rows,
            "input_format": input_format,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass
