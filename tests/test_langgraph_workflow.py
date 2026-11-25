import pytest
from database.connection import init_db, SessionLocal
from database.repository import repo
from database.models import PurchaseOrder, Approval, SupplierResponse, GoodsReceipt
from graph.builder import grocery_graph, workflow_controller
from graph.state import GroceryInventoryState

@pytest.fixture(autouse=True)
def clean_orders():
    init_db()
    with SessionLocal() as s:
        s.query(GoodsReceipt).delete()
        s.query(SupplierResponse).delete()
        s.query(Approval).delete()
        s.query(PurchaseOrder).delete()
        s.commit()

def test_langgraph_sufficient_stock_routes_to_end():
    # Set high stock (30 kg > 10 kg min)
    repo.set_stock("Basmati Rice", 30.0)

    config = {"configurable": {"thread_id": "test_sufficient"}}
    state: GroceryInventoryState = {"product_name": "Basmati Rice"}
    res = grocery_graph.invoke(state, config=config)

    assert res["stock_status"] == "SUFFICIENT"
    # Alert agent should NOT have run
    assert res.get("alert_sent") is not True

def test_langgraph_low_stock_triggers_alert_and_approval():
    repo.set_stock("Basmati Rice", 5.0)

    config = {"configurable": {"thread_id": "test_low_stock"}}
    state: GroceryInventoryState = {"product_name": "Basmati Rice"}
    res = grocery_graph.invoke(state, config=config)

    assert res["stock_status"] == "LOW_STOCK"
    assert res["alert_sent"] is True
    assert res["po_id"] is not None
    assert res["order_quantity"] == 50.0

def test_langgraph_full_scenario_1_approval_and_receipt():
    repo.set_stock("Basmati Rice", 5.0)

    res = workflow_controller.run_full_scenario(
        "Basmati Rice",
        admin_approval="APPROVED",
        supplier_available=True,
        thread_id="test_scenario_1"
    )

    assert res["stock_status"] == "LOW_STOCK"
    assert res["approval_status"] == "APPROVED"
    assert res["supplier_availability"] == "AVAILABLE"
    assert res["dispatch_status"] == "DISPATCHED"
    assert res["goods_received"] is True
    assert res["inventory_updated"] is True
    assert res["updated_stock"] == 55.0

def test_langgraph_scenario_2_supplier_out_of_stock():
    repo.set_stock("Sugar", 4.0)

    res = workflow_controller.run_full_scenario(
        "Sugar",
        admin_approval="APPROVED",
        supplier_available=False,
        thread_id="test_scenario_2"
    )

    assert res["stock_status"] == "LOW_STOCK"
    assert res["approval_status"] == "APPROVED"
    assert res["supplier_availability"] == "OUT_OF_STOCK"
    assert len(res.get("alternative_suppliers", [])) > 0
    assert res["workflow_complete"] is True
