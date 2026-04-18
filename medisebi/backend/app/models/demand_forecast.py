"""
MediSebi — Demand Forecast Model
=================================
Stores ML-generated demand predictions for each medicine at each shop.
The forecasting engine writes predictions here; the dashboard reads from here.
"""

from sqlalchemy import String, Integer, Float, ForeignKey, Date, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date

from app.core.database import Base
from app.core.mixins import TimestampMixin


class DemandForecast(Base, TimestampMixin):
    """
    Time-series demand predictions.
    One record per (medicine, shop, prediction_date) triplet.
    The Expiry Watchdog and Redistribution Engine both consume this data.
    """
    __tablename__ = "demand_forecasts"
    __table_args__ = (
        Index("ix_forecast_med_shop", "med_id", "shop_id"),
        Index("ix_forecast_date", "prediction_date"),
        Index("ix_forecast_confidence", "confidence_score"),
        {
            "comment": (
                "ML-generated demand predictions. Updated periodically by the "
                "forecasting engine. Consumed by the dashboard and alerting system."
            ),
        },
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # ── Target Entity ───────────────────────────────────────
    med_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("medicines.id", ondelete="CASCADE"),
        nullable=False,
        comment="Medicine being forecasted",
    )
    shop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        comment="Shop location for this forecast",
    )

    # ── Prediction Data ─────────────────────────────────────
    prediction_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date for which this prediction applies",
    )
    predicted_demand: Mapped[float] = mapped_column(
        Float(10, 2),
        nullable=False,
        comment="Predicted number of units that will be consumed/sold",
    )
    current_stock: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Stock level at the time the forecast was generated",
    )
    stock_deficit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="predicted_demand - current_stock (negative = surplus, positive = deficit)",
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float(5, 4),
        nullable=True,
        comment="Model confidence (0.0 to 1.0). Lower scores = less reliable predictions.",
    )
    model_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Version/tag of the ML model that generated this forecast",
    )
    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Additional model metadata (seasonal factors, feature importance, etc.)",
    )

    def __repr__(self) -> str:
        return (
            f"<DemandForecast med_id={self.med_id} shop_id={self.shop_id} "
            f"date={self.prediction_date} demand={self.predicted_demand}>"
        )
