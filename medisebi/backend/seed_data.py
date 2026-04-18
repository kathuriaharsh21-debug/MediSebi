"""
MediSebi — Database Seed Script
================================
Creates initial sample data for development and testing.

Creates:
  - 2 Users (admin + pharmacist)
  - 4 Salts (Paracetamol, Amoxicillin, ORS, Ibuprofen)
  - 6 Medicines (brand-name variants)
  - 3 Shops (Mumbai + Delhi)
  - 18 Inventory entries (various quantities and expiry dates)
  - 3 Shop-Staff assignments
"""

import sys
import os
from datetime import date, datetime, timezone

# ── Ensure the backend directory is on sys.path ──────────────────
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import bcrypt
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_engine
from app.models.user import User, UserRole
from app.models.salt import Salt, ABCClass
from app.models.medicine import Medicine
from app.models.shop import Shop
from app.models.inventory import Inventory
from app.models.shop_staff import ShopStaff

# ── Database Setup (uses same engine as the app) ─────────────────
engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with 12 rounds."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def seed_database() -> None:
    """Seed the database with sample data."""
    # ── Create all tables if they don't exist ──────────────────
    Base.metadata.create_all(bind=engine)
    print("✓ Tables ensured via Base.metadata.create_all()")

    db = SessionLocal()

    try:
        # ────────────────────────────────────────────────────────
        # 1. USERS
        # ────────────────────────────────────────────────────────
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
            username="pharmacist1",
            email="pharm1@medisebi.com",
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
        db.flush()  # Flush to get IDs
        print(f"✓ Users created: admin (id={admin_user.id}), pharmacist1 (id={pharmacist_user.id})")

        # ────────────────────────────────────────────────────────
        # 2. SALTS
        # ────────────────────────────────────────────────────────
        salts_data = [
            {
                "formula_name": "Paracetamol",
                "category": "Analgesic",
                "abc_class": ABCClass.A,
                "reorder_level": 200,
                "safety_stock": 100,
                "critical_threshold": 50,
                "warning_threshold": 100,
                "description": "Widely used analgesic and antipyretic. First-line treatment for pain and fever.",
                "dosage_form": "Tablet",
                "standard_strength": "500mg",
                "unit_of_measure": "tablets",
            },
            {
                "formula_name": "Amoxicillin",
                "category": "Antibiotic",
                "abc_class": ABCClass.A,
                "reorder_level": 150,
                "safety_stock": 75,
                "critical_threshold": 30,
                "warning_threshold": 75,
                "description": "Broad-spectrum beta-lactam antibiotic. Commonly used for bacterial infections.",
                "dosage_form": "Capsule",
                "standard_strength": "500mg",
                "unit_of_measure": "capsules",
            },
            {
                "formula_name": "Oral Rehydration Salts",
                "category": "ORS",
                "abc_class": ABCClass.B,
                "reorder_level": 300,
                "safety_stock": 100,
                "critical_threshold": 50,
                "warning_threshold": 150,
                "description": "WHO-formulated oral rehydration solution for dehydration management.",
                "dosage_form": "Powder",
                "standard_strength": "21.8g sachet",
                "unit_of_measure": "sachets",
            },
            {
                "formula_name": "Ibuprofen",
                "category": "Analgesic",
                "abc_class": ABCClass.B,
                "reorder_level": 100,
                "safety_stock": 50,
                "critical_threshold": 20,
                "warning_threshold": 50,
                "description": "NSAID used for pain, inflammation, and fever reduction.",
                "dosage_form": "Tablet",
                "standard_strength": "400mg",
                "unit_of_measure": "tablets",
            },
        ]

        salt_objects = {}
        for sd in salts_data:
            salt = Salt(**sd)
            db.add(salt)
            db.flush()
            salt_objects[sd["formula_name"]] = salt

        salt_names = list(salt_objects.keys())
        print(f"✓ Salts created ({len(salt_objects)}): {', '.join(salt_names)}")

        # ────────────────────────────────────────────────────────
        # 3. MEDICINES
        # ────────────────────────────────────────────────────────
        medicines_data = [
            {"brand_name": "Crocin 500mg", "salt_key": "Paracetamol", "manufacturer": "GSK", "strength": "500mg", "dosage_form": "Tablet", "unit_price": 2.50, "batch_prefix": "CRC"},
            {"brand_name": "Calpol 500mg", "salt_key": "Paracetamol", "manufacturer": "GSK", "strength": "500mg", "dosage_form": "Tablet", "unit_price": 2.00, "batch_prefix": "CPL"},
            {"brand_name": "Dolo 650mg", "salt_key": "Paracetamol", "manufacturer": "Micro Labs", "strength": "650mg", "dosage_form": "Tablet", "unit_price": 3.00, "batch_prefix": "DLO"},
            {"brand_name": "Mox 500mg", "salt_key": "Amoxicillin", "manufacturer": "Sun Pharma", "strength": "500mg", "dosage_form": "Capsule", "unit_price": 8.50, "batch_prefix": "MOX"},
            {"brand_name": "Electral Powder", "salt_key": "Oral Rehydration Salts", "manufacturer": "FDC Ltd", "strength": "21.8g", "dosage_form": "Powder", "unit_price": 22.00, "batch_prefix": "ELC"},
            {"brand_name": "Brufen 400mg", "salt_key": "Ibuprofen", "manufacturer": "Abbott", "strength": "400mg", "dosage_form": "Tablet", "unit_price": 4.50, "batch_prefix": "BRF"},
        ]

        medicine_objects = {}
        for md in medicines_data:
            medicine = Medicine(
                brand_name=md["brand_name"],
                salt_id=salt_objects[md["salt_key"]].id,
                manufacturer=md["manufacturer"],
                strength=md["strength"],
                dosage_form=md["dosage_form"],
                unit_price=md["unit_price"],
                batch_prefix=md["batch_prefix"],
            )
            db.add(medicine)
            db.flush()
            medicine_objects[md["brand_name"]] = medicine

        medicine_names = list(medicine_objects.keys())
        print(f"✓ Medicines created ({len(medicine_objects)}): {', '.join(medicine_names)}")

        # ────────────────────────────────────────────────────────
        # 4. SHOPS
        # ────────────────────────────────────────────────────────
        shops_data = [
            {
                "name": "MediSebi Central",
                "code": "PH-CEN-001",
                "city": "Mumbai",
                "state": "Maharashtra",
                "address": "123 Marine Drive, Fort, Mumbai 400001",
                "pincode": "400001",
                "latitude": 18.9434,
                "longitude": 72.8235,
                "contact_phone": "+91-22-12345678",
                "contact_email": "central@medisebi.com",
                "storage_capacity": 50000,
            },
            {
                "name": "MediSebi West",
                "code": "PH-WST-002",
                "city": "Mumbai",
                "state": "Maharashtra",
                "address": "456 Linking Road, Bandra, Mumbai 400050",
                "pincode": "400050",
                "latitude": 19.0596,
                "longitude": 72.8295,
                "contact_phone": "+91-22-23456789",
                "contact_email": "west@medisebi.com",
                "storage_capacity": 30000,
            },
            {
                "name": "MediSebi North",
                "code": "PH-NRT-003",
                "city": "Delhi",
                "state": "Delhi NCR",
                "address": "789 Connaught Place, New Delhi 110001",
                "pincode": "110001",
                "latitude": 28.6315,
                "longitude": 77.2167,
                "contact_phone": "+91-11-34567890",
                "contact_email": "north@medisebi.com",
                "storage_capacity": 40000,
            },
        ]

        shop_objects = {}
        for sd in shops_data:
            shop = Shop(**sd)
            db.add(shop)
            db.flush()
            shop_objects[sd["code"]] = shop

        shop_names = [f"{s.name} ({s.code})" for s in shop_objects.values()]
        print(f"✓ Shops created ({len(shop_objects)}): {', '.join(shop_names)}")

        # ────────────────────────────────────────────────────────
        # 5. INVENTORY ENTRIES
        # ────────────────────────────────────────────────────────
        inventory_data = [
            # MediSebi Central — Crocin 500mg
            {"med": "Crocin 500mg", "shop": "PH-CEN-001", "qty": 500, "batch": "CRC-2025-001", "expiry": date(2026, 6, 30), "cost": 2.00, "sell": 2.50, "location": "Shelf-A1"},
            {"med": "Crocin 500mg", "shop": "PH-CEN-001", "qty": 150, "batch": "CRC-2025-002", "expiry": date(2025, 9, 15), "cost": 2.00, "sell": 2.50, "location": "Shelf-A1"},
            # MediSebi Central — Calpol 500mg
            {"med": "Calpol 500mg", "shop": "PH-CEN-001", "qty": 300, "batch": "CPL-2025-001", "expiry": date(2026, 3, 20), "cost": 1.60, "sell": 2.00, "location": "Shelf-A2"},
            # MediSebi Central — Dolo 650mg
            {"med": "Dolo 650mg", "shop": "PH-CEN-001", "qty": 250, "batch": "DLO-2025-001", "expiry": date(2026, 8, 10), "cost": 2.40, "sell": 3.00, "location": "Shelf-A3"},
            # MediSebi Central — Mox 500mg
            {"med": "Mox 500mg", "shop": "PH-CEN-001", "qty": 80, "batch": "MOX-2025-001", "expiry": date(2026, 1, 15), "cost": 6.80, "sell": 8.50, "location": "Shelf-B1"},
            # MediSebi Central — Electral Powder
            {"med": "Electral Powder", "shop": "PH-CEN-001", "qty": 400, "batch": "ELC-2025-001", "expiry": date(2027, 5, 30), "cost": 17.50, "sell": 22.00, "location": "Shelf-C1"},
            # MediSebi Central — Brufen 400mg
            {"med": "Brufen 400mg", "shop": "PH-CEN-001", "qty": 120, "batch": "BRF-2025-001", "expiry": date(2025, 12, 1), "cost": 3.60, "sell": 4.50, "location": "Shelf-A4"},

            # MediSebi West — Crocin 500mg
            {"med": "Crocin 500mg", "shop": "PH-WST-002", "qty": 30, "batch": "CRC-2025-003", "expiry": date(2025, 8, 10), "cost": 2.00, "sell": 2.50, "location": "Shelf-A1"},
            # MediSebi West — Calpol 500mg
            {"med": "Calpol 500mg", "shop": "PH-WST-002", "qty": 200, "batch": "CPL-2025-002", "expiry": date(2026, 5, 15), "cost": 1.60, "sell": 2.00, "location": "Shelf-A2"},
            # MediSebi West — Dolo 650mg
            {"med": "Dolo 650mg", "shop": "PH-WST-002", "qty": 450, "batch": "DLO-2025-002", "expiry": date(2026, 11, 30), "cost": 2.40, "sell": 3.00, "location": "Shelf-A3"},
            # MediSebi West — Mox 500mg
            {"med": "Mox 500mg", "shop": "PH-WST-002", "qty": 200, "batch": "MOX-2025-002", "expiry": date(2026, 4, 20), "cost": 6.80, "sell": 8.50, "location": "Shelf-B1"},
            # MediSebi West — Electral Powder
            {"med": "Electral Powder", "shop": "PH-WST-002", "qty": 50, "batch": "ELC-2025-002", "expiry": date(2025, 10, 5), "cost": 17.50, "sell": 22.00, "location": "Shelf-C1"},
            # MediSebi West — Brufen 400mg
            {"med": "Brufen 400mg", "shop": "PH-WST-002", "qty": 90, "batch": "BRF-2025-002", "expiry": date(2026, 2, 28), "cost": 3.60, "sell": 4.50, "location": "Shelf-A4"},

            # MediSebi North — Crocin 500mg
            {"med": "Crocin 500mg", "shop": "PH-NRT-003", "qty": 350, "batch": "CRC-2025-004", "expiry": date(2026, 7, 20), "cost": 2.00, "sell": 2.50, "location": "Shelf-A1"},
            # MediSebi North — Calpol 500mg
            {"med": "Calpol 500mg", "shop": "PH-NRT-003", "qty": 10, "batch": "CPL-2025-003", "expiry": date(2025, 7, 30), "cost": 1.60, "sell": 2.00, "location": "Shelf-A2"},
            # MediSebi North — Dolo 650mg
            {"med": "Dolo 650mg", "shop": "PH-NRT-003", "qty": 180, "batch": "DLO-2025-003", "expiry": date(2026, 9, 15), "cost": 2.40, "sell": 3.00, "location": "Shelf-A3"},
            # MediSebi North — Mox 500mg
            {"med": "Mox 500mg", "shop": "PH-NRT-003", "qty": 25, "batch": "MOX-2025-003", "expiry": date(2026, 2, 10), "cost": 6.80, "sell": 8.50, "location": "Shelf-B1"},
            # MediSebi North — Electral Powder
            {"med": "Electral Powder", "shop": "PH-NRT-003", "qty": 250, "batch": "ELC-2025-003", "expiry": date(2027, 1, 10), "cost": 17.50, "sell": 22.00, "location": "Shelf-C1"},
            # MediSebi North — Brufen 400mg
            {"med": "Brufen 400mg", "shop": "PH-NRT-003", "qty": 60, "batch": "BRF-2025-003", "expiry": date(2025, 11, 15), "cost": 3.60, "sell": 4.50, "location": "Shelf-A4"},
        ]

        inv_count = 0
        for inv in inventory_data:
            item = Inventory(
                med_id=medicine_objects[inv["med"]].id,
                shop_id=shop_objects[inv["shop"]].id,
                quantity=inv["qty"],
                batch_number=inv["batch"],
                expiry_date=inv["expiry"],
                cost_price=inv["cost"],
                selling_price=inv["sell"],
                storage_location=inv["location"],
            )
            db.add(item)
            inv_count += 1

        db.flush()
        print(f"✓ Inventory entries created: {inv_count}")

        # ────────────────────────────────────────────────────────
        # 6. SHOP-STAFF ASSIGNMENTS
        # ────────────────────────────────────────────────────────
        assignments = [
            {"user_id": pharmacist_user.id, "shop_code": "PH-CEN-001", "is_primary": True},
            {"user_id": pharmacist_user.id, "shop_code": "PH-WST-002", "is_primary": False},
            {"user_id": pharmacist_user.id, "shop_code": "PH-NRT-003", "is_primary": False},
        ]

        for i, asgn in enumerate(assignments):
            shop_staff = ShopStaff(
                user_id=asgn["user_id"],
                shop_id=shop_objects[asgn["shop_code"]].id,
                assigned_date=date.today(),
                is_primary=asgn["is_primary"],
            )
            db.add(shop_staff)

        db.flush()
        print(f"✓ Shop-Staff assignments created: {len(assignments)} (pharmacist1 → all 3 shops)")

        # ────────────────────────────────────────────────────────
        # COMMIT
        # ────────────────────────────────────────────────────────
        db.commit()

        # ────────────────────────────────────────────────────────
        # SUMMARY
        # ────────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  MediSebi Database Seeded Successfully!")
        print("=" * 60)
        print(f"""
  📊 SEED SUMMARY
  ─────────────────────────────────────────────
  Users:           2  (admin, pharmacist1)
  Salts:           4  (Paracetamol, Amoxicillin, ORS, Ibuprofen)
  Medicines:       6  (Crocin, Calpol, Dolo, Mox, Electral, Brufen)
  Shops:           3  (Central-Mumbai, West-Mumbai, North-Delhi)
  Inventory:       {inv_count} entries across 3 shops
  Shop-Staff:      3 assignments

  🔑 TEST CREDENTIALS
  ─────────────────────────────────────────────
  Admin:       admin@medisebi.com  /  Admin@12345!
  Pharmacist:  pharm1@medisebi.com  /  Pharm@12345!

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
