"""
MediSebi — Medicine Master Catalog
====================================
A predefined catalog of 60+ common medicines found in a typical Indian dispensary.
Used for quick-add to shop inventory without manual entry.

Categories: Analgesics, Antibiotics, Antacids, Anti-allergic, Cough & Cold,
Vitamins & Supplements, ORS & Electrolytes, Antidiabetic, Antihypertensive,
Dermatology, Ophthalmology, Gastrointestinal, Anti-inflammatory, Antipyretic.

Each medicine links to a salt (existing or auto-created) for the substitution engine.
"""

MEDICINE_CATALOG = [
    # ── ANALGESICS & ANTIPIRETICS ──────────────────────────────
    {"brand_name": "Dolo 650", "salt_name": "Paracetamol", "category": "Analgesic", "strength": "650mg", "form": "Tablet", "manufacturer": "Micro Labs", "price": 28.00, "temp_sensitive": False, "abc_class": "A", "reorder": 200, "safety_stock": 100, "critical": 50},
    {"brand_name": "Crocin Advance", "salt_name": "Paracetamol", "category": "Analgesic", "strength": "500mg", "form": "Tablet", "manufacturer": "GSK", "price": 30.00, "temp_sensitive": False, "abc_class": "A", "reorder": 200, "safety_stock": 100, "critical": 50},
    {"brand_name": "Calpol 500", "salt_name": "Paracetamol", "category": "Analgesic", "strength": "500mg", "form": "Syrup 60ml", "manufacturer": "GSK", "price": 58.00, "temp_sensitive": False, "abc_class": "A", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Combiflam", "salt_name": "Ibuprofen + Paracetamol", "category": "Analgesic", "strength": "400mg/325mg", "form": "Tablet", "manufacturer": "Sanofi", "price": 38.00, "temp_sensitive": False, "abc_class": "A", "reorder": 150, "safety_stock": 75, "critical": 30},
    {"brand_name": "Brufen 400", "salt_name": "Ibuprofen", "category": "Analgesic", "strength": "400mg", "form": "Tablet", "manufacturer": "Abbott", "price": 32.00, "temp_sensitive": False, "abc_class": "A", "reorder": 100, "safety_stock": 50, "critical": 25},
    {"brand_name": "Voveran 50", "salt_name": "Diclofenac Sodium", "category": "Analgesic", "strength": "50mg", "form": "Tablet", "manufacturer": "Novartis", "price": 36.00, "temp_sensitive": False, "abc_class": "B", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Nise 100", "salt_name": "Nimesulide", "category": "Analgesic", "strength": "100mg", "form": "Tablet", "manufacturer": "Panacea Biotec", "price": 42.00, "temp_sensitive": False, "abc_class": "B", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Saridon", "salt_name": "Propyphenazone + Paracetamol + Caffeine", "category": "Analgesic", "strength": "150mg/250mg/50mg", "form": "Tablet", "manufacturer": "Bayer", "price": 22.00, "temp_sensitive": False, "abc_class": "C", "reorder": 50, "safety_stock": 25, "critical": 10},

    # ── ANTIBIOTICS ───────────────────────────────────────────
    {"brand_name": "Augmentin 625", "salt_name": "Amoxicillin + Clavulanic Acid", "category": "Antibiotic", "strength": "500mg/125mg", "form": "Tablet", "manufacturer": "GSK", "price": 228.00, "temp_sensitive": False, "abc_class": "A", "reorder": 100, "safety_stock": 50, "critical": 25},
    {"brand_name": "Mox 500", "salt_name": "Amoxicillin", "category": "Antibiotic", "strength": "500mg", "form": "Capsule", "manufacturer": "Sun Pharma", "price": 62.00, "temp_sensitive": False, "abc_class": "A", "reorder": 150, "safety_stock": 75, "critical": 30},
    {"brand_name": "Azithral 500", "salt_name": "Azithromycin", "category": "Antibiotic", "strength": "500mg", "form": "Tablet", "manufacturer": "Alembic Pharma", "price": 102.00, "temp_sensitive": False, "abc_class": "A", "reorder": 60, "safety_stock": 30, "critical": 15},
    {"brand_name": "Ciplox 500", "salt_name": "Ciprofloxacin", "category": "Antibiotic", "strength": "500mg", "form": "Tablet", "manufacturer": "Cipla", "price": 58.00, "temp_sensitive": False, "abc_class": "A", "reorder": 100, "safety_stock": 50, "critical": 25},
    {"brand_name": "Doxy 100", "salt_name": "Doxycycline", "category": "Antibiotic", "strength": "100mg", "form": "Capsule", "manufacturer": "J.B. Chemicals", "price": 48.00, "temp_sensitive": True, "abc_class": "A", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Metrogyl 400", "salt_name": "Metronidazole", "category": "Antibiotic", "strength": "400mg", "form": "Tablet", "manufacturer": "J.B. Chemicals", "price": 32.00, "temp_sensitive": False, "abc_class": "B", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Clavamox 375", "salt_name": "Amoxicillin + Clavulanic Acid", "category": "Antibiotic", "strength": "250mg/125mg", "form": "Suspension 30ml", "manufacturer": "GSK", "price": 128.00, "temp_sensitive": True, "abc_class": "A", "reorder": 40, "safety_stock": 20, "critical": 10},

    # ── ANTIALLERGIC ──────────────────────────────────────────
    {"brand_name": "Cetzine", "salt_name": "Cetirizine", "category": "Anti-allergic", "strength": "10mg", "form": "Tablet", "manufacturer": "Dr Reddy's", "price": 25.00, "temp_sensitive": False, "abc_class": "B", "reorder": 100, "safety_stock": 50, "critical": 25},
    {"brand_name": "Allegra 120", "salt_name": "Fexofenadine", "category": "Anti-allergic", "strength": "120mg", "form": "Tablet", "manufacturer": "Sanofi", "price": 78.00, "temp_sensitive": False, "abc_class": "B", "reorder": 60, "safety_stock": 30, "critical": 15},
    {"brand_name": "Avil 25", "salt_name": "Pheniramine Maleate", "category": "Anti-allergic", "strength": "25mg", "form": "Tablet", "manufacturer": "Sanofi", "price": 18.00, "temp_sensitive": False, "abc_class": "C", "reorder": 80, "safety_stock": 40, "critical": 20},

    # ── COUGH & COLD ────────────────────────────────────────────
    {"brand_name": "Benadryl", "salt_name": "Diphenhydramine", "category": "Cough & Cold", "strength": "25mg", "form": "Syrup 100ml", "manufacturer": "Johnson & Johnson", "price": 72.00, "temp_sensitive": True, "abc_class": "B", "reorder": 60, "safety_stock": 30, "critical": 15},
    {"brand_name": "Honitus", "salt_name": "Dextromethorphan + Phenylephrine", "category": "Cough & Cold", "strength": "10mg/5mg", "form": "Syrup 60ml", "manufacturer": "Mankind Pharma", "price": 85.00, "temp_sensitive": False, "abc_class": "B", "reorder": 60, "safety_stock": 30, "critical": 15},
    {"brand_name": "Vicks Action 500", "salt_name": "Paracetamol + Phenylephrine + Caffeine", "category": "Cough & Cold", "strength": "500mg/10mg/30mg", "form": "Tablet", "manufacturer": "P&G", "price": 30.00, "temp_sensitive": False, "abc_class": "B", "reorder": 100, "safety_stock": 50, "critical": 25},
    {"brand_name": "Sinarest", "salt_name": "Paracetamol + Chlorpheniramine + Phenylephrine", "category": "Cough & Cold", "strength": "500mg/2mg/10mg", "form": "Tablet", "manufacturer": "Centaur Pharma", "price": 26.00, "temp_sensitive": False, "abc_class": "C", "reorder": 100, "safety_stock": 50, "critical": 25},

    # ── GASTROINTESTINAL ──────────────────────────────────────
    {"brand_name": "Pan 40", "salt_name": "Pantoprazole", "category": "Gastrointestinal", "strength": "40mg", "form": "Tablet", "manufacturer": "Alkem Labs", "price": 68.00, "temp_sensitive": False, "abc_class": "A", "reorder": 150, "safety_stock": 75, "critical": 30},
    {"brand_name": "Gelusil MPS", "salt_name": "Magaldrate + Simethicone", "category": "Gastrointestinal", "strength": "480mg/40mg", "form": "Syrup 170ml", "manufacturer": "Pfizer", "price": 118.00, "temp_sensitive": False, "abc_class": "B", "reorder": 40, "safety_stock": 20, "critical": 10},
    {"brand_name": "Imodium", "salt_name": "Loperamide", "category": "Gastrointestinal", "strength": "2mg", "form": "Capsule", "manufacturer": "Janssen", "price": 32.00, "temp_sensitive": False, "abc_class": "B", "reorder": 60, "safety_stock": 30, "critical": 15},
    {"brand_name": "ORS Electral", "salt_name": "Oral Rehydration Salts", "category": "ORS", "strength": "21.8g sachet", "form": "Powder", "manufacturer": "FDC Ltd", "price": 22.00, "temp_sensitive": False, "abc_class": "A", "reorder": 300, "safety_stock": 100, "critical": 50},
    {"brand_name": "Econorm", "salt_name": "Bacillus Clausii", "category": "Gastrointestinal", "strength": "2 billion spores", "form": "Sachet", "manufacturer": "Dr Reddy's", "price": 55.00, "temp_sensitive": True, "abc_class": "B", "reorder": 40, "safety_stock": 20, "critical": 10},
    {"brand_name": "Ranitidine 150", "salt_name": "Ranitidine", "category": "Gastrointestinal", "strength": "150mg", "form": "Tablet", "manufacturer": "Cipla", "price": 20.00, "temp_sensitive": False, "abc_class": "B", "reorder": 100, "safety_stock": 50, "critical": 25},

    # ── VITAMINS & SUPPLEMENTS ─────────────────────────────────
    {"brand_name": "Limcee", "salt_name": "Ascorbic Acid (Vitamin C)", "category": "Vitamins", "strength": "500mg", "form": "Chewable Tablet", "manufacturer": "Abbott", "price": 16.00, "temp_sensitive": False, "abc_class": "C", "reorder": 100, "safety_stock": 50, "critical": 25},
    {"brand_name": "Shelcal 500", "salt_name": "Calcium + Vitamin D3", "category": "Vitamins", "strength": "500mg/250IU", "form": "Tablet", "manufacturer": "Torrent Pharma", "price": 82.00, "temp_sensitive": False, "abc_class": "B", "reorder": 60, "safety_stock": 30, "critical": 15},
    {"brand_name": "Becosules", "salt_name": "Vitamin B Complex", "category": "Vitamins", "strength": "B1+B2+B6+B12+Niacinamide+Folic Acid", "form": "Capsule", "manufacturer": "Pfizer", "price": 32.00, "temp_sensitive": True, "abc_class": "C", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Zincovit", "salt_name": "Zinc + Vitamin C", "category": "Vitamins", "strength": "50mg/250mg", "form": "Tablet", "manufacturer": "Apex Labs", "price": 48.00, "temp_sensitive": False, "abc_class": "B", "reorder": 60, "safety_stock": 30, "critical": 15},
    {"brand_name": "D-Rise 60K", "salt_name": "Cholecalciferol (Vitamin D3)", "category": "Vitamins", "strength": "60,000 IU", "form": "Granules 4 sachets", "manufacturer": "USV Ltd", "price": 135.00, "temp_sensitive": True, "abc_class": "B", "reorder": 40, "safety_stock": 20, "critical": 10},

    # ── ANTIDIABETIC ────────────────────────────────────────────
    {"brand_name": "Glycomet 500", "salt_name": "Metformin", "category": "Antidiabetic", "strength": "500mg", "form": "Tablet", "manufacturer": "USV Ltd", "price": 18.00, "temp_sensitive": False, "abc_class": "A", "reorder": 200, "safety_stock": 100, "critical": 50},
    {"brand_name": "Glimepiride 2", "salt_name": "Glimepiride", "category": "Antidiabetic", "strength": "2mg", "form": "Tablet", "manufacturer": "Sun Pharma", "price": 35.00, "temp_sensitive": False, "abc_class": "A", "reorder": 100, "safety_stock": 50, "critical": 25},
    {"brand_name": "Human Mixtard 30/70", "salt_name": "Insulin (Biphasic)", "category": "Antidiabetic", "strength": "100IU/ml", "form": "Penfill 10ml", "manufacturer": "Novo Nordisk", "price": 375.00, "temp_sensitive": True, "abc_class": "A", "reorder": 30, "safety_stock": 15, "critical": 10},

    # ── ANTIHYPERTENSIVE ───────────────────────────────────────
    {"brand_name": "Telma 40", "salt_name": "Telmisartan", "category": "Antihypertensive", "strength": "40mg", "form": "Tablet", "manufacturer": "Glenmark", "price": 42.00, "temp_sensitive": False, "abc_class": "A", "reorder": 150, "safety_stock": 75, "critical": 30},
    {"brand_name": "Amlong 5", "salt_name": "Amlodipine", "category": "Antihypertensive", "strength": "5mg", "form": "Tablet", "manufacturer": "Micro Labs", "price": 25.00, "temp_sensitive": False, "abc_class": "A", "reorder": 150, "safety_stock": 75, "critical": 30},
    {"brand_name": "Atorva 10", "salt_name": "Atorvastatin", "category": "Antihypertensive", "strength": "10mg", "form": "Tablet", "manufacturer": "Zydus Cadila", "price": 72.00, "temp_sensitive": False, "abc_class": "A", "reorder": 100, "safety_stock": 50, "critical": 25},

    # ── DERMATOLOGY ────────────────────────────────────────────
    {"brand_name": "Betadine", "salt_name": "Povidone Iodine", "category": "Dermatology", "strength": "5%", "form": "Ointment 15g", "manufacturer": "Win-Medicare", "price": 62.00, "temp_sensitive": False, "abc_class": "B", "reorder": 50, "safety_stock": 25, "critical": 10},
    {"brand_name": "Candid-B", "salt_name": "Clotrimazole + Beclometasone", "category": "Dermatology", "strength": "1%/0.025%", "form": "Cream 15g", "manufacturer": "Glenmark", "price": 88.00, "temp_sensitive": False, "abc_class": "B", "reorder": 40, "safety_stock": 20, "critical": 10},
    {"brand_name": "Soframycin", "salt_name": "Framycetin", "category": "Dermatology", "strength": "1%", "form": "Skin Cream 30g", "manufacturer": "Sanofi", "price": 62.00, "temp_sensitive": False, "abc_class": "B", "reorder": 50, "safety_stock": 25, "critical": 10},
    {"brand_name": "DermiCool", "salt_name": "Menthol + Camphor", "category": "Dermatology", "strength": "0.5%/0.5%", "form": "Cream 20g", "manufacturer": "Dr Morepen", "price": 45.00, "temp_sensitive": False, "abc_class": "C", "reorder": 60, "safety_stock": 30, "critical": 15},
    {"brand_name": "Four Derm", "salt_name": "Mometasone Furoate", "category": "Dermatology", "strength": "0.1%", "form": "Cream 10g", "manufacturer": "Glenmark", "price": 78.00, "temp_sensitive": False, "abc_class": "B", "reorder": 30, "safety_stock": 15, "critical": 8},

    # ── OPHTHALMOLOGY ─────────────────────────────────────────
    {"brand_name": "Refresh Tears", "salt_name": "Carboxymethylcellulose", "category": "Ophthalmology", "strength": "0.5%", "form": "Eye Drops 10ml", "manufacturer": "Allergan", "price": 108.00, "temp_sensitive": True, "abc_class": "B", "reorder": 40, "safety_stock": 20, "critical": 10},
    {"brand_name": "Ciprodex", "salt_name": "Ciprofloxacin + Dexamethasone", "category": "Ophthalmology", "strength": "0.3%/0.1%", "form": "Eye Drops 5ml", "manufacturer": "Novartis", "price": 132.00, "temp_sensitive": True, "abc_class": "B", "reorder": 30, "safety_stock": 15, "critical": 8},
    {"brand_name": "Gatiflox", "salt_name": "Gatifloxacin", "category": "Ophthalmology", "strength": "0.3%", "form": "Eye Drops 5ml", "manufacturer": "Allergan", "price": 98.00, "temp_sensitive": True, "abc_class": "B", "reorder": 30, "safety_stock": 15, "critical": 8},

    # ── ANTI-INFLAMMATORY / NSAIDS ─────────────────────────────
    {"brand_name": "Naprosyn 250", "salt_name": "Naproxen", "category": "Anti-inflammatory", "strength": "250mg", "form": "Tablet", "manufacturer": "Sanofi", "price": 45.00, "temp_sensitive": False, "abc_class": "B", "reorder": 60, "safety_stock": 30, "critical": 15},
    {"brand_name": "Etorica 90", "salt_name": "Etoricoxib", "category": "Anti-inflammatory", "strength": "90mg", "form": "Tablet", "manufacturer": "Zydus Cadila", "price": 108.00, "temp_sensitive": False, "abc_class": "A", "reorder": 60, "safety_stock": 30, "critical": 15},
    {"brand_name": "Aceclofenac 100", "salt_name": "Aceclofenac", "category": "Anti-inflammatory", "strength": "100mg", "form": "Tablet", "manufacturer": "Intas Pharma", "price": 28.00, "temp_sensitive": False, "abc_class": "B", "reorder": 100, "safety_stock": 50, "critical": 25},

    # ── ANTISPASMODIC ──────────────────────────────────────────
    {"brand_name": "Cyclopam", "salt_name": "Dicyclomine + Paracetamol", "category": "Antispasmodic", "strength": "20mg/500mg", "form": "Tablet", "manufacturer": "Wockhardt", "price": 38.00, "temp_sensitive": False, "abc_class": "B", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Colospa 135", "salt_name": "Mebeverine", "category": "Antispasmodic", "strength": "135mg", "form": "Tablet", "manufacturer": "Abbott", "price": 68.00, "temp_sensitive": False, "abc_class": "B", "reorder": 50, "safety_stock": 25, "critical": 12},

    # ── ANTIEMETIC ─────────────────────────────────────────────
    {"brand_name": "Emset 4", "salt_name": "Ondansetron", "category": "Antiemetic", "strength": "4mg", "form": "Tablet", "manufacturer": "Cipla", "price": 42.00, "temp_sensitive": False, "abc_class": "A", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Domperidone 10", "salt_name": "Domperidone", "category": "Antiemetic", "strength": "10mg", "form": "Tablet", "manufacturer": "Intas Pharma", "price": 18.00, "temp_sensitive": False, "abc_class": "C", "reorder": 80, "safety_stock": 40, "critical": 20},

    # ── MISC COMMON ───────────────────────────────────────────
    {"brand_name": "Crocin Cold & Flu", "salt_name": "Paracetamol + Phenylephrine + Chlorpheniramine", "category": "Cough & Cold", "strength": "500mg/10mg/2mg", "form": "Tablet", "manufacturer": "GSK", "price": 35.00, "temp_sensitive": False, "abc_class": "B", "reorder": 100, "safety_stock": 50, "critical": 25},
    {"brand_name": "Mucaine Gel", "salt_name": "Oxetacaine + Aluminium", "category": "Gastrointestinal", "strength": "20mg/145mg", "form": "Gel 15g", "manufacturer": "P&G", "price": 55.00, "temp_sensitive": False, "abc_class": "C", "reorder": 40, "safety_stock": 20, "critical": 10},
    {"brand_name": "Strepsils", "salt_name": "Amylmetacresol + Dichlorobenzyl Alcohol", "category": "Cough & Cold", "strength": "600mcg/1.2mg", "form": "Lozenges", "manufacturer": "Reckitt", "price": 28.00, "temp_sensitive": False, "abc_class": "C", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Streptomycin 500", "salt_name": "Streptomycin", "category": "Antibiotic", "strength": "500mg", "form": "Injection 1ml", "manufacturer": "Hindustan Antibiotics", "price": 25.00, "temp_sensitive": True, "abc_class": "C", "reorder": 30, "safety_stock": 15, "critical": 8},
    {"brand_name": "Amoxyclav 625 Duo", "salt_name": "Amoxicillin + Clavulanic Acid", "category": "Antibiotic", "strength": "500mg/125mg", "form": "Tablet", "manufacturer": "Cipla", "price": 178.00, "temp_sensitive": False, "abc_class": "A", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Disprin", "salt_name": "Aspirin", "category": "Analgesic", "strength": "350mg", "form": "Tablet", "manufacturer": "Reckitt", "price": 12.00, "temp_sensitive": False, "abc_class": "C", "reorder": 80, "safety_stock": 40, "critical": 20},
    {"brand_name": "Lopamide", "salt_name": "Loperamide", "category": "Gastrointestinal", "strength": "2mg", "form": "Capsule", "manufacturer": "Cipla", "price": 15.00, "temp_sensitive": False, "abc_class": "C", "reorder": 60, "safety_stock": 30, "critical": 15},
]

# ── Demo Stores (8 pharmacies across India) ───────────────────
DEMO_STORES = [
    {"name": "MediSebi Central", "code": "PH-CEN-001", "city": "Mumbai", "state": "Maharashtra", "address": "123 Marine Drive, Fort, Mumbai 400001", "pincode": "400001", "lat": 18.9434, "lon": 72.8235, "phone": "+91-22-12345678", "email": "central@medisebi.com", "capacity": 50000},
    {"name": "MediSebi West", "code": "PH-WST-002", "city": "Mumbai", "state": "Maharashtra", "address": "456 Linking Road, Bandra, Mumbai 400050", "pincode": "400050", "lat": 19.0596, "lon": 72.8295, "phone": "+91-22-23456789", "email": "west@medisebi.com", "capacity": 30000},
    {"name": "MediSebi North", "code": "PH-NRT-003", "city": "Delhi", "state": "Delhi NCR", "address": "789 Connaught Place, New Delhi 110001", "pincode": "110001", "lat": 28.6315, "lon": 77.2167, "phone": "+91-11-34567890", "email": "north@medisebi.com", "capacity": 40000},
    {"name": "MediSebi South", "code": "PH-STH-004", "city": "Delhi", "state": "Delhi NCR", "address": "321 Greater Kailash, New Delhi 110048", "pincode": "110048", "lat": 28.5494, "lon": 77.2001, "phone": "+91-11-45678901", "email": "south@medisebi.com", "capacity": 35000},
    {"name": "MediSebi Koramangala", "code": "PH-KOR-005", "city": "Bangalore", "state": "Karnataka", "address": "567 100 Feet Road, Koramangala, Bangalore 560034", "pincode": "560034", "lat": 12.9352, "lon": 77.6245, "phone": "+91-80-56789012", "email": "kormangala@medisebi.com", "capacity": 35000},
    {"name": "MediSebi Whitefield", "code": "PH-WHT-006", "city": "Bangalore", "state": "Karnataka", "address": "890 ITPL Main Road, Whitefield, Bangalore 560066", "pincode": "560066", "lat": 12.9698, "lon": 77.7500, "phone": "+91-80-67890123", "email": "whitefield@medisebi.com", "capacity": 30000},
    {"name": "MediSebi T. Nagar", "code": "PH-TNG-007", "city": "Chennai", "state": "Tamil Nadu", "address": "234 Usman Road, T. Nagar, Chennai 600017", "pincode": "600017", "lat": 13.0418, "lon": 80.2341, "phone": "+91-44-78901234", "email": "tnagar@medisebi.com", "capacity": 25000},
    {"name": "MediSebi Salt Lake", "code": "PH-SLK-008", "city": "Kolkata", "state": "West Bengal", "address": "456 Sector V, Salt Lake, Kolkata 700091", "pincode": "700091", "lat": 22.5726, "lon": 88.3639, "phone": "+91-33-89012345", "email": "saltlake@medisebi.com", "capacity": 30000},
]


def get_catalog_by_category():
    """Return catalog grouped by category."""
    cats = {}
    for med in MEDICINE_CATALOG:
        cat = med["category"]
        if cat not in cats:
            cats[cat] = []
        cats[cat].append(med)
    return cats


def search_catalog(query: str = "", category: str = ""):
    """Search catalog by name, salt, or category."""
    query = query.lower()
    results = []
    for med in MEDICINE_CATALOG:
        if category and med["category"] != category:
            continue
        if query:
            if (query in med["brand_name"].lower() or
                query in med["salt_name"].lower() or
                query in med["category"].lower() or
                query in med["manufacturer"].lower()):
                results.append(med)
        else:
            results.append(med)
    return results
