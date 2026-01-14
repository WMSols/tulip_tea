"""
Delivery Man-Warehouse Junction Table Model
===========================================
SQLAlchemy ORM model for the 'delivery_man_warehouses' junction table.

PURPOSE:
Junction table for many-to-many relationship between Delivery Men and Warehouses.
A delivery man can be assigned to multiple warehouses, and a warehouse can have
multiple delivery men assigned.

RELATIONSHIP:
Delivery Men ←→ Warehouses (Many-to-Many)
- One delivery man can be assigned to many warehouses
- One warehouse can have many delivery men assigned

WORKFLOW:
1. Distributor creates a warehouse in a zone
2. Distributor assigns delivery men to the warehouse via this junction table
3. Delivery men can manage inventory and fulfill orders from assigned warehouses

DATABASE TABLE: delivery_man_warehouses
"""
from sqlalchemy import Column, BigInteger, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from config.database import Base


class DeliveryManWarehouse(Base):
    """
    Delivery Man-Warehouse junction table model.
    
    Maps to the 'delivery_man_warehouses' table in PostgreSQL.
    """
    __tablename__ = "delivery_man_warehouses"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """Primary key: Unique identifier for the delivery man-warehouse relationship."""

    # Foreign Keys
    delivery_man_id = Column(BigInteger, ForeignKey("delivery_men.id", ondelete="CASCADE"), nullable=False)
    """Foreign key to delivery_men table."""

    warehouse_id = Column(BigInteger, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    """Foreign key to warehouses table."""

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """Timestamp when delivery man-warehouse assignment was created."""

    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """Soft delete timestamp. NULL = active assignment."""

    # Unique Constraint: One delivery man can only be assigned to a warehouse once
    __table_args__ = (
        UniqueConstraint('delivery_man_id', 'warehouse_id', name='uq_delivery_man_warehouse'),
    )


