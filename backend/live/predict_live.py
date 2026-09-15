"""Live-mode prediction wrapper."""

from typing import Any

from backend.api.inference import predict_binary, predict_multiclass
from backend.live.flow_adapter import validate_live_flow


def predict_live(features: dict[str, Any]) -> dict[str, Any]:
    """Validate a live flow and run the existing binary + multiclass models."""

    validated_features = validate_live_flow(features)

    binary_result = predict_binary(validated_features)
    multiclass_result = predict_multiclass(validated_features)

    return {
        "mode": "live",
        "prediction": binary_result["prediction"],
        "label": binary_result["label"],
        "confidence": binary_result["confidence"],
        "attack_category": multiclass_result["label"],
        "multiclass_confidence": multiclass_result["confidence"],
    }