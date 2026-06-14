#!/usr/bin/env python3
"""
check_cp314_wheels.py — Validates that every package in requirements.txt
has a pre-built CPython 3.14 wheel on PyPI.

Packages without cp314 wheels fall back to source compilation on Streamlit
Cloud, which fails because the platform lacks build headers (zlib, libjpeg,
gfortran, etc.).

Usage:
    python scripts/check_cp314_wheels.py

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
ROOT = Path(__file__).parent.parent
REQUIREMENTS = ROOT / "requirements.txt"

# ── PyPI API endpoints ─────────────────────────────────────────────────────────
PYPI_VERSION_URL = "https://pypi.org/pypi/{name}/{version}/json"
PYPI_LATEST_URL  = "https://pypi.org/pypi/{name}/json"

# ── ANSI colours ───────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


# ── Data types ─────────────────────────────────────────────────────────────────

class PackageSpec(NamedTuple):
    name: str          # normalised package name
    raw_spec: str      # version constraint string, e.g. ">=2.2.0,<3"
    exact: str | None  # resolved exact version, or None if range


# ── Requirement parser ─────────────────────────────────────────────────────────

def parse_requirements(path: Path) -> list[PackageSpec]:
    specs: list[PackageSpec] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split("#")[0].strip()  # strip inline comment
        if not line:
            continue

        # Exact pin: name==1.2.3
        m = re.match(r"^([A-Za-z0-9_.+-]+)==([^\s,;]+)$", line)
        if m:
            specs.append(PackageSpec(m.group(1), f"=={m.group(2)}", m.group(2)))
            continue

        # Range or bare name: capture everything after the package name
        m = re.match(r"^([A-Za-z0-9_.+-]+)(.*)?$", line)
        if m:
            specs.append(PackageSpec(m.group(1), m.group(2).strip(), None))

    return specs


# ── PyPI helpers ───────────────────────────────────────────────────────────────

def _fetch_json(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError,
            TimeoutError):
        return None


def resolve_version(name: str, raw_spec: str) -> str | None:
    """
    For range specs, find the latest stable version on PyPI that satisfies
    the constraint.  Falls back to the PyPI 'latest' field on parse errors.
    """
    data = _fetch_json(PYPI_LATEST_URL.format(name=name))
    if not data:
        return None

    # Try packaging.SpecifierSet (always available — pip bundles packaging)
    try:
        from packaging.specifiers import SpecifierSet
        from packaging.version import Version

        all_versions = list(data.get("releases", {}).keys())
        stable = [
            v for v in all_versions
            if not re.search(r"[ab]rc|\.dev|\.post", v, re.I)
        ]
        spec = SpecifierSet(raw_spec) if raw_spec else SpecifierSet()
        matching = sorted(
            (v for v in stable if Version(v) in spec),
            key=lambda v: Version(v),
        )
        if matching:
            return matching[-1]
    except Exception:
        pass

    # Hard fallback: PyPI 'latest' (ignores upper bounds but good enough)
    return data.get("info", {}).get("version")


def get_wheel_filenames(name: str, version: str) -> list[str]:
    """Return the list of filenames published for name==version on PyPI."""
    data = _fetch_json(PYPI_VERSION_URL.format(name=name, version=version))
    if not data:
        return []
    return [f["filename"] for f in data.get("urls", [])]


# ── Wheel compatibility logic ──────────────────────────────────────────────────

def is_cp314_compatible(filename: str) -> bool:
    """
    Return True if this wheel filename can be installed on CPython 3.14.

    Wheel filename format: {name}-{version}-{python_tag}-{abi_tag}-{platform_tag}.whl

    Compatible tags:
      - abi_tag == 'none'   → pure-Python wheel, no ABI dependency (any Python)
      - python_tag == 'cp314'         → CPython 3.14 specific
      - abi_tag == 'abi3' and min_ver <= 314  → stable ABI, works on 3.14+
    """
    if not filename.endswith(".whl"):
        return False

    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return False

    python_tag = parts[2]
    abi_tag    = parts[3]

    # Pure-Python: no ABI dependency → works on any Python version
    if abi_tag == "none":
        return True

    # CPython 3.14 native wheel
    if python_tag == "cp314":
        return True

    # Stable ABI (abi3): wheel requires CPython >= tagged version.
    # e.g. cp32-abi3 → requires 3.2+, so works on 3.14. ✅
    #      cp315-abi3 → requires 3.15+, does NOT work on 3.14. ❌
    if abi_tag == "abi3":
        try:
            min_ver = int(re.sub(r"[^0-9]", "", python_tag))  # 'cp310' → 310
            return min_ver <= 314
        except (ValueError, TypeError):
            pass

    return False


# ── Per-package check ──────────────────────────────────────────────────────────

def check_package(spec: PackageSpec) -> tuple[bool, str]:
    """
    Returns (is_safe, human-readable message).
    """
    # Resolve version
    version = spec.exact
    if version is None:
        version = resolve_version(spec.name, spec.raw_spec)
    if not version:
        return False, f"{spec.name}{spec.raw_spec} — could not resolve version from PyPI"

    # Fetch file list for that version
    filenames = get_wheel_filenames(spec.name, version)
    if not filenames:
        return False, f"{spec.name}=={version} — no files found on PyPI (package or version unknown?)"

    wheels = [f for f in filenames if f.endswith(".whl")]
    if not wheels:
        return False, (
            f"{spec.name}=={version} — source distribution only, no wheel published\n"
            f"  {DIM}→ Will trigger source build on Streamlit Cloud (likely to fail){RESET}"
        )

    safe = [w for w in wheels if is_cp314_compatible(w)]
    if safe:
        # Show the most informative filename (shortest usually)
        best = min(safe, key=len)
        return True, f"{spec.name}=={version}  →  {DIM}{best}{RESET}"

    # Wheels exist but none are cp314-compatible
    tags = ", ".join(w.split("-")[2] for w in wheels[:5])
    return False, (
        f"{spec.name}=={version} — wheels published but NONE support cp314\n"
        f"  {DIM}Available python tags: {tags}{RESET}\n"
        f"  {DIM}→ Upgrade to a newer version or find an alternative package{RESET}"
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    if not REQUIREMENTS.exists():
        print(f"{RED}requirements.txt not found at {REQUIREMENTS}{RESET}")
        return 1

    specs = parse_requirements(REQUIREMENTS)

    print(f"\n{BOLD}CP314 Wheel Compatibility Check{RESET}")
    print(f"{DIM}Checking {len(specs)} packages against PyPI …{RESET}\n")

    safe_msgs:   list[str] = []
    unsafe_msgs: list[str] = []

    for spec in specs:
        ok, msg = check_package(spec)
        if ok:
            safe_msgs.append(msg)
            print(f"  {GREEN}✅  {msg}{RESET}")
        else:
            unsafe_msgs.append(msg)
            print(f"  {RED}❌  {msg}{RESET}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'─' * 62}")
    print(f"  {GREEN}{len(safe_msgs)} safe{RESET}    {RED}{len(unsafe_msgs)} unsafe{RESET}")

    if unsafe_msgs:
        print(
            f"\n{RED}{BOLD}❌  UNSAFE — deployment on Streamlit Cloud WILL fail{RESET}\n"
            f"{DIM}   Fix: upgrade the flagged packages to versions with cp314 wheels.{RESET}\n"
            f"{DIM}   Check: https://pypi.org/project/<name>/#files{RESET}\n"
        )
        return 1

    print(f"\n{GREEN}{BOLD}✅  All packages have cp314 wheels — safe to deploy{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
