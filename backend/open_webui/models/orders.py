import json
import time
import uuid
from typing import Optional
from enum import Enum

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, get_db, get_db_context
from open_webui.models.users import User, UserModel, Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON, Float, ForeignKey

####################
# Order DB Schema
####################


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "order"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text, nullable=True)  # Nullable for guest orders
    shop_id = Column(Text, nullable=False)

    # Customer information
    customer_name = Column(Text, nullable=False)
    customer_email = Column(Text, nullable=False)
    customer_phone = Column(Text, nullable=True)
    
    # Shipping address
    shipping_address = Column(JSON, nullable=False)
    
    # Order items
    items = Column(JSON, nullable=False)  # List of {product_id, name, price, quantity, currency}
    
    # Order totals
    subtotal = Column(Float, nullable=False)
    shipping_cost = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    currency = Column(Text, nullable=False)
    
    # Order status
    status = Column(Text, default=OrderStatus.PENDING.value)
    
    # Delivery tracking information
    tracking_number = Column(Text, nullable=True)
    carrier = Column(Text, nullable=True)  # e.g., "Colissimo", "Chronopost", "DHL", etc.
    tracking_url = Column(Text, nullable=True)
    shipped_at = Column(BigInteger, nullable=True)
    estimated_delivery_date = Column(BigInteger, nullable=True)
    delivered_at = Column(BigInteger, nullable=True)
    
    # Delivery assignment
    assigned_user_id = Column(Text, nullable=True)  # User assigned to manage this delivery
    assigned_delivery_person_id = Column(Text, nullable=True)  # Delivery person assigned to deliver
    
    # Additional information
    notes = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class OrderModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    shop_id: str

    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    
    shipping_address: dict
    items: list[dict]
    
    subtotal: float
    shipping_cost: float = 0.0
    total: float
    currency: str
    
    status: str = OrderStatus.PENDING.value
    
    # Delivery tracking information
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    tracking_url: Optional[str] = None
    shipped_at: Optional[int] = None
    estimated_delivery_date: Optional[int] = None
    delivered_at: Optional[int] = None
    
    # Delivery assignment
    assigned_user_id: Optional[str] = None
    assigned_delivery_person_id: Optional[str] = None
    
    notes: Optional[str] = None
    meta: Optional[dict] = None

    created_at: int
    updated_at: int


####################
# Forms
####################


