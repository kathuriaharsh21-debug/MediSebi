"""
MediSebi — Enhanced Database Seed Script
==========================================
Creates a realistic demo dataset with:
  - 5 Users (admin + 4 pharmacists across cities)
  - 40+ Salts (unique APIs from the medicine catalog)
  - 55 Medicines (brand-name products from MEDICINE_CATALOG)
  - 8 Shops (pharmacies across Mumbai, Delhi, Bangalore, Chennai, Kolkata)
  - 250+ Inventory entries (realistic stock levels with variety)
  - Shop-Staff assignments linking pharmacists to their cities

Features:
  - Idempotent: safe to run multiple times (checks for duplicates)
  - Deterministic: uses per-city random seeds for reproducible results
  - Realistic: includes expired items, low-stock items, and varied expiry dates
"""

import sys
import os
import random
import hashlib
from datetime import date, datetime, timezone, timedelta

# ── Ensure the backend directory is on sys.path ──────────────────
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_engine
from app.models.user import User, UserRole
from app.models.salt import Salt, ABCClass
from app.models.medicine import Medicine
from app.models.shop import Shop
from app.models.inventory import Inventory
from app.models.shop_staff import ShopStaff
from app.core.medicine_catalog import MEDICINE_CATALOG, DEMO_STORES

# ── Database Setup (uses same engine as the app) ─────────────────
engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with 12 rounds."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


# ── Constants ─────────────────────────────────────────────────────
ABC_CLASS_MAP = {
    "A": ABCClass.A,
    "B": ABCClass.B,
    "C": ABCClass.C,
}

# Shop classification: central shops get higher stock
CENTRAL_CODES = {"PH-CEN-001", "PH-WST-002", "PH-NRT-003", "PH-STH-004", "PH-KOR-005"}
PERIPHERAL_CODES = {"PH-WHT-006", "PH-TNG-007", "PH-SLK-008"}

# City → pharmacist mapping
CITY_PHARMACIST_MAP = {
    "Mumbai": "pharmacist1",
    "Delhi": "pharmacist2",
    "Bangalore": "pharmacist3",
}

# Chennai + Kolkata share pharmacist4
EXTRA_CITY_PHARMACIST_MAP = {
    "Chennai": "pharmacist4",
    "Kolkata": "pharmacist4",
}

# Seed data for users
USERS_DATA = [
    {
        "username": "admin",
        "email": "admin@medisebi.com",
        "password": "Admin@12345!",
        "full_name": "System Administrator",
        "role": UserRole.ADMIN,
    },
    {
        "username": "pharmacist1",
        "email": "pharmacist1@medisebi.com",
        "password": "Pharm@12345!",
        "full_name": "Dr. Priya Sharma",
        "role": UserRole.PHARMACIST,
    },
    {
        "username": "pharmacist2",
        "email": "pharmacist2@medisebi.com",
        "password": "Pharm2@12345!",
        "full_name": "Dr. Rajesh Gupta",
        "role": UserRole.PHARMACIST,
    },
    {
        "username": "pharmacist3",
        "email": "pharmacist3@medisebi.com",
        "password": "Pharm3@12345!",
        "full_name": "Dr. Anitha Reddy",
        "role": UserRole.PHARMACIST,
    },
    {
        "username": "pharmacist4",
        "email": "pharmacist4@medisebi.com",
        "password": "Pharm4@12345!",
        "full_name": "Dr. Suresh Menon",
        "role": UserRole.PHARMACIST,
    },
]


def derive_batch_prefix(brand_name: str, manufacturer: str) -> str:
    """Derive a short batch prefix from brand name + manufacturer."""
    # Take first 3 alpha chars from brand name, uppercase
    chars = [c.upper() for c in brand_name if c.isalpha()]
    prefix = "".join(chars[:3])
    # Pad to 3 chars if needed
    while len(prefix) < 3:
        prefix += "X"
    return prefix[:3]


def generate_batch_number(prefix: str, seed_val: int, year: int = 2025) -> str:
    """Generate a deterministic batch number."""
    batch_id = (seed_val % 999) + 1
    return f"{prefix}-{year}-{batch_id:03d}"


def random_expiry_date(rng: random.Random, min_date: date = None, max_date: date = None) -> date:
    """Generate a random expiry date between min_date and max_date."""
    if min_date is None:
        min_date = date(2025, 6, 1)
    if max_date is None:
        max_date = date(2027, 12, 31)

    days_range = (max_date - min_date).days
    random_days = rng.randint(0, days_range)
    return min_date + timedelta(days=random_days)


