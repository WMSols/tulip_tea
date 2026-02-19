"""
Zone Database Model
===================
SQLAlchemy ORM model for the 'zones' table.

PURPOSE:
Represents a geographic zone/area in the distribution system. Zones are used
to organize distributors, order bookers, delivery men, routes, and shops
by geographic location.

USAGE:
- Distributors CREATE zones (but are not assigned to them)
- Order Bookers are assigned to zones
- Delivery Men are assigned to zones
- Routes are created within zones
- Shops are registered in zones

EXAMPLES:
- "Islamabad"
- "Rawalpindi"
- "Chakwal"
- "Lahore"

RELATIONSHIPS:
- Created by Distributors (distributors create zones but are not assigned to them)
- Has many Order Bookers (via order_bookers.zone_id)
- Has many Delivery Men (via delivery_men.zone_id)
- Has many Routes (via routes.zone_id)
- Has many Shops (via shops.zone_id)

IMPORTANT:
- Distributors can CREATE zones but are NOT assigned to zones
- Zones are assigned to Order Bookers and Delivery Men
- This allows distributors to manage multiple zones

DATABASE TABLE: zones
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from config.database import Base


class Zone(Base):
    """
    Zone table model.
    
    Maps to the 'zones' table in PostgreSQL.
    Each zone represents a geographic area for organizing operations.
    """
    __tablename__ = "zones"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the zone.
    Auto-incremented by database.
    Used as foreign key in: order_bookers, delivery_men, routes, shops
    Note: Distributors are NOT assigned to zones - they create zones but are not assigned to them
    """

    # Relationships
    distributor_id = Column(BigInteger, ForeignKey("distributors.id"), nullable=True)
    """
    Foreign key to distributors table.
    - Links zone to the distributor who created it
    - Nullable: For backward compatibility with existing zones
    - Used for data isolation: distributors can only see/manage their own zones
    - Order Bookers and Delivery Men see zones from their distributor
    """

    # Basic Information
    name = Column(String, nullable=False, unique=True)
    """
    Zone name.
    - Required field
    - Unique constraint: No two zones can have the same name
    - Used for display and identification
    - Examples: "Islamabad", "Rawalpindi", "Chakwal"
    - Case-sensitive: "Islamabad" ≠ "islamabad"
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when zone record was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and sorting
    - Zones are rarely deleted (historical data preservation)
    """

    # Soft Delete
    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """
    Soft delete timestamp.
    - When set, zone is considered deleted but data is preserved
    - NULL = active record
    - Used for soft delete functionality
    """

    # Activation Status
    is_active = Column(Boolean, nullable=False, default=True)
    """
    Activation status.
    - TRUE = active (zone is operational)
    - FALSE = inactive (zone is suspended)
    - Default: TRUE
    - Used for temporary suspension without deletion
    """



