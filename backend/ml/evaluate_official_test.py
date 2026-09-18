from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "raw" / "UNSW_NB15_testing-set.csv"
SCHEMA = BASE / "data" / "feature_schema.json"
ARTIFACTS = BASE / "ml" / "artifacts"

schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
multi_meta = json.loads((ARTIFACTS / "xgboost_multiclass_results.json").read_text(encoding="utf-8"))

features = schema["final_feature_order"]
classes = multi_meta["classes"]
class_to_id = {name: int(value) for name, value in multi_meta["class_to_id"].items()}

print("=" * 80)
print("OFFICIAL UNSW-NB15 TEST-SET EVALUATION")
print("=" * 80)

df = pd.read_csv(DATA, encoding="utf-8-sig")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")

X_test = df[features].copy()
y_binary = df["label"].astype(int)
y_multi = df["attack_cat"].map(class_to_id)

preprocessor = joblib.load(ARTIFACTS / "preprocessor.joblib")
binary_model = joblib.load(ARTIFACTS / "xgboost.joblib")
multi_model = joblib.load(ARTIFACTS / "xgboost_multiclass.joblib")

X_test_transformed = preprocessor.transform(X_test)

if X_test_transformed.shape[1] != 192:
    raise RuntimeError(f"Expected 192 transformed features, got {X_test_transformed.shape[1]}")

print(f"Transformed shape: {X_test_transformed.shape}")
print("Preprocessor fitted on test set: NO")
print("Models retrained on test set: NO")

binary_pred = binary_model.predict(X_test_transformed)
binary_cm = confusion_matrix(y_binary, binary_pred, labels=[0, 1])
tn, fp, fn, tp = binary_cm.ravel()

binary_results = {
    "accuracy": float(accuracy_score(y_binary, binary_pred)),
    "precision": float(precision_score(y_binary, binary_pred, zero_division=0)),
    "recall": float(recall_score(y_binary, binary_pred, zero_division=0)),
    "f1": float(f1_score(y_binary, binary_pred, zero_division=0)),
    "false_positive_rate": float(fp / (fp + tn) if (fp + tn) else 0.0),
    "confusion_matrix": binary_cm.tolist(),
    "confusion_matrix_labels": ["Normal", "Attack"],
    "true_negative": int(tn),
    "false_positive": int(fp),
    "false_negative": int(fn),
    "true_positive": int(tp),
}

multi_pred = multi_model.predict(X_test_transformed)
label_ids = list(range(len(classes)))

multi_report = classification_report(
    y_multi,
    multi_pred,
    labels=label_ids,
    target_names=classes,
    output_dict=True,
    zero_division=0,
)

multi_cm = confusion_matrix(
    y_multi,
    multi_pred,
    labels=label_ids,
)

multi_results = {
    "accuracy": float(accuracy_score(y_multi, multi_pred)),
    "weighted_precision": float(precision_score(y_multi, multi_pred, labels=label_ids, average="weighted", zero_division=0)),
    "weighted_recall": float(recall_score(y_multi, multi_pred, labels=label_ids, average="weighted", zero_division=0)),
    "weighted_f1": float(f1_score(y_multi, multi_pred, labels=label_ids, average="weighted", zero_division=0)),
    "macro_f1": float(f1_score(y_multi, multi_pred, labels=label_ids, average="macro", zero_division=0)),
    "classification_report": multi_report,
    "confusion_matrix": multi_cm.tolist(),
    "confusion_matrix_labels": classes,
}

output = {
    "dataset": "UNSW-NB15",
    "evaluation_type": "official_test_set",
    "official_test_set_used": True,
    "test_rows": int(len(df)),
    "test_columns": int(len(df.columns)),
    "input_feature_count": int(len(features)),
    "transformed_feature_count": int(X_test_transformed.shape[1]),
    "preprocessing_fitted_on_test": False,
    "models_retrained_on_test": False,
    "binary": {
        "model": "XGBoost",
        "artifact": "backend/ml/artifacts/xgboost.joblib",
        "results": binary_results,
    },
    "multiclass": {
        "model": "XGBoost",
        "artifact": "backend/ml/artifacts/xgboost_multiclass.joblib",
        "classes": classes,
        "class_to_id": class_to_id,
        "results": multi_results,
    },
}

(ARTIFACTS / "official_test_results.json").write_text(
    json.dumps(output, indent=2),
    encoding="utf-8",
)

pd.DataFrame(
    binary_cm,
    index=["Normal", "Attack"],
    columns=["Normal", "Attack"],
).rename_axis("actual").to_csv(
    ARTIFACTS / "binary_confusion_matrix.csv"
)

pd.DataFrame(
    multi_cm,
    index=classes,
    columns=classes,
).rename_axis("actual").to_csv(
    ARTIFACTS / "multiclass_confusion_matrix.csv"
)

print()
print("BINARY TEST RESULTS")
print("-" * 40)
for key in ["accuracy", "precision", "recall", "f1", "false_positive_rate"]:
    print(f"{key}: {binary_results[key]:.6f}")
print("Confusion matrix:")
print(binary_cm)

print()
print("MULTICLASS TEST RESULTS")
print("-" * 40)
for key in ["accuracy", "weighted_precision", "weighted_recall", "weighted_f1", "macro_f1"]:
    print(f"{key}: {multi_results[key]:.6f}")

print()
print("PER-CLASS RESULTS")
print("-" * 40)
for name in classes:
    item = multi_report[name]
    print(
        f"{name}: "
        f"precision={item['precision']:.6f}, "
        f"recall={item['recall']:.6f}, "
        f"f1={item['f1-score']:.6f}, "
        f"support={int(item['support'])}"
    )

print()
print("Multiclass confusion matrix:")
print(multi_cm)

print()
print("=" * 80)
print("OFFICIAL TEST EVALUATION COMPLETE")
print("=" * 80)
print("Saved:")
print(ARTIFACTS / "official_test_results.json")
print(ARTIFACTS / "binary_confusion_matrix.csv")
print(ARTIFACTS / "multiclass_confusion_matrix.csv")
