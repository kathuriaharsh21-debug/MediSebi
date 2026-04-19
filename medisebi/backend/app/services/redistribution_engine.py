"""
MediSebi — Smart Redistribution Engine (Tier 3)
================================================
Core algorithm for analyzing redistribution opportunities across the
pharmacy network. Scans all shops, identifies surplus/deficit pairs,
scores transfer candidates, and manages the full transfer lifecycle.

Functions:
    - calculate_distance: Haversine formula for geographic distance
    - analyze_redistribution_opportunities: Full network scan for transfers
    - create_transfer_request: Create a new StockTransferRequest
    - approve_transfer_request: Approve a pending transfer
    - execute_transfer: Execute an approved transfer (atomic)
    - reject_transfer_request: Reject a transfer request
    - get_transfer_analytics: Dashboard analytics
"""

import json
import math
from datetime import datetime, timezone, date, timedelta

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.inventory import Inventory
from app.models.shop import Shop
from app.models.medicine import Medicine
from app.models.salt import Salt
from app.models.stock_transfer import (
    StockTransferRequest,
    TransferStatus,
    TransferPriority,
)
from app.models.notification import (
    Notification,
    NotificationSeverity,
    NotificationSource,
)
from app.models.audit_log import AuditLog, ActionType
from app.core.audit_hash import compute_audit_hash


# ── Constants ──────────────────────────────────────────────────
EXPIRY_WINDOW_DAYS = 60  # Items expiring within this window are priority
DEMAND_FORECAST_DAYS = 7  # Forecast horizon for run-out detection
MAX_DISTANCE_KM = 200  # Don't suggest transfers beyond this distance
MIN_TRANSFER_QTY = 1  # Minimum quantity to suggest a transfer


# ── Haversine Distance ─────────────────────────────────────────
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula.

    Args:
        lat1: Latitude of point 1 (decimal degrees)
        lon1: Longitude of point 1 (decimal degrees)
        lat2: Latitude of point 2 (decimal degrees)
        lon2: Longitude of point 2 (decimal degrees)

    Returns:
        Distance in kilometers (float). Returns float('inf') if coordinates
        are missing (None).
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float("inf")

    # Convert decimal degrees to radians
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in km
    R = 6371.0
    return R * c


