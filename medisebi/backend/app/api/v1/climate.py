"""
MediSebi — Climate Intelligence API Routes
============================================
REST endpoints for the Climate-Disease Intelligence Engine.
Provides weather data retrieval, disease risk scanning, and alert dashboards.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.models.climate_alert import ClimateAlert, RiskLevel
from app.services.climate_engine import fetch_weather_for_shop, generate_climate_alerts

router = APIRouter()


# ── TRIGGER CLIMATE SCAN ─────────────────────────────────────────
@router.get("/scan", summary="Trigger climate scan for all shops")
def trigger_climate_scan(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """
    Scan all active shops for climate-based disease risks.
    Generates ClimateAlert and Notification records for significant risks.
    """
    alerts = generate_climate_alerts(db)
    db.commit()
    return {
        "status": "ok",
        "message": f"Climate scan complete. Generated {len(alerts)} significant alert(s).",
        "alerts": alerts,
    }


# ── SHOP-SPECIFIC CLIMATE ALERTS ─────────────────────────────────
@router.get("/shop/{shop_id}", summary="Get climate alerts for a specific shop")
def shop_climate_alerts(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get all climate alerts for a specific shop.
    Ordered by most recent first. Supports risk_level filtering.
    """
    # Verify shop exists
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id)
    ).scalar_one_or_none()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={shop_id} not found",
        )

    stmt = (
        select(ClimateAlert)
        .where(ClimateAlert.shop_id == shop_id)
        .order_by(ClimateAlert.created_at.desc())
    )

    alerts = db.execute(stmt).scalars().all()

    return {
        "shop_id": shop_id,
        "shop_name": shop.name,
        "city": shop.city,
        "total_alerts": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "city": a.city,
                "temperature_c": a.temperature_c,
                "humidity_pct": a.humidity_pct,
                "weather_condition": a.weather_condition,
                "risk_level": a.risk_level.value,
                "disease_risk": a.disease_risk,
                "recommended_salts": a.recommended_salts,
                "recommended_medicines": a.recommended_medicines,
                "action_summary": a.action_summary,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ],
    }


# ── DASHBOARD: ALL ACTIVE CLIMATE ALERTS ─────────────────────────
@router.get("/dashboard", summary="Get all active climate alerts with disease breakdown")
def climate_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    risk_level: str | None = Query(None, description="Filter by risk level: low, moderate, high, critical"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
):
    """
    Dashboard widget data: all climate alerts with disease breakdown.
    Supports risk level filtering and pagination.
    """
    stmt = select(ClimateAlert).order_by(ClimateAlert.created_at.desc())

    if risk_level is not None:
        try:
            level_enum = RiskLevel(risk_level.lower())
            stmt = stmt.where(ClimateAlert.risk_level == level_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk_level: {risk_level}. Must be one of: low, moderate, high, critical",
            )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar() or 0

    # Paginate
    alerts = db.execute(
        stmt.offset((page - 1) * size).limit(size)
    ).scalars().all()

    # Disease breakdown
    disease_breakdown = _get_disease_breakdown(db)

    # Risk level summary
    risk_summary = _get_risk_summary(db)

    return {
        "total_alerts": total,
        "risk_summary": risk_summary,
        "disease_breakdown": disease_breakdown,
        "alerts": [
            {
                "id": a.id,
                "shop_id": a.shop_id,
                "city": a.city,
                "temperature_c": a.temperature_c,
                "humidity_pct": a.humidity_pct,
                "weather_condition": a.weather_condition,
                "risk_level": a.risk_level.value,
                "disease_risk": a.disease_risk,
                "recommended_salts": a.recommended_salts,
                "recommended_medicines": a.recommended_medicines,
                "action_summary": a.action_summary,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ],
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if total > 0 else 1,
    }


# ── CURRENT WEATHER FOR A SHOP ───────────────────────────────────
@router.get("/weather/{shop_id}", summary="Get current weather data for a shop")
def shop_weather(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get current weather data for a specific shop (cached for 30 minutes).
    Uses OpenWeather API if configured, otherwise returns simulated data.
    """
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id)
    ).scalar_one_or_none()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={shop_id} not found",
        )

    if shop.latitude is None or shop.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Shop {shop.name} does not have geographic coordinates configured",
        )

    weather = fetch_weather_for_shop(shop)
    if weather is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch weather data for this shop",
        )

    # Also run disease risk assessment for display
    from app.services.climate_engine import assess_disease_risks
    risks = assess_disease_risks(weather)

    # Determine data source safely
    try:
        raw = json.loads(weather.get("raw_response") or "{}")
        data_source = "simulated" if raw.get("simulated") is True else "openweather_api"
    except (json.JSONDecodeError, TypeError, ValueError):
        data_source = "openweather_api"

    return {
        "shop_id": shop_id,
        "shop_name": shop.name,
        "city": shop.city,
        "latitude": shop.latitude,
        "longitude": shop.longitude,
        "weather": {
            "temperature_c": weather["temperature_c"],
            "humidity_pct": weather["humidity_pct"],
            "weather_condition": weather["weather_condition"],
            "data_source": data_source,
        },
        "disease_risks": [
            {
                "disease": r["disease"],
                "risk_level": r["risk_level"].value,
                "risk_score": r["risk_score"],
                "risk_description": r["risk_description"],
                "recommended_salts": r["recommended_salts"],
            }
            for r in risks
        ],
    }


# ---------------------------------------------------------------------------
# Internal helpers for dashboard aggregation
# ---------------------------------------------------------------------------

def _get_disease_breakdown(db: Session) -> list[dict]:
    """Aggregate alerts by disease name."""
    stmt = (
        select(
            ClimateAlert.disease_risk,
            func.count(ClimateAlert.id).label("count"),
        )
        .group_by(ClimateAlert.disease_risk)
        .order_by(func.count(ClimateAlert.id).desc())
    )

    rows = db.execute(stmt).all()
    return [
        {"disease": row.disease_risk, "alert_count": row.count}
        for row in rows
    ]


def _get_risk_summary(db: Session) -> dict:
    """Count alerts per risk level."""
    stmt = (
        select(
            ClimateAlert.risk_level,
            func.count(ClimateAlert.id).label("count"),
        )
        .group_by(ClimateAlert.risk_level)
    )

    rows = db.execute(stmt).all()
    summary = {
        "critical": 0,
        "high": 0,
        "moderate": 0,
        "low": 0,
        "total": 0,
    }
    for row in rows:
        key = row.risk_level.value
        if key in summary:
            summary[key] = row.count
        summary["total"] += row.count

    return summary
