#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  test_cloud_env.sh — Simulates a Streamlit Cloud deployment
#  locally on Linux / macOS / GitHub Actions CI.
#
#  What it does:
#    1. Creates a clean temporary virtual environment
#    2. Installs requirements.txt using WHEEL-ONLY mode
#       (mirrors Streamlit Cloud uv --only-binary behaviour)
#    3. Verifies all critical imports load without error
#    4. Cleans up the test environment
#
#  Usage:
#    bash scripts/test_cloud_env.sh
#    (or run via: python scripts/predeploy_check.py --full)
# ══════════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_VENV="$ROOT/.test_venv"
REQUIREMENTS="$ROOT/requirements.txt"
PASS_COUNT=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; ((PASS_COUNT++)) || true; }
fail() {
    echo -e "\n  ${RED}[FAIL]${NC} $1"
    echo "$2"
    rm -rf "$TEST_VENV"
    echo -e "\n${RED}  RESULT: DEPLOYMENT WILL FAIL${NC}\n"
    exit 1
}

echo ""
echo "============================================================="
echo "  ColtraDataAi - Pre-Deploy Cloud Environment Test (Linux)"
echo "============================================================="
echo ""

# ── 1. Clean previous test venv ────────────────────────────────
rm -rf "$TEST_VENV"

# ── 2. Create fresh venv ───────────────────────────────────────
echo "Creating clean virtual environment..."
python3 -m venv "$TEST_VENV"
"$TEST_VENV/bin/pip" install --upgrade pip --quiet

# ── 3. Wheel-only install ──────────────────────────────────────
echo ""
echo "[Step 1/3] Installing requirements.txt (wheel-only, no source builds)..."
echo ""

if ! "$TEST_VENV/bin/pip" install \
    --only-binary=:all: \
    --no-cache-dir \
    --quiet \
    -r "$REQUIREMENTS"; then
    fail \
        "Dependency install failed in wheel-only mode." \
        "  Run: python scripts/check_cp314_wheels.py  to find the unsafe package."
fi

pass "All dependencies installed (wheel-only)."

# ── 4. Import smoke test ───────────────────────────────────────
echo ""
echo "[Step 2/3] Running import smoke test..."
echo ""

if ! "$TEST_VENV/bin/python" -c "
import streamlit, pandas, numpy, scipy, matplotlib, plotly
import PIL, reportlab, anthropic, xlrd, openpyxl, xlsxwriter
print('  All core imports OK')
"; then
    fail \
        "One or more core imports failed." \
        "  Check the error above for the offending package."
fi

pass "Core imports verified."

# ── 5. App module import check ─────────────────────────────────
echo ""
echo "[Step 3/3] Checking app module imports..."
echo ""

if ! PYTHONPATH="$ROOT" "$TEST_VENV/bin/python" -c "
import sys
mods = [
    'config.branding_config', 'config.tier_config',
    'core.feature_gate',
    'ui.homepage', 'ui.upload_panel', 'ui.cleaning_options',
    'ui.results_panel', 'utils.session_helpers', 'services.subscription',
]
for m in mods:
    __import__(m)
print('  All app modules imported OK')
" 2>&1; then
    fail \
        "App module import failed." \
        "  A module or its dependency has an issue."
fi

pass "App modules verified."

# ── Clean up ───────────────────────────────────────────────────
rm -rf "$TEST_VENV"

echo ""
echo "============================================================="
echo -e "  RESULT: ${PASS_COUNT}/3 checks passed"
echo -e "  ${GREEN}✅ SAFE TO DEPLOY to Streamlit Cloud${NC}"
echo "============================================================="
echo ""
