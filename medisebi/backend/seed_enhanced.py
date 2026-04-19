"""
MediSebi — Enhanced Database Seed Script
==========================================
Comprehensive seed data for development, testing, and AI feature validation.

Creates:
  - 2 Users (admin + pharmacist) with bcrypt-hashed passwords
  - 20+ Salts (unique active pharmaceutical ingredients from catalog)
  - 35 Medicines (diverse brands across all therapeutic categories)
  - 8 Shops (pharmacies across 5 Indian cities from DEMO_STORES)
  - 120+ Inventory entries with:
      * Varied expiry dates (expired, 7-day, 30-day, safe 6+ months)
      * Varied quantities (excess, adequate, low, critical, deficit)
      * Redistribution-ready (excess in some shops, deficit in others)
  - 16 Shop-Staff assignments (both users assigned across all shops)

Drops and recreates all tables from scratch — use with caution!

Usage:
    cd /home/z/my-project/medisebi/backend
    python seed_enhanced.py
"""

import sys
import os
import random
from datetime import date, datetime, timedelta, timezone

# ── Ensure the backend directory is on sys.path ──────────────────
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import bcrypt
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_engine
from app.models import (
    User, UserRole,
    Salt, ABCClass,
    Medicine,
    Shop,
    Inventory,
    ShopStaff,
)
from app.core.medicine_catalog import MEDICINE_CATALOG, DEMO_STORES

# ── Database Setup (uses same engine as the app) ─────────────────
engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ── Reproducible randomness ──────────────────────────────────────
random.seed(42)

# ── Reference date for expiry calculations ───────────────────────
TODAY = date.today()

# ──────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt with 12 rounds."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def expiry_offset(days: int) -> date:
    """Return a date `days` from today."""
    return TODAY + timedelta(days=days)


def random_expiry_bucket() -> date:
    """Return a random expiry date in one of four buckets."""
    bucket = random.choices(
        ["expired", "7day", "30day", "safe"],
        weights=[10, 15, 15, 60],  # ~60% safe stock
        k=1,
    )[0]
    if bucket == "expired":
        return expiry_offset(-random.randint(10, 200))
    elif bucket == "7day":
        return expiry_offset(random.randint(1, 7))
    elif bucket == "30day":
        return expiry_offset(random.randint(8, 30))
    else:
        return expiry_offset(random.randint(180, 730))


# ──────────────────────────────────────────────────────────────────
# DATA SELECTION FROM CATALOG
# ──────────────────────────────────────────────────────────────────

# 35 medicines selected for broad category coverage
SELECTED_MEDICINE_NAMES = [
    # Analgesics & Antipyretics (7)
    "Dolo 650",
    "Crocin Advance",
    "Calpol 500",
    "Combiflam",
    "Brufen 400",
    "Voveran 50",
    "Nise 100",
    # Antibiotics (5)
    "Augmentin 625",
    "Mox 500",
    "Azithral 500",
    "Ciplox 500",
    "Doxy 100",
    # Anti-allergic (2)
    "Cetzine",
    "Allegra 120",
    # Cough & Cold (2)
    "Benadryl",
    "Vicks Action 500",
    # Gastrointestinal + ORS (4)
    "Pan 40",
    "Imodium",
    "ORS Electral",
    "Econorm",
    # Vitamins & Supplements (4)
    "Limcee",
    "Shelcal 500",
    "Becosules",
    "Zincovit",
    # Antidiabetic (3)
    "Glycomet 500",
    "Glimepiride 2",
    "Human Mixtard 30/70",
    # Antihypertensive (3)
    "Telma 40",
    "Amlong 5",
    "Atorva 10",
    # Dermatology (3)
    "Betadine",
    "Candid-B",
    "Soframycin",
    # Ophthalmology (1)
    "Refresh Tears",
    # Anti-inflammatory (1)
    "Etorica 90",
    # Antispasmodic (1)
    "Cyclopam",
    # Antiemetic (1)
    "Emset 4",
]

# Build lookup: brand_name → catalog entry
CATALOG_MAP = {m["brand_name"]: m for m in MEDICINE_CATALOG}

# Extract unique salts from selected medicines
SELECTED_CATALOG = [CATALOG_MAP[name] for name in SELECTED_MEDICINE_NAMES]

