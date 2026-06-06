from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BRAND = {
    "navy":   "#071733",
    "teal":   "#008E9B",
    "green":  "#46D324",
    "amber":  "#F59E0B",
    "red":    "#DC2626",
    "purple": "#6D5DF5",
    "gray":   "#CBD5E1",
    "muted":  "#657286",
    "white":  "#FFFFFF",
    "light":  "#F8FAFC",
}

RISK_COLORS = {
    "Critical": "#7F1D1D",
    "High":     "#DC2626",
    "Medium":   "#F59E0B",
    "Low":      "#46D324",
}


class ReportBuilder:

    def __init__(self, config=None):
        self.config    = config or {}
        self.company   = self.config.get("company",        "Coltrane Ltd")
        self.app_name  = self.config.get("app_name",       "ColtraDataAi")
        self.version   = self.config.get("version",        "2.0")
        self.tagline   = self.config.get("tagline",        "DATA. INSIGHTS. INTELLIGENCE.")
        self.primary   = self.config.get("primary_colour",   BRAND["navy"]).lstrip("#")
        self.secondary = self.config.get("secondary_colour", "#D9E1F2").lstrip("#")

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    def build_report(self, raw_df, cleaned_df, log_df, quality_df, dictionary_df=None):
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        filename = f"ColtraDataAi_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        filepath = output_dir / filename

        with pd.ExcelWriter(str(filepath), engine="xlsxwriter") as writer:
            workbook = writer.book
            self._create_styles(workbook)
            self._build_cover_sheet(workbook, writer, filename)
            self._build_dashboard_sheet(workbook, writer, raw_df, log_df)
            self._build_missing_chart(workbook, writer, cleaned_df)
            self._write_dataframe(writer, cleaned_df, "Cleaned Data")
            self._write_dataframe(writer, raw_df,     "Raw Data")
            self._write_dataframe(writer, log_df,     "Cleaning Log")
            self._write_dataframe(writer, quality_df, "Quality Checks")
            if dictionary_df is not None:
                self._write_dataframe(writer, dictionary_df, "Data Dictionary")
            self._build_processing_notes(writer)

        return str(filepath)

    # ------------------------------------------------------------------ #
    # Styles                                                               #
    # ------------------------------------------------------------------ #

    def _create_styles(self, workbook):
        def c(h):
            return h.lstrip("#")

        primary   = self.primary
        secondary = self.secondary
        teal  = c(BRAND["teal"])
        amber = c(BRAND["amber"])
        red   = c(BRAND["red"])
        white = c(BRAND["white"])
        light = c(BRAND["light"])
        muted = c(BRAND["muted"])
        gray  = c(BRAND["gray"])

        self.title_format = workbook.add_format({
            "bold": True, "font_size": 18, "font_color": primary,
        })
        self.header_format = workbook.add_format({
            "bold": True, "bg_color": secondary, "border": 1,
        })
        self.text_format = workbook.add_format({
            "font_size": 11,
        })
        self.small_text = workbook.add_format({
            "font_size": 9, "italic": True,
        })

        base = {"font_name": "Calibri", "font_size": 10, "valign": "vcenter"}

        self.tagline_format = workbook.add_format({
            **base, "bold": True, "font_size": 11, "font_color": teal, "italic": True,
        })
        self.subtitle_format = workbook.add_format({
            **base, "font_size": 12, "font_color": muted,
        })
        self.section_header_format = workbook.add_format({
            **base, "bold": True, "font_size": 11,
            "font_color": white, "bg_color": primary,
            "border": 1, "border_color": gray,
        })
        self.sheet_title_format = workbook.add_format({
            **base, "bold": True, "font_size": 13,
            "font_color": white, "bg_color": primary,
        })
        self.kpi_value_format = workbook.add_format({
            **base, "bold": True, "font_size": 22,
            "font_color": primary, "bg_color": secondary,
            "border": 1, "border_color": gray, "align": "center",
        })
        self.kpi_label_format = workbook.add_format({
            **base, "font_size": 9, "font_color": muted,
            "bg_color": light, "border": 1, "border_color": gray, "align": "center",
        })
        self.meta_key_format = workbook.add_format({
            **base, "bold": True, "bg_color": secondary, "border": 1, "border_color": gray,
        })
        self.meta_value_format = workbook.add_format({
            **base, "bg_color": white, "border": 1, "border_color": gray,
        })
        self.row_even_format = workbook.add_format({
            **base, "bg_color": light, "border": 1, "border_color": gray,
        })
        self.row_odd_format = workbook.add_format({
            **base, "bg_color": white, "border": 1, "border_color": gray,
        })
        self.row_high_format = workbook.add_format({
            **base, "bg_color": "FECACA", "border": 1, "border_color": red,
        })
        self.row_medium_format = workbook.add_format({
            **base, "bg_color": "FEF3C7", "border": 1, "border_color": amber,
        })
        self.note_format = workbook.add_format({
            **base, "text_wrap": True, "align": "left",
            "bg_color": light, "border": 1, "border_color": gray,
        })

    # ------------------------------------------------------------------ #
    # Cover sheet                                                          #
    # ------------------------------------------------------------------ #

    def _build_cover_sheet(self, workbook, writer, filename):
        sheet = workbook.add_worksheet("Report Summary")
        writer.sheets["Report Summary"] = sheet

        sheet.merge_range("A1:H4", "")  # Logo space

        sheet.merge_range("A6:H6", "ColtraDataAi Report", self.title_format)
        sheet.merge_range("A8:H8", self.config.get("tagline", ""), self.text_format)

        sheet.write("A10", "Generated On:")
        sheet.write("C10", datetime.now().strftime("%Y-%m-%d %H:%M"))

        sheet.write("A11", "Source File:")
        sheet.write("C11", filename)

        sheet.merge_range(
            "A13:H16",
            "This report provides structured data cleaning outputs including raw data, "
            "cleaned data, logs and quality summaries.",
            self.text_format,
        )
        sheet.merge_range(
            "A20:H20",
            "ColtraDataAi provides data cleaning and structured reporting only.",
            self.small_text,
        )
        sheet.merge_range(
            "A22:H22",
            f"Contact: {self.config.get('contact_email', 'support@coltradata.com')}",
            self.small_text,
        )

    # ------------------------------------------------------------------ #
    # Executive Summary (matplotlib boardroom chart)                       #
    # ------------------------------------------------------------------ #

    def _build_dashboard_sheet(self, workbook, writer, raw_df, log_df):
        ws = workbook.add_worksheet("Executive Summary")
        writer.sheets["Executive Summary"] = ws
        ws.hide_gridlines(2)
        ws.set_zoom(80)
        img_buf = self._make_dashboard_png(raw_df, log_df)
        ws.insert_image("B2", "dashboard.png", {"image_data": img_buf, "x_scale": 1, "y_scale": 1})

    def _make_dashboard_png(self, raw_df, log_df):
        error_df = log_df if (log_df is not None and not log_df.empty) else pd.DataFrame()

        total_cells  = raw_df.size
        missing      = int(raw_df.isnull().sum().sum())
        valid        = max(total_cells - missing, 0)
        completeness = (valid / total_cells * 100) if total_cells else 0
        issues       = len(error_df)
        high_risk    = (
            int(error_df["Risk Level"].isin(["High", "Critical"]).sum())
            if "Risk Level" in error_df.columns else 0
        )

        missing_by_col = (
            raw_df.isnull().sum()
            .sort_values(ascending=False)
            .reset_index()
            .rename(columns={"index": "Column", 0: "Missing Cells"})
        )

        if error_df.empty:
            risk_df  = pd.DataFrame({"Risk Level": ["No issues"], "Issues": [0]})
            issue_df = pd.DataFrame({"Issue": ["No issues"], "Records": [0]})
        else:
            risk_df = (
                error_df["Risk Level"]
                .value_counts()
                .reindex(["Critical", "High", "Medium", "Low"], fill_value=0)
                .reset_index()
            )
            risk_df.columns = ["Risk Level", "Issues"]
            issue_df = error_df["Issue"].value_counts().head(6).reset_index()
            issue_df.columns = ["Issue", "Records"]

        fig = plt.figure(figsize=(22, 10), facecolor="white")
        grid = fig.add_gridspec(2, 4, hspace=0.5, wspace=0.6, top=0.78, bottom=0.08)

        fig.suptitle(
            f"{self.app_name} — Executive Summary",
            x=0.03, y=0.97, ha="left", fontsize=20,
            fontweight="bold", color=BRAND["navy"],
        )
        fig.text(
            0.03, 0.92,
            f"{self.tagline}  |  Powered by {self.company}",
            ha="left", fontsize=11, color=BRAND["muted"],
        )

        kpis = [
            (f"{completeness:.1f}%", "Completeness",   BRAND["teal"]),
            (f"{missing:,}",         "Missing Cells",   BRAND["amber"]),
            (f"{issues:,}",          "Issues Flagged",  BRAND["red"]),
            (f"{high_risk:,}",       "High / Critical", BRAND["purple"]),
        ]
        for i, (val, lbl, color) in enumerate(kpis):
            ax = fig.add_axes([0.03 + i * 0.15, 0.82, 0.13, 0.10])
            ax.axis("off")
            ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, color="#F8FAFC"))
            ax.add_patch(plt.Rectangle((0, 0), 0.03, 1, transform=ax.transAxes, color=color))
            ax.text(0.08, 0.62, val, transform=ax.transAxes, fontsize=22,
                    fontweight="bold", color=BRAND["navy"])
            ax.text(0.08, 0.22, lbl, transform=ax.transAxes, fontsize=10, color=BRAND["muted"])

        ax1 = fig.add_subplot(grid[0, 0])
        ax1.pie([valid, missing], colors=[BRAND["teal"], BRAND["amber"]],
                startangle=90, wedgeprops=dict(width=0.35, edgecolor="white"))
        ax1.text(0,  0.08, f"{completeness:.1f}%", ha="center", fontsize=18, fontweight="bold")
        ax1.text(0, -0.18, "complete", ha="center", fontsize=10, color=BRAND["muted"])
        ax1.set_title("Coverage", loc="left", fontsize=12, fontweight="bold", color=BRAND["navy"])

        ax2 = fig.add_subplot(grid[0, 1:3])
        plot_m = missing_by_col[missing_by_col["Missing Cells"] > 0].tail(6)
        if plot_m.empty:
            ax2.text(0.5, 0.5, "No missing values", ha="center", va="center",
                     transform=ax2.transAxes, fontsize=11, color=BRAND["muted"])
            ax2.axis("off")
        else:
            mc = [BRAND["red"] if v == plot_m["Missing Cells"].max() else BRAND["amber"]
                  for v in plot_m["Missing Cells"]]
            ax2.barh(plot_m["Column"].astype(str), plot_m["Missing Cells"],
                     color=mc, edgecolor="#111827", linewidth=0.3)
            ax2.invert_yaxis()
            ax2.spines[["top", "right", "left"]].set_visible(False)
            ax2.grid(axis="x", color="#E5E7EB", linewidth=0.7)
        ax2.set_title("Where Data Is Thinnest", loc="left", fontsize=12,
                      fontweight="bold", color=BRAND["navy"])

        ax3 = fig.add_subplot(grid[0, 3])
        risk_plot = risk_df[risk_df["Issues"] > 0]
        if risk_plot.empty:
            ax3.text(0.5, 0.5, "No issues", ha="center", va="center",
                     transform=ax3.transAxes, fontsize=11, color=BRAND["muted"])
            ax3.axis("off")
        else:
            rc = [RISK_COLORS.get(r, BRAND["gray"]) for r in risk_plot["Risk Level"]]
            ax3.barh(risk_plot["Risk Level"], risk_plot["Issues"],
                     color=rc, edgecolor="#111827", linewidth=0.3)
            ax3.invert_yaxis()
            ax3.spines[["top", "right", "left"]].set_visible(False)
            ax3.grid(axis="x", color="#E5E7EB", linewidth=0.7)
        ax3.set_title("Risk Profile", loc="left", fontsize=12,
                      fontweight="bold", color=BRAND["navy"])

        ax4 = fig.add_subplot(grid[1, 0:2])
        issue_plot = issue_df[issue_df["Records"] > 0].sort_values("Records")
        if issue_plot.empty:
            ax4.text(0.5, 0.5, "No issues flagged", ha="center", va="center",
                     transform=ax4.transAxes, fontsize=11, color=BRAND["muted"])
            ax4.axis("off")
        else:
            ic = [BRAND["red"] if v == issue_plot["Records"].max() else BRAND["teal"]
                  for v in issue_plot["Records"]]
            ax4.barh(issue_plot["Issue"].astype(str), issue_plot["Records"],
                     color=ic, edgecolor="#111827", linewidth=0.3)
            ax4.spines[["top", "right", "left"]].set_visible(False)
            ax4.grid(axis="x", color="#E5E7EB", linewidth=0.7)
        ax4.set_title("Most Common Issues", loc="left", fontsize=12,
                      fontweight="bold", color=BRAND["navy"])

        ax5 = fig.add_subplot(grid[1, 2:4])
        dtype_counts = raw_df.dtypes.astype(str).value_counts()
        palette = [BRAND["teal"], BRAND["amber"], BRAND["red"], BRAND["purple"], BRAND["green"]]
        ax5.barh(dtype_counts.index.astype(str), dtype_counts.values,
                 color=palette[:len(dtype_counts)], edgecolor="#111827", linewidth=0.3)
        ax5.invert_yaxis()
        ax5.spines[["top", "right", "left"]].set_visible(False)
        ax5.grid(axis="x", color="#E5E7EB", linewidth=0.7)
        ax5.set_title("Column Type Mix", loc="left", fontsize=12,
                      fontweight="bold", color=BRAND["navy"])

        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf

    # ------------------------------------------------------------------ #
    # Data sheets                                                          #
    # ------------------------------------------------------------------ #

    def _write_dataframe(self, writer, df, sheet_name):
        if df is None or df.empty:
            df = pd.DataFrame({"Note": ["No data available."]})

        df.to_excel(writer, sheet_name=sheet_name, index=False)

        workbook  = writer.book
        worksheet = writer.sheets[sheet_name]

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, self.header_format)

        worksheet.freeze_panes(1, 0)

        # Highlight blank cells across all data columns
        last_row = len(df)          # row 0 is header, data is rows 1..last_row
        last_col = len(df.columns) - 1
        blank_fmt = workbook.add_format({"bg_color": "#FFF2CC"})
        worksheet.conditional_format(1, 0, last_row, last_col, {
            "type":   "blanks",
            "format": blank_fmt,
        })

    # ------------------------------------------------------------------ #
    # Missing values chart (native xlsxwriter)                            #
    # ------------------------------------------------------------------ #

    def _build_missing_chart(self, workbook, writer, cleaned_df):
        sheet = workbook.add_worksheet("Dashboard")
        writer.sheets["Dashboard"] = sheet

        missing = cleaned_df.isnull().sum()
        missing = missing[missing > 0]

        sheet.write(0, 0, "Column",         self.header_format)
        sheet.write(0, 1, "Missing Values",  self.header_format)

        sheet.write_column("A2", missing.index.tolist())
        sheet.write_column("B2", missing.values.tolist())

        n = len(missing)
        if n > 0:
            chart = workbook.add_chart({"type": "column"})
            chart.add_series({
                "name":       "Missing Values",
                "categories": f"=Dashboard!$A$2:$A${n + 1}",
                "values":     f"=Dashboard!$B$2:$B${n + 1}",
                "fill":       {"color": BRAND["amber"]},
                "border":     {"color": BRAND["navy"]},
            })
            chart.set_title({"name": "Missing Values by Column"})
            chart.set_x_axis({"name": "Column"})
            chart.set_y_axis({"name": "Missing Count"})
            chart.set_style(10)
            sheet.insert_chart("D2", chart, {"x_scale": 1.6, "y_scale": 1.4})
        else:
            sheet.write(1, 0, "No missing values detected.", self.text_format)

    # ------------------------------------------------------------------ #
    # Processing notes                                                     #
    # ------------------------------------------------------------------ #

    def _build_processing_notes(self, writer):
        workbook = writer.book
        sheet = workbook.add_worksheet("Processing Notes")
        writer.sheets["Processing Notes"] = sheet

        notes = [
            "Data cleaning rules applied:",
            "- Duplicate removal",
            "- Whitespace trimming",
            "- Header standardisation",
            "- Null handling",
            "",
            "Assumptions:",
            "- Input structure preserved where possible",
            "",
            "Limitations:",
            "- Output is non-advisory",
        ]

        for row, text in enumerate(notes):
            sheet.write(row, 0, text)
