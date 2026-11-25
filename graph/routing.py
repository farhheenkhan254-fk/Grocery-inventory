from typing import Literal
from langgraph.graph import END
from graph.state import GroceryInventoryState

def route_after_inventory_check(state: GroceryInventoryState) -> str:
    """
    Conditional Routing after Inventory Check:
    - Low Stock / Out of Stock -> Alert Agent
    - Sufficient Stock -> END
    """
    status = state.get("stock_status")
    if status in ["LOW_STOCK", "OUT_OF_STOCK"]:
        return "alert_agent"
    return END

def route_after_admin_approval(state: GroceryInventoryState) -> str:
    """
    Conditional Routing after Admin Approval (Human-in-the-loop):
    - Approved -> Procurement Agent
    - Rejected -> END
    """
    status = state.get("approval_status")
    if status == "APPROVED":
        return "procurement_agent"
    return END

def route_after_supplier_check(state: GroceryInventoryState) -> str:
    """
    Conditional Routing after Supplier Stock Confirmation:
    - Available -> Dispatch
    - Out of Stock -> Notify Admin
    """
    avail = state.get("supplier_availability")
    if avail == "AVAILABLE":
        return "dispatch"
    return "notify_admin_oos"
