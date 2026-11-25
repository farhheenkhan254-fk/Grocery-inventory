import logging
from typing import Dict, Any
from tools.inventory_tools import check_stock_status, receive_goods_and_update_stock
from services.audit_service import audit_service

logger = logging.getLogger("smart_grocery.agents.inventory")

class InventoryAgent:
    """
    Inventory Monitoring Agent:
    - Monitors grocery products.
    - Checks current stock against minimum stock threshold.
    - Detects low-stock and out-of-stock conditions.
    - Updates stock in database when physical goods are received.
    """
    def __init__(self):
        self.name = "Inventory Monitoring Agent"

    def check_product(self, product_name: str) -> Dict[str, Any]:
        """
        Inspects current stock and threshold.
        """
        info = check_stock_status(product_name)
        audit_service.record_event(
            event_type="STOCK_CHECK",
            entity_type="PRODUCT",
            entity_id=str(info.get("product_id", "N/A")),
            actor=self.name,
            details=info
        )
        logger.info(f"[{self.name}] Stock check for '{product_name}': {info.get('status')} ({info.get('current_stock')} {info.get('unit')})")
        return info

    def update_inventory_on_receipt(self, po_id: str, quantity: float, received_by: str = "Admin") -> Dict[str, Any]:
        """
        Increases stock upon confirmed receipt.
        """
        res = receive_goods_and_update_stock(po_id, received_quantity=quantity, received_by=received_by)
        logger.info(f"[{self.name}] Updated inventory for PO {po_id}: {res.get('message')}")
        return res

inventory_agent = InventoryAgent()
