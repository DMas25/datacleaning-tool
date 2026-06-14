# ════════════════════════════════════════════════════════════════════════════
# STREAMLIT CLOUD DEPLOYMENT GUIDE
# ════════════════════════════════════════════════════════════════════════════
#
# VERIFIED SAFETY CHECKS ✅
# ════════════════════════════════════════════════════════════════════════════
#
# [1] NO SERVER PACKAGES
# ✅ No uvicorn, starlette, httptools, or websockets in requirements.txt
# ✅ Streamlit Cloud manages all server infrastructure
# ✅ Desktop version uses tkinter (stdlib) — no conflicts
#
# [2] PYTHON VERSION
# ✅ runtime.txt = python-3.11 (locked to stable 3.11.x)
# ✅ All packages pinned for Python 3.11 compatibility
#
# [3] DUAL-MODE SAFETY
# ✅ app_desktop.py protected with `if __name__ == "__main__":`
# ✅ No module-level auto-exec code (all functions/classes properly gated)
# ✅ app.py = Streamlit entry point only
# ✅ No circular imports or side effects on import
#
# [4] STREAMLIT CLOUD CONFIGURATION
# ✅ .streamlit/config.toml has NO port specification (Cloud-compatible)
# ✅ Headless mode enabled for Cloud
# ✅ .streamlit/.gitignore prevents local configs from reaching Cloud
#
# ════════════════════════════════════════════════════════════════════════════
# DEPLOYMENT INSTRUCTIONS
# ════════════════════════════════════════════════════════════════════════════
#
# 1. STREAMLIT CLOUD DEPLOYMENT
# ────────────────────────────────────────────────────────────────────────────
#    a) Create app in Streamlit Cloud (https://share.streamlit.io)
#    b) Point to this repository's `master` branch
#    c) Set app entry point to: app.py
#    d) Add secrets in Streamlit Cloud dashboard:
#       [credentials]
#       password = "your_secure_password"
#       
#       [dev]
#       app_mode = "live"  # Use "live" for production, "dev" for testing
#
# 2. LOCAL DESKTOP DEVELOPMENT
# ────────────────────────────────────────────────────────────────────────────
#    a) Activate .venv: source .venv/bin/activate (Mac/Linux) or .venv\Scripts\activate (Windows)
#    b) Run: python app_desktop.py (uses tkinter, no port conflicts)
#    c) OR use batch file: Start ColtraData.bat (Windows) — runs Streamlit on :8502 for testing
#
# 3. LOCAL STREAMLIT TESTING
# ────────────────────────────────────────────────────────────────────────────
#    For testing Streamlit locally:
#    streamlit run app.py --server.port 8502 --server.address localhost
#    (The .streamlit/config.toml will NOT override port on Cloud — it's Cloud-managed)
#
# ════════════════════════════════════════════════════════════════════════════
# ARCHITECTURE
# ════════════════════════════════════════════════════════════════════════════
#
# app.py                     → Streamlit entry point (Cloud + local testing)
# app_desktop.py             → Desktop tkinter app (local only, protected by if __name__)
# .streamlit/config.toml     → Shared config (Cloud-safe: no port specification)
# requirements.txt           → Pinned dependencies (no server packages)
# runtime.txt                → Python 3.11 (stable)
#
# ════════════════════════════════════════════════════════════════════════════
# TROUBLESHOOTING
# ════════════════════════════════════════════════════════════════════════════
#
# "Uvicorn server started on port 8502"  [OLD ERROR — NOW FIXED]
# → This was caused by port=8502 in .streamlit/config.toml
# → FIXED: Port specification removed from Cloud-compatible config
# → Local dev users can still use port 8502 via command line or batch file
#
# "Health check failed on port 8501"  [OLD ERROR — NOW FIXED]
# → Caused by port conflicts during Cloud deployment
# → FIXED: No port specification in config.toml (Cloud manages ports)
#
# ════════════════════════════════════════════════════════════════════════════
