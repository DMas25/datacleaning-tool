"""
CLI utility to provision an Enterprise API key.

Usage:
    python scripts/create_api_key.py --email customer@example.com --label "Acme Corp"

The script prints the raw API key ONCE — save it immediately.
Only the SHA-256 hash is stored in Supabase.
"""
from __future__ import annotations

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.auth import generate_api_key
from services.supabase_client import get_supabase_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a ColtraDataAi Enterprise API key.")
    parser.add_argument("--email", required=True, help="Customer email address")
    parser.add_argument("--label", required=True, help="Human-readable label (e.g. company name)")
    args = parser.parse_args()

    raw_key, key_hash = generate_api_key()

    client = get_supabase_client()
    result = client.table("api_keys").insert({
        "key_hash": key_hash,
        "label": args.label,
        "email": args.email,
        "is_active": True,
    }).execute()

    if not result.data:
        print("ERROR: Failed to insert API key into Supabase.", file=sys.stderr)
        sys.exit(1)

    key_id = result.data[0]["id"]
    print(f"\nAPI key created successfully.")
    print(f"  ID:     {key_id}")
    print(f"  Label:  {args.label}")
    print(f"  Email:  {args.email}")
    print(f"\n  API KEY (save this — it will not be shown again):")
    print(f"\n      {raw_key}\n")


if __name__ == "__main__":
    main()
