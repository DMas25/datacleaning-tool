#!/usr/bin/env python3
"""
synthetic_tests.py — Synthetic pipeline tests for ColtraDataAi pre-deploy validation.

Four test suites callable from predeploy_check.py --full:

    run_user_flow_test()     — upload → clean → export pipeline       (HARD GATE)
    run_edge_case_tests()    — empty / null / mixed-type / stress      (HARD GATE)
    run_benchmark_test()     — throughput + regression tracking        (advisory)
    run_staging_validation() — API reachability + secrets + config     (advisory)

Each function returns True on pass, False on fail, and prints its own output.
"""
from __future__ import annotations

import datetime
import io
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── ANSI colours ───────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ── Benchmark config ───────────────────────────────────────────────────────────
ARTIFACTS_DIR              = ROOT / "artifacts"
BENCHMARK_HISTORY_FILE     = ARTIFACTS_DIR / "benchmark_history.json"
BENCHMARK_ROWS             = 50_000
BENCHMARK_MIN_RPS          = 5_000   # rows/sec — first-run baseline warning
BENCHMARK_WARN_DROP_PCT    = 20      # % slower than last run → ⚠  WARNING
BENCHMARK_FAIL_DROP_PCT    = 40      # % slower than last run → potential FAIL
BENCHMARK_FAIL_ON_REGRESSION = False # set True to hard-fail on >40% regression

# ── Staging config ─────────────────────────────────────────────────────────────
STAGING_TIMEOUT  = 5
REQUIRED_SECRETS = ["ANTHROPIC_API_KEY", "LEMON_SQUEEZY_API_KEY"]


# ── Benchmark history helpers ──────────────────────────────────────────────────

