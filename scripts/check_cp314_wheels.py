#!/usr/bin/env python3
"""
check_cp314_wheels.py — Validates that every package in requirements.txt
has a pre-built CPython 3.14 wheel on PyPI.

Packages without cp314 wheels fall back to source compilation on Streamlit
Cloud, which fails because the platform lacks build headers.

Usage:
    python scripts/check_cp314_wheels.py
    python scripts/check_cp314_wheels.py --json   # machine-readable output

Exit codes:
    0  — all packages are wheel-safe for cp314
    1  — one or more packages would trigger a source build / are unsafe
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import NamedTuple

# Ensure emoji / Unicode output works on Windows terminals (cp1252 → utf-8)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).parent.parent
REQUIREMENTS = ROOT / "requirements.txt"

# ── PyPI API endpoints ────────────────────────────────────────────────────────
PYPI_VERSION_URL = "https://pypi.org/pypi/{name}/{version}/json"
PYPI_LATEST_URL  = "https://pypi.org/pypi/{name}/json"

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


# ── Data types ────────────────────────────────────────────────────────────────

class PackageSpec(NamedTuple):
    name: str          # normalised package name
    raw_spec: str      # version constraint string, e.g. ">=2.2.0,<3"
    exact: str | None  # resolved exact version, or None if range

class CheckResult(NamedTuple):
    safe:   list[str]   # "name==version" strings that passed
    unsafe: list[str]   # "name==version → reason" strings that failed


# ── Requirement parser ────────────────────────────────────────────────────────

def parse_requirements(path: Path) -> list[PackageSpec]:
    specs: list[PackageSpec] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split("#")[0].strip()
        if not line:
            continue

        m = re.match(r"^([A-Za-z0-9_.+-]+)==([^\s,;]+)$", line)
        if m:
            specs.append(PackageSpec(m.group(1), f"=={m.group(2)}", m.group(2)))
            continue

        m = re.match(r"^([A-Za-z0-9_.+-]+)(.*)?$", line)
        if m:
            specs.append(PackageSpec(m.group(1), m.group(2).strip(), None))
    return specs


# ── PyPI helpers ──────────────────────────────────────────────────────────────

def _fetch_json(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError,
            json.JSONDecodeError, TimeoutError):
        return None


def resolve_version(name: str, raw_spec: str) -> str | None:
    data = _fetch_json(PYPI_LATEST_URL.format(name=name))
    if not data:
        return None
    try:
        from packaging.specifiers import SpecifierSet
        from packaging.version import Version
        all_versions = list(data.get("releases", {}).keys())
        stable = [v for v in all_versions
                  if not re.search(r"[ab]rc|\.dev|\.post", v, re.I)]
        spec = SpecifierSet(raw_spec) if raw_spec else SpecifierSet()
        matching = sorted(
            (v for v in stable if Version(v) in spec),
            key=lambda v: Version(v),
        )
        if matching:
            return matching[-1]
    except Exception:
        pass
    return data.get("info", {}).get("version")


def get_wheel_filenames(name: str, version: str) -> list[str]:
    data = _fetch_json(PYPI_VERSION_URL.format(name=name, version=version))
    if not data:
        return []
    return [f["filename"] for f in data.get("urls", [])]


# ── Wheel compatibility ───────────────────────────────────────────────────────

def is_cp314_compatible(filename: str) -> bool:
    """
    Return True if this wheel filename is installable on CPython 3.14.
      abi_tag == 'none'            → pure-Python (any Python version)
      python_tag == 'cp314'        → CPython 3.14 native wheel
      abi_tag == 'abi3', min ≤ 314 → stable ABI, works on 3.14+
    """
    if not filename.endswith(".whl"):
        return False
    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return False
    python_tag, abi_tag = parts[2], parts[3]

    if abi_tag == "none":
        return True
    if python_tag == "cp314":
        return True
    if abi_tag == "abi3":
        try:
            return int(re.sub(r"[^0-9]", "", python_tag)) <= 314
        except (ValueError, TypeError):
            pass
    return False


# ── Per-package check ─────────────────────────────────────────────────────────

def check_package(spec: PackageSpec) -> tuple[bool, str, str]:
    """
    Returns (is_safe, display_message, key) where key is "name==version".
    """
    version = spec.exact or resolve_version(spec.name, spec.raw_spec)
    key = f"{spec.name}=={version}" if version else f"{spec.name}{spec.raw_spec}"

    if not version:
        return False, f"{key}  →  could not resolve version from PyPI", key

    filenames = get_wheel_filenames(spec.name, version)
    if not filenames:
        return False, f"{key}  →  package not found on PyPI", key

    wheels = [f for f in filenames if f.endswith(".whl")]
    if not wheels:
        return (
            False,
            f"{key}  →  no wheel published  {DIM}(source-only — will fail on Cloud){RESET}",
            key,
        )

    safe = [w for w in wheels if is_cp314_compatible(w)]
    if safe:
        best = min(safe, key=len)
        return True, f"{key}  →  {DIM}{best}{RESET}", key

    tags = ", ".join(w.split("-")[2] for w in wheels[:5])
    return (
        False,
        f"{key}  →  no cp314 wheel  {DIM}(published tags: {tags}){RESET}",
        key,
    )


# ── Public API (importable by predeploy_check.py) ────────────────────────────

def run_checks(quiet: bool = False) -> CheckResult:
    """
    Run all wheel checks and return a CheckResult(safe, unsafe).
    Prints per-package status lines unless quiet=True.
    """
    if not REQUIREMENTS.exists():
        if not quiet:
            print(f"{RED}requirements.txt not found{RESET}")
        return CheckResult([], [f"requirements.txt not found at {REQUIREMENTS}"])

    specs = parse_requirements(REQUIREMENTS)
    if not quiet:
        print(f"\n{BOLD}CP314 Wheel Compatibility Check{RESET}")
        print(f"{DIM}Checking {len(specs)} packages against PyPI …{RESET}\n")

    safe_list:   list[str] = []
    unsafe_list: list[str] = []

    for spec in specs:
        ok, msg, key = check_package(spec)
        if ok:
            safe_list.append(key)
            if not quiet:
                print(f"  {GREEN}✅  {msg}{RESET}")
        else:
            unsafe_list.append(msg)   # store the descriptive message
            if not quiet:
                print(f"  {RED}❌  {msg}{RESET}")

    return CheckResult(safe_list, unsafe_list)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    as_json = "--json" in sys.argv
    result  = run_checks(quiet=as_json)

    if as_json:
        print(json.dumps({"safe": result.safe, "unsafe": result.unsafe}, indent=2))
        return 0 if not result.unsafe else 1

    # ── Human-readable summary ─────────────────────────────────────────────────
    print(f"\n{'─' * 62}")
    print(f"  {GREEN}{len(result.safe)} safe{RESET}    {RED}{len(result.unsafe)} unsafe{RESET}")

    if result.unsafe:
        print(f"\n  {RED}{BOLD}❌  UNSAFE PACKAGES FOUND{RESET}")
        print(f"  {RED}🚫  Deployment blocked — fix requirements.txt before pushing{RESET}")
        print(f"\n  {DIM}How to fix:{RESET}")
        print(f"  {DIM}  1. Visit https://pypi.org/project/<name>/#files{RESET}")
        print(f"  {DIM}  2. Find a version that ships a cp314 wheel{RESET}")
        print(f"  {DIM}  3. Update the version bound in requirements.txt{RESET}\n")
        return 1

    print(f"\n  {GREEN}{BOLD}✅  All dependencies safe (cp314 wheels){RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
