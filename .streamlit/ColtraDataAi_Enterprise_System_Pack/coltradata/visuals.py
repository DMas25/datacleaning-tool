from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

plt.switch_backend("Agg")


def _safe_save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def create_visuals(cleaned_df: pd.DataFrame, metrics_df: pd.DataFrame, seg_df: pd.DataFrame, output_dir: Path):
    charts_dir = Path(output_dir) / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    chart_paths = []

    # Chart 1: top numeric metric distributions (first numeric column)
    num_cols = cleaned_df.select_dtypes(include=[np.number]).columns.tolist()
    if num_cols:
        col = num_cols[0]
        fig, ax = plt.subplots(figsize=(8.5, 4.5))
        cleaned_df[col].dropna().plot(kind="hist", bins=25, ax=ax, color="#1F4E78", alpha=0.85)
        ax.set_title(f"Distribution of {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("Frequency")
        p = charts_dir / "01_distribution.png"
        _safe_save(fig, p)
        chart_paths.append(p)

    # Chart 2: top category counts (first categorical column)
    cat_cols = [c for c in cleaned_df.columns if cleaned_df[c].dtype == object or str(cleaned_df[c].dtype).startswith("string")]
    if cat_cols:
        col = cat_cols[0]
        vc = cleaned_df[col].fillna("(blank)").astype(str).value_counts().head(10)
        fig, ax = plt.subplots(figsize=(8.5, 4.5))
        vc.sort_values().plot(kind="barh", ax=ax, color="#4F81BD")
        ax.set_title(f"Top 10 values in {col}")
        ax.set_xlabel("Count")
        ax.set_ylabel(col)
        p = charts_dir / "02_top_categories.png"
        _safe_save(fig, p)
        chart_paths.append(p)

    # Chart 3: completeness by column
    completeness = (1 - cleaned_df.isna().mean()).sort_values(ascending=False) * 100
    if len(completeness) > 0:
        fig, ax = plt.subplots(figsize=(10, 5))
        completeness.plot(kind="bar", ax=ax, color="#9BBB59")
        ax.set_title("Column completeness %")
        ax.set_xlabel("Column")
        ax.set_ylabel("Completeness %")
        ax.tick_params(axis='x', labelrotation=45)
        p = charts_dir / "03_completeness.png"
        _safe_save(fig, p)
        chart_paths.append(p)

    # Chart 4: outlier count by numeric field (derived from metrics and cleaned data)
    if num_cols:
        outlier_counts = {}
        for col in num_cols:
            s = pd.to_numeric(cleaned_df[col], errors='coerce').dropna()
            if len(s) >= 3 and s.nunique() > 1:
                z = ((s - s.mean()) / s.std(ddof=0)).abs()
                outlier_counts[col] = int((z > 3).sum())
        if outlier_counts:
            fig, ax = plt.subplots(figsize=(9, 4.5))
            pd.Series(outlier_counts).sort_values(ascending=False).plot(kind='bar', ax=ax, color='#C0504D')
            ax.set_title('Outlier count by numeric field')
            ax.set_xlabel('Field')
            ax.set_ylabel('Outlier count')
            ax.tick_params(axis='x', labelrotation=45)
            p = charts_dir / "04_outlier_counts.png"
            _safe_save(fig, p)
            chart_paths.append(p)

    return chart_paths
