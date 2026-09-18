import json
import unittest
from pathlib import Path

import joblib
import pandas as pd

from backend.api.inference import predict_binary, predict_multiclass


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "backend" / "data" / "feature_schema.json"
PREPROCESSOR_PATH = ROOT / "backend" / "ml" / "artifacts" / "preprocessor.joblib"
BINARY_MODEL_PATH = ROOT / "backend" / "ml" / "artifacts" / "xgboost.joblib"
MULTICLASS_MODEL_PATH = ROOT / "backend" / "ml" / "artifacts" / "xgboost_multiclass.joblib"


def load_schema():
    with SCHEMA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_valid_features():
    schema = load_schema()
    features = {}

    for name in schema["numeric_feature_columns"]:
        features[name] = 0

    for name in schema["categorical_feature_columns"]:
        features[name] = "tcp" if name == "proto" else (
            "http" if name == "service" else "FIN"
        )

    return {
        name: features[name]
        for name in schema["final_feature_order"]
    }


class TestNIDSMLPipeline(unittest.TestCase):

    def test_feature_schema(self):
        schema = load_schema()

        self.assertEqual(
            schema["total_raw_feature_count"],
            42,
        )

        self.assertEqual(
            len(schema["final_feature_order"]),
            42,
        )

        self.assertEqual(
            len(schema["numeric_feature_columns"]),
            39,
        )

        self.assertEqual(
            len(schema["categorical_feature_columns"]),
            3,
        )

        self.assertNotIn(
            "label",
            schema["final_feature_order"],
        )

        self.assertNotIn(
            "attack_cat",
            schema["final_feature_order"],
        )

        self.assertNotIn(
            "id",
            schema["final_feature_order"],
        )

    def test_preprocessor_loads_and_outputs_192_features(self):
        preprocessor = joblib.load(
            PREPROCESSOR_PATH
        )

        features = build_valid_features()

        frame = pd.DataFrame(
            [features],
            columns=load_schema()["final_feature_order"],
        )

        transformed = preprocessor.transform(frame)

        self.assertEqual(
            transformed.shape,
            (1, 192),
        )

        self.assertEqual(
            len(preprocessor.get_feature_names_out()),
            192,
        )

    def test_binary_model_loads(self):
        model = joblib.load(
            BINARY_MODEL_PATH
        )

        self.assertEqual(
            type(model).__name__,
            "XGBClassifier",
        )

        self.assertEqual(
            model.classes_.tolist(),
            [0, 1],
        )

    def test_multiclass_model_loads(self):
        model = joblib.load(
            MULTICLASS_MODEL_PATH
        )

        self.assertEqual(
            type(model).__name__,
            "XGBClassifier",
        )

        self.assertEqual(
            model.classes_.tolist(),
            list(range(10)),
        )

    def test_binary_prediction(self):
        result = predict_binary(
            build_valid_features()
        )

        self.assertIn(
            result["prediction"],
            [0, 1],
        )

        self.assertIn(
            result["label"],
            ["Normal", "Attack"],
        )

        self.assertGreaterEqual(
            result["confidence"],
            0.0,
        )

        self.assertLessEqual(
            result["confidence"],
            1.0,
        )

    def test_multiclass_prediction(self):
        result = predict_multiclass(
            build_valid_features()
        )

        schema = load_schema()
        results_path = (
            ROOT
            / "backend"
            / "ml"
            / "artifacts"
            / "xgboost_multiclass_results.json"
        )

        with results_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            metadata = json.load(file)

        self.assertIn(
            result["prediction"],
            list(range(10)),
        )

        self.assertIn(
            result["label"],
            metadata["classes"],
        )

        self.assertGreaterEqual(
            result["confidence"],
            0.0,
        )

        self.assertLessEqual(
            result["confidence"],
            1.0,
        )

        self.assertEqual(
            len(schema["final_feature_order"]),
            42,
        )

    def test_missing_feature_is_rejected(self):
        features = build_valid_features()

        removed_feature = next(
            iter(features)
        )

        del features[removed_feature]

        with self.assertRaises(
            ValueError
        ):
            predict_binary(features)


if __name__ == "__main__":
    unittest.main(verbosity=2)