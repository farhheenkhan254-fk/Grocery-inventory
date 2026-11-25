from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime, Text, Enum
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    slack_user_id = Column(String(50), nullable=False)
    slack_channel_id = Column(String(50), nullable=True)
    contact_email = Column(String(100), nullable=True)

    products = relationship("Product", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slack_user_id": self.slack_user_id,
            "slack_channel_id": self.slack_channel_id,
            "contact_email": self.contact_email,
        }


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50), nullable=False, default="General")
    current_stock = Column(Float, nullable=False, default=0.0)
    minimum_stock = Column(Float, nullable=False, default=10.0)
    reorder_quantity = Column(Float, nullable=False, default=50.0)
    unit = Column(String(20), nullable=False, default="kg")
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)

    supplier = relationship("Supplier", back_populates="products", lazy="joined")
    purchase_orders = relationship("PurchaseOrder", back_populates="product")

    def to_dict(self):
        supp_name = None
        try:
            supp_name = self.supplier.name if self.supplier else None
        except Exception:
            supp_name = None
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "current_stock": self.current_stock,
            "minimum_stock": self.minimum_stock,
            "reorder_quantity": self.reorder_quantity,
            "unit": self.unit,
            "supplier_id": self.supplier_id,
            "supplier_name": supp_name,
            "is_low_stock": self.current_stock <= self.minimum_stock,
        }


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(String(50), primary_key=True)  # PO-XXXXXX format
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    status = Column(String(40), nullable=False, default="PENDING_APPROVAL")
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="purchase_orders", lazy="joined")
    supplier = relationship("Supplier", back_populates="purchase_orders", lazy="joined")
    approval = relationship("Approval", uselist=False, back_populates="purchase_order", lazy="joined")
    supplier_response = relationship("SupplierResponse", uselist=False, back_populates="purchase_order", lazy="joined")
    goods_receipt = relationship("GoodsReceipt", uselist=False, back_populates="purchase_order", lazy="joined")

    def to_dict(self):
        prod_name = None
        unit = "units"
        supp_name = None
        appr_status = None
        avail_status = None
        disp_status = None
        rec_qty = None

        try:
            prod_name = self.product.name if self.product else None
            unit = self.product.unit if self.product else "units"
        except Exception:
            pass

        try:
            supp_name = self.supplier.name if self.supplier else None
        except Exception:
            pass

        try:
            appr_status = self.approval.approval_status if self.approval else None
        except Exception:
            pass

        try:
            avail_status = self.supplier_response.availability_status if self.supplier_response else None
            disp_status = self.supplier_response.dispatch_status if self.supplier_response else None
        except Exception:
            pass

        try:
            rec_qty = self.goods_receipt.received_quantity if self.goods_receipt else None
        except Exception:
            pass

        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": prod_name,
            "supplier_id": self.supplier_id,
            "supplier_name": supp_name,
            "quantity": self.quantity,
            "unit": unit,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "approval_status": appr_status,
            "availability_status": avail_status,
            "dispatch_status": disp_status,
            "received_quantity": rec_qty,
        }


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id = Column(String(50), ForeignKey("purchase_orders.id"), nullable=False, unique=True)
    admin_id = Column(String(50), nullable=False)
    approval_status = Column(String(20), nullable=False)  # APPROVED or REJECTED
    approved_at = Column(DateTime, default=datetime.utcnow)

    purchase_order = relationship("PurchaseOrder", back_populates="approval")

    def to_dict(self):
        return {
            "id": self.id,
            "purchase_order_id": self.purchase_order_id,
            "admin_id": self.admin_id,
            "approval_status": self.approval_status,
            "approved_at": self.approved_at.strftime("%Y-%m-%d %H:%M:%S") if self.approved_at else None,
        }


class SupplierResponse(Base):
    __tablename__ = "supplier_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id = Column(String(50), ForeignKey("purchase_orders.id"), nullable=False, unique=True)
    availability_status = Column(String(20), nullable=False)  # AVAILABLE or OUT_OF_STOCK
    dispatch_status = Column(String(20), nullable=False, default="PENDING")  # PENDING or DISPATCHED
    response_at = Column(DateTime, default=datetime.utcnow)

    purchase_order = relationship("PurchaseOrder", back_populates="supplier_response")

    def to_dict(self):
        return {
            "id": self.id,
            "purchase_order_id": self.purchase_order_id,
            "availability_status": self.availability_status,
            "dispatch_status": self.dispatch_status,
            "response_at": self.response_at.strftime("%Y-%m-%d %H:%M:%S") if self.response_at else None,
        }


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id = Column(String(50), ForeignKey("purchase_orders.id"), nullable=False, unique=True)
    received_quantity = Column(Float, nullable=False)
    received_by = Column(String(50), nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)

    purchase_order = relationship("PurchaseOrder", back_populates="goods_receipt")

    def to_dict(self):
        return {
            "id": self.id,
            "purchase_order_id": self.purchase_order_id,
            "received_quantity": self.received_quantity,
            "received_by": self.received_by,
            "received_at": self.received_at.strftime("%Y-%m-%d %H:%M:%S") if self.received_at else None,
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=False)
    actor = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "actor": self.actor,
            "details": self.details,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
