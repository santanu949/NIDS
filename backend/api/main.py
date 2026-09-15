from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.inference import predict_binary, predict_multiclass
from backend.api.schemas import (
    AnalyticsResponse,
    HealthResponse,
    LiveStatusResponse,
    PredictionEventResponse,
    PredictionRequest,
    PredictionResponse,
)
from backend.app.database import Base, engine, get_db
from backend.app.models.prediction_event import PredictionEvent
from backend.live.service import live_capture_service


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="NIDS Monitor API",
    description="Network Intrusion Detection System inference API.",
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


@app.get(
    "/health",
    response_model=HealthResponse,
)
def health() -> HealthResponse:
    return HealthResponse(
        status="online",
        service="NIDS FastAPI",
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
        .order_by(PredictionEvent.timestamp.desc())
        .limit(50)
        .all()
    )


@app.get(
    "/analytics",
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
        .filter(PredictionEvent.binary_prediction == 0)
        .scalar()
        or 0
    )

    attack_events = (
        db.query(func.count(PredictionEvent.id))
        .filter(PredictionEvent.binary_prediction == 1)
        .scalar()
        or 0
    )

    average_binary_confidence = (
        db.query(func.avg(PredictionEvent.binary_confidence))
        .scalar()
        or 0.0
    )

    average_multiclass_confidence = (
        db.query(func.avg(PredictionEvent.multiclass_confidence))
        .scalar()
        or 0.0
    )

    category_rows = (
        db.query(
            PredictionEvent.attack_category,
            func.count(PredictionEvent.id),
        )
        .group_by(PredictionEvent.attack_category)
        .order_by(func.count(PredictionEvent.id).desc())
        .all()
    )

    attack_categories = {
        category: count
        for category, count in category_rows
    }

    attack_rate = (
        attack_events / total_events
        if total_events > 0
        else 0.0
    )

    return AnalyticsResponse(
        total_events=total_events,
        normal_events=normal_events,
        attack_events=attack_events,
        attack_rate=attack_rate,
        average_binary_confidence=float(average_binary_confidence),
        average_multiclass_confidence=float(average_multiclass_confidence),
        attack_categories=attack_categories,
    )


@app.get(
    "/live/status",
    response_model=LiveStatusResponse,
)
def live_status() -> LiveStatusResponse:
    return LiveStatusResponse(
        **live_capture_service.status(),
    )


@app.post(
    "/live/start",
    response_model=LiveStatusResponse,
)
def live_start() -> LiveStatusResponse:
    try:
        live_capture_service.start()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return LiveStatusResponse(
        **live_capture_service.status(),
    )


@app.post(
    "/live/stop",
    response_model=LiveStatusResponse,
)
def live_stop() -> LiveStatusResponse:
    live_capture_service.stop()

    return LiveStatusResponse(
        **live_capture_service.status(),
    )


@app.post(
    "/predict",
    response_model=PredictionResponse,
)
def predict(
    request: PredictionRequest,
    db: Session = Depends(get_db),
) -> PredictionResponse:
    if request.mode == "live":
        from backend.live.predict_live import predict_live

        result = predict_live(request.features)

        binary_prediction = result["prediction"]
        binary_label = result["label"]
        binary_confidence = result["confidence"]
        attack_category = result["attack_category"]
        multiclass_confidence = result["multiclass_confidence"]

    else:
        binary_result = predict_binary(request.features)
        multiclass_result = predict_multiclass(request.features)

        binary_prediction = binary_result["prediction"]
        binary_label = binary_result["label"]
        binary_confidence = binary_result["confidence"]
        attack_category = multiclass_result["label"]
        multiclass_confidence = multiclass_result["confidence"]

    event = PredictionEvent(
        mode=request.mode,
        binary_prediction=binary_prediction,
        binary_label=binary_label,
        binary_confidence=binary_confidence,
        attack_category=attack_category,
        multiclass_confidence=multiclass_confidence,
    )

    db.add(event)
    db.commit()

    return PredictionResponse(
        prediction=binary_prediction,
        label=binary_label,
        confidence=binary_confidence,
        attack_category=attack_category,
        multiclass_confidence=multiclass_confidence,
    )