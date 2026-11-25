import os
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.connection import init_db
from database.repository import repo
from app.config import settings
from graph.builder import grocery_graph, workflow_controller
from slack.slack_app import (
    slack_service,
    slack_simulator,
    CHANNEL_INVENTORY_ALERTS,
    CHANNEL_ADMIN_APPROVALS,
    CHANNEL_PURCHASE_ORDERS,
    CHANNEL_SUPPLIER_UPDATES,
    CHANNEL_INVENTORY_REPORTS,
    ALL_CHANNELS,
)
from services.stock_monitor import stock_monitor
from services.scheduler import inventory_scheduler
from services.audit_service import audit_service

# Initialize database on startup
init_db()

def run_cli_scenario(scenario_number: int):
    """
    Executes presentation scenarios directly in the CLI terminal.
    """
    print("=" * 70)
    print("🛒 SMART GROCERY INVENTORY & PROCUREMENT MANAGEMENT SYSTEM")
    print("   Agentic AI • LangGraph • Multi-Agent Collaboration • Slack API")
    print("=" * 70)

    if scenario_number == 1:
        print("\n🚀 EXECUTING SCENARIO 1: Full Procurement & Goods Receipt Lifecycle")
        print("Product: Basmati Rice | Initial Stock: 20 kg | Minimum Threshold: 10 kg")
        print("-" * 70)

        # Step 1: Stock drops to 5 kg
        print("\n[STEP 1] Simulating inventory consumption...")
        repo.set_stock("Basmati Rice", 5.0)
        p = repo.get_product_by_name("Basmati Rice")
        print(f" -> Current Stock for {p['name']}: {p['current_stock']} {p['unit']} (Threshold: {p['minimum_stock']} {p['unit']})")

        # Step 2: Inventory Agent detects low stock
        print("\n[STEP 2] Running LangGraph Workflow...")
        state = workflow_controller.run_check("Basmati Rice")
        po_id = state.get("po_id")
        print(f" -> Stock Status: {state.get('stock_status')}")
        print(f" -> Suggested Reorder: {state.get('order_quantity')} {state.get('unit')}")
        print(f" -> Generated Draft PO: {po_id}")
        print(" -> Alert Agent posted to #inventory-alerts & Admin Approval requested in #admin-approvals")

        # Step 3: Admin Approves
        print(f"\n[STEP 3] Admin clicks [Approve] for PO {po_id}...")
        appr_res = slack_service.simulate_button_action("approve_purchase_order", po_id, "U_ADMIN_01")
        print(f" -> Approval recorded: {appr_res.get('status')}. Audit log saved.")

        # Step 4: Procurement Agent sends to Wholesaler
        print(f"\n[STEP 4] Procurement Agent dispatches PO {po_id} to Wholesaler Apex Agro in #purchase-orders...")
        from agents.procurement_agent import procurement_agent
        procurement_agent.dispatch_to_wholesaler(repo.get_purchase_order(po_id))

        # Step 5: Wholesaler Confirms Available
        print(f"\n[STEP 5] Wholesaler clicks [In Stock - Available] for PO {po_id}...")
        avail_res = slack_service.simulate_button_action("supplier_confirm_available", po_id, "U_SUPPLIER_APEX")
        print(f" -> Wholesaler response: AVAILABLE. Dispatch button prompted.")

        # Step 6: Wholesaler Confirms Dispatch
        print(f"\n[STEP 6] Wholesaler clicks [Confirm Consignment Dispatch] for PO {po_id}...")
        disp_res = slack_service.simulate_button_action("supplier_confirm_dispatch", po_id, "U_SUPPLIER_APEX")
        p_check = repo.get_product_by_name("Basmati Rice")
        print(f" -> PO Status: DISPATCHED. Goods in transit.")
        print(f" -> Business Rule Check: Stock at dispatch time is {p_check['current_stock']} {p_check['unit']} (Unchanged!).")

        # Step 7: Admin Confirms Physical Goods Received
        print(f"\n[STEP 7] Goods arrive at store dock. Admin clicks [Confirm Physical Goods Received]...")
        recv_res = slack_service.simulate_button_action("admin_confirm_goods_received", po_id, "U_ADMIN_01")
        p_final = repo.get_product_by_name("Basmati Rice")
        print(f" -> Goods Received! Stock updated: {recv_res.get('product', {}).get('current_stock')} {p_final['unit']}")
        print(f" -> Final Stock in DB: {p_final['current_stock']} {p_final['unit']} (Restocked from 5 kg to 55 kg!)")
        print("\n✅ SCENARIO 1 SUCCESSFULLY COMPLETED!\n")

    elif scenario_number == 2:
        print("\n🚫 EXECUTING SCENARIO 2: Wholesaler Out of Stock & Alternative Routing")
        print("Product: Sugar | Initial Stock: 25 kg | Minimum Threshold: 10 kg")
        print("-" * 70)

        # Step 1: Stock drops to 4 kg
        print("\n[STEP 1] Setting Sugar stock to 4 kg (Threshold: 10 kg)...")
        repo.set_stock("Sugar", 4.0)

        # Step 2: Workflow runs
        print("\n[STEP 2] Running Inventory Monitoring & Admin Approval...")
        state = workflow_controller.run_check("Sugar")
        po_id = state.get("po_id")
        slack_service.simulate_button_action("approve_purchase_order", po_id, "U_ADMIN_01")
        from agents.procurement_agent import procurement_agent
        procurement_agent.dispatch_to_wholesaler(repo.get_purchase_order(po_id))

        # Step 3: Wholesaler clicks Out of Stock
        print(f"\n[STEP 3] Wholesaler Golden Harvest reports [Out of Stock] for PO {po_id}...")
        oos_res = slack_service.simulate_button_action("supplier_out_of_stock", po_id, "U_SUPPLIER_GOLDEN")
        po_updated = repo.get_purchase_order(po_id)
        print(f" -> PO Status: {po_updated['status']}")
        print(f" -> Admin notified in #inventory-alerts of stockout.")
        alts = oos_res.get("alternatives", [])
        print(f" -> Recommended Alternative Wholesalers found: {[a['name'] for a in alts]}")
        print("\n✅ SCENARIO 2 SUCCESSFULLY COMPLETED!\n")

