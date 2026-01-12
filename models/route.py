"""
Route Database Model
====================
SQLAlchemy ORM model for the 'routes' table.

PURPOSE:
Represents a delivery route that contains multiple shops. Routes are used
to organize shop visits for Order Bookers and Delivery Men.

WORKFLOW:
1. Distributor creates a route in a zone
2. Route is assigned to an Order Booker
3. Shops are assigned to the route (via route_shops junction table)
4. Order Booker visits shops on the route
5. Delivery Man delivers orders to shops on the route

EXAMPLES:
- "Route 1 - Islamabad Central"
- "Route 2 - Rawalpindi Market"
- "Route A - Chakwal Main"

RELATIONSHIPS:
- Belongs to a Zone (via zone_id foreign key)
- Created by a Distributor (via created_by_distributor foreign key)
- Assigned to an Order Booker (via order_booker_id foreign key)
- Has many Shops (via route_shops junction table)

DATABASE TABLE: routes
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from config.database import Base


class Route(Base):
    """
    Route table model.
    
    Maps to the 'routes' table in PostgreSQL.
    Each route represents a collection of shops that can be visited together.
    """
    __tablename__ = "routes"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the route.
    Auto-incremented by database.
    Used as foreign key in: route_shops (junction table)
    """

    # Basic Information
    name = Column(String, nullable=False)
    """
    Route name.
    - Required field
    - Used for display and identification
    - Examples: "Route 1", "Islamabad Central", "Market Area"
    - Not unique: Multiple routes can have the same name (but in different zones)
    """

    # Relationships
    zone_id = Column(BigInteger, ForeignKey("zones.id"), nullable=True)
    """
    Foreign key to zones table.
    - Links route to its geographic zone
    - Nullable: Can be assigned later
    - Used for filtering routes by zone
    - Ensures route is within a specific zone
    """

    created_by_distributor = Column(BigInteger, ForeignKey("distributors.id"), nullable=True)
    """
    Foreign key to distributors table.
    - Links route to the distributor who created it
    - Nullable: For flexibility (could be created by system admin)
    - Used for filtering routes by distributor
    - Tracks who created the route for auditing
    """

    order_booker_id = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=True)
    """
    Foreign key to order_bookers table.
    - Links route to the order booker assigned to it
    - Nullable: Route can exist without assignment initially
    - Used for filtering routes by order booker
    - When assigned, order booker is responsible for visiting shops on this route
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when route record was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and sorting
    """

    # Soft Delete
    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """
    Soft delete timestamp.
    - When set, route is considered deleted but data is preserved
    - NULL = active record
    - Used for soft delete functionality
    """

    # Activation Status
    is_active = Column(Boolean, nullable=False, default=True)
    """
    Activation status.
    - TRUE = active (route is operational)
    - FALSE = inactive (route is suspended)
    - Default: TRUE
    - Used for temporary suspension without deletion
    """

