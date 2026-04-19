"""
MediSebi — Schema Visualization Generator
===========================================
Generates a Mermaid ER diagram and a visual PNG of the database schema.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import os

def generate_er_diagram():
    """Generate a visual ER diagram of the MediSebi database schema."""

    fig, ax = plt.subplots(1, 1, figsize=(22, 18))
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 18)
    ax.axis("off")
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")

    title = ax.text(11, 17.3, "MediSebi — Database Schema (ER Diagram)",
                    fontsize=20, fontweight="bold", color="#e2e8f0",
                    ha="center", va="center", fontfamily="monospace")

    subtitle = ax.text(11, 16.8,
                       "AI-Driven Healthcare Supply Intelligence & Redistribution Platform",
                       fontsize=11, color="#94a3b8", ha="center", va="center",
                       fontfamily="monospace", style="italic")

    tables = [
        {
            "name": "users",
            "x": 1, "y": 9,
            "color": "#3b82f6",
            "fields": [
                "PK  id (INT)",
                "    username (VARCHAR 50)",
                "    email (VARCHAR 255)",
                "    password_hash (VARCHAR 255)",
                "    full_name (VARCHAR 100)",
                "    role (ENUM: admin/pharmacist)",
                "    is_locked (BOOLEAN)",
                "    is_active (BOOLEAN)",
                "    created_at / updated_at",
            ]
        },
        {
            "name": "salts",
            "x": 8, "y": 13.5,
            "color": "#10b981",
            "fields": [
                "PK  id (INT)",
                "    formula_name (VARCHAR 100)",
                "    category (VARCHAR 50)",
                "    atc_code (VARCHAR 20)",
                "    dosage_form (VARCHAR 50)",
                "    standard_strength (VARCHAR 50)",
                "    is_active (BOOLEAN)",
                "    created_at / updated_at",
            ]
        },
        {
            "name": "shops",
            "x": 15, "y": 9,
            "color": "#f59e0b",
            "fields": [
                "PK  id (INT)",
                "    name (VARCHAR 150)",
                "    code (VARCHAR 20, UNIQUE)",
                "    city (VARCHAR 100, INDEXED)",
                "    latitude / longitude (FLOAT)",
                "    storage_capacity (INT)",
                "    is_active (BOOLEAN)",
                "    created_at / updated_at",
            ]
        },
        {
            "name": "medicines",
            "x": 8, "y": 5.5,
            "color": "#8b5cf6",
            "fields": [
                "PK  id (INT)",
                "    brand_name (VARCHAR 150)",
                "FK  salt_id → salts.id",
                "    manufacturer (VARCHAR 150)",
                "    strength (VARCHAR 50)",
                "    unit_price (FLOAT)",
                "    temperature_sensitive (BOOL)",
                "    is_active (BOOLEAN)",
                "    created_at / updated_at",
            ]
        },
        {
            "name": "inventory",
            "x": 1, "y": 0.5,
            "color": "#ef4444",
            "fields": [
                "PK  id (INT)",
                "FK  med_id → medicines.id",
                "FK  shop_id → shops.id",
                "    quantity (INT)",
                "    batch_number (VARCHAR 50)",
                "    expiry_date (DATE, INDEXED)",
                "    cost_price / selling_price",
                "    is_reserved (BOOLEAN)",
                "    created_at / updated_at",
            ]
        },
        {
            "name": "audit_logs",
            "x": 8, "y": 0.5,
            "color": "#dc2626",
            "fields": [
                "PK  id (INT)",
                "    action_type (ENUM, 17 types)",
                "    description (TEXT)",
                "    details (TEXT, JSON payload)",
                "FK  user_id → users.id",
                "    ip_address (VARCHAR 45)",
                "    resource_type / resource_id",
                "    sha256_hash (VARCHAR 64)",
                "    created_at / updated_at",
            ]
        },
        {
            "name": "shop_staff",
            "x": 15, "y": 4,
            "color": "#06b6d4",
            "fields": [
                "PK  id (INT)",
                "FK  user_id → users.id",
                "FK  shop_id → shops.id",
                "    assigned_date (DATE)",
                "    is_primary (BOOLEAN)",
                "    created_at / updated_at",
            ]
        },
        {
            "name": "stock_transfer_requests",
            "x": 15, "y": 0.2,
            "color": "#f97316",
            "fields": [
                "PK  id (INT)",
                "FK  from_shop_id → shops.id",
                "FK  to_shop_id → shops.id",
                "FK  med_id → medicines.id",
                "FK  inventory_id → inventory.id",
                "    quantity_requested (INT)",
                "    status (ENUM: 6 states)",
                "    priority (ENUM: 4 levels)",
                "    created_at / updated_at",
            ]
        },
        {
            "name": "demand_forecasts",
            "x": 1, "y": 13.5,
            "color": "#a855f7",
            "fields": [
                "PK  id (INT)",
                "FK  med_id → medicines.id",
                "FK  shop_id → shops.id",
                "    prediction_date (DATE)",
                "    predicted_demand (FLOAT)",
                "    current_stock (INT)",
                "    stock_deficit (INT)",
                "    confidence_score (FLOAT)",
                "    created_at / updated_at",
            ]
        },
        {
            "name": "climate_alerts",
            "x": 15, "y": 13.5,
            "color": "#14b8a6",
            "fields": [
                "PK  id (INT)",
                "FK  shop_id → shops.id",
                "    city (VARCHAR 100)",
                "    temperature_c (FLOAT)",
                "    humidity_pct (FLOAT)",
                "    risk_level (ENUM: 4 levels)",
                "    disease_risk (VARCHAR 100)",
                "    recommended_salts (TEXT)",
                "    created_at / updated_at",
            ]
        },
    ]

    for table in tables:
        name = table["name"]
        x, y = table["x"], table["y"]
        color = table["color"]
        fields = table["fields"]

        num_fields = len(fields)
        row_h = 0.38
        header_h = 0.55
        total_h = header_h + num_fields * row_h + 0.15
        w = 5.5

        # Table background
        rect = FancyBboxPatch(
            (x, y), w, total_h,
            boxstyle="round,pad=0.1",
            facecolor="#1e293b",
            edgecolor=color,
            linewidth=2,
            alpha=0.95,
        )
        ax.add_patch(rect)

        # Header background
        header_rect = FancyBboxPatch(
            (x + 0.05, y + total_h - header_h + 0.05), w - 0.1, header_h - 0.1,
            boxstyle="round,pad=0.08",
            facecolor=color,
            edgecolor="none",
            alpha=0.9,
        )
        ax.add_patch(header_rect)

        # Table name
        ax.text(x + w / 2, y + total_h - header_h / 2 + 0.02, name.upper(),
                fontsize=11, fontweight="bold", color="white",
                ha="center", va="center", fontfamily="monospace")

        # Fields
        for i, field in enumerate(fields):
            fy = y + total_h - header_h - 0.15 - i * row_h - row_h / 2
            is_pk = field.startswith("PK")
            is_fk = field.startswith("FK")
            if is_pk:
                fc = "#fbbf24"
                fw = "bold"
            elif is_fk:
                fc = "#60a5fa"
                fw = "normal"
            else:
                fc = "#cbd5e1"
                fw = "normal"
            ax.text(x + 0.25, fy, field, fontsize=7, color=fc,
                    va="center", fontfamily="monospace", fontweight=fw)

    # ── Relationship Lines ──────────────────────────────────────
    def draw_rel(x1, y1, x2, y2, label="", color="#475569"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                     arrowprops=dict(arrowstyle="->", color=color, lw=1.5,
                                     connectionstyle="arc3,rad=0.05"))
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my + 0.15, label, fontsize=6, color="#94a3b8",
                    ha="center", fontfamily="monospace", style="italic",
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="#0f172a",
                              edgecolor="none", alpha=0.8))

    # users → audit_logs
    draw_rel(3.75, 10.5, 8, 5.5, "1:N")
    # users → shop_staff
    draw_rel(4, 11, 15, 5.5, "M:N")

    # salts → medicines
    draw_rel(10.75, 13.5, 10.75, 10.7, "1:N")

    # medicines → inventory
    draw_rel(8, 7.5, 4.5, 5.5, "1:N")

    # shops → inventory
    draw_rel(15, 9, 6.5, 3.5, "1:N")

    # shops → shop_staff
    draw_rel(15, 7.5, 17.75, 6.5, "1:N")

    # shops → stock_transfer_requests
    draw_rel(17.75, 4, 17.75, 2.7, "1:N")
    draw_rel(19, 4, 19, 2.7, "1:N")

    # shops → climate_alerts
    draw_rel(17.75, 12, 17.75, 14, "1:N")

    # Legend
    legend_items = [
        ("Primary Key", "#fbbf24"),
        ("Foreign Key", "#60a5fa"),
        ("Indexed Field", "#cbd5e1"),
        ("1:N Relationship", "#475569"),
    ]
    for i, (label, color) in enumerate(legend_items):
        lx = 1 + i * 3.5
        ly = 17.0
        ax.plot(lx, ly, "s", color=color, markersize=8)
        ax.text(lx + 0.3, ly, label, fontsize=8, color="#94a3b8",
                va="center", fontfamily="monospace")

    plt.tight_layout(pad=1.0)
    output_path = "/home/z/my-project/download/medisebi_er_diagram.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches="tight",
                facecolor="#0f172a", edgecolor="none")
    plt.close()
    print(f"ER diagram saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_er_diagram()
