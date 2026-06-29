"""One-off SMTP credential test — sends a single test email and exits.

Not part of the lifecycle email pipeline; delete after confirming SMTP works.
Usage: python scripts/test_smtp.py you@example.com
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_DIR / ".streamlit" / "secrets.toml"
sys.path.insert(0, str(PROJECT_DIR))

from services.transactional_email import send_email  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_smtp.py you@example.com")
        return 1

    to_email = sys.argv[1]
    secrets = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    cfg = secrets.get("transactional_email", {})

    ok = send_email(cfg, to_email, "ColtraDataAi SMTP test", "If you're reading this, SMTP works.")
    print("Sent." if ok else "Failed — check logs above for the exception.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
