from typing import Any

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    features: dict[str, Any] = Field(
        ...,
        description="Raw UNSW-NB15 feature values."
    )


class PredictionResponse(BaseModel):
    prediction: int
    label: str
    confidence: float = Field(
        ge=0.0,
        le=1.0
    )


class HealthResponse(BaseModel):
    status: str
    service: str