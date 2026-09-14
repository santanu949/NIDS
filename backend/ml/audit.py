"""
UNSW-NB15 Data Audit Script
============================
Phase 2 – Part A

Produces:
  backend/data/audit_report.json  (machine-readable)
  backend/data/audit_report.txt   (human-readable)

Run from the project root (nids-ml/):
  python -m backend.ml.audit
  -- or --
  python backend/ml/audit.py
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent           # backend/ml/
_BACKEND = _HERE.parent                           # backend/
_DATA_RAW = _BACKEND / "data" / "raw"
_DATA_OUT = _BACKEND / "data"

TRAIN_CSV = _DATA_RAW / "UNSW_NB15_training-set.csv"
TEST_CSV  = _DATA_RAW / "UNSW_NB15_testing-set.csv"

AUDIT_JSON = _DATA_OUT / "audit_report.json"
AUDIT_TXT  = _DATA_OUT / "audit_report.txt"

# Columns that deserve explicit inspection (per task spec)
INSPECT_COLS = ["label", "attack_cat", "id", "proto", "service", "state"]

# Threshold for "near-constant": if a column's most-frequent value accounts
# for >= this fraction of rows, flag it as near-constant.
NEAR_CONSTANT_THRESHOLD = 0.99


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_serialise(obj: Any) -> Any:
    """Recursively make an object JSON-serialisable."""
    if isinstance(obj, dict):
        return {k: _safe_serialise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialise(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


def _load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV robustly, handling UTF-8 BOM."""
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def _count_infinities(df: pd.DataFrame) -> dict[str, int]:
    """Count +/- inf values per numeric column."""
    result: dict[str, int] = {}
    for col in df.select_dtypes(include=[np.number]).columns:
        n = int(np.isinf(df[col].values).sum())
        if n:
            result[col] = n
    return result


def _categorise_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """
    Separate columns into numeric vs categorical based on *actual* dtypes.
    object/string columns → categorical.
    int/float columns     → numeric.
    """
    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    return numeric, categorical


def _near_constant(df: pd.DataFrame, threshold: float) -> list[dict]:
    """Return columns whose dominant value accounts for >= threshold of rows."""
    flagged = []
    n = len(df)
    for col in df.columns:
        counts = df[col].value_counts(dropna=False)
        if len(counts) == 0:
            continue
        top_val = counts.iloc[0]
        frac = top_val / n
        if frac >= threshold:
            flagged.append({
                "column": col,
                "dominant_value": str(counts.index[0]),
                "dominant_count": int(top_val),
                "dominant_fraction": round(float(frac), 6),
                "unique_values": int(df[col].nunique(dropna=False)),
            })
    return flagged


def _inspect_col(df: pd.DataFrame, col: str, top_n: int = 20) -> dict:
    """Produce a per-column inspection dict."""
    if col not in df.columns:
        return {"present": False}
    s = df[col]
    info: dict[str, Any] = {
        "present": True,
        "dtype": str(s.dtype),
        "null_count": int(s.isna().sum()),
        "unique_count": int(s.nunique(dropna=False)),
    }
    # value counts (top_n)
    vc = s.value_counts(dropna=False).head(top_n)
    info["top_value_counts"] = {str(k): int(v) for k, v in vc.items()}
    # numeric extras
    if pd.api.types.is_numeric_dtype(s):
        finite = s.replace([np.inf, -np.inf], np.nan).dropna()
        info["inf_count"] = int(np.isinf(s.values).sum())
        info["min"] = float(finite.min()) if len(finite) else None
        info["max"] = float(finite.max()) if len(finite) else None
        info["mean"] = float(finite.mean()) if len(finite) else None
    return info


def _column_summary(df: pd.DataFrame) -> list[dict]:
    """Return per-column summary for all columns."""
    summaries = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        inf_cnt = int(np.isinf(s.values).sum()) if pd.api.types.is_numeric_dtype(s) else 0
        summaries.append({
            "column": col,
            "dtype": str(s.dtype),
            "null_count": int(s.isna().sum()),
            "inf_count": inf_cnt,
            "unique_count": int(s.nunique(dropna=False)),
            "null_pct": round(float(s.isna().sum() / n * 100), 4),
        })
    return summaries


# ---------------------------------------------------------------------------
# Main audit function
# ---------------------------------------------------------------------------

def audit_dataset(df: pd.DataFrame, name: str) -> dict:
    """Produce a full audit dict for a single DataFrame."""
    numeric_cols, cat_cols = _categorise_columns(df)

    report: dict[str, Any] = {
        "dataset": name,
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "column_names": df.columns.tolist(),
        "column_summary": _column_summary(df),
        "numeric_columns": numeric_cols,
        "categorical_columns": cat_cols,
        "total_missing_values": int(df.isna().sum().sum()),
        "columns_with_missing": df.columns[df.isna().any()].tolist(),
        "total_infinite_values": sum(_count_infinities(df).values()),
        "infinite_values_by_column": _count_infinities(df),
        "duplicate_rows": int(df.duplicated().sum()),
        "near_constant_columns": _near_constant(df, NEAR_CONSTANT_THRESHOLD),
        "target_distribution_label": {
            str(k): int(v)
            for k, v in df["label"].value_counts(dropna=False).items()
        } if "label" in df.columns else {},
        "target_distribution_attack_cat": {
            str(k): int(v)
            for k, v in df["attack_cat"].value_counts(dropna=False).items()
        } if "attack_cat" in df.columns else {},
        "explicit_column_inspection": {
            col: _inspect_col(df, col) for col in INSPECT_COLS
        },
    }
    return report