def seed_database() -> None:
    """Seed the database with enhanced sample data."""
    # ── Create all tables if they don't exist ──────────────────
    Base.metadata.create_all(bind=engine)
    print("✓ Tables ensured via Base.metadata.create_all()")

    db = SessionLocal()

    try:
        counters = {
            "users_created": 0,
            "users_existing": 0,
            "salts_created": 0,
            "salts_existing": 0,
            "medicines_created": 0,
            "medicines_existing": 0,
            "shops_created": 0,
            "shops_existing": 0,
            "inventory_created": 0,
            "assignments_created": 0,
        }

        # ────────────────────────────────────────────────────────
        # 1. USERS
        # ────────────────────────────────────────────────────────
        user_objects = {}
        for ud in USERS_DATA:
            existing = db.execute(
                select(User).where(User.email == ud["email"])
            ).scalar_one_or_none()

            if existing:
                user_objects[ud["username"]] = existing
                counters["users_existing"] += 1
                print(f"  · User already exists: {ud['email']}")
            else:
                hashed_pw = hash_password(ud["password"])
                user = User(
                    username=ud["username"],
                    email=ud["email"],
                    password_hash=hashed_pw,
                    full_name=ud["full_name"],
                    role=ud["role"],
                    is_locked=False,
                    failed_login_attempts=0,
                    password_changed_at=datetime.now(timezone.utc),
                    password_changed_by="self",
                    must_change_password=False,
                    mfa_enabled=False,
                )
                db.add(user)
                db.flush()
                user_objects[ud["username"]] = user
                counters["users_created"] += 1
                print(f"  ✓ User created: {ud['email']} (role={ud['role'].value})")

        print(f"✓ Users: {counters['users_created']} created, {counters['users_existing']} existing")

        # ────────────────────────────────────────────────────────
        # 2. SALTS & MEDICINES (from MEDICINE_CATALOG)
        # ────────────────────────────────────────────────────────
        salt_objects = {}   # formula_name -> Salt
        medicine_objects = []  # list of (Medicine, catalog_item)

        for item in MEDICINE_CATALOG:
            salt_name = item["salt_name"]

            # Check or create Salt
            existing_salt = db.execute(
                select(Salt).where(Salt.formula_name == salt_name)
            ).scalar_one_or_none()

            if existing_salt:
                salt = existing_salt
                counters["salts_existing"] += 1
            else:
                abc_class = ABC_CLASS_MAP.get(item["abc_class"], ABCClass.C)
                warning_threshold = int(item["reorder"] * 0.5) if item.get("reorder") else None

                salt = Salt(
                    formula_name=salt_name,
                    category=item["category"],
                    abc_class=abc_class,
                    reorder_level=item["reorder"],
                    safety_stock=item["safety_stock"],
                    critical_threshold=item["critical"],
                    warning_threshold=warning_threshold,
                    description=f"{salt_name} — {item['category']}",
                    dosage_form=item.get("form"),
                    standard_strength=item.get("strength"),
                    unit_of_measure="units",
                )
                db.add(salt)
                db.flush()
                counters["salts_created"] += 1

            salt_objects[salt_name] = salt

            # Check or create Medicine
            existing_med = db.execute(
                select(Medicine).where(
                    Medicine.brand_name == item["brand_name"],
                    Medicine.manufacturer == item["manufacturer"],
                )
            ).scalar_one_or_none()

            if existing_med:
                counters["medicines_existing"] += 1
                medicine_objects.append((existing_med, item))
            else:
                batch_prefix = derive_batch_prefix(item["brand_name"], item["manufacturer"])
                med = Medicine(
                    brand_name=item["brand_name"],
                    salt_id=salt.id,
                    manufacturer=item["manufacturer"],
                    strength=item["strength"],
                    dosage_form=item["form"],
                    unit_price=item["price"],
                    batch_prefix=batch_prefix,
                    temperature_sensitive=item.get("temp_sensitive", False),
                )
                db.add(med)
                db.flush()
                counters["medicines_created"] += 1
                medicine_objects.append((med, item))

        total_salts = counters["salts_created"] + counters["salts_existing"]
        total_meds = counters["medicines_created"] + counters["medicines_existing"]
        print(f"✓ Salts: {counters['salts_created']} created, {counters['salts_existing']} existing (total: {total_salts})")
        print(f"✓ Medicines: {counters['medicines_created']} created, {counters['medicines_existing']} existing (total: {total_meds})")

        # ────────────────────────────────────────────────────────
        # 3. SHOPS (from DEMO_STORES)
        # ────────────────────────────────────────────────────────
        shop_objects = {}  # code -> Shop

        for sd in DEMO_STORES:
            existing_shop = db.execute(
                select(Shop).where(Shop.code == sd["code"])
            ).scalar_one_or_none()

            if existing_shop:
                shop_objects[sd["code"]] = existing_shop
                counters["shops_existing"] += 1
                print(f"  · Shop already exists: {sd['code']} — {sd['name']}")
            else:
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
                counters["shops_created"] += 1
                print(f"  ✓ Shop created: {sd['code']} — {sd['name']} ({sd['city']})")

        total_shops = counters["shops_created"] + counters["shops_existing"]
        print(f"✓ Shops: {counters['shops_created']} created, {counters['shops_existing']} existing (total: {total_shops})")

        # ────────────────────────────────────────────────────────
        # 4. INVENTORY (realistic stock levels per shop)
        # ────────────────────────────────────────────────────────
        # Use a global RNG for deterministic results
        master_rng = random.Random(42)

        # Group shops by city for per-city seeding
        shops_by_city = {}
        for code, shop in shop_objects.items():
            city = shop.city
            if city not in shops_by_city:
                shops_by_city[city] = []
            shops_by_city[city].append((code, shop))

        # Track how many inventory items we create
        low_stock_count = 0
        expired_count = 0
        near_expiry_count = 0
        normal_count = 0

        today = date.today()

        for city, city_shops in shops_by_city.items():
            # Deterministic seed per city
            city_seed = int(hashlib.md5(city.encode()).hexdigest()[:8], 16)
            city_rng = random.Random(city_seed)

            for shop_code, shop in city_shops:
                is_central = shop_code in CENTRAL_CODES
                is_peripheral = shop_code in PERIPHERAL_CODES

                # Central shops carry 38-50 medicines; peripheral carry 30-40
                if is_central:
                    num_medicines = city_rng.randint(38, 50)
                else:
                    num_medicines = city_rng.randint(30, 40)

                # Select medicines for this shop (shuffle and take first N)
                shuffled_meds = list(medicine_objects)
                city_rng.shuffle(shuffled_meds)
                selected_meds = shuffled_meds[:num_medicines]

                for idx, (med, cat_item) in enumerate(selected_meds):
                    # Determine stock level category
                    roll = city_rng.random()

                    if roll < 0.08:
                        # ~8% EXPIRED items — expired before today
                        stock_multiplier = city_rng.uniform(0.2, 0.8)
                        # Expiry date in the past (3-12 months ago)
                        expired_days_ago = city_rng.randint(90, 365)
                        expiry = today - timedelta(days=expired_days_ago)
                        expired_count += 1
                    elif roll < 0.15:
                        # ~7% NEAR-EXPIRY — expiring within 90 days
                        stock_multiplier = city_rng.uniform(0.5, 1.0)
                        days_until_expiry = city_rng.randint(1, 90)
                        expiry = today + timedelta(days=days_until_expiry)
                        near_expiry_count += 1
                    elif roll < 0.30:
                        # ~15% LOW STOCK — 10-30% of reorder level
                        stock_multiplier = city_rng.uniform(0.10, 0.30)
                        expiry = random_expiry_date(
                            city_rng,
                            min_date=today + timedelta(days=60),
                            max_date=date(2027, 6, 30),
                        )
                        low_stock_count += 1
                    elif is_central:
                        # Central shops: 60-120% of reorder level
                        stock_multiplier = city_rng.uniform(0.60, 1.20)
                        expiry = random_expiry_date(
                            city_rng,
                            min_date=today + timedelta(days=90),
                            max_date=date(2027, 12, 31),
                        )
                        normal_count += 1
                    else:
                        # Peripheral shops: 20-60% of reorder level
                        stock_multiplier = city_rng.uniform(0.20, 0.60)
                        expiry = random_expiry_date(
                            city_rng,
                            min_date=today + timedelta(days=90),
                            max_date=date(2027, 12, 31),
                        )
                        normal_count += 1

                    # Calculate actual quantity
                    reorder_level = cat_item.get("reorder", 100)
                    quantity = max(1, int(reorder_level * stock_multiplier))

                    # Determine pricing
                    base_price = cat_item.get("price", 25.0)
                    cost_price = round(base_price * city_rng.uniform(0.65, 0.80), 2)
                    selling_price = round(base_price * city_rng.uniform(0.95, 1.10), 2)

                    # Generate batch number
                    batch_prefix = med.batch_prefix or "XXX"
                    batch_seed = city_seed + med.id + idx
                    batch_number = generate_batch_number(batch_prefix, batch_seed)

                    # Storage location
                    shelf_letter = chr(ord('A') + (idx % 6))
                    shelf_number = (idx // 6) + 1
                    storage_location = f"Shelf-{shelf_letter}{shelf_number}"

                    # Check for existing inventory entry (idempotency)
                    existing_inv = db.execute(
                        select(Inventory).where(
                            Inventory.med_id == med.id,
                            Inventory.shop_id == shop.id,
                            Inventory.batch_number == batch_number,
                        )
                    ).scalar_one_or_none()

                    if existing_inv:
                        continue

                    # Create inventory entry
                    inv = Inventory(
                        med_id=med.id,
                        shop_id=shop.id,
                        quantity=quantity,
                        batch_number=batch_number,
                        expiry_date=expiry,
                        cost_price=cost_price,
                        selling_price=selling_price,
                        storage_location=storage_location,
                    )
                    db.add(inv)
                    counters["inventory_created"] += 1

                # Flush per shop to avoid memory buildup
                db.flush()

        print(f"✓ Inventory entries created: {counters['inventory_created']}")
        print(f"    ├─ Normal stock:    {normal_count}")
        print(f"    ├─ Low stock:       {low_stock_count}")
        print(f"    ├─ Near-expiry:     {near_expiry_count}")
        print(f"    └─ Expired:         {expired_count}")

        # ────────────────────────────────────────────────────────
        # 5. SHOP-STAFF ASSIGNMENTS
        # ────────────────────────────────────────────────────────
        for city, city_shops in shops_by_city.items():
            # Determine which pharmacist manages this city
            pharmacist_key = CITY_PHARMACIST_MAP.get(city) or EXTRA_CITY_PHARMACIST_MAP.get(city)
            if not pharmacist_key or pharmacist_key not in user_objects:
                continue

            pharmacist = user_objects[pharmacist_key]

            for shop_idx, (shop_code, shop) in enumerate(city_shops):
                # Check if assignment already exists
                existing_assignment = db.execute(
                    select(ShopStaff).where(
                        ShopStaff.user_id == pharmacist.id,
                        ShopStaff.shop_id == shop.id,
                    )
                ).scalar_one_or_none()

                if existing_assignment:
                    print(f"  · Assignment exists: {pharmacist_key} → {shop_code}")
                    continue

                is_primary = (shop_idx == 0)
                assignment = ShopStaff(
                    user_id=pharmacist.id,
                    shop_id=shop.id,
                    assigned_date=today,
                    is_primary=is_primary,
                )
                db.add(assignment)
                counters["assignments_created"] += 1
                primary_marker = " (primary)" if is_primary else ""
                print(f"  ✓ Assignment created: {pharmacist_key} → {shop_code}{primary_marker}")

        print(f"✓ Shop-Staff assignments: {counters['assignments_created']} created")

        # ────────────────────────────────────────────────────────
        # COMMIT
        # ────────────────────────────────────────────────────────
        db.commit()

        # ────────────────────────────────────────────────────────
        # SUMMARY
        # ────────────────────────────────────────────────────────
        city_summary = {}
        for code, shop in shop_objects.items():
            city = shop.city
            if city not in city_summary:
                city_summary[city] = []
            city_summary[city].append(f"{shop.name} ({code})")

        print("\n" + "=" * 64)
        print("  MediSebi Enhanced Database — Seeded Successfully!")
        print("=" * 64)
        print(f"""
  📊 SEED SUMMARY
  ─────────────────────────────────────────────────────
  Users:              {counters['users_created']} created, {counters['users_existing']} existing
  Salts (APIs):       {counters['salts_created']} created, {counters['salts_existing']} existing
  Medicines:          {counters['medicines_created']} created, {counters['medicines_existing']} existing
  Shops:              {counters['shops_created']} created, {counters['shops_existing']} existing
  Inventory Entries:  {counters['inventory_created']}
  Shop-Staff Links:   {counters['assignments_created']}

  📦 INVENTORY BREAKDOWN
  ─────────────────────────────────────────────────────
  Normal Stock:       {normal_count}
  Low Stock:          {low_stock_count}  (for marketplace demo)
  Near-Expiry:        {near_expiry_count}  (within 90 days)
  Expired:            {expired_count}  (for expiry watchdog demo)

  🏪 SHOPS BY CITY
  ─────────────────────────────────────────────────────""")

        for city, shops in sorted(city_summary.items()):
            pharm_key = CITY_PHARMACIST_MAP.get(city) or EXTRA_CITY_PHARMACIST_MAP.get(city, "?")
            print(f"\n  {city} (pharmacist: {pharm_key})")
            for s in shops:
                print(f"    • {s}")

        print(f"""
  🔑 TEST CREDENTIALS
  ─────────────────────────────────────────────────────
  Admin:        admin@medisebi.com         / Admin@12345!
  Pharmacist 1: pharmacist1@medisebi.com   / Pharm@12345!   (Mumbai)
  Pharmacist 2: pharmacist2@medisebi.com   / Pharm2@12345!  (Delhi)
  Pharmacist 3: pharmacist3@medisebi.com   / Pharm3@12345!  (Bangalore)
  Pharmacist 4: pharmacist4@medisebi.com   / Pharm4@12345!  (Chennai + Kolkata)

  📁 Database: medisebi_dev.db (local SQLite)
""")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Seed failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
