"""Validation adapter for controlled live-mode network flows."""

from pathlib import Path
import json
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BASE_DIR / "data" / "feature_schema.json"

with SCHEMA_PATH.open("r", encoding="utf-8") as f:
    FEATURE_SCHEMA = json.load(f)

FEATURE_ORDER = FEATURE_SCHEMA["final_feature_order"]
EXPECTED_FEATURES = set(FEATURE_ORDER)


def validate_live_flow(features: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a live flow in the exact training feature order."""

    if not isinstance(features, dict):
        raise TypeError("Live flow must be provided as a dictionary.")

    provided_features = set(features)

    missing = EXPECTED_FEATURES - provided_features
    extra = provided_features - EXPECTED_FEATURES

    if missing:
        raise ValueError(
            f"Missing required live-flow features: {sorted(missing)}"
        )

    if extra:
        raise ValueError(
            f"Unexpected live-flow features: {sorted(extra)}"
        )

    return {name: features[name] for name in FEATURE_ORDER}