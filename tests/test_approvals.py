import pytest
import uuid
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

def test_admin_approval_success():
    p = repo.get_product_by_name("Basmati Rice")
    po = repo.create_purchase_order(p["id"], p["supplier_id"], 50.0)
    assert po is not None
    assert po["status"] == "PENDING_APPROVAL"

    res = interactive_handlers.handle_admin_approval(po["id"], admin_user_id="U_ADMIN_01", action="approve")
    assert res["success"] is True
    assert res["status"] == "APPROVED"

    updated = repo.get_purchase_order(po["id"])
    assert updated["status"] in ["APPROVED", "SENT_TO_SUPPLIER"]
    assert updated["approval_status"] == "APPROVED"

def test_admin_rejection_success():
    p = repo.get_product_by_name("Wheat Flour")
    po = repo.create_purchase_order(p["id"], p["supplier_id"], 40.0)

    res = interactive_handlers.handle_admin_approval(po["id"], admin_user_id="U_ADMIN_01", action="reject")
    assert res["success"] is True
    assert res["status"] == "REJECTED"

    updated = repo.get_purchase_order(po["id"])
    assert updated["status"] == "REJECTED"

def test_prevent_duplicate_active_orders():
    p = repo.get_product_by_name("Sugar")
    po1 = repo.create_purchase_order(p["id"], p["supplier_id"], 30.0)
    assert po1 is not None

    # Attempt second PO for same product while first is active
    po2 = repo.create_purchase_order(p["id"], p["supplier_id"], 30.0)
    assert po2 is None
