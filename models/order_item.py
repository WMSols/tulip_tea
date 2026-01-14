"""
Order Item Database Model
=========================
SQLAlchemy ORM model for the 'order_items' table.

PURPOSE:
Represents individual items/products in an order. Each order can have multiple items.

RELATIONSHIP:
Orders ←→ Order Items (One-to-Many)
- One order can have many items
- Each item belongs to one order

DATABASE TABLE: order_items
"""
from sqlalchemy import Column, BigInteger, Integer, Numeric, ForeignKey, String, Text, DateTime
from config.database import Base


class OrderItem(Base):
    """
    Order Item table model.
    
    Maps to the 'order_items' table in PostgreSQL.
    Each record represents one product/item in an order.
    """
    __tablename__ = "order_items"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the order item.
    Auto-incremented by database.
    """

    # Foreign Keys
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=True)
    """
    Foreign key to orders table.
    - Links item to the order it belongs to
    - CASCADE delete: If order is deleted, all its items are deleted
    - Example: Order ID 1 = "Order #12345"
    """

    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    """
    Foreign key to products table.
    - Links item to the product (if product exists in products table)
    - SET NULL on delete: If product is deleted, product_id is set to NULL but order_item remains
    - Nullable: For backward compatibility with existing data
    - Example: Product ID 1 = "Tulip Tea Premium 500g"
    """

    # Product Information
    product_name = Column(Text, nullable=True)
    """
    Product name.
    - Name of the product/item
    - Example: "Tulip Tea Premium 500g"
    - Used for order details and delivery verification
    """

    quantity = Column(Integer, nullable=True)
    """
    Quantity ordered.
    - Number of units of this product
    - Example: 10 (10 boxes)
    - Used for calculating total price
    """

    unit_price = Column(Numeric(10, 2), nullable=True)
    """
    Unit price of the product.
    - Price per unit
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 500.00 (Rs. 500 per unit)
    - Used for calculating total price
    """

    total_price = Column(Numeric(10, 2), nullable=True)
    """
    Total price for this item (quantity × unit_price).
    - Calculated: quantity × unit_price
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 5000.00 (10 × 500.00 = Rs. 5,000)
    - Used for order total calculation
    """

    # Soft Delete
    # NOTE: Temporarily commented out until database column is added
    # Run sql/add_deleted_at_to_order_items.sql to add the column, then uncomment this
    # deleted_at = Column(DateTime(timezone=False), nullable=True)
    # """
    # Soft delete timestamp.
    # - When set, order item is considered deleted but data is preserved
    # - NULL = active record
    # - Used for soft delete functionality
    # """






