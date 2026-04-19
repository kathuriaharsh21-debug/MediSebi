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
from app.models.salt import Salt, ABCClass
from app.models.shop import Shop
from app.models.medicine import Medicine
from app.models.inventory import Inventory
from app.models.audit_log import AuditLog, ActionType
from app.models.shop_staff import ShopStaff
from app.models.stock_transfer import StockTransferRequest, TransferStatus, TransferPriority
from app.models.demand_forecast import DemandForecast
from app.models.climate_alert import ClimateAlert, RiskLevel
from app.models.refresh_token import RefreshToken
from app.models.password_history import PasswordHistory
from app.models.notification import Notification, NotificationSeverity, NotificationSource
from app.models.bill import Bill, BillItem, PaymentMethod, BillStatus

# ── Public API ─────────────────────────────────────────────────
__all__ = [
    # Base
    "Base",
    # Core Models
    "User",
    "UserRole",
    "Salt",
    "ABCClass",
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
    # Security Models (Post-Research)
    "RefreshToken",
    "PasswordHistory",
    "Notification",
    "NotificationSeverity",
    "NotificationSource",
    # Billing Models
    "Bill",
    "BillItem",
    "PaymentMethod",
    "BillStatus",
]
