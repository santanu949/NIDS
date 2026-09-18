from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class PredictionEvent(Base):
    __tablename__ = "prediction_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    source_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    destination_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    protocol: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    binary_prediction: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    binary_label: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    binary_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    attack_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    multiclass_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="low",
    )

    model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="xgboost-1.0",
    )