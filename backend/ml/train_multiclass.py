import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

from xgboost import XGBClassifier


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
y = df["attack_cat"].astype(str).str.strip()


# --------------------------------------------------
# Fixed class mapping
# --------------------------------------------------

classes = sorted(y.unique().tolist())

class_to_id = {
    class_name: index
    for index, class_name in enumerate(classes)
}

id_to_class = {
    index: class_name
    for class_name, index in class_to_id.items()
}

y_encoded = y.map(class_to_id)


# --------------------------------------------------
# Reproduce the Phase 2 split
# --------------------------------------------------

X_train, X_val, y_train, y_val = train_test_split(
    X,
    y_encoded,
    test_size=0.20,
    stratify=y_encoded,
    random_state=42,
    shuffle=True,
)


# --------------------------------------------------
# Load Phase 2 preprocessing
# --------------------------------------------------

preprocessor = joblib.load(
    "backend/ml/artifacts/preprocessor.joblib"
)

X_train = preprocessor.transform(X_train)
X_val = preprocessor.transform(X_val)


# --------------------------------------------------
# Train multiclass XGBoost
# --------------------------------------------------

model = XGBClassifier(
    n_estimators=300,
    learning_rate=0.10,
    max_depth=8,
    subsample=0.80,
    colsample_bytree=0.80,
    objective="multi:softprob",
    num_class=len(classes),
    eval_metric="mlogloss",
    tree_method="hist",
    random_state=42,
    n_jobs=-1,
)

model.fit(
    X_train,
    y_train,
)


# --------------------------------------------------
# Predictions
# --------------------------------------------------

train_pred = model.predict(X_train)
val_pred = model.predict(X_val)


# --------------------------------------------------
# Overall validation metrics
# --------------------------------------------------

accuracy = accuracy_score(
    y_val,
    val_pred,
)

precision = precision_score(
    y_val,
    val_pred,
    average="weighted",
    zero_division=0,
)

recall = recall_score(
    y_val,
    val_pred,
    average="weighted",
    zero_division=0,
)

f1 = f1_score(
    y_val,
    val_pred,
    average="weighted",
    zero_division=0,
)

macro_f1 = f1_score(
    y_val,
    val_pred,
    average="macro",
    zero_division=0,
)


# --------------------------------------------------
# Per-class metrics
# --------------------------------------------------

report = classification_report(
    y_val,
    val_pred,
    labels=list(range(len(classes))),
    target_names=classes,
    output_dict=True,
    zero_division=0,
)


# --------------------------------------------------
# Confusion matrix
# --------------------------------------------------

cm = confusion_matrix(
    y_val,
    val_pred,
    labels=list(range(len(classes))),
)


# --------------------------------------------------
# Save model
# --------------------------------------------------

model_path = (
    "backend/ml/artifacts/xgboost_multiclass.joblib"
)

joblib.dump(
    model,
    model_path,
)


# --------------------------------------------------
# Save results
# --------------------------------------------------

results = {
    "dataset": "UNSW-NB15",
    "task": "multiclass_attack_category_classification",
    "target_column": "attack_cat",
    "classes": classes,
    "class_to_id": class_to_id,
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
    "model": {
        "model_class": "XGBClassifier",
        "objective": "multi:softprob",
        "n_estimators": 300,
        "learning_rate": 0.10,
        "max_depth": 8,
        "subsample": 0.80,
        "colsample_bytree": 0.80,
        "random_state": 42,
    },
    "metrics_validation": {
        "accuracy": round(accuracy, 6),
        "weighted_precision": round(precision, 6),
        "weighted_recall": round(recall, 6),
        "weighted_f1": round(f1, 6),
        "macro_f1": round(macro_f1, 6),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    },
    "official_test_set_used": False,
    "artifact_path": model_path,
}


with open(
    "backend/ml/artifacts/xgboost_multiclass_results.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        results,
        f,
        indent=2,
    )


# --------------------------------------------------
# Print summary
# --------------------------------------------------

print("MULTICLASS XGBOOST")
print("=" * 70)
print(f"Classes: {len(classes)}")
print(f"Training rows: {len(X_train)}")
print(f"Validation rows: {len(X_val)}")
print(f"Features after preprocessing: {X_train.shape[1]}")
print()
print(f"Validation Accuracy : {accuracy:.4f}")
print(f"Weighted Precision  : {precision:.4f}")
print(f"Weighted Recall     : {recall:.4f}")
print(f"Weighted F1         : {f1:.4f}")
print(f"Macro F1            : {macro_f1:.4f}")
print()
print("PER-CLASS METRICS")
print("-" * 70)

for class_name in classes:
    metrics = report[class_name]

    print(
        f"{class_name:16s}"
        f" Precision={metrics['precision']:.4f}"
        f" Recall={metrics['recall']:.4f}"
        f" F1={metrics['f1-score']:.4f}"
        f" Support={int(metrics['support'])}"
    )

print()
print(f"Model saved to: {model_path}")
print(
    "Results saved to: "
    "backend/ml/artifacts/xgboost_multiclass_results.json"
)
print("Official test set used: NO")