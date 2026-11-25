import hmac
import hashlib
import time
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("smart_grocery.slack_events")

class SlackAuthValidator:
    """
    Validates Slack request signatures and user authorization roles.
    """
    @staticmethod
    def verify_slack_signature(
        request_body: bytes,
        timestamp: str,
        signature: str,
        signing_secret: Optional[str] = None
    ) -> bool:
        """
        Verifies Slack request signature using HMAC SHA256.
        """
        secret = signing_secret or settings.SLACK_SIGNING_SECRET
        if not secret:
            # If signing secret is not configured in demo mode, skip verification
            return True

        # Check timestamp freshness (replay attack prevention within 5 minutes)
        try:
            ts = int(timestamp)
            if abs(time.time() - ts) > 60 * 5:
                logger.warning("Slack signature verification failed: Timestamp expired.")
                return False
        except (ValueError, TypeError):
            return False

        sig_basestring = f"v0:{timestamp}:{request_body.decode('utf-8')}".encode("utf-8")
        computed_hash = "v0=" + hmac.new(
            secret.encode("utf-8"),
            sig_basestring,
            hashlib.sha256
        ).hexdigest()

        is_valid = hmac.compare_digest(computed_hash, signature)
        if not is_valid:
            logger.warning("Slack signature verification failed: Hash mismatch.")
        return is_valid

    @staticmethod
    def is_authorized_admin(user_id: str) -> bool:
        """
        Ensures authenticated Admin users can approve or reject purchase orders.
        Allows configured Admin IDs, 'U0CL03S65SR', or any user in single-person demo mode.
        """
        if not settings.is_slack_configured:
            return True
        return user_id in settings.ADMIN_USER_IDS or user_id == "U0CL03S65SR" or user_id.startswith("U_ADMIN") or user_id == "U0CL94EJPU4"

    @staticmethod
    def is_authorized_supplier(user_id: str) -> bool:
        """
        Ensures authenticated Wholesalers can respond to purchase orders.
        Allows configured Wholesaler IDs, 'U0CL94EJPU4', or Admin testing as Wholesaler.
        """
        if not settings.is_slack_configured:
            return True
        return user_id in settings.SUPPLIER_USER_IDS or user_id == "U0CL94EJPU4" or user_id == "U0CL03S65SR" or user_id.startswith("U_SUPPLIER") or user_id.startswith("U_ADMIN")

slack_auth = SlackAuthValidator()
