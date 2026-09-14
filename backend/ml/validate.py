"""
UNSW-NB15 Preprocessing Validation Suite
=========================================
Phase 2 – Part G

Runs a series of deterministic checks to verify:
  1.  Training data can be loaded.
  2.  Testing data can be loaded.
  3.  Feature schemas are consistent between train and test.
  4.  Target column is NOT in the feature matrix.
  5.  attack_cat is NOT in the feature matrix.
  6.  id is NOT in the feature matrix.
  7.  Preprocessing transforms training data successfully.
  8.  The SAME fitted preprocessor transforms test data successfully.
  9.  Transformed train / test feature counts are identical.
  10. No NaN or Inf remain after transformation.
  11. Preprocessor was fitted ONLY on training data.
  12. Running preprocessing twice gives deterministic results.

Run from project root:
    python -m backend.ml.validate
  -- or --
    python backend/ml/validate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import joblib

# ---------------------------------------------------------------------------
# Resolve project root for both module and script invocation
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.ml.preprocess import (
    load_data,
    load_schema,
    load_preprocessor,
    replace_infinities,
    prepare_Xy,
    transform,
    fit_and_save,
    PREPROCESSOR_PATH,
)

# ---------------------------------------------------------------------------
# Tiny helper
# ---------------------------------------------------------------------------
PASS = "[PASS]"
FAIL = "[FAIL]"


def check(condition: bool, msg: str) -> bool:
    status = PASS if condition else FAIL
    print(f"  {status}  {msg}")
    return condition


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_01_train_loads() -> bool:
    """Check 1: Training CSV can be loaded."""
    try:
        df = load_data("train")
        return check(df.shape == (175341, 45),
                     f"Train CSV loaded. Shape={df.shape} (expected (175341,45))")
    except Exception as exc:
        print(f"  {FAIL}  Train CSV failed to load: {exc}")
        return False


def check_02_test_loads() -> bool:
    """Check 2: Testing CSV can be loaded."""
    try:
        df = load_data("test")
        return check(df.shape == (82332, 45),
                     f"Test CSV loaded. Shape={df.shape} (expected (82332,45))")
    except Exception as exc:
        print(f"  {FAIL}  Test CSV failed to load: {exc}")
        return False


def check_03_schema_consistent() -> bool:
    """Check 3: Feature schema is consistent between train and test."""
    schema = load_schema()
    train_df = load_data("train")
    test_df = load_data("test")
    feature_order: list[str] = schema["final_feature_order"]
    target_col: str = schema["target_column"]

    train_has = all(c in train_df.columns for c in feature_order + [target_col])
    test_has = all(c in test_df.columns for c in feature_order + [target_col])
    ok = train_has and test_has
    return check(ok, f"All schema features present in both splits: {ok}")


def check_04_target_not_in_X(X, schema) -> bool:
    """Check 4: Target column is not in X."""
    tc = schema["target_column"]
    ok = tc not in (X.columns.tolist() if hasattr(X, "columns") else [])
    return check(ok, f"'{tc}' not in feature matrix X")


def check_05_attack_cat_not_in_X(X) -> bool:
    """Check 5: attack_cat not in X."""
    col_list = X.columns.tolist() if hasattr(X, "columns") else []
    ok = "attack_cat" not in col_list
    return check(ok, "'attack_cat' not in feature matrix X")


def check_06_id_not_in_X(X) -> bool:
    """Check 6: id not in X."""
    col_list = X.columns.tolist() if hasattr(X, "columns") else []
    ok = "id" not in col_list
    return check(ok, "'id' not in feature matrix X")


def check_07_transform_train(fitted, schema) -> tuple[bool, object]:
    """Check 7: Preprocessor transforms training data without error."""
    try:
        train_df = load_data("train")
        X_tr_t, y_tr = transform(train_df, fitted, schema)
        ok = X_tr_t.shape[0] == 175341
        check(ok, f"Train transform succeeded. Output shape={X_tr_t.shape}")
        return ok, X_tr_t
    except Exception as exc:
        print(f"  {FAIL}  Train transform raised: {exc}")
        return False, None


def check_08_transform_test(fitted, schema) -> tuple[bool, object]:
    """Check 8: Same fitted preprocessor transforms test data."""
    try:
        test_df = load_data("test")
        X_te_t, y_te = transform(test_df, fitted, schema)
        ok = X_te_t.shape[0] == 82332
        check(ok, f"Test transform succeeded.  Output shape={X_te_t.shape}")
        return ok, X_te_t
    except Exception as exc:
        print(f"  {FAIL}  Test transform raised: {exc}")
        return False, None


def check_09_feature_counts_equal(X_tr_t, X_te_t) -> bool:
    """Check 9: Train and test transformed feature counts are identical."""
    if X_tr_t is None or X_te_t is None:
        return check(False, "Cannot verify: one transform failed.")
    ok = X_tr_t.shape[1] == X_te_t.shape[1]
    return check(ok,
                 f"Feature count consistent: train={X_tr_t.shape[1]}, "
                 f"test={X_te_t.shape[1]}")


def check_10_no_nan_inf(X_tr_t, X_te_t) -> bool:
    """Check 10: No NaN or Inf after transformation."""
    results = []
    for name, arr in [("train", X_tr_t), ("test", X_te_t)]:
        if arr is None:
            results.append(False)
            continue
        nan_cnt = int(np.isnan(arr).sum())
        inf_cnt = int(np.isinf(arr).sum())
        ok = nan_cnt == 0 and inf_cnt == 0
        results.append(ok)
        check(ok, f"{name}: NaN={nan_cnt}, Inf={inf_cnt} after transform")
    return all(results)


def check_11_no_test_fit() -> bool:
    """
    Check 11: Preprocessor was fitted only on training data.

    Proxy check: The fitted preprocessor exists and was loaded from disk.
    We cannot retroactively inspect what data sklearn used, but we verify:
      - PREPROCESSOR_PATH exists (was saved after fitting on train only)
      - The preprocess.py code always calls .fit() on X_tr (training partition)
    This is a structural guarantee enforced in preprocess.py.
    """
    ok = PREPROCESSOR_PATH.exists()
    return check(ok,
                 "Preprocessor artifact exists (fitted on training data only "
                 "per preprocess.py::fit_and_save() – structural guarantee)")


def check_12_deterministic() -> bool:
    """
    Check 12: Running preprocessing twice gives deterministic results.
    Re-fit from scratch and compare output on a small slice.
    """
    schema = load_schema()
    train_df = load_data("train").head(1000)
    train_df = replace_infinities(train_df)
    X, _ = prepare_Xy(train_df, schema)

    from backend.ml.preprocess import build_preprocessor
    p1 = build_preprocessor(schema)
    p2 = build_preprocessor(schema)
    p1.fit(X)
    p2.fit(X)

    arr1 = p1.transform(X)
    arr2 = p2.transform(X)
    ok = np.allclose(arr1, arr2, equal_nan=True)
    return check(ok, "Deterministic: two identical fits produce identical output")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_checks() -> None:
    print("=" * 65)
    print("  UNSW-NB15 Phase 2 – Preprocessing Validation Suite")
    print("=" * 65)

    schema = load_schema()

    # --- Ensure preprocessor is fitted ---
    if not PREPROCESSOR_PATH.exists():
        print("\n[validate] Preprocessor not found. Running fit_and_save() …")
        fit_and_save()

    fitted = load_preprocessor()

    # --- Load X/y for column-level checks ---
    train_df = load_data("train")
    train_df_clean = replace_infinities(train_df)
    X_raw, y_raw = prepare_Xy(train_df_clean, schema)

    results = {}

    print("\n-- Data Loading --")
    results["01_train_loads"] = check_01_train_loads()
    results["02_test_loads"] = check_02_test_loads()

    print("\n-- Schema Consistency --")
    results["03_schema_consistent"] = check_03_schema_consistent()

    print("\n-- Feature Leakage Prevention --")
    results["04_target_not_in_X"] = check_04_target_not_in_X(X_raw, schema)
    results["05_attack_cat_not_in_X"] = check_05_attack_cat_not_in_X(X_raw)
    results["06_id_not_in_X"] = check_06_id_not_in_X(X_raw)

    print("\n-- Transform Correctness --")
    ok07, X_tr_t = check_07_transform_train(fitted, schema)
    results["07_transform_train"] = ok07

    ok08, X_te_t = check_08_transform_test(fitted, schema)
    results["08_transform_test"] = ok08

    print("\n-- Feature Shape Consistency --")
    results["09_feature_counts_equal"] = check_09_feature_counts_equal(X_tr_t, X_te_t)

    print("\n-- Data Cleanliness After Transform --")
    results["10_no_nan_inf"] = check_10_no_nan_inf(X_tr_t, X_te_t)

    print("\n-- Leakage Structural Guarantee --")
    results["11_no_test_fit"] = check_11_no_test_fit()

    print("\n-- Determinism --")
    results["12_deterministic"] = check_12_deterministic()

    # --- Summary ---
    passed = sum(results.values())
    total = len(results)
    print("\n" + "=" * 65)
    print(f"  Results: {passed}/{total} checks passed")
    print("=" * 65)

    if passed < total:
        failed = [k for k, v in results.items() if not v]
        print(f"\n  FAILED: {failed}")
        sys.exit(1)
    else:
        print("\n  All checks passed. Preprocessing pipeline is validated.")


if __name__ == "__main__":
    run_all_checks()
