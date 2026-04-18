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

api_router = APIRouter()

# Include all sub-routers with their prefixes
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(salts_router, prefix="/salts", tags=["Salts"])
api_router.include_router(medicines_router, prefix="/medicines", tags=["Medicines"])
api_router.include_router(shops_router, prefix="/shops", tags=["Shops"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(substitution_router, prefix="/substitution", tags=["Substitution"])
