from typing import Dict, Any, List, Optional
from database.repository import repo

def get_supplier_info(supplier_id: int) -> Optional[Dict[str, Any]]:
    return repo.get_supplier_by_id(supplier_id)

def get_alternative_wholesalers(current_supplier_id: int) -> List[Dict[str, Any]]:
    """
    Finds backup wholesalers when primary supplier reports out of stock.
    """
    return repo.get_alternative_suppliers(current_supplier_id)

def process_supplier_decision(po_id: str, is_available: bool, notes: str = "") -> Dict[str, Any]:
    """
    Business rules:
    - Supplier can only confirm availability or OOS for an approved purchase order.
    - If available, status updates to CONFIRMED_AVAILABLE.
    - If out of stock, status updates to OUT_OF_STOCK and triggers alternative supplier notification.
    """
    po = repo.get_purchase_order(po_id)
    if not po:
        return {"success": False, "message": f"Purchase order {po_id} not found."}

    if po["status"] not in ["APPROVED", "SENT_TO_SUPPLIER"]:
        return {
            "success": False,
            "message": f"Supplier cannot respond to order {po_id}. Current status is {po['status']} (must be APPROVED or SENT_TO_SUPPLIER)."
        }

    status_str = "AVAILABLE" if is_available else "OUT_OF_STOCK"
    updated_po = repo.record_supplier_response(po_id, availability_status=status_str)

    alternatives = []
    if not is_available:
        alternatives = repo.get_alternative_suppliers(po["supplier_id"])

    return {
        "success": True,
        "po": updated_po,
        "status": status_str,
        "alternatives": alternatives,
        "message": f"Supplier confirmed {status_str} for order {po_id}."
    }

def process_supplier_dispatch(po_id: str) -> Dict[str, Any]:
    """
    Business rules:
    - Supplier cannot dispatch an unapproved or out-of-stock order.
    - Stock must NOT increase at dispatch time!
    """
    po = repo.get_purchase_order(po_id)
    if not po:
        return {"success": False, "message": f"Purchase order {po_id} not found."}

    if po["status"] not in ["CONFIRMED_AVAILABLE", "APPROVED", "SENT_TO_SUPPLIER"]:
        return {
            "success": False,
            "message": f"Cannot dispatch order {po_id}. Status is {po['status']}."
        }

    updated_po = repo.record_supplier_response(po_id, availability_status="AVAILABLE", dispatch_status="DISPATCHED")
    return {
        "success": True,
        "po": updated_po,
        "message": f"Purchase order {po_id} dispatched by wholesaler. In-transit to store."
    }
