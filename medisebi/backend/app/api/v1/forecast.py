"""
MediSebi — Demand Forecast API
================================
Endpoints for generating and viewing demand forecasts.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole

from app.services.demand_forecaster import (
    generate_forecasts,
    get_forecast_summary,
    get_top_deficit_items,
)

router = APIRouter()


@router.post("/generate", summary="Generate demand forecasts")
async def run_forecast_generation(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Trigger demand forecast generation.
    Generates synthetic history, trains ML models, and creates predictions.
    Admin only — this is a computationally expensive operation.
    """
    try:
        results = generate_forecasts(db)
        deficit_count = sum(1 for r in results if r["stock_deficit"] > 0)
        return {
            "message": f"Forecasts generated for {len(results)} medicine-shop pairs",
            "total_pairs": len(results),
            "deficit_items": deficit_count,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")


@router.get("/summary", summary="Forecast dashboard summary")
async def forecast_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated forecast summary for the dashboard."""
    summary = get_forecast_summary(db)
    return summary


@router.get("/items", summary="List forecast items")
async def list_forecast_items(
    shop_id: int | None = Query(None, description="Filter by shop"),
    has_deficit: bool | None = Query(None, description="Only items with deficit"),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all forecast items with optional filters and pagination."""
    from app.models import DemandForecast, Medicine, Shop, Salt
    from sqlalchemy import select, func, and_

    today = date.today()
    horizon_end = today + timedelta(days=7)

    # Build base query
    query = (
        select(
            DemandForecast.med_id,
            DemandForecast.shop_id,
            func.sum(DemandForecast.predicted_demand).label("total_predicted"),
            func.min(DemandForecast.current_stock).label("current_stock"),
            func.avg(DemandForecast.confidence_score).label("avg_confidence"),
            func.min(DemandForecast.prediction_date).label("start_date"),
            func.max(DemandForecast.prediction_date).label("end_date"),
        )
        .where(
            and_(
                DemandForecast.prediction_date >= today,
                DemandForecast.prediction_date <= horizon_end,
            )
        )
        .group_by(DemandForecast.med_id, DemandForecast.shop_id)
    )

    # Apply filters
    if shop_id is not None:
        query = query.where(DemandForecast.shop_id == shop_id)

    if has_deficit is True:
        query = query.having(
            func.sum(DemandForecast.predicted_demand) > func.min(DemandForecast.current_stock)
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Sort by deficit descending
    query = query.order_by(
        (func.sum(DemandForecast.predicted_demand) - func.min(DemandForecast.current_stock)).desc()
    )

    # Paginate
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    rows = db.execute(query).all()

    items = []
    for row in rows:
        med = db.execute(select(Medicine).where(Medicine.id == row.med_id)).scalar_one_or_none()
        shop = db.execute(select(Shop).where(Shop.id == row.shop_id)).scalar_one_or_none()
        predicted = int(row.total_predicted or 0)
        stock = int(row.current_stock or 0)
        confidence = float(row.avg_confidence or 0)

        if min_confidence is not None and confidence < min_confidence:
            continue

        salt_name = None
        category = None
        if med:
            salt = db.execute(select(Salt).where(Salt.id == med.salt_id)).scalar_one_or_none()
            if salt:
                salt_name = salt.formula_name
                category = salt.category

        items.append({
            "med_id": row.med_id,
            "shop_id": row.shop_id,
            "medicine_name": med.brand_name if med else "Unknown",
            "salt_name": salt_name,
            "category": category,
            "shop_name": shop.name if shop else "Unknown",
            "city": shop.city if shop else "",
            "predicted_demand_7d": predicted,
            "current_stock": stock,
            "deficit": max(0, predicted - stock),
            "confidence": round(confidence, 4),
            "status": "DEFICIT" if predicted > stock else "OK",
            "forecast_start": row.start_date.isoformat() if row.start_date else None,
            "forecast_end": row.end_date.isoformat() if row.end_date else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@router.get("/top-deficits", summary="Top deficit items")
async def top_deficits(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get items most likely to run out, sorted by deficit severity."""
    items = get_top_deficit_items(db, limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/charts/demand-trend", summary="Demand trend chart data")
async def demand_trend_data(
    med_id: int = Query(..., description="Medicine ID"),
    shop_id: int = Query(..., description="Shop ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get time-series data for chart rendering.
    Returns predicted demand per day for the 7-day forecast horizon.
    """
    from app.models import DemandForecast, Medicine, Shop

    today = date.today()

    forecasts = db.execute(
        select(DemandForecast).where(
            and_(
                DemandForecast.med_id == med_id,
                DemandForecast.shop_id == shop_id,
                DemandForecast.prediction_date >= today,
            )
        ).order_by(DemandForecast.prediction_date)
    ).all()

    med = db.execute(select(Medicine).where(Medicine.id == med_id)).scalar_one_or_none()
    shop = db.execute(select(Shop).where(Shop.id == shop_id)).scalar_one_or_none()

    data_points = []
    for f in forecasts:
        data_points.append({
            "date": f.prediction_date.isoformat(),
            "predicted_demand": f.predicted_demand,
            "current_stock": f.current_stock,
            "stock_deficit": f.stock_deficit or 0,
            "confidence": round(f.confidence_score, 4) if f.confidence_score else 0,
        })

    return {
        "medicine_name": med.brand_name if med else "Unknown",
        "shop_name": shop.name if shop else "Unknown",
        "data_points": data_points,
        "forecast_horizon_days": len(data_points),
    }
