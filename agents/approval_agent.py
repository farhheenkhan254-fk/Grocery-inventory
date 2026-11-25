import logging
from datetime import datetime
from typing import Dict, Any, Optional
from tools.notification_tools import format_admin_approval_blocks
from slack.slack_app import slack_service, CHANNEL_ADMIN_APPROVALS
from database.repository import repo
from slack.events import slack_auth

logger = logging.getLogger("smart_grocery.agents.approval")

class AdminApprovalAgent:
    """
    Admin Approval Agent:
    - Sends interactive Slack messages with Approve and Reject buttons.
    - Waits for authenticated Admin action.
    - Prevents unauthorized users from approving orders.
    - Stores approval status and timestamp.
    """
    def __init__(self):
        self.name = "Admin Approval Agent"

    def request_approval(self, po: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends interactive approval card to Admin in #admin-approvals.
        """
        payload = format_admin_approval_blocks(po)
        slack_service.post_message(
            channel=CHANNEL_ADMIN_APPROVALS,
            text=payload["text"],
            blocks=payload["blocks"]
        )
        logger.info(f"[{self.name}] Dispatched approval request for PO {po['id']} to #{CHANNEL_ADMIN_APPROVALS}")
        return {
            "success": True,
            "po_id": po["id"],
            "channel": CHANNEL_ADMIN_APPROVALS,
            "status": "AWAITING_ADMIN_DECISION"
        }

    def process_decision(self, po_id: str, admin_user_id: str, action: str) -> Dict[str, Any]:
        """
        Validates authorization, updates approval state in DB.
        """
        if not slack_auth.is_authorized_admin(admin_user_id):
            logger.warning(f"[{self.name}] Unauthorized approval attempt by {admin_user_id}")
            return {
                "success": False,
                "error": "UNAUTHORIZED",
                "message": f"Action blocked: <@{admin_user_id}> is not authorized as an Admin."
            }

        status = "APPROVED" if action.lower() == "approve" else "REJECTED"
        updated_po = repo.record_approval(po_id, admin_id=admin_user_id, status=status)

        if not updated_po:
            return {"success": False, "message": f"Could not approve/reject PO {po_id}."}

        logger.info(f"[{self.name}] Admin {admin_user_id} {status} PO {po_id}")
        return {
            "success": True,
            "status": status,
            "po": updated_po,
            "approved_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }

approval_agent = AdminApprovalAgent()
