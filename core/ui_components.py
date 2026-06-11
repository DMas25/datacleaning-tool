"""Backward-compatibility shim for core.ui_components.

The canonical implementations live in ``ui.branding_components``.
Any existing code that imports from ``core.ui_components`` will
continue to work without changes.
"""
from ui.branding_components import (   # noqa: F401
    inject_app_css,
    render_step_header,
    render_kpi_row,
    render_risk_kpi,
    render_section_divider,
    render_chart_section_header,
)
