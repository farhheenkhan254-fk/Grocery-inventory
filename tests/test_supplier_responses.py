import pytest
from database.connection import init_db, SessionLocal
from database.repository import repo
from database.models import PurchaseOrder, Approval, SupplierResponse, GoodsReceipt
from slack.interactive_buttons import interactive_handlers

@pytest.fixture(autouse=True)
def clean_orders():
    init_db()
    with SessionLocal() as s:
        s.query(GoodsReceipt).delete()
        s.query(SupplierResponse).delete()
        s.query(Approval).delete()
        s.query(PurchaseOrder).delete()
        s.commit()

def test_supplier_confirms_available():
    p = repo.get_product_by_name("Basmati Rice")
    po = repo.create_purchase_order(p["id"], p["supplier_id"], 50.0)
    repo.record_approval(po["id"], "U_ADMIN_01", "APPROVED")

    res = interactive_handlers.handle_supplier_response(po["id"], supplier_user_id="U_SUPPLIER_APEX", is_available=True)
    assert res["success"] is True
    assert res["status"] == "AVAILABLE"

    updated = repo.get_purchase_order(po["id"])
    assert updated["status"] == "CONFIRMED_AVAILABLE"
    assert updated["availability_status"] == "AVAILABLE"

def test_supplier_confirms_out_of_stock_and_recommends_alternatives():
    p = repo.get_product_by_name("Cooking Oil")
    po = repo.create_purchase_order(p["id"], p["supplier_id"], 25.0)
    repo.record_approval(po["id"], "U_ADMIN_01", "APPROVED")

    res = interactive_handlers.handle_supplier_response(po["id"], supplier_user_id="U_SUPPLIER_PUREOIL", is_available=False)
    assert res["success"] is True
    assert res["status"] == "OUT_OF_STOCK"

    # Business rule: Recommends alternative suppliers
    assert len(res["alternatives"]) > 0
    alt_ids = [a["id"] for a in res["alternatives"]]
    assert p["supplier_id"] not in alt_ids

    updated = repo.get_purchase_order(po["id"])
    assert updated["status"] == "OUT_OF_STOCK"