def run_streamlit_app():
    import streamlit as st

    st.set_page_config(
        page_title="Smart Grocery Inventory & Procurement Agent",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom styling
    st.markdown("""
        <style>
        .metric-card {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 12px;
            border-left: 5px solid #007bff;
        }
        .stButton>button {
            border-radius: 6px;
            font-weight: 600;
        }
        .slack-message-box {
            background-color: #1a1d21;
            color: #d1d2d3;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        </style>
    """, unsafe_allow_html=True)

    # ---------------- Sidebar ---------------- #
    st.sidebar.title("🛒 Smart Grocery Agent")
    st.sidebar.caption("Agentic AI • LangGraph • Slack Bolt")

    # Status Indicators
    slack_mode = "🟢 Live Slack API" if settings.is_slack_configured else "🟡 Demo Mode (Simulated Slack)"
    st.sidebar.info(f"**Slack Interface:** {slack_mode}")

    llm_mode = f"🟢 Groq ({settings.GROQ_MODEL})" if settings.is_groq_configured else "⚡ Rule-Based Deterministic Fallback"
    st.sidebar.caption(f"**LLM Reasoner:** {llm_mode}")

    db_type = "MySQL" if settings.DATABASE_URL.startswith("mysql") else "SQLite (smart_grocery.db)"
    st.sidebar.caption(f"**Database:** {db_type}")

    # Scheduler controls
    scheduler_running = inventory_scheduler.is_running()
    st.sidebar.markdown("---")
    st.sidebar.subheader("⏱️ Auto-Stock Monitoring")
    col_s1, col_s2 = st.sidebar.columns(2)
    if col_s1.button("Start Monitor" if not scheduler_running else "Running ✅", disabled=scheduler_running):
        inventory_scheduler.start()
        st.sidebar.success("Scheduler active!")
        st.rerun()
    if col_s2.button("Stop Monitor", disabled=not scheduler_running):
        inventory_scheduler.stop()
        st.sidebar.warning("Scheduler paused.")
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎬 Presentation Scenarios")
    if st.sidebar.button("🚀 Run Scenario 1 (Basmati Rice Demo)", width="stretch"):
        with st.spinner("Executing Scenario 1 agent chain..."):
            repo.set_stock("Basmati Rice", 5.0)
            res = workflow_controller.run_full_scenario("Basmati Rice", admin_approval="APPROVED", supplier_available=True)
            st.session_state["scenario_result"] = res
            st.session_state["scenario_name"] = "Scenario 1: Basmati Rice (Restocked to 55 kg)"
            st.success("Scenario 1 completed!")
            st.rerun()

    if st.sidebar.button("🚫 Run Scenario 2 (Supplier Out of Stock)", width="stretch"):
        with st.spinner("Executing Scenario 2 (Out of stock handling)..."):
            repo.set_stock("Sugar", 4.0)
            res = workflow_controller.run_full_scenario("Sugar", admin_approval="APPROVED", supplier_available=False)
            st.session_state["scenario_result"] = res
            st.session_state["scenario_name"] = "Scenario 2: Sugar (Out of Stock alert to Admin)"
            st.warning("Scenario 2 executed: Out of stock alert sent to Admin.")
            st.rerun()

    if st.sidebar.button("🔄 Reset Sample Database", width="stretch"):
        from database.connection import INITIAL_PRODUCTS
        for product in INITIAL_PRODUCTS:
            repo.set_stock(product["name"], product["current_stock"])
        slack_simulator.clear()
        st.sidebar.success("Catalog reset to initial baseline values.")
        st.rerun()

    # ---------------- Top Metrics ---------------- #
    products = repo.get_all_products()
    orders = repo.get_all_purchase_orders()
    low_stock_items = [p for p in products if p["is_low_stock"]]
    active_orders = [o for o in orders if o["status"] not in ["RECEIVED", "REJECTED"]]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Catalog SKUs", len(products))
    m2.metric("Items Low / Out of Stock", len(low_stock_items), delta=f"-{len(low_stock_items)}" if low_stock_items else "0", delta_color="inverse")
    m3.metric("Active Purchase Orders", len(active_orders))
    m4.metric("Completed Restocks", sum(1 for o in orders if o["status"] == "RECEIVED"))

    # ---------------- Tabs ---------------- #
    tab1, tab2, tab3, tab4 = st.tabs([
        "🛒 Inventory & Simulator",
        "💬 Slack Channels (Interactive)",
        "🕸️ LangGraph Architecture & State",
        "📋 Purchase Orders & Audit Trail"
    ])

    # ---------------- Tab 1: Inventory & Simulator ---------------- #
    with tab1:
        st.subheader("📦 Grocery Inventory Catalog")
        
        # Format table data
        formatted_products = []
        for p in products:
            status_badge = "🔴 Low Stock" if p["is_low_stock"] else "🟢 Sufficient"
            formatted_products.append({
                "ID": p["id"],
                "Product Name": p["name"],
                "Category": p["category"],
                "Current Stock": f"{p['current_stock']} {p['unit']}",
                "Minimum Threshold": f"{p['minimum_stock']} {p['unit']}",
                "Reorder Quantity": f"{p['reorder_quantity']} {p['unit']}",
                "Status": status_badge,
                "Supplier": p["supplier_name"]
            })
        st.dataframe(
            formatted_products,
            hide_index=True,
            alt="Grocery inventory catalog with stock levels and suppliers",
        )

        st.markdown("---")
        st.subheader("🧪 Stock Adjustment Simulator")
        st.caption("Change stock level to trigger automated Inventory Monitoring and LangGraph agent workflow.")

        with st.form("stock_simulator_form"):
            col_f1, col_f2 = st.columns(2)
            prod_names = [p["name"] for p in products]
            selected_name = col_f1.selectbox("Select Grocery Item", prod_names, index=0)
            target_prod = next(p for p in products if p["name"] == selected_name)
            new_stock_val = col_f2.number_input(
                f"Enter new stock level ({target_prod['unit']})",
                min_value=0.0,
                max_value=200.0,
                value=float(target_prod["current_stock"]),
                step=1.0
            )
            submit_stock = st.form_submit_button(
                "Update Stock & Run Agent Workflow", width="stretch"
            )

        if submit_stock:
            repo.set_stock(selected_name, new_stock_val)
            workflow_res = workflow_controller.run_check(selected_name)
            st.session_state["last_workflow"] = workflow_res
            st.session_state["last_low_stock_email_sent"] = (
                workflow_res.get("email_sent")
                if workflow_res.get("stock_status") in ("LOW_STOCK", "OUT_OF_STOCK")
                else None
            )
            st.success(f"Stock for '{selected_name}' updated to {new_stock_val} {target_prod['unit']}.")
            st.rerun()

        if st.session_state.get("last_low_stock_email_sent") is True:
            st.success("Low-stock alert email was sent to the configured admin address.")
        elif st.session_state.get("last_low_stock_email_sent") is False:
            st.warning(
                "The Slack alert was created, but the low-stock email was not sent. "
                "Check SMTP settings and the Streamlit terminal for the SMTP warning."
            )

        if "scenario_name" in st.session_state:
            st.info(f"Last executed: **{st.session_state['scenario_name']}**")
            with st.expander("View Workflow Execution Log", expanded=True):
                res = st.session_state.get("scenario_result", {})
                for msg in res.get("messages", []):
                    st.write(f"• {msg}")

    # ---------------- Tab 2: Slack Channels ---------------- #
    with tab2:
        st.subheader("💬 Slack Workspace Channels")
        st.caption("Primary communication interface for Store Admin and Wholesalers with interactive action buttons.")

        sub_tabs = st.tabs([
            "🚨 #inventory-alerts",
            "📋 #admin-approvals",
            "📦 #purchase-orders",
            "🚚 #supplier-updates",
            "📊 #inventory-reports"
        ])

        channel_map = {
            0: CHANNEL_INVENTORY_ALERTS,
            1: CHANNEL_ADMIN_APPROVALS,
            2: CHANNEL_PURCHASE_ORDERS,
            3: CHANNEL_SUPPLIER_UPDATES,
            4: CHANNEL_INVENTORY_REPORTS,
        }

        for idx, sub_tab in enumerate(sub_tabs):
            ch_name = channel_map[idx]
            with sub_tab:
                msgs = slack_simulator.get_messages(ch_name)
                if not msgs:
                    st.info(f"No messages posted to #{ch_name} yet.")
                for m in msgs:
                    with st.container(border=True):
                        st.markdown(f"**[Bot @ {m['timestamp']}]**")
                        st.markdown(m["text"])

                        # Render interactive buttons if present
                        blocks = m.get("blocks", [])
                        for b in blocks:
                            if b.get("type") == "actions":
                                cols = st.columns(len(b.get("elements", [])))
                                for btn_idx, elem in enumerate(b.get("elements", [])):
                                    action_id = elem.get("action_id")
                                    btn_text = elem.get("text", {}).get("text", "Action")
                                    po_id = elem.get("value")

                                    if cols[btn_idx].button(btn_text, key=f"btn_{m['id']}_{btn_idx}"):
                                        res = slack_service.simulate_button_action(action_id, po_id)
                                        if res.get("success"):
                                            st.success(res.get("message", "Action completed!"))
                                        else:
                                            st.error(res.get("message", "Action failed."))
                                        st.rerun()

    # ---------------- Tab 3: LangGraph Architecture ---------------- #
    with tab3:
        st.subheader("🕸️ LangGraph StateGraph Architecture")
        st.markdown("""
        ```mermaid
        graph TD
            START([START]) --> IV[Input Validation]
            IV --> SA[Supervisor Agent]
            SA --> PA[Planner Agent]
            PA --> IMA[Inventory Monitoring Agent]
            IMA --> CR1{Stock <= Min?}
            CR1 -- Yes (Low Stock) --> AA[Alert Agent]
            CR1 -- No (Sufficient) --> END1([END])
            AA --> ADM[Admin Approval Agent<br/>(Human-in-the-Loop)]
            ADM --> CR2{Admin Decision?}
            CR2 -- Rejected --> END2([END])
            CR2 -- Approved --> PROC[Procurement Agent]
            PROC --> SUP[Supplier Agent]
            SUP --> CR3{Supplier Status?}
            CR3 -- Out of Stock --> OOS[Notify Admin & Recommend Alts]
            OOS --> END3([END])
            CR3 -- Available --> DISP[Supplier Dispatch]
            DISP --> GRC[Goods Received Confirmation<br/>(Admin In-Dock Signoff)]
            GRC --> IUA[Inventory Update Agent]
            IUA --> END4([END])
        ```
        """)

        st.subheader("🔍 Active State & Checkpointer Inspector")
        if "last_workflow" in st.session_state:
            st.json(st.session_state["last_workflow"])
        elif "scenario_result" in st.session_state:
            st.json(st.session_state["scenario_result"])
        else:
            st.info("Run a stock check in Tab 1 or trigger a Scenario from the sidebar to inspect live StateGraph variables.")

    # ---------------- Tab 4: Purchase Orders & Audit Trail ---------------- #
    with tab4:
        st.subheader("📋 Purchase Order Registry")
        if orders:
            po_display = []
            for o in orders:
                po_display.append({
                    "PO Number": o["id"],
                    "Product": o["product_name"],
                    "Supplier": o["supplier_name"],
                    "Quantity": f"{o['quantity']} {o['unit']}",
                    "Current Status": o["status"],
                    "Created At": o["created_at"],
                    "Approval": o.get("approval_status") or "PENDING",
                    "Supplier Response": o.get("availability_status") or "PENDING",
                    "Dispatch": o.get("dispatch_status") or "PENDING",
                })
            st.dataframe(
                po_display,
                width="stretch",
                hide_index=True,
                alt="Purchase orders and their approval and fulfillment statuses",
            )
        else:
            st.info("No purchase orders registered yet.")

        st.markdown("---")
        st.subheader("🛡️ Enterprise Audit Logs (ISO/SOX Compliance)")
        audit_logs = audit_service.get_recent_logs(limit=40)
        if audit_logs:
            st.dataframe(
                audit_logs,
                width="stretch",
                hide_index=True,
                alt="Recent inventory and procurement audit events",
            )
        else:
            st.info("No audit logs recorded yet.")

def main():
    parser = argparse.ArgumentParser(description="Smart Grocery Agentic AI System")
    parser.add_argument("--cli", action="store_true", help="Run in command-line interface mode")
    parser.add_argument("--scenario", type=int, choices=[1, 2], help="Run presentation demo scenario 1 or 2")
    args, unknown = parser.parse_known_args()

    if args.cli or args.scenario:
        scenario = args.scenario or 1
        run_cli_scenario(scenario)
    else:
        run_streamlit_app()

if __name__ == "__main__":
    main()