# ── Redistribution Analysis ────────────────────────────────────
def analyze_redistribution_opportunities(db: Session) -> list[dict]:
    """
    Scan all shops and find redistribution opportunities.

    Algorithm:
    1. For each medicine (grouped by salt_id for substitution potential):
       a. Find shops with EXCESS stock
       b. Find shops with DEFICIT stock
       c. Calculate transfer score for each (source, destination) pair
    2. Score each opportunity (distance, urgency, expiry)
    3. Return sorted list of transfer recommendations
    """
    today = date.today()
    expiry_cutoff = today + timedelta(days=EXPIRY_WINDOW_DAYS)

    # ── Step 1: Load all shops with coordinates ────────────────
    shops = db.execute(
        select(Shop).where(Shop.is_active == True)
    ).scalars().all()
    shop_map = {s.id: s for s in shops}

    if len(shop_map) < 2:
        return []  # Need at least 2 shops for transfers

    # ── Step 2: Load all salt thresholds ───────────────────────
    salts = db.execute(select(Salt)).scalars().all()
    salt_map = {s.id: s for s in salts}

    # ── Step 3: Load all inventory with medicine/salt info ─────
    inventory_rows = db.execute(
        select(Inventory, Medicine, Salt)
        .join(Medicine, Inventory.med_id == Medicine.id)
        .join(Salt, Medicine.salt_id == Salt.id)
        .where(
            Inventory.quantity > 0,
            Medicine.is_active == True,
        )
    ).all()

    # ── Step 4: Group inventory by (shop_id, med_id) ──────────
    # shop_med_stock[shop_id][med_id] = [inventory_records...]
    shop_med_stock: dict[int, dict[int, list[Inventory]]] = {}

    # Track all medicines and their salts for cross-referencing
    med_salt_map: dict[int, int] = {}  # med_id -> salt_id

    for inv, med, salt in inventory_rows:
        if inv.shop_id not in shop_med_stock:
            shop_med_stock[inv.shop_id] = {}
        if inv.med_id not in shop_med_stock[inv.shop_id]:
            shop_med_stock[inv.shop_id][inv.med_id] = []
        shop_med_stock[inv.shop_id][inv.med_id].append(inv)
        med_salt_map[inv.med_id] = salt.id

    # ── Step 5: Collect all unique med_ids across all shops ───
    all_med_ids = set()
    for shop_meds in shop_med_stock.values():
        all_med_ids.update(shop_meds.keys())

    # ── Step 6: Identify deficit and surplus per medicine ──────
    opportunities: list[dict] = []

    for med_id in all_med_ids:
        salt_id = med_salt_map.get(med_id)
        salt = salt_map.get(salt_id) if salt_id else None

        reorder_level = salt.reorder_level if salt and salt.reorder_level else 0
        safety_stock = salt.safety_stock if salt and salt.safety_stock else 0
        critical_threshold = salt.critical_threshold if salt and salt.critical_threshold else 0
        warning_threshold = salt.warning_threshold if salt and salt.warning_threshold else reorder_level
        surplus_threshold = reorder_level + safety_stock

        # Classify shops for this medicine
        excess_shops: list[tuple[int, list[Inventory]]] = []
        deficit_shops: list[tuple[int, int, TransferPriority]] = []  # (shop_id, total_qty, priority)

        for shop_id in shop_med_stock:
            if med_id not in shop_med_stock[shop_id]:
                # Shop doesn't have this medicine at all
                # If we know the medicine exists elsewhere, this is a deficit
                if critical_threshold > 0:
                    deficit_shops.append((shop_id, 0, TransferPriority.CRITICAL))
                elif warning_threshold > 0:
                    deficit_shops.append((shop_id, 0, TransferPriority.HIGH))
                continue

            inv_items = shop_med_stock[shop_id][med_id]
            total_qty = sum(i.quantity for i in inv_items)
            available_qty = sum(i.quantity for i in inv_items if not i.is_reserved)

            # Check for expiring items
            has_expiring = any(
                i.expiry_date <= expiry_cutoff and i.expiry_date >= today
                for i in inv_items
            )

            # Total available (non-reserved) stock
            effective_qty = total_qty  # Use total for surplus detection

            # ── EXCESS detection ──────────────────────────────
            if available_qty > surplus_threshold or has_expiring:
                # Sort by expiry date (FIFO — closest expiry first)
                sorted_items = sorted(
                    [i for i in inv_items if not i.is_reserved],
                    key=lambda x: x.expiry_date,
                )
                if sorted_items:
                    excess_qty = available_qty - surplus_threshold
                    # If there are expiring items, count them as excess even above threshold
                    expiring_qty = sum(
                        i.quantity for i in sorted_items
                        if i.expiry_date <= expiry_cutoff and i.expiry_date >= today
                    )
                    actual_excess = max(excess_qty, expiring_qty)
                    if actual_excess > 0:
                        excess_shops.append((shop_id, sorted_items))

            # ── DEFICIT detection ─────────────────────────────
            if effective_qty < critical_threshold:
                deficit_shops.append((shop_id, effective_qty, TransferPriority.CRITICAL))
            elif effective_qty < warning_threshold:
                deficit_shops.append((shop_id, effective_qty, TransferPriority.HIGH))
            elif effective_qty < reorder_level:
                deficit_shops.append((shop_id, effective_qty, TransferPriority.MEDIUM))

        # ── Step 7: Match excess to deficit ───────────────────
        for deficit_shop_id, deficit_qty, deficit_priority in deficit_shops:
            for excess_shop_id, excess_items in excess_shops:
                if excess_shop_id == deficit_shop_id:
                    continue  # Don't transfer to self

                source_shop = shop_map.get(excess_shop_id)
                dest_shop = shop_map.get(deficit_shop_id)
                if not source_shop or not dest_shop:
                    continue

                # Calculate distance
                distance = calculate_distance(
                    source_shop.latitude, source_shop.longitude,
                    dest_shop.latitude, dest_shop.longitude,
                )
                if distance > MAX_DISTANCE_KM:
                    continue  # Too far for practical transfer

                # Calculate transfer quantity
                available_excess = sum(i.quantity for i in excess_items)
                deficit_gap = (
                    (reorder_level + safety_stock) - deficit_qty
                    if deficit_qty < reorder_level + safety_stock
                    else (warning_threshold - deficit_qty)
                )
                deficit_gap = max(deficit_gap, 0)
                transfer_qty = min(available_excess, deficit_gap)

                if transfer_qty < MIN_TRANSFER_QTY:
                    continue

                # Determine priority
                if deficit_priority == TransferPriority.CRITICAL:
                    priority = TransferPriority.CRITICAL
                elif deficit_priority == TransferPriority.HIGH:
                    priority = TransferPriority.HIGH
                else:
                    # Check if source has expiring items
                    has_expiring = any(
                        i.expiry_date <= expiry_cutoff and i.expiry_date >= today
                        for i in excess_items
                    )
                    priority = TransferPriority.HIGH if has_expiring else TransferPriority.MEDIUM

                # Get medicine info
                first_inv = excess_items[0]
                med_name = first_inv.medicine.brand_name if first_inv.medicine else f"Med#{med_id}"
                salt_name = first_inv.medicine.salt.formula_name if first_inv.medicine and first_inv.medicine.salt else "Unknown"

                # Build source_items list (specific batches to transfer)
                source_items = []
                remaining = transfer_qty
                for item in excess_items:
                    if remaining <= 0:
                        break
                    qty_from_batch = min(item.quantity, remaining)
                    source_items.append({
                        "inventory_id": item.id,
                        "batch_number": item.batch_number,
                        "expiry_date": str(item.expiry_date),
                        "quantity": qty_from_batch,
                        "cost_price": item.cost_price,
                    })
                    remaining -= qty_from_batch

                # Calculate estimated savings (avoided expiry waste)
                expiring_in_window = sum(
                    i.quantity for i in excess_items
                    if i.expiry_date <= expiry_cutoff and i.expiry_date >= today
                )
                estimated_savings = min(transfer_qty, expiring_in_window)
                avg_cost = sum(
                    i.cost_price for i in excess_items
                    if i.cost_price is not None
                ) / max(len([i for i in excess_items if i.cost_price is not None]), 1) if any(i.cost_price for i in excess_items) else 0
                savings_value = estimated_savings * avg_cost

                # Calculate composite score (higher = better opportunity)
                # Distance factor: 0 (far) to 1 (close)
                dist_factor = 1.0 - (distance / MAX_DISTANCE_KM) if MAX_DISTANCE_KM > 0 else 0.5
                # Urgency factor: 0 (low) to 1 (critical)
                urgency_map = {
                    TransferPriority.CRITICAL: 1.0,
                    TransferPriority.HIGH: 0.75,
                    TransferPriority.MEDIUM: 0.5,
                    TransferPriority.LOW: 0.25,
                }
                urgency_factor = urgency_map.get(priority, 0.25)
                # Expiry factor: based on days until earliest expiry in transfer
                min_expiry = min(i.expiry_date for i in excess_items[:len(source_items)])
                days_until_expiry = (min_expiry - today).days
                expiry_factor = max(0.0, 1.0 - (days_until_expiry / EXPIRY_WINDOW_DAYS))

                composite_score = (dist_factor * 0.3) + (urgency_factor * 0.4) + (expiry_factor * 0.3)

                # Build reason string
                if deficit_qty == 0:
                    reason = f"Shop '{dest_shop.name}' has zero stock of {med_name}. Transfer from '{source_shop.name}' to prevent stockout."
                elif deficit_qty < critical_threshold:
                    reason = f"CRITICAL: Shop '{dest_shop.name}' has {deficit_qty} units of {med_name} (below critical threshold {critical_threshold}). Transfer from '{source_shop.name}' to prevent treatment interruption."
                elif deficit_qty < warning_threshold:
                    reason = f"WARNING: Shop '{dest_shop.name}' has {deficit_qty} units of {med_name} (below warning threshold {warning_threshold}). Transfer from '{source_shop.name}' to maintain adequate stock."
                else:
                    expiring_note = " with items expiring within 60 days" if any(
                        i.expiry_date <= expiry_cutoff for i in excess_items
                    ) else ""
                    reason = f"Shop '{source_shop.name}' has excess stock{expiring_note} of {med_name}. Shop '{dest_shop.name}' could benefit from redistribution."

                opportunities.append({
                    "from_shop": {
                        "id": source_shop.id,
                        "name": source_shop.name,
                        "code": source_shop.code,
                        "city": source_shop.city,
                    },
                    "to_shop": {
                        "id": dest_shop.id,
                        "name": dest_shop.name,
                        "code": dest_shop.code,
                        "city": dest_shop.city,
                    },
                    "medicine": {
                        "id": med_id,
                        "brand_name": med_name,
                        "salt_name": salt_name,
                    },
                    "suggested_quantity": transfer_qty,
                    "priority": priority.value,
                    "reason": reason,
                    "source_items": source_items,
                    "estimated_savings": {
                        "units_saved_from_expiry": estimated_savings,
                        "estimated_cost_value": round(savings_value, 2),
                    },
                    "scoring": {
                        "composite_score": round(composite_score, 3),
                        "distance_km": round(distance, 1),
                        "distance_factor": round(dist_factor, 3),
                        "urgency_factor": round(urgency_factor, 3),
                        "expiry_factor": round(expiry_factor, 3),
                    },
                })

    # Sort by composite score (descending) then priority
    priority_order = {TransferPriority.CRITICAL.value: 0, TransferPriority.HIGH.value: 1,
                      TransferPriority.MEDIUM.value: 2, TransferPriority.LOW.value: 3}
    opportunities.sort(key=lambda x: (-x["scoring"]["composite_score"], priority_order.get(x["priority"], 9)))

    return opportunities


