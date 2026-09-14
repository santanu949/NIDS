from fastapi import FastAPI, HTTPException

from backend.api.inference import (
    predict_binary,
    predict_multiclass,
)

from backend.api.schemas import (
    HealthResponse,
    PredictionRequest,
    PredictionResponse,
)


app = FastAPI(
    title="NIDS ML API",
    version="1.0.0",
    description="Network Intrusion Detection System API",
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
):
    try:
        return predict_binary(
            request.features
        )
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
):
    try:
        return predict_multiclass(
            request.features
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )