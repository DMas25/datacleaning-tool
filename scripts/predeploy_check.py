#!/usr/bin/env python3
"""
predeploy_check.py — Master pre-deploy safety orchestrator for ColtraDataAi.

Steps:
  1 — CP314 wheel validator  (always)
  2 — Local env divergence   (always, advisory)
  3 — Cloud simulation boot  (--full only)

Usage:
    python scripts/predeploy_check.py               # steps 1 + 2
    python scripts/predeploy_check.py --full        # + step 3 boot test
    python scripts/predeploy_check.py --force       # run all, exit 0 regardless
    python scripts/predeploy_check.py --full --force

Exit codes:
    0  — all checks passed (or --force active)
    1  — one or more checks failed
"""
from __future__ import annotations

import os
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

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ── Flags ─────────────────────────────────────────────────────────────────────
FULL_RUN  = "--full"  in sys.argv
FORCE     = "--force" in sys.argv
IN_CI     = os.getenv("CI") == "true"   # GitHub Actions sets CI=true


# ── Helpers ───────────────────────────────────────────────────────────────────

def _header(title: str, step: int) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {BOLD}Step {step} — {title}{RESET}")
    print(f"{'─' * 62}")


def _write_gha_summary(lines: list[str]) -> None:
    """Append markdown lines to the GitHub Actions job summary."""
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


# ── Steps ─────────────────────────────────────────────────────────────────────

def step_wheel_check() -> tuple[bool, list[str]]:
    """
    Run check_cp314_wheels.py (--json mode) and return (ok, unsafe_list).
    Also prints the human-readable output via a second subprocess call.
    """
    # Human-readable output for the terminal
    subprocess.run(
        [sys.executable, str(SCRIPTS / "check_cp314_wheels.py")],
        cwd=ROOT,
    )

    # Machine-readable output for the summary
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_cp314_wheels.py"), "--json"],
        capture_output=True, text=True, cwd=ROOT,
    )
    try:
        import json
        data = json.loads(r.stdout)
        unsafe = data.get("unsafe", [])
        return (len(unsafe) == 0), unsafe
    except Exception:
        return r.returncode == 0, []


def step_divergence_check() -> bool:
    """
    Compare locally installed versions against requirements.txt pins.
    Advisory only — never fails the build.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            cwd=ROOT,
        )
        raw = result.stdout.decode("utf-8", errors="replace")
        installed: dict[str, str] = {
            name.lower().replace("-", "_"): ver.strip()
            for line in raw.splitlines()
            if "==" in line
            for name, ver in [line.split("==", 1)]
        }

        diverged: list[tuple[str, str, str]] = []
        for raw in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            line = line.split("#")[0].strip()
            m = re.match(r"^([A-Za-z0-9_.+-]+)==([^\s,;]+)", line)
            if not m:
                continue
            key = m.group(1).lower().replace("-", "_")
            ver_req = m.group(2)
            ver_local = installed.get(key)
            if ver_local and ver_local != ver_req:
                diverged.append((m.group(1), ver_local, ver_req))

        if diverged:
            print(f"\n  {YELLOW}⚠  Local env differs from Cloud-pinned versions:{RESET}")
            col = max(len(p) for p, *_ in diverged) + 2
            for pkg, local, cloud in diverged:
                print(f"  {DIM}  {pkg:<{col}} local={local:<12} cloud-pin={cloud}{RESET}")
            print(
                f"\n  {YELLOW}  Tip: pip install -r requirements.txt"
                f" to align with Cloud.{RESET}"
            )
        else:
            print(f"\n  {GREEN}✔  Local environment matches all pinned versions.{RESET}")

        return True  # divergence is advisory — never a hard failure

    except Exception as exc:
        print(f"  {YELLOW}⚠  Could not run divergence check: {exc}{RESET}")
        return True


def step_cloud_sim() -> bool:
    """Run the platform-appropriate cloud simulation script."""
    script = (
        SCRIPTS / "test_cloud_env.bat"
        if platform.system() == "Windows"
        else SCRIPTS / "test_cloud_env.sh"
    )
    if not script.exists():
        print(f"  {YELLOW}⚠  Simulation script not found: {script}{RESET}")
        return False

    cmd = (
        ["cmd", "/c", str(script)]
        if platform.system() == "Windows"
        else ["bash", str(script)]
    )
    return subprocess.run(cmd, cwd=ROOT).returncode == 0


# ── CI / GHA summary ──────────────────────────────────────────────────────────

def _build_ci_summary(
    steps: list[tuple[str, bool]],
    unsafe_packages: list[str],
    all_ok: bool,
    forced: bool,
) -> list[str]:
    """Return markdown lines for the GitHub Actions job summary panel."""
    lines = ["## 🛡️ ColtraDataAi Pre-Deploy Check", ""]
    lines += ["| Check | Result |", "|---|---|"]

    for label, ok in steps:
        icon = "✅ Pass" if ok else ("⚠️ Overridden" if forced else "❌ Fail")
        lines.append(f"| {label} | {icon} |")

    lines.append("")

    if unsafe_packages:
        lines += ["### ❌ Unsafe packages", ""]
        for pkg in unsafe_packages:
            # Strip ANSI codes for markdown
            clean = re.sub(r"\033\[[0-9;]*m", "", pkg)
            lines.append(f"- `{clean}`")
        lines.append("")

    if forced and not all_ok:
        lines += [
            "---",
            "⚠️ **FORCE MODE ACTIVE** — checks were overridden.",
            "Fix `requirements.txt` before the next deploy.",
            "",
        ]
    elif all_ok:
        lines += ["---", "✅ **READY FOR STREAMLIT CLOUD DEPLOYMENT**", ""]
    else:
        lines += [
            "---",
            "🚫 **Deployment blocked — fix requirements.txt before pushing**",
            "",
        ]

    return lines


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n{BOLD}{'═' * 62}{RESET}")
    print(f"{BOLD}  ColtraDataAi — Pre-Deploy Safety Check{RESET}")
    if FORCE:
        print(
            f"  {YELLOW}{BOLD}⚠  FORCE MODE — failures will NOT block exit{RESET}"
        )
    print(f"{BOLD}{'═' * 62}{RESET}")

    steps: list[tuple[str, bool]] = []
    unsafe_packages: list[str] = []

    # ── Step 1: CP314 wheel validator ─────────────────────────────────────────
    _header("CP314 wheel validator", 1)
    wheel_ok, unsafe_packages = step_wheel_check()
    steps.append(("All dependencies have cp314 wheels", wheel_ok))

    # ── Step 2: Divergence check ──────────────────────────────────────────────
    _header("Local env divergence check", 2)
    div_ok = step_divergence_check()
    steps.append(("Local env matches requirements.txt pins", div_ok))

    # ── Step 3: Cloud simulation (--full) ─────────────────────────────────────
    if FULL_RUN:
        _header("Cloud simulation boot test", 3)
        sim_ok = step_cloud_sim()
        steps.append(("Cloud simulation boot", sim_ok))
    else:
        print(
            f"\n  {DIM}Boot test skipped — re-run with --full to include it.{RESET}"
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    all_ok = all(ok for _, ok in steps)

    print(f"\n{'═' * 62}")
    print(f"  {BOLD}SUMMARY{RESET}")
    print(f"{'═' * 62}")

    for label, ok in steps:
        if ok:
            print(f"  {GREEN}✔  {label}{RESET}")
        else:
            icon = f"{YELLOW}⚠ " if FORCE else f"{RED}✘ "
            print(f"  {icon} {label}{RESET}")

    # ── Error detail block ────────────────────────────────────────────────────
    if unsafe_packages:
        print(f"\n{'─' * 62}")
        for pkg in unsafe_packages:
            print(f"  {RED}❌  {pkg}{RESET}")
        if not FORCE:
            print(
                f"\n  {RED}{BOLD}🚫  Deployment blocked"
                f" — fix requirements.txt before pushing{RESET}"
            )

    print(f"\n{'─' * 62}")

    # ── Final verdict ─────────────────────────────────────────────────────────
    if all_ok:
        print(f"\n  {GREEN}{BOLD}✅  READY FOR STREAMLIT CLOUD DEPLOYMENT{RESET}\n")
    elif FORCE:
        print(
            f"\n  {YELLOW}{BOLD}⚠  FORCE MODE ACTIVE — exiting 0 despite failures{RESET}"
        )
        print(
            f"  {YELLOW}     Fix the issues above before the next real deploy.{RESET}\n"
        )
    else:
        print(
            f"\n  {RED}{BOLD}❌  DEPLOYMENT WILL FAIL"
            f" — resolve issues above before pushing{RESET}\n"
        )

    # ── Write GitHub Actions job summary ─────────────────────────────────────
    if IN_CI or os.getenv("GITHUB_STEP_SUMMARY"):
        summary = _build_ci_summary(steps, unsafe_packages, all_ok, FORCE)
        _write_gha_summary(summary)

    if FORCE:
        return 0
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
