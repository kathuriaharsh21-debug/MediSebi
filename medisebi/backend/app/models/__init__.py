"""
MediSebi — Model Registry
==========================
Single import point for ALL SQLAlchemy ORM models.
Import this module to ensure all models are registered with the Base
metadata before creating tables or running migrations.

Usage:
    from app.models import Base, User, Salt, Medicine, Inventory, AuditLog
    Base.metadata.create_all(bind=engine)
"""

from app.core.database import Base

# ── Import all models to register them with Base.metadata ──────
from app.models.user import User, UserRole
from app.models.salt import Salt
from app.models.shop import Shop
from app.models.medicine import Medicine
from app.models.inventory import Inventory
from app.models.audit_log import AuditLog, ActionType
from app.models.shop_staff import ShopStaff
from app.models.stock_transfer import StockTransferRequest, TransferStatus, TransferPriority
from app.models.demand_forecast import DemandForecast
from app.models.climate_alert import ClimateAlert, RiskLevel

# ── Public API ─────────────────────────────────────────────────
__all__ = [
    # Base
    "Base",
    # Models
    "User",
    "UserRole",
    "Salt",
    "Shop",
    "Medicine",
    "Inventory",
    "AuditLog",
    "ActionType",
    "ShopStaff",
    "StockTransferRequest",
    "TransferStatus",
    "TransferPriority",
    "DemandForecast",
    "ClimateAlert",
    "RiskLevel",
]
