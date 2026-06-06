from pathlib import Path
from datetime import datetime
from .io_utils import load_input_file
from .pipeline import build_report_data, write_excel_report


def run_pipeline_from_uploaded_file(uploaded_file, output_dir="output", z_threshold=3.0, include_dashboard=True):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_path = output_dir / uploaded_file.name
    temp_path.write_bytes(uploaded_file.read())
    return run_pipeline_from_path(temp_path, output_dir=output_dir, z_threshold=z_threshold, include_dashboard=include_dashboard)


def run_pipeline_from_path(input_path, output_dir="output", z_threshold=3.0, include_dashboard=True):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    loaded = load_input_file(input_path)
    report_data = build_report_data(loaded, z_threshold=z_threshold, include_dashboard=include_dashboard, output_dir=output_dir)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"ColtraDataAi_Refined_Report_{ts}.xlsx"
    write_excel_report(report_data, output_path)

    preview = {
        "rows": len(report_data["cleaned_df"]),
        "columns": len(report_data["cleaned_df"].columns),
        "duplicates_removed": report_data["summary"]["duplicates_removed"],
        "issue_count": int(len(report_data["outlier_log"])),
        "detected_sheets": loaded.get("detected_sheets", {}),
    }
    return str(output_path), preview
