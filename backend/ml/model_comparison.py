import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)


# --------------------------------------------------
# Load schema and dataset
# --------------------------------------------------

with open("backend/data/feature_schema.json", encoding="utf-8") as f:
    schema = json.load(f)

df = pd.read_csv(
    "backend/data/raw/UNSW_NB15_training-set.csv",
    encoding="utf-8-sig",
)

X = df[schema["final_feature_order"]].copy()
y = df[schema["target_column"]].astype(int)


# --------------------------------------------------
# Reproduce the exact Phase 2 split
# --------------------------------------------------

X_train, X_val, y_train, y_val = train_test_split(
    X,
    y,
    test_size=0.20,
    stratify=y,
    random_state=42,
    shuffle=True,
)


# --------------------------------------------------
# Load the already-fitted preprocessing pipeline
# --------------------------------------------------

preprocessor = joblib.load(
    "backend/ml/artifacts/preprocessor.joblib"
)

X_train = preprocessor.transform(X_train)
X_val = preprocessor.transform(X_val)


# --------------------------------------------------
# Load trained models
# --------------------------------------------------

models = {
    "Logistic Regression": "logistic_regression.joblib",
    "Random Forest": "random_forest.joblib",
    "XGBoost": "xgboost.joblib",
}


results = []


# --------------------------------------------------
# Evaluate each model
# --------------------------------------------------

for model_name, filename in models.items():

    model = joblib.load(
        "backend/ml/artifacts/" + filename
    )

    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)

    train_f1 = f1_score(
        y_train,
        train_pred,
        zero_division=0,
    )

    val_f1 = f1_score(
        y_val,
        val_pred,
        zero_division=0,
    )

    train_accuracy = accuracy_score(
        y_train,
        train_pred,
    )

    val_accuracy = accuracy_score(
        y_val,
        val_pred,
    )

    val_precision = precision_score(
        y_val,
        val_pred,
        zero_division=0,
    )

    val_recall = recall_score(
        y_val,
        val_pred,
        zero_division=0,
    )

    cm = confusion_matrix(
        y_val,
        val_pred,
        labels=[0, 1],
    )

    tn, fp, fn, tp = cm.ravel()

    fpr = fp / (fp + tn)

    results.append(
        {
            "model": model_name,
            "train_accuracy": round(train_accuracy, 6),
            "validation_accuracy": round(val_accuracy, 6),
            "train_f1": round(train_f1, 6),
            "validation_f1": round(val_f1, 6),
            "validation_precision": round(val_precision, 6),
            "validation_recall": round(val_recall, 6),
            "false_positive_rate": round(fpr, 6),
            "train_validation_f1_gap": round(
                train_f1 - val_f1,
                6,
            ),
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        }
    )


# --------------------------------------------------
# Select primary model using validation F1
# --------------------------------------------------

best_model = max(
    results,
    key=lambda result: result["validation_f1"],
)


comparison = {
    "dataset": "UNSW-NB15",
    "split": {
        "training_rows": int(len(X_train)),
        "validation_rows": int(len(X_val)),
        "random_state": 42,
        "test_size": 0.20,
        "stratified": True,
    },
    "preprocessing": {
        "artifact": "backend/ml/artifacts/preprocessor.joblib",
        "feature_count_after_transform": int(X_train.shape[1]),
    },
    "official_test_set_used": False,
    "model_selection_metric": "validation_f1",
    "primary_model": best_model["model"],
    "models": results,
}


# --------------------------------------------------
# Save reproducible comparison report
# --------------------------------------------------

output_path = (
    "backend/ml/artifacts/model_comparison_results.json"
)

with open(
    output_path,
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        comparison,
        f,
        indent=2,
    )


# --------------------------------------------------
# Print summary
# --------------------------------------------------

print("MODEL COMPARISON")
print("=" * 80)

for result in results:

    print()
    print(result["model"])
    print(f"  Validation Accuracy : {result['validation_accuracy']:.4f}")
    print(f"  Validation Precision: {result['validation_precision']:.4f}")
    print(f"  Validation Recall   : {result['validation_recall']:.4f}")
    print(f"  Validation F1       : {result['validation_f1']:.4f}")
    print(f"  False Positive Rate : {result['false_positive_rate']:.4f}")
    print(f"  Train/Val F1 Gap    : {result['train_validation_f1_gap']:.4f}")

print()
print("=" * 80)
print(f"PRIMARY MODEL: {best_model['model']}")
print(f"Selection metric: validation F1")
print(f"Results saved to: {output_path}")
print("Official test set used: NO")