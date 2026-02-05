"""
Warehouse Database Model
========================
SQLAlchemy ORM model for the 'warehouses' table.

PURPOSE:
Represents a warehouse where inventory is stored. Warehouses are created by
distributors and assigned to zones. Delivery men can be assigned to warehouses
to manage inventory and fulfill orders.

RELATIONSHIPS:
- Belongs to a Zone (via zone_id foreign key)
- Has many Inventory Items (via inventory.warehouse_id)
- Can have Delivery Men assigned (via delivery_man_warehouses junction table)
- Created by Distributor (implicitly via zone management)

DATABASE TABLE: warehouses
"""
from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from config.database import Base


class Warehouse(Base):
    """
    Warehouse database model.
    
    Maps to the 'warehouses' table in PostgreSQL.
    """
    __tablename__ = "warehouses"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """Primary key: Unique identifier for the warehouse."""

    # Basic Information
    name = Column(String, nullable=False)
    """Warehouse name (e.g., 'Islamabad Main Warehouse')."""

    distributor_id = Column(BigInteger, ForeignKey("distributors.id"), nullable=False)
    """Foreign key to distributors table. One warehouse per distributor."""

    zone_id = Column(BigInteger, ForeignKey("zones.id"), nullable=True)
    """Foreign key to zones table. Warehouse can optionally belong to a zone (for backward compatibility)."""

    address = Column(Text, nullable=True)
    """Physical address of the warehouse."""

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    """Whether the warehouse is active. Inactive warehouses cannot receive new inventory."""

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    """Timestamp when warehouse was created."""

    updated_at = Column(DateTime(timezone=False), onupdate=func.now())
    """Timestamp when warehouse was last updated."""

    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """Soft delete timestamp. NULL = active warehouse."""


