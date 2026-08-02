"""
CLI utility to provision an Enterprise API key.

Usage:
    python scripts/create_api_key.py --email customer@example.com --label "Acme Corp"

The script prints the raw API key ONCE — save it immediately.
Only the SHA-256 hash is stored in Supabase.

Requires SUPABASE_URL and SUPABASE_ANON_KEY as environment variables,
or a .streamlit/secrets.toml file with [supabase] url / anon_key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sys


def _get_supabase_creds() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        try:
            import tomllib
            secrets_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                ".streamlit", "secrets.toml"
            )
            with open(secrets_path, "rb") as f:
                data = tomllib.load(f)
            sb = data.get("supabase", {})
            url = url or sb.get("url", "")
            key = key or sb.get("anon_key", "")
        except Exception:
            pass
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_ANON_KEY must be set as env vars.", file=sys.stderr)
        sys.exit(1)
    return url, key


def generate_api_key() -> tuple[str, str]:
    raw = "cdai_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a ColtraDataAi Enterprise API key.")
    parser.add_argument("--email", required=True, help="Customer email address")
    parser.add_argument("--label", required=True, help="Human-readable label (e.g. company name)")
    args = parser.parse_args()

    url, anon_key = _get_supabase_creds()
    raw_key, key_hash = generate_api_key()

    import urllib.request
    payload = json.dumps({
        "key_hash": key_hash,
        "label": args.label,
        "email": args.email,
        "is_active": True,
    }).encode()

    req = urllib.request.Request(
        f"{url}/rest/v1/api_keys",
        data=payload,
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"ERROR: Supabase returned {exc.code}: {body}", file=sys.stderr)
        sys.exit(1)

    if not result:
        print("ERROR: No data returned from Supabase.", file=sys.stderr)
        sys.exit(1)

    key_id = result[0]["id"]
    print(f"\nAPI key created successfully.")
    print(f"  ID:     {key_id}")
    print(f"  Label:  {args.label}")
    print(f"  Email:  {args.email}")
    print(f"\n  API KEY (save this — it will not be shown again):")
    print(f"\n      {raw_key}\n")


if __name__ == "__main__":
    main()