def _load_benchmark_history() -> list[dict]:
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    if BENCHMARK_HISTORY_FILE.exists():
        try:
            return json.loads(BENCHMARK_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_benchmark_history(history: list[dict]) -> None:
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    BENCHMARK_HISTORY_FILE.write_text(
        json.dumps(history, indent=2, default=str), encoding="utf-8"
    )


# ── 1. Synthetic user flow: upload → clean → export ────────────────────────────

def run_user_flow_test() -> bool:
    """
    HARD GATE — product guarantee test.

    Validates the full upload → clean → export pipeline end-to-end without
    Streamlit.  If this test fails, the core promise of ColtraDataAi is broken:
    "If a user uploads messy data, the cleaning pipeline will fix it correctly."

    Fixture design (7 rows, 4 real-world quality issues):
      - Sentinels:   "UNKNOWN", "ERROR" → NaN  (step 4, sentinel normalisation)
      - Whitespace:  "  Alice  " → "Alice"     (step 3, whitespace trimming)
      - Duplicates:  rows 0+4 (Alice), 1+5 (Bob), 3+6 (Dave) are exact pairs
                     after trimming/normalisation — dedup removes 3 rows
      - Nulls:       None in email column       (step 9, null handling)

    Duplicate fixture rule: both copies of a row must be IDENTICAL after
    trimming and sentinel normalisation — differing amounts (e.g. 100 vs 150)
    are NOT duplicates and will not be removed.

    Five assertions (hard gate — any failure returns False):
      i)   7 rows in → 4 rows out          (duplicates removed)
      ii)  9 cleaning steps logged          (full pipeline executed)
      iii) headers normalised               (lowercase, underscores, no spaces)
      iv)  CSV export works                 (in-memory, > 0 bytes)
      v)   Excel export works               (openpyxl, > 0 bytes)

    file_loader.load_file() is intentionally bypassed — it requires a
    Streamlit UploadedFile object and calls st.stop() on error.
    """
    def _check(label: str, condition: bool, detail: str = "") -> bool:
        if condition:
            print(f"  {GREEN}✔  {label}{RESET}")
        else:
            suffix = f": {detail}" if detail else ""
            print(f"  {RED}✘  {label}{suffix}{RESET}")
        return condition

    passed = True

    try:
        import pandas as pd
        from core.cleaner import apply_cleaning, CleaningOptions
        from core.profiler import profile_dataframe

        # ── Fixture ────────────────────────────────────────────────────────────
        #
        #   Row  Customer Name   amount    email                  region
        #   0    "  Alice  "     "100"     alice@test.com         North  ← dup of 4
        #   1    "Bob"           "UNKNOWN" None                   South  ← dup of 5
        #   2    "Charlie"       "ERROR"   charlie@test.com       East   (unique)
        #   3    "  Dave  "      "300"     dave@test.com          West   ← dup of 6
        #   4    "  Alice  "     "100"     alice@test.com         North  ← dup of 0
        #   5    "Bob"           "UNKNOWN" None                   South  ← dup of 1
        #   6    "  Dave  "      "300"     dave@test.com          West   ← dup of 3
        #
        raw = pd.DataFrame({
            "Customer Name": [
                "  Alice  ", "Bob",       "Charlie",          "  Dave  ",
                "  Alice  ", "Bob",       "  Dave  ",
            ],
            "amount": [
                "100",       "UNKNOWN",   "ERROR",            "300",
                "100",       "UNKNOWN",   "300",
            ],
            "email": [
                "alice@test.com", None,   "charlie@test.com", "dave@test.com",
                "alice@test.com", None,   "dave@test.com",
            ],
            "region": [
                "North",     "South",     "East",             "West",
                "North",     "South",     "West",
            ],
        })

        EXPECTED_ROWS_IN  = 7
        EXPECTED_ROWS_OUT = 4
        EXPECTED_STEPS    = 9

        raw_profile = profile_dataframe(raw)
        print(
            f"\n  {DIM}  Fixture: {len(raw)} rows  |  "
            f"{raw_profile['duplicate_total']} raw dupes  |  "
            f"{raw_profile['missing_total']} nulls  |  "
            f"sentinels: UNKNOWN, ERROR{RESET}"
        )

        options = CleaningOptions(
            remove_duplicates=True,
            trim_whitespace=True,
            standardise_headers=True,
            null_handling="Fill with placeholder",
        )
        result  = apply_cleaning(raw, options)
        cleaned = result.cleaned_df

        rows_ok = (len(raw) == EXPECTED_ROWS_IN) and (len(cleaned) == EXPECTED_ROWS_OUT)
        passed &= _check(
            f"i)   {EXPECTED_ROWS_IN} rows in → {EXPECTED_ROWS_OUT} rows out"
            f"  (got {len(raw)} → {len(cleaned)})",
            rows_ok,
            f"Expected {EXPECTED_ROWS_IN} → {EXPECTED_ROWS_OUT}, got {len(raw)} → {len(cleaned)}",
        )

        steps_count = len(result.steps_taken)
        passed &= _check(
            f"ii)  {EXPECTED_STEPS} cleaning steps logged  (got {steps_count})",
            steps_count == EXPECTED_STEPS,
            f"Expected {EXPECTED_STEPS} steps, got {steps_count}",
        )

        bad_headers = [c for c in cleaned.columns if c != c.lower() or " " in c]
        passed &= _check(
            f"iii) Headers normalised  ({', '.join(cleaned.columns)})",
            len(bad_headers) == 0,
            f"Non-normalised: {bad_headers}",
        )

        csv_buf   = io.StringIO()
        cleaned.to_csv(csv_buf, index=False)
        csv_bytes = len(csv_buf.getvalue().encode())
        passed &= _check(f"iv)  CSV export  ({csv_bytes:,} bytes)", csv_bytes > 0)

        xlsx_buf   = io.BytesIO()
        cleaned.to_excel(xlsx_buf, index=False, engine="openpyxl")
        xlsx_bytes = xlsx_buf.tell()
        passed &= _check(f"v)   Excel export  ({xlsx_bytes:,} bytes)", xlsx_bytes > 0)

        return passed

    except ImportError as exc:
        print(f"  {RED}✘  Import error: {exc}{RESET}")
        return False
    except Exception as exc:
        print(f"  {RED}✘  User flow test error: {exc}{RESET}")
        return False


# ── 2. Edge-case test suite ─────────────────────────────────────────────────────

def run_edge_case_tests() -> bool:
    """
    HARD GATE — boundary condition validation suite.

    Ensures the cleaning pipeline does not crash, corrupt output, or silently
    misbehave when users upload edge-case datasets that occur in production.

    Five sub-tests (A–E):

      A) Empty dataset         — 0 rows in; 0 rows out; steps still logged
      B) Single row            — 1 row in; 1 row out; no unwanted deletion
      C) All-null dataset      — all values None; no crash; output ≤ input rows
      D) Mixed data types      — str/int/float/Timestamp/bool in same column
      E) Large stress sample   — 100,000 rows; no crash; pipeline completes

    Each sub-test asserts:
      • Pipeline completes without exception
      • Output row count within expected bounds
      • 9 cleaning steps logged
      • CSV export produces non-empty output
      • Excel export produces non-empty output  (A–D only; skipped for E)

    Any sub-test failure returns False immediately — this is a hard gate.
    """
    try:
        import numpy as np
        import pandas as pd
        from core.cleaner import apply_cleaning, CleaningOptions
    except ImportError as exc:
        print(f"  {RED}✘  Import error: {exc}{RESET}")
        return False

    options = CleaningOptions(
        remove_duplicates=True,
        trim_whitespace=True,
        standardise_headers=True,
        null_handling="Fill with placeholder",
    )

    sub_results: list[tuple[str, bool]] = []

    def _case(
        label: str,
        df: "pd.DataFrame",
        *,
        min_out: int = 0,
        max_out: int | None = None,
        excel: bool = True,
    ) -> None:
        """
        Run one sub-test.  Appends (label, ok) to sub_results.

        min_out / max_out: inclusive bounds on accepted output row count.
        excel:             set False to skip Excel export (e.g. very large datasets).
        """
        case_ok = True
        failures: list[str] = []
        try:
            result  = apply_cleaning(df, options)
            cleaned = result.cleaned_df

            n_in  = len(df)
            n_out = len(cleaned)

            # Row count
            rows_ok = n_out >= min_out and (max_out is None or n_out <= max_out)
            if not rows_ok:
                bound = f"{min_out}–{max_out}" if max_out is not None else f"≥{min_out}"
                failures.append(f"rows {n_in}→{n_out} (expected {bound})")
                case_ok = False

            # Step count
            if len(result.steps_taken) != 9:
                failures.append(f"{len(result.steps_taken)}/9 steps")
                case_ok = False

            # CSV export
            csv_buf = io.StringIO()
            cleaned.to_csv(csv_buf, index=False)
            if len(csv_buf.getvalue().encode()) == 0:
                failures.append("CSV empty")
                case_ok = False

            # Excel export (optional)
            if excel:
                xlsx_buf = io.BytesIO()
                cleaned.to_excel(xlsx_buf, index=False, engine="openpyxl")
                if xlsx_buf.tell() == 0:
                    failures.append("Excel empty")
                    case_ok = False

            detail = f"{n_in}→{n_out} rows" + (
                f"  |  ❌ {', '.join(failures)}" if failures else ""
            )
            colour = GREEN if case_ok else RED
            icon   = "✔" if case_ok else "✘"
            print(f"  {colour}{icon}  {label}  [{detail}]{RESET}")

        except Exception as exc:
            print(f"  {RED}✘  {label}  →  CRASH: {exc}{RESET}")
            case_ok = False

        sub_results.append((label, case_ok))

    # ── A: Empty dataset ────────────────────────────────────────────────────────
    _case(
        "A) Empty dataset",
        pd.DataFrame(columns=["name", "value", "region"]),
        min_out=0, max_out=0,
    )

    # ── B: Single row ───────────────────────────────────────────────────────────
    _case(
        "B) Single row",
        pd.DataFrame({"name": ["Alice"], "value": ["100"], "region": ["North"]}),
        min_out=1, max_out=1,
    )

    # ── C: All-null dataset ─────────────────────────────────────────────────────
    # pandas drop_duplicates treats NaN==NaN for dedup, so 3 all-null rows
    # collapse to 1; null_handling fills remaining NaN with "MISSING".
    _case(
        "C) All-null dataset",
        pd.DataFrame({"name": [None] * 3, "value": [None] * 3, "region": [None] * 3}),
        min_out=0, max_out=3,
    )

    # ── D: Mixed data types ─────────────────────────────────────────────────────
    # str/int/float/Timestamp/bool all in the same column.
    # Whitespace trim uses isinstance(x, str) guard; sentinel normalisation
    # matches strings only; numeric coercion targets named columns not present
    # here.  Pipeline must complete without crashing.
    _case(
        "D) Mixed data types  (str / int / float / Timestamp / bool)",
        pd.DataFrame({
            "name":   ["Alice", 42, 3.14, pd.Timestamp("2024-01-01"), True],
            "value":  [1, "two", 3.0, None, "ERROR"],
            "region": ["North", "South", 99, "East", None],
        }),
        min_out=0,
    )

    # ── E: Large stress sample ──────────────────────────────────────────────────
    # 100k rows; Excel skipped (openpyxl for 100k rows adds ~15s to the check).
    n   = 100_000
    rng = np.random.default_rng(0)
    _case(
        f"E) Large stress sample  ({n:,} rows)",
        pd.DataFrame({
            "name":   [f"User_{i}" for i in range(n)],
            "value":  rng.choice(["100", "200", "UNKNOWN"], n).tolist(),
            "region": rng.choice(["North", "South", "East", "West"], n).tolist(),
        }),
        min_out=1,
        excel=False,
    )

    suite_ok = all(ok for _, ok in sub_results)
    failed   = [lbl for lbl, ok in sub_results if not ok]

    print()
    if suite_ok:
        print(f"  {GREEN}{BOLD}✅  All {len(sub_results)} edge-case tests passed{RESET}")
    else:
        print(
            f"  {RED}{BOLD}✘  {len(failed)}/{len(sub_results)} edge-case tests failed:"
            f"  {', '.join(failed)}{RESET}"
        )
    return suite_ok


# ── 3. Benchmark: throughput + regression tracking ─────────────────────────────

def run_benchmark_test() -> bool:
    """
    Generate BENCHMARK_ROWS-row synthetic dataset, time apply_cleaning(),
    persist the result, and compare against the previous run.

    History file: artifacts/benchmark_history.json
    Each entry stores: timestamp, rows_processed, time_taken, rows_per_sec

    Regression thresholds (configurable at module level):
      > BENCHMARK_WARN_DROP_PCT  (20%) slower than last run → ⚠  WARNING
      > BENCHMARK_FAIL_DROP_PCT  (40%) slower than last run → ⚠  or ❌ FAIL
        (hard-fail only when BENCHMARK_FAIL_ON_REGRESSION = True)

    Always advisory by default — returns True unless BENCHMARK_FAIL_ON_REGRESSION
    is True and the regression exceeds BENCHMARK_FAIL_DROP_PCT.
    """
    try:
        import numpy as np
        import pandas as pd
        from core.cleaner import apply_cleaning, CleaningOptions

        rng = np.random.default_rng(42)
        n   = BENCHMARK_ROWS

        base = pd.DataFrame({
            "name":   [f"Customer_{i}" for i in range(n)],
            "amount": rng.choice(
                ["100", "UNKNOWN", "200", "ERROR", "150", "300"], n
            ).tolist(),
            "region": rng.choice(["North", "South", "East", "West"], n).tolist(),
            "email":  [
                f"user{i}@test.com" if i % 10 != 0 else None for i in range(n)
            ],
        })
        dupes = base.sample(n // 10, random_state=42)
        df    = pd.concat([base, dupes], ignore_index=True)
        total = len(df)

        options = CleaningOptions(
            remove_duplicates=True,
            trim_whitespace=True,
            standardise_headers=True,
        )

        t0      = time.perf_counter()
        apply_cleaning(df, options)
        elapsed = time.perf_counter() - t0
        rps     = total / elapsed

        # ── Absolute throughput ────────────────────────────────────────────────
        if rps >= BENCHMARK_MIN_RPS:
            print(
                f"  {GREEN}✔  {total:,} rows in {elapsed:.2f}s"
                f"  →  {rps:,.0f} rows/sec"
                f"  (baseline: ≥{BENCHMARK_MIN_RPS:,}){RESET}"
            )
        else:
            print(
                f"  {YELLOW}⚠  {total:,} rows in {elapsed:.2f}s"
                f"  →  {rps:,.0f} rows/sec"
                f"  (below baseline: {BENCHMARK_MIN_RPS:,}){RESET}"
            )

        # ── Regression check against history ──────────────────────────────────
        history   = _load_benchmark_history()
        hard_fail = False

        if history:
            prev     = history[-1]
            prev_rps = float(prev["rows_per_sec"])
            prev_ts  = prev.get("timestamp", "?")[:19]   # trim microseconds

            if prev_rps > 0:
                drop_pct = ((prev_rps - rps) / prev_rps) * 100

                if drop_pct > BENCHMARK_FAIL_DROP_PCT:
                    colour = RED if BENCHMARK_FAIL_ON_REGRESSION else YELLOW
                    print(f"  {colour}⚠  Benchmark regression detected:{RESET}")
                    print(f"  {colour}   Previous ({prev_ts}): {prev_rps:,.0f} rows/sec{RESET}")
                    print(f"  {colour}   Current:              {rps:,.0f} rows/sec"
                          f"  ({drop_pct:.1f}% slower){RESET}")
                    if BENCHMARK_FAIL_ON_REGRESSION:
                        print(
                            f"  {RED}   BENCHMARK_FAIL_ON_REGRESSION=True"
                            f" — marking as failure{RESET}"
                        )
                        hard_fail = True

                elif drop_pct > BENCHMARK_WARN_DROP_PCT:
                    print(f"  {YELLOW}⚠  Benchmark regression detected:{RESET}")
                    print(f"  {YELLOW}   Previous ({prev_ts}): {prev_rps:,.0f} rows/sec{RESET}")
                    print(f"  {YELLOW}   Current:              {rps:,.0f} rows/sec"
                          f"  ({drop_pct:.1f}% slower){RESET}")

                elif drop_pct < 0:
                    print(
                        f"  {GREEN}✔  Benchmark improved vs last run"
                        f"  ({prev_rps:,.0f} → {rps:,.0f} rows/sec,"
                        f" {abs(drop_pct):.1f}% faster){RESET}"
                    )
                else:
                    print(
                        f"  {GREEN}✔  Benchmark stable vs last run"
                        f"  ({prev_rps:,.0f} → {rps:,.0f} rows/sec,"
                        f" {drop_pct:.1f}% change){RESET}"
                    )
        else:
            print(f"  {DIM}  First run — establishing baseline in history{RESET}")

        # ── Persist ───────────────────────────────────────────────────────────
        history.append({
            "timestamp":      datetime.datetime.now().isoformat(),
            "rows_processed": total,
            "time_taken":     round(elapsed, 3),
            "rows_per_sec":   round(rps, 0),
        })
        _save_benchmark_history(history)
        print(
            f"  {DIM}  History: {len(history)} run(s) recorded"
            f" → {BENCHMARK_HISTORY_FILE.relative_to(ROOT)}{RESET}"
        )

        return not hard_fail

    except ImportError as exc:
        print(f"  {RED}✘  Import error during benchmark: {exc}{RESET}")
        return False
    except Exception as exc:
        print(f"  {RED}✘  Benchmark error: {exc}{RESET}")
        return False


# ── 4. Staging environment validation ──────────────────────────────────────────

def run_staging_validation() -> bool:
    """
    Advisory — external API reachability + secrets presence + config sanity.

    Sections:
      A) Python version label
      B) External service reachability — HEAD probes to Anthropic + Lemon Squeezy
         (any HTTP < 500 = reachable; 401/403 without credentials is expected)
      C) Secrets validation — checks REQUIRED_SECRETS are present in env
         (missing = ⚠ WARNING, not failure — secrets live in Cloud Secrets panel)
      D) Config sanity — reads .streamlit/config.toml and checks for overrides
         that would break Streamlit Cloud (rogue port, headless=false)

    Always returns True — staging environment differences from a developer
    machine do not predict Cloud deployment behaviour.
    """
    # ── A: Python version ──────────────────────────────────────────────────────
    v      = sys.version_info
    py_str = f"{v.major}.{v.minor}.{v.micro}"
    if v >= (3, 14):
        print(
            f"  {GREEN}✔  Python {py_str}"
            f"  (matches Streamlit Cloud runtime — cp314 wheels required){RESET}"
        )
    else:
        print(
            f"  {DIM}ℹ  Python {py_str}"
            f"  (local dev runtime — Cloud runs Python 3.14){RESET}"
        )

    # ── B: External service reachability ───────────────────────────────────────
    endpoints = {
        "Anthropic API":     "https://api.anthropic.com",
        "Lemon Squeezy API": "https://api.lemonsqueezy.com",
    }
    try:
        import requests as _requests
        for label, url in endpoints.items():
            try:
                resp = _requests.head(url, timeout=STAGING_TIMEOUT, allow_redirects=True)
                if resp.status_code < 500:
                    print(f"  {GREEN}✔  {label}  →  HTTP {resp.status_code}{RESET}")
                else:
                    print(
                        f"  {YELLOW}⚠  {label}  →  HTTP {resp.status_code}"
                        f"  (server-side error){RESET}"
                    )
            except _requests.ConnectionError:
                print(f"  {YELLOW}⚠  {label}  →  connection refused / no route{RESET}")
            except _requests.Timeout:
                print(f"  {YELLOW}⚠  {label}  →  timed out after {STAGING_TIMEOUT}s{RESET}")
            except _requests.RequestException as exc:
                print(f"  {YELLOW}⚠  {label}  →  {exc}{RESET}")
    except ImportError:
        print(f"  {YELLOW}⚠  requests not available — API probes skipped{RESET}")

    # ── C: Secrets validation ──────────────────────────────────────────────────
    print()
    present = [s for s in REQUIRED_SECRETS if os.getenv(s)]
    missing = [s for s in REQUIRED_SECRETS if not os.getenv(s)]

    for s in present:
        print(f"  {GREEN}✔  Secret present: {s}{RESET}")
    for s in missing:
        print(
            f"  {YELLOW}⚠  Secret not set: {s}"
            f"  (expected on local dev — add to Streamlit Cloud Secrets panel){RESET}"
        )

    # ── D: Config sanity ───────────────────────────────────────────────────────
    print()
    config_path = ROOT / ".streamlit" / "config.toml"

    if not config_path.exists():
        print(f"  {DIM}ℹ  No .streamlit/config.toml — Streamlit defaults apply{RESET}")
    else:
        try:
            content = config_path.read_text(encoding="utf-8")

            # Port override: anything other than 8501 breaks Cloud health-checks
            port_m = re.search(r"^\s*port\s*=\s*(\d+)", content, re.MULTILINE)
            if port_m:
                port = int(port_m.group(1))
                if port != 8501:
                    print(
                        f"  {RED}⚠  config.toml: port = {port}"
                        f"  (Cloud health-check uses 8501 — this WILL break deploy){RESET}"
                    )
                else:
                    print(f"  {GREEN}✔  config.toml: port = 8501  (correct){RESET}")
            else:
                print(
                    f"  {GREEN}✔  config.toml: no port override"
                    f"  (Cloud default 8501 applies){RESET}"
                )

            # headless = false breaks Cloud (Cloud always runs headless)
            hl_m = re.search(
                r"^\s*headless\s*=\s*(true|false)", content,
                re.MULTILINE | re.IGNORECASE,
            )
            if hl_m:
                val = hl_m.group(1).lower()
                if val == "false":
                    print(
                        f"  {RED}⚠  config.toml: headless = false"
                        f"  (Cloud always runs headless — WILL break deploy){RESET}"
                    )
                else:
                    print(f"  {GREEN}✔  config.toml: headless = true  (correct){RESET}")
            else:
                print(f"  {DIM}ℹ  config.toml: headless not set  (Cloud default applies){RESET}")

        except Exception as exc:
            print(f"  {YELLOW}⚠  Could not read config.toml: {exc}{RESET}")

    return True   # advisory — always returns True
