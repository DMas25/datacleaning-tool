import os
import re
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable,
)

from core.chart_gallery import CHART_IMAGE_ASPECT
from core.advisory_text import parse_advisory_blocks, strip_residual_markdown, split_advisory_sections
from core.report_builder import ReportBuilder

RISK_COLOURS = {
    "High":   colors.HexColor("#DC2626"),
    "Medium": colors.HexColor("#D97706"),
    "Low":    colors.HexColor("#16A34A"),
}
RISK_BG = {
    "High":   colors.HexColor("#FEF2F2"),
    "Medium": colors.HexColor("#FFFBEB"),
    "Low":    colors.HexColor("#F0FDF4"),
}


def _draw_page_footer(canvas, doc, branding: dict) -> None:
    """Draws branded footer line and page number on every page."""
    canvas.saveState()
    page_w = doc.pagesize[0]
    footer_y = 12 * mm
    rule_y = 17 * mm

    # Thin divider rule
    canvas.setStrokeColor(colors.HexColor("#E6ECF0"))
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, rule_y, page_w - 20 * mm, rule_y)

    # Footer text — branding line left, page number right
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(colors.HexColor("#9CA3AF"))
    canvas.drawString(20 * mm, footer_y, branding.get("footer_line", branding["app_name"]))
    canvas.drawRightString(page_w - 20 * mm, footer_y, f"Page {doc.page}")
    canvas.restoreState()


def _escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline_markdown(text: str) -> str:
    """Escape XML, then convert **bold** markers to ReportLab <b> tags."""
    escaped = _escape_xml(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)


def _markdown_to_flowables(text: str, heading_style, bullet_style, body_style) -> list:
    """Claude's advisory markdown → ReportLab flowables.

    Structure (headings/bullets/body) comes from the shared advisory_text
    parser; inline **bold** is rendered as <b> tags and any residual markdown
    symbols (stray **, '') are scrubbed so they never reach the reader.
    """
    flowables: list = []
    for kind, content in parse_advisory_blocks(text):
        if kind == "heading":
            flowables.append(Paragraph(_escape_xml(content), heading_style))
        elif kind == "bullet":
            flowables.append(Paragraph(
                f"•&nbsp;&nbsp;{strip_residual_markdown(_inline_markdown(content))}", bullet_style,
            ))
        else:
            flowables.append(Paragraph(strip_residual_markdown(_inline_markdown(content)), body_style))
    return flowables


