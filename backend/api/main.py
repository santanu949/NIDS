from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.api.inference import (
    predict_binary,
    predict_multiclass,
)
from backend.api.schemas import (
    HealthResponse,
    PredictionRequest,
    PredictionResponse,
)
from backend.app.database import Base, engine, get_db
from backend.app.models.prediction_event import PredictionEvent


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="NIDS ML API",
    version="1.0.0",
    description="Network Intrusion Detection System API",
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
def health_check():
    return {
        "status": "ok",
        "service": "nids-ml-api",
    }


@app.post(
    "/predict/binary",
    response_model=PredictionResponse,
)
def binary_prediction(
    request: PredictionRequest,
    db: Session = Depends(get_db),
):
    try:
        result = predict_binary(request.features)

        event = PredictionEvent(
            mode="dataset",
            prediction=result["prediction"],
            label=result["label"],
            confidence=result["confidence"],
            attack_category=(
                "Normal"
                if result["prediction"] == 0
                else "Attack"
            ),
        )

        db.add(event)
        db.commit()

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )


@app.post(
    "/predict/multiclass",
    response_model=PredictionResponse,
)
def multiclass_prediction(
    request: PredictionRequest,
    db: Session = Depends(get_db),
):
    try:
        result = predict_multiclass(request.features)

        event = PredictionEvent(
            mode="dataset",
            prediction=result["prediction"],
            label=result["label"],
            confidence=result["confidence"],
            attack_category=result["label"],
        )

        db.add(event)
        db.commit()

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )