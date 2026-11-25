import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import (
    Product, Supplier, PurchaseOrder, Approval, SupplierResponse, GoodsReceipt, AuditLog
)

class GroceryRepository:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def get_session(self) -> Session:
        return self.session_factory()

    # ---------------- Products ---------------- #
    def get_all_products(self) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            products = session.query(Product).order_by(Product.name).all()
            return [p.to_dict() for p in products]

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            return product.to_dict() if product else None

    def get_product_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            product = session.query(Product).filter(Product.name.ilike(name.strip())).first()
            return product.to_dict() if product else None

    def get_low_stock_products(self) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            products = session.query(Product).filter(Product.current_stock <= Product.minimum_stock).all()
            return [p.to_dict() for p in products]

    def set_stock(self, product_name: str, new_stock: float) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            product = session.query(Product).filter(Product.name.ilike(product_name.strip())).first()
            if not product:
                return None
            old_stock = product.current_stock
            product.current_stock = float(new_stock)
            session.commit()
            res = product.to_dict()

        self.log_audit(
            event_type="STOCK_ADJUSTMENT",
            entity_type="PRODUCT",
            entity_id=str(res["id"]),
            actor="System/Admin",
            details={"product": res["name"], "old_stock": old_stock, "new_stock": res["current_stock"]}
        )
        return res

    def add_stock(self, product_id: int, quantity_to_add: float) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
            old_stock = product.current_stock
            product.current_stock = old_stock + float(quantity_to_add)
            session.commit()
            res = product.to_dict()

        self.log_audit(
            event_type="STOCK_INCREASE",
            entity_type="PRODUCT",
            entity_id=str(res["id"]),
            actor="Inventory Update Agent",
            details={
                "product": res["name"],
                "previous_stock": old_stock,
                "added": quantity_to_add,
                "new_stock": res["current_stock"]
            }
        )
        return res

    # ---------------- Suppliers ---------------- #
    def get_all_suppliers(self) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            suppliers = session.query(Supplier).all()
            return [s.to_dict() for s in suppliers]

    def get_supplier_by_id(self, supplier_id: int) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
            return supplier.to_dict() if supplier else None

    def get_alternative_suppliers(self, current_supplier_id: int) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            suppliers = session.query(Supplier).filter(Supplier.id != current_supplier_id).all()
            return [s.to_dict() for s in suppliers]

    # ---------------- Purchase Orders & Business Rules ---------------- #
    def has_active_order_for_product(self, product_id: int) -> bool:
        """Business rule: Prevent duplicate active purchase orders for the same product."""
        with self.get_session() as session:
            active_statuses = ["PENDING_APPROVAL", "APPROVED", "SENT_TO_SUPPLIER", "CONFIRMED_AVAILABLE", "DISPATCHED"]
            existing = session.query(PurchaseOrder).filter(
                PurchaseOrder.product_id == product_id,
                PurchaseOrder.status.in_(active_statuses)
            ).first()
            return existing is not None

    def create_purchase_order(self, product_id: int, supplier_id: int, quantity: float, po_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if self.has_active_order_for_product(product_id):
            return None  # Prevent duplicate active order

        po_id = po_id or f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        with self.get_session() as session:
            po = PurchaseOrder(
                id=po_id,
                product_id=product_id,
                supplier_id=supplier_id,
                quantity=float(quantity),
                status="PENDING_APPROVAL",
                created_at=datetime.utcnow()
            )
            session.add(po)
            session.commit()
            res = po.to_dict()

        self.log_audit(
            event_type="PO_CREATED",
            entity_type="PURCHASE_ORDER",
            entity_id=po_id,
            actor="Procurement Agent / Planner",
            details={"product_id": product_id, "supplier_id": supplier_id, "quantity": quantity}
        )
        return res

    def get_purchase_order(self, po_id: str) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
            return po.to_dict() if po else None

    def get_all_purchase_orders(self) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            orders = session.query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).all()
            return [po.to_dict() for po in orders]

    def update_purchase_order_status(self, po_id: str, new_status: str) -> bool:
        with self.get_session() as session:
            po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
            if not po:
                return False
            po.status = new_status
            session.commit()
            return True

    def assign_new_supplier_to_order(self, po_id: str, new_supplier_id: int) -> bool:
        """Allows reassignment when supplier reports out of stock."""
        with self.get_session() as session:
            po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
            if not po:
                return False
            po.supplier_id = new_supplier_id
            po.status = "SENT_TO_SUPPLIER"
            session.commit()
            self.log_audit(
                event_type="SUPPLIER_REASSIGNED",
                entity_type="PURCHASE_ORDER",
                entity_id=po_id,
                actor="Admin / Supervisor",
                details={"new_supplier_id": new_supplier_id}
            )
            return True

    # ---------------- Approvals ---------------- #
    def record_approval(self, po_id: str, admin_id: str, status: str) -> Optional[Dict[str, Any]]:
        """Admin approves or rejects PO. Changes status to APPROVED or REJECTED."""
        status = status.upper()
        if status not in ["APPROVED", "REJECTED"]:
            raise ValueError("Approval status must be APPROVED or REJECTED")

        with self.get_session() as session:
            po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
            if not po:
                return None
            if po.status != "PENDING_APPROVAL":
                return None  # Cannot approve already processed order

            # Record approval
            existing_approval = session.query(Approval).filter(Approval.purchase_order_id == po_id).first()
            if existing_approval:
                existing_approval.approval_status = status
                existing_approval.admin_id = admin_id
                existing_approval.approved_at = datetime.utcnow()
            else:
                appr = Approval(
                    purchase_order_id=po_id,
                    admin_id=admin_id,
                    approval_status=status,
                    approved_at=datetime.utcnow()
                )
                session.add(appr)

            po.status = status if status == "REJECTED" else "APPROVED"
            session.commit()

        self.log_audit(
            event_type=f"PO_{status}",
            entity_type="PURCHASE_ORDER",
            entity_id=po_id,
            actor=f"Admin ({admin_id})",
            details={"status": status}
        )
        return self.get_purchase_order(po_id)

    # ---------------- Supplier Responses & Dispatch ---------------- #
    def record_supplier_response(self, po_id: str, availability_status: str, dispatch_status: str = "PENDING") -> Optional[Dict[str, Any]]:
        """Business rule: Supplier cannot dispatch an unapproved order."""
        availability_status = availability_status.upper()
        dispatch_status = dispatch_status.upper()

        with self.get_session() as session:
            po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
            if not po:
                return None
            if po.status not in ["APPROVED", "SENT_TO_SUPPLIER", "CONFIRMED_AVAILABLE"]:
                return None

            resp = session.query(SupplierResponse).filter(SupplierResponse.purchase_order_id == po_id).first()
            if not resp:
                resp = SupplierResponse(
                    purchase_order_id=po_id,
                    availability_status=availability_status,
                    dispatch_status=dispatch_status,
                    response_at=datetime.utcnow()
                )
                session.add(resp)
            else:
                resp.availability_status = availability_status
                resp.dispatch_status = dispatch_status
                resp.response_at = datetime.utcnow()

            if availability_status == "OUT_OF_STOCK":
                po.status = "OUT_OF_STOCK"
            elif dispatch_status == "DISPATCHED":
                # Stock must NOT increase at dispatch time!
                po.status = "DISPATCHED"
            elif availability_status == "AVAILABLE":
                po.status = "CONFIRMED_AVAILABLE"

            session.commit()

        self.log_audit(
            event_type=f"SUPPLIER_{availability_status}_{dispatch_status}",
            entity_type="PURCHASE_ORDER",
            entity_id=po_id,
            actor="Wholesaler / Supplier Agent",
            details={"availability": availability_status, "dispatch": dispatch_status}
        )
        return self.get_purchase_order(po_id)

    # ---------------- Goods Receipt ---------------- #
    def record_goods_receipt(self, po_id: str, received_quantity: float, received_by: str) -> Optional[Dict[str, Any]]:
        """
        Business rule: Stock increases only after goods receipt confirmation!
        """
        with self.get_session() as session:
            po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
            if not po:
                return None
            if po.status != "DISPATCHED":
                return None  # Can only receive dispatched orders

            receipt = GoodsReceipt(
                purchase_order_id=po_id,
                received_quantity=float(received_quantity),
                received_by=received_by,
                received_at=datetime.utcnow()
            )
            session.add(receipt)
            po.status = "RECEIVED"

            # Atomically increase product stock
            product = session.query(Product).filter(Product.id == po.product_id).first()
            if product:
                product.current_stock += float(received_quantity)

            session.commit()

        self.log_audit(
            event_type="GOODS_RECEIVED",
            entity_type="PURCHASE_ORDER",
            entity_id=po_id,
            actor=f"Admin ({received_by})",
            details={"received_quantity": received_quantity}
        )
        return self.get_purchase_order(po_id)

    # ---------------- Audit Logs ---------------- #
    def log_audit(self, event_type: str, entity_type: str, entity_id: str, actor: str, details: Optional[Dict[str, Any]] = None):
        try:
            with self.get_session() as session:
                log = AuditLog(
                    event_type=event_type,
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                    actor=actor,
                    details=json.dumps(details or {}),
                    created_at=datetime.utcnow()
                )
                session.add(log)
                session.commit()
        except Exception:
            pass

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            logs = session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
            return [l.to_dict() for l in logs]

repo = GroceryRepository()
