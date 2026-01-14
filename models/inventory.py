"""
Inventory Database Model
========================
SQLAlchemy ORM model for the 'inventory' table.

PURPOSE:
Represents inventory items stored in warehouses. Each inventory item belongs
to a warehouse and tracks the quantity of a specific product/item.

RELATIONSHIPS:
- Belongs to a Warehouse (via warehouse_id foreign key)
- One warehouse can have many inventory items

DATABASE TABLE: inventory
"""
from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, DateTime, Numeric
from sqlalchemy.sql import func
from config.database import Base


class Inventory(Base):
    """
    Inventory database model.
    
    Maps to the 'inventory' table in PostgreSQL.
    """
    __tablename__ = "inventory"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """Primary key: Unique identifier for the inventory item."""

    # Foreign Keys
    warehouse_id = Column(BigInteger, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    """Foreign key to warehouses table. Inventory item belongs to a warehouse."""

    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    """
    Foreign key to products table.
    - Links inventory item to a product from the products table
    - SET NULL on delete: If product is deleted, product_id is set to NULL but inventory item remains
    - Nullable: For backward compatibility with existing data
    - When set, item_name, item_code, and unit should match the product
    """

    # Item Information (kept for backward compatibility and when product_id is NULL)
    item_name = Column(String, nullable=False)
    """Name of the inventory item (e.g., 'Tea Packet 500g'). Should match product.name if product_id is set."""

    item_code = Column(String, nullable=True)
    """Optional item code/SKU for the inventory item. Should match product.code if product_id is set."""

    unit = Column(String, nullable=True)
    """Unit of measurement (e.g., 'kg', 'packet', 'box'). Should match product.unit if product_id is set."""

    quantity = Column(Integer, nullable=False, default=0)
    """Current quantity of the item in stock."""

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    """Timestamp when inventory item was created."""

    updated_at = Column(DateTime(timezone=False), onupdate=func.now())
    """Timestamp when inventory item was last updated."""

    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """Soft delete timestamp. NULL = active inventory item."""

