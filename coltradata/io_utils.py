from pathlib import Path
import pandas as pd


def load_input_file(input_path):
    input_path = Path(input_path)
    suffix = input_path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(input_path)
        return {
            "raw_df": df.copy(),
            "cleaned_df": None,
            "detected_sheets": {"raw": input_path.name, "cleaned": None},
            "source_name": input_path.name,
        }

    if suffix in {".xlsx", ".xls"}:
        xls = pd.ExcelFile(input_path)
        sheets = xls.sheet_names
        raw_name = None
        clean_name = None
        for s in sheets:
            sn = s.strip().lower()
            if raw_name is None and "raw" in sn:
                raw_name = s
            if clean_name is None and "clean" in sn:
                clean_name = s
        if raw_name is None and sheets:
            raw_name = sheets[0]
        if clean_name is None and len(sheets) > 1:
            clean_name = sheets[1]
        raw_df = pd.read_excel(input_path, sheet_name=raw_name) if raw_name else pd.DataFrame()
        cleaned_df = pd.read_excel(input_path, sheet_name=clean_name) if clean_name else None
        return {
            "raw_df": raw_df,
            "cleaned_df": cleaned_df,
            "detected_sheets": {"raw": raw_name, "cleaned": clean_name},
            "source_name": input_path.name,
        }

    raise ValueError("Unsupported file type. Please use CSV, XLSX, or XLS.")
