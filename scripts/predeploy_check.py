#!/usr/bin/env python3
"""
predeploy_check.py — Master pre-deploy safety orchestrator for ColtraDataAi.

Runs all reliability checks before pushing to Streamlit Cloud:
  Step 1 — CP314 wheel validator    (always)
  Step 2 — Local env divergence     (always)
  Step 3 — Cloud simulation boot    (--full only)

Usage:
    python scripts/predeploy_check.py            # steps 1 + 2
    python scripts/predeploy_check.py --full     # steps 1 + 2 + 3 (boot test)

Exit codes:
    0  — all checks passed, safe to deploy
    1  — one or more checks failed
"""
from __future__ import annotations

import platform
import re
import subprocess
import sys
from pathlib import Path

# Ensure emoji / Unicode output works on Windows terminals (cp1252 → utf-8)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT    = Path(__file__).parent.parent
SCRIPTS = Path(__file__).parent

# ── ANSI colours ───────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


# ── Step runners ───────────────────────────────────────────────────────────────

def _header(title: str, step: int) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {BOLD}Step {step} — {title}{RESET}")
    print(f"{'─' * 62}")


def step_wheel_check() -> bool:
    """Run check_cp314_wheels.py and return True if all wheels are safe."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_cp314_wheels.py")],
        cwd=ROOT,
    )
    return result.returncode == 0


def step_divergence_check() -> bool:
    """
    Compare locally-installed package versions against requirements.txt.
    Flags divergence as a WARNING (not a hard failure) because the Cloud
    env is resolved independently.  Returns True always.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True, text=True, cwd=ROOT,
        )
        installed: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if "==" in line:
                name, ver = line.split("==", 1)
                installed[name.lower().replace("-", "_")] = ver.strip()

        req_file = ROOT / "requirements.txt"
        diverged: list[tuple[str, str, str]] = []

        for raw in req_file.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            line = line.split("#")[0].strip()
            m = re.match(r"^([A-Za-z0-9_.+-]+)==([^\s,;]+)", line)
            if not m:
                continue
            pkg_req = m.group(1).lower().replace("-", "_")
            ver_req = m.group(2)
            ver_local = installed.get(pkg_req)
            if ver_local and ver_local != ver_req:
                diverged.append((m.group(1), ver_local, ver_req))

        if diverged:
            print(
                f"\n  {YELLOW}⚠  Local env differs from Cloud-pinned versions:{RESET}"
            )
            col_w = max(len(p) for p, *_ in diverged) + 2
            for pkg, local, cloud in diverged:
                print(
                    f"  {DIM}  {pkg:<{col_w}} local={local:<12} cloud-pin={cloud}{RESET}"
                )
            print(
                f"\n  {YELLOW}  Run `pip install -r requirements.txt` if you want"
                f" to replicate the Cloud env locally.{RESET}"
            )
        else:
            print(f"\n  {GREEN}✔  Local environment matches all pinned versions.{RESET}")

        return True   # divergence is advisory only

    except Exception as exc:
        print(f"  {YELLOW}⚠  Could not run divergence check: {exc}{RESET}")
        return True


def step_cloud_sim() -> bool:
    """
    Run the platform-appropriate cloud simulation script.
    Creates a fresh venv, installs requirements wheel-only, and boots Streamlit.
    """
    if platform.system() == "Windows":
        script = SCRIPTS / "test_cloud_env.bat"
        cmd = ["cmd", "/c", str(script)]
    else:
        script = SCRIPTS / "test_cloud_env.sh"
        cmd = ["bash", str(script)]

    if not script.exists():
        print(f"  {YELLOW}⚠  Simulation script not found: {script}{RESET}")
        return False

    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode == 0


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    full_run = "--full" in sys.argv

    print(f"\n{BOLD}{'═' * 62}{RESET}")
    print(f"{BOLD}  ColtraDataAi — Pre-Deploy Safety Check{RESET}")
    print(f"{BOLD}{'═' * 62}{RESET}")

    steps: list[tuple[str, bool]] = []

    _header("CP314 wheel validator", 1)
    steps.append(("CP314 wheel validator", step_wheel_check()))

    _header("Local env divergence check", 2)
    steps.append(("Local env divergence", step_divergence_check()))

    if full_run:
        _header("Cloud simulation boot test", 3)
        steps.append(("Cloud simulation boot", step_cloud_sim()))
    else:
        print(
            f"\n  {DIM}Boot test skipped — re-run with --full to include it.{RESET}"
        )

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 62}")
    print(f"  {BOLD}SUMMARY{RESET}")
    print(f"{'═' * 62}")

    all_ok = all(ok for _, ok in steps)

    for label, ok in steps:
        icon = f"{GREEN}✔{RESET}" if ok else f"{RED}✘{RESET}"
        print(f"  {icon}  {label}")

    print(f"{'─' * 62}")
    if all_ok:
        print(
            f"\n  {GREEN}{BOLD}✅  READY FOR STREAMLIT CLOUD DEPLOYMENT{RESET}\n"
        )
        return 0

    print(
        f"\n  {RED}{BOLD}❌  DEPLOYMENT WILL FAIL — resolve issues above before pushing{RESET}\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
