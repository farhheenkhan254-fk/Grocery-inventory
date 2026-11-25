import logging
from typing import Dict, Any
from tools.notification_tools import format_low_stock_alert_blocks
from slack.slack_app import slack_service, CHANNEL_INVENTORY_ALERTS
from services.email_service import email_service

logger = logging.getLogger("smart_grocery.agents.alert")

class AlertAgent:
    """
    Alert Agent:
    - Sends Slack notifications to Admin in #inventory-alerts.
    - Includes product name, current stock, minimum stock, and suggested reorder quantity.
    """
    def __init__(self):
        self.name = "Alert Agent"

    def send_low_stock_alert(self, product: Dict[str, Any], reorder_plan: Dict[str, Any]) -> Dict[str, Any]:
        payload = format_low_stock_alert_blocks(product, reorder_plan)
        res = slack_service.post_message(
            channel=CHANNEL_INVENTORY_ALERTS,
            text=payload["text"],
            blocks=payload["blocks"]
        )
        email_sent = email_service.notify_low_stock_to_admin(product, reorder_plan)
        logger.info(f"[{self.name}] Sent low stock alert for {product.get('name') or product.get('product_name')} to #{CHANNEL_INVENTORY_ALERTS}")
        return {
            "success": True,
            "email_sent": email_sent,
            "channel": CHANNEL_INVENTORY_ALERTS,
            "message": payload["text"],
            "blocks": payload["blocks"]
        }

alert_agent = AlertAgent()
