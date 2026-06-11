"""xlsxwriter format factory for ColtraDataAi Excel reports.

All format definitions are centralised here so ``report_builder.py`` can
reference them by name.  Call ``create_all_formats(workbook, branding)``
to get a dict of ready-to-use format objects.
"""
from __future__ import annotations

from typing import Dict


def create_all_formats(workbook, branding: dict) -> Dict:
    """
    Create every named xlsxwriter format used across the workbook.

    Returns a dict keyed by format name so callers can do::

        fmts = create_all_formats(workbook, branding)
        worksheet.write("A1", "Title", fmts["title"])
    """
    p  = branding["primary_colour"]
    s  = branding["secondary_colour"]
    n  = branding["neutral_fill"]
    ok = branding["success_colour"]
    wa = branding["warning_colour"]
    er = branding["danger_colour"]

    return {
        "title": workbook.add_format({
            "bold": True, "font_size": 20,
            "font_color": p, "align": "left", "valign": "vcenter",
        }),
        "subtitle": workbook.add_format({
            "font_size": 11, "font_color": "#444444", "italic": True,
        }),
        "section_header": workbook.add_format({
            "bold": True, "font_size": 12, "font_color": "white",
            "bg_color": p, "border": 1, "align": "left", "valign": "vcenter",
        }),
        "table_header": workbook.add_format({
            "bold": True, "bg_color": s, "font_color": p,
            "border": 1, "text_wrap": True,
        }),
        "body": workbook.add_format({
            "border": 1, "valign": "top",
        }),
        "note": workbook.add_format({
            "font_size": 10, "font_color": "#555555", "italic": True, "text_wrap": True,
        }),
        "metric_label": workbook.add_format({
            "bold": True, "bg_color": n, "border": 1,
        }),
        "metric_value": workbook.add_format({
            "bold": True, "font_color": p, "border": 1,
        }),
        "success": workbook.add_format({
            "bold": True, "font_color": "white", "bg_color": ok,
            "align": "center", "border": 1,
        }),
        "warning": workbook.add_format({
            "bold": True, "font_color": "black", "bg_color": wa,
            "align": "center", "border": 1,
        }),
        "danger": workbook.add_format({
            "bold": True, "font_color": "white", "bg_color": er,
            "align": "center", "border": 1,
        }),
        "disclaimer": workbook.add_format({
            "font_size": 9, "italic": True, "font_color": "#666666", "text_wrap": True,
        }),
        "blank_highlight": workbook.add_format({
            "bg_color": "#FFF2CC",
        }),
        "toc_link": workbook.add_format({
            "bold": True, "bg_color": n, "font_color": p,
            "border": 1, "underline": True,
        }),
    }
