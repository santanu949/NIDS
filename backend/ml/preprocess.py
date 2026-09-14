"""
UNSW-NB15 Reusable Preprocessing Pipeline
==========================================
Phase 2 – Parts C, D, E, F

Public API
----------
build_preprocessor()
    Returns an unfitted sklearn Pipeline.

load_data(split="train"|"test")
    Loads the raw CSV for the requested split.

prepare_Xy(df, schema)
    Separates target from features using the schema.

fit_and_save(random_state=42)
    Fits the preprocessor on training data,
    creates a stratified validation split,
    saves the fitted preprocessor to disk.

load_preprocessor()
    Loads the saved preprocessor from disk.

transform(df, fitted_preprocessor, schema)
    Applies a fitted preprocessor to new/raw data.

Run from the project root (nids-ml/):
    python -m backend.ml.preprocess
  -- or --
    python backend/ml/preprocess.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent           # backend/ml/
_BACKEND = _HERE.parent                           # backend/
_DATA_RAW = _BACKEND / "data" / "raw"
_ARTIFACTS = _HERE / "artifacts"
_SCHEMA_PATH = _BACKEND / "data" / "feature_schema.json"

TRAIN_CSV = _DATA_RAW / "UNSW_NB15_training-set.csv"
TEST_CSV = _DATA_RAW / "UNSW_NB15_testing-set.csv"

PREPROCESSOR_PATH = _ARTIFACTS / "preprocessor.joblib"
VAL_INDICES_PATH = _ARTIFACTS / "val_indices.json"

# ---------------------------------------------------------------------------
# Schema loader
# ---------------------------------------------------------------------------

def load_schema() -> dict:
    """Load the feature schema JSON."""
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

def load_data(split: str = "train") -> pd.DataFrame:
    """
    Load the raw CSV for the requested split.

    Parameters
    ----------
    split : "train" | "test"

    Returns
    -------
    pd.DataFrame  (unchanged from disk)
    """
    if split == "train":
        path = TRAIN_CSV
    elif split == "test":
        path = TEST_CSV
    else:
        raise ValueError(f"split must be 'train' or 'test', got {split!r}")

    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    print(f"[preprocess] Loaded {split} data: shape={df.shape}")
    return df


# ---------------------------------------------------------------------------
# Infinity -> NaN conversion
# ---------------------------------------------------------------------------

def replace_infinities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replace +inf / -inf with NaN in all numeric columns.

    This must be applied BEFORE sklearn imputation.
    It is applied inside the raw-load step so the pipeline sees clean inputs.
    Note: this does NOT fit anything; it is a deterministic transformation.
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df = df.copy()
    df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
    return df


# ---------------------------------------------------------------------------
# X / y separation
# ---------------------------------------------------------------------------

def prepare_Xy(
    df: pd.DataFrame,
    schema: dict,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Separate features (X) from the binary target (y).

    Rules
    -----
    - Drop all excluded_columns (id, label, attack_cat).
    - Retain only the columns listed in final_feature_order.
    - Verify no target column leaks into X.
    - Enforce final_feature_order exactly.

    Parameters
    ----------
    df     : raw DataFrame (after replace_infinities)
    schema : loaded feature_schema.json dict

    Returns
    -------
    X : pd.DataFrame  (features only, ordered per schema)
    y : pd.Series     (binary label, int)
    """
    target_col = schema["target_column"]          # "label"
    excluded = set(schema["excluded_columns"].keys())  # {id, label, attack_cat}
    feature_order: list[str] = schema["final_feature_order"]

    # --- safety checks ---
    assert target_col in df.columns, f"Target column '{target_col}' missing from data."
    for col in excluded:
        if col != target_col and col in df.columns:
            pass  # will be dropped below

    y = df[target_col].astype(int)

    # Select only columns in feature_order (drops excluded automatically)
    missing_features = [c for c in feature_order if c not in df.columns]
    if missing_features:
        raise ValueError(f"Features missing from data: {missing_features}")

    X = df[feature_order].copy()

    # Verify no target leak
    assert target_col not in X.columns, "BUG: target column leaked into X!"
    assert "attack_cat" not in X.columns, "BUG: attack_cat leaked into X!"
    assert "id" not in X.columns, "BUG: id leaked into X!"

    return X, y


