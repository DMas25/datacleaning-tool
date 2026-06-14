@echo off
REM ══════════════════════════════════════════════════════════════
REM  test_cloud_env.bat — Simulates a Streamlit Cloud deployment
REM  locally on Windows.
REM
REM  What it does:
REM    1. Creates a clean temporary virtual environment
REM    2. Installs requirements.txt using WHEEL-ONLY mode
REM       (mirrors Streamlit Cloud uv --only-binary behaviour)
REM    3. Verifies all critical imports load without error
REM    4. Cleans up the test environment
REM
REM  Usage:
REM    scripts\test_cloud_env.bat
REM    (or run via: python scripts/predeploy_check.py --full)
REM ══════════════════════════════════════════════════════════════
setlocal EnableDelayedExpansion

set "ROOT=%~dp0.."
set "TEST_VENV=%ROOT%\.test_venv"
set "REQUIREMENTS=%ROOT%\requirements.txt"
set "APP=%ROOT%\app.py"
set "PASS_COUNT=0"
set "FAIL=0"

echo.
echo =============================================================
echo   ColtraDataAi - Pre-Deploy Cloud Environment Test (Windows)
echo =============================================================
echo.

REM ── 1. Remove previous test venv ──────────────────────────────
if exist "%TEST_VENV%" (
    echo Cleaning up previous test venv...
    rmdir /s /q "%TEST_VENV%" 2>nul
)

REM ── 2. Create fresh venv ──────────────────────────────────────
echo Creating clean virtual environment...
python -m venv "%TEST_VENV%"
if errorlevel 1 (
    echo.
    echo [FAIL] Could not create virtual environment.
    echo        Ensure Python is on PATH.
    exit /b 1
)

REM ── 3. Upgrade pip silently ───────────────────────────────────
"%TEST_VENV%\Scripts\python.exe" -m pip install --upgrade pip --quiet

REM ── 4. Wheel-only install ─────────────────────────────────────
echo.
echo [Step 1/3] Installing requirements.txt (wheel-only, no source builds)...
echo.
"%TEST_VENV%\Scripts\pip.exe" install ^
    --only-binary=:all: ^
    --no-cache-dir ^
    --quiet ^
    -r "%REQUIREMENTS%"

if errorlevel 1 (
    echo.
    echo [FAIL] Dependency install failed in wheel-only mode.
    echo        At least one package has no cp314 wheel.
    echo.
    echo [FIX]  Run: python scripts\check_cp314_wheels.py
    echo        to identify which package is missing a wheel.
    goto :cleanup_fail
)

echo [PASS] All dependencies installed (wheel-only).
set /a PASS_COUNT+=1

REM ── 5. Import smoke test ──────────────────────────────────────
echo.
echo [Step 2/3] Running import smoke test...
echo.

"%TEST_VENV%\Scripts\python.exe" -c ^
    "import streamlit, pandas, numpy, scipy, matplotlib, plotly, PIL, reportlab, anthropic, xlrd, openpyxl, xlsxwriter; print('  All core imports OK')"

if errorlevel 1 (
    echo.
    echo [FAIL] One or more core imports failed.
    echo        Check the error above for the offending package.
    goto :cleanup_fail
)

echo [PASS] Core imports verified.
set /a PASS_COUNT+=1

REM ── 6. Module-level app import check ─────────────────────────
echo.
echo [Step 3/3] Checking app module imports...
echo.

"%TEST_VENV%\Scripts\python.exe" -c ^
    "import sys; sys.path.insert(0,'%ROOT:\=/%'); ^
     mods=['config.branding_config','config.tier_config','core.feature_gate', ^
           'ui.homepage','ui.upload_panel','ui.cleaning_options', ^
           'ui.results_panel','utils.session_helpers','services.subscription']; ^
     [__import__(m) for m in mods]; print('  All app modules imported OK')" 2>&1

if errorlevel 1 (
    echo.
    echo [FAIL] App module import failed.
    echo        A module or its dependency has an issue.
    goto :cleanup_fail
)

echo [PASS] App modules verified.
set /a PASS_COUNT+=1

REM ── Result ────────────────────────────────────────────────────
goto :cleanup_pass

:cleanup_fail
echo.
rmdir /s /q "%TEST_VENV%" 2>nul
echo =============================================================
echo   RESULT: DEPLOYMENT WILL FAIL
echo =============================================================
echo.
exit /b 1

:cleanup_pass
echo.
rmdir /s /q "%TEST_VENV%" 2>nul
echo =============================================================
echo   RESULT: !PASS_COUNT!/3 checks passed
echo   SAFE TO DEPLOY to Streamlit Cloud
echo =============================================================
echo.
exit /b 0
