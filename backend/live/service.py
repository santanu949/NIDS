from __future__ import annotations
from threading import Lock, Thread

from backend.app.config import LIVE_FLOW_TIMEOUT, LIVE_INTERFACE
from backend.app.database import SessionLocal
from backend.app.models.prediction_event import PredictionEvent
from backend.live.capture import LiveCapture
from backend.live.predict_live import predict_live

class LiveCaptureService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._capture: LiveCapture | None = None
        self._thread: Thread | None = None
        self._last_error: str | None = None

    def _handle_flow(self, features: dict) -> None:
        try:
            result = predict_live(features)
            db = SessionLocal()
            try:
                event = PredictionEvent(mode="live", binary_prediction=result["prediction"], binary_label=result["label"], binary_confidence=result["confidence"], attack_category=result["attack_category"], multiclass_confidence=result["multiclass_confidence"])
                db.add(event)
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            self._last_error = str(exc)

    def _run_capture(self) -> None:
        if self._capture is None:
            return
        try:
            self._capture.start()
        except Exception as exc:
            self._last_error = str(exc)
        finally:
            with self._lock:
                self._capture = None
                self._thread = None

    def start(self) -> None:
        if not LIVE_INTERFACE:
            raise RuntimeError("NIDS_LIVE_INTERFACE is not configured.")
        with self._lock:
            if self._capture is not None and self._capture.is_running():
                raise RuntimeError("Live capture is already running.")
            self._last_error = None
            self._capture = LiveCapture(iface=LIVE_INTERFACE, timeout_seconds=LIVE_FLOW_TIMEOUT, on_flow=self._handle_flow)
            self._thread = Thread(target=self._run_capture, name="nids-live-capture", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            capture = self._capture
        if capture is not None:
            capture.stop()

    def is_running(self) -> bool:
        with self._lock:
            return self._capture is not None and self._capture.is_running()

    def status(self) -> dict:
        return {"running": self.is_running(), "interface_configured": bool(LIVE_INTERFACE), "interface": LIVE_INTERFACE, "flow_timeout": LIVE_FLOW_TIMEOUT, "last_error": self._last_error}

live_capture_service = LiveCaptureService()