from pathlib import Path
import json
import time

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from xgboost import XGBClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRAIN_CSV = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "raw"
    / "UNSW_NB15_training-set.csv"
)

SCHEMA_PATH = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "feature_schema.json"
)

PREPROCESSOR_PATH = (
    PROJECT_ROOT
    / "backend"
    / "ml"
    / "artifacts"
    / "preprocessor.joblib"
)

ARTIFACT_DIR = PROJECT_ROOT / "backend" / "ml" / "artifacts"

MODEL_PATH = ARTIFACT_DIR / "xgboost.joblib"
RESULT_PATH = ARTIFACT_DIR / "xgboost_results.json"

RANDOM_STATE = 42
VAL_SIZE = 0.20


def load_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def calculate_metrics(y_true, y_pred) -> dict:
    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    ).ravel()

    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(
            precision_score(y_true, y_pred, zero_division=0)
        ),
        "recall": float(
            recall_score(y_true, y_pred, zero_division=0)
        ),
        "f1": float(
            f1_score(y_true, y_pred, zero_division=0)
        ),
        "confusion_matrix": [
            [int(tn), int(fp)],
            [int(fn), int(tp)],
        ],
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
        "false_positive_rate": float(fpr),
        "classification_report": classification_report(
            y_true,
            y_pred,
            labels=[0, 1],
            target_names=["Normal", "Attack"],
            output_dict=True,
            zero_division=0,
        ),
    }


def main() -> None:
    print("=" * 65)
    print("  UNSW-NB15 Phase 3 – XGBoost")
    print("=" * 65)

    schema = load_schema()

    print("\n[1/6] Loading training data...")

    df = pd.read_csv(
        TRAIN_CSV,
        encoding="utf-8-sig",
    )

    target_column = schema["target_column"]
    feature_order = schema["final_feature_order"]

    X = df[feature_order].copy()
    y = df[target_column].astype(int)

    print(f"  Dataset shape: {df.shape}")
    print(f"  Input features: {len(feature_order)}")
    print(f"  Target: {target_column}")

    print("\n[2/6] Reproducing Phase 2 train/validation split...")

    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=VAL_SIZE,
        stratify=y,
        random_state=RANDOM_STATE,
        shuffle=True,
    )

    print(f"  Training rows:   {len(X_train)}")
    print(f"  Validation rows: {len(X_val)}")

    assert len(X_train) == 140272
    assert len(X_val) == 35069

    print("\n[3/6] Loading fitted Phase 2 preprocessor...")

    preprocessor = joblib.load(PREPROCESSOR_PATH)

    scaler = (
        preprocessor
        .named_steps["preprocessor"]
        .named_transformers_["numeric"]
        .named_steps["scaler"]
    )

    print(
        f"  Preprocessor scaler samples: "
        f"{scaler.n_samples_seen_}"
    )

    assert scaler.n_samples_seen_ == 140272

    print("\n[4/6] Transforming training and validation data...")

    X_train_transformed = preprocessor.transform(X_train)
    X_val_transformed = preprocessor.transform(X_val)

    print(
        f"  X_train transformed: "
        f"{X_train_transformed.shape}"
    )

    print(
        f"  X_val transformed:   "
        f"{X_val_transformed.shape}"
    )

    assert X_train_transformed.shape == (140272, 192)
    assert X_val_transformed.shape == (35069, 192)

    print("\n[5/6] Training XGBoost...")

    model = XGBClassifier(
        n_estimators=300,
        learning_rate=0.10,
        max_depth=8,
        subsample=0.80,
        colsample_bytree=0.80,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    start_time = time.perf_counter()

    model.fit(
        X_train_transformed,
        y_train,
    )

    training_time = time.perf_counter() - start_time

    print(
        f"  Training completed in "
        f"{training_time:.2f} seconds."
    )

    print("\n[6/6] Evaluating on validation data...")

    start_time = time.perf_counter()

    y_pred = model.predict(X_val_transformed)

    prediction_time = time.perf_counter() - start_time

    metrics = calculate_metrics(
        y_val,
        y_pred,
    )

    print("\n" + "=" * 65)
    print("  VALIDATION RESULTS")
    print("=" * 65)

    print(
        f"Accuracy:            "
        f"{metrics['accuracy']:.6f}"
    )

    print(
        f"Precision:           "
        f"{metrics['precision']:.6f}"
    )

    print(
        f"Recall:              "
        f"{metrics['recall']:.6f}"
    )

    print(
        f"F1-score:            "
        f"{metrics['f1']:.6f}"
    )

    print(
        f"False Positive Rate: "
        f"{metrics['false_positive_rate']:.6f}"
    )

    print("\nConfusion Matrix:")

    print("                 Predicted")
    print("                 Normal  Attack")

    print(
        f"Actual Normal    "
        f"{metrics['true_negative']:6d}  "
        f"{metrics['false_positive']:6d}"
    )

    print(
        f"Actual Attack    "
        f"{metrics['false_negative']:6d}  "
        f"{metrics['true_positive']:6d}"
    )

    print("\nClassification Report:")

    report_df = pd.DataFrame(
        metrics["classification_report"]
    ).transpose()

    print(report_df.to_string())

    ARTIFACT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_PATH,
    )

    results = {
        "model": {
            "name": "XGBoost",
            "class": "xgboost.XGBClassifier",
            "parameters": model.get_params(),
        },
        "dataset": {
            "name": "UNSW-NB15",
            "training_csv_rows": int(len(df)),
            "training_partition_rows": int(len(X_train)),
            "validation_rows": int(len(X_val)),
        },
        "features": {
            "raw_feature_count": int(len(feature_order)),
            "transformed_feature_count": int(
                X_train_transformed.shape[1]
            ),
            "target_column": target_column,
        },
        "split": {
            "validation_fraction": VAL_SIZE,
            "random_state": RANDOM_STATE,
            "stratified": True,
            "shuffle": True,
        },
        "class_distribution": {
            "training": {
                str(k): int(v)
                for k, v in (
                    y_train
                    .value_counts()
                    .sort_index()
                    .items()
                )
            },
            "validation": {
                str(k): int(v)
                for k, v in (
                    y_val
                    .value_counts()
                    .sort_index()
                    .items()
                )
            },
        },
        "preprocessing": {
            "artifact": (
                "backend/ml/artifacts/"
                "preprocessor.joblib"
            ),
            "fitted_rows": int(
                scaler.n_samples_seen_
            ),
        },
        "training_time_seconds": float(
            training_time
        ),
        "prediction_time_seconds": float(
            prediction_time
        ),
        "metrics": metrics,
        "official_test_set_used": False,
    }

    with RESULT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            results,
            f,
            indent=2,
        )

    print("\nArtifacts created:")
    print(f"  Model:   {MODEL_PATH}")
    print(f"  Results: {RESULT_PATH}")

    print(
        "\nOfficial UNSW-NB15 test set used: NO"
    )

    print(
        "\nXGBoost training completed successfully."
    )


if __name__ == "__main__":
    main()