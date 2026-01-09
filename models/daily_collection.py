"""
Daily Collection Database Model
================================
SQLAlchemy ORM model for the 'daily_collections' table.

PURPOSE:
Represents a daily collection entry submitted by an Order Booker for a shop.
Collections must be approved by a Distributor before being moved to the payment table.

WORKFLOW:
1. Order Booker visits shop and collects payment
2. Order Booker submits daily collection entry
3. Status: "pending" (awaiting distributor approval)
4. Distributor reviews and approves/rejects
5. If approved: Status changes to "approved" and moves to payment table
6. If rejected: Status changes to "rejected" with remarks

RELATIONSHIPS:
- Belongs to a Shop (via shop_id foreign key)
- Can be linked to an Order (via order_id foreign key)
- Collected by an Order Booker (via collected_by_order_booker foreign key)
- Can be collected by Delivery Man (via collected_by_delivery_man foreign key)
- Verified by a Distributor (via verified_by_distributor foreign key)
- Linked to Visit (via visit_id foreign key)

DATABASE TABLE: daily_collections
Actual columns: id, shop_id, order_id, collected_by_delivery_man, verified_by_distributor, 
amount, status, collection_date, photo_proof, visit_id, collected_by_order_booker
"""
from sqlalchemy import Column, BigInteger, Numeric, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func
from config.database import Base


class DailyCollection(Base):
    """
    Daily Collection table model.
    
    Maps to the 'daily_collections' table in PostgreSQL.
    Each entry represents a collection made by an Order Booker or Delivery Man that needs distributor verification.
    """
    __tablename__ = "daily_collections"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the collection entry.
    Auto-incremented by database.
    """

    # Relationships
    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=True)
    """
    Foreign key to shops table.
    - Links collection to the shop where payment was collected
    - Used for tracking which shop the collection belongs to
    """

    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=True)
    """
    Foreign key to orders table.
    - Links collection to a specific order (if applicable)
    - Optional field
    """

    collected_by_order_booker = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=True)
    """
    Foreign key to order_bookers table.
    - Links collection to the order booker who collected it
    - Nullable: Can also be collected by delivery man
    - Used for tracking who submitted the collection
    """

    collected_by_delivery_man = Column(BigInteger, ForeignKey("delivery_men.id"), nullable=True)
    """
    Foreign key to delivery_men table.
    - Links collection to the delivery man who collected it
    - Nullable: Can also be collected by order booker
    - Used for tracking who submitted the collection
    """

    verified_by_distributor = Column(BigInteger, ForeignKey("distributors.id"), nullable=True)
    """
    Foreign key to distributors table.
    - Links collection to the distributor who verified it
    - Nullable: Set when distributor verifies
    - Used for tracking who verified the collection
    """

    visit_id = Column(BigInteger, ForeignKey("shop_visits.id"), nullable=True)
    """
    Foreign key to shop_visits table.
    - Links collection to the visit where it was collected
    - Nullable: For collections created outside of visits
    """

    # Financial Information
    amount = Column(Numeric, nullable=True)
    """
    Collection amount.
    - Format: Decimal
    - Example: 5000.00 (Rs. 5,000)
    - Represents the amount collected from the shop
    """

    # Status
    status = Column(String, nullable=True)
    """
    Collection status.
    - Values: "pending", "verified", "rejected"
    - Default: "pending" when first submitted
    - "pending": Awaiting distributor verification
    - "verified": Distributor verified, moved to payment
    - "rejected": Distributor rejected the collection
    """

    # Timestamps
    collection_date = Column(DateTime, nullable=True)
    """
    Timestamp when collection was made (at shop).
    - Used for tracking actual collection time
    """

    # Photo Proof
    photo_proof = Column(Text, nullable=True)
    """
    Photo proof of collection.
    - Optional field
    - Can contain URL or base64 encoded image
    - Used for verification purposes
    """





