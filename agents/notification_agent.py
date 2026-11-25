import logging
from typing import Dict, Any, List, Optional
from slack.slack_app import (
    slack_service,
    CHANNEL_INVENTORY_ALERTS,
    CHANNEL_ADMIN_APPROVALS,
    CHANNEL_PURCHASE_ORDERS,
    CHANNEL_SUPPLIER_UPDATES,
    CHANNEL_INVENTORY_REPORTS,
)
from slack.messages import build_inventory_report_blocks

logger = logging.getLogger("smart_grocery.agents.notification")

class NotificationAgent:
    """
    Notification Agent:
    - Sends all important workflow updates through Slack.
    - Handles dispatch, out-of-stock, delivery, and receiving notifications.
    - Generates executive inventory status summaries.
    """
    def __init__(self):
        self.name = "Notification Agent"

    def notify_dispatch(self, po: Dict[str, Any]):
        msg = f"🚚 *Dispatch Notice:* PO `{po['id']}` ({po['product_name']}) is en route to grocery store."
        slack_service.post_message(CHANNEL_SUPPLIER_UPDATES, msg)

    def notify_out_of_stock(self, po: Dict[str, Any], supplier_name: str):
        msg = f"🚫 *Stock Alert:* Supplier *{supplier_name}* is unable to fulfill PO `{po['id']}` ({po['product_name']})."
        slack_service.post_message(CHANNEL_INVENTORY_ALERTS, msg)

    def notify_goods_received(self, po: Dict[str, Any], current_stock: float):
        msg = (
            f"✅ *Consignment Received & Verified!*\n"
            f"PO `{po['id']}` has been physically received.\n"
            f"Product: *{po['product_name']}*\n"
            f"Received Quantity: *+{po['quantity']} {po.get('unit', 'kg')}*\n"
            f"Updated Stock Level: *{current_stock} {po.get('unit', 'kg')}*\n"
            f"Inventory database successfully updated."
        )
        slack_service.post_message(CHANNEL_INVENTORY_REPORTS, msg)
        slack_service.post_message(CHANNEL_ADMIN_APPROVALS, msg)
        logger.info(f"[{self.name}] Posted goods received confirmation for PO {po['id']}")

    def notify_rejection(self, po: Dict[str, Any], admin_id: str):
        msg = f"❌ *Purchase Order Rejected:* PO `{po['id']}` for {po['product_name']} was rejected by Admin <@{admin_id}>. Procurement halted."
        slack_service.post_message(CHANNEL_ADMIN_APPROVALS, msg)
        logger.info(f"[{self.name}] Posted PO rejection notice for PO {po['id']}")

notification_agent = NotificationAgent()
