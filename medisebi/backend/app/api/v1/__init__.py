"""
MediSebi — API v1 Router
=========================
Aggregates all sub-routers under a single api_router.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.salts import router as salts_router
from app.api.v1.medicines import router as medicines_router
from app.api.v1.shops import router as shops_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.substitution import router as substitution_router
from app.api.v1.expiry import router as expiry_router
from app.api.v1.climate import router as climate_router
from app.api.v1.transfers import router as transfers_router
from app.api.v1.forecast import router as forecast_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.marketplace import router as marketplace_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.billing import router as billing_router
from app.api.v1.analytics import router as analytics_router

api_router = APIRouter()

# Include all sub-routers with their prefixes
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(salts_router, prefix="/salts", tags=["Salts"])
api_router.include_router(medicines_router, prefix="/medicines", tags=["Medicines"])
api_router.include_router(shops_router, prefix="/shops", tags=["Shops"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(substitution_router, prefix="/substitution", tags=["Substitution"])
api_router.include_router(expiry_router, prefix="/expiry", tags=["Expiry Watchdog"])
api_router.include_router(climate_router, prefix="/climate", tags=["Climate Intelligence"])
api_router.include_router(transfers_router, prefix="/transfers", tags=["Redistribution"])
api_router.include_router(forecast_router, prefix="/forecast", tags=["Demand Forecast"])
api_router.include_router(catalog_router, prefix="/catalog", tags=["Medicine Catalog"])
api_router.include_router(marketplace_router, prefix="/marketplace", tags=["Marketplace"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(billing_router, prefix="/bills", tags=["Billing"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