def analyze_shop_redistribution(db: Session, shop_id: int) -> dict:
    """
    Analyze redistribution opportunities specific to a single shop.
    Returns both incoming (deficit) and outgoing (excess) opportunities.
    """
    all_opportunities = analyze_redistribution_opportunities(db)

    incoming = [opp for opp in all_opportunities if opp["to_shop"]["id"] == shop_id]
    outgoing = [opp for opp in all_opportunities if opp["from_shop"]["id"] == shop_id]

    return {
        "shop_id": shop_id,
        "incoming_transfers": incoming,
        "outgoing_transfers": outgoing,
        "total_opportunities": len(incoming) + len(outgoing),
    }


# ── Transfer Request Management ────────────────────────────────
def create_transfer_request(
    db: Session,
    from_shop_id: int,
    to_shop_id: int,
    med_id: int,
    quantity: int,
    priority: TransferPriority,
    reason: str,
    inventory_id: int | None = None,
    requested_by_user_id: int | None = None,
) -> StockTransferRequest:
    """
    Create a new StockTransferRequest record with status PENDING.

    Args:
        db: Database session
        from_shop_id: Source shop ID
        to_shop_id: Destination shop ID
        med_id: Medicine ID to transfer
        quantity: Number of units to transfer
        priority: Transfer priority level
        reason: Explanation for the transfer
        inventory_id: Optional specific inventory batch ID
        requested_by_user_id: Optional user who created the request

    Returns:
        The created StockTransferRequest instance.
    """
    transfer = StockTransferRequest(
        from_shop_id=from_shop_id,
        to_shop_id=to_shop_id,
        med_id=med_id,
        quantity_requested=quantity,
        priority=priority,
        reason=reason,
        inventory_id=inventory_id,
        status=TransferStatus.PENDING,
    )
    db.add(transfer)
    db.flush()

    # Create audit log for transfer request creation
    _create_audit_entry(
        db=db,
        action_type=ActionType.REDISTRIBUTION_TRIGGERED,
        user_id=requested_by_user_id,
        description=(
            f"Transfer request created: {quantity} units from Shop#{from_shop_id} "
            f"to Shop#{to_shop_id} for Med#{med_id} (priority={priority.value})"
        ),
        details={
            "transfer_id": transfer.id,
            "from_shop_id": from_shop_id,
            "to_shop_id": to_shop_id,
            "med_id": med_id,
            "quantity": quantity,
            "priority": priority.value,
            "reason": reason,
        },
        resource_type="stock_transfer_request",
        resource_id=transfer.id,
    )

    # Mark inventory as reserved if inventory_id is specified
    if inventory_id:
        inv = db.execute(
            select(Inventory).where(Inventory.id == inventory_id)
        ).scalar_one_or_none()
        if inv:
            inv.is_reserved = True

    db.commit()
    db.refresh(transfer)
    return transfer


