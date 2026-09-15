from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    features: dict[str, Any] = Field(
        ...,
        description="Raw UNSW-NB15 feature values.",
    )
    mode: Literal["dataset", "live"] = Field(
        default="dataset",
        description="Prediction mode: dataset or live.",
    )


class PredictionResponse(BaseModel):
    prediction: int
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    attack_category: str
    multiclass_confidence: float = Field(ge=0.0, le=1.0)


class HealthResponse(BaseModel):
    status: str
    service: str


class PredictionEventResponse(BaseModel):
    id: int
    timestamp: datetime
    mode: str

    binary_prediction: int
    binary_label: str
    binary_confidence: float = Field(ge=0.0, le=1.0)

    attack_category: str
    multiclass_confidence: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(from_attributes=True)


class AnalyticsResponse(BaseModel):
    total_events: int
    normal_events: int
    attack_events: int
    attack_rate: float = Field(ge=0.0, le=1.0)
    average_binary_confidence: float = Field(ge=0.0, le=1.0)
    average_multiclass_confidence: float = Field(ge=0.0, le=1.0)
    attack_categories: dict[str, int]


class LiveStatusResponse(BaseModel):
    running: bool
    interface_configured: bool
    interface: str
    flow_timeout: float
    last_error: str | None