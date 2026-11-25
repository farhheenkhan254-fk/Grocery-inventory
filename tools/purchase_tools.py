from typing import Dict, Any, Optional
from database.repository import repo
from app.config import settings

def calculate_reorder_plan(
    current_stock: float,
    minimum_stock: float,
    base_reorder: float,
    lead_time_days: int = None,
    safety_factor: float = None
) -> Dict[str, Any]:
    """
    Planner rule: calculates suggested reorder quantity considering minimum stock deficit,
    safety buffer, and standard vendor batch sizing.
    Never approves a purchase automatically.
    """
    lead_time = lead_time_days or settings.DEFAULT_LEAD_TIME_DAYS
    factor = safety_factor or settings.SAFETY_STOCK_FACTOR

    deficit = max(0.0, minimum_stock - current_stock)
    # Standard reorder quantity is base_reorder, expanding if deficit exceeds base batch
    suggested_qty = float(base_reorder if deficit <= base_reorder else (base_reorder + deficit))

    urgency = "CRITICAL" if current_stock <= 0 else ("HIGH" if current_stock < (minimum_stock * 0.5) else "MEDIUM")

    return {
        "current_stock": current_stock,
        "minimum_stock": minimum_stock,
        "suggested_quantity": suggested_qty,
        "deficit": deficit,
        "lead_time_days": lead_time,
        "urgency": urgency,
        "formula": f"reorder_quantity={suggested_qty} (base={base_reorder}, deficit={deficit})"
    }

def create_order_if_eligible(product_id: int, supplier_id: int, quantity: float) -> Dict[str, Any]:
    """
    Business rules validation:
    1. Check for duplicate active purchase orders for the same product.
    2. Check supplier validity.
    3. If valid, creates PO in PENDING_APPROVAL status.
    """
    if repo.has_active_order_for_product(product_id):
        return {
            "success": False,
            "error": "DUPLICATE_ACTIVE_ORDER",
            "message": f"An active purchase order is already in progress for product ID {product_id}."
        }

    supplier = repo.get_supplier_by_id(supplier_id)
    if not supplier:
        return {
            "success": False,
            "error": "INVALID_SUPPLIER",
            "message": f"Supplier with ID {supplier_id} not found."
        }

    po = repo.create_purchase_order(product_id=product_id, supplier_id=supplier_id, quantity=quantity)
    if not po:
        return {
            "success": False,
            "error": "CREATION_FAILED",
            "message": "Failed to create purchase order in database."
        }

    return {
        "success": True,
        "po": po,
        "message": f"Purchase order {po['id']} generated in PENDING_APPROVAL status."
    }
