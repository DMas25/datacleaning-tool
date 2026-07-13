#!/usr/bin/env bash
# Render startup script for the ColtraDataAi Streamlit app.
# Writes .streamlit/secrets.toml from Render env vars, then starts Streamlit.
# Run via: bash run_render.sh   (set as startCommand in render.yaml)

set -euo pipefail

python3 << 'PYEOF'
import os, json, pathlib, sys

def s(key, default=""):
    """Return JSON-encoded string — compatible with TOML basic string syntax."""
    return json.dumps(os.environ.get(key, default))

if not os.environ.get("CREDENTIALS_PASSWORD"):
    print("ERROR: CREDENTIALS_PASSWORD env var is required", file=sys.stderr)
    sys.exit(1)

smtp_port    = int(os.environ.get("SMTP_PORT", "587"))
smtp_enabled = os.environ.get("SMTP_ENABLED", "false").lower()

content = f"""[credentials]
password = {s("CREDENTIALS_PASSWORD")}

[dev]
testing_mode = false
local_dev = false

[admin]
admin_password     = {s("ADMIN_PASSWORD")}
dashboard_password = {s("ADMIN_DASHBOARD_PASSWORD")}
insights_password  = {s("ADMIN_INSIGHTS_PASSWORD")}

[anthropic]
api_key = {s("ANTHROPIC_API_KEY")}

[transactional_email]
enabled       = {smtp_enabled}
smtp_host     = {s("SMTP_HOST", "smtp.office365.com")}
smtp_port     = {smtp_port}
smtp_user     = {s("SMTP_USER", "support@coltradata.com")}
smtp_password = {s("SMTP_PASSWORD")}
from_name     = "ColtraDataAi"
from_email    = {s("SMTP_FROM", "noreply@coltradata.com")}
app_url       = {s("APP_URL")}

[supabase]
database_url = {s("DATABASE_URL")}
"""

pathlib.Path(".streamlit").mkdir(exist_ok=True)
pathlib.Path(".streamlit/secrets.toml").write_text(content)
print("secrets.toml written successfully")
PYEOF

exec streamlit run app.py \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.headless true
