"""
Delivery Man-Route Junction Table Model
=======================================
SQLAlchemy ORM model for the 'delivery_man_routes' junction table.

PURPOSE:
Junction table for many-to-many relationship between Delivery Men and Routes.
A delivery man can be assigned to multiple routes, and a route can have multiple delivery men.

RELATIONSHIP:
Delivery Men ←→ Routes (Many-to-Many)
- One delivery man can be assigned to many routes
- One route can have many delivery men assigned

WORKFLOW:
1. Distributor creates a delivery man and assigns zone
2. Distributor assigns routes to the delivery man via this junction table
3. Delivery man can deliver orders to shops on assigned routes
4. Orders are assigned to delivery men based on route assignment

USAGE:
1. Distributor creates delivery man with zone_id
2. Routes are assigned to delivery man via this junction table
3. When assigning orders, system can filter by delivery man's assigned routes
4. Delivery man sees orders for shops on their assigned routes

DATABASE TABLE: delivery_man_routes
"""
from sqlalchemy import Column, BigInteger, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from config.database import Base


class DeliveryManRoute(Base):
    """
    Delivery Man-Route junction table model.
    
    Maps to the 'delivery_man_routes' table in PostgreSQL.
    This table links delivery men to routes they are assigned to deliver on.
    """
    __tablename__ = "delivery_man_routes"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the delivery man-route relationship.
    Auto-incremented by database.
    Each row represents one delivery man's assignment to one route.
    """

    # Foreign Keys
    delivery_man_id = Column(BigInteger, ForeignKey("delivery_men.id", ondelete="CASCADE"), nullable=False)
    """
    Foreign key to delivery_men table.
    - Links this junction record to a specific delivery man
    - Required field
    - CASCADE delete: If delivery man is deleted, all route assignments are deleted
    - Used for:
      * Finding all routes assigned to a delivery man
      * Filtering delivery man-route relationships by delivery man
    """

    route_id = Column(BigInteger, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    """
    Foreign key to routes table.
    - Links this junction record to a specific route
    - Required field
    - CASCADE delete: If route is deleted, all delivery man assignments are deleted
    - Used for:
      * Finding all delivery men assigned to a route
      * Filtering delivery man-route relationships by route
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when delivery man-route assignment was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and tracking when assignment was made
    """

    # Soft Delete
    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """
    Soft delete timestamp.
    - When set, delivery man-route assignment is considered deleted but data is preserved
    - NULL = active assignment
    - Used for soft delete functionality (unassigning without losing history)
    """

    # Unique Constraint: One delivery man can only be assigned to a route once
    __table_args__ = (
        UniqueConstraint('delivery_man_id', 'route_id', name='uq_delivery_man_route'),
    )