UNIQUE_SALTS = {}
for med in SELECTED_CATALOG:
    sn = med["salt_name"]
    if sn not in UNIQUE_SALTS:
        UNIQUE_SALTS[sn] = {
            "formula_name": sn,
            "category": med["category"],
            "abc_class": med["abc_class"],
            "reorder_level": med["reorder"],
            "safety_stock": med["safety_stock"],
            "critical_threshold": med["critical"],
            "warning_threshold": int(med["reorder"] * 0.75),
            "dosage_form": med["form"],
            "standard_strength": med["strength"],
            "unit_of_measure": "units",
        }


# ──────────────────────────────────────────────────────────────────
# INVENTORY DISTRIBUTION STRATEGY
# ──────────────────────────────────────────────────────────────────
# Each medicine is assigned to 3-4 shops with intentional quantity
# variation to enable redistribution engine testing:
#   - excess:  300-600 units (well above reorder level)
#   - adequate: 100-250 units (above reorder level)
#   - low:      20-80 units (below reorder, above critical)
#   - critical: 5-15 units (near/below critical threshold)
#   - deficit:  0-3 units (essentially out of stock)
#
# For key medicines, some shops have excess while others have deficit,
# creating clear redistribution opportunities.

SHOP_CODES = [s["code"] for s in DEMO_STORES]

# (quantity_range, expiry_pattern) tuples
QTY_EXCESS   = (300, 600)
QTY_ADEQUATE = (100, 250)
QTY_LOW      = (20, 80)
QTY_CRITICAL = (5, 15)
QTY_DEFICIT  = (0, 3)


