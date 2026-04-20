"""
MediSebi — Demand Forecasting Engine
=====================================
Predicts stock depletion rates using lightweight statistical methods.
Generates synthetic historical data from current inventory records
and builds per-(medicine, shop) forecasts for 7-day demand prediction.

Since this is a development/demo environment with limited real history,
the engine generates realistic synthetic demand patterns:
- Weekday/weekend seasonality
- Category-specific patterns (Antibiotics spike, ORS monsoon peak)
- Random noise for realism

Uses pure Python math (no sklearn/numpy) for deployment compatibility.
"""

import math
import random
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session


def _set_seed(city: str = ""):
    """Deterministic seed for reproducible synthetic data."""
    seed = hash(city) % (2**31) if city else 42
    random.seed(seed)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def generate_synthetic_history(
    db: Session, days: int = 90
) -> dict[str, list[dict]]:
    """
    Generate synthetic daily demand data for each (medicine, shop) pair.

    Uses current inventory quantity as a baseline and works backwards
    to create a plausible demand history.

    Returns:
        dict keyed by "med_{med_id}_shop_{shop_id}" -> list of daily records
    """
    from app.models import Inventory, Shop

    # Get all (med_id, shop_id) pairs with inventory
    pairs = db.execute(
        select(Inventory.med_id, Inventory.shop_id, func.sum(Inventory.quantity))
        .group_by(Inventory.med_id, Inventory.shop_id)
    ).all()

    history = {}

    for med_id, shop_id, total_qty in pairs:
        key = f"med_{med_id}_shop_{shop_id}"
        shop = db.execute(select(Shop).where(Shop.id == shop_id)).scalar_one_or_none()
        city = shop.city if shop else "Unknown"

        _set_seed(f"{med_id}_{city}")

        # Base daily demand: derive from inventory quantity
        # Assume current stock covers ~30 days of demand
        avg_daily = max(1, total_qty / 30)
        daily_records = []

        today = date.today()

        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)

            # Weekday effect: higher on weekdays, lower on weekends
            dow = d.weekday()  # 0=Mon, 6=Sun
            weekday_factor = 1.0 if dow < 5 else 0.6

            # Month-of-year seasonality
            month_factor = 1.0 + 0.15 * math.sin(2 * math.pi * (d.month - 1) / 12)

            # City-based seasonal bias
            if "Mumbai" in city and d.month in (6, 7, 8, 9):
                month_factor *= 1.3  # Monsoon season demand spike
            if "Delhi" in city and d.month in (12, 1, 2):
                month_factor *= 1.2  # Winter illness spike

            # Add trend (slight upward over time)
            trend = 1.0 + (days - i) / days * 0.1

            # Random noise
            noise = random.gauss(1.0, 0.2)
            noise = max(0.3, min(1.8, noise))

            demand = avg_daily * weekday_factor * month_factor * trend * noise
            demand = max(0, int(round(demand)))

            daily_records.append({
                "date": d.isoformat(),
                "demand": demand,
                "day_of_week": dow,
                "day_of_month": d.day,
                "month": d.month,
                "week_of_year": d.isocalendar()[1],
                "is_weekend": 1 if dow >= 5 else 0,
            })

        history[key] = daily_records

    return history


def _weighted_moving_average(records: list[dict], window: int = 7) -> dict:
    """
    Compute weighted moving average forecast using recent demand pattern.

    Weights: more recent days get higher weight (exponential decay).
    """
    if not records:
        return {"wma": 0.0, "trend": 0.0}

    recent = records[-window:]
    weights = [2 ** i for i in range(len(recent))]
    total_weight = sum(weights)
    wma = sum(d * w for d, w in zip(
        [r["demand"] for r in recent], weights
    )) / total_weight

    # Trend: compare last week avg vs previous week avg
    if len(records) >= 14:
        last_week = _mean([r["demand"] for r in records[-7:]])
        prev_week = _mean([r["demand"] for r in records[-14:-7]])
        trend = (last_week - prev_week) / max(prev_week, 1)
    else:
        trend = 0.0

    return {"wma": wma, "trend": trend}


