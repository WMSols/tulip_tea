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
- Can be linked to an Order (via order_id foreign key)
- Received by a Distributor (via received_by_distributor foreign key)

DATABASE TABLE: payments
Actual columns: id, shop_id, order_id, amount, received_by_distributor, payment_date
"""
from sqlalchemy import Column, BigInteger, Numeric, DateTime, ForeignKey
from config.database import Base


class Payment(Base):
    """
    Payment table model.
    
    Maps to the 'payments' table in PostgreSQL.
    Each payment represents an approved daily collection that has been verified by a distributor.
    
    WORKFLOW:
    1. Order Booker creates daily collection (in daily_collections table)
    2. Distributor verifies the daily collection
    3. Payment record is created in payments table (this table)
    4. Payment is used for calculating outstanding balance
    """
    __tablename__ = "payments"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the payment.
    Auto-incremented by database.
    """

    # Relationships
    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=True)
    """
    Foreign key to shops table.
    - Links payment to the shop where payment was collected
    - Used for tracking which shop the payment belongs to
    - Used for calculating outstanding balance
    """

    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=True)
    """
    Foreign key to orders table.
    - Links payment to a specific order (if applicable)
    - Optional field
    """

    # Financial Information
    amount = Column(Numeric, nullable=True)
    """
    Payment amount.
    - Format: Decimal
    - Example: 5000.00 (Rs. 5,000)
    - Represents the verified amount collected from the shop
    - Used for calculating outstanding balance
    """

    # Distributor Information
    received_by_distributor = Column(BigInteger, ForeignKey("distributors.id"), nullable=True)
    """
    Foreign key to distributors table.
    - Links payment to the distributor who received/verified it
    - Optional field
    """

    # Timestamps
    payment_date = Column(DateTime, nullable=True)
    """
    Timestamp when payment was received.
    - Used for tracking when payment was actually received
    """





