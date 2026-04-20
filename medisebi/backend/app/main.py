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
    """Seed the database with demo data if no users exist.
    This is critical for Render free tier where the filesystem
    is ephemeral and gets wiped on every deploy/restart.

    Creates:
      - 3 Users (admin, pharmacist, demo-pharmacy owner)
      - 12 Salts (winter-season focused)
      - 24 Medicines (brand-name variants)
      - 4 Shops (incl. demo pharmacy)
      - 55+ Inventory entries across all shops
      - 6 months of bill/sales history for the demo pharmacy
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
        from app.models.bill import Bill, BillItem, PaymentMethod, BillStatus
        from app.auth.password import hash_password
        from datetime import date, datetime, timezone, timedelta
        import random

        random.seed(42)

        # ────────────────────────────────────────────────────────
        # 1. USERS (3 accounts)
        # ────────────────────────────────────────────────────────
        admin = User(
            username="admin", email="admin@medisebi.com",
            password_hash=hash_password("Admin@12345!"),
            full_name="System Administrator", role="admin",
            is_active=True, is_locked=False, failed_login_attempts=0,
            password_changed_at=datetime.now(timezone.utc),
            password_changed_by="self", must_change_password=False, mfa_enabled=False,
        )
        pharmacist = User(
            username="pharmacist1", email="pharm1@medisebi.com",
            password_hash=hash_password("Pharm@12345!"),
            full_name="Dr. Priya Sharma", role="pharmacist",
            is_active=True, is_locked=False, failed_login_attempts=0,
            password_changed_at=datetime.now(timezone.utc),
            password_changed_by="self", must_change_password=False, mfa_enabled=False,
        )
        demo_user = User(
            username="demopharmacy", email="demo@citymeds.com",
            password_hash=hash_password("Demo@12345!"),
            full_name="Rajesh Kumar", role="pharmacist",
            is_active=True, is_locked=False, failed_login_attempts=0,
            password_changed_at=datetime.now(timezone.utc),
            password_changed_by="self", must_change_password=False, mfa_enabled=False,
        )
        db.add(admin); db.add(pharmacist); db.add(demo_user)
        db.flush()
        logger.info(f"Users: admin(id={admin.id}), pharmacist1(id={pharmacist.id}), demopharmacy(id={demo_user.id})")

        # ────────────────────────────────────────────────────────
        # 2. SALTS — 12 winter-season focused
        # ────────────────────────────────────────────────────────
        salts = [
            Salt(formula_name="Paracetamol", category="Analgesic", abc_class=ABCClass.A,
                 reorder_level=200, safety_stock=100, critical_threshold=50, warning_threshold=100,
                 description="Widely used analgesic and antipyretic.", dosage_form="Tablet",
                 standard_strength="500mg", unit_of_measure="tablets"),
            Salt(formula_name="Amoxicillin", category="Antibiotic", abc_class=ABCClass.A,
                 reorder_level=150, safety_stock=75, critical_threshold=30, warning_threshold=75,
                 description="Broad-spectrum beta-lactam antibiotic.", dosage_form="Capsule",
                 standard_strength="500mg", unit_of_measure="capsules"),
            Salt(formula_name="Ibuprofen", category="Analgesic", abc_class=ABCClass.B,
                 reorder_level=100, safety_stock=50, critical_threshold=20, warning_threshold=50,
                 description="NSAID for pain, inflammation, fever.", dosage_form="Tablet",
                 standard_strength="400mg", unit_of_measure="tablets"),
            Salt(formula_name="Oral Rehydration Salts", category="ORS", abc_class=ABCClass.B,
                 reorder_level=300, safety_stock=100, critical_threshold=50, warning_threshold=150,
                 description="WHO-formulated ORS for dehydration.", dosage_form="Powder",
                 standard_strength="21.8g sachet", unit_of_measure="sachets"),
            Salt(formula_name="Cetirizine", category="Antihistamine", abc_class=ABCClass.A,
                 reorder_level=120, safety_stock=60, critical_threshold=25, warning_threshold=60,
                 description="2nd gen antihistamine for cold, allergy, rhinitis.", dosage_form="Tablet",
                 standard_strength="10mg", unit_of_measure="tablets"),
            Salt(formula_name="Dextromethorphan", category="Antitussive", abc_class=ABCClass.B,
                 reorder_level=80, safety_stock=40, critical_threshold=15, warning_threshold=40,
                 description="Cough suppressant for dry cough.", dosage_form="Syrup",
                 standard_strength="15mg/5ml", unit_of_measure="bottles"),
            Salt(formula_name="Ambroxol", category="Mucolytic", abc_class=ABCClass.B,
                 reorder_level=100, safety_stock=50, critical_threshold=20, warning_threshold=50,
                 description="Mucolytic agent for productive cough.", dosage_form="Syrup",
                 standard_strength="30mg/5ml", unit_of_measure="bottles"),
            Salt(formula_name="Azithromycin", category="Antibiotic", abc_class=ABCClass.A,
                 reorder_level=100, safety_stock=50, critical_threshold=20, warning_threshold=50,
                 description="Macrolide antibiotic for respiratory infections.", dosage_form="Tablet",
                 standard_strength="500mg", unit_of_measure="tablets"),
            Salt(formula_name="Cetrimide", category="Antiseptic", abc_class=ABCClass.C,
                 reorder_level=50, safety_stock=25, critical_threshold=10, warning_threshold=25,
                 description="Topical antiseptic for wounds.", dosage_form="Cream",
                 standard_strength="0.5%", unit_of_measure="tubes"),
            Salt(formula_name="Vitamin C", category="Vitamin", abc_class=ABCClass.B,
                 reorder_level=200, safety_stock=100, critical_threshold=50, warning_threshold=100,
                 description="Ascorbic acid immunity booster.", dosage_form="Tablet",
                 standard_strength="500mg", unit_of_measure="tablets"),
            Salt(formula_name="Chlorpheniramine", category="Antihistamine", abc_class=ABCClass.B,
                 reorder_level=80, safety_stock=40, critical_threshold=15, warning_threshold=40,
                 description="1st gen antihistamine for cold & allergy.", dosage_form="Tablet",
                 standard_strength="4mg", unit_of_measure="tablets"),
            Salt(formula_name="Chlorpheniramine+Paracetamol", category="Antihistamine+Analgesic", abc_class=ABCClass.B,
                 reorder_level=100, safety_stock=50, critical_threshold=20, warning_threshold=50,
                 description="Combination cold relief (antihistamine + analgesic).", dosage_form="Tablet",
                 standard_strength="2mg+500mg", unit_of_measure="tablets"),
            Salt(formula_name="Ibuprofen+Paracetamol", category="Analgesic", abc_class=ABCClass.A,
                 reorder_level=120, safety_stock=60, critical_threshold=25, warning_threshold=60,
                 description="Combination pain reliever and fever reducer.", dosage_form="Tablet",
                 standard_strength="400mg+325mg", unit_of_measure="tablets"),
            Salt(formula_name="Guaifenesin", category="Expectorant", abc_class=ABCClass.C,
                 reorder_level=60, safety_stock=30, critical_threshold=10, warning_threshold=30,
                 description="Expectorant for chesty cough.", dosage_form="Syrup",
                 standard_strength="100mg/5ml", unit_of_measure="bottles"),
        ]
        salt_map = {}
        for s in salts:
            db.add(s); db.flush()
            salt_map[s.formula_name] = s
        logger.info(f"Salts: {len(salt_map)} created")

        # ────────────────────────────────────────────────────────
        # 3. MEDICINES — 24 brand-name variants
        # ────────────────────────────────────────────────────────
        med_defs = [
            # Paracetamol family (fever, headache, body ache)
            ("Crocin 500mg", "Paracetamol", "GSK", "500mg", "Tablet", 2.50, "CRC"),
            ("Calpol 500mg", "Paracetamol", "GSK", "500mg", "Tablet", 2.00, "CPL"),
            ("Dolo 650mg", "Paracetamol", "Micro Labs", "650mg", "Tablet", 3.00, "DLO"),
            ("P-650 Tablet", "Paracetamol", "Alkem", "650mg", "Tablet", 2.80, "P65"),
            # Antibiotics (throat infection, bronchitis, pneumonia)
            ("Mox 500mg", "Amoxicillin", "Sun Pharma", "500mg", "Capsule", 8.50, "MOX"),
            ("Amoxil 500mg", "Amoxicillin", "GSK", "500mg", "Capsule", 9.00, "AMX"),
            ("Azithral 500mg", "Azithromycin", "Alembic", "500mg", "Tablet", 52.00, "AZR"),
            ("Zithromax 500mg", "Azithromycin", "Pfizer", "500mg", "Tablet", 65.00, "ZTH"),
            # Pain & Inflammation (joint pain, body ache, fever)
            ("Brufen 400mg", "Ibuprofen", "Abbott", "400mg", "Tablet", 4.50, "BRF"),
            ("Combiflam", "Ibuprofen+Paracetamol", "Sanofi", "400+325mg", "Tablet", 5.00, "CBF"),
            ("Flexon MR", "Ibuprofen+Paracetamol", "Sun Pharma", "400+325mg", "Tablet", 4.80, "FLX"),
            # Cold, Cough & Allergy (winter seasonal demand spike)
            ("Cetzine 10mg", "Cetirizine", "Dr Reddys", "10mg", "Tablet", 3.50, "CTZ"),
            ("Zyrtec 10mg", "Cetirizine", "UCB", "10mg", "Tablet", 6.00, "ZRC"),
            ("Benadryl Cough Syrup", "Dextromethorphan", "J&J", "15mg/5ml", "Syrup", 85.00, "BEN"),
            ("Corex Syrup", "Dextromethorphan", "Pfizer", "15mg/5ml", "Syrup", 78.00, "CRX"),
            ("Ambrodil Syrup", "Ambroxol", "Mankind", "30mg/5ml", "Syrup", 68.00, "AMB"),
            ("Mucolite Syrup", "Ambroxol", "Cipla", "30mg/5ml", "Syrup", 72.00, "MUC"),
            ("Sinarest New", "Chlorpheniramine+Paracetamol", "Centaur", "2mg+500mg", "Tablet", 4.20, "SIN"),
            ("Vicks Action 500", "Chlorpheniramine+Paracetamol", "P&G", "500mg", "Tablet", 5.50, "VCK"),
            ("TusQ Dx Syrup", "Guaifenesin", "Mankind", "100mg/5ml", "Syrup", 55.00, "TUS"),
            # Immunity & General Health
            ("Electral Powder", "Oral Rehydration Salts", "FDC Ltd", "21.8g", "Powder", 22.00, "ELC"),
            ("Limcee 500mg", "Vitamin C", "Abbott", "500mg", "Tablet", 1.50, "LMC"),
            ("Celin 500mg", "Vitamin C", "Abbott", "500mg", "Tablet", 1.20, "CLN"),
            # Antiseptic (winter wound care)
            ("Savlon Cream", "Cetrimide", "J&J", "0.5%", "Cream", 45.00, "SVL"),
        ]
        med_map = {}
        for brand, salt_name, mfr, strength, form, price, prefix in med_defs:
            m = Medicine(brand_name=brand, salt_id=salt_map[salt_name].id,
                        manufacturer=mfr, strength=strength, dosage_form=form,
                        unit_price=price, batch_prefix=prefix)
            db.add(m); db.flush()
            med_map[brand] = m
        logger.info(f"Medicines: {len(med_map)} created")

        # ────────────────────────────────────────────────────────
        # 4. SHOPS — 4 pharmacies
        # ────────────────────────────────────────────────────────
        shop_defs = [
            ("MediSebi Central", "PH-CEN-001", "Mumbai", "Maharashtra",
             "123 Marine Drive, Fort, Mumbai 400001", "400001", 18.9434, 72.8235, 50000),
            ("MediSebi West", "PH-WST-002", "Mumbai", "Maharashtra",
             "456 Linking Road, Bandra, Mumbai 400050", "400050", 19.0596, 72.8295, 30000),
            ("MediSebi North", "PH-NRT-003", "Delhi", "Delhi NCR",
             "789 Connaught Place, New Delhi 110001", "110001", 28.6315, 77.2167, 40000),
            ("CityMeds Pharmacy", "PH-DEM-004", "Jaipur", "Rajasthan",
             "22 MI Road, Pink City, Jaipur 302001", "302001", 26.9124, 75.7873, 20000),
        ]
        shop_map = {}
        for name, code, city, state, addr, pin, lat, lon, cap in shop_defs:
            s = Shop(name=name, code=code, city=city, state=state, address=addr,
                     pincode=pin, latitude=lat, longitude=lon, storage_capacity=cap)
            db.add(s); db.flush()
            shop_map[code] = s
        logger.info(f"Shops: {len(shop_map)} created")

        # ────────────────────────────────────────────────────────
        # 5. INVENTORY — realistic stock for all shops
        # ────────────────────────────────────────────────────────
        inv_data = [
            # === MediSebi Central (PH-CEN-001) ===
            ("Crocin 500mg", "PH-CEN-001", 500, "CRC-2025-001", date(2026,6,30), 2.00, 2.50),
            ("Crocin 500mg", "PH-CEN-001", 120, "CRC-2025-002", date(2025,9,15), 2.00, 2.50),
            ("Calpol 500mg", "PH-CEN-001", 300, "CPL-2025-001", date(2026,3,20), 1.60, 2.00),
            ("Dolo 650mg", "PH-CEN-001", 250, "DLO-2025-001", date(2026,8,10), 2.40, 3.00),
            ("P-650 Tablet", "PH-CEN-001", 180, "P65-2025-001", date(2026,5,15), 2.20, 2.80),
            ("Mox 500mg", "PH-CEN-001", 80, "MOX-2025-001", date(2026,1,15), 6.80, 8.50),
            ("Amoxil 500mg", "PH-CEN-001", 60, "AMX-2025-001", date(2026,4,20), 7.20, 9.00),
            ("Azithral 500mg", "PH-CEN-001", 45, "AZR-2025-001", date(2026,7,10), 42.00, 52.00),
            ("Brufen 400mg", "PH-CEN-001", 120, "BRF-2025-001", date(2025,12,1), 3.60, 4.50),
            ("Combiflam", "PH-CEN-001", 200, "CBF-2025-001", date(2026,9,30), 4.00, 5.00),
            ("Cetzine 10mg", "PH-CEN-001", 90, "CTZ-2025-001", date(2026,6,15), 2.80, 3.50),
            ("Benadryl Cough Syrup", "PH-CEN-001", 35, "BEN-2025-001", date(2026,3,1), 68.00, 85.00),
            ("Corex Syrup", "PH-CEN-001", 20, "CRX-2025-001", date(2025,11,20), 62.00, 78.00),
            ("Ambrodil Syrup", "PH-CEN-001", 40, "AMB-2025-001", date(2026,5,10), 54.00, 68.00),
            ("Sinarest New", "PH-CEN-001", 110, "SIN-2025-001", date(2026,2,28), 3.36, 4.20),
            ("Vicks Action 500", "PH-CEN-001", 75, "VCK-2025-001", date(2026,4,15), 4.40, 5.50),
            ("Electral Powder", "PH-CEN-001", 400, "ELC-2025-001", date(2027,5,30), 17.50, 22.00),
            ("Limcee 500mg", "PH-CEN-001", 250, "LMC-2025-001", date(2027,2,28), 1.20, 1.50),
            ("Savlon Cream", "PH-CEN-001", 30, "SVL-2025-001", date(2026,8,20), 36.00, 45.00),

            # === MediSebi West (PH-WST-002) ===
            ("Crocin 500mg", "PH-WST-002", 30, "CRC-2025-003", date(2025,8,10), 2.00, 2.50),
            ("Calpol 500mg", "PH-WST-002", 200, "CPL-2025-002", date(2026,5,15), 1.60, 2.00),
            ("Dolo 650mg", "PH-WST-002", 450, "DLO-2025-002", date(2026,11,30), 2.40, 3.00),
            ("Mox 500mg", "PH-WST-002", 200, "MOX-2025-002", date(2026,4,20), 6.80, 8.50),
            ("Electral Powder", "PH-WST-002", 50, "ELC-2025-002", date(2025,10,5), 17.50, 22.00),
            ("Brufen 400mg", "PH-WST-002", 90, "BRF-2025-002", date(2026,2,28), 3.60, 4.50),
            ("Combiflam", "PH-WST-002", 150, "CBF-2025-002", date(2026,8,15), 4.00, 5.00),
            ("Cetzine 10mg", "PH-WST-002", 60, "CTZ-2025-002", date(2026,5,30), 2.80, 3.50),
            ("Benadryl Cough Syrup", "PH-WST-002", 25, "BEN-2025-002", date(2026,2,10), 68.00, 85.00),
            ("Sinarest New", "PH-WST-002", 80, "SIN-2025-002", date(2026,1,20), 3.36, 4.20),
            ("Limcee 500mg", "PH-WST-002", 180, "LMC-2025-002", date(2026,12,31), 1.20, 1.50),

            # === MediSebi North Delhi (PH-NRT-003) ===
            ("Crocin 500mg", "PH-NRT-003", 350, "CRC-2025-004", date(2026,7,20), 2.00, 2.50),
            ("Calpol 500mg", "PH-NRT-003", 10, "CPL-2025-003", date(2025,7,30), 1.60, 2.00),
            ("Dolo 650mg", "PH-NRT-003", 180, "DLO-2025-003", date(2026,9,15), 2.40, 3.00),
            ("Mox 500mg", "PH-NRT-003", 25, "MOX-2025-003", date(2026,2,10), 6.80, 8.50),
            ("Electral Powder", "PH-NRT-003", 250, "ELC-2025-003", date(2027,1,10), 17.50, 22.00),
            ("Brufen 400mg", "PH-NRT-003", 60, "BRF-2025-003", date(2025,11,15), 3.60, 4.50),
            ("Azithral 500mg", "PH-NRT-003", 30, "AZR-2025-002", date(2026,3,30), 42.00, 52.00),
            ("Combiflam", "PH-NRT-003", 100, "CBF-2025-003", date(2026,6,10), 4.00, 5.00),
            ("Vicks Action 500", "PH-NRT-003", 40, "VCK-2025-002", date(2026,1,25), 4.40, 5.50),
            ("Celin 500mg", "PH-NRT-003", 200, "CLN-2025-001", date(2027,1,15), 0.96, 1.20),

            # ═══════════════════════════════════════════════════════
            # === DEMO PHARMACY — CityMeds Jaipur (PH-DEM-004) ===
            # Full winter-season stock (Oct 2025 – Mar 2026)
            # ═══════════════════════════════════════════════════════
            # -- Analgesics / Fever (high demand in winter) --
            ("Crocin 500mg", "PH-DEM-004", 280, "CRC-D25-001", date(2026,8,15), 2.00, 2.50),
            ("Calpol 500mg", "PH-DEM-004", 200, "CPL-D25-001", date(2026,6,20), 1.60, 2.00),
            ("Dolo 650mg", "PH-DEM-004", 350, "DLO-D25-001", date(2026,10,30), 2.40, 3.00),
            ("P-650 Tablet", "PH-DEM-004", 150, "P65-D25-001", date(2026,7,10), 2.20, 2.80),
            ("Brufen 400mg", "PH-DEM-004", 100, "BRF-D25-001", date(2026,5,1), 3.60, 4.50),
            ("Combiflam", "PH-DEM-004", 220, "CBF-D25-001", date(2026,9,25), 4.00, 5.00),
            ("Flexon MR", "PH-DEM-004", 80, "FLX-D25-001", date(2026,4,15), 3.84, 4.80),
            # -- Antibiotics (throat, chest, sinus infections) --
            ("Mox 500mg", "PH-DEM-004", 120, "MOX-D25-001", date(2026,3,20), 6.80, 8.50),
            ("Amoxil 500mg", "PH-DEM-004", 80, "AMX-D25-001", date(2026,5,10), 7.20, 9.00),
            ("Azithral 500mg", "PH-DEM-004", 55, "AZR-D25-001", date(2026,7,5), 42.00, 52.00),
            ("Zithromax 500mg", "PH-DEM-004", 25, "ZTH-D25-001", date(2026,6,15), 52.00, 65.00),
            # -- Cold, Cough, Allergy (peak winter demand) --
            ("Cetzine 10mg", "PH-DEM-004", 160, "CTZ-D25-001", date(2026,6,25), 2.80, 3.50),
            ("Zyrtec 10mg", "PH-DEM-004", 60, "ZRC-D25-001", date(2026,8,10), 4.80, 6.00),
            ("Benadryl Cough Syrup", "PH-DEM-004", 50, "BEN-D25-001", date(2026,4,1), 68.00, 85.00),
            ("Corex Syrup", "PH-DEM-004", 30, "CRX-D25-001", date(2026,3,15), 62.00, 78.00),
            ("Ambrodil Syrup", "PH-DEM-004", 55, "AMB-D25-001", date(2026,5,20), 54.00, 68.00),
            ("Mucolite Syrup", "PH-DEM-004", 40, "MUC-D25-001", date(2026,6,30), 57.60, 72.00),
            ("Sinarest New", "PH-DEM-004", 180, "SIN-D25-001", date(2026,3,10), 3.36, 4.20),
            ("Vicks Action 500", "PH-DEM-004", 100, "VCK-D25-001", date(2026,4,25), 4.40, 5.50),
            ("TusQ Dx Syrup", "PH-DEM-004", 35, "TUS-D25-001", date(2026,5,30), 44.00, 55.00),
            # -- Immunity & Winter wellness --
            ("Electral Powder", "PH-DEM-004", 300, "ELC-D25-001", date(2027,3,15), 17.50, 22.00),
            ("Limcee 500mg", "PH-DEM-004", 400, "LMC-D25-001", date(2027,1,31), 1.20, 1.50),
            ("Celin 500mg", "PH-DEM-004", 300, "CLN-D25-001", date(2027,2,15), 0.96, 1.20),
            # -- Winter wound care / skin --
            ("Savlon Cream", "PH-DEM-004", 40, "SVL-D25-001", date(2026,9,10), 36.00, 45.00),
        ]
        inv_map = {}
        for med_name, shop_code, qty, batch, exp, cost, sell in inv_data:
            inv = Inventory(
                med_id=med_map[med_name].id, shop_id=shop_map[shop_code].id,
                quantity=qty, batch_number=batch, expiry_date=exp,
                cost_price=cost, selling_price=sell, storage_location="Shelf-A1",
            )
            db.add(inv)
            db.flush()
            inv_map[(med_name, shop_code)] = inv
        logger.info(f"Inventory: {len(inv_data)} entries created")

        # ────────────────────────────────────────────────────────
        # 6. SHOP-STAFF ASSIGNMENTS
        # ────────────────────────────────────────────────────────
        for shop_code in ["PH-CEN-001", "PH-WST-002", "PH-NRT-003"]:
            ss = ShopStaff(user_id=pharmacist.id, shop_id=shop_map[shop_code].id,
                          assigned_date=date.today(), is_primary=(shop_code=="PH-CEN-001"))
            db.add(ss)
        ss_demo = ShopStaff(user_id=demo_user.id, shop_id=shop_map["PH-DEM-004"].id,
                           assigned_date=date.today(), is_primary=True)
        db.add(ss_demo)
        logger.info("Shop-staff assignments created")

        # ────────────────────────────────────────────────────────
        # 7. BILL HISTORY — 6 months of sales for Demo Pharmacy
        #    Oct 2025 to Mar 2026 (winter season)
        # ────────────────────────────────────────────────────────
        demo_shop = shop_map["PH-DEM-004"]
        demo_shop_id = demo_shop.id

        # Winter sales patterns:
        #   Oct 2025: moderate (season starting, cold wave beginning)
        #   Nov 2025: high (peak cold, flu season)
        #   Dec 2025: very high (peak winter, Christmas infections)
        #   Jan 2026: highest (New Year cold, fog, pneumonia)
        #   Feb 2026: high (post-winter lingering cold)
        #   Mar 2026: moderate (spring, declining)
        winter_sales_config = [
            # (month, num_bills, avg_items_per_bill)
            # Simulating increasing then decreasing seasonal demand
            (2025, 10, 55, 2.3),
            (2025, 11, 85, 2.6),
            (2025, 12, 110, 2.8),
            (2026, 1, 120, 2.9),
            (2026, 2, 90, 2.5),
            (2026, 3, 60, 2.2),
        ]

        # Medicines commonly sold per month with frequency weights
        # Higher weight = more likely to be picked
        winter_med_weights = {
            "Crocin 500mg": 9, "Dolo 650mg": 8, "Combiflam": 8,
            "Sinarest New": 7, "Vicks Action 500": 7,
            "Cetzine 10mg": 7, "Benadryl Cough Syrup": 6,
            "Ambrodil Syrup": 6, "Mox 500mg": 5,
            "Limcee 500mg": 6, "Electral Powder": 5,
            "Brufen 400mg": 5, "Calpol 500mg": 5,
            "P-650 Tablet": 4, "Corex Syrup": 4,
            "Mucolite Syrup": 3, "TusQ Dx Syrup": 3,
            "Azithral 500mg": 4, "Amoxil 500mg": 3,
            "Flexon MR": 3, "Celin 500mg": 4,
            "Savlon Cream": 2, "Zyrtec 10mg": 3,
            "Zithromax 500mg": 2,
        }

        # Weighted random medicine picker
        all_winter_meds = list(winter_med_weights.keys())
        med_weights = [winter_med_weights[m] for m in all_winter_meds]

        # Customer names pool (realistic Indian names)
        customers = [
            "Amit Sharma", "Sunita Devi", "Ravi Meena", "Priya Gupta",
            "Vikram Singh", "Anita Joshi", "Rakesh Verma", "Kavita Purohit",
            "Suresh Agarwal", "Meena Kumari", "Deepak Mali", "Pooja Sharma",
            "Arjun Patel", "Rekha Jain", "Mahesh Soni", "Suman Sharma",
            "Ramesh Kumar", "Sarla Devi", "Gopal Prajapat", "Lata Sharma",
            "Manish Gupta", "Usha Devi", "Kiran Meena", "Dinesh Verma",
            "Neelam Joshi", "Rajendra Sharma", "Pushpa Devi", "Hari Mohan",
            "Kamlesh Mali", "Geeta Devi", "Naresh Prajapat", "Saroj Kumari",
            "Pankaj Sharma", "Shanti Devi", "Ashok Verma", "Bimla Devi",
            "Sunil Jain", "Sushila Devi", "Mohan Lal", "Kamla Devi",
        ]
        doctor_names = [
            "Dr. A. Sharma", "Dr. R. Gupta", "Dr. S. Jain", "Dr. P. Meena",
            "Dr. K. Soni", None, None, None,  # many walk-ins without doctor
        ]
        payment_methods = ["cash", "cash", "cash", "upi", "upi", "card"]  # cash dominant

        bill_count = 0
        for yr, mon, num_bills, avg_items in winter_sales_config:
            for _ in range(num_bills):
                days_in_month = 30 if mon in [4, 6, 9, 11] else 31 if mon != 2 else 28
                bill_day = random.randint(1, days_in_month)
                bill_hour = random.randint(8, 21)
                bill_minute = random.randint(0, 59)
                bill_dt = datetime(yr, mon, bill_day, bill_hour, bill_minute, 0,
                                   tzinfo=timezone.utc)

                inv_num = f"MED-{yr}{mon:02d}{bill_day:02d}-{bill_count+1:04d}"

                # Pick items for this bill
                num_items = max(1, int(random.gauss(avg_items, 0.8)))
                num_items = min(num_items, 5)
                chosen_meds = random.choices(all_winter_meds, weights=med_weights, k=num_items)
                chosen_meds = list(set(chosen_meds))  # deduplicate

                customer = random.choice(customers)
                doctor = random.choice(doctor_names)
                pay_method = random.choice(payment_methods)

                items = []
                subtotal = 0.0
                for med_name in chosen_meds:
                    inv_key = (med_name, "PH-DEM-004")
                    inv_record = inv_map.get(inv_key)
                    if not inv_record:
                        continue
                    med = med_map[med_name]
                    # Find salt name by matching med's salt_id to salt objects
                    salt_name = None
                    for sn, so in salt_map.items():
                        if so.id == med.salt_id:
                            salt_name = so.formula_name
                            break
                    qty = random.choices([1, 2, 3, 5, 10], weights=[30, 30, 20, 15, 5])[0]
                    unit_price = inv_record.selling_price
                    item_total = qty * unit_price
                    gst_rate = 5.0 if med.unit_price < 20 else 12.0
                    gst_amount = round(item_total * gst_rate / 100, 2)
                    item_total_with_gst = round(item_total + gst_amount, 2)

                    bi = BillItem(
                        med_id=med.id,
                        inventory_id=inv_record.id,
                        medicine_name=med.brand_name,
                        salt_name=salt_name,
                        batch_number=inv_record.batch_number,
                        expiry_date=str(inv_record.expiry_date),
                        quantity=qty,
                        unit_price=unit_price,
                        cost_price=inv_record.cost_price,
                        item_total=item_total_with_gst,
                        discount=0.0,
                        gst_rate=gst_rate,
                        gst_amount=gst_amount,
                    )
                    items.append(bi)
                    subtotal += item_total

                if not items:
                    continue

                # Calculate totals
                discount_pct = random.choice([0, 0, 0, 0, 5, 10, 5, 0, 0, 0])  # 10% chance of discount
                discount_amt = round(subtotal * discount_pct / 100, 2)
                after_discount = subtotal - discount_amt
                cgst = round(after_discount * 0.05, 2)  # approx CGST
                sgst = round(after_discount * 0.05, 2)  # approx SGST
                total = round(after_discount + cgst + sgst, 2)

                bill = Bill(
                    invoice_number=inv_num,
                    shop_id=demo_shop_id,
                    created_by=demo_user.id,
                    customer_name=customer,
                    doctor_name=doctor,
                    subtotal=round(subtotal, 2),
                    discount_amount=discount_amt,
                    discount_percent=discount_pct if discount_pct > 0 else None,
                    cgst_amount=cgst,
                    sgst_amount=sgst,
                    total_amount=total,
                    amount_paid=total,
                    status=BillStatus.PAID.value,
                    payment_method=pay_method,
                )
                bill.items = items

                # Manually set created_at for historical data
                from app.core.mixins import TimestampMixin
                db.add(bill)
                db.flush()

                # Update timestamps to historical dates
                db.execute(
                    __import__('sqlalchemy').text(
                        f"UPDATE bills SET created_at='{bill_dt.isoformat()}' WHERE id={bill.id}"
                    )
                )
                for bi in items:
                    db.execute(
                        __import__('sqlalchemy').text(
                            f"UPDATE bill_items SET created_at='{bill_dt.isoformat()}' WHERE id={bi.id}"
                        )
                    )

                bill_count += 1

        db.commit()
        total_revenue = sum(
            float(row[0]) for row in
            db.execute(__import__('sqlalchemy').text(
                f"SELECT total_amount FROM bills WHERE shop_id={demo_shop_id}"
            )).fetchall()
        )
        logger.info(
            f"Auto-seed complete: 3 users, {len(salt_map)} salts, {len(med_map)} medicines, "
            f"{len(shop_map)} shops, {len(inv_data)} inventory items, "
            f"{bill_count} bills ({total_revenue:.0f} total revenue for demo pharmacy)"
        )
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
