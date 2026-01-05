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
- Collected by an Order Booker (via collected_by_order_booker foreign key)
- Reviewed by a Distributor (via reviewed_by_distributor foreign key)
- Moves to Payment (via payment_id reference, created after approval)

DATABASE TABLE: daily_collections
"""
from sqlalchemy import Column, BigInteger, Numeric, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func
from config.database import Base


class DailyCollection(Base):
    """
    Daily Collection table model.
    
    Maps to the 'daily_collections' table in PostgreSQL.
    Each entry represents a collection made by an Order Booker that needs distributor approval.
    """
    __tablename__ = "daily_collections"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the collection entry.
    Auto-incremented by database.
    """

    # Relationships
    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=False)
    """
    Foreign key to shops table.
    - Links collection to the shop where payment was collected
    - Required field
    - Used for tracking which shop the collection belongs to
    """

    collected_by_order_booker = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=False)
    """
    Foreign key to order_bookers table.
    - Links collection to the order booker who collected it
    - Required field
    - Used for tracking who submitted the collection
    """

    # Financial Information
    amount = Column(Numeric(10, 2), nullable=False)
    """
    Collection amount.
    - Required field
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 5000.00 (Rs. 5,000)
    - Represents the amount collected from the shop
    """

    # Status and Review
    status = Column(String, nullable=False, default="pending")
    """
    Collection status.
    - Values: "pending", "approved", "rejected"
    - Default: "pending" when first submitted
    - "pending": Awaiting distributor approval
    - "approved": Distributor approved, moved to payment
    - "rejected": Distributor rejected the collection
    """

    reviewed_by_distributor = Column(BigInteger, ForeignKey("distributors.id"), nullable=True)
    """
    Foreign key to distributors table.
    - Links collection to the distributor who reviewed it
    - Nullable: Set when distributor reviews
    - Used for tracking who approved/rejected the collection
    """

    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    """
    Timestamp when distributor reviewed the collection.
    - Nullable: Set when distributor reviews
    - Timezone-aware (stores UTC)
    - Used for tracking when collection was reviewed
    """

    remarks = Column(Text, nullable=True)
    """
    Remarks or notes about the collection.
    - Optional field
    - Can contain notes from order booker or distributor
    - Used for rejection reasons or additional information
    """

    # Reference to Payment (created after approval)
    payment_id = Column(BigInteger, ForeignKey("payments.id"), nullable=True)
    """
    Foreign key to payments table.
    - Links to the payment record created after approval
    - Nullable: Set when collection is approved and payment is created
    - Used for tracking which payment this collection became
    """

    # Timestamps
    collected_at = Column(DateTime(timezone=True), nullable=True)
    """
    Timestamp when collection was made (at shop).
    - Can be different from created_at
    - Used for tracking actual collection time
    - Timezone-aware (stores UTC)
    """

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when collection entry was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and sorting
    """

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """
    Timestamp when collection entry was last updated.
    - Automatically updated by database on UPDATE
    - Timezone-aware (stores UTC)
    - Used for tracking modifications
    - Null on initial creation
    """

