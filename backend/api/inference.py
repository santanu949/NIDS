import json
from pathlib import Path

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

ARTIFACT_DIR = BASE_DIR / "ml" / "artifacts"
DATA_DIR = BASE_DIR / "data"


# --------------------------------------------------
# Load preprocessing and models once at startup
# --------------------------------------------------

PREPROCESSOR_PATH = ARTIFACT_DIR / "preprocessor.joblib"
BINARY_MODEL_PATH = ARTIFACT_DIR / "xgboost.joblib"
MULTICLASS_MODEL_PATH = ARTIFACT_DIR / "xgboost_multiclass.joblib"
SCHEMA_PATH = DATA_DIR / "feature_schema.json"
MULTICLASS_RESULTS_PATH = (
    ARTIFACT_DIR / "xgboost_multiclass_results.json"
)


preprocessor = joblib.load(PREPROCESSOR_PATH)
binary_model = joblib.load(BINARY_MODEL_PATH)
multiclass_model = joblib.load(MULTICLASS_MODEL_PATH)

with open(SCHEMA_PATH, encoding="utf-8") as f:
    schema = json.load(f)

with open(MULTICLASS_RESULTS_PATH, encoding="utf-8") as f:
    multiclass_results = json.load(f)


FEATURE_ORDER = schema["final_feature_order"]
FEATURE_SET = set(FEATURE_ORDER)
MULTICLASS_CLASSES = multiclass_results["classes"]


def _prepare_features(features: dict) -> object:
    """
    Convert a raw feature dictionary into the exact
    feature order expected by the Phase 2 preprocessor.
    """

    provided_features = set(features)

    missing = sorted(FEATURE_SET - provided_features)
    extra = sorted(provided_features - FEATURE_SET)

    if missing:
        raise ValueError(
            f"Missing required features: {missing}"
        )

    if extra:
        raise ValueError(
            f"Unexpected features: {extra}"
        )

    row = {
        feature: features[feature]
        for feature in FEATURE_ORDER
    }

    dataframe = pd.DataFrame([row])

    try:
        return preprocessor.transform(dataframe)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid feature values: {exc}"
        ) from exc


def predict_binary(features: dict) -> dict:
    """
    Binary prediction:
    0 = Normal
    1 = Attack
    """

    transformed = _prepare_features(features)

    prediction = int(
        binary_model.predict(transformed)[0]
    )

    probabilities = binary_model.predict_proba(
        transformed
    )[0]

    confidence = float(
        probabilities[prediction]
    )

    return {
        "prediction": prediction,
        "label": (
            "Attack"
            if prediction == 1
            else "Normal"
        ),
        "confidence": confidence,
    }


def predict_multiclass(features: dict) -> dict:
    """
    Multiclass attack-category prediction.
    """

    transformed = _prepare_features(features)

    prediction = int(
        multiclass_model.predict(transformed)[0]
    )

    probabilities = multiclass_model.predict_proba(
        transformed
    )[0]

    confidence = float(
        probabilities[prediction]
    )

    return {
        "prediction": prediction,
        "label": MULTICLASS_CLASSES[prediction],
        "confidence": confidence,
    }