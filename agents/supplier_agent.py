import logging
from typing import Dict, Any, List
from database.repository import repo
from tools.supplier_tools import process_supplier_decision, process_supplier_dispatch, get_alternative_wholesalers
from tools.notification_tools import format_dispatch_action_blocks, format_out_of_stock_alert_blocks, format_goods_receipt_blocks
from slack.slack_app import slack_service, CHANNEL_SUPPLIER_UPDATES, CHANNEL_INVENTORY_ALERTS, CHANNEL_ADMIN_APPROVALS
from slack.events import slack_auth
from app.config import settings

logger = logging.getLogger("smart_grocery.agents.supplier")

class SupplierAgent:
    """
    Supplier Agent:
    - Receives purchase requests.
    - Allows Wholesaler to confirm availability or Out of Stock.
    - Allows Wholesaler to confirm dispatch.
    - Sends supplier status updates to Admin.
    - If unavailable, reports Out of Stock to Admin and lists alternative suppliers.
    """
    def __init__(self):
        self.name = "Supplier Agent"

    def handle_stock_confirmation(self, po_id: str, is_available: bool, user_id: str = "U_SUPPLIER_DEMO") -> Dict[str, Any]:
        if not slack_auth.is_authorized_supplier(user_id):
            return {"success": False, "error": "UNAUTHORIZED", "message": f"User {user_id} is not an authorized supplier."}

        res = process_supplier_decision(po_id, is_available)
        if not res["success"]:
            return res

        po = res["po"]

        if is_available:
            # Send dispatch action prompt to supplier channel
            dispatch_blocks = format_dispatch_action_blocks(po)
            slack_service.post_message(
                channel=CHANNEL_SUPPLIER_UPDATES,
                text=dispatch_blocks["text"],
                blocks=dispatch_blocks["blocks"]
            )
            # Notify Admin in supplier-updates
            slack_service.post_message(
                channel=CHANNEL_SUPPLIER_UPDATES,
                text=f"✅ Wholesaler *{po['supplier_name']}* confirmed availability for PO `{po_id}` ({po['product_name']}). Awaiting dispatch."
            )
            logger.info(f"[{self.name}] Supplier confirmed AVAILABLE for PO {po_id}")
        else:
            # Report Out of Stock to Admin
            alternatives = res.get("alternatives", [])
            oos_blocks = format_out_of_stock_alert_blocks(po, alternatives)
            slack_service.post_message(
                channel=CHANNEL_INVENTORY_ALERTS,
                text=oos_blocks["text"],
                blocks=oos_blocks["blocks"]
            )
            logger.warning(f"[{self.name}] Supplier reported OUT_OF_STOCK for PO {po_id}. Admin notified of {len(alternatives)} alternatives.")

        return res

    def handle_dispatch(self, po_id: str, user_id: str = "U_SUPPLIER_DEMO") -> Dict[str, Any]:
        """
        Wholesaler confirms dispatch.
        Business Rule: Stock does NOT increase at dispatch time!
        """
        if not slack_auth.is_authorized_supplier(user_id):
            return {"success": False, "error": "UNAUTHORIZED", "message": f"User {user_id} is not an authorized supplier."}

        res = process_supplier_dispatch(po_id)
        if not res["success"]:
            return res

        po = res["po"]

        # Notify Admin in supplier-updates and request physical goods receipt confirmation
        slack_service.post_message(
            channel=CHANNEL_SUPPLIER_UPDATES,
            text=f"🚚 *Consignment Dispatched:* PO `{po_id}` ({po['quantity']} {po['unit']} of {po['product_name']}) has left the wholesaler warehouse."
        )

        receipt_blocks = format_goods_receipt_blocks(po)
        slack_service.post_message(
            channel=CHANNEL_ADMIN_APPROVALS,
            text=receipt_blocks["text"],
            blocks=receipt_blocks["blocks"]
        )

        logger.info(f"[{self.name}] Dispatched PO {po_id}. Goods in transit; stock unchanged.")
        return res

    def reassign_supplier(self, po_id: str, new_supplier_id: int) -> Dict[str, Any]:
        """
        Reassigns an out-of-stock PO to an alternative supplier.
        """
        success = repo.assign_new_supplier_to_order(po_id, new_supplier_id)
        if not success:
            return {"success": False, "message": "Failed to reassign supplier."}

        po = repo.get_purchase_order(po_id)
        # Notify new supplier
        from tools.notification_tools import format_supplier_po_blocks
        payload = format_supplier_po_blocks(po)
        slack_service.post_message(
            channel=CHANNEL_PURCHASE_ORDERS,
            text=payload["text"],
            blocks=payload["blocks"]
        )
        return {"success": True, "po": po, "message": f"Reassigned PO {po_id} to {po['supplier_name']}."}

supplier_agent = SupplierAgent()
