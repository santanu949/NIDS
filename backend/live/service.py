from __future__ import annotations

import asyncio
from threading import Lock, Thread

from backend.api.websocket import alert_manager
from backend.app import config
from backend.app.database import SessionLocal
from backend.app.models.prediction_event import PredictionEvent
from backend.live.capture import LiveCapture
from backend.live.predict_live import predict_live


MODEL_VERSION = "xgboost-1.0"


def calculate_severity(
    binary_prediction: int,
    binary_confidence: float,
    multiclass_confidence: float,
) -> str:
    """Calculate a simple severity level for a prediction."""

    if binary_prediction == 0:
        return "low"

    confidence = max(
        binary_confidence,
        multiclass_confidence,
    )

    if confidence >= 0.90:
        return "critical"

    if confidence >= 0.75:
        return "high"

    if confidence >= 0.55:
        return "medium"

    return "low"


class LiveCaptureService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._capture: LiveCapture | None = None
        self._thread: Thread | None = None
        self._last_error: str | None = None
        self._event_loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(
        self,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Register the FastAPI event loop for thread-safe alerts."""

        with self._lock:
            self._event_loop = loop

    def clear_event_loop(self) -> None:
        """Clear the registered event loop."""

        with self._lock:
            self._event_loop = None

    def _get_interface(self) -> str:
        """Return the current configured live-capture interface."""

        return config.LIVE_INTERFACE

    def _get_flow_timeout(self) -> float:
        """Return the current configured live flow timeout."""

        return config.LIVE_FLOW_TIMEOUT

    def _broadcast_from_capture_thread(
        self,
        payload: dict,
    ) -> None:
        """Schedule a WebSocket broadcast from the capture thread."""

        with self._lock:
            loop = self._event_loop

        if loop is None or loop.is_closed():
            return

        try:
            future = asyncio.run_coroutine_threadsafe(
                alert_manager.broadcast(payload),
                loop,
            )

            future.add_done_callback(
                self._broadcast_finished,
            )
        except Exception as exc:
            self._last_error = (
                f"WebSocket broadcast failed: {exc}"
            )

    def _broadcast_finished(
        self,
        future,
    ) -> None:
        """Capture exceptions from the scheduled broadcast."""

        try:
            future.result()
        except Exception as exc:
            self._last_error = (
                f"WebSocket broadcast failed: {exc}"
            )

    def _handle_flow(
        self,
        features: dict,
    ) -> None:
        try:
            result = predict_live(features)

            severity = calculate_severity(
                binary_prediction=result["prediction"],
                binary_confidence=result["confidence"],
                multiclass_confidence=result[
                    "multiclass_confidence"
                ],
            )

            db = SessionLocal()

            try:
                event = PredictionEvent(
                    mode="live",
                    source_ip=features.get("srcip"),
                    destination_ip=features.get("dstip"),
                    protocol=features.get("proto"),
                    binary_prediction=result[
                        "prediction"
                    ],
                    binary_label=result["label"],
                    binary_confidence=result[
                        "confidence"
                    ],
                    attack_category=result[
                        "attack_category"
                    ],
                    multiclass_confidence=result[
                        "multiclass_confidence"
                    ],
                    severity=severity,
                    model_version=MODEL_VERSION,
                )

                db.add(event)
                db.commit()
                db.refresh(event)

            finally:
                db.close()

            payload = {
                "event": "prediction",
                "detection": {
                    "id": event.id,
                    "timestamp": (
                        event.timestamp.isoformat()
                    ),
                    "mode": event.mode,
                    "source_ip": event.source_ip,
                    "destination_ip": (
                        event.destination_ip
                    ),
                    "protocol": event.protocol,
                    "binary_prediction": (
                        event.binary_prediction
                    ),
                    "binary_label": (
                        event.binary_label
                    ),
                    "binary_confidence": (
                        event.binary_confidence
                    ),
                    "attack_category": (
                        event.attack_category
                    ),
                    "multiclass_confidence": (
                        event.multiclass_confidence
                    ),
                    "severity": event.severity,
                    "model_version": (
                        event.model_version
                    ),
                },
            }

            self._broadcast_from_capture_thread(
                payload,
            )

        except Exception as exc:
            self._last_error = str(exc)

    def _run_capture(self) -> None:
        with self._lock:
            capture = self._capture

        if capture is None:
            return

        try:
            capture.start()
        except Exception as exc:
            self._last_error = str(exc)
        finally:
            with self._lock:
                self._capture = None
                self._thread = None

    def start(self) -> None:
        interface = self._get_interface()
        flow_timeout = self._get_flow_timeout()

        if not interface:
            raise RuntimeError(
                "NIDS_LIVE_INTERFACE is not configured."
            )

        with self._lock:
            if self._thread is not None:
                raise RuntimeError(
                    "Live capture is already running."
                )

            self._last_error = None

            self._capture = LiveCapture(
                iface=interface,
                timeout_seconds=flow_timeout,
                on_flow=self._handle_flow,
            )

            self._thread = Thread(
                target=self._run_capture,
                name="nids-live-capture",
                daemon=True,
            )

            self._thread.start()

        import time

        for _ in range(50):
            if self.is_running() or self._last_error is not None:
                break

            with self._lock:
                if self._thread is None:
                    break

            time.sleep(0.02)

        if self._last_error is not None:
            raise RuntimeError(self._last_error)

    def stop(self) -> None:
        with self._lock:
            capture = self._capture

        if capture is not None:
            capture.stop()

            import time

            for _ in range(75):
                with self._lock:
                    if self._thread is None:
                        break

                time.sleep(0.02)

    def is_running(self) -> bool:
        with self._lock:
            return (
                self._capture is not None
                and self._capture.is_running()
            )

    def status(self) -> dict:
        interface = self._get_interface()
        flow_timeout = self._get_flow_timeout()

        return {
            "running": self.is_running(),
            "interface_configured": bool(interface),
            "interface": interface,
            "flow_timeout": flow_timeout,
            "last_error": self._last_error,
        }


live_capture_service = LiveCaptureService()