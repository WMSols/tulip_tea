"""
Route-Shop Junction Table Model
================================
SQLAlchemy ORM model for the 'route_shops' junction table.

PURPOSE:
Junction table for many-to-many relationship between Routes and Shops.
A route can contain multiple shops, and a shop can belong to multiple routes
(though typically a shop belongs to one primary route).

RELATIONSHIP:
Routes ←→ Shops (Many-to-Many)
- One route can have many shops
- One shop can be on multiple routes (rare, but possible)

SEQUENCE:
The sequence field defines the order in which shops should be visited
on a route. This helps with:
- Route optimization
- Delivery planning
- Visit order for Order Bookers

USAGE:
1. Distributor/Order Booker creates a route
2. Shops are assigned to the route via this junction table
3. Sequence number determines visit order
4. Order Booker visits shops in sequence order
5. Delivery Man follows same sequence for deliveries

DATABASE TABLE: route_shops
"""
from sqlalchemy import Column, BigInteger, Integer, ForeignKey, DateTime
from config.database import Base


class RouteShop(Base):
    """
    Route-Shop junction table model.
    
    Maps to the 'route_shops' table in PostgreSQL.
    This table links routes to shops and defines the visit sequence.
    """
    __tablename__ = "route_shops"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the route-shop relationship.
    Auto-incremented by database.
    Each row represents one shop's membership in one route.
    """

    # Foreign Keys
    route_id = Column(BigInteger, ForeignKey("routes.id"), nullable=True)
    """
    Foreign key to routes table.
    - Links this junction record to a specific route
    - Nullable: For flexibility (can be assigned later)
    - Used for:
      * Finding all shops on a route
      * Filtering route-shop relationships by route
    """

    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=True)
    """
    Foreign key to shops table.
    - Links this junction record to a specific shop
    - Nullable: For flexibility (can be assigned later)
    - Used for:
      * Finding all routes a shop belongs to
      * Filtering route-shop relationships by shop
    """

    # Sequence
    sequence = Column(Integer, nullable=True)
    """
    Visit sequence number for this shop on the route.
    - Defines the order in which shops should be visited
    - Lower numbers = visited earlier
    - Example: 1 = first shop, 2 = second shop, etc.
    - Nullable: Can be set later or auto-calculated
    - Used for:
      * Route optimization
      * Delivery planning
      * Generating delivery lists in order
    """

    # Soft Delete
    # NOTE: Temporarily commented out until database column is added
    # Run sql/add_deleted_at_to_route_shops.sql to add the column, then uncomment this
    # deleted_at = Column(DateTime(timezone=False), nullable=True)
    # """
    # Soft delete timestamp.
    # - When set, shop-route relationship is considered deleted but data is preserved
    # - NULL = active record
    # - Used for soft delete functionality
    # """



