import logging
from typing import Dict, Any, Optional
from database.repository import repo
from tools.purchase_tools import create_order_if_eligible
from tools.notification_tools import format_supplier_po_blocks
from slack.slack_app import slack_service, CHANNEL_PURCHASE_ORDERS

logger = logging.getLogger("smart_grocery.agents.procurement")

class ProcurementAgent:
    """
    Procurement Agent:
    - Creates Purchase Orders in the database.
    - Prevents duplicate active orders for the same product.
    - Sends approved orders to Wholesaler through Slack (#purchase-orders).
    - Tracks purchase order status.
    """
    def __init__(self):
        self.name = "Procurement Agent"

    def create_po(self, product_id: int, supplier_id: int, quantity: float) -> Dict[str, Any]:
        """
        Generates PO in PENDING_APPROVAL status.
        """
        res = create_order_if_eligible(product_id=product_id, supplier_id=supplier_id, quantity=quantity)
        if not res["success"]:
            logger.warning(f"[{self.name}] PO creation rejected: {res.get('message')}")
            return res

        logger.info(f"[{self.name}] Created PO {res['po']['id']} for product ID {product_id}")
        return res

    def dispatch_to_wholesaler(self, po: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends the approved PO to Wholesaler via Slack with Available / Out of Stock buttons.
        """
        # Update PO status to SENT_TO_SUPPLIER
        repo.update_purchase_order_status(po["id"], "SENT_TO_SUPPLIER")

        payload = format_supplier_po_blocks(po)
        slack_service.post_message(
            channel=CHANNEL_PURCHASE_ORDERS,
            text=payload["text"],
            blocks=payload["blocks"]
        )
        logger.info(f"[{self.name}] Dispatched PO {po['id']} to Wholesaler in #{CHANNEL_PURCHASE_ORDERS}")
        return {
            "success": True,
            "po_id": po["id"],
            "channel": CHANNEL_PURCHASE_ORDERS,
            "status": "SENT_TO_SUPPLIER"
        }

procurement_agent = ProcurementAgent()
