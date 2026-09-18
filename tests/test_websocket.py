import unittest

from fastapi.testclient import TestClient

from backend.api.main import app


class WebSocketAlertTests(unittest.TestCase):
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

    def test_prediction_is_broadcast_over_websocket(self):
        with self.client.websocket_connect("/ws/alerts") as websocket:
            response = self.client.post("/api/predict", json=self.payload)

            self.assertEqual(response.status_code, 200)

            message = websocket.receive_json()

            self.assertEqual(message["event"], "prediction")
            self.assertIn("detection", message)

            detection = message["detection"]

            self.assertIn("id", detection)
            self.assertIn("timestamp", detection)
            self.assertIn("binary_label", detection)
            self.assertIn("binary_confidence", detection)
            self.assertIn("attack_category", detection)


if __name__ == "__main__":
    unittest.main()