class OrderItemForm(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int
    currency: str


class ShippingAddressForm(BaseModel):
    street: str
    city: str
    postal_code: str
    country: str
    state: Optional[str] = None


class OrderForm(BaseModel):
    shop_id: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    shipping_address: ShippingAddressForm
    items: list[OrderItemForm]
    shipping_cost: float = 0.0
    notes: Optional[str] = None
    meta: Optional[dict] = None


class OrderUpdateForm(BaseModel):
    status: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    tracking_url: Optional[str] = None
    estimated_delivery_date: Optional[int] = None
    assigned_user_id: Optional[str] = None
    assigned_delivery_person_id: Optional[str] = None
    notes: Optional[str] = None
    meta: Optional[dict] = None


class OrderUserResponse(OrderModel):
    user: Optional[UserResponse] = None


class OrderListResponse(BaseModel):
    items: list[OrderUserResponse]
    total: int


class OrderTable:
    def insert_new_order(
        self, user_id: Optional[str], form_data: OrderForm, db: Optional[Session] = None
    ) -> Optional[OrderModel]:
        with get_db_context(db) as db:
            # Calculate totals
            subtotal = sum(item.price * item.quantity for item in form_data.items)
            total = subtotal + form_data.shipping_cost
            
            # Get currency from first item (assuming all items have same currency)
            currency = form_data.items[0].currency if form_data.items else "EUR"
            
            order = OrderModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "shop_id": form_data.shop_id,
                    "customer_name": form_data.customer_name,
                    "customer_email": form_data.customer_email,
                    "customer_phone": form_data.customer_phone,
                    "shipping_address": form_data.shipping_address.model_dump(),
                    "items": [item.model_dump() for item in form_data.items],
                    "subtotal": subtotal,
                    "shipping_cost": form_data.shipping_cost,
                    "total": total,
                    "currency": currency,
                    "status": OrderStatus.PENDING.value,
                    "notes": form_data.notes,
                    "meta": form_data.meta,
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )

            new_order = Order(**order.model_dump())
            db.add(new_order)
            db.commit()
            return order

    def get_orders_by_user_id(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[OrderModel]:
        with get_db_context(db) as db:
            query = db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc())
            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)
            orders = query.all()
            return [OrderModel.model_validate(order) for order in orders]

    def get_orders_by_shop_id(
        self,
        shop_id: str,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[OrderModel]:
        with get_db_context(db) as db:
            query = db.query(Order).filter(Order.shop_id == shop_id).order_by(Order.created_at.desc())
            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)
            orders = query.all()
            return [OrderModel.model_validate(order) for order in orders]

    def get_order_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[OrderModel]:
        with get_db_context(db) as db:
            order = db.query(Order).filter(Order.id == id).first()
            return OrderModel.model_validate(order) if order else None

    def update_order_by_id(
        self, id: str, form_data: OrderUpdateForm, db: Optional[Session] = None
    ) -> Optional[OrderModel]:
        with get_db_context(db) as db:
            order = db.query(Order).filter(Order.id == id).first()
            if not order:
                return None

            form_data = form_data.model_dump(exclude_unset=True)

            if "status" in form_data:
                old_status = order.status
                new_status = form_data["status"]
                
                # Only update if status changed
                if old_status != new_status:
                    order.status = new_status
                    
                    # Create status history entry (will be created after OrderStatusHistories is defined)
                    # We'll handle this in the router to avoid circular import
                    
                    # Auto-set shipped_at when status changes to "shipped"
                    if new_status == OrderStatus.SHIPPED.value and not order.shipped_at:
                        order.shipped_at = int(time.time_ns())
                    
                    # Auto-set delivered_at when status changes to "delivered"
                    if new_status == OrderStatus.DELIVERED.value and not order.delivered_at:
                        order.delivered_at = int(time.time_ns())
            
            if "tracking_number" in form_data:
                order.tracking_number = form_data["tracking_number"]
            if "carrier" in form_data:
                order.carrier = form_data["carrier"]
            if "tracking_url" in form_data:
                order.tracking_url = form_data["tracking_url"]
            if "estimated_delivery_date" in form_data:
                order.estimated_delivery_date = form_data["estimated_delivery_date"]
            if "assigned_user_id" in form_data:
                order.assigned_user_id = form_data["assigned_user_id"]
            if "assigned_delivery_person_id" in form_data:
                order.assigned_delivery_person_id = form_data["assigned_delivery_person_id"]
            if "notes" in form_data:
                order.notes = form_data["notes"]
            if "meta" in form_data:
                order.meta = {**order.meta, **form_data["meta"]} if order.meta else form_data["meta"]

            order.updated_at = int(time.time_ns())

            db.commit()
            return OrderModel.model_validate(order) if order else None

    def delete_order_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Order).filter(Order.id == id).delete()
                db.commit()
                return True
        except Exception:
            return False


Orders = OrderTable()


####################
# Order Status History
####################


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(Text, primary_key=True, unique=True)
    order_id = Column(Text, ForeignKey("order.id"), nullable=False)
    status = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class OrderStatusHistoryModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    status: str
    notes: Optional[str] = None
    created_at: int


class OrderStatusHistoryForm(BaseModel):
    status: str
    notes: Optional[str] = None


class OrderStatusHistoryTable:
    def insert_status_history(
        self,
        order_id: str,
        status: str,
        notes: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[OrderStatusHistoryModel]:
        with get_db_context(db) as db:
            history = OrderStatusHistory(
                id=str(uuid.uuid4()),
                order_id=order_id,
                status=status,
                notes=notes,
                created_at=int(time.time_ns()),
            )
            db.add(history)
            db.commit()
            return OrderStatusHistoryModel.model_validate(history)

    def get_status_history_by_order_id(
        self, order_id: str, db: Optional[Session] = None
    ) -> list[OrderStatusHistoryModel]:
        with get_db_context(db) as db:
            history = (
                db.query(OrderStatusHistory)
                .filter(OrderStatusHistory.order_id == order_id)
                .order_by(OrderStatusHistory.created_at.asc())
                .all()
            )
            return [OrderStatusHistoryModel.model_validate(h) for h in history]


OrderStatusHistories = OrderStatusHistoryTable()