def approve_transfer_request(
    db: Session,
    request_id: int,
    approved_by_user_id: int,
) -> StockTransferRequest:
    """
    Approve a pending transfer request.
    Sets status to APPROVED, records approver and timestamp.

    Args:
        db: Database session
        request_id: The transfer request ID to approve
        approved_by_user_id: The admin user ID who approved

    Returns:
        The updated StockTransferRequest.

    Raises:
        ValueError: If request not found or not in PENDING status.
    """
    transfer = db.execute(
        select(StockTransferRequest).where(StockTransferRequest.id == request_id)
    ).scalar_one_or_none()

    if not transfer:
        raise ValueError(f"Transfer request with id={request_id} not found")

    if transfer.status != TransferStatus.PENDING:
        raise ValueError(
            f"Cannot approve transfer request in status '{transfer.status.value}'. "
            f"Only PENDING requests can be approved."
        )

    transfer.status = TransferStatus.APPROVED
    transfer.approved_by = approved_by_user_id
    transfer.approved_at = datetime.now(timezone.utc)

    # Audit log
    _create_audit_entry(
        db=db,
        action_type=ActionType.REDISTRIBUTION_TRIGGERED,
        user_id=approved_by_user_id,
        description=f"Transfer request #{request_id} approved by User#{approved_by_user_id}",
        details={
            "transfer_id": request_id,
            "action": "approved",
            "approved_by": approved_by_user_id,
        },
        resource_type="stock_transfer_request",
        resource_id=request_id,
    )

    # Notify pharmacists at both shops
    _notify_shops_for_transfer(
        db=db,
        transfer=transfer,
        severity=NotificationSeverity.INFO,
        message=f"Transfer request #{request_id} has been approved. "
                f"{transfer.quantity_requested} units ready to ship.",
    )

    db.commit()
    db.refresh(transfer)
    return transfer