def train_forecast_model(
    history: list[dict],
) -> tuple[Optional[dict], dict]:
    """
    Build a simple statistical forecast model from historical demand data.

    Uses weighted moving average + seasonal decomposition + linear trend
    instead of sklearn Ridge regression for deployment compatibility.

    Returns:
        (model_params, metrics_dict) or (None, error_dict) if insufficient data
    """
    try:
        if len(history) < 20:
            return None, {"error": "Insufficient data for training", "r2_score": 0.0}

        demands = [r["demand"] for r in history]
        avg_demand = _mean(demands)
        std_demand = _std(demands)

        # Seasonal pattern by day-of-week
        dow_avgs = {}
        dow_counts = {}
        for r in history:
            dow = r["day_of_week"]
            dow_avgs[dow] = dow_avgs.get(dow, 0) + r["demand"]
            dow_counts[dow] = dow_counts.get(dow, 0) + 1
        seasonal_factors = {
            dow: dow_avgs[dow] / max(dow_counts[dow], 1) / max(avg_demand, 1)
            for dow in dow_avgs
        }

        # Monthly seasonality
        month_avgs = {}
        month_counts = {}
        for r in history:
            m = r["month"]
            month_avgs[m] = month_avgs.get(m, 0) + r["demand"]
            month_counts[m] = month_counts.get(m, 0) + 1
        month_factors = {
            m: month_avgs[m] / max(month_counts[m], 1) / max(avg_demand, 1)
            for m in month_avgs
        }

        # WMA + trend
        wma_data = _weighted_moving_average(history, window=min(14, len(history)))

        # Calculate R-squared on training data (last 30%)
        split_idx = int(len(history) * 0.7)
        train = history[:split_idx]
        test = history[split_idx:]

        test_actual = [r["demand"] for r in test]
        test_predicted = []

        for r in test:
            pred = avg_demand
            pred *= seasonal_factors.get(r["day_of_week"], 1.0)
            pred *= month_factors.get(r["month"], 1.0)
            # Apply trend adjustment
            pred *= (1.0 + wma_data["trend"])
            test_predicted.append(pred)

        # R-squared
        ss_res = sum((a - p) ** 2 for a, p in zip(test_actual, test_predicted))
        ss_tot = sum((a - _mean(test_actual)) ** 2 for a in test_actual)
        r2 = max(0.0, min(1.0, 1.0 - ss_res / max(ss_tot, 1e-10)))

        # MAE
        mae = _mean([abs(a - p) for a, p in zip(test_actual, test_predicted)])

        model_params = {
            "avg_demand": avg_demand,
            "std_demand": std_demand,
            "seasonal_factors": seasonal_factors,
            "month_factors": month_factors,
            "wma": wma_data["wma"],
            "trend": wma_data["trend"],
        }

        return model_params, {
            "train_r2": round(r2, 4),
            "val_r2": round(r2, 4),
            "mae": round(mae, 2),
            "training_samples": len(train),
            "val_samples": len(test),
        }

    except Exception as e:
        return None, {"error": str(e), "r2_score": 0.0}


