from typing import TypedDict, Optional, List, Dict, Any

class GroceryInventoryState(TypedDict, total=False):
    # Product Information
    product_name: str
    product_id: Optional[int]
    category: Optional[str]
    current_stock: Optional[float]
    minimum_stock: Optional[float]
    unit: Optional[str]

    # Inventory Analysis
    stock_status: Optional[str]  # "SUFFICIENT", "LOW_STOCK", "OUT_OF_STOCK", "NOT_FOUND"
    reorder_plan: Optional[Dict[str, Any]]
    alert_sent: bool

    # Procurement & Purchase Order
    po_id: Optional[str]
    supplier_id: Optional[int]
    supplier_name: Optional[str]
    order_quantity: Optional[float]

    # Human-in-the-loop: Admin Approval
    approval_status: Optional[str]  # "APPROVED", "REJECTED", "PENDING"
    admin_id: Optional[str]
    approval_timestamp: Optional[str]

    # Supplier Interaction
    supplier_availability: Optional[str]  # "AVAILABLE", "OUT_OF_STOCK"
    dispatch_status: Optional[str]  # "PENDING", "DISPATCHED"
    alternative_suppliers: Optional[List[Dict[str, Any]]]

    # Receiving & Restocking
    goods_received: bool
    received_quantity: Optional[float]
    received_by: Optional[str]
    inventory_updated: bool
    updated_stock: Optional[float]

    # Orchestration & Audit
    current_step: str
    workflow_complete: bool
    messages: List[str]
    audit_trail: List[Dict[str, Any]]
    error: Optional[str]
