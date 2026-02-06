"""
Wallet Database Model
=====================
SQLAlchemy ORM model for the 'wallets' table.

PURPOSE:
Represents a wallet account for tracking cash collected by distributors,
order bookers, and delivery men. Each user has one wallet.

RELATIONSHIPS:
- Polymorphic relationship: user_type + user_id links to distributors, order_bookers, or delivery_men
- Has many WalletTransactions (via wallet_transactions.wallet_id)

WORKFLOW:
1. Wallet is created when user is created (distributor, order_booker, delivery_man)
2. Money is credited when collections are approved
3. Money can be transferred between wallets
4. All transactions are logged in wallet_transactions table

DATABASE TABLE: wallets
"""
from sqlalchemy import Column, BigInteger, Numeric, String, Boolean, DateTime, CheckConstraint
from sqlalchemy.sql import func
from config.database import Base


class Wallet(Base):
    """
    Wallet table model.
    
    Maps to the 'wallets' table in PostgreSQL.
    Each wallet represents a cash account for a user (distributor, order_booker, or delivery_man).
    """
    __tablename__ = "wallets"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the wallet.
    Auto-incremented by database.
    """

    # Polymorphic relationship to user
    user_type = Column(String(20), nullable=False)
    """
    Type of user this wallet belongs to.
    - Values: 'distributor', 'order_booker', 'delivery_man'
    - Used with user_id to create polymorphic relationship
    """
    
    user_id = Column(BigInteger, nullable=False)
    """
    ID of the user in their respective table.
    - If user_type='distributor', references distributors.id
    - If user_type='order_booker', references order_bookers.id
    - If user_type='delivery_man', references delivery_men.id
    """

    # Wallet balance
    current_balance = Column(Numeric(15, 2), nullable=False, default=0)
    """
    Current available balance in the wallet.
    - Format: Decimal (15 digits, 2 decimal places)
    - Example: 50000.00 (Rs. 50,000)
    - Should match sum of all transactions
    - Cannot be negative (enforced by CHECK constraint)
    """

    # Soft delete and active status
    is_active = Column(Boolean, nullable=False, default=True)
    """
    Whether this wallet is currently active.
    - True: Wallet is active and can receive transactions
    - False: Wallet is inactive
    """
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when wallet was created.
    - Auto-set by database
    """
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """
    Timestamp when wallet was last updated.
    - Auto-updated when balance changes
    """
    
    deleted_at = Column(DateTime, nullable=True)
    """
    Soft delete timestamp.
    - NULL: Wallet is active
    - Not NULL: Wallet is soft-deleted
    """

    # Constraints
    __table_args__ = (
        CheckConstraint('user_type IN (\'distributor\', \'order_booker\', \'delivery_man\')', name='wallets_user_type_check'),
        CheckConstraint('current_balance >= 0', name='wallets_balance_check'),
        {'extend_existing': True}
    )





