from typing import Dict, Any, List, Optional
import json

def format_low_stock_alert_blocks(product: Dict[str, Any], reorder_plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs a Slack Block Kit payload for an immediate low-stock alert.
    """
    prod_name = product.get("name") or product.get("product_name")
    curr_stock = product.get("current_stock")
    min_stock = product.get("minimum_stock")
    unit = product.get("unit", "units")
    sugg_qty = reorder_plan.get("suggested_quantity", product.get("reorder_quantity"))
    urgency = reorder_plan.get("urgency", "MEDIUM")

    emoji = "🚨" if urgency == "CRITICAL" else "⚠️"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} Low Stock Alert: {prod_name}", "emoji": True}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Product:*\n{prod_name}"},
                {"type": "mrkdwn", "text": f"*Category:*\n{product.get('category', 'Grocery')}"},
                {"type": "mrkdwn", "text": f"*Current Stock:*\n*{curr_stock} {unit}*"},
                {"type": "mrkdwn", "text": f"*Minimum Threshold:*\n{min_stock} {unit}"},
                {"type": "mrkdwn", "text": f"*Suggested Reorder:*\n*{sugg_qty} {unit}*"},
                {"type": "mrkdwn", "text": f"*Urgency Level:*\n`{urgency}`"}
            ]
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "🤖 *Inventory Monitoring Agent* • Automatic threshold scan"}
            ]
        }
    ]
    fallback = f"🚨 LOW STOCK ALERT: {prod_name} is at {curr_stock} {unit} (Min: {min_stock} {unit}). Suggested reorder: {sugg_qty} {unit}."
    return {"text": fallback, "blocks": blocks}

def format_admin_approval_blocks(po: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs a Slack Block Kit payload with interactive Approve and Reject buttons for the Admin.
    """
    po_id = po.get("id")
    prod_name = po.get("product_name")
    qty = po.get("quantity")
    unit = po.get("unit", "units")
    supplier_name = po.get("supplier_name", "Primary Supplier")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📋 Approval Required: Purchase Order {po_id}", "emoji": True}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"A purchase request has been planned for *{prod_name}*. Please review and authorize procurement."
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Order ID:*\n`{po_id}`"},
                {"type": "mrkdwn", "text": f"*Item:*\n{prod_name}"},
                {"type": "mrkdwn", "text": f"*Order Quantity:*\n*{qty} {unit}*"},
                {"type": "mrkdwn", "text": f"*Assigned Supplier:*\n{supplier_name}"},
                {"type": "mrkdwn", "text": f"*Status:*\n`PENDING_APPROVAL`"},
                {"type": "mrkdwn", "text": "*Authorization:*\n`Admin Only`"}
            ]
        },
        {
            "type": "actions",
            "block_id": f"approval_actions_{po_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve Purchase", "emoji": True},
                    "style": "primary",
                    "value": po_id,
                    "action_id": "approve_purchase_order"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Reject Request", "emoji": True},
                    "style": "danger",
                    "value": po_id,
                    "action_id": "reject_purchase_order"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "🔒 *Safety rule:* Agentic AI cannot auto-execute orders without Admin sign-off."}
            ]
        }
    ]
    fallback = f"📋 Admin Approval Request: PO {po_id} for {qty} {unit} of {prod_name}. Action required."
    return {"text": fallback, "blocks": blocks}