def execute_transfer(db: Session, request_id: int, executed_by_user_id: int) -> dict:
    """
    Execute an approved transfer:
    1. Verify request is APPROVED
    2. Decrement source inventory (from_shop)
    3. Increment destination inventory (to_shop) — create new record if needed
    4. Mark source items as transferred
    5. Update transfer request: status=COMPLETED, completed_at, quantity_transferred
    6. Create audit logs for both source and destination modifications
    7. Create notifications for both shops' pharmacists
    8. Return summary of changes

    Args:
        db: Database session
        request_id: The transfer request ID to execute
        executed_by_user_id: The admin user ID executing the transfer

    Returns:
        Summary dict with details of changes made.

    Raises:
        ValueError: If request not found, not APPROVED, or execution fails.
    """
    transfer = db.execute(
        select(StockTransferRequest).where(StockTransferRequest.id == request_id)
    ).scalar_one_or_none()

    if not transfer:
        raise ValueError(f"Transfer request with id={request_id} not found")

    if transfer.status != TransferStatus.APPROVED:
        raise ValueError(
            f"Cannot execute transfer request in status '{transfer.status.value}'. "
            f"Only APPROVED requests can be executed."
        )

    try:
        # ── Step 1: Find and validate source inventory ────────
        if transfer.inventory_id:
            source_inv = db.execute(
                select(Inventory).where(Inventory.id == transfer.inventory_id)
            ).scalar_one_or_none()
        else:
            # Find best source inventory: non-reserved, FIFO by expiry
            source_inv = db.execute(
                select(Inventory)
                .where(
                    Inventory.shop_id == transfer.from_shop_id,
                    Inventory.med_id == transfer.med_id,
                    Inventory.quantity > 0,
                    Inventory.is_reserved == False,
                )
                .order_by(Inventory.expiry_date.asc())
            ).first()

        if not source_inv:
            raise ValueError(
                f"No available inventory found at source shop #{transfer.from_shop_id} "
                f"for medicine #{transfer.med_id}. Cannot execute transfer."
            )

        if source_inv.quantity < transfer.quantity_requested:
            raise ValueError(
                f"Insufficient stock at source. Available: {source_inv.quantity}, "
                f"Requested: {transfer.quantity_requested}."
            )

        old_source_qty = source_inv.quantity

        # ── Step 2: Decrement source inventory ────────────────
        source_inv.quantity -= transfer.quantity_requested

        # If quantity reaches zero, mark as reserved (no longer active stock)
        if source_inv.quantity == 0:
            source_inv.is_reserved = True

        # Source audit log
        _create_audit_entry(
            db=db,
            action_type=ActionType.STOCK_TRANSFERRED,
            user_id=executed_by_user_id,
            description=(
                f"Transfer OUT: {transfer.quantity_requested} units of Med#{transfer.med_id} "
                f"from Shop#{transfer.from_shop_id} (Inventory#{source_inv.id}). "
                f"Quantity: {old_source_qty} → {source_inv.quantity}."
            ),
            details={
                "transfer_id": request_id,
                "direction": "outbound",
                "inventory_id": source_inv.id,
                "shop_id": transfer.from_shop_id,
                "med_id": transfer.med_id,
                "old_quantity": old_source_qty,
                "new_quantity": source_inv.quantity,
                "transferred_quantity": transfer.quantity_requested,
            },
            resource_type="inventory",
            resource_id=source_inv.id,
        )

        # ── Step 3: Find or create destination inventory ──────
        dest_inv = db.execute(
            select(Inventory).where(
                Inventory.shop_id == transfer.to_shop_id,
                Inventory.med_id == transfer.med_id,
                Inventory.expiry_date == source_inv.expiry_date,
            )
        ).scalar_one_or_none()

        if dest_inv:
            # Existing record — increment quantity
            old_dest_qty = dest_inv.quantity
            dest_inv.quantity += transfer.quantity_requested
            dest_inv.is_reserved = False  # Activate if was reserved
        else:
            # Create new inventory record at destination
            dest_inv = Inventory(
                shop_id=transfer.to_shop_id,
                med_id=transfer.med_id,
                quantity=transfer.quantity_requested,
                batch_number=source_inv.batch_number,
                expiry_date=source_inv.expiry_date,
                cost_price=source_inv.cost_price,
                selling_price=source_inv.selling_price,
                is_reserved=False,
            )
            db.add(dest_inv)
            db.flush()
            old_dest_qty = 0

        # Destination audit log
        _create_audit_entry(
            db=db,
            action_type=ActionType.STOCK_TRANSFERRED,
            user_id=executed_by_user_id,
            description=(
                f"Transfer IN: {transfer.quantity_requested} units of Med#{transfer.med_id} "
                f"to Shop#{transfer.to_shop_id} (Inventory#{dest_inv.id}). "
                f"Quantity: {old_dest_qty} → {dest_inv.quantity}."
            ),
            details={
                "transfer_id": request_id,
                "direction": "inbound",
                "inventory_id": dest_inv.id,
                "shop_id": transfer.to_shop_id,
                "med_id": transfer.med_id,
                "old_quantity": old_dest_qty,
                "new_quantity": dest_inv.quantity,
                "transferred_quantity": transfer.quantity_requested,
            },
            resource_type="inventory",
            resource_id=dest_inv.id,
        )

        # ── Step 4: Update transfer request status ────────────
        transfer.status = TransferStatus.COMPLETED
        transfer.quantity_transferred = transfer.quantity_requested
        transfer.completed_at = datetime.now(timezone.utc)

        # ── Step 5: Notify both shops ─────────────────────────
        _notify_shops_for_transfer(
            db=db,
            transfer=transfer,
            severity=NotificationSeverity.INFO,
            message=(
                f"Transfer #{request_id} completed: "
                f"{transfer.quantity_requested} units transferred from "
                f"Shop#{transfer.from_shop_id} to Shop#{transfer.to_shop_id}."
            ),
        )

        db.commit()

        return {
            "transfer_id": request_id,
            "status": "completed",
            "quantity_transferred": transfer.quantity_requested,
            "source": {
                "shop_id": transfer.from_shop_id,
                "inventory_id": source_inv.id,
                "old_quantity": old_source_qty,
                "new_quantity": source_inv.quantity,
            },
            "destination": {
                "shop_id": transfer.to_shop_id,
                "inventory_id": dest_inv.id,
                "old_quantity": old_dest_qty,
                "new_quantity": dest_inv.quantity,
                "was_created": old_dest_qty == 0,
            },
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise ValueError(f"Database error during transfer execution: {str(e)}")


def reject_transfer_request(
    db: Session,
    request_id: int,
    rejected_by_user_id: int,
    reason: str,
) -> StockTransferRequest:
    """
    Reject a transfer request with reason.

    Args:
        db: Database session
        request_id: The transfer request ID to reject
        rejected_by_user_id: The admin user ID who rejected
        reason: Reason for rejection

    Returns:
        The updated StockTransferRequest.

    Raises:
        ValueError: If request not found or not in a rejectable status.
    """
    transfer = db.execute(
        select(StockTransferRequest).where(StockTransferRequest.id == request_id)
    ).scalar_one_or_none()

    if not transfer:
        raise ValueError(f"Transfer request with id={request_id} not found")

    if transfer.status not in (TransferStatus.PENDING, TransferStatus.APPROVED):
        raise ValueError(
            f"Cannot reject transfer request in status '{transfer.status.value}'. "
            f"Only PENDING or APPROVED requests can be rejected."
        )

    old_status = transfer.status.value
    transfer.status = TransferStatus.REJECTED

    # Append rejection reason to existing reason
    if transfer.reason:
        transfer.reason = f"{transfer.reason}\n[REJECTED] {reason}"
    else:
        transfer.reason = f"[REJECTED] {reason}"

    # Unreserve inventory if it was reserved
    if transfer.inventory_id:
        inv = db.execute(
            select(Inventory).where(Inventory.id == transfer.inventory_id)
        ).scalar_one_or_none()
        if inv:
            inv.is_reserved = False

    # Audit log
    _create_audit_entry(
        db=db,
        action_type=ActionType.REDISTRIBUTION_TRIGGERED,
        user_id=rejected_by_user_id,
        description=f"Transfer request #{request_id} rejected by User#{rejected_by_user_id}",
        details={
            "transfer_id": request_id,
            "action": "rejected",
            "rejected_by": rejected_by_user_id,
            "previous_status": old_status,
            "rejection_reason": reason,
        },
        resource_type="stock_transfer_request",
        resource_id=request_id,
    )

    # Notify relevant users
    _notify_shops_for_transfer(
        db=db,
        transfer=transfer,
        severity=NotificationSeverity.WARNING,
        message=f"Transfer request #{request_id} has been rejected. Reason: {reason}",
    )

    db.commit()
    db.refresh(transfer)
    return transfer


# ── Transfer Analytics ─────────────────────────────────────────
def get_transfer_analytics(db: Session) -> dict:
    """
    Analytics for the dashboard.

    Returns:
        Dictionary with:
        - total_transfers_by_status
        - total_units_redistributed
        - pending_transfers_count
        - completed_this_month
        - most_transferred_medicines
        - shop_transfer_frequency
    """
    today = date.today()
    month_start = today.replace(day=1)

    # ── Total transfers by status ─────────────────────────────
    status_counts = db.execute(
        select(StockTransferRequest.status, func.count(StockTransferRequest.id))
        .group_by(StockTransferRequest.status)
    ).all()
    total_by_status = {s.value: c for s, c in status_counts}

    # ── Total units redistributed (completed transfers) ──────
    total_units = db.execute(
        select(func.coalesce(func.sum(StockTransferRequest.quantity_transferred), 0))
        .where(StockTransferRequest.status == TransferStatus.COMPLETED)
    ).scalar() or 0

    # ── Pending transfers count ───────────────────────────────
    pending_count = db.execute(
        select(func.count(StockTransferRequest.id))
        .where(StockTransferRequest.status == TransferStatus.PENDING)
    ).scalar() or 0

    # ── Completed transfers this month ────────────────────────
    completed_this_month = db.execute(
        select(func.count(StockTransferRequest.id))
        .where(
            StockTransferRequest.status == TransferStatus.COMPLETED,
            StockTransferRequest.completed_at >= datetime(month_start.year, month_start.month, 1, tzinfo=timezone.utc),
        )
    ).scalar() or 0

    # ── Units transferred this month ──────────────────────────
    units_this_month = db.execute(
        select(func.coalesce(func.sum(StockTransferRequest.quantity_transferred), 0))
        .where(
            StockTransferRequest.status == TransferStatus.COMPLETED,
            StockTransferRequest.completed_at >= datetime(month_start.year, month_start.month, 1, tzinfo=timezone.utc),
        )
    ).scalar() or 0

    # ── Most transferred medicines (top 10) ──────────────────
    top_medicines = db.execute(
        select(
            StockTransferRequest.med_id,
            Medicine.brand_name,
            Salt.formula_name,
            func.count(StockTransferRequest.id).label("transfer_count"),
            func.coalesce(func.sum(StockTransferRequest.quantity_transferred), 0).label("total_units"),
        )
        .join(Medicine, StockTransferRequest.med_id == Medicine.id)
        .join(Salt, Medicine.salt_id == Salt.id)
        .where(StockTransferRequest.status == TransferStatus.COMPLETED)
        .group_by(StockTransferRequest.med_id, Medicine.brand_name, Salt.formula_name)
        .order_by(func.count(StockTransferRequest.id).desc())
        .limit(10)
    ).all()

    most_transferred = [
        {
            "med_id": row.med_id,
            "brand_name": row.brand_name,
            "salt_name": row.formula_name,
            "transfer_count": row.transfer_count,
            "total_units": row.total_units,
        }
        for row in top_medicines
    ]

    # ── Shop-to-shop transfer frequency matrix ────────────────
    from sqlalchemy.orm import aliased

    SourceShop = aliased(Shop)
    DestShop = aliased(Shop)

    transfer_pairs = db.execute(
        select(
            StockTransferRequest.from_shop_id,
            SourceShop.name.label("from_shop_name"),
            StockTransferRequest.to_shop_id,
            DestShop.name.label("to_shop_name"),
            func.count(StockTransferRequest.id).label("transfer_count"),
            func.coalesce(func.sum(StockTransferRequest.quantity_transferred), 0).label("total_units"),
        )
        .join(SourceShop, StockTransferRequest.from_shop_id == SourceShop.id)
        .join(DestShop, StockTransferRequest.to_shop_id == DestShop.id)
        .where(StockTransferRequest.status == TransferStatus.COMPLETED)
        .group_by(
            StockTransferRequest.from_shop_id,
            SourceShop.name,
            StockTransferRequest.to_shop_id,
            DestShop.name,
        )
        .order_by(func.count(StockTransferRequest.id).desc())
        .limit(20)
    ).all()

    shop_frequency = [
        {
            "from_shop_id": row.from_shop_id,
            "from_shop_name": row.from_shop_name,
            "to_shop_id": row.to_shop_id,
            "to_shop_name": row.to_shop_name,
            "transfer_count": row.transfer_count,
            "total_units": row.total_units,
        }
        for row in transfer_pairs
    ]

    # ── Priority distribution ─────────────────────────────────
    priority_counts = db.execute(
        select(StockTransferRequest.priority, func.count(StockTransferRequest.id))
        .where(StockTransferRequest.status != TransferStatus.CANCELLED)
        .group_by(StockTransferRequest.priority)
    ).all()
    priority_distribution = {p.value: c for p, c in priority_counts}

    return {
        "total_transfers_by_status": total_by_status,
        "total_units_redistributed": total_units,
        "pending_transfers_count": pending_count,
        "completed_this_month": completed_this_month,
        "units_this_month": units_this_month,
        "most_transferred_medicines": most_transferred,
        "shop_transfer_frequency": shop_frequency,
        "priority_distribution": priority_distribution,
    }


# ── Shop Transfer History ──────────────────────────────────────
def get_shop_transfer_history(
    db: Session,
    shop_id: int,
    status_filter: TransferStatus | None = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    """
    Get transfer history for a specific shop (both incoming and outgoing).

    Args:
        db: Database session
        shop_id: Shop to get history for
        status_filter: Optional status filter
        page: Page number
        size: Page size

    Returns:
        Dict with incoming, outgoing, and pagination info.
    """
    base_filter = [
        or_(
            StockTransferRequest.from_shop_id == shop_id,
            StockTransferRequest.to_shop_id == shop_id,
        ),
    ]
    if status_filter:
        base_filter.append(StockTransferRequest.status == status_filter)

    count_q = select(func.count()).select_from(
        select(StockTransferRequest.id)
        .where(and_(*base_filter))
        .subquery()
    )
    total = db.execute(count_q).scalar() or 0

    transfers = db.execute(
        select(StockTransferRequest)
        .where(and_(*base_filter))
        .order_by(StockTransferRequest.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()

    result = []
    for t in transfers:
        source = t.from_shop
        dest = t.to_shop
        med = db.execute(
            select(Medicine).where(Medicine.id == t.med_id)
        ).scalar_one_or_none()
        result.append({
            "id": t.id,
            "from_shop": {"id": source.id, "name": source.name, "code": source.code} if source else None,
            "to_shop": {"id": dest.id, "name": dest.name, "code": dest.code} if dest else None,
            "medicine": {"id": t.med_id, "brand_name": med.brand_name if med else "Unknown"} if med else {"id": t.med_id, "brand_name": "Unknown"},
            "direction": "outgoing" if t.from_shop_id == shop_id else "incoming",
            "quantity_requested": t.quantity_requested,
            "quantity_transferred": t.quantity_transferred,
            "priority": t.priority.value,
            "status": t.status.value,
            "reason": t.reason,
            "approved_by": t.approved_by,
            "approved_at": t.approved_at.isoformat() if t.approved_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    return {
        "shop_id": shop_id,
        "transfers": result,
        "total": total,
        "page": page,
        "size": size,
    }


# ── Helper Functions ───────────────────────────────────────────
def _create_audit_entry(
    db: Session,
    action_type: ActionType,
    user_id: int | None,
    description: str,
    details: dict,
    resource_type: str,
    resource_id: int,
) -> None:
    """
    Create an AuditLog entry with SHA-256 hash.
    Used internally by the redistribution engine.
    """
    now = datetime.now(timezone.utc).isoformat()
    details_str = json.dumps(details, default=str)

    audit = AuditLog(
        action_type=action_type,
        description=description,
        details=details_str,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        sha256_hash=compute_audit_hash(
            action_type=action_type.value,
            user_id=user_id,
            timestamp=now,
            details=details_str,
            resource_type=resource_type,
            resource_id=resource_id,
        ),
    )
    db.add(audit)


def _notify_shops_for_transfer(
    db: Session,
    transfer: StockTransferRequest,
    severity: NotificationSeverity,
    message: str,
) -> None:
    """
    Create notifications for staff at both the source and destination
    shops involved in a transfer.
    """
    from app.models.shop_staff import ShopStaff

    # Get staff at source shop
    source_staff = db.execute(
        select(ShopStaff.user_id).where(ShopStaff.shop_id == transfer.from_shop_id)
    ).scalars().all()

    # Get staff at destination shop
    dest_staff = db.execute(
        select(ShopStaff.user_id).where(ShopStaff.shop_id == transfer.to_shop_id)
    ).scalars().all()

    all_user_ids = set(source_staff) | set(dest_staff)

    for user_id in all_user_ids:
        direction = "outgoing" if user_id in source_staff else "incoming"
        notif = Notification(
            user_id=user_id,
            title=f"Stock Transfer #{transfer.id} Update",
            message=f"[{direction.upper()}] {message}",
            severity=severity,
            source=NotificationSource.REDISTRIBUTION,
            resource_type="stock_transfer_request",
            resource_id=transfer.id,
        )
        db.add(notif)
