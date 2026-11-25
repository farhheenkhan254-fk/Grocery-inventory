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

def test_stock_does_not_increase_at_dispatch():
    """Business rule: Stock must not increase at dispatch time."""
    repo.set_stock("Basmati Rice", 5.0)
    p = repo.get_product_by_name("Basmati Rice")
    po = repo.create_purchase_order(p["id"], p["supplier_id"], 50.0)
    repo.record_approval(po["id"], "U_ADMIN_01", "APPROVED")

    # Supplier dispatches
    disp_res = interactive_handlers.handle_supplier_dispatch(po["id"], "U_SUPPLIER_APEX")
    assert disp_res["success"] is True

    # Check stock remains exactly 5.0 kg
    p_after_dispatch = repo.get_product_by_name("Basmati Rice")
    assert p_after_dispatch["current_stock"] == 5.0

    po_after = repo.get_purchase_order(po["id"])
    assert po_after["status"] == "DISPATCHED"

def test_stock_increases_only_after_goods_receipt():
    """Business rule: Stock increases only after goods receipt confirmation."""
    repo.set_stock("Basmati Rice", 5.0)
    p = repo.get_product_by_name("Basmati Rice")
    po = repo.create_purchase_order(p["id"], p["supplier_id"], 50.0)
    repo.record_approval(po["id"], "U_ADMIN_01", "APPROVED")
    interactive_handlers.handle_supplier_dispatch(po["id"], "U_SUPPLIER_APEX")

    # Before receipt
    assert repo.get_product_by_name("Basmati Rice")["current_stock"] == 5.0

    # Goods receipt confirmed by Admin
    recv_res = interactive_handlers.handle_goods_receipt(po["id"], "U_ADMIN_01")
    assert recv_res["success"] is True

    # After receipt: 5.0 + 50.0 = 55.0 kg
    p_final = repo.get_product_by_name("Basmati Rice")
    assert p_final["current_stock"] == 55.0

    po_final = repo.get_purchase_order(po["id"])
    assert po_final["status"] == "RECEIVED"

def test_cannot_dispatch_unapproved_order():
    """Business rule: Supplier cannot dispatch an unapproved order."""
    p = repo.get_product_by_name("Tea Leaves")
    po = repo.create_purchase_order(p["id"], p["supplier_id"], 20.0)
    # Status is PENDING_APPROVAL; not approved

    disp_res = interactive_handlers.handle_supplier_dispatch(po["id"], "U_SUPPLIER_GOLDEN")
    assert disp_res["success"] is False
    assert "Cannot dispatch" in disp_res["message"]
