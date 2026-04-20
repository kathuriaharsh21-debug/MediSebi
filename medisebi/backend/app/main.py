"""
MediSebi — Main FastAPI Application
=====================================
AI-Driven Healthcare Supply Intelligence & Redistribution Platform.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1 import api_router
from app.core.database import Base, get_engine, get_session_factory
from app.models.user import User

logger = logging.getLogger(__name__)


def _auto_seed_if_empty():
    """Seed the database with default data if no users exist.
    This is critical for Render free tier where the filesystem
    is ephemeral and gets wiped on every deploy/restart.
    """
    db = get_session_factory()()
    try:
        user_count = db.query(User).count()
        if user_count > 0:
            logger.info(f"Database has {user_count} user(s) — skipping seed.")
            return
        logger.info("No users found — running auto-seed...")
        from app.models.salt import Salt, ABCClass
        from app.models.medicine import Medicine
        from app.models.shop import Shop
        from app.models.inventory import Inventory
        from app.models.shop_staff import ShopStaff
        from app.auth.password import hash_password
        from datetime import date, datetime, timezone
        import uuid

        # 1. Users
        admin = User(
            username="admin", email="admin@medisebi.com",
            password_hash=hash_password("Admin@12345!"),
            full_name="System Administrator",
            role="admin", is_active=True, is_locked=False,
            failed_login_attempts=0,
            password_changed_at=datetime.now(timezone.utc),
            password_changed_by="self", must_change_password=False,
            mfa_enabled=False,
        )
        pharmacist = User(
            username="pharmacist1", email="pharm1@medisebi.com",
            password_hash=hash_password("Pharm@12345!"),
            full_name="Dr. Priya Sharma",
            role="pharmacist", is_active=True, is_locked=False,
            failed_login_attempts=0,
            password_changed_at=datetime.now(timezone.utc),
            password_changed_by="self", must_change_password=False,
            mfa_enabled=False,
        )
        db.add(admin); db.add(pharmacist)
        db.flush()

        # 2. Salts
        salts = [
            Salt(formula_name="Paracetamol", category="Analgesic", abc_class=ABCClass.A,
                 reorder_level=200, safety_stock=100, critical_threshold=50, warning_threshold=100,
                 description="Widely used analgesic and antipyretic.", dosage_form="Tablet",
                 standard_strength="500mg", unit_of_measure="tablets"),
            Salt(formula_name="Amoxicillin", category="Antibiotic", abc_class=ABCClass.A,
                 reorder_level=150, safety_stock=75, critical_threshold=30, warning_threshold=75,
                 description="Broad-spectrum beta-lactam antibiotic.", dosage_form="Capsule",
                 standard_strength="500mg", unit_of_measure="capsules"),
            Salt(formula_name="Oral Rehydration Salts", category="ORS", abc_class=ABCClass.B,
                 reorder_level=300, safety_stock=100, critical_threshold=50, warning_threshold=150,
                 description="WHO-formulated ORS for dehydration.", dosage_form="Powder",
                 standard_strength="21.8g sachet", unit_of_measure="sachets"),
            Salt(formula_name="Ibuprofen", category="Analgesic", abc_class=ABCClass.B,
                 reorder_level=100, safety_stock=50, critical_threshold=20, warning_threshold=50,
                 description="NSAID for pain, inflammation, fever.", dosage_form="Tablet",
                 standard_strength="400mg", unit_of_measure="tablets"),
        ]
        salt_map = {}
        for s in salts:
            db.add(s); db.flush()
            salt_map[s.formula_name] = s

        # 3. Medicines
        med_defs = [
            ("Crocin 500mg", "Paracetamol", "GSK", "500mg", "Tablet", 2.50, "CRC"),
            ("Calpol 500mg", "Paracetamol", "GSK", "500mg", "Tablet", 2.00, "CPL"),
            ("Dolo 650mg", "Paracetamol", "Micro Labs", "650mg", "Tablet", 3.00, "DLO"),
            ("Mox 500mg", "Amoxicillin", "Sun Pharma", "500mg", "Capsule", 8.50, "MOX"),
            ("Electral Powder", "Oral Rehydration Salts", "FDC Ltd", "21.8g", "Powder", 22.00, "ELC"),
            ("Brufen 400mg", "Ibuprofen", "Abbott", "400mg", "Tablet", 4.50, "BRF"),
        ]
        med_map = {}
        for brand, salt_name, mfr, strength, form, price, prefix in med_defs:
            m = Medicine(brand_name=brand, salt_id=salt_map[salt_name].id,
                        manufacturer=mfr, strength=strength, dosage_form=form,
                        unit_price=price, batch_prefix=prefix)
            db.add(m); db.flush()
            med_map[brand] = m

        # 4. Shops
        shop_defs = [
            ("MediSebi Central", "PH-CEN-001", "Mumbai", "Maharashtra",
             "123 Marine Drive, Fort, Mumbai 400001", "400001", 18.9434, 72.8235, 50000),
            ("MediSebi West", "PH-WST-002", "Mumbai", "Maharashtra",
             "456 Linking Road, Bandra, Mumbai 400050", "400050", 19.0596, 72.8295, 30000),
            ("MediSebi North", "PH-NRT-003", "Delhi", "Delhi NCR",
             "789 Connaught Place, New Delhi 110001", "110001", 28.6315, 77.2167, 40000),
        ]
        shop_map = {}
        for name, code, city, state, addr, pin, lat, lon, cap in shop_defs:
            s = Shop(name=name, code=code, city=city, state=state, address=addr,
                     pincode=pin, latitude=lat, longitude=lon, storage_capacity=cap)
            db.add(s); db.flush()
            shop_map[code] = s

        # 5. Inventory
        inv_data = [
            ("Crocin 500mg", "PH-CEN-001", 500, "CRC-2025-001", date(2026,6,30), 2.00, 2.50),
            ("Crocin 500mg", "PH-CEN-001", 150, "CRC-2025-002", date(2025,9,15), 2.00, 2.50),
            ("Calpol 500mg", "PH-CEN-001", 300, "CPL-2025-001", date(2026,3,20), 1.60, 2.00),
            ("Dolo 650mg", "PH-CEN-001", 250, "DLO-2025-001", date(2026,8,10), 2.40, 3.00),
            ("Mox 500mg", "PH-CEN-001", 80, "MOX-2025-001", date(2026,1,15), 6.80, 8.50),
            ("Electral Powder", "PH-CEN-001", 400, "ELC-2025-001", date(2027,5,30), 17.50, 22.00),
            ("Brufen 400mg", "PH-CEN-001", 120, "BRF-2025-001", date(2025,12,1), 3.60, 4.50),
            ("Crocin 500mg", "PH-WST-002", 30, "CRC-2025-003", date(2025,8,10), 2.00, 2.50),
            ("Calpol 500mg", "PH-WST-002", 200, "CPL-2025-002", date(2026,5,15), 1.60, 2.00),
            ("Dolo 650mg", "PH-WST-002", 450, "DLO-2025-002", date(2026,11,30), 2.40, 3.00),
            ("Mox 500mg", "PH-WST-002", 200, "MOX-2025-002", date(2026,4,20), 6.80, 8.50),
            ("Electral Powder", "PH-WST-002", 50, "ELC-2025-002", date(2025,10,5), 17.50, 22.00),
            ("Brufen 400mg", "PH-WST-002", 90, "BRF-2025-002", date(2026,2,28), 3.60, 4.50),
            ("Crocin 500mg", "PH-NRT-003", 350, "CRC-2025-004", date(2026,7,20), 2.00, 2.50),
            ("Calpol 500mg", "PH-NRT-003", 10, "CPL-2025-003", date(2025,7,30), 1.60, 2.00),
            ("Dolo 650mg", "PH-NRT-003", 180, "DLO-2025-003", date(2026,9,15), 2.40, 3.00),
            ("Mox 500mg", "PH-NRT-003", 25, "MOX-2025-003", date(2026,2,10), 6.80, 8.50),
            ("Electral Powder", "PH-NRT-003", 250, "ELC-2025-003", date(2027,1,10), 17.50, 22.00),
            ("Brufen 400mg", "PH-NRT-003", 60, "BRF-2025-003", date(2025,11,15), 3.60, 4.50),
        ]
        for med_name, shop_code, qty, batch, exp, cost, sell in inv_data:
            inv = Inventory(
                med_id=med_map[med_name].id, shop_id=shop_map[shop_code].id,
                quantity=qty, batch_number=batch, expiry_date=exp,
                cost_price=cost, selling_price=sell, storage_location="Shelf-A1",
            )
            db.add(inv)

        # 6. Shop-Staff assignments
        for shop_code in ["PH-CEN-001", "PH-WST-002", "PH-NRT-003"]:
            ss = ShopStaff(user_id=pharmacist.id, shop_id=shop_map[shop_code].id,
                          assigned_date=date.today(), is_primary=(shop_code=="PH-CEN-001"))
            db.add(ss)

        db.commit()
        logger.info("Auto-seed complete: 2 users, 4 salts, 6 medicines, 3 shops, 19 inventory items")
    except Exception as e:
        db.rollback()
        logger.error(f"Auto-seed failed: {e}")
        raise
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables and auto-seed if empty."""
    Base.metadata.create_all(bind=get_engine())
    _auto_seed_if_empty()
    yield


def create_application() -> FastAPI:
    """
    Application factory with all middleware and routers configured.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Parse CORS origins from comma-separated string
    cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Router ───────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ── Health Check ─────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    # ── Global Exception Handlers ────────────────────────────
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return JSONResponse(
            status_code=404,
            content={"detail": "Resource not found", "path": str(request.url)},
        )

    return app


app = create_application()
