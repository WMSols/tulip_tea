"""
Delivery Item Database Model
============================
SQLAlchemy ORM model for the 'delivery_items' table.

PURPOSE:
Tracks quantities for each product/item in a delivery. Links deliveries to order_items
and tracks how much was picked up, delivered, and returned for inventory management.

RELATIONSHIPS:
- Belongs to a Delivery (via delivery_id foreign key)
- Belongs to an Order Item (via order_item_id foreign key)
- Links to a Product (via product_id foreign key)
- Links to Inventory (via inventory_item_id foreign key) for automatic deduction

DATABASE TABLE: delivery_items
"""
from sqlalchemy import Column, BigInteger, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from config.database import Base


class DeliveryItem(Base):
    """
    Delivery Item table model.
    
    Maps to the 'delivery_items' table in PostgreSQL.
    Each record tracks quantities for one product in a delivery.
    """
    __tablename__ = "delivery_items"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """Primary key: Unique identifier for the delivery item."""

    # Foreign Keys
    delivery_id = Column(BigInteger, ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False)
    """Foreign key to deliveries table. Links to the delivery."""

    order_item_id = Column(BigInteger, ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False)
    """Foreign key to order_items table. Links to the order item being delivered."""

    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    """Foreign key to products table. Product being delivered."""

    inventory_item_id = Column(BigInteger, ForeignKey("inventory.id", ondelete="SET NULL"), nullable=True)
    """
    Foreign key to inventory table.
    Links to the specific inventory item used for this delivery.
    Used for automatic inventory deduction/addition.
    """

    # Quantity Tracking
    quantity_picked_up = Column(Integer, nullable=False, default=0)
    """
    Quantity picked up from warehouse.
    - Set when delivery status changes to 'picked_up'
    - Inventory is deducted by this amount
    - Must be >= quantity_delivered + quantity_returned
    """

    quantity_delivered = Column(Integer, nullable=False, default=0)
    """
    Quantity delivered to shop.
    - Set when delivery man confirms delivery at shop
    - Can be less than quantity_picked_up if some items are returned
    """

    quantity_returned = Column(Integer, nullable=False, default=0)
    """
    Quantity returned to warehouse.
    - Set when delivery man returns unsold stock
    - Inventory is added back by this amount
    - quantity_picked_up = quantity_delivered + quantity_returned
    """

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    """Timestamp when delivery item was created."""
    
    updated_at = Column(DateTime(timezone=False), onupdate=func.now())
    """Timestamp when delivery item was last updated."""
    
    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """Soft delete timestamp. NULL = active delivery item."""

