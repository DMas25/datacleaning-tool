from typing import Optional, Dict, List, Tuple
from io import BytesIO
import pandas as pd
from datetime import datetime
import os

from core.data_validator import build_validation_issues
from core.insights_engine import generate_insights, detect_date_columns
from core.chart_gallery import ChartCard, build_chart_gallery, render_chart_images
from core.coltradata_refine_patch import column_risk_levels, recommended_action


class ReportBuilder:
    RISK_EMOJI = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
    RISK_COLOURS = {"High": "#E74C3C", "Medium": "#F39C12", "Low": "#2ECC71"}

    def __init__(self, config):
        self.config = config

    def build_report(
        self, raw_df, cleaned_df, log_df, quality_df, dictionary_df=None,
        quality_breakdown_df=None, chart_assets=None,
    ):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        file_name = f"ColtraDataAi_Cleaned_Report_{timestamp}.xlsx"

        if quality_breakdown_df is None:
            quality_breakdown_df = self.build_quality_breakdown(cleaned_df)

        if chart_assets is None:
            chart_assets = self.build_chart_assets(raw_df, cleaned_df, quality_breakdown_df)

        with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
            workbook = writer.book
            self._create_formats(workbook)

            # Build every sheet in the desired tab order
            self._build_cover_sheet(workbook, writer, raw_df)
            self._write_dataframe(writer, raw_df, "Raw Data")
            self._write_dataframe(writer, cleaned_df, "Cleaned Data")
            self._write_dataframe(writer, log_df, "Cleaning Log")
            self._write_quality_sheet(writer, quality_df, quality_breakdown_df)

            if dictionary_df is not None:
                self._write_dataframe(writer, dictionary_df, "Data Dictionary")

            self._build_processing_notes(workbook)
            self._build_insights_sheet(workbook, cleaned_df)
            self._build_executive_summary_sheet(workbook, raw_df, cleaned_df, quality_breakdown_df, chart_assets)
            self._build_dashboard_sheet(workbook, raw_df, cleaned_df, quality_df, quality_breakdown_df)

            # Apply branded tab colours now that all sheets exist
            self._apply_tab_colours(workbook)

        return file_name

    def build_quality_breakdown(self, cleaned_df) -> pd.DataFrame:
        return self._build_column_quality_breakdown(cleaned_df)

    def build_risk_summary(self, quality_breakdown_df: pd.DataFrame) -> Dict[str, object]:
        return self._build_risk_summary_v2(quality_breakdown_df)

    def build_chart_assets(
        self, raw_df, cleaned_df, quality_breakdown_df=None, date_cols=None,
    ) -> List[Tuple[ChartCard, bytes]]:
        """
        Builds the premium chart gallery for this dataset and renders each
        figure to PNG bytes (via Kaleido) so the same visuals can be embedded
        in the Excel Executive Summary sheet and the downloadable PDF report.
        """
        if quality_breakdown_df is None:
            quality_breakdown_df = self.build_quality_breakdown(cleaned_df)

        if date_cols is None:
            date_cols = detect_date_columns(cleaned_df)

        cards = build_chart_gallery(raw_df, cleaned_df, self.config, quality_breakdown_df, date_cols=date_cols)
        return render_chart_images(cards)

    def _create_formats(self, workbook):
        self.title_format = workbook.add_format({
            "bold": True,
            "font_size": 20,
            "font_color": self.config["primary_colour"],
            "align": "left",
            "valign": "vcenter"
        })

        self.subtitle_format = workbook.add_format({
            "font_size": 11,
            "font_color": "#444444",
            "italic": True
        })

        self.section_header = workbook.add_format({
            "bold": True,
            "font_size": 12,
            "font_color": "white",
            "bg_color": self.config["primary_colour"],
            "border": 1,
            "align": "left",
            "valign": "vcenter"
        })

        self.table_header = workbook.add_format({
            "bold": True,
            "bg_color": self.config["header_fill"],
            "font_color": self.config["primary_colour"],
            "border": 1,
            "text_wrap": True
        })

        self.body_format = workbook.add_format({
            "border": 1,
            "valign": "top"
        })

        self.note_format = workbook.add_format({
            "font_size": 10,
            "font_color": "#555555",
            "italic": True,
            "text_wrap": True
        })

        self.metric_label = workbook.add_format({
            "bold": True,
            "bg_color": self.config["neutral_fill"],
            "border": 1
        })

        self.metric_value = workbook.add_format({
            "bold": True,
            "font_color": self.config["primary_colour"],
            "border": 1
        })

        self.success_format = workbook.add_format({
            "bold": True,
            "font_color": "white",
            "bg_color": self.config["success_colour"],
            "align": "center",
            "border": 1
        })

        self.warning_format = workbook.add_format({
            "bold": True,
            "font_color": "black",
            "bg_color": self.config["warning_colour"],
            "align": "center",
            "border": 1
        })

        self.danger_format = workbook.add_format({
            "bold": True,
            "font_color": "white",
            "bg_color": self.config["danger_colour"],
            "align": "center",
            "border": 1
        })

        self.disclaimer_format = workbook.add_format({
            "font_size": 9,
            "italic": True,
            "font_color": "#666666",
            "text_wrap": True
        })

    def _apply_tab_colours(self, workbook) -> None:
        """Apply branded colour coding to every sheet tab."""
        tab_map = {
            "Report Summary":   self.config["primary_colour"],
            "Raw Data":         "#8DA9C4",
            "Cleaned Data":     self.config.get("accent_colour", "#2E86AB"),
            "Cleaning Log":     "#4472C4",
            "Quality Checks":   self.config["warning_colour"],
            "Data Dictionary":  "#9CA3AF",
            "Processing Notes": "#9CA3AF",
            "Data Insights":    "#48C9B0",
            "Executive Summary": self.config["primary_colour"],
            "Dashboard":        self.config["success_colour"],
        }
        for name, colour in tab_map.items():
            ws = workbook.get_worksheet_by_name(name)
            if ws is not None:
                ws.set_tab_color(colour)

    def _set_header_row_height(self, worksheet, row: int = 1, height: int = 22) -> None:
        """Sets a taller row height for the header row so column labels breathe."""
        worksheet.set_row(row, height)

    def _build_cover_sheet(self, workbook, writer, raw_df):
        sheet = workbook.add_worksheet("Report Summary")

        # Column widths — narrow gutter, then label, then wide value area
        sheet.set_column("A:A", 3)
        sheet.set_column("B:B", 22)
        sheet.set_column("C:H", 16)

        # Logo — scaled to ~100 px wide, top-left
        logo_path = self.config.get("logo_path", "assets/logo/coltradata_logo.png")
        if os.path.exists(logo_path):
            sheet.insert_image("B2", logo_path, {"x_scale": 0.45, "y_scale": 0.45, "x_offset": 4})

        # Title and tagline (pushed down below logo)
        sheet.set_row(8, 28)
        sheet.merge_range("B9:H9", self.config["app_name"], self.title_format)
        sheet.merge_range("B10:H10", self.config["tagline"], self.subtitle_format)

        # Key report metrics
        sheet.set_row(12, 20)
        sheet.write("B13", "Generated On", self.metric_label)
        sheet.write("C13", datetime.now().strftime("%d %B %Y, %H:%M"), self.metric_value)

        sheet.write("B14", "Total Rows", self.metric_label)
        sheet.write("C14", len(raw_df), self.metric_value)

        sheet.write("B15", "Total Columns", self.metric_label)
        sheet.write("C15", len(raw_df.columns), self.metric_value)

        sheet.write("B16", "Prepared By", self.metric_label)
        sheet.write("C16", self.config["app_name"], self.metric_value)

        # Description block
        sheet.merge_range(
            "B18:H21",
            "This workbook contains the original uploaded dataset, cleaned data output, "
            "processing log, quality checks, data insights, an executive summary with "
            "embedded charts, and a dashboard — all generated by ColtraDataAi.",
            self.body_format,
        )

        # Non-advisory disclaimer
        sheet.merge_range(
            "B23:H24",
            self.config.get(
                "report_disclaimer",
                "ColtraDataAi provides structured data cleaning, validation and dashboard "
                "reporting outputs. It does not provide advisory or decision-making recommendations.",
            ),
            self.disclaimer_format,
        )

        sheet.write("B26", "Contact", self.metric_label)
        sheet.write("C26", self.config["contact_email"], self.metric_value)

        # ── Workbook Contents (Table of Contents) ─────────────────────────────
        toc_title_row = 28   # 0-indexed → row 29 in Excel
        sheet.set_row(toc_title_row, 20)
        sheet.merge_range(toc_title_row, 1, toc_title_row, 7, "Workbook Contents", self.section_header)

        toc_hdr_row = toc_title_row + 1
        sheet.set_row(toc_hdr_row, 18)
        sheet.write(toc_hdr_row, 1, "Sheet", self.table_header)
        sheet.merge_range(toc_hdr_row, 2, toc_hdr_row, 7, "Contents", self.table_header)

        toc_link_format = workbook.add_format({
            "bold": True,
            "bg_color": self.config["neutral_fill"],
            "font_color": self.config["primary_colour"],
            "border": 1,
            "underline": True,
        })

        toc_entries = [
            ("Report Summary",    "Overview metrics, key facts and this workbook index"),
            ("Raw Data",          "Original uploaded dataset — unmodified source records"),
            ("Cleaned Data",      "Processed dataset after all configured cleaning steps"),
            ("Cleaning Log",      "Step-by-step record of every operation applied"),
            ("Quality Checks",    "Issue detection, risk scoring and column-level breakdown"),
            ("Processing Notes",  "Assumptions and rules applied during report generation"),
            ("Data Insights",     "Structured descriptive observations — observational only"),
            ("Executive Summary", "Premium chart gallery and top-line KPI summary"),
            ("Dashboard",         "Charts, completeness ratio, risk levels and status summary"),
        ]

        for i, (sheet_name, description) in enumerate(toc_entries):
            r = toc_hdr_row + 1 + i
            sheet.set_row(r, 16)
            internal_url = f"internal:'{sheet_name}'!A1"
            sheet.write_url(r, 1, internal_url, toc_link_format, sheet_name)
            sheet.merge_range(r, 2, r, 7, description, self.body_format)

    def _write_dataframe(self, writer, df, sheet_name):
        df.to_excel(writer, sheet_name=sheet_name, startrow=1, index=False)

        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # Title row height and label
        worksheet.set_row(0, 20)
        worksheet.write(0, 0, sheet_name, self.section_header)

        # Header row height and formatting
        worksheet.set_row(1, 22)
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(1, col_num, value, self.table_header)

        # Freeze panes below header
        worksheet.freeze_panes(2, 0)

        # Autofilter
        worksheet.autofilter(1, 0, len(df) + 1, max(len(df.columns) - 1, 0))

        # Column widths
        for i, col in enumerate(df.columns):
            series = df[col].head(200).map(lambda v: "" if pd.isna(v) else str(v))
            max_len = max(
                [len(str(col))] + series.map(len).tolist()
            )
            worksheet.set_column(i, i, min(max_len + 2, 28))

        # Conditional formatting for blanks
        if len(df.columns) > 0 and len(df) > 0:
            worksheet.conditional_format(
                2, 0, len(df) + 1, len(df.columns) - 1,
                {
                    "type": "blanks",
                    "format": workbook.add_format({"bg_color": "#FFF2CC"})
                }
            )

    def _safe_divide(self, a, b):
        return a / b if b else 0

    def _normalise_quality_columns(self, quality_df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardises likely quality_df column names so downstream logic is stable.

        Expected output columns:
        - Column
        - Issue Type
        - Issue Count
        - Total Rows
        """
        df = quality_df.copy()

        rename_map = {}

        for col in df.columns:
            c = col.strip().lower()

            if c in ["column", "field", "field name", "column name"]:
                rename_map[col] = "Column"
            elif c in ["issue type", "check", "rule", "problem type", "issue"]:
                rename_map[col] = "Issue Type"
            elif c in ["issue count", "count", "errors", "error count", "affected rows"]:
                rename_map[col] = "Issue Count"
            elif c in ["total rows", "rows", "row count", "dataset rows"]:
                rename_map[col] = "Total Rows"

        df = df.rename(columns=rename_map)

        # Ensure required columns exist
        if "Column" not in df.columns:
            df["Column"] = "Dataset"
        if "Issue Type" not in df.columns:
            df["Issue Type"] = "General Quality Issue"
        if "Issue Count" not in df.columns:
            df["Issue Count"] = 0
        if "Total Rows" not in df.columns:
            # fallback: use max issue count basis if actual total not present
            df["Total Rows"] = max(int(df["Issue Count"].max()) if len(df) else 0, 1)

        df["Issue Count"] = pd.to_numeric(df["Issue Count"], errors="coerce").fillna(0)
        df["Total Rows"] = pd.to_numeric(df["Total Rows"], errors="coerce").fillna(1)

        return df

    def _issue_weight(self, issue_type: str) -> float:
        """
        Assigns a weight to each issue type.
        You can tune these commercially later.
        """
        issue = str(issue_type).strip().lower()

        weights = {
            "missing values": 1.0,
            "missing": 1.0,
            "nulls": 1.0,
            "duplicates": 0.9,
            "duplicate rows": 0.9,
            "invalid format": 1.2,
            "format": 1.2,
            "type mismatch": 1.2,
            "inconsistent values": 1.1,
            "inconsistent text": 1.1,
            "outliers": 0.8,
            "blank strings": 0.9,
            "invalid dates": 1.3,
            "invalid emails": 1.3,
            "invalid numbers": 1.2,
        }

        return weights.get(issue, 1.0)

    def _assign_risk_level_v2(self, issue_pct: float, weighted_score: float) -> str:
        """
        Risk bands based on prevalence + issue severity weighting.
        """
        if issue_pct >= 0.30 or weighted_score >= 35:
            return "High"
        elif issue_pct >= 0.10 or weighted_score >= 12:
            return "Medium"
        else:
            return "Low"

    def _prepare_quality_df_with_risk_v2(
        self,
        quality_df: pd.DataFrame,
        total_rows: Optional[int] = None,
        business_rules_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Extends quality_df with Issue %, Weighted Score, and Risk Level.
        Optionally merges in a business-rules layer later.
        """
        df = self._normalise_quality_columns(quality_df)

        if total_rows is not None and total_rows > 0:
            df["Total Rows"] = total_rows

        df["Issue %"] = df.apply(
            lambda r: self._safe_divide(r["Issue Count"], r["Total Rows"]),
            axis=1
        )

        df["Weight"] = df["Issue Type"].apply(self._issue_weight)
        df["Weighted Score"] = (df["Issue %"] * 100 * df["Weight"]).round(2)

        df["Risk Level"] = df.apply(
            lambda r: self._assign_risk_level_v2(r["Issue %"], r["Weighted Score"]),
            axis=1
        )

        # Optional future business rule overlay
        if business_rules_df is not None and not business_rules_df.empty:
            br = business_rules_df.copy()
            br = br.rename(columns={
                "Rule Name": "Issue Type",
                "Failed Count": "Issue Count"
            })

            if "Column" not in br.columns:
                br["Column"] = "Business Rules"
            if "Total Rows" not in br.columns:
                br["Total Rows"] = total_rows if total_rows else 1

            br["Issue %"] = br.apply(
                lambda r: self._safe_divide(r["Issue Count"], r["Total Rows"]),
                axis=1
            )
            br["Weight"] = 1.5  # slightly higher than standard data issues
            br["Weighted Score"] = (br["Issue %"] * 100 * br["Weight"]).round(2)
            br["Risk Level"] = br.apply(
                lambda r: self._assign_risk_level_v2(r["Issue %"], r["Weighted Score"]),
                axis=1
            )

            df = pd.concat([df, br[df.columns]], ignore_index=True)

        return df

    def _build_risk_summary_v2(self, quality_df: pd.DataFrame) -> Dict[str, object]:
        """
        Creates top-line dashboard summary.
        """
        if quality_df.empty:
            return {
                "overall_risk": "Low",
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "top_issue": "None",
                "avg_issue_pct": 0,
            }

        risk_counts = quality_df["Risk Level"].value_counts().to_dict()
        high_count = risk_counts.get("High", 0)
        medium_count = risk_counts.get("Medium", 0)
        low_count = risk_counts.get("Low", 0)

        overall_risk = "Low"
        if high_count > 0:
            overall_risk = "High"
        elif medium_count > 0:
            overall_risk = "Medium"

        top_issue_row = quality_df.sort_values(
            by=["Weighted Score", "Issue Count"],
            ascending=False
        ).iloc[0]

        return {
            "overall_risk": overall_risk,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "top_issue": f"{top_issue_row['Issue Type']} ({top_issue_row['Column']})",
            "avg_issue_pct": round(float(quality_df["Issue %"].mean()), 2),
        }

    def _build_column_quality_breakdown(self, cleaned_df):
        total_rows = len(cleaned_df)
        rows = []

        for col in cleaned_df.columns:
            issue_count = int(cleaned_df[col].isnull().sum())
            rows.append({
                "Column": str(col),
                "Issue Type": "Missing",
                "Issue Count": issue_count,
                "Total Rows": total_rows,
            })

        issues_df = pd.DataFrame(rows)

        validation_df = build_validation_issues(cleaned_df)
        if not validation_df.empty:
            issues_df = pd.concat([issues_df, validation_df], ignore_index=True)

        breakdown_df = self._prepare_quality_df_with_risk_v2(issues_df, total_rows=total_rows)
        breakdown_df["Issue %"] = (breakdown_df["Issue %"] * 100).round(2)

        return breakdown_df

    def _format_risk_level(self, risk_level):
        return f"{self.RISK_EMOJI[risk_level]} {risk_level}"

    def _write_quality_sheet(self, writer, quality_df, quality_breakdown_df):
        quality_df.to_excel(writer, sheet_name="Quality Checks", startrow=1, index=False)
        workbook = writer.book
        worksheet = writer.sheets["Quality Checks"]

        worksheet.write(0, 0, "Quality Checks", self.section_header)

        for col_num, value in enumerate(quality_df.columns.values):
            worksheet.write(1, col_num, value, self.table_header)

        worksheet.freeze_panes(2, 0)
        worksheet.autofilter(1, 0, len(quality_df) + 1, max(len(quality_df.columns) - 1, 0))
        worksheet.set_column("A:A", 26)
        worksheet.set_column("B:B", 16)

        # Optional visual highlight for status-style values if present
        if "Metric" in quality_df.columns and "Value" in quality_df.columns:
            worksheet.write("D2", "Overall Status", self.metric_label)
            worksheet.write("D3", "Risk Level", self.metric_label)

            missing_total = 0
            rows_total = 0

            try:
                if "Missing Values" in quality_df["Metric"].values:
                    missing_total = int(
                        quality_df.loc[quality_df["Metric"] == "Missing Values", "Value"].iloc[0]
                    )
                if "Rows" in quality_df["Metric"].values:
                    rows_total = int(
                        quality_df.loc[quality_df["Metric"] == "Rows", "Value"].iloc[0]
                    )
            except Exception:
                pass

            ratio = self._safe_divide(missing_total, rows_total)
            weighted_score = round(ratio * 100 * self._issue_weight("Missing Values"), 2)
            risk_level = self._assign_risk_level_v2(ratio, weighted_score)
            risk_format = {
                "Low": self.success_format,
                "Medium": self.warning_format,
                "High": self.danger_format,
            }[risk_level]

            if missing_total == 0:
                worksheet.write("E2", "PASS", self.success_format)
            elif missing_total < max(50, rows_total * 0.05):
                worksheet.write("E2", "REVIEW", self.warning_format)
            else:
                worksheet.write("E2", "WARNING", self.danger_format)

            worksheet.write("E3", risk_level, risk_format)

        # Column-level issue breakdown
        breakdown_title_row = len(quality_df) + 4
        breakdown_header_row = breakdown_title_row + 1
        breakdown_data_row = breakdown_header_row + 1

        worksheet.write(breakdown_title_row, 0, "Column-Level Issue Breakdown", self.section_header)

        for col_num, value in enumerate(quality_breakdown_df.columns.values):
            worksheet.write(breakdown_header_row, col_num, value, self.table_header)

        risk_col = quality_breakdown_df.columns.get_loc("Risk Level")

        for r, (_, row) in enumerate(quality_breakdown_df.iterrows(), start=breakdown_data_row):
            for c, value in enumerate(row):
                if c == risk_col:
                    value = self._format_risk_level(value)
                worksheet.write(r, c, value, self.body_format)

        last_row = breakdown_data_row + len(quality_breakdown_df) - 1

        if last_row >= breakdown_data_row:
            for level, fmt in (
                ("High", self.danger_format),
                ("Medium", self.warning_format),
                ("Low", self.success_format),
            ):
                worksheet.conditional_format(
                    breakdown_data_row, risk_col, last_row, risk_col,
                    {
                        "type": "text",
                        "criteria": "containing",
                        "value": level,
                        "format": fmt,
                    }
                )

    def _build_insights_sheet(self, workbook, cleaned_df):
        sheet = workbook.add_worksheet("Data Insights")
        sheet.set_column("A:A", 4)
        sheet.set_column("B:B", 110)

        sheet.write("A1", "Data Insights", self.section_header)
        sheet.merge_range(
            "A2:B2",
            "Structured, descriptive observations generated directly from the dataset. "
            "These are observational only and do not constitute advice or recommendations.",
            self.disclaimer_format
        )

        insights = generate_insights(cleaned_df)

        row = 4
        for category, lines in insights.items():
            sheet.write(row, 0, category, self.section_header)
            row += 1
            for line in lines:
                sheet.write(row, 0, "-", self.note_format)
                sheet.write(row, 1, line, self.body_format)
                row += 1
            row += 1

    def _build_processing_notes(self, workbook):
        sheet = workbook.add_worksheet("Processing Notes")
        sheet.set_column("A:A", 100)

        sheet.write("A1", "Processing Notes", self.section_header)
        notes = [
            "This section records the assumptions and processing rules applied during report generation.",
            "",
            "Standard elements may include:",
            "- Duplicate handling",
            "- Whitespace trimming",
            "- Header standardisation",
            "- Missing value reporting",
            "- Dashboard summary generation",
            "",
            "This output is non-advisory and is provided for structured reporting purposes only."
        ]

        for idx, line in enumerate(notes, start=3):
            sheet.write(f"A{idx}", line, self.body_format if not line.startswith("-") else self.note_format)

    def _build_executive_summary_sheet(self, workbook, raw_df, cleaned_df, quality_breakdown_df, chart_assets):
        sheet = workbook.add_worksheet("Executive Summary")

        # Two-column KPI layout: col A/B = left KPIs, col D/E = right KPIs
        sheet.set_column("A:A", 24)
        sheet.set_column("B:B", 18)
        sheet.set_column("C:C", 4)    # gutter
        sheet.set_column("D:D", 24)
        sheet.set_column("E:E", 18)
        sheet.set_column("F:Z", 14)

        sheet.set_row(0, 20)
        sheet.merge_range("A1:E1", "Executive Summary", self.section_header)

        sheet.merge_range(
            "A2:E2",
            "Top-line metrics and premium visual highlights generated automatically from the "
            "cleaned dataset. Charts mirror the live dashboard and are embedded for offline review.",
            self.disclaimer_format,
        )

        risk_summary  = self.build_risk_summary(quality_breakdown_df)
        missing_values = int(cleaned_df.isnull().sum().sum())
        rows_removed   = len(raw_df) - len(cleaned_df)
        total_cells    = cleaned_df.shape[0] * cleaned_df.shape[1]
        completeness   = (
            round((1 - missing_values / total_cells) * 100, 1)
            if total_cells else 100.0
        )

        overall_risk = risk_summary["overall_risk"]
        overall_fmt = {
            "Low":    self.success_format,
            "Medium": self.warning_format,
            "High":   self.danger_format,
        }[overall_risk]

        # Left column KPIs
        left_metrics = [
            ("Original Rows",    len(raw_df)),
            ("Cleaned Rows",     len(cleaned_df)),
            ("Rows Removed",     rows_removed),
            ("Columns",          len(cleaned_df.columns)),
        ]
        # Right column KPIs
        right_metrics = [
            ("Missing Values",   missing_values),
            ("Completeness",     f"{completeness}%"),
            ("High-Risk Fields", risk_summary["high_count"]),
            ("Avg Issue Rate",   f"{risk_summary['avg_issue_pct']}%"),
        ]

        kpi_title_row = 3
        sheet.set_row(kpi_title_row, 18)
        sheet.write(kpi_title_row, 0, "Key Metrics", self.section_header)
        sheet.merge_range(kpi_title_row, 3, kpi_title_row, 4, "Quality Summary", self.section_header)

        for i, (label, value) in enumerate(left_metrics):
            r = kpi_title_row + 1 + i
            sheet.set_row(r, 18)
            sheet.write(r, 0, label, self.metric_label)
            sheet.write(r, 1, value, self.metric_value)

        for i, (label, value) in enumerate(right_metrics):
            r = kpi_title_row + 1 + i
            sheet.write(r, 3, label, self.metric_label)
            sheet.write(r, 4, value, self.metric_value)

        # Overall Risk prominent cell
        risk_row = kpi_title_row + len(left_metrics) + 2
        sheet.set_row(risk_row, 22)
        sheet.write(risk_row, 0, "Overall Risk", self.metric_label)
        sheet.write(
            risk_row, 1,
            f"{self.RISK_EMOJI[overall_risk]} {overall_risk.upper()} RISK",
            overall_fmt,
        )
        sheet.write(risk_row, 3, "Top Issue", self.metric_label)
        sheet.merge_range(risk_row, 4, risk_row, 5, risk_summary["top_issue"], self.metric_value)

        # Chart gallery
        chart_start_row = risk_row + 3
        if not chart_assets:
            sheet.write(chart_start_row, 0, "No charts could be generated for this dataset.", self.note_format)
            return

        sheet.write(chart_start_row, 0, "Premium Chart Gallery", self.section_header)
        sheet.merge_range(
            chart_start_row + 1, 0, chart_start_row + 1, 5,
            "Charts are auto-generated from the cleaned dataset and match the live dashboard.",
            self.note_format,
        )

        row = chart_start_row + 3
        for card, png_bytes in chart_assets:
            sheet.set_row(row, 18)
            sheet.merge_range(row, 0, row, 5, card.title, self.section_header)
            row += 1
            sheet.write(row, 0, card.description, self.note_format)
            row += 1
            sheet.insert_image(row, 0, f"{card.key}.png", {
                "image_data": BytesIO(png_bytes),
                "x_scale": 0.5,
                "y_scale": 0.5,
            })
            row += 22

    def _build_dashboard_sheet(self, workbook, raw_df, cleaned_df, quality_df, quality_breakdown_df):
        sheet = workbook.add_worksheet("Dashboard")

        # Set layout
        sheet.set_column("A:A", 24)
        sheet.set_column("B:B", 14)
        sheet.set_column("D:J", 12)

        sheet.write("A1", "Dashboard Reporting", self.section_header)

        # Summary cards area
        original_rows = len(raw_df)
        cleaned_rows = len(cleaned_df)
        removed_rows = original_rows - cleaned_rows
        total_columns = len(cleaned_df.columns)
        missing_values = int(cleaned_df.isnull().sum().sum())

        metrics = [
            ("Original Rows", original_rows),
            ("Cleaned Rows", cleaned_rows),
            ("Rows Removed", removed_rows),
            ("Columns", total_columns),
            ("Missing Values", missing_values),
        ]

        r = 3
        for label, value in metrics:
            sheet.write(r, 0, label, self.metric_label)
            sheet.write(r, 1, value, self.metric_value)
            r += 1

        # Chart source data: missing values by top columns
        missing_by_col = cleaned_df.isnull().sum().sort_values(ascending=False).head(10)
        start_row = 3
        sheet.write(start_row - 1, 3, "Top Columns by Missing Values", self.table_header)
        sheet.write(start_row - 1, 4, "Count", self.table_header)

        for i, (col_name, val) in enumerate(missing_by_col.items(), start=start_row):
            sheet.write(i, 3, str(col_name), self.body_format)
            sheet.write(i, 4, int(val), self.body_format)

        # Chart 1 - Missing values
        chart1 = workbook.add_chart({"type": "column"})
        chart1.add_series({
            "name": "Missing Values",
            "categories": ["Dashboard", start_row, 3, start_row + len(missing_by_col) - 1, 3],
            "values": ["Dashboard", start_row, 4, start_row + len(missing_by_col) - 1, 4],
            "fill": {"color": self.config["secondary_colour"]},
            "border": {"color": self.config["primary_colour"]}
        })
        chart1.set_title({"name": "Missing Values by Column"})
        chart1.set_legend({"none": True})
        chart1.set_y_axis({"major_gridlines": {"visible": False}})
        chart1.set_style(10)

        sheet.insert_chart("G3", chart1, {"x_scale": 1.15, "y_scale": 1.15})

        # Chart source data: row counts comparison
        compare_row = 18
        sheet.write(compare_row, 3, "Dataset Stage", self.table_header)
        sheet.write(compare_row, 4, "Rows", self.table_header)

        sheet.write(compare_row + 1, 3, "Original", self.body_format)
        sheet.write(compare_row + 1, 4, original_rows, self.body_format)

        sheet.write(compare_row + 2, 3, "Cleaned", self.body_format)
        sheet.write(compare_row + 2, 4, cleaned_rows, self.body_format)

        chart2 = workbook.add_chart({"type": "bar"})
        chart2.add_series({
            "name": "Rows",
            "categories": ["Dashboard", compare_row + 1, 3, compare_row + 2, 3],
            "values": ["Dashboard", compare_row + 1, 4, compare_row + 2, 4],
            "fill": {"color": self.config["primary_colour"]},
            "border": {"color": self.config["primary_colour"]}
        })
        chart2.set_title({"name": "Original vs Cleaned Rows"})
        chart2.set_legend({"none": True})
        chart2.set_x_axis({"major_gridlines": {"visible": False}})
        chart2.set_style(10)

        sheet.insert_chart("G18", chart2, {"x_scale": 1.15, "y_scale": 1.0})

        # Optional completeness ratio example
        completeness_row = 26
        sheet.write(completeness_row, 0, "Data Completeness", self.section_header)

        total_cells = cleaned_df.shape[0] * cleaned_df.shape[1] if cleaned_df.shape[0] > 0 and cleaned_df.shape[1] > 0 else 0
        complete_cells = total_cells - missing_values
        completeness_pct = round((complete_cells / total_cells) * 100, 2) if total_cells else 0

        sheet.write(completeness_row + 2, 0, "Completeness %", self.metric_label)
        sheet.write(completeness_row + 2, 1, completeness_pct, self.metric_value)

        # Column risk levels
        risk_table_row = completeness_row + 5
        sheet.write(risk_table_row, 0, "Column Risk Levels", self.section_header)

        risk_header_row = risk_table_row + 1
        sheet.write(risk_header_row, 0, "Column", self.table_header)
        sheet.write(risk_header_row, 1, "Risk Level", self.table_header)

        risk_data_row = risk_header_row + 1
        deduped_risks = column_risk_levels(quality_breakdown_df)
        for i, (_, row) in enumerate(deduped_risks.iterrows(), start=risk_data_row):
            sheet.write(i, 0, row["Column"], self.body_format)
            sheet.write(i, 1, self._format_risk_level(row["Risk Level"]), self.body_format)

        risk_last_row = risk_data_row + len(deduped_risks) - 1
        if risk_last_row >= risk_data_row:
            sheet.conditional_format(
                risk_data_row, 1, risk_last_row, 1,
                {
                    "type": "text",
                    "criteria": "containing",
                    "value": "High",
                    "format": self.danger_format,
                }
            )

        # Data quality status summary
        status_row = max(risk_last_row, risk_data_row) + 3
        sheet.write(status_row, 0, "Data Quality Status", self.section_header)

        risk_summary = self._build_risk_summary_v2(quality_breakdown_df)
        overall_risk = risk_summary["overall_risk"]
        overall_format = {
            "Low": self.success_format,
            "Medium": self.warning_format,
            "High": self.danger_format,
        }[overall_risk]

        sheet.write(status_row + 1, 0, "Status", self.metric_label)
        sheet.write(
            status_row + 1, 1,
            f"{self.RISK_EMOJI[overall_risk]} {overall_risk.upper()} RISK",
            overall_format
        )

        duplicate_count = int(raw_df.duplicated().sum())
        duplicate_pct = round((duplicate_count / max(len(raw_df), 1)) * 100, 2)

        bullet_lines = [
            f"- {risk_summary['avg_issue_pct']}% Average Issue Rate Across Columns",
            f"- {duplicate_pct}% Duplicate Records",
            f"- {risk_summary['high_count']} Field(s) with High Risk",
            f"- Top Issue: {risk_summary['top_issue']}",
        ]
        for i, line in enumerate(bullet_lines, start=status_row + 2):
            sheet.write(i, 0, line, self.body_format)

        action_row = status_row + 2 + len(bullet_lines) + 1
        sheet.write(action_row, 0, "Recommended Action", self.metric_label)
        sheet.write(action_row + 1, 0, recommended_action(cleaned_df), self.body_format)
