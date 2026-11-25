from typing import Dict, Any, List, Optional
from database.repository import repo

def check_stock_status(product_name_or_id: Any) -> Dict[str, Any]:
    """
    Checks the stock status for a given product by name or ID.
    Returns details including whether stock is low or out of stock.
    """
    if isinstance(product_name_or_id, int) or (isinstance(product_name_or_id, str) and product_name_or_id.isdigit()):
        product = repo.get_product_by_id(int(product_name_or_id))
    else:
        product = repo.get_product_by_name(str(product_name_or_id))

    if not product:
        return {"status": "NOT_FOUND", "message": f"Product '{product_name_or_id}' not found in catalog."}

    current = product["current_stock"]
    minimum = product["minimum_stock"]
    reorder = product["reorder_quantity"]
    is_low = current <= minimum
    is_oos = current <= 0

    return {
        "status": "OUT_OF_STOCK" if is_oos else ("LOW_STOCK" if is_low else "SUFFICIENT"),
        "product_id": product["id"],
        "product_name": product["name"],
        "category": product["category"],
        "current_stock": current,
        "minimum_stock": minimum,
        "suggested_reorder": reorder,
        "unit": product["unit"],
        "supplier_id": product["supplier_id"],
        "supplier_name": product["supplier_name"],
        "needs_reorder": is_low
    }

def scan_all_inventory() -> List[Dict[str, Any]]:
    """
    Scans the entire database and returns all products requiring replenishment.
    """
    low_stock_items = repo.get_low_stock_products()
    results = []
    for p in low_stock_items:
        results.append({
            "product_id": p["id"],
            "product_name": p["name"],
            "category": p["category"],
            "current_stock": p["current_stock"],
            "minimum_stock": p["minimum_stock"],
            "reorder_quantity": p["reorder_quantity"],
            "unit": p["unit"],
            "supplier_id": p["supplier_id"],
            "has_active_po": repo.has_active_order_for_product(p["id"])
        })
    return results

def update_stock_level(product_name: str, new_stock: float) -> Optional[Dict[str, Any]]:
    """
    Updates the stock level of a product (e.g. for inventory adjustments or demo simulation).
    """
    return repo.set_stock(product_name, new_stock)

def receive_goods_and_update_stock(po_id: str, received_quantity: float, received_by: str = "Admin") -> Dict[str, Any]:
    """
    Processes physical goods receipt and increases stock in the database.
    """
    po = repo.get_purchase_order(po_id)
    if not po:
        return {"success": False, "message": f"Purchase order {po_id} not found."}
    if po["status"] != "DISPATCHED":
        return {
            "success": False,
            "message": f"Cannot receive order {po_id}. Current status is {po['status']} (must be DISPATCHED)."
        }

    updated_po = repo.record_goods_receipt(po_id, received_quantity, received_by)
    product = repo.get_product_by_id(po["product_id"])

    return {
        "success": True,
        "message": f"Successfully received {received_quantity} {product['unit']} of {product['name']}. Current stock is now {product['current_stock']} {product['unit']}.",
        "po": updated_po,
        "product": product
    }
