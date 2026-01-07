"""
Shop Visit Database Model
==========================
SQLAlchemy ORM model for the 'shop_visits' table.

PURPOSE:
Tracks visits made by Order Bookers and Delivery Men to shops. This is used for:
- Attendance tracking
- Route compliance verification
- GPS location validation
- Visit history and analytics

VISIT TYPES:
- "order_booking": Order booker visiting to take orders
- "delivery": Delivery man visiting to deliver orders
- "collection": Collecting payments
- "inspection": General shop inspection
- "other": Other types of visits

RELATIONSHIPS:
- Belongs to a Shop (via shop_id foreign key)
- Made by an Order Booker (via order_booker_id foreign key) - Optional
- Made by a Delivery Man (via delivery_man_id foreign key) - Optional
- At least one of order_booker_id or delivery_man_id must be provided

GPS VALIDATION:
- GPS coordinates are captured during visit
- Can be compared with shop's registered GPS to validate visit location
- Format: Decimal degrees (e.g., 33.6844, 73.0479)

PHOTO PROOF:
- Photo can be stored as base64 string or URL
- Used to verify visit actually occurred
- Optional but recommended for important visits

DATABASE TABLE: shop_visits
"""
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from config.database import Base


class ShopVisit(Base):
    """
    Shop Visit table model.
    
    Maps to the 'shop_visits' table in PostgreSQL.
    Each record represents a visit by an order booker or delivery man to a shop.
    """
    __tablename__ = "shop_visits"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the visit.
    Auto-incremented by database.
    """

    # Foreign Keys
    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=True)
    """
    Foreign key to shops table.
    - Links visit to the shop that was visited
    - Nullable: Visit can exist without shop reference (rare)
    - Example: Shop ID 1 = "Ali General Store"
    """

    order_booker_id = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=True)
    """
    Foreign key to order_bookers table.
    - Links visit to the order booker who made the visit
    - Nullable: Visit can be made by delivery man instead
    - Example: Order Booker ID 1 = "Ahmed Khan"
    """

    delivery_man_id = Column(BigInteger, ForeignKey("delivery_men.id"), nullable=True)
    """
    Foreign key to delivery_men table.
    - Links visit to the delivery man who made the visit
    - Nullable: Visit can be made by order booker instead
    - At least one of order_booker_id or delivery_man_id should be provided
    - Example: Delivery Man ID 1 = "Hassan Ali"
    """

    # Visit Details
    visit_type = Column(Text, nullable=True)
    """
    Type of visit.
    - Common values: "order_booking", "delivery", "collection", "inspection", "other"
    - Used to categorize visits for reporting
    - Example: "order_booking" = Order booker visiting to take orders
    """

    gps_lat = Column(Numeric, nullable=True)
    """
    GPS latitude where visit was recorded.
    - Captured from device GPS during visit
    - Can be compared with shop's registered GPS for validation
    - Format: Decimal degrees (e.g., 33.6844)
    - Example: 33.6844 (Islamabad)
    """

    gps_lng = Column(Numeric, nullable=True)
    """
    GPS longitude where visit was recorded.
    - Captured from device GPS during visit
    - Can be compared with shop's registered GPS for validation
    - Format: Decimal degrees (e.g., 73.0479)
    - Example: 73.0479 (Islamabad)
    """

    visit_time = Column(DateTime(timezone=True), nullable=True)
    """
    Timestamp when visit occurred.
    - Can be set manually or automatically from device time
    - Timezone-aware (stores UTC)
    - Used for attendance tracking and route compliance
    - Example: 2026-01-07 10:30:00 UTC
    """

    photo = Column(Text, nullable=True)
    """
    Photo proof of visit.
    - Can be stored as base64 string or URL
    - Used to verify visit actually occurred
    - Optional but recommended for important visits
    - Example: "data:image/jpeg;base64,..." or "https://..."
    """

    reason = Column(Text, nullable=True)
    """
    Reason or notes for the visit.
    - Free-form text field for additional context
    - Can include visit purpose, issues found, etc.
    - Example: "Regular order booking visit", "Shop owner requested meeting"
    """
    
    # Note: The database table does not have a created_at column
    # If you need timestamps, use visit_time field or add created_at to the database schema

