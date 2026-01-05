"""
Zone Database Model
===================
SQLAlchemy ORM model for the 'zones' table.

PURPOSE:
Represents a geographic zone/area in the distribution system. Zones are used
to organize distributors, order bookers, delivery men, routes, and shops
by geographic location.

USAGE:
- Distributors are assigned to zones
- Order Bookers work in specific zones
- Delivery Men operate in specific zones
- Routes are created within zones
- Shops are registered in zones

EXAMPLES:
- "Islamabad"
- "Rawalpindi"
- "Chakwal"
- "Lahore"

RELATIONSHIPS:
- Has many Distributors (via distributors.zone_id)
- Has many Order Bookers (via order_bookers.zone_id)
- Has many Delivery Men (via delivery_men.zone_id)
- Has many Routes (via routes.zone_id)
- Has many Shops (via shops.zone_id)

DATABASE TABLE: zones
"""
from sqlalchemy import Column, BigInteger, String, DateTime
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
    Used as foreign key in: distributors, order_bookers, delivery_men, routes, shops
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



