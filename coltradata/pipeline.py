from __future__ import annotations
from pathlib import Path
import math
import pandas as pd
import numpy as np
from scipy.stats import zscore
from .visuals import create_visuals

PROTECTED_SHEETS = {
    "Raw Data",
    "Cleaned Data",
    "Executive Summary",
    "Data Quality Summary",
    "Missing Values",
    "Key Metrics Summary",
    "Segmentation Summary",
    "Outlier Log",
    "Outlier Summary",
    "Dashboard Data",
    "Dashboard",
    "Data Dictionary",
    "Disclaimer",
}


def _standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [
        str(c).strip().replace(" ", "_").replace("-", "_").replace("/", "_")
        for c in out.columns
    ]
    return out


def _normalise_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    obj_cols = out.select_dtypes(include=["object", "string"]).columns
    for col in obj_cols:
        out[col] = out[col].astype("string").str.strip()
        # title case for low-cardinality categoricals only
        nunique = out[col].nunique(dropna=True)
        if nunique and nunique <= 50:
            out[col] = out[col].str.replace(r"\s+", " ", regex=True)
    return out


def _coerce_dates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    corrections = {}
    for col in out.columns:
        if out[col].dtype == object or str(out[col].dtype).startswith("string"):
            sample = out[col].dropna().astype(str).head(30)
            if sample.empty:
                continue
            parsed = pd.to_datetime(sample, errors="coerce", dayfirst=False)
            success_rate = parsed.notna().mean() if len(parsed) else 0
            if success_rate >= 0.6:
                full = pd.to_datetime(out[col], errors="coerce", dayfirst=False)
                if full.notna().sum() > 0:
                    out[col] = full.dt.strftime("%Y-%m-%d")
                    corrections[col] = "Converted to YYYY-MM-DD"
    return out, corrections


