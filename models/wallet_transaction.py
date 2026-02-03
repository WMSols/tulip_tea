"""
Wallet Transaction Database Model
==================================
SQLAlchemy ORM model for the 'wallet_transactions' table.

PURPOSE:
Represents a transaction in a wallet. Every credit, debit, transfer, or adjustment
is recorded here for complete audit trail.

RELATIONSHIPS:
- Belongs to a Wallet (via wallet_id foreign key)
- Can reference another Wallet for transfers (via related_wallet_id)

WORKFLOW:
1. Transaction is created when wallet balance changes
2. Balance before and after are recorded for audit
3. Reference to related entity (collection, order, etc.) is stored
4. Who initiated the transaction is tracked

DATABASE TABLE: wallet_transactions
"""
from sqlalchemy import Column, BigInteger, Numeric, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from config.database import Base


class WalletTransaction(Base):
    """
    Wallet Transaction table model.
    
    Maps to the 'wallet_transactions' table in PostgreSQL.
    Each transaction represents a movement of money in or out of a wallet.
    """
    __tablename__ = "wallet_transactions"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the transaction.
    Auto-incremented by database.
    """

    # Link to wallet
    wallet_id = Column(BigInteger, ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False)
    """
    Foreign key to wallets table.
    - Links transaction to the wallet it affects
    - RESTRICT delete: Cannot delete wallet with transactions
    """

    # Transaction details
    transaction_type = Column(String(20), nullable=False)
    """
    Type of transaction.
    - Values: 'credit' (money added), 'debit' (money removed), 
              'transfer_in' (received from another wallet),
              'transfer_out' (sent to another wallet),
              'adjustment' (manual correction)
    """
    
    amount = Column(Numeric(15, 2), nullable=False)
    """
    Transaction amount.
    - Format: Decimal (15 digits, 2 decimal places)
    - Always positive (enforced by CHECK constraint)
    - Example: 5000.00 (Rs. 5,000)
    """

    # Balance tracking (for audit and reconciliation)
    balance_before = Column(Numeric(15, 2), nullable=False)
    """
    Wallet balance before this transaction.
    - Used for audit trail and reconciliation
    - Cannot be negative (enforced by CHECK constraint)
    """
    
    balance_after = Column(Numeric(15, 2), nullable=False)
    """
    Wallet balance after this transaction.
    - Used for audit trail and reconciliation
    - Cannot be negative (enforced by CHECK constraint)
    - Should equal: balance_before + amount (for credit/transfer_in)
    - Should equal: balance_before - amount (for debit/transfer_out)
    """

    # Description and reference
    description = Column(Text, nullable=True)
    """
    Human-readable description of the transaction.
    - Example: "Collection from shop ABC", "Transfer to distributor"
    """
    
    reference_type = Column(String(50), nullable=True)
    """
    Type of related entity.
    - Values: 'order', 'collection', 'payment', 'transfer', 'adjustment', 'daily_collection'
    - Used with reference_id to link to related records
    """
    
    reference_id = Column(BigInteger, nullable=True)
    """
    ID of related entity.
    - If reference_type='daily_collection', this is collection_id
    - If reference_type='order', this is order_id
    - If reference_type='payment', this is payment_id
    - If reference_type='transfer', this is the other transaction_id
    """

    # Who initiated this transaction
    initiated_by_type = Column(String(20), nullable=True)
    """
    Type of user who initiated this transaction.
    - Values: 'distributor', 'order_booker', 'delivery_man', 'system'
    - Used with initiated_by_id to track who made the change
    """
    
    initiated_by_id = Column(BigInteger, nullable=True)
    """
    ID of user who initiated this transaction.
    - If initiated_by_type='distributor', this is distributor_id
    - If initiated_by_type='order_booker', this is order_booker_id
    - If initiated_by_type='delivery_man', this is delivery_man_id
    - If initiated_by_type='system', this is NULL
    """

    # For transfers: link to the other wallet
    related_wallet_id = Column(BigInteger, ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True)
    """
    Foreign key to wallets table.
    - For transfers: the other wallet involved in the transfer
    - SET NULL on delete: If related wallet is deleted, keep transaction but clear reference
    """

    # Additional metadata (JSON for flexibility)
    transaction_metadata = Column('metadata', JSONB, nullable=True)
    """
    Additional JSON data.
    - Can store: shop_id, order_id, collection_id, transfer_notes, etc.
    - Flexible structure for future needs
    - Column name in database is 'metadata', but Python attribute is 'transaction_metadata' to avoid SQLAlchemy reserved word conflict
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when transaction was created.
    - Auto-set by database
    - Used for transaction history and reporting
    """

    # Constraints
    __table_args__ = (
        {'extend_existing': True}
    )