def format_supplier_po_blocks(po: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs a Slack Block Kit payload sent to the Wholesaler with Available and Out of Stock buttons.
    """
    po_id = po.get("id")
    prod_name = po.get("product_name")
    qty = po.get("quantity")
    unit = po.get("unit", "units")
    supplier_name = po.get("supplier_name", "Wholesaler")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📦 New Purchase Order: {po_id}", "emoji": True}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Hello *{supplier_name}*, we have an approved order request for immediate fulfillment:"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*PO Number:*\n`{po_id}`"},
                {"type": "mrkdwn", "text": f"*Product:*\n{prod_name}"},
                {"type": "mrkdwn", "text": f"*Requested Quantity:*\n*{qty} {unit}*"},
                {"type": "mrkdwn", "text": "*Delivery Term:*\nImmediate Dispatch"}
            ]
        },
        {
            "type": "actions",
            "block_id": f"supplier_actions_{po_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📦 In Stock - Confirm Availability", "emoji": True},
                    "style": "primary",
                    "value": po_id,
                    "action_id": "supplier_confirm_available"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🚫 Out of Stock", "emoji": True},
                    "style": "danger",
                    "value": po_id,
                    "action_id": "supplier_out_of_stock"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "📨 Sent by *Procurement Agent* via Automated Slack Gateway"}
            ]
        }
    ]
    fallback = f"📦 Purchase Order {po_id}: {qty} {unit} of {prod_name}. Please confirm stock availability."
    return {"text": fallback, "blocks": blocks}

def format_dispatch_action_blocks(po: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs a button for the supplier to confirm dispatch once goods are ready.
    """
    po_id = po.get("id")
    prod_name = po.get("product_name")
    qty = po.get("quantity")
    unit = po.get("unit", "units")

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"✅ *Availability Confirmed* for `{po_id}` ({qty} {unit} of {prod_name}).\nPlease confirm when the consignment leaves the warehouse:"
            }
        },
        {
            "type": "actions",
            "block_id": f"dispatch_actions_{po_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🚚 Confirm Consignment Dispatch", "emoji": True},
                    "style": "primary",
                    "value": po_id,
                    "action_id": "supplier_confirm_dispatch"
                }
            ]
        }
    ]
    fallback = f"🚚 Order {po_id} is ready for dispatch."
    return {"text": fallback, "blocks": blocks}

def format_goods_receipt_blocks(po: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs interactive button for Store Admin to confirm receipt of dispatched goods.
    """
    po_id = po.get("id")
    prod_name = po.get("product_name")
    qty = po.get("quantity")
    unit = po.get("unit", "units")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🚚 Consignment In Transit: {po_id}", "emoji": True}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"The supplier has dispatched *{qty} {unit}* of *{prod_name}*. Once physically verified at the loading dock, click below to update inventory."
            }
        },
        {
            "type": "actions",
            "block_id": f"receipt_actions_{po_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📥 Confirm Physical Goods Received", "emoji": True},
                    "style": "primary",
                    "value": po_id,
                    "action_id": "admin_confirm_goods_received"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "⚠️ *Inventory Rule:* Stock is updated only upon Admin receipt confirmation."}
            ]
        }
    ]
    fallback = f"🚚 PO {po_id} is in transit. Confirm receipt upon arrival."
    return {"text": fallback, "blocks": blocks}

def format_out_of_stock_alert_blocks(po: Dict[str, Any], alternatives: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Constructs an alert to the Admin when a supplier reports Out of Stock,
    offering alternative suppliers.
    """
    po_id = po.get("id")
    prod_name = po.get("product_name")
    supplier_name = po.get("supplier_name", "Supplier")

    alt_text = ""
    if alternatives:
        alt_list = [f"• *{alt['name']}* ({alt.get('contact_email', 'N/A')})" for alt in alternatives]
        alt_text = "\n*Recommended Alternative Wholesalers:*\n" + "\n".join(alt_list)
    else:
        alt_text = "\n*No alternative wholesalers currently registered for this product line.*"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🚫 Supplier Out of Stock: {po_id}", "emoji": True}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Supplier *{supplier_name}* has reported that *{prod_name}* is *OUT OF STOCK*.\nOrder `{po_id}` could not be fulfilled by this vendor.{alt_text}"
            }
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "🤖 *Supplier Agent* • Notified Admin and triggered alternative routing."}
            ]
        }
    ]
    fallback = f"🚫 OUT OF STOCK: {supplier_name} cannot fulfill {prod_name} for order {po_id}."
    return {"text": fallback, "blocks": blocks}
