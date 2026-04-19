"""
MediSebi — Analytics API Routes
================================
Seasonal medicine usage analytics, demand frequency charts,
and ordering recommendations by season.
"""
from datetime import datetime, date, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, extract, case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.bill import Bill, BillItem
from app.models.medicine import Medicine
from app.models.shop import Shop
from app.schemas.analytics import (
    SeasonalAnalyticsResponse,
    SeasonalUsageItem,
    MedicineFrequencyItem,
    MedicineFrequencyResponse,
)


router = APIRouter()

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

SEASON_MAP = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Monsoon", 10: "Monsoon", 11: "Monsoon",
}


def _get_season(month_num: int) -> str:
    return SEASON_MAP.get(month_num, "Unknown")


@router.get("/seasonal", response_model=SeasonalAnalyticsResponse)
def seasonal_analytics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    shop_id: Optional[int] = Query(None, description="Filter by shop"),
    year: Optional[int] = Query(None, description="Year to analyze (default current)"),
):
    """
    Get seasonal medicine usage trends.
    Returns monthly breakdown with seasonal classification.
    """
    year = year or date.today().year

    base_filter = and_(
        func.extract('year', Bill.created_at) == year,
        Bill.status == "paid",
    )
    if shop_id:
        base_filter = and_(base_filter, Bill.shop_id == shop_id)

    # Monthly trend
    monthly_rows = db.execute(
        select(
            func.extract('month', Bill.created_at).label('month_num'),
            func.sum(Bill.total_amount).label('total_sales'),
            func.count(Bill.id).label('bill_count'),
        )
        .where(base_filter)
        .group_by(func.extract('month', Bill.created_at))
        .order_by(func.extract('month', Bill.created_at))
    ).all()

    # Monthly unit data from bill_items
    monthly_units = db.execute(
        select(
            func.extract('month', Bill.created_at).label('month_num'),
            func.sum(BillItem.quantity).label('total_units'),
        )
        .join(BillItem, BillItem.bill_id == Bill.id)
        .where(base_filter)
        .group_by(func.extract('month', Bill.created_at))
        .order_by(func.extract('month', Bill.created_at))
    ).all()

    # Map units to monthly data
    units_map = {int(r.month_num): int(r.total_units or 0) for r in monthly_units}

    # Top medicine per month
    top_meds = db.execute(
        select(
            func.extract('month', Bill.created_at).label('month_num'),
            BillItem.medicine_name,
            func.sum(BillItem.quantity).label('qty'),
        )
        .join(BillItem, BillItem.bill_id == Bill.id)
        .where(base_filter)
        .group_by(func.extract('month', Bill.created_at), BillItem.medicine_name)
    ).all()

    # Find top medicine per month
    top_med_map = {}
    for r in top_meds:
        mn = int(r.month_num)
        qty = int(r.qty or 0)
        if mn not in top_med_map or qty > top_med_map[mn][1]:
            top_med_map[mn] = (r.medicine_name, qty)

    # Build monthly trend data
    monthly_trend = []
    for m in range(1, 13):
        row_data = next((r for r in monthly_rows if int(r.month_num) == m), None)
        monthly_trend.append(SeasonalUsageItem(
            month=MONTH_NAMES[m - 1],
            month_num=m,
            season=_get_season(m),
            total_sales=float(row_data.total_sales or 0) if row_data else 0.0,
            total_units=units_map.get(m, 0),
            bill_count=int(row_data.bill_count or 0) if row_data else 0,
            top_medicine=top_med_map.get(m, (None, None))[0],
        ))

    # Season totals
    season_totals = {}
    for mt in monthly_trend:
        s = mt.season
        if s not in season_totals:
            season_totals[s] = {"total_sales": 0.0, "total_units": 0, "bill_count": 0}
        season_totals[s]["total_sales"] += mt.total_sales
        season_totals[s]["total_units"] += mt.total_units
        season_totals[s]["bill_count"] += mt.bill_count

    # Top medicines by season
    season_meds = db.execute(
        select(
            BillItem.medicine_name,
            func.sum(BillItem.quantity).label('qty'),
            func.sum(BillItem.item_total).label('revenue'),
        )
        .join(Bill, Bill.id == BillItem.bill_id)
        .where(base_filter)
        .group_by(BillItem.medicine_name)
        .order_by(func.sum(BillItem.quantity).desc())
        .limit(20)
    ).all()

    top_medicines_by_season = {
        "top_overall": [
            {"name": r.medicine_name, "units_sold": int(r.qty or 0), "revenue": float(r.revenue or 0)}
            for r in season_meds
        ]
    }

    return SeasonalAnalyticsResponse(
        monthly_trend=monthly_trend,
        season_totals=season_totals,
        top_medicines_by_season=top_medicines_by_season,
        period=f"{year}",
    )


