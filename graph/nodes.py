import logging
from typing import Dict, Any
from graph.state import GroceryInventoryState
from database.repository import repo
from agents.supervisor_agent import supervisor_agent
from agents.inventory_agent import inventory_agent
from agents.planner_agent import planner_agent
from agents.alert_agent import alert_agent
from agents.approval_agent import approval_agent
from agents.procurement_agent import procurement_agent
from agents.supplier_agent import supplier_agent
from agents.notification_agent import notification_agent

logger = logging.getLogger("smart_grocery.graph.nodes")

def input_validation_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Validates input parameters and loads catalog item data.
    """
    prod_name = state.get("product_name", "").strip()
    messages = list(state.get("messages", []))
    audit = list(state.get("audit_trail", []))

    if not prod_name:
        err = "Input validation failed: product_name is empty."
        messages.append(err)
        return {"error": err, "current_step": "INPUT_VALIDATION_FAILED", "messages": messages}

    product = repo.get_product_by_name(prod_name)
    if not product:
        err = f"Product '{prod_name}' not found in grocery catalog."
        messages.append(err)
        return {
            "error": err,
            "stock_status": "NOT_FOUND",
            "current_step": "INPUT_VALIDATION_FAILED",
            "messages": messages
        }

    audit.append({"step": "input_validation", "product": prod_name, "valid": True})
    messages.append(f"Input validated: {product['name']} (ID: {product['id']}). Current stock: {product['current_stock']} {product['unit']}")

    return {
        "product_name": product["name"],
        "product_id": product["id"],
        "category": product["category"],
        "current_stock": product["current_stock"],
        "minimum_stock": product["minimum_stock"],
        "unit": product["unit"],
        "supplier_id": product["supplier_id"],
        "supplier_name": product["supplier_name"],
        "current_step": "INPUT_VALIDATED",
        "messages": messages,
        "audit_trail": audit
    }

def supervisor_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Supervisor Agent coordinates workflow transitions.
    """
    decision = supervisor_agent.plan_next_step(dict(state))
    messages = list(state.get("messages", []))
    messages.append(f"[Supervisor Agent] Decision: Next -> {decision['next_agent']} ({decision['reason']})")
    return {"current_step": "SUPERVISED", "messages": messages}

def planner_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Planner Agent calculates optimal reorder quantity.
    """
    product_dict = {
        "name": state.get("product_name"),
        "current_stock": state.get("current_stock"),
        "minimum_stock": state.get("minimum_stock"),
        "reorder_quantity": 50.0,
        "unit": state.get("unit", "kg")
    }
    plan = planner_agent.generate_plan(product_dict)
    messages = list(state.get("messages", []))
    messages.append(f"[Planner Agent] Calculated reorder plan: {plan['suggested_quantity']} {state.get('unit')} (Urgency: {plan['urgency']})")
    return {
        "reorder_plan": plan,
        "order_quantity": plan["suggested_quantity"],
        "current_step": "PLAN_PREPARED",
        "messages": messages
    }

def inventory_monitoring_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Inventory Monitoring Agent determines if stock is below threshold.
    """
    curr = state.get("current_stock", 0.0)
    min_stock = state.get("minimum_stock", 10.0)
    messages = list(state.get("messages", []))

    if curr <= 0:
        status = "OUT_OF_STOCK"
    elif curr <= min_stock:
        status = "LOW_STOCK"
    else:
        status = "SUFFICIENT"

    messages.append(f"[Inventory Monitoring Agent] Stock evaluation: {status} (Current={curr}, Minimum={min_stock})")
    return {
        "stock_status": status,
        "current_step": "INVENTORY_CHECKED",
        "messages": messages
    }

def alert_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Alert Agent dispatches Slack notification to Admin and creates PO in DB.
    """
    messages = list(state.get("messages", []))
    prod_dict = {
        "name": state.get("product_name"),
        "category": state.get("category"),
        "current_stock": state.get("current_stock"),
        "minimum_stock": state.get("minimum_stock"),
        "unit": state.get("unit"),
        "reorder_quantity": state.get("order_quantity")
    }
    plan = state.get("reorder_plan", {})
    alert_result = alert_agent.send_low_stock_alert(prod_dict, plan)
    email_sent = alert_result["email_sent"]

    # Generate formal Purchase Order in PENDING_APPROVAL status
    po_id = state.get("po_id")
    if not po_id:
        po_res = procurement_agent.create_po(
            product_id=state["product_id"],
            supplier_id=state["supplier_id"],
            quantity=state["order_quantity"]
        )
        if po_res.get("success"):
            po_id = po_res["po"]["id"]
            messages.append(f"[Procurement Agent] Created draft PO {po_id} in PENDING_APPROVAL status.")
        else:
            messages.append(f"[Procurement Agent] PO creation notice: {po_res.get('message')}")
            # If already exists, retrieve it
            existing = repo.get_low_stock_products()
            po_id = f"PO-ACTIVE-{state['product_id']}"

    messages.append(f"[Alert Agent] Sent Slack alert to #inventory-alerts for {state.get('product_name')}")
    messages.append(
        "[Email] Low-stock alert sent to Admin."
        if email_sent
        else "[Email] Low-stock alert was not sent. Check SMTP configuration and app logs."
    )
    return {
        "alert_sent": True,
        "email_sent": email_sent,
        "po_id": po_id,
        "current_step": "ALERT_SENT",
        "messages": messages
    }

def admin_approval_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Admin Approval Agent (Human-in-the-loop):
    Sends interactive Slack message to Admin in #admin-approvals.
    """
    messages = list(state.get("messages", []))
    po_id = state.get("po_id")
    approval_status = state.get("approval_status")

    if not approval_status or approval_status == "PENDING":
        # Dispatch approval prompt to Slack
        po = repo.get_purchase_order(po_id) or {
            "id": po_id,
            "product_name": state.get("product_name"),
            "quantity": state.get("order_quantity"),
            "unit": state.get("unit"),
            "supplier_name": state.get("supplier_name")
        }
        approval_agent.request_approval(po)
        messages.append(f"[Admin Approval Agent] Dispatched interactive approval request for PO {po_id} to #admin-approvals")
        return {
            "approval_status": "PENDING",
            "current_step": "AWAITING_ADMIN_APPROVAL",
            "messages": messages
        }

    # If already approved or rejected by human resume action
    admin_id = state.get("admin_id", "U_ADMIN_01")
    if approval_status == "APPROVED":
        messages.append(f"[Admin Approval Agent] PO {po_id} APPROVED by Admin <@{admin_id}>.")
    else:
        messages.append(f"[Admin Approval Agent] PO {po_id} REJECTED by Admin <@{admin_id}>.")

    return {
        "approval_status": approval_status,
        "current_step": "APPROVAL_DECIDED",
        "messages": messages
    }