def build_pdf_report(
    branding: dict,
    raw_df, cleaned_df,
    risk_summary: dict,
    chart_assets,
    ai_advisory: str | None = None,
) -> bytes:
    """
    Builds a downloadable PDF executive summary: cover block, KPIs, data-quality
    risk mix, the same premium chart gallery shown on the live dashboard, and
    (when provided) the Claude-generated AI Advisory section.
    """
    buffer = BytesIO()
    primary      = colors.HexColor(branding["primary_colour"])
    accent       = colors.HexColor(branding.get("accent_colour", branding["primary_colour"]))
    neutral_fill = colors.HexColor(branding.get("neutral_fill", "#F4F6F8"))
    light_fill   = colors.HexColor(branding.get("light_fill", "#F8FAFC"))

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=24 * mm,   # extra bottom margin for footer
        title=f"{branding['app_name']} – Executive Summary",
    )

    styles = getSampleStyleSheet()

    tagline_style = ParagraphStyle(
        "CDTagline",
        parent=styles["Normal"],
        textColor=colors.HexColor("#657286"),
        fontSize=11,
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "CDMeta",
        parent=styles["Normal"],
        textColor=colors.HexColor("#33414E"),
        fontSize=10.5,
        spaceAfter=14,
    )
    section_style = ParagraphStyle(
        "CDSection",
        parent=styles["Heading2"],
        textColor=colors.white,
        backColor=primary,
        fontSize=12,
        leading=16,
        spaceBefore=14,
        spaceAfter=6,
        leftIndent=6,
        borderPadding=(5, 6, 5, 6),
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "CDBody",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#33414E"),
    )
    caption_style = ParagraphStyle(
        "CDCaption",
        parent=styles["Italic"],
        fontSize=9.5,
        textColor=colors.HexColor("#657286"),
        spaceAfter=8,
        leading=13,
    )
    chart_title_style = ParagraphStyle(
        "CDChartTitle",
        parent=styles["Heading4"],
        textColor=primary,
        fontSize=12,
        spaceBefore=12,
        spaceAfter=2,
        fontName="Helvetica-Bold",
    )
    advisory_heading_style = ParagraphStyle(
        "CDAdvisoryHeading",
        parent=styles["Heading4"],
        textColor=primary,
        fontSize=10.5,
        spaceBefore=10,
        spaceAfter=3,
        fontName="Helvetica-Bold",
    )
    advisory_bullet_style = ParagraphStyle(
        "CDAdvisoryBullet",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        leftIndent=10,
        spaceAfter=4,
        textColor=colors.HexColor("#33414E"),
    )
    bottom_line_style = ParagraphStyle(
        "CDBottomLine",
        parent=styles["BodyText"],
        fontSize=11,
        leading=16,
        textColor=colors.white,
        backColor=primary,
        borderPadding=(8, 10, 8, 10),
        spaceAfter=4,
    )

    story = []

    # ── Cover block ──────────────────────────────────────────────────────────
    # Logo carries the brand name on its own — no typed app-name title beside
    # it, so it can run larger without crowding the page (was 40mm). A custom
    # branded logo (uploaded for this run) takes priority over the default.
    logo_bytes = branding.get("logo_bytes")
    logo_source = BytesIO(logo_bytes) if logo_bytes else branding.get("logo_path", "assets/logo/coltradata_logo.png")
    if logo_bytes or os.path.exists(logo_source):
        reader = ImageReader(logo_source)
        iw, ih = reader.getSize()
        logo_width = 56 * mm
        if logo_bytes:
            logo_source.seek(0)
        story.append(Image(logo_source, width=logo_width, height=logo_width * ih / iw))
        story.append(Spacer(1, 10))

    story.append(Paragraph(branding["tagline"], tagline_style))
    story.append(Paragraph(
        f"Data Quality &amp; Intelligence Report &nbsp;&nbsp;·&nbsp;&nbsp; "
        f"Generated {datetime.now().strftime('%d %B %Y, %H:%M')} "
        f"&nbsp;&nbsp;·&nbsp;&nbsp; {branding.get('company', 'Coltrane Ltd')}",
        meta_style,
    ))
    story.append(HRFlowable(
        width="100%", thickness=1.5, color=primary, spaceAfter=14, spaceBefore=2,
    ))

    # ── AI advisory, split into named sections (empty dict if none supplied) ──
    ai_sections = split_advisory_sections(ai_advisory) if ai_advisory else {}

    # ── Executive Summary ────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", section_style))

    missing_values = int(cleaned_df.isnull().sum().sum())
    rows_removed   = len(raw_df) - len(cleaned_df)

    kpi_data = [
        ["Original Rows",   f"{len(raw_df):,}",
         "Cleaned Rows",    f"{len(cleaned_df):,}"],
        ["Rows Removed",    f"{rows_removed:,}",
         "Columns",         f"{len(cleaned_df.columns):,}"],
        ["Missing Values",  f"{missing_values:,}",
         "Overall Risk",    risk_summary["overall_risk"]],
        ["Top Issue",       risk_summary["top_issue"],
         "Avg Issue Rate",  f"{risk_summary['avg_issue_pct']}%"],
    ]

    col_w = [34 * mm, 36 * mm, 34 * mm, 66 * mm]
    kpi_table = Table(kpi_data, colWidths=col_w)

    risk_row = 2   # row index where "Overall Risk" value appears
    risk_level = risk_summary["overall_risk"]
    risk_text_colour = RISK_COLOURS.get(risk_level, colors.HexColor("#33414E"))

    kpi_style = TableStyle([
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (0, 0), (0, -1), primary),
        ("TEXTCOLOR",   (2, 0), (2, -1), primary),
        ("BACKGROUND",  (0, 0), (0, -1), light_fill),
        ("BACKGROUND",  (2, 0), (2, -1), light_fill),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#E6ECF0")),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",(0, 0), (-1, -1), 7),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        # Colour the risk value cell
        ("TEXTCOLOR",   (3, risk_row), (3, risk_row), risk_text_colour),
        ("FONTNAME",    (3, risk_row), (3, risk_row), "Helvetica-Bold"),
        ("BACKGROUND",  (3, risk_row), (3, risk_row), RISK_BG.get(risk_level, neutral_fill)),
    ])
    kpi_table.setStyle(kpi_style)
    story.append(kpi_table)
    story.append(Spacer(1, 8))

    executive_bottom_line = ai_sections.get("Executive Bottom Line")
    if not executive_bottom_line:
        executive_bottom_line = ReportBuilder(branding).build_bottom_line(raw_df, cleaned_df, risk_summary)
    story.append(Paragraph("<b>Bottom Line</b>", body_style))
    story.extend(_markdown_to_flowables(
        executive_bottom_line, advisory_heading_style, advisory_bullet_style, body_style,
    ))
    story.append(Spacer(1, 6))

    # ── Data Quality Summary ─────────────────────────────────────────────────
    story.append(Paragraph("Data Quality Summary", section_style))
    story.append(Spacer(1, 4))

    total_cells = len(cleaned_df) * len(cleaned_df.columns)
    missing_pct = round(missing_values / total_cells * 100, 1) if total_cells else 0.0
    story.append(Paragraph(
        f"Missing values: {missing_values:,} of {total_cells:,} cells ({missing_pct}%).",
        body_style,
    ))
    story.append(Spacer(1, 4))

    risk_levels = ["High", "Medium", "Low"]
    risk_rows = [["Risk Level", "Columns Flagged", "Status"]]
    for level in risk_levels:
        count = risk_summary.get(f"{level.lower()}_count", 0)
        status = "Action required" if level == "High" else ("Review flagged" if level == "Medium" else "Within tolerance")
        risk_rows.append([level, count, status])

    risk_style_commands = [
        ("FONTSIZE",     (0, 0), (-1, -1), 9.5),
        ("BACKGROUND",   (0, 0), (-1, 0), primary),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",     (0, 1), (0, -1), "Helvetica-Bold"),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#E6ECF0")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, light_fill]),
        ("LEFTPADDING",  (0, 0), (-1, -1), 7),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("ALIGN",        (1, 0), (1, -1), "CENTER"),
    ]
    for i, level in enumerate(risk_levels, start=1):
        risk_style_commands.append(("TEXTCOLOR", (0, i), (0, i), RISK_COLOURS[level]))
        risk_style_commands.append(("BACKGROUND", (0, i), (0, i), RISK_BG[level]))

    risk_table = Table(risk_rows, colWidths=[50 * mm, 40 * mm, 80 * mm])
    risk_table.setStyle(TableStyle(risk_style_commands))
    story.append(risk_table)
    story.append(Paragraph(
        f"Average issue rate across columns: {risk_summary['avg_issue_pct']}%.",
        caption_style,
    ))
    if risk_summary.get("overall_risk") == "High" and risk_summary.get("structural_missingness"):
        story.append(Paragraph(
            "Risk is primarily driven by structurally expected missing data, not data corruption.",
            caption_style,
        ))

    # ── Premium Chart Gallery ────────────────────────────────────────────────
    if chart_assets:
        story.append(Paragraph("Visual Insights", section_style))
        story.append(Paragraph(
            "Premium charts generated automatically from the cleaned dataset, "
            "mirroring the live dashboard and embedded in the Excel Executive Summary.",
            caption_style,
        ))

        chart_width  = doc.width
        chart_height = chart_width / CHART_IMAGE_ASPECT

        for card, png_bytes in chart_assets:
            story.append(Paragraph(card.title, chart_title_style))
            story.append(Paragraph(card.description, caption_style))
            story.append(Image(BytesIO(png_bytes), width=chart_width, height=chart_height))
            story.append(Spacer(1, 6))

    # ── Key Data Insights ────────────────────────────────────────────────────
    key_insights = ai_sections.get("Key Data Insights")
    if key_insights:
        story.append(Paragraph("Key Data Insights", section_style))
        story.append(Paragraph(
            "Business-focused patterns drawn from the cleaned dataset — what is happening, "
            "and why it matters.",
            caption_style,
        ))
        story.extend(_markdown_to_flowables(
            key_insights, advisory_heading_style, advisory_bullet_style, body_style,
        ))

    # ── AI Advisory ──────────────────────────────────────────────────────────
    ai_advisory_body = ai_sections.get("AI Advisory")
    if ai_advisory_body:
        story.append(Paragraph("AI Advisory", section_style))
        story.append(Paragraph(
            "Claude-powered interpretation of the cleaned data — patterns, anomalies, "
            "quality risks, and concrete next steps.",
            caption_style,
        ))
        story.extend(_markdown_to_flowables(
            ai_advisory_body, advisory_heading_style, advisory_bullet_style, body_style,
        ))

    # ── Modelling & Analytics Readiness ──────────────────────────────────────
    modelling_readiness = ai_sections.get("Modelling & Analytics Readiness")
    if modelling_readiness:
        story.append(Paragraph("Modelling &amp; Analytics Readiness", section_style))
        story.extend(_markdown_to_flowables(
            modelling_readiness, advisory_heading_style, advisory_bullet_style, body_style,
        ))

    # ── Top Priority Actions ─────────────────────────────────────────────────
    top_actions = ai_sections.get("Top Priority Actions")
    if top_actions:
        story.append(Paragraph("Top Priority Actions", section_style))
        story.extend(_markdown_to_flowables(
            top_actions, advisory_heading_style, advisory_bullet_style, body_style,
        ))

    # ── Bottom Line Summary ──────────────────────────────────────────────────
    story.append(Paragraph("Bottom Line Summary", section_style))
    closing_summary = ai_sections.get("Bottom Line Summary")
    if not closing_summary:
        closing_summary = ReportBuilder(branding).build_bottom_line(raw_df, cleaned_df, risk_summary)
    closing_lines = [line.strip() for line in closing_summary.splitlines() if line.strip()]
    closing_html = "<br/>".join(
        strip_residual_markdown(_inline_markdown(line.lstrip("-* ").strip()))
        for line in closing_lines
    )
    story.append(Paragraph(closing_html, bottom_line_style))

    # ── Footer disclaimer ────────────────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(HRFlowable(
        width="100%", thickness=0.5, color=colors.HexColor("#E6ECF0"),
        spaceAfter=6, spaceBefore=0,
    ))
    story.append(Paragraph(
        branding.get("report_disclaimer",
            f"{branding['app_name']} provides structured data cleaning, validation and dashboard "
            "reporting outputs. It does not provide advisory or decision-making recommendations."),
        caption_style,
    ))
    story.append(Paragraph(
        f"Contact: {branding['contact_email']}  &nbsp;·&nbsp;  &copy; 2026 {branding.get('company', 'Coltrane Ltd')}. All rights reserved.",
        caption_style,
    ))
    if branding.get("legal_line"):
        story.append(Paragraph(branding["legal_line"], caption_style))

    footer_cb = lambda c, d: _draw_page_footer(c, d, branding)
    doc.build(story, onFirstPage=footer_cb, onLaterPages=footer_cb)
    return buffer.getvalue()