# ---------------------------------------------------------------------------
# Preprocessor builder
# ---------------------------------------------------------------------------

def build_preprocessor(schema: dict) -> Pipeline:
    """
    Build an unfitted sklearn preprocessing Pipeline.

    Numeric path
    ------------
    1. SimpleImputer(strategy="median")
       – handles NaN from: real missing data, or infinities converted to NaN
    2. StandardScaler()
       – required for distance-based and linear models; tree-based models may
         ignore it at evaluation time but it is already inside the pipeline.

    Categorical path
    ----------------
    1. SimpleImputer(strategy="most_frequent")
       – handles NaN for unseen inference rows
    2. OneHotEncoder(handle_unknown="ignore", sparse_output=False)
       – consistent encoding; unknown categories at inference -> all-zero row

    Parameters
    ----------
    schema : loaded feature_schema.json dict

    Returns
    -------
    sklearn Pipeline (unfitted)
    """
    num_cols: list[str] = schema["numeric_feature_columns"]
    cat_cols: list[str] = schema["categorical_feature_columns"]

    numeric_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    # remainder="drop" ensures any column not explicitly listed is dropped.
    # This is the safe default – no accidental feature leakage from stray cols.
    column_transformer = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, num_cols),
            ("categorical", categorical_pipeline, cat_cols),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    pipeline = Pipeline(steps=[
        ("preprocessor", column_transformer),
    ])

    return pipeline


# ---------------------------------------------------------------------------
# Validation split helper
# ---------------------------------------------------------------------------

