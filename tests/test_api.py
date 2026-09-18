import unittest

from fastapi.testclient import TestClient

from backend.api.main import app


class APITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.payload = {
            "mode": "dataset",
            "features": {
                "dur": 0.12,
                "proto": "tcp",
                "service": "http",
                "state": "FIN",
                "spkts": 10,
                "dpkts": 8,
                "sbytes": 1200,
                "dbytes": 900,
                "rate": 50.0,
                "sttl": 64,
                "dttl": 64,
                "sload": 10000.0,
                "dload": 8000.0,
                "sloss": 0,
                "dloss": 0,
                "sinpkt": 0.01,
                "dinpkt": 0.01,
                "sjit": 0.0,
                "djit": 0.0,
                "swin": 255,
                "stcpb": 0,
                "dtcpb": 0,
                "dwin": 255,
                "tcprtt": 0.01,
                "synack": 0.005,
                "ackdat": 0.005,
                "smean": 120.0,
                "dmean": 112.5,
                "trans_depth": 0,
                "response_body_len": 0,
                "ct_srv_src": 1,
                "ct_state_ttl": 1,
                "ct_dst_ltm": 1,
                "ct_src_dport_ltm": 1,
                "ct_dst_sport_ltm": 1,
                "ct_dst_src_ltm": 1,
                "is_ftp_login": 0,
                "ct_ftp_cmd": 0,
                "ct_flw_http_mthd": 1,
                "ct_src_ltm": 1,
                "ct_srv_dst": 1,
                "is_sm_ips_ports": 0,
            },
        }

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "nids-ml-api")

    def test_dashboard_summary(self):
        response = self.client.get("/api/dashboard/summary")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("total_events", data)
        self.assertIn("malicious_events", data)
        self.assertIn("normal_events", data)
        self.assertIn("threat_rate", data)
        self.assertIn("high_severity_events", data)
        self.assertIn("live_capture_running", data)
        self.assertIn("recent_events", data)

    def test_prediction_creates_detection(self):
        before = self.client.get("/api/detections?limit=1").json()["total"]

        response = self.client.post("/api/predict", json=self.payload)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("prediction", data)
        self.assertIn("label", data)
        self.assertIn("confidence", data)
        self.assertIn("attack_category", data)
        self.assertIn("multiclass_confidence", data)
        self.assertIn("severity", data)
        self.assertIn("model_version", data)

        self.assertIn(data["prediction"], [0, 1])
        self.assertGreaterEqual(data["confidence"], 0.0)
        self.assertLessEqual(data["confidence"], 1.0)
        self.assertGreaterEqual(data["multiclass_confidence"], 0.0)
        self.assertLessEqual(data["multiclass_confidence"], 1.0)

        after = self.client.get("/api/detections?limit=1").json()["total"]

        self.assertEqual(after, before + 1)

    def test_batch_prediction(self):
        response = self.client.post(
            "/api/predict/batch",
            json={
                "predictions": [
                    {
                        "mode": "dataset",
                        "features": self.payload["features"],
                    },
                    {
                        "mode": "dataset",
                        "features": self.payload["features"],
                    },
                ],
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["results"]), 2)

        for result in data["results"]:
            self.assertIn("prediction", result)
            self.assertIn("label", result)
            self.assertIn("confidence", result)
            self.assertIn("attack_category", result)
            self.assertIn("severity", result)
            self.assertIn("model_version", result)

    def test_detection_detail(self):
        response = self.client.post("/api/predict", json=self.payload)

        self.assertEqual(response.status_code, 200)

        detections = self.client.get(
            "/api/detections",
            params={"limit": 1},
        )

        self.assertEqual(detections.status_code, 200)

        items = detections.json()["items"]

        self.assertTrue(items)

        detection_id = items[0]["id"]

        detail = self.client.get(f"/api/detections/{detection_id}")

        self.assertEqual(detail.status_code, 200)

        data = detail.json()

        self.assertEqual(data["id"], detection_id)
        self.assertIn("timestamp", data)
        self.assertIn("mode", data)
        self.assertIn("binary_prediction", data)
        self.assertIn("binary_label", data)
        self.assertIn("binary_confidence", data)
        self.assertIn("attack_category", data)
        self.assertIn("multiclass_confidence", data)
        self.assertIn("severity", data)
        self.assertIn("model_version", data)

    def test_detection_filters(self):
        self.client.post("/api/predict", json=self.payload)

        response = self.client.get(
            "/api/detections",
            params={
                "mode": "dataset",
                "limit": 10,
                "offset": 0,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(data["offset"], 0)
        self.assertLessEqual(len(data["items"]), 10)

        for item in data["items"]:
            self.assertEqual(item["mode"], "dataset")

    def test_detection_malicious_filter(self):
        response = self.client.get(
            "/api/detections",
            params={
                "malicious_only": "true",
                "limit": 10,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("items", data)

        for item in data["items"]:
            self.assertEqual(item["binary_prediction"], 1)

    def test_csv_export(self):
        self.client.post("/api/predict", json=self.payload)

        response = self.client.get("/api/detections/export.csv")

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "text/csv",
            response.headers.get("content-type", ""),
        )

        csv_text = response.text

        self.assertIn("id", csv_text)
        self.assertIn("timestamp", csv_text)
        self.assertIn("binary_prediction", csv_text)
        self.assertIn("binary_confidence", csv_text)
        self.assertIn("attack_category", csv_text)
        self.assertIn("severity", csv_text)

    def test_analytics(self):
        response = self.client.get("/api/analytics/attacks")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("total_events", data)
        self.assertIn("normal_events", data)
        self.assertIn("attack_events", data)
        self.assertIn("attack_rate", data)
        self.assertIn("average_binary_confidence", data)
        self.assertIn("average_multiclass_confidence", data)
        self.assertIn("attack_categories", data)

        self.assertIsInstance(data["attack_categories"], dict)

    def test_model_metrics(self):
        response = self.client.get("/api/model/metrics")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("dataset", data)
        self.assertEqual(data["primary_model"], "XGBoost")
        self.assertIn("model_selection_metric", data)
        self.assertIn("official_test_set_used", data)
        self.assertIn("official_test_evaluation_available", data)
        self.assertIn("training_rows", data)
        self.assertIn("validation_rows", data)
        self.assertIn("transformed_feature_count", data)
        self.assertIn("binary_models", data)
        self.assertIn("multiclass_accuracy", data)
        self.assertIn("multiclass_weighted_precision", data)
        self.assertIn("multiclass_weighted_recall", data)
        self.assertIn("multiclass_weighted_f1", data)
        self.assertIn("multiclass_macro_f1", data)

        self.assertTrue(data["official_test_evaluation_available"])
        self.assertGreater(data["training_rows"], 0)
        self.assertGreater(data["validation_rows"], 0)
        self.assertGreater(data["transformed_feature_count"], 0)
        self.assertTrue(data["binary_models"])

    def test_model_features(self):
        response = self.client.get("/api/model/features")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["model"], "XGBoost")
        self.assertGreater(data["feature_count"], 0)
        self.assertTrue(data["features"])

        for feature in data["features"]:
            self.assertIn("name", feature)
            self.assertIn("importance", feature)
            self.assertIn("rank", feature)

    def test_live_status(self):
        response = self.client.get("/live/status")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("running", data)
        self.assertIn("interface_configured", data)
        self.assertIn("interface", data)
        self.assertIn("flow_timeout", data)
        self.assertIn("last_error", data)

    def test_missing_features_rejected(self):
        response = self.client.post(
            "/api/predict",
            json={
                "mode": "dataset",
                "features": {},
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()