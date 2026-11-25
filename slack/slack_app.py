import os
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.config import settings
from slack.interactive_buttons import interactive_handlers
from slack.commands import slack_commands

logger = logging.getLogger("smart_grocery.slack_app")

# Channel Constants
CHANNEL_INVENTORY_ALERTS = "inventory-alerts"
CHANNEL_ADMIN_APPROVALS = "admin-approvals"
CHANNEL_PURCHASE_ORDERS = "purchase-orders"
CHANNEL_SUPPLIER_UPDATES = "supplier-updates"
CHANNEL_INVENTORY_REPORTS = "inventory-reports"

ALL_CHANNELS = [
    CHANNEL_INVENTORY_ALERTS,
    CHANNEL_ADMIN_APPROVALS,
    CHANNEL_PURCHASE_ORDERS,
    CHANNEL_SUPPLIER_UPDATES,
    CHANNEL_INVENTORY_REPORTS,
]

class SlackSimulator:
    """
    Maintains simulated in-memory Slack channels for presentation demos,
    tests, and when Slack credentials are unavailable.
    """
    def __init__(self):
        self.channels: Dict[str, List[Dict[str, Any]]] = {ch: [] for ch in ALL_CHANNELS}

    def post(self, channel: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        ch_name = channel.replace("#", "")
        if ch_name not in self.channels:
            self.channels[ch_name] = []

        message_obj = {
            "id": msg_id,
            "channel": ch_name,
            "text": text,
            "blocks": blocks or [],
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "iso_time": datetime.utcnow().isoformat()
        }
        self.channels[ch_name].append(message_obj)
        logger.info(f"[SLACK DEMO -> #{ch_name}] {text}")
        return {"ok": True, "ts": str(time.time()), "message": message_obj}

    def get_messages(self, channel: str) -> List[Dict[str, Any]]:
        ch_name = channel.replace("#", "")
        return list(reversed(self.channels.get(ch_name, [])))

    def clear(self):
        for ch in self.channels:
            self.channels[ch].clear()

slack_simulator = SlackSimulator()

class SlackService:
    def __init__(self):
        self.simulator = slack_simulator
        self.bolt_app = None
        self.web_client = None
        self._init_real_slack_client()

    def _init_real_slack_client(self):
        if settings.is_slack_configured:
            try:
                from slack_bolt import App
                from slack_sdk import WebClient
                self.bolt_app = App(
                    token=settings.SLACK_BOT_TOKEN,
                    signing_secret=settings.SLACK_SIGNING_SECRET,
                    token_verification_enabled=False
                )
                self.web_client = WebClient(token=settings.SLACK_BOT_TOKEN)
                self._register_bolt_handlers()
                logger.info("Real Slack Bolt app initialized successfully.")
            except Exception as e:
                logger.warning(f"Could not initialize real Slack client: {e}. Falling back to demo mode.")

    def _register_bolt_handlers(self):
        if not self.bolt_app:
            return

        @self.bolt_app.action("approve_purchase_order")
        def on_approve(ack, body, client):
            ack()
            po_id = body["actions"][0]["value"]
            user_id = body["user"]["id"]
            res = interactive_handlers.handle_admin_approval(po_id, user_id, action="approve")
            client.chat_postMessage(
                channel=body["channel"]["id"],
                text=res["message"],
                thread_ts=body["message"]["ts"]
            )

        @self.bolt_app.action("reject_purchase_order")
        def on_reject(ack, body, client):
            ack()
            po_id = body["actions"][0]["value"]
            user_id = body["user"]["id"]
            res = interactive_handlers.handle_admin_approval(po_id, user_id, action="reject")
            client.chat_postMessage(
                channel=body["channel"]["id"],
                text=res["message"],
                thread_ts=body["message"]["ts"]
            )

        @self.bolt_app.action("supplier_confirm_available")
        def on_avail(ack, body, client):
            ack()
            po_id = body["actions"][0]["value"]
            user_id = body["user"]["id"]
            res = interactive_handlers.handle_supplier_response(po_id, user_id, is_available=True)
            client.chat_postMessage(
                channel=body["channel"]["id"],
                text=res["message"],
                thread_ts=body["message"]["ts"]
            )

        @self.bolt_app.action("supplier_out_of_stock")
        def on_oos(ack, body, client):
            ack()
            po_id = body["actions"][0]["value"]
            user_id = body["user"]["id"]
            res = interactive_handlers.handle_supplier_response(po_id, user_id, is_available=False)
            client.chat_postMessage(
                channel=body["channel"]["id"],
                text=res["message"],
                thread_ts=body["message"]["ts"]
            )

        @self.bolt_app.action("supplier_confirm_dispatch")
        def on_dispatch(ack, body, client):
            ack()
            po_id = body["actions"][0]["value"]
            user_id = body["user"]["id"]
            res = interactive_handlers.handle_supplier_dispatch(po_id, user_id)
            client.chat_postMessage(
                channel=body["channel"]["id"],
                text=res["message"],
                thread_ts=body["message"]["ts"]
            )

        @self.bolt_app.action("admin_confirm_goods_received")
        def on_recv(ack, body, client):
            ack()
            po_id = body["actions"][0]["value"]
            user_id = body["user"]["id"]
            res = interactive_handlers.handle_goods_receipt(po_id, user_id)
            client.chat_postMessage(
                channel=body["channel"]["id"],
                text=res["message"],
                thread_ts=body["message"]["ts"]
            )

        @self.bolt_app.command("/stock-check")
        def on_cmd_stock_check(ack, respond, command):
            ack()
            res = slack_commands.handle_stock_check()
            respond(res)

        @self.bolt_app.command("/pending-orders")
        def on_cmd_pending(ack, respond, command):
            ack()
            res = slack_commands.handle_pending_orders()
            respond(res)

        @self.bolt_app.command("/inventory-report")
        def on_cmd_report(ack, respond, command):
            ack()
            res = slack_commands.handle_inventory_report()
            respond(res)

    def start_socket_mode(self):
        """
        Runs the Slack Bolt App in Socket Mode for real-time live events.
        """
        if not settings.SLACK_APP_TOKEN or not settings.SLACK_BOT_TOKEN:
            logger.error("Cannot start Socket Mode: Missing SLACK_APP_TOKEN or SLACK_BOT_TOKEN in .env")
            print("\n❌ ERROR: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be configured in .env to run Slack live.\n")
            return

        if not self.bolt_app:
            self._init_real_slack_client()

        if not self.bolt_app:
            print("\n❌ ERROR: Failed to initialize Slack Bolt App.")
            return

        from slack_bolt.adapter.socket_mode import SocketModeHandler
        print("=" * 60)
        print("⚡ SMART GROCERY AGENT - SLACK SOCKET MODE BOT")
        print("   Listening for Slack actions, button clicks, and commands...")
        print("=" * 60)
        handler = SocketModeHandler(self.bolt_app, settings.SLACK_APP_TOKEN)
        handler.start()

    def post_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        retries: int = 2
    ) -> Dict[str, Any]:
        """
        Sends message to specified channel.
        Always logs into simulator (so UI and tests can see it),
        and if real Slack tokens are available, dispatches to Slack API with retry.
        """
        # Always record to demo simulator for dashboard viewing
        sim_res = self.simulator.post(channel, text, blocks)

        # If real Slack is configured, send via API
        if self.web_client and settings.is_slack_configured:
            ch_target = getattr(settings, f"SLACK_{channel.upper().replace('-', '_')}_CHANNEL", channel)
            for attempt in range(retries + 1):
                try:
                    kwargs = {"channel": ch_target, "text": text}
                    if blocks:
                        kwargs["blocks"] = blocks
                    api_res = self.web_client.chat_postMessage(**kwargs)
                    return {"ok": True, "api_response": api_res.data, "demo_id": sim_res["message"]["id"]}
                except Exception as e:
                    logger.warning(f"Slack post attempt {attempt+1} failed: {e}")
                    if attempt == retries:
                        logger.error(f"Failed to post to real Slack channel '{ch_target}' after {retries} retries.")

        return sim_res

    def simulate_button_action(
        self,
        action_id: str,
        po_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulates an interactive button click in demo mode.
        """
        if action_id in ["approve_purchase_order", "reject_purchase_order", "admin_confirm_goods_received"]:
            uid = user_id or "U0CL03S65SR"
            if action_id == "approve_purchase_order":
                return interactive_handlers.handle_admin_approval(po_id, uid, action="approve")
            elif action_id == "reject_purchase_order":
                return interactive_handlers.handle_admin_approval(po_id, uid, action="reject")
            elif action_id == "admin_confirm_goods_received":
                return interactive_handlers.handle_goods_receipt(po_id, uid)
        else:
            uid = user_id if (user_id and not user_id.startswith("U0CL03S") and not user_id.startswith("U_ADMIN")) else "U0CL94EJPU4"
            if action_id == "supplier_confirm_available":
                return interactive_handlers.handle_supplier_response(po_id, uid, is_available=True)
            elif action_id == "supplier_out_of_stock":
                return interactive_handlers.handle_supplier_response(po_id, uid, is_available=False)
            elif action_id == "supplier_confirm_dispatch":
                return interactive_handlers.handle_supplier_dispatch(po_id, uid)

        return {"success": False, "error": f"Unknown action: {action_id}"}

slack_service = SlackService()
