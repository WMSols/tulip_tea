"""
Visit Type Database Model
==========================
SQLAlchemy ORM model for the 'visit_types' junction table.

PURPOSE:
Junction table for many-to-many relationship between Shop Visits and Visit Types.
Allows a single visit to have multiple types (e.g., order_booking + daily_collections).

RELATIONSHIP:
Shop Visits ←→ Visit Types (Many-to-Many)
- One visit can have many types
- One type can be in many visits

USAGE:
1. Order Booker creates a visit
2. Multiple visit types are selected (e.g., "order_booking", "daily_collections")
3. Each type is stored as a separate row in visit_types table
4. When viewing visit, all types are retrieved

DATABASE TABLE: visit_types
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from config.database import Base


class VisitType(Base):
    """
    Visit Type junction table model.
    
    Maps to the 'visit_types' table in PostgreSQL.
    Each record represents one visit type associated with a visit.
    """
    __tablename__ = "visit_types"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the visit type association.
    Auto-incremented by database.
    """

    # Foreign Keys
    visit_id = Column(BigInteger, ForeignKey("shop_visits.id", ondelete="CASCADE"), nullable=False)
    """
    Foreign key to shop_visits table.
    - Links visit type to the visit
    - Required field
    - CASCADE delete: If visit is deleted, all its types are deleted
    - Example: Visit ID 1 = "Visit to Ali General Store"
    """

    visit_type = Column(String, nullable=False)
    """
    Type of visit.
    - Values: "order_booking", "daily_collections", "inspection", "delivery", "other"
    - Required field
    - Used to categorize what activities happened during the visit
    - Example: "order_booking" = Order was placed during this visit
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when visit type was associated with visit.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing
    """

    # Soft Delete
    # NOTE: Temporarily commented out until database column is added
    # Run sql/add_deleted_at_to_visit_types.sql to add the column, then uncomment this
    # deleted_at = Column(DateTime(timezone=False), nullable=True)
    # """
    # Soft delete timestamp.
    # - When set, visit type link is considered deleted but data is preserved
    # - NULL = active record
    # - Used for soft delete functionality
    # """

    # Unique constraint: Prevent duplicate types per visit
    __table_args__ = (
        UniqueConstraint('visit_id', 'visit_type', name='uq_visit_type'),
    )