def build_inventory_plan():
    """
    Build a structured inventory distribution plan.
    Returns list of dicts: {brand_name, shop_code, qty_min, qty_max, expiry_bucket, shelf}
    """
    plan = []

    # Define shelf zones per shop
    shelf_zones = ["Shelf-A1", "Shelf-A2", "Shelf-B1", "Shelf-B2", "Shelf-C1", "Shelf-C2", "Fridge-01", "Fridge-02"]

    def add_entries(brand_name, shop_assignments):
        """
        shop_assignments: list of (shop_code, qty_range, expiry_bucket)
        expiry_bucket: "expired" | "7day" | "30day" | "safe" | "random"
        """
        for shop_code, qty_range, expiry_bucket in shop_assignments:
            shelf = random.choice(shelf_zones)
            # For cold-sensitive items, prefer fridge shelves
            med_entry = CATALOG_MAP.get(brand_name, {})
            if med_entry.get("temp_sensitive"):
                shelf = random.choice(["Fridge-01", "Fridge-02"])
            plan.append({
                "brand_name": brand_name,
                "shop_code": shop_code,
                "qty_min": qty_range[0],
                "qty_max": qty_range[1],
                "expiry_bucket": expiry_bucket,
                "shelf": shelf,
            })

    # ── HIGH-TURNOVER ANALGESICS (6+ shops each for redistribution) ──
    add_entries("Dolo 650", [
        ("PH-CEN-001", QTY_EXCESS, "safe"),
        ("PH-WST-002", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_DEFICIT, "30day"),
        ("PH-STH-004", QTY_EXCESS, "safe"),
        ("PH-KOR-005", QTY_LOW, "7day"),
        ("PH-TNG-007", QTY_CRITICAL, "safe"),
        ("PH-SLK-008", QTY_ADEQUATE, "expired"),
    ])
    add_entries("Crocin Advance", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-WST-002", QTY_EXCESS, "safe"),
        ("PH-NRT-003", QTY_EXCESS, "safe"),
        ("PH-STH-004", QTY_LOW, "30day"),
        ("PH-KOR-005", QTY_DEFICIT, "7day"),
        ("PH-WHT-006", QTY_ADEQUATE, "safe"),
        ("PH-TNG-007", QTY_LOW, "expired"),
    ])
    add_entries("Combiflam", [
        ("PH-CEN-001", QTY_EXCESS, "safe"),
        ("PH-NRT-003", QTY_ADEQUATE, "safe"),
        ("PH-SLK-008", QTY_DEFICIT, "expired"),
        ("PH-TNG-007", QTY_LOW, "30day"),
    ])
    add_entries("Calpol 500", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-WST-002", QTY_LOW, "7day"),
        ("PH-KOR-005", QTY_EXCESS, "safe"),
        ("PH-WHT-006", QTY_CRITICAL, "30day"),
        ("PH-SLK-008", QTY_DEFICIT, "7day"),
    ])

    # ── OTHER ANALGESICS ──
    add_entries("Brufen 400", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-WST-002", QTY_LOW, "expired"),
        ("PH-NRT-003", QTY_EXCESS, "safe"),
        ("PH-KOR-005", QTY_DEFICIT, "30day"),
    ])
    add_entries("Voveran 50", [
        ("PH-WST-002", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_LOW, "7day"),
        ("PH-TNG-007", QTY_EXCESS, "safe"),
        ("PH-SLK-008", QTY_DEFICIT, "safe"),
    ])
    add_entries("Nise 100", [
        ("PH-CEN-001", QTY_LOW, "safe"),
        ("PH-STH-004", QTY_EXCESS, "safe"),
        ("PH-WHT-006", QTY_ADEQUATE, "30day"),
        ("PH-TNG-007", QTY_DEFICIT, "expired"),
    ])

    # ── ANTIBIOTICS (controlled, lower quantities) ──
    add_entries("Augmentin 625", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-WST-002", QTY_LOW, "safe"),
        ("PH-NRT-003", QTY_DEFICIT, "7day"),
        ("PH-KOR-005", QTY_EXCESS, "safe"),
        ("PH-SLK-008", QTY_LOW, "30day"),
    ])
    add_entries("Mox 500", [
        ("PH-CEN-001", QTY_LOW, "safe"),
        ("PH-WST-002", QTY_EXCESS, "safe"),
        ("PH-NRT-003", QTY_ADEQUATE, "30day"),
        ("PH-TNG-007", QTY_DEFICIT, "expired"),
    ])
    add_entries("Azithral 500", [
        ("PH-CEN-001", QTY_EXCESS, "safe"),
        ("PH-STH-004", QTY_LOW, "7day"),
        ("PH-KOR-005", QTY_ADEQUATE, "safe"),
        ("PH-WHT-006", QTY_DEFICIT, "safe"),
    ])
    add_entries("Ciplox 500", [
        ("PH-WST-002", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_EXCESS, "safe"),
        ("PH-TNG-007", QTY_LOW, "30day"),
        ("PH-SLK-008", QTY_DEFICIT, "expired"),
    ])
    add_entries("Doxy 100", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_LOW, "7day"),
        ("PH-WHT-006", QTY_EXCESS, "safe"),
    ])

    # ── ANTI-ALLERGIC ──
    add_entries("Cetzine", [
        ("PH-CEN-001", QTY_EXCESS, "safe"),
        ("PH-WST-002", QTY_ADEQUATE, "safe"),
        ("PH-KOR-005", QTY_LOW, "30day"),
        ("PH-TNG-007", QTY_DEFICIT, "safe"),
    ])
    add_entries("Allegra 120", [
        ("PH-NRT-003", QTY_EXCESS, "safe"),
        ("PH-STH-004", QTY_LOW, "7day"),
        ("PH-KOR-005", QTY_ADEQUATE, "safe"),
        ("PH-WHT-006", QTY_DEFICIT, "safe"),
    ])

    # ── COUGH & COLD ──
    add_entries("Benadryl", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_EXCESS, "safe"),
        ("PH-TNG-007", QTY_LOW, "expired"),
        ("PH-SLK-008", QTY_DEFICIT, "30day"),
    ])
    add_entries("Vicks Action 500", [
        ("PH-WST-002", QTY_EXCESS, "safe"),
        ("PH-NRT-003", QTY_ADEQUATE, "safe"),
        ("PH-KOR-005", QTY_LOW, "7day"),
        ("PH-WHT-006", QTY_DEFICIT, "safe"),
    ])

    # ── GASTROINTESTINAL + ORS ──
    add_entries("Pan 40", [
        ("PH-CEN-001", QTY_EXCESS, "safe"),
        ("PH-WST-002", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_LOW, "30day"),
        ("PH-STH-004", QTY_DEFICIT, "7day"),
        ("PH-KOR-005", QTY_EXCESS, "safe"),
        ("PH-TNG-007", QTY_CRITICAL, "expired"),
    ])
    add_entries("Imodium", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-WST-002", QTY_LOW, "expired"),
        ("PH-SLK-008", QTY_EXCESS, "safe"),
        ("PH-TNG-007", QTY_DEFICIT, "30day"),
    ])
    add_entries("ORS Electral", [
        ("PH-CEN-001", QTY_EXCESS, "safe"),
        ("PH-WST-002", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_EXCESS, "safe"),
        ("PH-KOR-005", QTY_LOW, "7day"),
        ("PH-WHT-006", QTY_DEFICIT, "safe"),
        ("PH-TNG-007", QTY_CRITICAL, "expired"),
        ("PH-SLK-008", QTY_ADEQUATE, "safe"),
    ])
    add_entries("Econorm", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_LOW, "7day"),
        ("PH-KOR-005", QTY_DEFICIT, "safe"),
    ])

    # ── VITAMINS & SUPPLEMENTS ──
    add_entries("Limcee", [
        ("PH-CEN-001", QTY_EXCESS, "safe"),
        ("PH-WST-002", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_LOW, "safe"),
        ("PH-TNG-007", QTY_DEFICIT, "expired"),
    ])
    add_entries("Shelcal 500", [
        ("PH-WST-002", QTY_EXCESS, "safe"),
        ("PH-NRT-003", QTY_ADEQUATE, "safe"),
        ("PH-KOR-005", QTY_LOW, "30day"),
        ("PH-SLK-008", QTY_DEFICIT, "safe"),
    ])
    add_entries("Becosules", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-STH-004", QTY_EXCESS, "safe"),
        ("PH-WHT-006", QTY_LOW, "7day"),
        ("PH-TNG-007", QTY_DEFICIT, "safe"),
    ])
    add_entries("Zincovit", [
        ("PH-NRT-003", QTY_EXCESS, "safe"),
        ("PH-KOR-005", QTY_ADEQUATE, "safe"),
        ("PH-WHT-006", QTY_DEFICIT, "30day"),
    ])

    # ── ANTIDIABETIC ──
    add_entries("Glycomet 500", [
        ("PH-CEN-001", QTY_EXCESS, "safe"),
        ("PH-NRT-003", QTY_ADEQUATE, "safe"),
        ("PH-KOR-005", QTY_LOW, "safe"),
        ("PH-TNG-007", QTY_DEFICIT, "7day"),
        ("PH-SLK-008", QTY_ADEQUATE, "safe"),
    ])
    add_entries("Glimepiride 2", [
        ("PH-WST-002", QTY_EXCESS, "safe"),
        ("PH-STH-004", QTY_LOW, "30day"),
        ("PH-WHT-006", QTY_ADEQUATE, "safe"),
        ("PH-SLK-008", QTY_DEFICIT, "safe"),
    ])
    add_entries("Human Mixtard 30/70", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_CRITICAL, "7day"),
        ("PH-KOR-005", QTY_LOW, "safe"),
        ("PH-TNG-007", QTY_DEFICIT, "safe"),
    ])

    # ── ANTIHYPERTENSIVE ──
    add_entries("Telma 40", [
        ("PH-CEN-001", QTY_EXCESS, "safe"),
        ("PH-WST-002", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_LOW, "30day"),
        ("PH-KOR-005", QTY_EXCESS, "safe"),
        ("PH-SLK-008", QTY_DEFICIT, "expired"),
    ])
    add_entries("Amlong 5", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-STH-004", QTY_EXCESS, "safe"),
        ("PH-TNG-007", QTY_LOW, "7day"),
        ("PH-WHT-006", QTY_DEFICIT, "safe"),
    ])
    add_entries("Atorva 10", [
        ("PH-WST-002", QTY_EXCESS, "safe"),
        ("PH-NRT-003", QTY_ADEQUATE, "safe"),
        ("PH-WHT-006", QTY_LOW, "30day"),
        ("PH-SLK-008", QTY_DEFICIT, "safe"),
    ])

    # ── DERMATOLOGY ──
    add_entries("Betadine", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-WST-002", QTY_LOW, "expired"),
        ("PH-KOR-005", QTY_EXCESS, "safe"),
        ("PH-TNG-007", QTY_DEFICIT, "safe"),
    ])
    add_entries("Candid-B", [
        ("PH-NRT-003", QTY_EXCESS, "safe"),
        ("PH-STH-004", QTY_ADEQUATE, "safe"),
        ("PH-WHT-006", QTY_LOW, "30day"),
        ("PH-SLK-008", QTY_DEFICIT, "safe"),
    ])
    add_entries("Soframycin", [
        ("PH-CEN-001", QTY_LOW, "7day"),
        ("PH-WST-002", QTY_EXCESS, "safe"),
        ("PH-TNG-007", QTY_ADEQUATE, "safe"),
    ])

    # ── OPHTHALMOLOGY ──
    add_entries("Refresh Tears", [
        ("PH-CEN-001", QTY_EXCESS, "safe"),
        ("PH-NRT-003", QTY_ADEQUATE, "safe"),
        ("PH-KOR-005", QTY_LOW, "30day"),
        ("PH-TNG-007", QTY_DEFICIT, "safe"),
    ])

    # ── ANTI-INFLAMMATORY ──
    add_entries("Etorica 90", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-WST-002", QTY_EXCESS, "safe"),
        ("PH-NRT-003", QTY_DEFICIT, "7day"),
        ("PH-SLK-008", QTY_LOW, "safe"),
    ])

    # ── ANTISPASMODIC ──
    add_entries("Cyclopam", [
        ("PH-CEN-001", QTY_ADEQUATE, "safe"),
        ("PH-NRT-003", QTY_LOW, "30day"),
        ("PH-KOR-005", QTY_EXCESS, "safe"),
        ("PH-WHT-006", QTY_DEFICIT, "safe"),
    ])

    # ── ANTIEMETIC ──
    add_entries("Emset 4", [
        ("PH-WST-002", QTY_EXCESS, "safe"),
        ("PH-NRT-003", QTY_ADEQUATE, "safe"),
        ("PH-TNG-007", QTY_LOW, "expired"),
        ("PH-SLK-008", QTY_DEFICIT, "7day"),
    ])

    return plan