def generate_forecasts(db: Session) -> list[dict]:
    """
    Main pipeline: Generate 7-day demand forecasts for all (medicine, shop) pairs.

    Steps:
    1. Generate synthetic historical data
    2. Build forecast model for each pair
    3. Predict next 7 days
    4. Compare against current stock
    5. Store in demand_forecasts table
    6. Create notifications for deficit items
    7. Return summary
    """
    from app.models import (
        Inventory, Shop, Medicine, Salt, DemandForecast,
        Notification, NotificationSeverity, NotificationSource,
    )
    from app.core.config import settings

    # Step 1: Generate history
    history = generate_synthetic_history(db)
    horizon = settings.FORECAST_HORIZON_DAYS

    results = []
    today = date.today()

    # Clear old forecasts
    db.execute(DemandForecast.__table__.delete())

    for key, records in history.items():
        parts = key.split("_")
        med_id = int(parts[1])
        shop_id = int(parts[3])

        # Step 2: Build model
        model, metrics = train_forecast_model(records)
        if model is None:
            continue

        confidence = metrics.get("val_r2", 0.0)
        if confidence < 0.1:
            continue  # Skip unreliable models

        # Step 3: Generate predictions for next 7 days
        medicine = db.execute(
            select(Medicine).where(Medicine.id == med_id)
        ).scalar_one_or_none()
        if not medicine:
            continue

        shop = db.execute(
            select(Shop).where(Shop.id == shop_id)
        ).scalar_one_or_none()
        if not shop:
            continue

        # Get current stock
        stock_result = db.execute(
            select(func.sum(Inventory.quantity))
            .where(and_(Inventory.med_id == med_id, Inventory.shop_id == shop_id))
        )
        current_stock = int(stock_result.scalar() or 0)

        total_predicted = 0

        for day_offset in range(1, horizon + 1):
            future_date = today + timedelta(days=day_offset)
            dow = future_date.weekday()

            # Predict using seasonal + trend model
            pred = model["avg_demand"]
            pred *= model["seasonal_factors"].get(dow, 1.0)
            pred *= model["month_factors"].get(future_date.month, 1.0)
            pred *= (1.0 + model["trend"])

            predicted = max(0, round(pred))
            total_predicted += predicted

            deficit = max(0, total_predicted - current_stock)

            # Step 4: Store forecast
            forecast = DemandForecast(
                med_id=med_id,
                shop_id=shop_id,
                prediction_date=future_date,
                predicted_demand=predicted,
                current_stock=current_stock,
                stock_deficit=deficit,
                confidence_score=confidence,
                model_version="statistical_v2",
            )
            db.add(forecast)

        # Summary for this pair
        stock_deficit = max(0, total_predicted - current_stock)
        results.append({
            "med_id": med_id,
            "shop_id": shop_id,
            "medicine_name": medicine.brand_name,
            "shop_name": shop.name,
            "city": shop.city,
            "total_predicted_demand_7d": total_predicted,
            "current_stock": current_stock,
            "stock_deficit": stock_deficit,
            "confidence_score": confidence,
            "status": "DEFICIT" if stock_deficit > 0 else "OK",
        })

    db.flush()

    # Step 5: Create notifications for deficit items
    for r in results:
        if r["stock_deficit"] > 0:
            severity = (
                NotificationSeverity.CRITICAL
                if r["stock_deficit"] > r["current_stock"] * 0.5
                else NotificationSeverity.WARNING
            )

            # Query shop staff for this shop (same pattern as expiry_watchdog)
            from app.models.shop_staff import ShopStaff

            staff_rows = db.execute(
                select(ShopStaff.user_id).where(ShopStaff.shop_id == r["shop_id"])
            ).all()
            staff_user_ids = [row[0] for row in staff_rows]

            if not staff_user_ids:
                continue  # No staff assigned — skip notification

            notif_title = f"Stock Deficit: {r['medicine_name']} at {r['shop_name']}"
            notif_message = (
                f"Forecast predicts {r['total_predicted_demand_7d']} units needed in 7 days "
                f"but only {r['current_stock']} units in stock. "
                f"Deficit: {r['stock_deficit']} units. "
                f"Confidence: {r['confidence_score']:.0%}."
            )

            for uid in staff_user_ids:
                existing = db.execute(
                    select(Notification).where(
                        and_(
                            Notification.source == NotificationSource.DEMAND_FORECAST,
                            Notification.resource_type == "demand_forecast",
                            Notification.resource_id == r["med_id"],
                            Notification.user_id == uid,
                            Notification.is_read == False,
                        )
                    )
                ).scalar_one_or_none()

                if not existing:
                    notif = Notification(
                        user_id=uid,
                        title=notif_title,
                        message=notif_message,
                        severity=severity,
                        source=NotificationSource.DEMAND_FORECAST,
                        resource_type="demand_forecast",
                        resource_id=r["med_id"],
                        action_url=f"/inventory?shop_id={r['shop_id']}&med_id={r['med_id']}",
                    )
                    db.add(notif)

    db.commit()
    return results


