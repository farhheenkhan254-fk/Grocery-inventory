import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger("smart_grocery.email_service")

class EmailService:
    """
    Sends SMTP email notifications to Admin and Wholesalers.
    Reports failure when delivery is disabled or SMTP is unavailable.
    """
    def __init__(self):
        self.sent_emails: List[Dict[str, Any]] = []

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> bool:
        email_record = {
            "to": to_email,
            "subject": subject,
            "body": body_text,
        }
        self.sent_emails.append(email_record)

        if not settings.EMAIL_NOTIFICATIONS_ENABLED:
            logger.info("Email notifications are disabled; no email was sent.")
            return False

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            try:
                clean_user = settings.SMTP_USER.strip()
                clean_pwd = settings.SMTP_PASSWORD.replace(" ", "").strip()

                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = clean_user
                msg["To"] = to_email

                part1 = MIMEText(body_text, "plain")
                msg.attach(part1)

                if body_html:
                    part2 = MIMEText(body_html, "html")
                    msg.attach(part2)

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                    server.starttls()
                    server.login(clean_user, clean_pwd)
                    server.sendmail(clean_user, to_email, msg.as_string())

                logger.info(f"📧 [REAL EMAIL SENT] To: {to_email} | Subject: {subject}")
                print(f"📧 [REAL EMAIL SENT] To: {to_email} | Subject: {subject}")
                return True
            except (smtplib.SMTPException, OSError) as exc:
                logger.exception("Could not send email via SMTP.")
                print(f"⚠️ [SMTP WARNING] Could not send email ({type(exc).__name__}).")
                return False
        else:
            logger.warning(
                "SMTP credentials are missing; email was not sent to %s.",
                to_email,
            )
            print("⚠️ [SMTP WARNING] Email not sent: SMTP credentials are missing.")
            return False

    def notify_po_approved_to_wholesaler(self, po: Dict[str, Any]):
        """Notifies Wholesaler of newly approved Purchase Order via email."""
        to_email = settings.SUPPLIER_EMAIL
        subject = f"🛒 New Approved Purchase Order: {po.get('id')} ({po.get('product_name')})"
        body = (
            f"Dear Wholesaler / Supplier,\n\n"
            f"An approved Purchase Order has been issued by Store Admin.\n\n"
            f"PO Number: {po.get('id')}\n"
            f"Product: {po.get('product_name')}\n"
            f"Quantity: {po.get('quantity')} {po.get('unit', 'kg')}\n\n"
            f"Please review in Slack channel #purchase-orders and confirm availability.\n\n"
            f"Best regards,\nSmart Grocery Procurement Agent"
        )
        self.send_email(to_email, subject, body)

    def notify_low_stock_to_admin(
        self, product: Dict[str, Any], reorder_plan: Dict[str, Any]
    ) -> bool:
        """Notifies Admin when inventory falls to or below its minimum threshold."""
        product_name = product.get("name") or product.get("product_name")
        unit = product.get("unit", "kg")
        subject = f"⚠️ Low Stock Alert: {product_name}"
        body = (
            f"Hello Admin,\n\n"
            f"{product_name} has reached a low stock level and needs review.\n\n"
            f"Current Stock: {product.get('current_stock')} {unit}\n"
            f"Minimum Stock: {product.get('minimum_stock')} {unit}\n"
            f"Suggested Reorder: {reorder_plan.get('suggested_quantity')} {unit}\n\n"
            f"Please review the purchase request in Slack #admin-approvals.\n\n"
            f"Smart Grocery Inventory Agent"
        )
        return self.send_email(settings.ADMIN_EMAIL, subject, body)

    def notify_availability_to_admin(self, po: Dict[str, Any], is_available: bool):
        """Notifies Admin whether goods are in stock or out of stock."""
        to_email = settings.ADMIN_EMAIL
        if is_available:
            subject = f"✅ Stock Confirmed by Wholesaler: PO {po.get('id')} ({po.get('product_name')})"
            body = (
                f"Hello Admin,\n\n"
                f"Wholesaler has confirmed that {po.get('product_name')} is IN STOCK for PO {po.get('id')}.\n"
                f"Consignment is being prepared for dispatch.\n\n"
                f"Smart Grocery Supplier Agent"
            )
        else:
            subject = f"🚫 URGENT: Wholesaler Out of Stock for PO {po.get('id')} ({po.get('product_name')})"
            body = (
                f"Hello Admin,\n\n"
                f"Wholesaler has reported that {po.get('product_name')} is OUT OF STOCK for PO {po.get('id')}.\n"
                f"Please check Slack channel #inventory-alerts to select an alternative supplier.\n\n"
                f"Smart Grocery Supplier Agent"
            )
        self.send_email(to_email, subject, body)

    def notify_dispatch_to_admin(self, po: Dict[str, Any]):
        """Notifies Admin that consignment has been dispatched and is in transit."""
        to_email = settings.ADMIN_EMAIL
        subject = f"🚚 Consignment Dispatched: PO {po.get('id')} ({po.get('product_name')})"
        body = (
            f"Hello Admin,\n\n"
            f"The wholesaler has dispatched {po.get('quantity')} {po.get('unit', 'kg')} of {po.get('product_name')}.\n"
            f"Consignment is currently in transit to the grocery store dock.\n\n"
            f"Note: Store inventory will update only after you physically confirm goods receipt.\n\n"
            f"Smart Grocery Notification Agent"
        )
        self.send_email(to_email, subject, body)

    def notify_goods_receipt_to_all(self, po: Dict[str, Any], new_stock: float):
        """Notifies both Admin and Wholesaler of successful delivery and restocking."""
        subject = f"🎉 Consignment Received & Restocked: PO {po.get('id')} ({po.get('product_name')})"
        body = (
            f"Purchase Order {po.get('id')} has been physically verified and received at store dock.\n\n"
            f"Product: {po.get('product_name')}\n"
            f"Received Quantity: +{po.get('quantity')} {po.get('unit', 'kg')}\n"
            f"New Inventory Stock: {new_stock} {po.get('unit', 'kg')}\n\n"
            f"Transaction complete.\nSmart Grocery Inventory Agent"
        )
        self.send_email(settings.ADMIN_EMAIL, subject, body)
        self.send_email(settings.SUPPLIER_EMAIL, subject, body)

email_service = EmailService()
