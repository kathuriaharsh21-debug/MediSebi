"""
MediSebi — Analytics Schemas
=============================
Pydantic models for seasonal analytics and medicine usage frequency.
"""
from pydantic import BaseModel
from typing import Optional


class SeasonalUsageItem(BaseModel):
    month: str
    month_num: int
    season: str
    total_sales: float
    total_units: int
    bill_count: int
    top_medicine: Optional[str] = None
    top_salt: Optional[str] = None

    model_config = {"from_attributes": True}


class MedicineFrequencyItem(BaseModel):
    med_id: int
    medicine_name: str
    salt_name: Optional[str] = None
    total_units_sold: int
    total_revenue: float
    total_bills: int
    avg_quantity_per_bill: float
    season_breakdown: Optional[dict] = None

    model_config = {"from_attributes": True}


class SeasonalAnalyticsResponse(BaseModel):
    monthly_trend: list[SeasonalUsageItem]
    season_totals: dict
    top_medicines_by_season: dict
    period: str


class MedicineFrequencyResponse(BaseModel):
    medicines: list[MedicineFrequencyItem]
    total: int
    page: int
    size: int