# ──────────────────────────────────────────────────────────────────
# MAIN SEED FUNCTION
# ──────────────────────────────────────────────────────────────────

def seed_database() -> None:
    """Seed the database with comprehensive sample data."""

    # ── Step 0: Drop all existing tables and recreate ──────────
    print("=" * 65)
    print("  MediSebi Enhanced Seed — Dropping & Recreating All Tables")
    print("=" * 65)
    Base.metadata.drop_all(bind=engine)
    print("  [DROP]  All existing tables dropped")
    Base.metadata.create_all(bind=engine)
    print("  [CREATE] All tables recreated from models\n")

    db = SessionLocal()

    try:
        # ────────────────────────────────────────────────────────
        # 1. USERS (2)
        # ────────────────────────────────────────────────────────
        print("─── 1. USERS ────────────────────────────────────")

        admin_password = hash_password("Admin@12345!")
        pharmacist_password = hash_password("Pharm@12345!")

        admin_user = User(
            username="admin",
            email="admin@medisebi.com",
            password_hash=admin_password,
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_locked=False,
            failed_login_attempts=0,
            password_changed_at=datetime.now(timezone.utc),
            password_changed_by="self",
            must_change_password=False,
            mfa_enabled=False,
        )
        pharmacist_user = User(
            username="pharmacist",
            email="pharmacist@medisebi.com",
            password_hash=pharmacist_password,
            full_name="Dr. Priya Sharma",
            role=UserRole.PHARMACIST,
            is_locked=False,
            failed_login_attempts=0,
            password_changed_at=datetime.now(timezone.utc),
            password_changed_by="self",
            must_change_password=False,
            mfa_enabled=False,
        )
        db.add(admin_user)
        db.add(pharmacist_user)
        db.flush()
        print(f"  + admin       (id={admin_user.id}, role=ADMIN)")
        print(f"  + pharmacist  (id={pharmacist_user.id}, role=PHARMACIST)")

        # ────────────────────────────────────────────────────────
        # 2. SHOPS (8 from DEMO_STORES)
        # ────────────────────────────────────────────────────────
        print("\n─── 2. SHOPS ───────────────────────────────────")

        shop_objects = {}
        for sd in DEMO_STORES:
            shop = Shop(
                name=sd["name"],
                code=sd["code"],
                city=sd["city"],
                state=sd["state"],
                address=sd["address"],
                pincode=sd["pincode"],
                latitude=sd["lat"],
                longitude=sd["lon"],
                contact_phone=sd["phone"],
                contact_email=sd["email"],
                storage_capacity=sd["capacity"],
            )
            db.add(shop)
            db.flush()
            shop_objects[sd["code"]] = shop
            print(f"  + {shop.name:30s} ({shop.code}) — {shop.city}, {shop.state}")

        # ────────────────────────────────────────────────────────
        # 3. SALTS (20+ unique from catalog)
        # ────────────────────────────────────────────────────────
        print("\n─── 3. SALTS ───────────────────────────────────")

        abc_map = {"A": ABCClass.A, "B": ABCClass.B, "C": ABCClass.C}
        salt_objects = {}
        for sn, sd in UNIQUE_SALTS.items():
            salt = Salt(
                formula_name=sd["formula_name"],
                category=sd["category"],
                abc_class=abc_map[sd["abc_class"]],
                reorder_level=sd["reorder_level"],
                safety_stock=sd["safety_stock"],
                critical_threshold=sd["critical_threshold"],
                warning_threshold=sd["warning_threshold"],
                dosage_form=sd["dosage_form"],
                standard_strength=sd["standard_strength"],
                unit_of_measure=sd["unit_of_measure"],
                description=f"{sd['formula_name']} — therapeutic category: {sd['category']}",
            )
            db.add(salt)
            db.flush()
            salt_objects[sd["formula_name"]] = salt

        salt_names = sorted(salt_objects.keys())
        print(f"  + {len(salt_objects)} salts created:")
        for sn in salt_names:
            s = salt_objects[sn]
            print(f"    - {sn:50s} [{s.abc_class.value}] reorder={s.reorder_level} critical={s.critical_threshold}")

        # ────────────────────────────────────────────────────────
        # 4. MEDICINES (35 from catalog)
        # ────────────────────────────────────────────────────────
        print("\n─── 4. MEDICINES ───────────────────────────────")

        medicine_objects = {}
        for med_cat in SELECTED_CATALOG:
            salt_key = med_cat["salt_name"]
            # Generate a batch prefix from brand initials
            brand_initials = "".join(w[0] for w in med_cat["brand_name"].split()[:2]).upper()[:5]
            medicine = Medicine(
                brand_name=med_cat["brand_name"],
                salt_id=salt_objects[salt_key].id,
                manufacturer=med_cat["manufacturer"],
                strength=med_cat["strength"],
                dosage_form=med_cat["form"],
                unit_price=med_cat["price"],
                temperature_sensitive=med_cat["temp_sensitive"],
                batch_prefix=brand_initials,
            )
            db.add(medicine)
            db.flush()
            medicine_objects[med_cat["brand_name"]] = medicine

        print(f"  + {len(medicine_objects)} medicines created:")
        for name, med in medicine_objects.items():
            salt_name = med.salt.formula_name if med.salt else "?"
            print(f"    - {name:30s} → {salt_name}")

        # ────────────────────────────────────────────────────────
        # 5. INVENTORY (120+ entries with strategic distribution)
        # ────────────────────────────────────────────────────────
        print("\n─── 5. INVENTORY ───────────────────────────────")

        inventory_plan = build_inventory_plan()
        inv_count = 0
        expired_count = 0
        near_expiry_count = 0  # within 30 days
        safe_count = 0

        for entry in inventory_plan:
            med = medicine_objects[entry["brand_name"]]
            shop = shop_objects[entry["shop_code"]]

            # Determine expiry date based on bucket
            bucket = entry["expiry_bucket"]
            if bucket == "expired":
                exp = expiry_offset(-random.randint(10, 200))
            elif bucket == "7day":
                exp = expiry_offset(random.randint(1, 7))
            elif bucket == "30day":
                exp = expiry_offset(random.randint(8, 30))
            elif bucket == "safe":
                exp = expiry_offset(random.randint(180, 730))
            else:  # "random"
                exp = random_expiry_bucket()

            # Classify expiry status
            days_to_exp = (exp - TODAY).days
            if days_to_exp < 0:
                expired_count += 1
            elif days_to_exp <= 30:
                near_expiry_count += 1
            else:
                safe_count += 1

            # Generate batch number
            bp = med.batch_prefix or "GEN"
            batch_num = f"{bp}-{TODAY.year}-{random.randint(100,999)}"

            # Determine prices (cost ~70-80% of sell)
            unit_sell = med.unit_price or 10.0
            unit_cost = round(unit_sell * random.uniform(0.65, 0.80), 2)

            qty = random.randint(entry["qty_min"], entry["qty_max"])

            item = Inventory(
                med_id=med.id,
                shop_id=shop.id,
                quantity=qty,
                batch_number=batch_num,
                expiry_date=exp,
                cost_price=unit_cost,
                selling_price=unit_sell,
                storage_location=entry["shelf"],
            )
            db.add(item)
            inv_count += 1

        db.flush()

        # Compute some redistribution stats
        deficit_items = sum(1 for e in inventory_plan if e["qty_max"] <= 3)
        excess_items = sum(1 for e in inventory_plan if e["qty_min"] >= 300)

        print(f"  + {inv_count} inventory entries created")
        print(f"    - Expired:        {expired_count:>4d} (past due)")
        print(f"    - Near expiry:    {near_expiry_count:>4d} (within 30 days)")
        print(f"    - Safe stock:     {safe_count:>4d} (6+ months)")
        print(f"    - Deficit stock:  {deficit_items:>4d} entries (0-3 units, redistribution targets)")
        print(f"    - Excess stock:   {excess_items:>4d} entries (300+, redistribution sources)")

        # ────────────────────────────────────────────────────────
        # 6. SHOP-STAFF ASSIGNMENTS
        # ────────────────────────────────────────────────────────
        print("\n─── 6. SHOP-STAFF ASSIGNMENTS ──────────────────")

        assignments = []

        # Admin assigned to all 8 shops
        for i, sd in enumerate(DEMO_STORES):
            assignments.append({
                "user_id": admin_user.id,
                "shop_code": sd["code"],
                "is_primary": (i == 0),  # Primary at Central
            })

        # Pharmacist assigned to all 8 shops (primary at Koramangala)
        for i, sd in enumerate(DEMO_STORES):
            is_primary = (sd["code"] == "PH-KOR-005")
            assignments.append({
                "user_id": pharmacist_user.id,
                "shop_code": sd["code"],
                "is_primary": is_primary,
            })

        for asgn in assignments:
            shop_staff = ShopStaff(
                user_id=asgn["user_id"],
                shop_id=shop_objects[asgn["shop_code"]].id,
                assigned_date=date.today(),
                is_primary=asgn["is_primary"],
            )
            db.add(shop_staff)

        db.flush()
        admin_assignments = sum(1 for a in assignments if a["user_id"] == admin_user.id)
        pharm_assignments = sum(1 for a in assignments if a["user_id"] == pharmacist_user.id)
        print(f"  + {len(assignments)} assignments created:")
        print(f"    - admin       → {admin_assignments} shops (primary: Central)")
        print(f"    - pharmacist  → {pharm_assignments} shops (primary: Koramangala)")

        # ────────────────────────────────────────────────────────
        # COMMIT
        # ────────────────────────────────────────────────────────
        db.commit()

        # ────────────────────────────────────────────────────────
        # FINAL SUMMARY
        # ────────────────────────────────────────────────────────
        print("\n" + "=" * 65)
        print("  MediSebi Enhanced Database Seeded Successfully!")
        print("=" * 65)
        print(f"""
  SEED SUMMARY
  ──────────────────────────────────────────────────────────
  Users:           2   (admin, pharmacist)
  Salts:           {len(salt_objects):>3d} ({len(salt_names)} unique APIs from catalog)
  Medicines:       {len(medicine_objects):>3d} (diverse brands across {len(set(c['category'] for c in SELECTED_CATALOG))} categories)
  Shops:           8   (Mumbai, Delhi, Bangalore, Chennai, Kolkata)
  Inventory:       {inv_count:>3d} entries across 8 shops
    Expired:       {expired_count:>3d} items (for expiry watchdog testing)
    Near-expiry:   {near_expiry_count:>3d} items (7-30 days, alert testing)
    Safe:          {safe_count:>3d} items (6+ months, normal operations)
    Deficit:       {deficit_items:>3d} items (redistribution demand targets)
    Excess:        {excess_items:>3d} items (redistribution supply sources)
  Shop-Staff:      {len(assignments):>3d} assignments (both users → all shops)

  TEST CREDENTIALS
  ──────────────────────────────────────────────────────────
  Admin:       admin@medisebi.com       /  Admin@12345!
  Pharmacist:  pharmacist@medisebi.com  /  Pharm@12345!

  SHOP NETWORK
  ──────────────────────────────────────────────────────────
  Mumbai:      PH-CEN-001 (Central), PH-WST-002 (West)
  Delhi:       PH-NRT-003 (North), PH-STH-004 (South)
  Bangalore:   PH-KOR-005 (Koramangala), PH-WHT-006 (Whitefield)
  Chennai:     PH-TNG-007 (T. Nagar)
  Kolkata:     PH-SLK-008 (Salt Lake)
""")

    except Exception as e:
        db.rollback()
        print(f"\n  [ERROR] Seed failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
