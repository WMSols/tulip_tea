"""
Product Database Model
=====================
SQLAlchemy ORM model for the 'products' table.

PURPOSE:
Represents products that can be ordered. Products have a code, name, and unit.
This standardizes product information across the system.

RELATIONSHIPS:
- Has Order Items (via order_items.product_id)

USAGE:
1. Products are created by administrators
2. Order Bookers select products when creating orders
3. Order Items reference products via product_id
4. Product name is also stored in order_items.product_name for backward compatibility
"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime
from sqlalchemy.sql import func
from config.database import Base


class Product(Base):
    """
    Product table model.
    
    Maps to the 'products' table in PostgreSQL.
    Each record represents a product that can be ordered.
    """
    __tablename__ = "products"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the product.
    Auto-incremented by database.
    """

    # Product Information
    code = Column(String(50), unique=True, nullable=False, index=True)
    """
    Product code (unique identifier).
    - Unique code for the product (e.g., "TTP-500", "TTR-250")
    - Used for quick identification and lookup
    - Example: "TTP-500" = "Tulip Tea Premium 500g"
    """

    name = Column(String(255), nullable=False, index=True)
    """
    Product name.
    - Full name of the product
    - Example: "Tulip Tea Premium 500g"
    - Used for display in order forms and invoices
    """

    unit = Column(String(20), nullable=True)
    """
    Unit of measurement.
    - Unit in which the product is sold
    - Examples: "kg", "pcs", "box", "pack", "g"
    - Used for quantity display and calculations
    """

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    """
    Active status.
    - TRUE: Product is available for ordering
    - FALSE: Product is discontinued/hidden
    - Used to hide products without deleting them
    """

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    """
    Timestamp when product was created.
    - Automatically set by database on INSERT
    - Used for auditing
    """

    updated_at = Column(DateTime(timezone=False), onupdate=func.now())
    """
    Timestamp when product was last updated.
    - Automatically updated by database on UPDATE
    - Used for tracking modifications
    - Null on initial creation
    """

    # Soft Delete
    deleted_at = Column(DateTime(timezone=False), nullable=True, index=True)
    """
    Soft delete timestamp.
    - When set, product is considered deleted but data is preserved
    - NULL = active record
    - Used for soft delete functionality
    """


