import os
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

from core.chart_gallery import CHART_IMAGE_ASPECT

RISK_COLOURS = {
    "High": colors.HexColor("#E74C3C"),
    "Medium": colors.HexColor("#F39C12"),
    "Low": colors.HexColor("#2ECC71"),
}


def build_pdf_report(branding, raw_df, cleaned_df, risk_summary, chart_assets) -> bytes:
    """
    Builds a downloadable PDF executive summary: KPIs, the data-quality risk
    mix and the same premium chart gallery shown on the live dashboard.
    """
    buffer = BytesIO()
    primary = colors.HexColor(branding["primary_colour"])
    neutral_fill = colors.HexColor(branding.get("neutral_fill", "#F4F6F8"))

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"{branding['app_name']} - Executive Summary",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CDTitle", parent=styles["Title"], textColor=primary, fontSize=22, leading=26, spaceAfter=2)
    subtitle_style = ParagraphStyle("CDSubtitle", parent=styles["Normal"], textColor=colors.HexColor("#657286"), fontSize=10, spaceAfter=16)
    section_style = ParagraphStyle("CDSection", parent=styles["Heading2"], textColor=colors.white, backColor=primary, fontSize=12, leading=16, spaceBefore=16, spaceAfter=8, leftIndent=6, borderPadding=6)
    body_style = ParagraphStyle("CDBody", parent=styles["BodyText"], fontSize=9.5, leading=13, textColor=colors.HexColor("#33414E"))
    caption_style = ParagraphStyle("CDCaption", parent=styles["Italic"], fontSize=9, textColor=colors.HexColor("#666666"), spaceAfter=10)
    chart_title_style = ParagraphStyle("CDChartTitle", parent=styles["Heading4"], textColor=primary, fontSize=11, spaceBefore=14, spaceAfter=2)

    story = []

    logo_path = "assets/logo/coltradata_logo.png"
    if os.path.exists(logo_path):
        reader = ImageReader(logo_path)
        iw, ih = reader.getSize()
        logo_width = 38 * mm
        story.append(Image(logo_path, width=logo_width, height=logo_width * ih / iw))
        story.append(Spacer(1, 6))

    story.append(Paragraph(branding["app_name"], title_style))
    story.append(Paragraph(branding["tagline"], subtitle_style))
    story.append(Paragraph(
        f"Executive Summary — generated {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        body_style,
    ))
    story.append(Spacer(1, 6))

    # KPI table
    missing_values = int(cleaned_df.isnull().sum().sum())
    kpi_rows = [
        ["Original Rows", f"{len(raw_df):,}", "Cleaned Rows", f"{len(cleaned_df):,}"],
        ["Columns", f"{len(cleaned_df.columns):,}", "Missing Values", f"{missing_values:,}"],
        ["Overall Risk", risk_summary["overall_risk"], "Top Issue", risk_summary["top_issue"]],
    ]
    kpi_table = Table(kpi_rows, colWidths=[32 * mm, 38 * mm, 32 * mm, 68 * mm])
    kpi_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), primary),
        ("TEXTCOLOR", (2, 0), (2, -1), primary),
        ("BACKGROUND", (0, 0), (0, -1), neutral_fill),
        ("BACKGROUND", (2, 0), (2, -1), neutral_fill),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E6ECF0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(kpi_table)

    # Risk mix
    story.append(Paragraph("Data Quality Risk Mix", section_style))
    risk_levels = ["High", "Medium", "Low"]
    risk_rows = [["Risk Level", "Columns Flagged"]]
    for level in risk_levels:
        risk_rows.append([level, risk_summary.get(f"{level.lower()}_count", 0)])

    risk_style_commands = [
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E6ECF0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, neutral_fill]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, level in enumerate(risk_levels, start=1):
        risk_style_commands.append(("TEXTCOLOR", (0, i), (0, i), RISK_COLOURS[level]))

    risk_table = Table(risk_rows, colWidths=[60 * mm, 40 * mm])
    risk_table.setStyle(TableStyle(risk_style_commands))
    story.append(risk_table)
    story.append(Paragraph(
        f"Average issue rate across columns: {risk_summary['avg_issue_pct']}%.",
        caption_style,
    ))

    # Chart gallery
    if chart_assets:
        story.append(Paragraph("Visual Highlights", section_style))
        story.append(Paragraph(
            "Premium charts generated automatically from the cleaned dataset, mirroring the live dashboard.",
            caption_style,
        ))

        chart_width = doc.width
        chart_height = chart_width / CHART_IMAGE_ASPECT

        for card, png_bytes in chart_assets:
            story.append(Paragraph(card.title, chart_title_style))
            story.append(Paragraph(card.description, caption_style))
            story.append(Image(BytesIO(png_bytes), width=chart_width, height=chart_height))
            story.append(Spacer(1, 4))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f"{branding['app_name']} provides structured data cleaning, validation and dashboard reporting "
        "outputs. It does not provide advisory or decision-making recommendations.",
        caption_style,
    ))
    story.append(Paragraph(f"Contact: {branding['contact_email']}", caption_style))

    doc.build(story)
    return buffer.getvalue()
