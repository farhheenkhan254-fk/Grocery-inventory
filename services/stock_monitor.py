import logging
from typing import List, Dict, Any
from database.repository import repo
from tools.inventory_tools import scan_all_inventory

logger = logging.getLogger("smart_grocery.stock_monitor")

class StockMonitorService:
    def __init__(self, workflow_runner=None):
        self.workflow_runner = workflow_runner

    def check_and_detect_low_stock(self) -> List[Dict[str, Any]]:
        """
        Monitors all grocery products.
        Checks current stock against minimum stock.
        Identifies products requiring reorder.
        """
        items_needing_reorder = scan_all_inventory()
        detected = []

        for item in items_needing_reorder:
            # Skip if an active purchase order is already in progress
            if item["has_active_po"]:
                logger.info(f"Item '{item['product_name']}' is low stock but has an active PO in progress. Skipping duplicate.")
                continue

            detected.append(item)
            logger.warning(
                f"[STOCK ALERT] Low stock detected for '{item['product_name']}': "
                f"Current={item['current_stock']}, Minimum={item['minimum_stock']}"
            )

        return detected

    def run_monitor_cycle(self) -> Dict[str, Any]:
        """
        Executes one full stock scan cycle and optionally dispatches workflow triggers.
        """
        low_items = self.check_and_detect_low_stock()
        triggered_workflows = []

        if self.workflow_runner:
            for item in low_items:
                try:
                    res = self.workflow_runner(item["product_name"])
                    triggered_workflows.append({"product": item["product_name"], "result": res})
                except Exception as e:
                    logger.error(f"Error executing workflow for {item['product_name']}: {e}")

        return {
            "scanned_items_count": len(repo.get_all_products()),
            "low_stock_detected": len(low_items),
            "items": low_items,
            "triggered_workflows": triggered_workflows
        }

stock_monitor = StockMonitorService()
