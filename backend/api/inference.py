from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = BASE_DIR / "ml" / "artifacts"
DATA_DIR = BASE_DIR / "data"

PREPROCESSOR_PATH = ARTIFACT_DIR / "preprocessor.joblib"
BINARY_MODEL_PATH = ARTIFACT_DIR / "xgboost.joblib"
MULTICLASS_MODEL_PATH = ARTIFACT_DIR / "xgboost_multiclass.joblib"
FEATURE_SCHEMA_PATH = DATA_DIR / "feature_schema.json"
MULTICLASS_RESULTS_PATH = ARTIFACT_DIR / "xgboost_multiclass_results.json"


@lru_cache(maxsize=1)
def _load_preprocessor():
    return joblib.load(PREPROCESSOR_PATH)


@lru_cache(maxsize=1)
def _load_binary_model():
    return joblib.load(BINARY_MODEL_PATH)


@lru_cache(maxsize=1)
def _load_multiclass_model():
    return joblib.load(MULTICLASS_MODEL_PATH)


@lru_cache(maxsize=1)
def _load_feature_schema() -> dict[str, Any]:
    with FEATURE_SCHEMA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def _load_multiclass_results() -> dict[str, Any]:
    with MULTICLASS_RESULTS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _prepare_features(features: dict[str, Any]):
    schema = _load_feature_schema()
    feature_order = schema["final_feature_order"]

    missing = [
        feature
        for feature in feature_order
        if feature not in features
    ]

    if missing:
        raise ValueError(
            f"Missing required features: {', '.join(missing)}"
        )

    row = {
        feature: features[feature]
        for feature in feature_order
    }

    frame = pd.DataFrame(
        [row],
        columns=feature_order,
    )

    return _load_preprocessor().transform(frame)


def predict_binary(features: dict[str, Any]) -> dict[str, Any]:
    transformed = _prepare_features(features)
    model = _load_binary_model()

    prediction = int(model.predict(transformed)[0])

    probabilities = model.predict_proba(transformed)[0]
    confidence = float(probabilities[prediction])

    label = "Attack" if prediction == 1 else "Normal"

    return {
        "prediction": prediction,
        "label": label,
        "confidence": confidence,
    }


def predict_multiclass(features: dict[str, Any]) -> dict[str, Any]:
    transformed = _prepare_features(features)
    model = _load_multiclass_model()
    results = _load_multiclass_results()

    prediction = int(model.predict(transformed)[0])

    probabilities = model.predict_proba(transformed)[0]
    confidence = float(probabilities[prediction])

    class_to_id = results["class_to_id"]
    classes = {
        int(class_id): label
        for label, class_id in class_to_id.items()
    }

    label = classes[prediction]

    return {
        "prediction": prediction,
        "label": label,
        "confidence": confidence,
    }