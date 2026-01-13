"""
Order Database Model
====================
SQLAlchemy ORM model for the 'orders' table.

PURPOSE:
Represents an order placed by an Order Booker for a shop during a visit.
Orders contain order items and are assigned to Delivery Men for delivery.

WORKFLOW:
1. Order Booker visits shop and places order
2. Order is created with status="pending" or "confirmed"
3. Distributor assigns order to Delivery Man
4. Delivery Man delivers order (status="delivered") or marks as failed
5. Payment is collected (linked via payments table)

RELATIONSHIPS:
- Belongs to a Shop (via shop_id foreign key)
- Created by an Order Booker (via order_booker_id foreign key)
- Assigned to a Distributor (via distributor_id foreign key)
- Assigned to a Delivery Man (via delivery_man_id foreign key) - Optional
- Linked to a Visit (via visit_id foreign key) - Optional
- Has Order Items (via order_items.order_id)
- Has Payments (via payments.order_id)

DATABASE TABLE: orders
"""
from sqlalchemy import Column, BigInteger, Numeric, DateTime, ForeignKey, String, Date, Text
from sqlalchemy.sql import func
from config.database import Base


class Order(Base):
    """
    Order table model.
    
    Maps to the 'orders' table in PostgreSQL.
    Each record represents an order placed for a shop.
    """
    __tablename__ = "orders"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the order.
    Auto-incremented by database.
    """

    # Foreign Keys
    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=True)
    """
    Foreign key to shops table.
    - Links order to the shop where order was placed
    - Nullable: For flexibility (though typically required)
    - Example: Shop ID 1 = "Ali General Store"
    """

    order_booker_id = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=True)
    """
    Foreign key to order_bookers table.
    - Links order to the order booker who placed it
    - Nullable: For flexibility (though typically required)
    - Example: Order Booker ID 1 = "Ahmed Khan"
    """

    distributor_id = Column(BigInteger, ForeignKey("distributors.id"), nullable=True)
    """
    Foreign key to distributors table.
    - Links order to the distributor (for assignment/approval)
    - Nullable: May be set later during assignment
    - Example: Distributor ID 1 = "Regional Manager"
    """

    delivery_man_id = Column(BigInteger, ForeignKey("delivery_men.id"), nullable=True)
    """
    Foreign key to delivery_men table.
    - Links order to the delivery man assigned to deliver it
    - Nullable: Initially NULL, set when distributor assigns
    - Example: Delivery Man ID 1 = "Hassan Ali"
    """

    visit_id = Column(BigInteger, ForeignKey("shop_visits.id"), nullable=True)
    """
    Foreign key to shop_visits table.
    - Links order to the visit where it was placed
    - Nullable: For orders created outside of visits (rare)
    - Example: Visit ID 1 = "Visit to Ali General Store on 2026-01-07"
    """

    # Financial Information
    total_amount = Column(Numeric(10, 2), nullable=True)
    """
    Total order amount.
    - Calculated from sum of order_items.total_price
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 5000.00 (Rs. 5,000)
    - Used for credit limit validation
    """

    # Status and Scheduling
    status = Column(String, nullable=True)
    """
    Order status.
    - Values: "pending", "confirmed", "delivered", "cancelled", "paid"
    - Default: "pending" when first created
    - "pending": Order placed, awaiting confirmation
    - "confirmed": Order confirmed, ready for delivery
    - "delivered": Order delivered to shop
    - "cancelled": Order cancelled
    - "paid": Order paid (outstanding balance cleared)
    """

    scheduled_date = Column(Date, nullable=True)
    """
    Scheduled delivery date.
    - Date when order should be delivered
    - Format: DATE (YYYY-MM-DD)
    - Example: 2026-01-10
    - Used for delivery planning
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when order was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and sorting
    """

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """
    Timestamp when order was last updated.
    - Automatically updated by database on UPDATE
    - Timezone-aware (stores UTC)
    - Used for tracking modifications
    - Null on initial creation
    """














