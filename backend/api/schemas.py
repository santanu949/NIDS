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
    severity: str
    model_version: str


class BatchPredictionRequest(BaseModel):
    predictions: list[PredictionRequest] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Batch of raw flow prediction requests.",
    )


class BatchPredictionResponse(BaseModel):
    results: list[PredictionResponse]
    total: int


class HealthResponse(BaseModel):
    status: str
    service: str


class PredictionEventResponse(BaseModel):
    id: int
    timestamp: datetime
    mode: str

    source_ip: str | None = None
    destination_ip: str | None = None
    protocol: str | None = None

    binary_prediction: int
    binary_label: str
    binary_confidence: float = Field(ge=0.0, le=1.0)

    attack_category: str
    multiclass_confidence: float = Field(ge=0.0, le=1.0)

    severity: str
    model_version: str

    model_config = ConfigDict(from_attributes=True)


class DetectionListResponse(BaseModel):
    items: list[PredictionEventResponse]
    total: int
    limit: int
    offset: int


class AnalyticsResponse(BaseModel):
    total_events: int
    normal_events: int
    attack_events: int
    attack_rate: float = Field(ge=0.0, le=1.0)
    average_binary_confidence: float = Field(ge=0.0, le=1.0)
    average_multiclass_confidence: float = Field(ge=0.0, le=1.0)
    attack_categories: dict[str, int]


class DashboardSummaryResponse(BaseModel):
    total_events: int
    malicious_events: int
    normal_events: int
    threat_rate: float = Field(ge=0.0, le=1.0)
    high_severity_events: int
    live_capture_running: bool
    recent_events: list[PredictionEventResponse]


class AttackCategoryMetric(BaseModel):
    category: str
    count: int


class ModelMetric(BaseModel):
    model: str
    accuracy: float = Field(ge=0.0, le=1.0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    false_positive_rate: float = Field(ge=0.0, le=1.0)


class ModelMetricsResponse(BaseModel):
    dataset: str
    primary_model: str
    model_selection_metric: str
    official_test_set_used: bool
    training_rows: int
    validation_rows: int
    transformed_feature_count: int
    binary_models: list[ModelMetric]

    multiclass_accuracy: float = Field(ge=0.0, le=1.0)
    multiclass_weighted_precision: float = Field(ge=0.0, le=1.0)
    multiclass_weighted_recall: float = Field(ge=0.0, le=1.0)
    multiclass_weighted_f1: float = Field(ge=0.0, le=1.0)
    multiclass_macro_f1: float = Field(ge=0.0, le=1.0)


class ModelFeature(BaseModel):
    name: str
    importance: float = Field(ge=0.0)
    rank: int


class ModelFeaturesResponse(BaseModel):
    model: str
    feature_count: int
    features: list[ModelFeature]


class LiveStatusResponse(BaseModel):
    running: bool
    interface_configured: bool
    interface: str
    flow_timeout: float
    last_error: str | None