@router.get("/frequency", response_model=MedicineFrequencyResponse)
def medicine_frequency(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    shop_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    season: Optional[str] = Query(None, description="Filter by season: Winter, Spring, Summer, Monsoon"),
    sort_by: Optional[str] = Query("total_units", description="total_units, total_revenue, total_bills"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """
    Get medicine usage frequency with seasonal breakdown.
    Shows which medicines are most frequently sold and in which seasons.
    """
    base_filter = [Bill.status == "paid"]
    if shop_id:
        base_filter.append(Bill.shop_id == shop_id)

    # Season filter: map season name to month numbers
    season_months = None
    if season:
        season_months = [m for m, s in SEASON_MAP.items() if s == season]
        if season_months:
            base_filter.append(func.extract('month', Bill.created_at).in_(season_months))

    # Main aggregation
    stmt = (
        select(
            BillItem.med_id,
            BillItem.medicine_name,
            BillItem.salt_name,
            func.sum(BillItem.quantity).label('total_units_sold'),
            func.sum(BillItem.item_total).label('total_revenue'),
            func.count(func.distinct(BillItem.bill_id)).label('total_bills'),
        )
        .join(Bill, Bill.id == BillItem.bill_id)
        .where(and_(*base_filter))
        .group_by(BillItem.med_id, BillItem.medicine_name, BillItem.salt_name)
    )

    # Sort
    if sort_by == "total_revenue":
        stmt = stmt.order_by(func.sum(BillItem.item_total).desc())
    elif sort_by == "total_bills":
        stmt = stmt.order_by(func.count(func.distinct(BillItem.bill_id)).desc())
    else:
        stmt = stmt.order_by(func.sum(BillItem.quantity).desc())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    rows = db.execute(stmt.offset((page - 1) * size).limit(size)).all()

    medicines = []
    for r in rows:
        units = int(r.total_units_sold or 0)
        bills = int(r.total_bills or 0)

        # Per-season breakdown for this medicine
        season_breakdown = {}
        if not season:  # Only compute if not already filtered by season
            for s_name in ["Winter", "Spring", "Summer", "Monsoon"]:
                s_months = [m for m, s in SEASON_MAP.items() if s == s_name]
                if s_months:
                    s_units = db.execute(
                        select(func.sum(BillItem.quantity))
                        .join(Bill, Bill.id == BillItem.bill_id)
                        .where(
                            and_(
                                BillItem.med_id == r.med_id,
                                Bill.status == "paid",
                                func.extract('month', Bill.created_at).in_(s_months),
                                *([Bill.shop_id == shop_id] if shop_id else []),
                            )
                        )
                    ).scalar() or 0
                    season_breakdown[s_name] = int(s_units)

        medicines.append(MedicineFrequencyItem(
            med_id=r.med_id,
            medicine_name=r.medicine_name,
            salt_name=r.salt_name,
            total_units_sold=units,
            total_revenue=float(r.total_revenue or 0),
            total_bills=bills,
            avg_quantity_per_bill=round(units / bills, 2) if bills > 0 else 0,
            season_breakdown=season_breakdown if season_breakdown else None,
        ))

    return MedicineFrequencyResponse(
        medicines=medicines,
        total=total,
        page=page,
        size=size,
    )


@router.get("/ordering-guide")
def ordering_guide(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    shop_id: Optional[int] = Query(None),
):
    """
    Smart ordering guide based on seasonal patterns.
    Recommends which medicines to order more of based on current/upcoming season.
    """
    today = date.today()
    current_month = today.month
    current_season = _get_season(current_month)

    # Get next season
    all_seasons = ["Winter", "Spring", "Summer", "Monsoon"]
    current_idx = all_seasons.index(current_season) if current_season in all_seasons else 0
    next_season = all_seasons[(current_idx + 1) % len(all_seasons)]
    next_months = [m for m, s in SEASON_MAP.items() if s == next_season]

    # Compare this season vs next season medicine demand
    current_months = [m for m, s in SEASON_MAP.items() if s == current_season]

    filters = [Bill.status == "paid"]
    if shop_id:
        filters.append(Bill.shop_id == shop_id)

    # Next season's top medicines from LAST YEAR (historical)
    last_year = today.year - 1
    next_season_data = db.execute(
        select(
            BillItem.medicine_name,
            BillItem.salt_name,
            func.sum(BillItem.quantity).label('qty'),
            func.sum(BillItem.item_total).label('revenue'),
        )
        .join(Bill, Bill.id == BillItem.bill_id)
        .where(and_(
            *filters,
            func.extract('year', Bill.created_at) == last_year,
            func.extract('month', Bill.created_at).in_(next_months),
        ))
        .group_by(BillItem.medicine_name, BillItem.salt_name)
        .order_by(func.sum(BillItem.quantity).desc())
        .limit(20)
    ).all()

    return {
        "current_season": current_season,
        "next_season": next_season,
        "current_month": MONTH_NAMES[current_month - 1],
        "based_on_year": last_year,
        "recommendations": [
            {
                "medicine_name": r.medicine_name,
                "salt_name": r.salt_name,
                "historical_units_sold": int(r.qty or 0),
                "historical_revenue": float(r.revenue or 0),
                "suggested_action": "Consider stocking up before season starts" if (r.qty or 0) > 10 else "Moderate demand expected",
                "priority": "HIGH" if (r.qty or 0) > 20 else "MEDIUM" if (r.qty or 0) > 10 else "LOW",
            }
            for r in next_season_data
        ],
    }
