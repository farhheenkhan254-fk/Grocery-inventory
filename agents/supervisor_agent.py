import logging
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger("smart_grocery.agents.supervisor")

class SupervisorAgent:
    """
    Supervisor Agent:
    - Coordinates all sub-agents.
    - Determines which agent should execute the next task.
    - Controls workflow transitions.
    - Uses LangGraph conditional routing decisions.
    """
    def __init__(self):
        self.name = "Supervisor Agent"

    def plan_next_step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates workflow state and determines next transition.
        """
        current_step = state.get("current_step", "START")
        stock_status = state.get("stock_status")
        approval_status = state.get("approval_status")
        supplier_response = state.get("supplier_availability")
        dispatch_status = state.get("dispatch_status")
        goods_received = state.get("goods_received", False)

        logger.info(f"[{self.name}] Coordinating state: step={current_step}, stock={stock_status}, approval={approval_status}")

        if not state.get("product_name"):
            return {"next_agent": "END", "reason": "Missing product_name in state."}

        # If stock check not done yet
        if not stock_status:
            return {"next_agent": "inventory_agent", "reason": "Requires stock level inspection."}

        # If stock is sufficient
        if stock_status == "SUFFICIENT":
            return {"next_agent": "END", "reason": "Stock is sufficient; no procurement required."}

        # If stock is low and no purchase plan created
        if stock_status in ["LOW_STOCK", "OUT_OF_STOCK"] and not state.get("reorder_plan"):
            return {"next_agent": "planner_agent", "reason": "Low stock detected; plan reorder parameters."}

        # If reorder plan exists but alert not sent
        if state.get("reorder_plan") and not state.get("alert_sent"):
            return {"next_agent": "alert_agent", "reason": "Dispatch immediate low stock notification to Admin."}

        # If alert sent and no PO created
        if state.get("alert_sent") and not state.get("po_id"):
            return {"next_agent": "procurement_agent", "reason": "Create formal Purchase Order request."}

        # If PO created but approval is pending
        if state.get("po_id") and not approval_status:
            return {"next_agent": "approval_agent", "reason": "Request human Admin authorization."}

        # If Admin rejected PO
        if approval_status == "REJECTED":
            return {"next_agent": "notification_agent", "reason": "Notify stakeholders of Admin rejection and conclude."}

        # If Admin approved PO but wholesaler not queried
        if approval_status == "APPROVED" and not supplier_response:
            return {"next_agent": "supplier_agent", "reason": "Route PO to Wholesaler for stock confirmation."}

        # If Wholesaler reported Out of Stock
        if supplier_response == "OUT_OF_STOCK":
            return {"next_agent": "supplier_agent", "reason": "Handle out-of-stock and find alternative suppliers."}

        # If Wholesaler confirmed available but not dispatched
        if supplier_response == "AVAILABLE" and dispatch_status != "DISPATCHED":
            return {"next_agent": "supplier_agent", "reason": "Awaiting Wholesaler dispatch confirmation."}

        # If dispatched but goods not received
        if dispatch_status == "DISPATCHED" and not goods_received:
            return {"next_agent": "approval_agent", "reason": "Awaiting physical goods arrival confirmation by Admin."}

        # If goods received, update inventory and end
        if goods_received and not state.get("inventory_updated"):
            return {"next_agent": "inventory_agent", "reason": "Restock database with received consignment."}

        return {"next_agent": "notification_agent", "reason": "Send final delivery report."}

supervisor_agent = SupervisorAgent()