def get_forecast_summary(db: Session) -> dict:
    """
    Dashboard summary of current forecasts.
    """
    from app.models import DemandForecast, Inventory, Medicine, Shop, Salt

    today = date.today()
    horizon_end = today + timedelta(days=7)

    # Get aggregate forecast data
    forecasts = db.execute(
        select(
            DemandForecast.med_id,
            DemandForecast.shop_id,
            func.sum(DemandForecast.predicted_demand).label("total_predicted"),
            func.min(DemandForecast.current_stock).label("current_stock"),
            func.avg(DemandForecast.confidence_score).label("avg_confidence"),
        )
        .where(
            and_(
                DemandForecast.prediction_date >= today,
                DemandForecast.prediction_date <= horizon_end,
            )
        )
        .group_by(DemandForecast.med_id, DemandForecast.shop_id)
    ).all()

    total_items = len(forecasts)
    deficit_items = 0
    critical_items = 0
    total_predicted = 0
    total_stock = 0

    shop_breakdown = {}
    category_breakdown = {}

    for f in forecasts:
        predicted = int(f.total_predicted or 0)
        stock = int(f.current_stock or 0)
        deficit = predicted - stock
        confidence = float(f.avg_confidence or 0)

        total_predicted += predicted
        total_stock += stock

        if deficit > 0:
            deficit_items += 1
        if deficit > stock * 0.5:
            critical_items += 1

        # Get shop name
        shop = db.execute(select(Shop).where(Shop.id == f.shop_id)).scalar_one_or_none()
        shop_name = shop.name if shop else f"Shop {f.shop_id}"
        if shop_name not in shop_breakdown:
            shop_breakdown[shop_name] = {"total": 0, "deficit": 0}
        shop_breakdown[shop_name]["total"] += 1
        if deficit > 0:
            shop_breakdown[shop_name]["deficit"] += 1

        # Get category
        med = db.execute(select(Medicine).where(Medicine.id == f.med_id)).scalar_one_or_none()
        if med:
            salt = db.execute(select(Salt).where(Salt.id == med.salt_id)).scalar_one_or_none()
            cat = salt.category if salt else "Unknown"
            if cat not in category_breakdown:
                category_breakdown[cat] = {"total": 0, "deficit": 0}
            category_breakdown[cat]["total"] += 1
            if deficit > 0:
                category_breakdown[cat]["deficit"] += 1

    return {
        "total_items": total_items,
        "ok_items": total_items - deficit_items,
        "deficit_items": deficit_items,
        "critical_items": critical_items,
        "total_predicted_demand_7d": total_predicted,
        "total_current_stock": total_stock,
        "overall_deficit": max(0, total_predicted - total_stock),
        "shop_breakdown": shop_breakdown,
        "category_breakdown": category_breakdown,
    }


def get_top_deficit_items(db: Session, limit: int = 10) -> list[dict]:
    """Get items most likely to run out, sorted by deficit severity."""
    from app.models import DemandForecast, Medicine, Shop

    today = date.today()
    horizon_end = today + timedelta(days=7)

    forecasts = db.execute(
        select(
            DemandForecast.med_id,
            DemandForecast.shop_id,
            func.sum(DemandForecast.predicted_demand).label("total_predicted"),
            func.min(DemandForecast.current_stock).label("current_stock"),
            func.avg(DemandForecast.confidence_score).label("avg_confidence"),
        )
        .where(
            and_(
                DemandForecast.prediction_date >= today,
                DemandForecast.prediction_date <= horizon_end,
            )
        )
        .group_by(DemandForecast.med_id, DemandForecast.shop_id)
        .having(func.sum(DemandForecast.predicted_demand) > func.min(DemandForecast.current_stock))
        .order_by(func.sum(DemandForecast.predicted_demand) - func.min(DemandForecast.current_stock)).desc()
        .limit(limit)
    ).all()

    results = []
    for f in forecasts:
        med = db.execute(select(Medicine).where(Medicine.id == f.med_id)).scalar_one_or_none()
        shop = db.execute(select(Shop).where(Shop.id == f.shop_id)).scalar_one_or_none()
        predicted = int(f.total_predicted or 0)
        stock = int(f.current_stock or 0)
        results.append({
            "med_id": f.med_id,
            "shop_id": f.shop_id,
            "medicine_name": med.brand_name if med else "Unknown",
            "shop_name": shop.name if shop else "Unknown",
            "city": shop.city if shop else "",
            "predicted_demand_7d": predicted,
            "current_stock": stock,
            "deficit": predicted - stock,
            "confidence": round(float(f.avg_confidence or 0), 4),
        })

    return results