# ---------------------------------------------------------------------------
# Human-readable formatter
# ---------------------------------------------------------------------------

def _format_txt(train_report: dict, test_report: dict) -> str:
    lines = []

    def section(title: str) -> None:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  {title}")
        lines.append("=" * 70)

    def subsection(title: str) -> None:
        lines.append("")
        lines.append(f"--- {title} ---")

    def kv(k: str, v: Any) -> None:
        lines.append(f"  {k}: {v}")

    lines.append("UNSW-NB15 DATA AUDIT REPORT")
    lines.append("Phase 2 – Part A")
    lines.append("=" * 70)

    for rpt in (train_report, test_report):
        ds = rpt["dataset"]
        section(f"DATASET: {ds}")

        subsection("Shape")
        kv("Rows", rpt["shape"]["rows"])
        kv("Columns", rpt["shape"]["columns"])

        subsection("Column Names")
        for i, c in enumerate(rpt["column_names"], 1):
            lines.append(f"  {i:>2}. {c}")

        subsection("Data Types  (numeric / categorical)")
        kv("Numeric columns", len(rpt["numeric_columns"]))
        lines.append("      " + ", ".join(rpt["numeric_columns"]))
        kv("Categorical columns", len(rpt["categorical_columns"]))
        lines.append("      " + ", ".join(rpt["categorical_columns"]))

        subsection("Missing Values")
        kv("Total missing cells", rpt["total_missing_values"])
        if rpt["columns_with_missing"]:
            kv("Columns with missing", rpt["columns_with_missing"])
        else:
            lines.append("  No missing values detected.")

        subsection("Infinite Values")
        kv("Total inf cells", rpt["total_infinite_values"])
        if rpt["infinite_values_by_column"]:
            for c, n in rpt["infinite_values_by_column"].items():
                lines.append(f"    {c}: {n}")
        else:
            lines.append("  No infinite values detected.")

        subsection("Duplicate Rows")
        kv("Duplicate rows", rpt["duplicate_rows"])

        subsection("Near-Constant Columns (>= 99% same value)")
        if rpt["near_constant_columns"]:
            for item in rpt["near_constant_columns"]:
                lines.append(
                    f"  {item['column']}: dominant='{item['dominant_value']}'"
                    f"  ({item['dominant_fraction']*100:.2f}%)"
                    f"  uniq={item['unique_values']}"
                )
        else:
            lines.append("  None detected at 99% threshold.")

        subsection("Target: label")
        for k, v in rpt["target_distribution_label"].items():
            lines.append(f"  {k}: {v}")

        subsection("Target: attack_cat")
        for k, v in rpt["target_distribution_attack_cat"].items():
            lines.append(f"  {k}: {v}")

        subsection("Explicit Column Inspections")
        for col, info in rpt["explicit_column_inspection"].items():
            lines.append(f"\n  [{col}]")
            if not info.get("present"):
                lines.append("    NOT PRESENT in this dataset.")
                continue
            for field, val in info.items():
                if field == "top_value_counts":
                    lines.append(f"    top_value_counts:")
                    for vk, vv in val.items():
                        lines.append(f"      {vk!r}: {vv}")
                else:
                    lines.append(f"    {field}: {val}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_audit() -> dict:
    print("[audit] Loading training CSV …")
    train_df = _load_csv(TRAIN_CSV)
    print(f"[audit] Training shape: {train_df.shape}")

    print("[audit] Loading testing CSV …")
    test_df = _load_csv(TEST_CSV)
    print(f"[audit] Testing shape: {test_df.shape}")

    print("[audit] Auditing training data …")
    train_report = audit_dataset(train_df, "UNSW_NB15_training-set")

    print("[audit] Auditing testing data …")
    test_report = audit_dataset(test_df, "UNSW_NB15_testing-set")

    full_report = {
        "near_constant_threshold_used": NEAR_CONSTANT_THRESHOLD,
        "train": _safe_serialise(train_report),
        "test": _safe_serialise(test_report),
    }

    # Save JSON
    _DATA_OUT.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_JSON, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
    print(f"[audit] Machine-readable report saved -> {AUDIT_JSON}")

    # Save TXT
    txt = _format_txt(train_report, test_report)
    with open(AUDIT_TXT, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"[audit] Human-readable report saved  -> {AUDIT_TXT}")

    return full_report


if __name__ == "__main__":
    # Allow running as: python backend/ml/audit.py
    # Add project root to sys.path if needed
    _project_root = Path(__file__).resolve().parents[2]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    run_audit()
    print("[audit] Done.")