def _coerce_numeric(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    corrections = {}
    for col in out.columns:
        if out[col].dtype == object or str(out[col].dtype).startswith("string"):
            temp = pd.to_numeric(out[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
            success_rate = temp.notna().mean()
            if success_rate >= 0.7:
                out[col] = temp.round(2)
                corrections[col] = "Converted to numeric and rounded to 2 decimals"
        elif pd.api.types.is_numeric_dtype(out[col]):
            out[col] = pd.to_numeric(out[col], errors="coerce").round(2)
    return out, corrections


def _duplicates_removed(before_len: int, after_len: int) -> int:
    return max(before_len - after_len, 0)


def _missing_values_table(df: pd.DataFrame) -> pd.DataFrame:
    missing = df.isna().sum()
    complete_pct = (1 - df.isna().mean()) * 100
    out = pd.DataFrame({
        "Column": df.columns,
        "Missing_Values": [int(missing[c]) for c in df.columns],
        "Completeness_%": [round(float(complete_pct[c]), 2) for c in df.columns],
    })
    out["RAG_Status"] = out["Completeness_%"].apply(lambda x: "Green" if x >= 95 else ("Amber" if x >= 80 else "Red"))
    return out


def _data_dictionary(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        sample = df[col].dropna().iloc[0] if df[col].dropna().shape[0] else ""
        records.append({
            "Column_Name": col,
            "Data_Type": dtype,
            "Sample_Value": str(sample),
            "Description": "Auto-detected field from source dataset",
        })
    return pd.DataFrame(records)


def _key_metrics(df: pd.DataFrame) -> pd.DataFrame:
    num_df = df.select_dtypes(include=[np.number])
    rows = []
    for col in num_df.columns:
        s = num_df[col]
        rows.append({
            "Metric": col,
            "Sum": round(float(s.sum()), 2),
            "Average": round(float(s.mean()), 2) if s.notna().any() else None,
            "Median": round(float(s.median()), 2) if s.notna().any() else None,
            "Minimum": round(float(s.min()), 2) if s.notna().any() else None,
            "Maximum": round(float(s.max()), 2) if s.notna().any() else None,
        })
    return pd.DataFrame(rows)


def _segmentation_summary(df: pd.DataFrame, top_n=10) -> pd.DataFrame:
    obj_cols = [c for c in df.columns if df[c].dtype == object or str(df[c].dtype).startswith("string")]
    records = []
    for col in obj_cols:
        vc = df[col].fillna("(blank)").astype(str).value_counts().head(top_n)
        total = vc.sum()
        for name, count in vc.items():
            records.append({
                "Field": col,
                "Value": name,
                "Count": int(count),
                "Share_%": round((count / total) * 100, 2) if total else 0,
            })
    return pd.DataFrame(records)


def _outlier_log(df: pd.DataFrame, z_threshold=3.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    log_rows = []
    summary_rows = []
    for col in num_cols:
        series = df[col].astype(float)
        non_null = series.dropna()
        if len(non_null) < 3 or non_null.nunique() < 2:
            continue
        z = pd.Series(zscore(non_null, nan_policy="omit"), index=non_null.index)
        mask = z.abs() > z_threshold
        idxs = z[mask].index.tolist()
        q1 = float(non_null.quantile(0.25))
        q3 = float(non_null.quantile(0.75))
        iqr = q3 - q1
        lower = round(q1 - 1.5 * iqr, 2)
        upper = round(q3 + 1.5 * iqr, 2)
        summary_rows.append({
            "Column_Name": col,
            "Normal_Range": f"{lower} to {upper}",
            "Outlier_Count": len(idxs),
            "Risk_Level": "Medium" if len(idxs) > 0 else "None",
        })
        for idx in idxs:
            value = series.loc[idx]
            deviation = round(float(abs(z.loc[idx])), 2) if pd.notna(z.loc[idx]) else None
            log_rows.append({
                "Row_ID": int(idx) + 2,
                "Column_Name": col,
                "Issue_Type": "Statistical Outlier",
                "Risk_Level": "Medium",
                "Detected_Value": round(float(value), 2) if pd.notna(value) else value,
                "Expected_Range": f"{lower} to {upper}",
                "Deviation_ZScore": deviation,
                "Notes": "Automatically detected using z-score threshold",
            })
    return pd.DataFrame(log_rows), pd.DataFrame(summary_rows)


def _dashboard_data(metrics_df: pd.DataFrame, seg_df: pd.DataFrame) -> pd.DataFrame:
    # a compact flat table useful for charts and auditing
    metrics_part = metrics_df.copy()
    metrics_part.insert(0, "Section", "Metric")
    metrics_part.rename(columns={"Metric": "Name"}, inplace=True)
    for missing_col in ["Count", "Share_%", "Value"]:
        if missing_col not in metrics_part.columns:
            metrics_part[missing_col] = None
    seg_part = seg_df.copy()
    if not seg_part.empty:
        seg_part = seg_part.rename(columns={"Field": "Section", "Value": "Name"})
        for col in ["Sum", "Average", "Median", "Minimum", "Maximum"]:
            if col not in seg_part.columns:
                seg_part[col] = None
    combined = pd.concat([metrics_part, seg_part], ignore_index=True, sort=False)
    return combined


def build_report_data(loaded: dict, z_threshold=3.0, include_dashboard=True, output_dir: Path | str = "output"):
    raw_df = loaded["raw_df"].copy()
    base_df = loaded.get("cleaned_df")
    if base_df is None or base_df.empty:
        base_df = raw_df.copy()

    before_len = len(base_df)
    cleaned_df = _standardise_columns(base_df)
    cleaned_df = _normalise_text(cleaned_df)
    cleaned_df, date_corrections = _coerce_dates(cleaned_df)
    cleaned_df, numeric_corrections = _coerce_numeric(cleaned_df)
    cleaned_df = cleaned_df.drop_duplicates().reset_index(drop=True)
    after_len = len(cleaned_df)

    duplicates_removed = _duplicates_removed(before_len, after_len)
    missing_tbl = _missing_values_table(cleaned_df)
    key_metrics = _key_metrics(cleaned_df)
    seg_summary = _segmentation_summary(cleaned_df)
    outlier_log, outlier_summary = _outlier_log(cleaned_df, z_threshold=z_threshold)
    ddict = _data_dictionary(cleaned_df)

    summary = {
        "source_name": loaded.get("source_name", ""),
        "raw_rows": len(raw_df),
        "raw_columns": len(raw_df.columns),
        "clean_rows": len(cleaned_df),
        "clean_columns": len(cleaned_df.columns),
        "duplicates_removed": duplicates_removed,
        "missing_cells": int(cleaned_df.isna().sum().sum()),
        "issue_count": int(len(outlier_log)),
        "critical_issues": 0,
        "high_risk_issues": 0,
        "medium_risk_issues": int(len(outlier_log)),
        "low_risk_issues": 0,
        "quarantined_rows": 0,
        "date_corrections": len(date_corrections),
        "numeric_corrections": len(numeric_corrections),
        "columns_with_missing": int((missing_tbl["Missing_Values"] > 0).sum()),
    }

    issues_by_row = outlier_log.groupby("Row_ID").size().rename("Issue_Count") if not outlier_log.empty else pd.Series(dtype=int)
    cleaned_df = cleaned_df.copy()
    cleaned_df.insert(len(cleaned_df.columns), "Issue_Flag", cleaned_df.index.map(lambda i: "Yes" if (i + 2) in issues_by_row.index else "No"))
    cleaned_df.insert(len(cleaned_df.columns), "Issue_Count", cleaned_df.index.map(lambda i: int(issues_by_row.get(i + 2, 0))))

    dashboard_data = _dashboard_data(key_metrics, seg_summary)
    chart_paths = create_visuals(cleaned_df, key_metrics, seg_summary, output_dir=Path(output_dir)) if include_dashboard else []

    disclaimer_df = pd.DataFrame({
        "Statement": [
            "ColtraDataAi performs automated data cleaning, structuring, and issue flagging only.",
            "This report does not provide recommendations, advice, or business interpretation.",
            "Outliers are detected using statistical rules and should be reviewed by the user.",
            "Users remain responsible for validation and downstream decision-making.",
            "No liability is accepted for outcomes derived from use of this report.",
        ]
    })

    executive_df = pd.DataFrame({
        "Metric": [
            "Source File",
            "Raw Rows",
            "Raw Columns",
            "Cleaned Rows",
            "Cleaned Columns",
            "Duplicates Removed",
            "Missing Cells",
            "Issues Flagged",
            "Critical Issues",
            "High Risk Issues",
            "Medium Risk Issues",
            "Low Risk Issues",
            "Quarantined Rows",
            "Date Corrections Applied",
            "Numeric Corrections Applied",
        ],
        "Value": [
            summary["source_name"],
            summary["raw_rows"],
            summary["raw_columns"],
            summary["clean_rows"],
            summary["clean_columns"],
            summary["duplicates_removed"],
            summary["missing_cells"],
            summary["issue_count"],
            summary["critical_issues"],
            summary["high_risk_issues"],
            summary["medium_risk_issues"],
            summary["low_risk_issues"],
            summary["quarantined_rows"],
            summary["date_corrections"],
            summary["numeric_corrections"],
        ]
    })

    data_quality_summary = pd.DataFrame({
        "Measure": [
            "Completeness Overall %",
            "Columns With Missing Values",
            "Columns Fully Complete",
            "Date Corrections Applied",
            "Numeric Corrections Applied",
        ],
        "Value": [
            round((1 - cleaned_df.isna().sum().sum() / max(cleaned_df.size, 1)) * 100, 2),
            summary["columns_with_missing"],
            int((missing_tbl["Missing_Values"] == 0).sum()),
            summary["date_corrections"],
            summary["numeric_corrections"],
        ]
    })

    return {
        "raw_df": raw_df,
        "cleaned_df": cleaned_df,
        "executive_df": executive_df,
        "data_quality_summary": data_quality_summary,
        "missing_tbl": missing_tbl,
        "key_metrics": key_metrics,
        "segmentation_summary": seg_summary,
        "outlier_log": outlier_log,
        "outlier_summary": outlier_summary,
        "dashboard_data": dashboard_data,
        "data_dictionary": ddict,
        "disclaimer_df": disclaimer_df,
        "summary": summary,
        "chart_paths": chart_paths,
    }


def _autofit_worksheet(ws, df, max_width=42):
    for idx, col in enumerate(df.columns):
        series = df[col].astype(str) if col in df.columns else []
        max_len = max([len(str(col))] + ([series.map(len).max()] if len(df) else [0]))
        ws.set_column(idx, idx, min(max_len + 2, max_width))
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(len(df), 1), max(len(df.columns) - 1, 0))


def write_excel_report(report_data: dict, output_path: Path):
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        wb = writer.book

        fmt_header = wb.add_format({"bold": True, "bg_color": "#1F4E78", "font_color": "white", "border": 1})
        fmt_green = wb.add_format({"bg_color": "#C6E0B4"})
        fmt_amber = wb.add_format({"bg_color": "#FFD966"})
        fmt_red = wb.add_format({"bg_color": "#F4CCCC"})
        fmt_title = wb.add_format({"bold": True, "font_size": 14})

        sheet_map = {
            "Raw Data": report_data["raw_df"],
            "Cleaned Data": report_data["cleaned_df"],
            "Executive Summary": report_data["executive_df"],
            "Data Quality Summary": report_data["data_quality_summary"],
            "Missing Values": report_data["missing_tbl"],
            "Key Metrics Summary": report_data["key_metrics"],
            "Segmentation Summary": report_data["segmentation_summary"],
            "Outlier Log": report_data["outlier_log"],
            "Outlier Summary": report_data["outlier_summary"],
            "Dashboard Data": report_data["dashboard_data"],
            "Data Dictionary": report_data["data_dictionary"],
            "Disclaimer": report_data["disclaimer_df"],
        }

        for sheet_name, df in sheet_map.items():
            safe_df = df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
            safe_df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            for col_num, value in enumerate(safe_df.columns.values):
                ws.write(0, col_num, value, fmt_header)
            _autofit_worksheet(ws, safe_df)

            if sheet_name == "Missing Values" and not safe_df.empty and "RAG_Status" in safe_df.columns:
                rag_col = safe_df.columns.get_loc("RAG_Status")
                for row in range(1, len(safe_df) + 1):
                    val = safe_df.iloc[row - 1, rag_col]
                    if val == "Green":
                        ws.write(row, rag_col, val, fmt_green)
                    elif val == "Amber":
                        ws.write(row, rag_col, val, fmt_amber)
                    elif val == "Red":
                        ws.write(row, rag_col, val, fmt_red)

        dashboard_ws = wb.add_worksheet("Dashboard")
        writer.sheets["Dashboard"] = dashboard_ws
        dashboard_ws.write(0, 0, "ColtraDataAi Dashboard", fmt_title)
        dashboard_ws.write(2, 0, "This dashboard contains automated visuals generated from the cleaned dataset.")

        row = 4
        for chart_path in report_data.get("chart_paths", []):
            dashboard_ws.insert_image(row, 0, str(chart_path), {"x_scale": 0.9, "y_scale": 0.9})
            row += 22

        dashboard_ws.set_column(0, 8, 20)
