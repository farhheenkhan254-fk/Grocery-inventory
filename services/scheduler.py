import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import settings
from services.stock_monitor import stock_monitor

logger = logging.getLogger("smart_grocery.scheduler")

class InventoryScheduler:
    def __init__(self, monitor_service=stock_monitor):
        self.scheduler = BackgroundScheduler(daemon=True)
        self.monitor_service = monitor_service
        self._is_running = False

    def start(self, interval_seconds: int = None):
        """
        Starts the APScheduler background stock monitoring job.
        """
        if self._is_running:
            logger.info("Scheduler already running.")
            return

        seconds = interval_seconds or settings.STOCK_MONITOR_INTERVAL_SECONDS
        self.scheduler.add_job(
            func=self.run_scheduled_scan,
            trigger=IntervalTrigger(seconds=seconds),
            id="inventory_stock_monitor_job",
            name="Periodic Grocery Stock Level Monitor",
            replace_existing=True
        )
        self.scheduler.start()
        self._is_running = True
        logger.info(f"APScheduler stock monitoring job started (interval: {seconds}s).")

    def stop(self):
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("APScheduler stopped.")

    def is_running(self) -> bool:
        return self._is_running

    def run_scheduled_scan(self):
        logger.info("Scheduled stock check triggered...")
        try:
            result = self.monitor_service.run_monitor_cycle()
            if result["low_stock_detected"] > 0:
                logger.info(f"Scan complete: {result['low_stock_detected']} items require reorder.")
        except Exception as e:
            logger.error(f"Error during scheduled stock check: {e}")

    def trigger_now(self):
        return self.monitor_service.run_monitor_cycle()

inventory_scheduler = InventoryScheduler()
