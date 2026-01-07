"""
Payment Database Model
=======================
SQLAlchemy ORM model for the 'payments' table.

PURPOSE:
Represents a payment record that was created from an approved daily collection.
Payments are the final, approved records of money collected from shops.

WORKFLOW:
1. Order Booker submits daily collection (status: "pending")
2. Distributor approves collection
3. Payment record is automatically created
4. Daily collection status changes to "approved" and links to payment_id
5. Payment is now in the system as an official record

RELATIONSHIPS:
- Belongs to a Shop (via shop_id foreign key)
- Created from Daily Collection (via daily_collection_id foreign key)
- Collected by an Order Booker (via collected_by_order_booker foreign key)
- Approved by a Distributor (via approved_by_distributor foreign key)

DATABASE TABLE: payments
"""
from sqlalchemy import Column, BigInteger, Numeric, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func
from config.database import Base


class Payment(Base):
    """
    Payment table model.
    
    Maps to the 'payments' table in PostgreSQL.
    Each payment represents an approved collection that has been moved from daily_collections.
    """
    __tablename__ = "payments"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the payment.
    Auto-incremented by database.
    """

    # Relationships
    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=False)
    """
    Foreign key to shops table.
    - Links payment to the shop where payment was collected
    - Required field
    - Used for tracking which shop the payment belongs to
    """

    daily_collection_id = Column(BigInteger, ForeignKey("daily_collections.id"), nullable=True)
    """
    Foreign key to daily_collections table.
    - Links payment to the daily collection it was created from
    - Nullable: For flexibility (could be created directly)
    - Used for tracking which collection this payment came from
    """

    collected_by_order_booker = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=False)
    """
    Foreign key to order_bookers table.
    - Links payment to the order booker who collected it
    - Required field
    - Used for tracking who collected the payment
    """

    approved_by_distributor = Column(BigInteger, ForeignKey("distributors.id"), nullable=False)
    """
    Foreign key to distributors table.
    - Links payment to the distributor who approved it
    - Required field
    - Used for tracking who approved the collection
    """

    # Financial Information
    amount = Column(Numeric(10, 2), nullable=False)
    """
    Payment amount.
    - Required field
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 5000.00 (Rs. 5,000)
    - Represents the approved amount collected from the shop
    """

    # Additional Information
    remarks = Column(Text, nullable=True)
    """
    Remarks or notes about the payment.
    - Optional field
    - Can contain notes from order booker or distributor
    - Used for additional information or context
    """

    # Timestamps
    collected_at = Column(DateTime(timezone=True), nullable=True)
    """
    Timestamp when payment was collected (at shop).
    - Can be different from created_at
    - Used for tracking actual collection time
    - Timezone-aware (stores UTC)
    """

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when payment record was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and sorting
    - This is when the collection was approved and payment was created
    """




