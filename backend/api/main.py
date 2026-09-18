from __future__ import annotations

import asyncio
import csv
import io
import json
from pathlib import Path
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.inference import predict_binary, predict_multiclass
from backend.api.schemas import (
    AnalyticsResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    DashboardSummaryResponse,
    DetectionListResponse,
    HealthResponse,
    LiveStatusResponse,
    ModelFeature,
    ModelFeaturesResponse,
    ModelMetric,
    ModelMetricsResponse,
    PredictionEventResponse,
    PredictionRequest,
    PredictionResponse,
)
from backend.api.websocket import alert_manager
from backend.app.database import Base, SessionLocal, engine, get_db
from backend.app.models.prediction_event import PredictionEvent
from backend.live.service import live_capture_service


BASE_DIR = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = BASE_DIR / "ml" / "artifacts"

MODEL_COMPARISON_PATH = (
    ARTIFACT_DIR / "model_comparison_results.json"
)

MULTICLASS_RESULTS_PATH = (
    ARTIFACT_DIR / "xgboost_multiclass_results.json"
)

OFFICIAL_TEST_RESULTS_PATH = (
    ARTIFACT_DIR / "official_test_results.json"
)

MODEL_VERSION = "xgboost-1.0"


app = FastAPI(
    title="NIDS ML API",
    description=(
        "Network Intrusion Detection System "
        "inference and monitoring API."
    ),
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    Base.metadata.create_all(bind=engine)
    live_capture_service.set_event_loop(
        asyncio.get_running_loop()
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def calculate_severity(
    binary_prediction: int,
    binary_confidence: float,
    attack_category: str,
) -> str:
    if binary_prediction == 0:
        return "low"

    category = attack_category.lower()

    if category in {"worms", "shellcode", "backdoor"}:
        return "critical"

    if binary_confidence >= 0.90:
        return "high"

    if binary_confidence >= 0.70:
        return "medium"

    return "low"


def prediction_to_response(
    binary_result: dict[str, Any],
    multiclass_result: dict[str, Any],
) -> PredictionResponse:
    attack_category = multiclass_result["label"]

    severity = calculate_severity(
        binary_prediction=binary_result["prediction"],
        binary_confidence=binary_result["confidence"],
        attack_category=attack_category,
    )

    return PredictionResponse(
        prediction=binary_result["prediction"],
        label=binary_result["label"],
        confidence=binary_result["confidence"],
        attack_category=attack_category,
        multiclass_confidence=multiclass_result["confidence"],
        severity=severity,
        model_version=MODEL_VERSION,
    )


def run_prediction(
    features: dict[str, Any],
) -> PredictionResponse:
    binary_result = predict_binary(features)
    multiclass_result = predict_multiclass(features)

    return prediction_to_response(
        binary_result=binary_result,
        multiclass_result=multiclass_result,
    )


def persist_prediction(
    db: Session,
    request: PredictionRequest,
    result: PredictionResponse,
) -> PredictionEvent:
    event = PredictionEvent(
        mode=request.mode,
        source_ip=request.features.get("srcip"),
        destination_ip=request.features.get("dstip"),
        protocol=request.features.get("proto"),
        binary_prediction=result.prediction,
        binary_label=result.label,
        binary_confidence=result.confidence,
        attack_category=result.attack_category,
        multiclass_confidence=result.multiclass_confidence,
        severity=result.severity,
        model_version=result.model_version,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event


@app.get(
    "/health",
    response_model=HealthResponse,
)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="nids-ml-api",
    )


@app.get(
    "/api/dashboard/summary",
    response_model=DashboardSummaryResponse,
)
def get_dashboard_summary(
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    total_events = (
        db.query(func.count(PredictionEvent.id))
        .scalar()
        or 0
    )

    malicious_events = (
        db.query(func.count(PredictionEvent.id))
        .filter(
            PredictionEvent.binary_prediction == 1
        )
        .scalar()
        or 0
    )

    normal_events = (
        db.query(func.count(PredictionEvent.id))
        .filter(
            PredictionEvent.binary_prediction == 0
        )
        .scalar()
        or 0
    )

    high_severity_events = (
        db.query(func.count(PredictionEvent.id))
        .filter(
            PredictionEvent.severity.in_(
                ["high", "critical"]
            )
        )
        .scalar()
        or 0
    )

    recent_events = (
        db.query(PredictionEvent)
        .order_by(
            PredictionEvent.timestamp.desc()
        )
        .limit(10)
        .all()
    )

    threat_rate = (
        malicious_events / total_events
        if total_events
        else 0.0
    )

    return DashboardSummaryResponse(
        total_events=total_events,
        malicious_events=malicious_events,
        normal_events=normal_events,
        threat_rate=threat_rate,
        high_severity_events=high_severity_events,
        live_capture_running=(
            live_capture_service.is_running()
        ),
        recent_events=recent_events,
    )


@app.post(
    "/predict",
    response_model=PredictionResponse,
)
@app.post(
    "/api/predict",
    response_model=PredictionResponse,
)
async def predict(
    request: PredictionRequest,
    db: Session = Depends(get_db),
) -> PredictionResponse:
    try:
        result = run_prediction(
            request.features
        )

        event = persist_prediction(
            db=db,
            request=request,
            result=result,
        )

        await alert_manager.broadcast(
            {
                "event": "prediction",
                "detection": {
                    "id": event.id,
                    "timestamp": event.timestamp.isoformat(),
                    "mode": event.mode,
                    "source_ip": event.source_ip,
                    "destination_ip": event.destination_ip,
                    "protocol": event.protocol,
                    "binary_prediction": (
                        event.binary_prediction
                    ),
                    "binary_label": event.binary_label,
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
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {exc}",
        ) from exc


@app.post(
    "/api/predict/batch",
    response_model=BatchPredictionResponse,
)
async def predict_batch(
    request: BatchPredictionRequest,
    db: Session = Depends(get_db),
) -> BatchPredictionResponse:
    results: list[PredictionResponse] = []

    for prediction_request in request.predictions:
        try:
            result = run_prediction(
                prediction_request.features
            )

            event = persist_prediction(
                db=db,
                request=prediction_request,
                result=result,
            )

            results.append(result)

            await alert_manager.broadcast(
                {
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
            )

        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Batch prediction failed: {exc}"
                ),
            ) from exc

    return BatchPredictionResponse(
        results=results,
        total=len(results),
    )


@app.get(
    "/events",
    response_model=list[PredictionEventResponse],
)
def get_events(
    db: Session = Depends(get_db),
) -> list[PredictionEvent]:
    return (
        db.query(PredictionEvent)
        .order_by(
            PredictionEvent.timestamp.desc()
        )
        .limit(100)
        .all()
    )


@app.get(
    "/api/detections",
    response_model=DetectionListResponse,
)
def get_detections(
    db: Session = Depends(get_db),
    attack_category: str | None = Query(
        default=None
    ),
    severity: str | None = Query(
        default=None
    ),
    protocol: str | None = Query(
        default=None
    ),
    mode: str | None = Query(
        default=None
    ),
    malicious_only: bool = Query(
        default=False
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> DetectionListResponse:
    query = db.query(PredictionEvent)

    if attack_category:
        query = query.filter(
            PredictionEvent.attack_category
            == attack_category
        )

    if severity:
        query = query.filter(
            PredictionEvent.severity == severity
        )

    if protocol:
        query = query.filter(
            PredictionEvent.protocol == protocol
        )

    if mode:
        query = query.filter(
            PredictionEvent.mode == mode
        )

    if malicious_only:
        query = query.filter(
            PredictionEvent.binary_prediction == 1
        )

    total = query.count()

    items = (
        query
        .order_by(
            PredictionEvent.timestamp.desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return DetectionListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/api/detections/export.csv",
)
def export_detections_csv(
    db: Session = Depends(get_db),
    malicious_only: bool = Query(
        default=False
    ),
) -> StreamingResponse:
    query = db.query(PredictionEvent)

    if malicious_only:
        query = query.filter(
            PredictionEvent.binary_prediction == 1
        )

    events = (
        query
        .order_by(
            PredictionEvent.timestamp.desc()
        )
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "id",
            "timestamp",
            "mode",
            "source_ip",
            "destination_ip",
            "protocol",
            "binary_prediction",
            "binary_label",
            "binary_confidence",
            "attack_category",
            "multiclass_confidence",
            "severity",
            "model_version",
        ]
    )

    for event in events:
        writer.writerow(
            [
                event.id,
                event.timestamp.isoformat(),
                event.mode,
                event.source_ip,
                event.destination_ip,
                event.protocol,
                event.binary_prediction,
                event.binary_label,
                event.binary_confidence,
                event.attack_category,
                event.multiclass_confidence,
                event.severity,
                event.model_version,
            ]
        )

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; "
                "filename=nids_detections.csv"
            )
        },
    )


@app.get(
    "/api/detections/{detection_id}",
    response_model=PredictionEventResponse,
)
def get_detection(
    detection_id: int,
    db: Session = Depends(get_db),
) -> PredictionEvent:
    event = (
        db.query(PredictionEvent)
        .filter(
            PredictionEvent.id == detection_id
        )
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Detection not found.",
        )

    return event


@app.get(
    "/analytics",
    response_model=AnalyticsResponse,
)
@app.get(
    "/api/analytics/attacks",
    response_model=AnalyticsResponse,
)
def get_analytics(
    db: Session = Depends(get_db),
) -> AnalyticsResponse:
    total_events = (
        db.query(func.count(PredictionEvent.id))
        .scalar()
        or 0
    )

    normal_events = (
        db.query(func.count(PredictionEvent.id))
        .filter(
            PredictionEvent.binary_prediction == 0
        )
        .scalar()
        or 0
    )

    attack_events = (
        db.query(func.count(PredictionEvent.id))
        .filter(
            PredictionEvent.binary_prediction == 1
        )
        .scalar()
        or 0
    )

    average_binary_confidence = (
        db.query(
            func.avg(
                PredictionEvent.binary_confidence
            )
        )
        .scalar()
        or 0.0
    )

    average_multiclass_confidence = (
        db.query(
            func.avg(
                PredictionEvent.multiclass_confidence
            )
        )
        .scalar()
        or 0.0
    )

    category_rows = (
        db.query(
            PredictionEvent.attack_category,
            func.count(PredictionEvent.id),
        )
        .group_by(
            PredictionEvent.attack_category
        )
        .order_by(
            func.count(
                PredictionEvent.id
            ).desc()
        )
        .all()
    )

    attack_categories = {
        category: count
        for category, count in category_rows
    }

    attack_rate = (
        attack_events / total_events
        if total_events
        else 0.0
    )

    return AnalyticsResponse(
        total_events=total_events,
        normal_events=normal_events,
        attack_events=attack_events,
        attack_rate=attack_rate,
        average_binary_confidence=float(
            average_binary_confidence
        ),
        average_multiclass_confidence=float(
            average_multiclass_confidence
        ),
        attack_categories=attack_categories,
    )


@app.get(
    "/api/model/metrics",
    response_model=ModelMetricsResponse,
)
def get_model_metrics() -> ModelMetricsResponse:
    comparison = load_json(
        MODEL_COMPARISON_PATH
    )

    multiclass = load_json(
        MULTICLASS_RESULTS_PATH
    )

    binary_models: list[ModelMetric] = []

    for result in comparison["models"]:
        binary_models.append(
            ModelMetric(
                model=result["model"],
                accuracy=float(
                    result["validation_accuracy"]
                ),
                precision=float(
                    result["validation_precision"]
                ),
                recall=float(
                    result["validation_recall"]
                ),
                f1=float(
                    result["validation_f1"]
                ),
                false_positive_rate=float(
                    result["false_positive_rate"]
                ),
            )
        )

    metrics_validation = (
        multiclass["metrics_validation"]
    )

    return ModelMetricsResponse(
        dataset=comparison["dataset"],
        primary_model=comparison["primary_model"],
        model_selection_metric=(
            comparison["model_selection_metric"]
        ),
        official_test_set_used=bool(
            comparison["official_test_set_used"]
        ),
        official_test_evaluation_available=(
            OFFICIAL_TEST_RESULTS_PATH.exists()
        ),
        training_rows=int(
            comparison["split"]["training_rows"]
        ),
        validation_rows=int(
            comparison["split"]["validation_rows"]
        ),
        transformed_feature_count=int(
            comparison["preprocessing"][
                "feature_count_after_transform"
            ]
        ),
        binary_models=binary_models,
        multiclass_accuracy=float(
            metrics_validation["accuracy"]
        ),
        multiclass_weighted_precision=float(
            metrics_validation[
                "weighted_precision"
            ]
        ),
        multiclass_weighted_recall=float(
            metrics_validation[
                "weighted_recall"
            ]
        ),
        multiclass_weighted_f1=float(
            metrics_validation["weighted_f1"]
        ),
        multiclass_macro_f1=float(
            metrics_validation["macro_f1"]
        ),
    )


def _load_preprocessor_feature_names() -> list[str]:
    from backend.api.inference import (
        _load_preprocessor,
    )

    preprocessor = _load_preprocessor()

    try:
        return list(
            preprocessor.get_feature_names_out()
        )
    except AttributeError:
        schema = load_json(
            BASE_DIR
            / "data"
            / "feature_schema.json"
        )

        return list(
            schema["final_feature_order"]
        )


@app.get(
    "/api/model/features",
    response_model=ModelFeaturesResponse,
)
def get_model_features() -> ModelFeaturesResponse:
    from backend.api.inference import (
        _load_binary_model,
    )

    model = _load_binary_model()

    feature_names = (
        _load_preprocessor_feature_names()
    )

    importances = model.feature_importances_

    sorted_features = sorted(
        zip(
            feature_names,
            importances,
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    features = [
        ModelFeature(
            name=name,
            importance=float(importance),
            rank=rank,
        )
        for rank, (name, importance) in enumerate(
            sorted_features,
            start=1,
        )
    ]

    return ModelFeaturesResponse(
        model="XGBoost",
        feature_count=len(features),
        features=features,
    )


@app.get(
    "/live/status",
    response_model=LiveStatusResponse,
)
def get_live_status() -> LiveStatusResponse:
    return live_capture_service.status()


@app.post(
    "/live/start",
    response_model=LiveStatusResponse,
)
def start_live_capture() -> LiveStatusResponse:
    try:
        live_capture_service.start()

        return live_capture_service.status()

    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to start live capture: "
                f"{exc}"
            ),
        ) from exc


@app.post(
    "/live/stop",
    response_model=LiveStatusResponse,
)
def stop_live_capture() -> LiveStatusResponse:
    try:
        live_capture_service.stop()

        return live_capture_service.status()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to stop live capture: "
                f"{exc}"
            ),
        ) from exc


@app.websocket("/ws/alerts")
async def websocket_alerts(
    websocket: WebSocket,
) -> None:
    await alert_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        alert_manager.disconnect(websocket)
    except Exception:
        alert_manager.disconnect(websocket)