def make_validation_split(
    X: pd.DataFrame,
    y: pd.Series,
    val_size: float = 0.20,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Create a stratified train/validation split from the training data.

    Parameters
    ----------
    X            : feature DataFrame (from prepare_Xy on train CSV)
    y            : target Series
    val_size     : fraction of training data to use for validation (default 0.20)
    random_state : fixed seed for reproducibility (default 42)

    Returns
    -------
    X_tr, X_val, y_tr, y_val
    """
    X_tr, X_val, y_tr, y_val = train_test_split(
        X, y,
        test_size=val_size,
        stratify=y,
        random_state=random_state,
        shuffle=True,
    )
    print(
        f"[preprocess] Validation split: "
        f"train={len(y_tr):,}  val={len(y_val):,}  "
        f"(stratified, random_state={random_state})"
    )
    return X_tr, X_val, y_tr, y_val


# ---------------------------------------------------------------------------
# Fit and save
# ---------------------------------------------------------------------------

def fit_and_save(random_state: int = 42) -> dict:
    """
    Full fit workflow:
      1. Load training data.
      2. Replace infinities.
      3. Separate X / y.
      4. Create stratified validation split.
      5. Fit preprocessor on X_train (not X_val, never test).
      6. Save fitted preprocessor to disk.
      7. Return metadata dict.

    The test CSV is deliberately NOT loaded here.
    """
    schema = load_schema()

    # --- load & clean ---
    train_df = load_data("train")
    train_df = replace_infinities(train_df)

    # --- X / y split ---
    X, y = prepare_Xy(train_df, schema)
    print(f"[preprocess] Feature matrix shape: {X.shape}  |  target shape: {y.shape}")

    # --- validation split (from training only) ---
    X_tr, X_val, y_tr, y_val = make_validation_split(X, y, random_state=random_state)

    # --- build & fit (FIT ON X_tr ONLY) ---
    preprocessor = build_preprocessor(schema)
    print("[preprocess] Fitting preprocessor on training partition …")
    preprocessor.fit(X_tr)
    print("[preprocess] Preprocessing fitted.")

    # --- save artifacts ---
    _ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, PREPROCESSOR_PATH)
    print(f"[preprocess] Preprocessor saved -> {PREPROCESSOR_PATH}")

    # Save validation indices for reproducibility
    val_idx_data = {
        "random_state": random_state,
        "val_fraction": 0.20,
        "train_indices": X_tr.index.tolist(),
        "val_indices": X_val.index.tolist(),
    }
    with open(VAL_INDICES_PATH, "w", encoding="utf-8") as f:
        json.dump(val_idx_data, f)
    print(f"[preprocess] Validation indices saved -> {VAL_INDICES_PATH}")

    meta = {
        "train_rows": int(len(X_tr)),
        "val_rows": int(len(X_val)),
        "n_features_in": int(X_tr.shape[1]),
        "random_state": random_state,
        "preprocessor_path": str(PREPROCESSOR_PATH),
    }
    return meta


# ---------------------------------------------------------------------------
# Load preprocessor
# ---------------------------------------------------------------------------

def load_preprocessor() -> Pipeline:
    """Load the fitted preprocessor from disk."""
    if not PREPROCESSOR_PATH.exists():
        raise FileNotFoundError(
            f"Preprocessor not found at {PREPROCESSOR_PATH}. "
            "Run fit_and_save() first."
        )
    return joblib.load(PREPROCESSOR_PATH)


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

def transform(
    df: pd.DataFrame,
    fitted_preprocessor: Pipeline,
    schema: dict,
) -> tuple[np.ndarray, pd.Series]:
    """
    Apply a FITTED preprocessor to raw data (training or inference).

    Steps:
      1. Replace infinities -> NaN.
      2. Separate X / y using the schema.
      3. Apply the fitted preprocessor (no re-fitting).

    Parameters
    ----------
    df                  : raw DataFrame (includes target column)
    fitted_preprocessor : previously fitted Pipeline
    schema              : feature schema dict

    Returns
    -------
    X_transformed : np.ndarray  (shape: [n_rows, n_output_features])
    y             : pd.Series   (binary target)
    """
    df = replace_infinities(df)
    X, y = prepare_Xy(df, schema)
    X_transformed = fitted_preprocessor.transform(X)
    return X_transformed, y


# ---------------------------------------------------------------------------
# Entry point – runs the full workflow and prints a summary
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow running as: python backend/ml/preprocess.py
    _project_root = Path(__file__).resolve().parents[2]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

    print("=" * 60)
    print("UNSW-NB15 Preprocessing Pipeline – Phase 2")
    print("=" * 60)

    meta = fit_and_save()

    print("\n[preprocess] Fit metadata:")
    for k, v in meta.items():
        print(f"  {k}: {v}")

    print("\n[preprocess] Verifying transform on training data …")
    schema = load_schema()
    fitted = load_preprocessor()
    train_df = load_data("train")
    X_tr_t, y_tr = transform(train_df, fitted, schema)
    print(f"  X_train transformed shape: {X_tr_t.shape}")
    print(f"  NaN in X_train: {np.isnan(X_tr_t).sum()}")
    print(f"  Inf in X_train: {np.isinf(X_tr_t).sum()}")

    print("\n[preprocess] Verifying transform on TEST data …")
    test_df = load_data("test")
    X_te_t, y_te = transform(test_df, fitted, schema)
    print(f"  X_test transformed shape:  {X_te_t.shape}")
    print(f"  NaN in X_test:  {np.isnan(X_te_t).sum()}")
    print(f"  Inf in X_test:  {np.isinf(X_te_t).sum()}")

    assert X_tr_t.shape[1] == X_te_t.shape[1], \
        "FAIL: training and testing feature counts differ!"
    print("\n[preprocess] Feature count consistent: OK")
    print("[preprocess] Done.")
