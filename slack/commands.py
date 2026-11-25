import logging
from typing import Dict, Any
from database.repository import repo
from tools.inventory_tools import scan_all_inventory
from slack.messages import build_inventory_report_blocks

logger = logging.getLogger("smart_grocery.commands")

class SlackCommandHandler:
    """
    Handles Slack Slash Commands:
    - /stock-check: scans catalog and returns items below threshold
    - /pending-orders: returns list of pending POs and approvals
    - /inventory-report: posts full inventory overview to #inventory-reports
    """
    @staticmethod
    def handle_stock_check() -> Dict[str, Any]:
        low_items = scan_all_inventory()
        if not low_items:
            return {
                "text": "✅ *Stock Check:* All grocery items are above their minimum thresholds.",
                "response_type": "ephemeral"
            }

        item_lines = [
            f"• *{item['product_name']}*: Current={item['current_stock']} {item['unit']}, Min={item['minimum_stock']} {item['unit']}"
            for item in low_items
        ]
        return {
            "text": f"⚠️ *Low Stock Detected ({len(low_items)} items):*\n" + "\n".join(item_lines),
            "response_type": "in_channel"
        }

    @staticmethod
    def handle_pending_orders() -> Dict[str, Any]:
        orders = repo.get_all_purchase_orders()
        pending = [o for o in orders if o["status"] in ["PENDING_APPROVAL", "SENT_TO_SUPPLIER", "DISPATCHED"]]

        if not pending:
            return {
                "text": "ℹ️ *Pending Orders:* No active purchase orders requiring attention.",
                "response_type": "ephemeral"
            }

        order_lines = [
            f"• *{o['id']}* - {o['product_name']} ({o['quantity']} {o['unit']}) → Status: `{o['status']}`"
            for o in pending
        ]
        return {
            "text": f"📋 *Active Purchase Orders ({len(pending)}):*\n" + "\n".join(order_lines),
            "response_type": "in_channel"
        }

    @staticmethod
    def handle_inventory_report() -> Dict[str, Any]:
        products = repo.get_all_products()
        orders = repo.get_all_purchase_orders()
        active = [o for o in orders if o["status"] != "RECEIVED" and o["status"] != "REJECTED"]
        return build_inventory_report_blocks(products, active)

slack_commands = SlackCommandHandler()
