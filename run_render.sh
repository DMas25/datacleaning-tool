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

smtp_port    = int(os.environ.get("SMTP_PORT", "587"))
smtp_enabled = os.environ.get("SMTP_ENABLED", "false").lower()

content = f"""[dev]
testing_mode = false
local_dev = false

[admin]
admin_password     = {s("ADMIN_PASSWORD")}
dashboard_password = {s("ADMIN_DASHBOARD_PASSWORD")}
insights_password  = {s("ADMIN_INSIGHTS_PASSWORD")}
admin_email        = {s("ADMIN_EMAIL")}

[email]
resend_api_key = {s("RESEND_API_KEY")}
from_name      = "ColtraDataAi"
from_email     = {s("FROM_EMAIL", "noreply@coltradata.com")}

[anthropic]
api_key = {s("ANTHROPIC_API_KEY")}

[transactional_email]
resend_api_key = {s("RESEND_API_KEY")}
from_name      = "ColtraDataAi"
from_email     = {s("FROM_EMAIL", "support@coltradata.com")}
app_url        = {s("APP_URL")}

[supabase]
database_url = {s("DATABASE_URL")}
"""

pathlib.Path(".streamlit").mkdir(exist_ok=True)
pathlib.Path(".streamlit/secrets.toml").write_text(content)
print("secrets.toml written successfully")
PYEOF

# Patch Streamlit's index.html to suppress its branding during cold-start loading.
# This CSS applies before the Python server has responded, hiding chrome that our
# inject_app_css() can't reach. Idempotent — safe to run on every deploy.
python3 << 'PATCHEOF'
import pathlib, subprocess, sys

result = subprocess.run(
    [sys.executable, "-c",
     "import streamlit, os; print(os.path.join(os.path.dirname(streamlit.__file__), 'static', 'index.html'))"],
    capture_output=True, text=True
)
index_html = pathlib.Path(result.stdout.strip())
if not index_html.exists():
    print("Streamlit index.html not found — skipping cold-start patch")
else:
    content = index_html.read_text(encoding="utf-8")
    css = (
        '<style>'
        'header,[data-testid="stToolbar"],[data-testid="stDecoration"],'
        '[data-testid="stStatusWidget"],footer,#MainMenu,.stDeployButton'
        '{display:none!important;visibility:hidden!important}'
        '</style>'
    )
    if css in content:
        print("Streamlit index.html already patched — skipping")
    else:
        index_html.write_text(content.replace("</head>", css + "</head>", 1), encoding="utf-8")
        print("Streamlit index.html patched — cold-start branding suppressed")
PATCHEOF

exec streamlit run app.py \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.headless true
