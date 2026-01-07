"""
Shop Database Model
===================
SQLAlchemy ORM model for the 'shops' table.

PURPOSE:
Represents a shop/store where tea products are sold. Shops are registered
by Order Bookers during field visits and are assigned to routes for delivery.

REGISTRATION WORKFLOW:
1. Order Booker visits a new shop location
2. Captures GPS coordinates (required)
3. Takes photos (shop, owner, CNIC)
4. Registers shop via API with all details
5. Shop is assigned to a route
6. Orders can be created for the shop

RELATIONSHIPS:
- Belongs to a Zone (via zone_id foreign key)
- Registered by an Order Booker (via created_by_order_booker foreign key) - Historical/Immutable
- Currently assigned to an Order Booker (via assigned_to_order_booker foreign key) - Mutable
- Can belong to Routes (via route_shops junction table)
- Has Orders (via orders.shop_id)
- Has Payments (via payments.shop_id)
- Has Daily Collections (via daily_collections.shop_id)

IMPORTANT: 
- created_by_order_booker: Tracks who originally registered the shop (never changes)
- assigned_to_order_booker: Tracks current responsibility (can be reassigned)
- When shop is created, both fields are set to the same order booker
- When order booker is deleted, shops can be reassigned by updating assigned_to_order_booker

GPS VALIDATION:
- GPS coordinates are required for shop registration
- Used to validate Order Booker visits (must be near shop location)
- Format: Decimal degrees (e.g., 33.6844, 73.0479 for Islamabad)

DATABASE TABLE: shops
"""
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from config.database import Base


class Shop(Base):
    """
    Shop table model.
    
    Maps to the 'shops' table in PostgreSQL.
    Each shop represents a retail location where tea products are sold.
    """
    __tablename__ = "shops"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the shop.
    Auto-incremented by database.
    Used as foreign key in: orders, payments, daily_collections, route_shops
    """

    # Basic Information
    name = Column(String, nullable=False)
    """
    Shop name.
    - Required field
    - Used for display and identification
    - Examples: "Ali General Store", "Khan Tea Shop", "Central Market"
    - Not unique: Multiple shops can have the same name
    """

    owner_name = Column(String)
    """
    Shop owner's full name.
    - Optional field
    - Used for identification and communication
    - Example: "Ahmed Ali", "Fatima Khan"
    """

    owner_phone = Column(String)
    """
    Shop owner's phone number.
    - Optional field
    - Used for communication and order confirmation
    - Format: Usually 11 digits (e.g., "03001234567")
    - Not unique: Owner can have multiple shops
    """

    # GPS Coordinates (Required for Registration)
    gps_lat = Column(Numeric(10, 8))
    """
    GPS Latitude coordinate.
    - Required for shop registration
    - Format: Decimal degrees (10 digits total, 8 decimal places)
    - Range: -90 to +90
    - Example: 33.6844 (Islamabad)
    - Used for:
      * Validating Order Booker visits (must be near shop)
      * Route planning and navigation
      * Location verification
    """

    gps_lng = Column(Numeric(11, 8))
    """
    GPS Longitude coordinate.
    - Required for shop registration
    - Format: Decimal degrees (11 digits total, 8 decimal places)
    - Range: -180 to +180
    - Example: 73.0479 (Islamabad)
    - Used for:
      * Validating Order Booker visits (must be near shop)
      * Route planning and navigation
      * Location verification
    """

    # Financial Information
    credit_limit = Column(Numeric(10, 2), default=0)
    """
    Maximum credit limit for the shop.
    - Default: 0 (no credit allowed initially)
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 50000.00 (Rs. 50,000)
    - Used to:
      * Prevent orders exceeding credit limit
      * Track shop's credit capacity
      * Set by KPO/Area Manager during approval
    """

    legacy_balance = Column(Numeric(10, 2), default=0)
    """
    Outstanding balance from previous system (if any).
    - Default: 0 (no legacy balance)
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 15000.50 (Rs. 15,000.50)
    - Used to:
      * Track existing debts when migrating from old system
      * Include in total outstanding calculation
    """

    # Status
    is_registered = Column(Boolean, default=False)
    """
    Registration status flag (legacy field).
    - Default: False (not yet registered/approved)
    - True: Shop is fully registered and approved
    - Used to:
      * Track approval status (pending/approved)
      * Filter shops by registration status
      * Prevent orders for unregistered shops
    Note: Consider using registration_status field instead
    """

    registration_status = Column(String, nullable=True)
    """
    Registration status of the shop.
    - Values: "pending", "approved", "rejected"
    - Default: "pending" when shop is first registered
    - "pending": Awaiting distributor verification
    - "approved": Distributor verified, shop is active
    - "rejected": Distributor rejected the registration
    - Used for tracking shop registration workflow
    """

    verified_by_distributor = Column(BigInteger, ForeignKey("distributors.id"), nullable=True)
    """
    Foreign key to distributors table.
    - Links shop to the distributor who verified/approved it
    - Nullable: Set when distributor verifies the shop
    - Used for tracking who approved the shop registration
    """

    verified_at = Column(DateTime(timezone=True), nullable=True)
    """
    Timestamp when distributor verified the shop.
    - Nullable: Set when distributor verifies/approves
    - Timezone-aware (stores UTC)
    - Used for tracking when shop was verified
    """

    # Relationships
    created_by_order_booker = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=True)
    """
    Foreign key to order_bookers table.
    - Links shop to the order booker who originally registered it
    - Nullable: For flexibility (could be created by admin)
    - IMMUTABLE: This field should never change once set (for audit trail)
    - Used for:
      * Historical tracking of who registered the shop
      * Audit purposes and reporting
      * Preserving original creator information
    Note: This is different from assigned_to_order_booker which tracks current responsibility
    """

    assigned_to_order_booker = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=True)
    """
    Foreign key to order_bookers table.
    - Links shop to the order booker currently responsible for it
    - Nullable: Shop can exist without current assignment
    - MUTABLE: Can be updated when shop is reassigned to another order booker
    - Used for:
      * Tracking current responsibility for the shop
      * Filtering shops by current order booker
      * Reassigning shops when order booker is deleted
      * Operational queries (who should handle this shop now)
    Note: Initially set to same as created_by_order_booker, but can be changed independently
    """

    zone_id = Column(BigInteger, ForeignKey("zones.id"), nullable=True)
    """
    Foreign key to zones table.
    - Links shop to its geographic zone
    - Nullable: Can be assigned later
    - Used for:
      * Filtering shops by zone
      * Ensuring shop is in correct zone
      * Zone-based reporting
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when shop record was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and sorting
    """

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """
    Timestamp when shop record was last updated.
    - Automatically updated by database on UPDATE
    - Timezone-aware (stores UTC)
    - Used for tracking modifications
    - Null on initial creation
    """

