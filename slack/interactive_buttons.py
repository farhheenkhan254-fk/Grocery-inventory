import logging
from typing import Dict, Any
from database.repository import repo
from tools.supplier_tools import process_supplier_decision, process_supplier_dispatch
from tools.inventory_tools import receive_goods_and_update_stock
from slack.events import slack_auth
from services.email_service import email_service

logger = logging.getLogger("smart_grocery.interactive_buttons")

class InteractiveButtonHandlers:
    """
    Handles Slack interactive button actions:
    - approve_purchase_order (Admin -> Dispatches PO to Wholesaler & sends Email)
    - reject_purchase_order (Admin -> Halts procurement)
    - supplier_confirm_available (Wholesaler -> Prompts Dispatch in #supplier-updates & sends Email)
    - supplier_out_of_stock (Wholesaler -> Alerts Admin with alternative suppliers & sends Email)
    - supplier_confirm_dispatch (Wholesaler -> Notifies #supplier-updates, prompts goods receipt in #admin-approvals & sends Email)
    - admin_confirm_goods_received (Admin -> Updates Stock in DB, notifies #inventory-reports & sends Restock Email)
    """
    def __init__(self, slack_dispatcher=None):
        self.slack_dispatcher = slack_dispatcher

    def handle_admin_approval(self, po_id: str, admin_user_id: str, action: str) -> Dict[str, Any]:
        """
        Admin clicks Approve or Reject.
        Validates Admin role, updates DB, records audit log, dispatches PO to Wholesaler,
        and triggers email notification.
        """
        if not slack_auth.is_authorized_admin(admin_user_id):
            logger.warning(f"Unauthorized approval attempt by user {admin_user_id} on PO {po_id}")
            return {
                "success": False,
                "error": "UNAUTHORIZED",
                "message": f"User <@{admin_user_id}> is not authorized as an Admin."
            }

        po_existing = repo.get_purchase_order(po_id)
        if po_existing and po_existing["status"] in ["APPROVED", "SENT_TO_SUPPLIER", "CONFIRMED_AVAILABLE", "DISPATCHED", "RECEIVED"]:
            return {
                "success": True,
                "status": po_existing["status"],
                "po": po_existing,
                "message": f"ℹ️ PO `{po_id}` is already *{po_existing['status']}*. Current order is in progress."
            }

        approval_status = "APPROVED" if action == "approve" else "REJECTED"
        updated_po = repo.record_approval(po_id, admin_id=admin_user_id, status=approval_status)

        if not updated_po:
            return {
                "success": False,
                "error": "INVALID_STATE",
                "message": f"PO {po_id} could not be updated."
            }

        logger.info(f"Admin {admin_user_id} {approval_status} PO {po_id}")

        if approval_status == "APPROVED":
            # Automatically dispatch PO to Wholesaler channel #purchase-orders
            from agents.procurement_agent import procurement_agent
            procurement_agent.dispatch_to_wholesaler(updated_po)

            # Send Email notification to Wholesaler
            email_service.notify_po_approved_to_wholesaler(updated_po)

            return {
                "success": True,
                "status": "APPROVED",
                "po": updated_po,
                "message": f"✅ Purchase Order `{po_id}` *APPROVED* by Admin. Sent to Wholesaler in #purchase-orders and emailed."
            }
        else:
            from agents.notification_agent import notification_agent
            notification_agent.notify_rejection(updated_po, admin_user_id)
            return {
                "success": True,
                "status": "REJECTED",
                "po": updated_po,
                "message": f"❌ Purchase order `{po_id}` was *REJECTED* by Admin. Procurement cancelled."
            }

    def handle_supplier_response(self, po_id: str, supplier_user_id: str, is_available: bool) -> Dict[str, Any]:
        """
        Wholesaler clicks Available or Out of Stock in #purchase-orders.
        Validates Supplier role, updates DB, prompts dispatch in #supplier-updates,
        and triggers email notification to Admin.
        """
        if not slack_auth.is_authorized_supplier(supplier_user_id):
            logger.warning(f"Unauthorized supplier action attempt by {supplier_user_id} on PO {po_id}")
            return {
                "success": False,
                "error": "UNAUTHORIZED",
                "message": f"User <@{supplier_user_id}> is not registered as a Wholesaler."
            }

        from agents.supplier_agent import supplier_agent
        res = supplier_agent.handle_stock_confirmation(po_id, is_available=is_available, user_id=supplier_user_id)

        po = res.get("po") or repo.get_purchase_order(po_id)
        if po:
            email_service.notify_availability_to_admin(po, is_available)

        return res

    def handle_supplier_dispatch(self, po_id: str, supplier_user_id: str) -> Dict[str, Any]:
        """
        Wholesaler confirms dispatch in #supplier-updates.
        Prompts physical goods receipt confirmation in #admin-approvals.
        Stock does NOT increase yet!
        """
        if not slack_auth.is_authorized_supplier(supplier_user_id):
            return {
                "success": False,
                "error": "UNAUTHORIZED",
                "message": f"User <@{supplier_user_id}> is not authorized to dispatch."
            }

        from agents.supplier_agent import supplier_agent
        res = supplier_agent.handle_dispatch(po_id, user_id=supplier_user_id)

        po = res.get("po") or repo.get_purchase_order(po_id)
        if po:
            email_service.notify_dispatch_to_admin(po)

        return res

    def handle_goods_receipt(self, po_id: str, admin_user_id: str) -> Dict[str, Any]:
        """
        Admin confirms physical receipt in #admin-approvals.
        Stock increases in DB, restock report posted to #inventory-reports,
        and confirmation email sent to both Admin and Wholesaler.
        """
        if not slack_auth.is_authorized_admin(admin_user_id):
            return {
                "success": False,
                "error": "UNAUTHORIZED",
                "message": f"User <@{admin_user_id}> is not authorized to confirm receipt."
            }

        po = repo.get_purchase_order(po_id)
        if not po:
            return {"success": False, "message": f"PO {po_id} not found."}

        res = receive_goods_and_update_stock(po_id, received_quantity=po["quantity"], received_by=admin_user_id)
        if not res.get("success"):
            return res

        product = res.get("product", {})
        new_stock = product.get("current_stock", 0.0)

        # Notify channels #inventory-reports and #admin-approvals
        from agents.notification_agent import notification_agent
        notification_agent.notify_goods_received(po, current_stock=new_stock)

        # Send confirmation email to both Admin and Wholesaler
        email_service.notify_goods_receipt_to_all(po, new_stock=new_stock)

        return {
            "success": True,
            "po": res.get("po"),
            "product": product,
            "message": f"✅ Consignment received! Restocked +{po['quantity']} {po.get('unit', 'kg')} in database. Current Stock: {new_stock} {po.get('unit', 'kg')}."
        }

interactive_handlers = InteractiveButtonHandlers()
