"""
MediSebi — Climate-Disease Intelligence Engine
================================================
Maps real-time weather data to epidemiological disease risk predictions.
Uses hardcoded rule sets based on published epidemiological data.

When weather conditions match disease patterns (e.g., high temp + humidity
→ Dengue risk), the engine:
  1. Looks up recommended salts/medicines for that disease
  2. Checks inventory levels at the affected shop
  3. If stock is low → creates ClimateAlert + Notification records

Works with OR without the OpenWeather API key (falls back to deterministic
simulated data based on city name).
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.shop import Shop
from app.models.salt import Salt
from app.models.medicine import Medicine
from app.models.inventory import Inventory
from app.models.notification import Notification, NotificationSeverity, NotificationSource
from app.models.climate_alert import ClimateAlert, RiskLevel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Climate-Disease mapping rules (epidemiological data)
# ---------------------------------------------------------------------------

RULES = [
    {
        "disease": "Dengue",
        "conditions": {
            "temp_min": 25, "temp_max": 40,
            "humidity_min": 60, "humidity_max": 95,
        },
        "recommended_salts": ["Paracetamol", "Oral Rehydration Salts"],
        "risk_description": (
            "High temperature + humidity create ideal mosquito breeding conditions"
        ),
    },
    {
        "disease": "Cholera / Gastroenteritis",
        "conditions": {
            "temp_min": 25, "temp_max": 40,
            "humidity_min": 70, "humidity_max": 100,
        },
        "recommended_salts": ["Oral Rehydration Salts"],
        "risk_description": (
            "Flooding and contaminated water sources during monsoon season"
        ),
    },
    {
        "disease": "Heat Stroke",
        "conditions": {
            "temp_min": 38, "temp_max": 55,
            "humidity_min": 0, "humidity_max": 100,
        },
        "recommended_salts": ["Oral Rehydration Salts"],
        "risk_description": "Extreme heat conditions causing heat-related illnesses",
    },
    {
        "disease": "Viral Fever / Flu",
        "conditions": {
            "temp_min": 10, "temp_max": 30,
            "humidity_min": 30, "humidity_max": 80,
        },
        "recommended_salts": ["Paracetamol", "Ibuprofen"],
        "risk_description": "Seasonal viral infections during temperature transitions",
    },
    {
        "disease": "Respiratory Infections",
        "conditions": {
            "temp_min": 5, "temp_max": 20,
            "humidity_min": 20, "humidity_max": 70,
        },
        "recommended_salts": ["Paracetamol", "Ibuprofen", "Amoxicillin"],
        "risk_description": "Cold weather increases respiratory infection risk",
    },
]

# ---------------------------------------------------------------------------
# Deterministic simulated weather (no API key needed)
# ---------------------------------------------------------------------------

# City → (temp_c, humidity_pct, condition)
_CITY_SIMULATIONS: dict[str, tuple[float, float, str]] = {
    "mumbai": (33.0, 78.0, "Partly Cloudy"),       # Dengue risk zone
    "delhi": (38.0, 45.0, "Clear Sky"),             # Heat Stroke risk zone
    "kolkata": (34.0, 82.0, "Light Rain"),          # Dengue + Cholera zone
    "chennai": (35.0, 72.0, "Humid & Warm"),        # Dengue zone
    "bangalore": (27.0, 55.0, "Moderate"),          # Viral Fever zone
    "hyderabad": (36.0, 50.0, "Sunny"),             # Heat Stroke zone
    "pune": (29.0, 48.0, "Clear"),                  # Moderate
    "jaipur": (40.0, 30.0, "Hot & Dry"),            # Heat Stroke zone
    "lucknow": (37.0, 60.0, "Hazy"),                # Heat Stroke + Dengue
    "ahmedabad": (39.0, 40.0, "Hot"),               # Heat Stroke zone
    "bhopal": (35.0, 55.0, "Warm"),                 # Moderate
    "patna": (36.0, 68.0, "Humid"),                 # Dengue zone
}

# Default fallback simulation
_DEFAULT_SIM = (25.0, 50.0, "Clear")


def _city_hash(city: str) -> tuple[float, float, str]:
    """
    Produce deterministic weather from a city name.
    If the city is in the known table, return that simulation.
    Otherwise derive from the hash of the city name.
    """
    city_lower = city.strip().lower()
    if city_lower in _CITY_SIMULATIONS:
        return _CITY_SIMULATIONS[city_lower]

    # Derive deterministic values from city name hash
    h = hashlib.md5(city.encode("utf-8")).hexdigest()
    temp = 15.0 + (int(h[:2], 16) % 30)       # 15–45 °C
    humidity = 20.0 + (int(h[2:4], 16) % 70)   # 20–90 %
    condition = "Simulated Weather"
    return (float(temp), float(humidity), condition)


# ---------------------------------------------------------------------------
# Simple in-memory weather cache
# ---------------------------------------------------------------------------

_weather_cache: dict[int, tuple[dict, datetime]] = {}
_CACHE_TTL = timedelta(minutes=30)  # Cache weather for 30 minutes


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def fetch_weather_for_shop(shop: Shop) -> dict | None:
    """
    Get current weather for a shop's location.

    - If OPENWEATHER_API_KEY is set → call OpenWeather API
    - If no API key → return deterministic simulated data

    Returns dict with keys:
        temperature_c, humidity_pct, weather_condition, city, raw_response
    """
    if shop.latitude is None or shop.longitude is None:
        return None

    city = shop.city or "Unknown"

    # Check cache first
    if shop.id in _weather_cache:
        cached_data, cached_at = _weather_cache[shop.id]
        if datetime.now(timezone.utc) - cached_at < _CACHE_TTL:
            return cached_data

    api_key = settings.OPENWEATHER_API_KEY
    base_url = settings.OPENWEATHER_BASE_URL

    if api_key:
        try:
            resp = httpx.get(
                f"{base_url}/weather",
                params={
                    "lat": shop.latitude,
                    "lon": shop.longitude,
                    "appid": api_key,
                    "units": "metric",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()

            temp = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            condition = data["weather"][0]["description"] if data.get("weather") else "Unknown"

            result = {
                "temperature_c": temp,
                "humidity_pct": humidity,
                "weather_condition": condition,
                "city": city,
                "raw_response": json.dumps(data),
            }

            _weather_cache[shop.id] = (result, datetime.now(timezone.utc))
            return result

        except Exception as e:
            logger.warning(
                "OpenWeather API call failed for shop %s (%s): %s. Falling back to simulated data.",
                shop.id, city, e,
            )

    # Fallback: deterministic simulation
    temp, humidity, condition = _city_hash(city)
    raw = {
        "simulated": True,
        "city": city,
        "temperature_c": temp,
        "humidity_pct": humidity,
        "weather_condition": condition,
    }

    result = {
        "temperature_c": temp,
        "humidity_pct": humidity,
        "weather_condition": condition,
        "city": city,
        "raw_response": json.dumps(raw),
    }

    _weather_cache[shop.id] = (result, datetime.now(timezone.utc))
    return result


def assess_disease_risks(weather_data: dict) -> list[dict]:
    """
    Evaluate all climate-disease rules against the given weather data.

    For each rule that matches, calculates a risk_score (0–100) based on
    how well the conditions match the rule thresholds.

    Risk score mapping:
        >= 70 → CRITICAL
        >= 50 → HIGH
        >= 30 → MODERATE
        < 30  → LOW

    Returns list of matching diseases with risk levels.
    """
    temp = weather_data["temperature_c"]
    humidity = weather_data["humidity_pct"]

    results = []

    for rule in RULES:
        cond = rule["conditions"]

        # Check if conditions are within bounds
        in_temp = cond["temp_min"] <= temp <= cond["temp_max"]
        in_humidity = cond["humidity_min"] <= humidity <= cond["humidity_max"]

        if not (in_temp and in_humidity):
            continue

        # Calculate risk score based on how deep into the range we are
        temp_range = cond["temp_max"] - cond["temp_min"]
        humidity_range = cond["humidity_max"] - cond["humidity_min"]

        if temp_range > 0:
            # How far past the midpoint — 0.5 = at midpoint, 1.0 = at max
            temp_position = (temp - cond["temp_min"]) / temp_range
        else:
            temp_position = 0.5

        if humidity_range > 0:
            humidity_position = (humidity - cond["humidity_min"]) / humidity_range
        else:
            humidity_position = 0.5

        # Weighted risk score: being in the upper range of both increases risk
        # Also factor in proximity to the extremes of the range
        temp_intensity = abs(temp_position - 0.5) * 2  # 0 at midpoint, 1 at extremes
        humidity_intensity = abs(humidity_position - 0.5) * 2

        # Base score from being in range + intensity bonus
        risk_score = 40.0  # Base score for being in range
        risk_score += temp_intensity * 25.0
        risk_score += humidity_intensity * 25.0

        # Bonus for extreme conditions (near bounds)
        if temp_position > 0.85 or temp_position < 0.15:
            risk_score += 5
        if humidity_position > 0.85 or humidity_position < 0.15:
            risk_score += 5

        risk_score = min(max(risk_score, 0), 100)

        # Map score to risk level
        if risk_score >= 70:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 50:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 30:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.LOW

        results.append({
            "disease": rule["disease"],
            "risk_level": risk_level,
            "risk_score": round(risk_score, 1),
            "risk_description": rule["risk_description"],
            "recommended_salts": rule["recommended_salts"],
            "conditions_matched": {
                "temperature": f"{temp}°C (range: {cond['temp_min']}–{cond['temp_max']}°C)",
                "humidity": f"{humidity}% (range: {cond['humidity_min']}–{cond['humidity_max']}%)",
            },
        })

    # Sort by risk score descending
    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results


def generate_climate_alerts(db: Session) -> list[dict]:
    """
    Full pipeline: fetch weather for all active shops, assess disease risks,
    check inventory for recommended medicines, and create alerts + notifications.

    Steps:
        1. Get all active shops with lat/long
        2. Fetch weather for each shop
        3. Assess disease risks
        4. For CRITICAL / HIGH risks:
            a. Look up recommended salts in the DB → get salt_ids
            b. Look up medicines for those salts
            c. Check inventory at this shop
            d. If stock is low/zero → URGENT alert
            e. Create ClimateAlert record
            f. Create Notification for shop's assigned staff
        5. Return all alerts generated
    """
    from app.models.shop_staff import ShopStaff

    # 1. Get all active shops with lat/long
    shops_stmt = select(Shop).where(
        and_(
            Shop.is_active == True,  # noqa: E712
            Shop.latitude.isnot(None),
            Shop.longitude.isnot(None),
        )
    )
    shops = db.execute(shops_stmt).scalars().all()

    all_alerts: list[dict] = []

    for shop in shops:
        # 2. Fetch weather
        weather = fetch_weather_for_shop(shop)
        if weather is None:
            continue

        # 3. Assess disease risks
        risks = assess_disease_risks(weather)

        # 4. Process significant risks (CRITICAL / HIGH)
        significant_risks = [
            r for r in risks
            if r["risk_level"] in (RiskLevel.CRITICAL, RiskLevel.HIGH)
        ]

        if not significant_risks:
            # Store low/moderate risks without inventory check
            for risk in risks:
                if risk["risk_level"] in (RiskLevel.LOW, RiskLevel.MODERATE):
                    _store_climate_alert(
                        db=db,
                        shop=shop,
                        weather=weather,
                        risk=risk,
                        recommended_salt_ids=[],
                        recommended_medicine_ids=[],
                        stock_status="not_checked",
                    )
            continue

        for risk in significant_risks:
            # 4a. Look up recommended salts in the DB
            recommended_salt_names = risk["recommended_salts"]
            salt_ids, medicine_ids, stock_issues = _check_recommended_stock(
                db=db,
                shop_id=shop.id,
                salt_names=recommended_salt_names,
            )

            # 4d. Determine stock status
            has_stock_issues = len(stock_issues) > 0
            stock_status = "low_stock" if has_stock_issues else "adequate"

            # 4e. Create ClimateAlert record
            _store_climate_alert(
                db=db,
                shop=shop,
                weather=weather,
                risk=risk,
                recommended_salt_ids=salt_ids,
                recommended_medicine_ids=medicine_ids,
                stock_status=stock_status,
                stock_issues=stock_issues,
            )

            # 4f. Create Notification for shop's assigned staff
            _create_climate_notifications(
                db=db,
                shop=shop,
                risk=risk,
                stock_status=stock_status,
                stock_issues=stock_issues,
            )

            all_alerts.append({
                "shop_id": shop.id,
                "shop_name": shop.name,
                "city": weather["city"],
                "temperature_c": weather["temperature_c"],
                "humidity_pct": weather["humidity_pct"],
                "disease": risk["disease"],
                "risk_level": risk["risk_level"].value,
                "risk_score": risk["risk_score"],
                "recommended_salts": recommended_salt_names,
                "stock_status": stock_status,
                "stock_issues": stock_issues,
            })

    db.flush()
    return all_alerts


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_recommended_stock(
    db: Session,
    shop_id: int,
    salt_names: list[str],
) -> tuple[list[int], list[int], list[dict]]:
    """
    Check inventory for recommended salts at a specific shop.

    Returns:
        (salt_ids, medicine_ids, stock_issues)
    """
    salt_ids: list[int] = []
    medicine_ids: list[int] = []
    stock_issues: list[dict] = []

    for name in salt_names:
        # Find the salt by formula_name (case-insensitive)
        salt_stmt = select(Salt).where(
            func.lower(Salt.formula_name) == name.lower()
        )
        salt = db.execute(salt_stmt).scalar_one_or_none()

        if salt is None:
            stock_issues.append({
                "salt_name": name,
                "status": "not_found",
                "message": f"Salt '{name}' not found in database",
            })
            continue

        salt_ids.append(salt.id)

        # Find medicines linked to this salt
        med_stmt = select(Medicine).where(
            and_(
                Medicine.salt_id == salt.id,
                Medicine.is_active == True,  # noqa: E712
            )
        )
        medicines = db.execute(med_stmt).scalars().all()

        if not medicines:
            stock_issues.append({
                "salt_name": name,
                "salt_id": salt.id,
                "status": "no_medicines",
                "message": f"No active medicines found for salt '{name}'",
            })
            continue

        for med in medicines:
            medicine_ids.append(med.id)

            # Check inventory at this shop
            inv_stmt = (
                select(func.sum(Inventory.quantity))
                .where(
                    and_(
                        Inventory.med_id == med.id,
                        Inventory.shop_id == shop_id,
                    )
                )
            )
            total_qty = db.execute(inv_stmt).scalar() or 0

            # Determine if stock is low using salt thresholds
            threshold = salt.warning_threshold or salt.critical_threshold
            is_low = False

            if threshold is not None and total_qty <= threshold:
                is_low = True
            elif total_qty == 0:
                is_low = True

            if is_low:
                stock_issues.append({
                    "salt_name": name,
                    "salt_id": salt.id,
                    "medicine_id": med.id,
                    "medicine_name": med.brand_name,
                    "status": "low_stock" if total_qty > 0 else "out_of_stock",
                    "current_quantity": total_qty,
                    "threshold": threshold,
                    "message": (
                        f"{med.brand_name}: {total_qty} units in stock"
                        + (f" (threshold: {threshold})" if threshold else "")
                    ),
                })

    return salt_ids, medicine_ids, stock_issues


def _store_climate_alert(
    db: Session,
    shop: Shop,
    weather: dict,
    risk: dict,
    recommended_salt_ids: list[int],
    recommended_medicine_ids: list[int],
    stock_status: str,
    stock_issues: list[dict] | None = None,
) -> ClimateAlert:
    """Persist a ClimateAlert record to the database."""
    # Build action summary
    action_parts = [risk["risk_description"]]
    if stock_status == "low_stock":
        action_parts.append("URGENT: Recommended medicines are LOW in stock — restock immediately.")
    elif stock_status == "adequate":
        action_parts.append("Stock levels for recommended medicines appear adequate.")
    if stock_issues:
        for issue in stock_issues:
            action_parts.append(f"  • {issue['message']}")

    alert = ClimateAlert(
        shop_id=shop.id,
        city=weather["city"],
        temperature_c=weather["temperature_c"],
        humidity_pct=weather["humidity_pct"],
        weather_condition=weather["weather_condition"],
        risk_level=risk["risk_level"],
        disease_risk=risk["disease"],
        recommended_salts=json.dumps(recommended_salt_ids),
        recommended_medicines=json.dumps(recommended_medicine_ids),
        action_summary="\n".join(action_parts),
        weather_api_response=weather.get("raw_response"),
    )
    db.add(alert)
    return alert


def _create_climate_notifications(
    db: Session,
    shop: Shop,
    risk: dict,
    stock_status: str,
    stock_issues: list[dict],
) -> None:
    """Create notifications for staff assigned to the shop."""
    from app.models.shop_staff import ShopStaff

    # Find all staff assigned to this shop
    staff_stmt = select(ShopStaff.user_id).where(ShopStaff.shop_id == shop.id)
    user_ids = [row[0] for row in db.execute(staff_stmt).all()]

    if not user_ids:
        return

    severity = (
        NotificationSeverity.CRITICAL
        if stock_status == "low_stock"
        else NotificationSeverity.WARNING
    )

    disease = risk["disease"]
    risk_level = risk["risk_level"].value
    stock_note = ""
    if stock_issues:
        issue_msgs = [si["message"] for si in stock_issues[:3]]  # Limit to 3 issues
        stock_note = f"\n\nStock Alerts:\n" + "\n".join(f"• {m}" for m in issue_msgs)

    title = f"⚠️ Climate Alert: {disease} risk ({risk_level}) — {shop.name}"
    message = (
        f"Disease Risk: {disease}\n"
        f"Risk Level: {risk_level.upper()}\n"
        f"Location: {shop.name} ({shop.city})\n"
        f"Conditions: {risk['risk_description']}\n"
        f"Recommended: {', '.join(risk['recommended_salts'])}\n"
        f"Stock Status: {stock_status.upper()}"
        f"{stock_note}"
    )

    for uid in user_ids:
        notif = Notification(
            user_id=uid,
            title=title,
            message=message,
            severity=severity,
            source=NotificationSource.CLIMATE_ENGINE,
            resource_type="shop",
            resource_id=shop.id,
            action_url=f"/shops/{shop.id}",
            expires_at=datetime.now(timezone.utc) + timedelta(
                days=settings.NOTIFICATION_CRITICAL_TTL_DAYS
            ),
        )
        db.add(notif)
