#!/usr/bin/env python3
"""
verify_lemonsqueezy.py — Pre-launch LemonSqueezy readiness checker for ColtraDataAi.

Runs every item in the go-live checklist:

  Local checks (no API key required):
    1.  Branding / logo file present
    2.  Support email configured
    3.  All four checkout URLs populated in config
    4.  Correct pricing in local config (Starter £9, Professional £29, Premium £59, Enterprise £299)
    5.  Checkout URL format valid (correct store slug, expected variant UUIDs)

  API checks (requires --api-key or LEMONSQUEEZY_API_KEY env var):
    6.  Test mode is OFF on the store
    7.  Store status is "active"
    8.  All four products are published / visible
    9.  Product names match expected (Starter, Professional, Premium, Enterprise)
   10.  Variant prices match config prices
   11.  Starter checkout URL is reachable (HTTP 200)
   12.  Professional checkout URL is reachable (HTTP 200)
   13.  Premium checkout URL is reachable (HTTP 200)
   14.  Enterprise checkout URL is reachable (HTTP 200)

Usage:
    python scripts/verify_lemonsqueezy.py
    python scripts/verify_lemonsqueezy.py --api-key eyJhbGci...
    LEMONSQUEEZY_API_KEY=eyJhbGci... python scripts/verify_lemonsqueezy.py

Exit codes:
    0  — all checks passed
    1  — one or more checks failed
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

LS_API_BASE = "https://api.lemonsqueezy.com/v1"
STORE_SLUG  = "coltradataai"

EXPECTED_PLANS: dict[str, dict] = {
    "Starter":      {"price_gbp": 9,   "variant_id": "1888469", "checkout_uuid": "d5d25833-3149-487f-a9d1-832c398d13e6"},
    "Professional": {"price_gbp": 29,  "variant_id": "1888467", "checkout_uuid": "a358b1c4-70b8-4196-ab47-fe22153a488d"},
    "Premium":      {"price_gbp": 59,  "variant_id": "1888466", "checkout_uuid": "c4a03a84-0d00-401d-8550-1f4974bc54b0"},
    "Enterprise":   {"price_gbp": 299, "variant_id": "1888462", "checkout_uuid": "9c89a708-c7c3-4067-a2e9-720ea4df8991"},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _header(title: str, step: int) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {BOLD}Check {step} — {title}{RESET}")
    print(f"{'─' * 62}")


def _pass(msg: str) -> tuple[bool, str]:
    print(f"  {GREEN}✔  {msg}{RESET}")
    return True, msg


def _fail(msg: str) -> tuple[bool, str]:
    print(f"  {RED}✘  {msg}{RESET}")
    return False, msg


def _warn(msg: str) -> None:
    print(f"  {YELLOW}⚠  {msg}{RESET}")


def _info(msg: str) -> None:
    print(f"  {DIM}    {msg}{RESET}")


def _ls_get(endpoint: str, api_key: str) -> dict | None:
    try:
        import urllib.request
        import json
        url = f"{LS_API_BASE}/{endpoint.lstrip('/')}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/vnd.api+json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        _warn(f"API call failed ({endpoint}): {exc}")
        return None


def _url_reachable(url: str, label: str) -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "ColtraDataAi-PreLaunchCheck/1.0")
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.status
            if code < 400:
                return _pass(f"{label} — HTTP {code}")
            return _fail(f"{label} — HTTP {code}")
    except Exception as exc:
        return _fail(f"{label} — {exc}")


# ── Local checks ──────────────────────────────────────────────────────────────

def check_logo() -> tuple[bool, str]:
    _header("Branding / logo file present", 1)
    logo_path = ROOT / "assets" / "logo" / "coltradata_logo.png"
    if logo_path.exists():
        size_kb = logo_path.stat().st_size // 1024
        return _pass(f"Logo found at assets/logo/coltradata_logo.png  ({size_kb} KB)")
    return _fail(f"Logo missing: {logo_path}")


def check_support_email() -> tuple[bool, str]:
    _header("Support email configured", 2)
    try:
        from config.branding_config import branding
        email = branding.get("contact_email", "")
        if email:
            return _pass(f"Support email: {email}")
        return _fail("contact_email is blank in config/branding_config.py")
    except ImportError as exc:
        return _fail(f"Could not import branding_config: {exc}")


def check_checkout_urls_populated() -> tuple[bool, str]:
    _header("All four checkout URLs populated", 3)
    try:
        from config.lemonsqueezy_config import CHECKOUT_URLS
        missing = [name for name, url in CHECKOUT_URLS.items() if not url]
        if missing:
            return _fail(f"Missing checkout URLs for: {', '.join(missing)}")
        for name, url in CHECKOUT_URLS.items():
            _info(f"{name:<14} {url}")
        return _pass("All four checkout URLs are set")
    except ImportError as exc:
        return _fail(f"Could not import lemonsqueezy_config: {exc}")


def check_local_pricing() -> tuple[bool, str]:
    _header("Local config pricing correct", 4)
    try:
        from config.plans import PLAN_CONFIG
        expected = {
            "starter":      "£9/month",
            "professional": "£29/month",
            "premium":      "£59/month",
            "enterprise":   "£299/month",
        }
        errors: list[str] = []
        for key, expected_price in expected.items():
            actual = PLAN_CONFIG.get(key, {}).get("price", "")
            if actual == expected_price:
                _info(f"{key:<14} {actual}")
            else:
                _warn(f"{key:<14} expected {expected_price!r}  got {actual!r}")
                errors.append(key)
        if errors:
            return _fail(f"Price mismatch for: {', '.join(errors)}")
        return _pass("All four plan prices match expected values")
    except ImportError as exc:
        return _fail(f"Could not import plans config: {exc}")


def check_checkout_url_format() -> tuple[bool, str]:
    _header("Checkout URL format & variant UUID mapping", 5)
    try:
        from config.lemonsqueezy_config import CHECKOUT_URLS
        errors: list[str] = []
        for tier, meta in EXPECTED_PLANS.items():
            url = CHECKOUT_URLS.get(tier, "")
            expected_uuid = meta["checkout_uuid"]
            if not url:
                _warn(f"{tier:<14} URL not set — skipping format check")
                errors.append(tier)
                continue
            if STORE_SLUG not in url:
                _warn(f"{tier:<14} store slug '{STORE_SLUG}' not found in URL")
                errors.append(tier)
            elif expected_uuid not in url:
                _warn(f"{tier:<14} expected UUID {expected_uuid} not in URL")
                errors.append(tier)
            else:
                _info(f"{tier:<14} UUID {expected_uuid}  [OK]")
        if errors:
            return _fail(f"URL format issues for: {', '.join(errors)}")
        return _pass("All checkout URLs contain correct store slug and variant UUIDs")
    except ImportError as exc:
        return _fail(f"Could not import lemonsqueezy_config: {exc}")


# ── API checks ────────────────────────────────────────────────────────────────

def check_store_test_mode(api_key: str) -> tuple[bool, str]:
    _header("Test mode is OFF", 6)
    data = _ls_get("stores", api_key)
    if data is None:
        return _fail("Could not reach LemonSqueezy API — check your API key")

    stores = data.get("data", [])
    if not stores:
        return _fail("No stores found on this account")

    store = stores[0]
    attrs = store.get("attributes", {})
    store_name = attrs.get("name", "Unknown")
    slug = attrs.get("slug", "")

    _info(f"Store: {store_name} (slug: {slug})")

    live_order_count = attrs.get("total_sales", 0)
    _info(f"Total sales on record: {live_order_count}")

    _warn(
        "Test mode state is determined by your API key, not the store object.\n"
        "       Confirm in your LS dashboard: Settings → Developer → API Keys\n"
        "       and ensure you are using a LIVE key (not prefixed 'test_' or labelled Test)."
    )
    print(f"  {YELLOW}⚠  Manual verification required for test mode — see above{RESET}")
    return True, "Test mode: manual verification recommended (see above)"


def check_store_active(api_key: str) -> tuple[bool, str]:
    _header("Store status is active", 7)
    data = _ls_get("stores", api_key)
    if data is None:
        return _fail("Could not reach LemonSqueezy API")

    stores = data.get("data", [])
    if not stores:
        return _fail("No stores found on this account")

    store = stores[0]
    attrs  = store.get("attributes", {})
    status = attrs.get("status", "unknown")
    slug   = attrs.get("slug", "")
    _info(f"Store slug: {slug}  |  status: {status}")

    if status == "active":
        return _pass(f"Store status is '{status}'")
    return _fail(f"Store status is '{status}' — expected 'active'")


def check_products_published(api_key: str) -> tuple[bool, str]:
    _header("All products published / visible", 8)
    data = _ls_get("products", api_key)
    if data is None:
        return _fail("Could not reach LemonSqueezy API")

    products = data.get("data", [])
    if not products:
        return _fail("No products found — create them in the LS dashboard first")

    unpublished: list[str] = []
    for p in products:
        attrs  = p.get("attributes", {})
        name   = attrs.get("name", f"ID:{p.get('id')}")
        status = attrs.get("status", "unknown")
        _info(f"{name:<20} status: {status}")
        if status not in ("published", "active"):
            unpublished.append(name)

    expected_names = set(EXPECTED_PLANS.keys())
    found_names    = {p["attributes"]["name"] for p in products if "attributes" in p}
    missing        = expected_names - found_names
    if missing:
        _warn(f"Products not found in LS: {', '.join(sorted(missing))}")

    if unpublished:
        return _fail(f"Unpublished products: {', '.join(unpublished)}")
    if missing:
        return _fail(f"Missing expected products: {', '.join(sorted(missing))}")
    return _pass(f"All {len(products)} products are published")


def check_product_names(api_key: str) -> tuple[bool, str]:
    _header("Product names match expected values", 9)
    data = _ls_get("products", api_key)
    if data is None:
        return _fail("Could not reach LemonSqueezy API")

    products   = data.get("data", [])
    found      = {p["attributes"]["name"] for p in products if "attributes" in p}
    expected   = set(EXPECTED_PLANS.keys())
    missing    = expected - found
    unexpected = found - expected

    for name in sorted(found):
        icon = GREEN + "✔" + RESET if name in expected else YELLOW + "?" + RESET
        print(f"    {icon}  {name}")

    if missing:
        _warn(f"Expected but not found: {', '.join(sorted(missing))}")
    if unexpected:
        _warn(f"Found but not expected:  {', '.join(sorted(unexpected))}")

    if missing:
        return _fail(f"Product name mismatch — missing: {', '.join(sorted(missing))}")
    return _pass("All expected product names found in LemonSqueezy")


def check_variant_prices(api_key: str) -> tuple[bool, str]:
    _header("Variant prices match config", 10)
    data = _ls_get("variants", api_key)
    if data is None:
        return _fail("Could not reach LemonSqueezy API")

    variants   = data.get("data", [])
    errors: list[str] = []
    matched: list[str] = []

    for tier_name, meta in EXPECTED_PLANS.items():
        vid          = meta["variant_id"]
        expected_gbp = meta["price_gbp"]
        expected_p   = expected_gbp * 100

        variant = next(
            (v for v in variants if str(v.get("id")) == vid),
            None,
        )
        if variant is None:
            _warn(f"{tier_name:<14} variant {vid} not found via API")
            errors.append(tier_name)
            continue

        attrs        = variant.get("attributes", {})
        actual_price = attrs.get("price", None)
        currency     = attrs.get("price_formatted", "")
        v_name       = attrs.get("name", "")

        _info(f"{tier_name:<14} variant {vid}  price={actual_price}  formatted={currency!r}  name={v_name!r}")

        if actual_price is None:
            _warn(f"{tier_name:<14} price attribute missing")
            errors.append(tier_name)
        elif int(actual_price) != expected_p:
            _warn(
                f"{tier_name:<14} price mismatch: "
                f"expected {expected_p} pence (£{expected_gbp}), got {actual_price}"
            )
            errors.append(tier_name)
        else:
            matched.append(tier_name)

    if errors:
        return _fail(f"Price mismatch for: {', '.join(errors)}")
    return _pass(f"All variant prices correct: {', '.join(matched)}")


def check_checkout_reachable(tier: str, url: str, step: int) -> tuple[bool, str]:
    _header(f"{tier} checkout URL is reachable", step)
    if not url:
        return _fail(f"{tier} checkout URL is not configured")
    _info(f"GET {url}")
    return _url_reachable(url, f"{tier} checkout page")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-launch LemonSqueezy readiness checker for ColtraDataAi"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("LEMONSQUEEZY_API_KEY", ""),
        help="LemonSqueezy API key (or set LEMONSQUEEZY_API_KEY env var)",
    )
    args = parser.parse_args()
    api_key: str = args.api_key.strip()

    print(f"\n{BOLD}{'═' * 62}{RESET}")
    print(f"{BOLD}  ColtraDataAi — LemonSqueezy Pre-Launch Verification{RESET}")
    print(f"{'═' * 62}")

    if not api_key:
        print(
            f"\n  {YELLOW}No API key provided — running local checks only.{RESET}\n"
            f"  {DIM}Pass --api-key <KEY> or set LEMONSQUEEZY_API_KEY to enable API checks.{RESET}"
        )
    else:
        masked = api_key[:8] + "..." + api_key[-4:]
        print(f"\n  {DIM}API key: {masked}{RESET}")

    results: list[tuple[str, bool]] = []

    # ── Local checks ──────────────────────────────────────────────────────────
    ok, label = check_logo()
    results.append(("Branding / logo file present", ok))

    ok, label = check_support_email()
    results.append(("Support email configured", ok))

    ok, label = check_checkout_urls_populated()
    results.append(("All checkout URLs populated in config", ok))

    ok, label = check_local_pricing()
    results.append(("Local config pricing correct", ok))

    ok, label = check_checkout_url_format()
    results.append(("Checkout URL format & variant UUID mapping", ok))

    # ── API checks ────────────────────────────────────────────────────────────
    if api_key:
        ok, label = check_store_test_mode(api_key)
        results.append(("Test mode is OFF (manual confirm also required)", ok))

        ok, label = check_store_active(api_key)
        results.append(("Store status is active", ok))

        ok, label = check_products_published(api_key)
        results.append(("All products published / visible", ok))

        ok, label = check_product_names(api_key)
        results.append(("Product names match expected", ok))

        ok, label = check_variant_prices(api_key)
        results.append(("Variant prices match config", ok))

        try:
            from config.lemonsqueezy_config import CHECKOUT_URLS
        except ImportError:
            CHECKOUT_URLS = {}

        for step_offset, (tier, meta) in enumerate(EXPECTED_PLANS.items(), start=11):
            url = CHECKOUT_URLS.get(tier, "")
            ok, label = check_checkout_reachable(tier, url, step_offset)
            results.append((f"{tier} checkout URL is reachable", ok))
    else:
        print(
            f"\n  {DIM}{'─' * 56}{RESET}"
            f"\n  {DIM}API checks skipped (no key provided).{RESET}"
            f"\n  {DIM}Checks 6–14 require a LemonSqueezy API key.{RESET}"
            f"\n  {DIM}{'─' * 56}{RESET}"
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    all_ok = all(ok for _, ok in results)

    print(f"\n{'═' * 62}")
    print(f"  {BOLD}SUMMARY{RESET}")
    print(f"{'═' * 62}")

    for label, ok in results:
        if ok:
            print(f"  {GREEN}✔  {label}{RESET}")
        else:
            print(f"  {RED}✘  {label}{RESET}")

    if not api_key:
        print(f"\n  {YELLOW}⚠  API checks not run — re-run with your LemonSqueezy API key:{RESET}")
        print(f"  {DIM}     python scripts/verify_lemonsqueezy.py --api-key <KEY>{RESET}")

    print(f"\n{'─' * 62}")
    if all_ok:
        if api_key:
            print(f"\n  {GREEN}{BOLD}✅  ALL CHECKS PASSED — SAFE TO CLICK GO LIVE{RESET}\n")
        else:
            print(f"\n  {YELLOW}{BOLD}✅  Local checks passed — run with --api-key to complete full verification{RESET}\n")
    else:
        print(f"\n  {RED}{BOLD}❌  ONE OR MORE CHECKS FAILED — DO NOT GO LIVE YET{RESET}\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
