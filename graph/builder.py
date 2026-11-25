import logging
from typing import Optional, Dict, Any
from langgraph.graph import StateGraph, START, END
from graph.state import GroceryInventoryState
from graph.nodes import (
    input_validation_node,
    supervisor_node,
    planner_node,
    inventory_monitoring_node,
    alert_node,
    admin_approval_node,
    procurement_node,
    supplier_node,
    dispatch_node,
    notify_admin_oos_node,
    goods_received_confirmation_node,
    inventory_update_node,
)
from graph.routing import (
    route_after_inventory_check,
    route_after_admin_approval,
    route_after_supplier_check,
)
from graph.checkpoint import get_checkpointer

logger = logging.getLogger("smart_grocery.graph.builder")

def build_grocery_graph(checkpointer=None, interrupt_before=None):
    """
    Builds the complete LangGraph StateGraph for Smart Grocery Inventory & Procurement:

    START
      |
    Input Validation
      |
    Supervisor Agent
      |
    Planner Agent
      |
    Inventory Monitoring Agent
      |
    Conditional Routing
      |
      +-- Low Stock --> Alert Agent
      |
      +-- Sufficient Stock --> END
      |
    Admin Approval (Human-in-the-loop)
      |
      +-- Rejected --> END
      |
      +-- Approved
              |
         Procurement Agent
              |
         Supplier Agent
              |
         Conditional Routing
              |
         +----+----------------+
         |                     |
      Available             Out of Stock
         |                     |
      Dispatch             Notify Admin
         |                     |
      Goods Received          END
         |
      Inventory Update Agent
         |
         END
    """
    graph = StateGraph(GroceryInventoryState)

    # 1. Register All Nodes
    graph.add_node("input_validation", input_validation_node)
    graph.add_node("supervisor_agent", supervisor_node)
    graph.add_node("planner_agent", planner_node)
    graph.add_node("inventory_monitoring_agent", inventory_monitoring_node)
    graph.add_node("alert_agent", alert_node)
    graph.add_node("admin_approval", admin_approval_node)
    graph.add_node("procurement_agent", procurement_node)
    graph.add_node("supplier_agent", supplier_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("notify_admin_oos", notify_admin_oos_node)
    graph.add_node("goods_received_confirmation", goods_received_confirmation_node)
    graph.add_node("inventory_update_agent", inventory_update_node)

    # 2. Add Fixed Sequential Edges
    graph.add_edge(START, "input_validation")
    graph.add_edge("input_validation", "supervisor_agent")
    graph.add_edge("supervisor_agent", "planner_agent")
    graph.add_edge("planner_agent", "inventory_monitoring_agent")

    # 3. Conditional Edge 1: Stock Check (Low Stock -> Alert Agent; Sufficient -> END)
    graph.add_conditional_edges(
        "inventory_monitoring_agent",
        route_after_inventory_check,
        {
            "alert_agent": "alert_agent",
            END: END,
        }
    )

    # 4. Alert -> Admin Approval
    graph.add_edge("alert_agent", "admin_approval")

    # 5. Conditional Edge 2: Admin Approval (Approved -> Procurement Agent; Rejected -> END)
    graph.add_conditional_edges(
        "admin_approval",
        route_after_admin_approval,
        {
            "procurement_agent": "procurement_agent",
            END: END,
        }
    )

    # 6. Procurement -> Supplier
    graph.add_edge("procurement_agent", "supplier_agent")

    # 7. Conditional Edge 3: Supplier Stock (Available -> Dispatch; OOS -> Notify Admin)
    graph.add_conditional_edges(
        "supplier_agent",
        route_after_supplier_check,
        {
            "dispatch": "dispatch",
            "notify_admin_oos": "notify_admin_oos",
        }
    )

    # 8. Out of Stock -> END
    graph.add_edge("notify_admin_oos", END)

    # 9. Dispatch -> Goods Received Confirmation -> Inventory Update -> END
    graph.add_edge("dispatch", "goods_received_confirmation")
    graph.add_edge("goods_received_confirmation", "inventory_update_agent")
    graph.add_edge("inventory_update_agent", END)

    # Compile with memory checkpointer
    chk = checkpointer if checkpointer is not None else get_checkpointer()
    compiled = graph.compile(
        checkpointer=chk,
        interrupt_before=interrupt_before
    )
    return compiled

# Pre-compiled default graph
grocery_graph = build_grocery_graph()

class WorkflowController:
    """
    High-level orchestration controller providing human-in-the-loop execution,
    checkpoint resumption, and presentation demo driving.
    """
    def __init__(self, graph=grocery_graph):
        self.graph = graph

    def run_check(self, product_name: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs the workflow up through inventory check or initial stage.
        """
        tid = thread_id or f"thread_{product_name.lower().replace(' ', '_')}"
        config = {"configurable": {"thread_id": tid}}
        initial_state: GroceryInventoryState = {
            "product_name": product_name,
            "messages": [],
            "audit_trail": []
        }
        res = self.graph.invoke(initial_state, config=config)
        return res

    def run_full_scenario(
        self,
        product_name: str,
        admin_approval: str = "APPROVED",
        supplier_available: bool = True,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end scenario with specified approval and supplier choices.
        """
        tid = thread_id or f"demo_{product_name.lower().replace(' ', '_')}"
        config = {"configurable": {"thread_id": tid}}

        state: GroceryInventoryState = {
            "product_name": product_name,
            "approval_status": admin_approval,
            "supplier_availability": "AVAILABLE" if supplier_available else "OUT_OF_STOCK",
            "messages": [],
            "audit_trail": []
        }
        result = self.graph.invoke(state, config=config)
        return result

workflow_controller = WorkflowController()
