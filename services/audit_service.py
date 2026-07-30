"""Cleaning run audit trail for ColtraDataAi.

Writes one record to cleaning_audit per completed cleaning run.
The table must exist before this is used — run
database/cleaning_audit_migration.sql in the Supabase SQL editor once.

All errors are logged and swallowed so that a DB hiccup never interrupts
a user's cleaning session.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from services.licence_manager_pg import _conn

log = logging.getLogger(__name__)


def log_cleaning_run(
    *,
    email: str,
    plan: str,
    dataset_type: str,
    rows_in: int,
    rows_out: int,
    cols_in: int,
    cols_out: int,
    completeness_pct: Optional[float],
    issues_found: int = 0,
    steps_log: Optional[list] = None,
) -> None:
    """Insert one audit record for a completed cleaning run.

    Never raises — all exceptions are caught and logged at WARNING level so
    that a database error does not interrupt the user's session.
    """
    try:
        with _conn() as cur:
            cur.execute(
                """
                INSERT INTO cleaning_audit
                    (email, plan, dataset_type,
                     rows_in, rows_out, cols_in, cols_out,
                     completeness_pct, issues_found, steps_log)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    email.lower().strip(),
                    plan,
                    dataset_type,
                    rows_in,
                    rows_out,
                    cols_in,
                    cols_out,
                    round(completeness_pct, 2) if completeness_pct is not None else None,
                    issues_found,
                    json.dumps(steps_log or []),
                ),
            )
    except Exception:
        log.warning(
            "audit_service.log_cleaning_run: could not write audit row for email=%s",
            email,
            exc_info=True,
        )