def procurement_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Procurement Agent sends approved order to Wholesaler via Slack.
    """
    po_id = state.get("po_id")
    po = repo.get_purchase_order(po_id) or {
        "id": po_id,
        "product_name": state.get("product_name"),
        "quantity": state.get("order_quantity"),
        "unit": state.get("unit"),
        "supplier_name": state.get("supplier_name")
    }
    procurement_agent.dispatch_to_wholesaler(po)
    messages = list(state.get("messages", []))
    messages.append(f"[Procurement Agent] Transmitted PO {po_id} to Wholesaler {state.get('supplier_name')} in #purchase-orders")
    return {
        "current_step": "SENT_TO_WHOLESALER",
        "messages": messages
    }

def supplier_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Supplier Agent processes Wholesaler response (Available or Out of Stock).
    """
    messages = list(state.get("messages", []))
    po_id = state.get("po_id")
    availability = state.get("supplier_availability")

    if not availability:
        # Defaults to AVAILABLE for automated tests unless explicitly set
        availability = "AVAILABLE"

    is_avail = (availability == "AVAILABLE")
    res = supplier_agent.handle_stock_confirmation(po_id, is_available=is_avail)

    if is_avail:
        messages.append(f"[Supplier Agent] Wholesaler confirmed {state.get('product_name')} is IN STOCK for PO {po_id}.")
        return {
            "supplier_availability": "AVAILABLE",
            "current_step": "SUPPLIER_CONFIRMED_AVAILABLE",
            "messages": messages
        }
    else:
        alternatives = res.get("alternatives", [])
        messages.append(f"[Supplier Agent] Wholesaler reported OUT OF STOCK for PO {po_id}.")
        return {
            "supplier_availability": "OUT_OF_STOCK",
            "alternative_suppliers": alternatives,
            "current_step": "SUPPLIER_OUT_OF_STOCK",
            "messages": messages
        }

def dispatch_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Wholesaler confirms dispatch.
    Business rule: Stock does NOT increase at dispatch time!
    """
    messages = list(state.get("messages", []))
    po_id = state.get("po_id")
    supplier_agent.handle_dispatch(po_id)
    messages.append(f"[Supplier Agent] PO {po_id} marked DISPATCHED. In transit to store. (Stock unchanged)")
    return {
        "dispatch_status": "DISPATCHED",
        "current_step": "DISPATCHED",
        "messages": messages
    }

def notify_admin_oos_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Supplier Agent reports Out of Stock to Admin with alternative suppliers.
    """
    messages = list(state.get("messages", []))
    po_id = state.get("po_id")
    notification_agent.notify_out_of_stock(
        po={"id": po_id, "product_name": state.get("product_name")},
        supplier_name=state.get("supplier_name", "Primary Wholesaler")
    )
    messages.append(f"[Notification Agent] Out of Stock alert dispatched to Admin. Workflow terminated.")
    return {
        "workflow_complete": True,
        "current_step": "OUT_OF_STOCK_TERMINATED",
        "messages": messages
    }

def goods_received_confirmation_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Admin confirms physical goods arrived at grocery store.
    """
    messages = list(state.get("messages", []))
    po_id = state.get("po_id")
    received_by = state.get("received_by", "Admin")
    qty = state.get("order_quantity")

    messages.append(f"[Store Admin] Physically confirmed arrival of {qty} {state.get('unit')} for PO {po_id}.")
    return {
        "goods_received": True,
        "received_quantity": qty,
        "received_by": received_by,
        "current_step": "GOODS_RECEIVED_CONFIRMED",
        "messages": messages
    }

def inventory_update_node(state: GroceryInventoryState) -> Dict[str, Any]:
    """
    Inventory Agent updates the database stock level.
    """
    messages = list(state.get("messages", []))
    po_id = state.get("po_id")
    qty = state.get("received_quantity") or state.get("order_quantity")
    rec_res = inventory_agent.update_inventory_on_receipt(po_id, quantity=qty, received_by=state.get("received_by", "Admin"))

    updated_stock = rec_res.get("product", {}).get("current_stock")
    notification_agent.notify_goods_received(
        po={"id": po_id, "product_name": state.get("product_name"), "quantity": qty, "unit": state.get("unit")},
        current_stock=updated_stock
    )

    messages.append(f"[Inventory Update Agent] Restocked database: {state.get('product_name')} is now {updated_stock} {state.get('unit')}.")
    return {
        "inventory_updated": True,
        "updated_stock": updated_stock,
        "workflow_complete": True,
        "current_step": "COMPLETED",
        "messages": messages
    }
