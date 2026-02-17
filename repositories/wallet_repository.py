"""
Wallet Repository
=================
Data access layer for Wallet operations.
"""
from sqlalchemy.orm import Session
from models.wallet import Wallet
from models.wallet_transaction import WalletTransaction
from typing import Optional, List
from decimal import Decimal


class WalletRepository:
    """Repository for Wallet database operations."""
    
    @staticmethod
    def create(db: Session, user_type: str, user_id: int) -> Wallet:
        """
        Create a new wallet for a user.
        
        Args:
            db: Database session
            user_type: Type of user ('distributor', 'order_booker', 'delivery_man')
            user_id: ID of the user in their respective table
        
        Returns:
            Created wallet instance
        """
        wallet = Wallet(
            user_type=user_type,
            user_id=user_id,
            current_balance=Decimal('0.00'),
            is_active=True
        )
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
        return wallet
    
    @staticmethod
    def get_by_user(db: Session, user_type: str, user_id: int) -> Optional[Wallet]:
        """
        Get wallet by user type and user ID.
        
        Args:
            db: Database session
            user_type: Type of user ('distributor', 'order_booker', 'delivery_man')
            user_id: ID of the user
        
        Returns:
            Wallet instance or None if not found
        """
        return db.query(Wallet).filter(
            Wallet.user_type == user_type,
            Wallet.user_id == user_id,
            Wallet.deleted_at.is_(None),
            Wallet.is_active == True
        ).first()
    
    @staticmethod
    def get_by_id(db: Session, wallet_id: int) -> Optional[Wallet]:
        """Get wallet by ID."""
        return db.query(Wallet).filter(
            Wallet.id == wallet_id,
            Wallet.deleted_at.is_(None),
            Wallet.is_active == True
        ).first()
    
    @staticmethod
    def update_balance(db: Session, wallet_id: int, new_balance: Decimal) -> Optional[Wallet]:
        """
        Update wallet balance.
        
        Args:
            db: Database session
            wallet_id: Wallet ID
            new_balance: New balance amount
        
        Returns:
            Updated wallet instance or None if not found
        """
        wallet = WalletRepository.get_by_id(db, wallet_id)
        if not wallet:
            return None
        
        wallet.current_balance = new_balance
        db.commit()
        db.refresh(wallet)
        return wallet
    
    @staticmethod
    def create_transaction(
        db: Session,
        wallet_id: int,
        transaction_type: str,
        amount: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        description: str = None,
        reference_type: str = None,
        reference_id: int = None,
        initiated_by_type: str = None,
        initiated_by_id: int = None,
        related_wallet_id: int = None,
        transaction_metadata: dict = None
    ) -> WalletTransaction:
        """
        Create a wallet transaction record.
        
        Args:
            db: Database session
            wallet_id: Wallet ID
            transaction_type: Type of transaction ('credit', 'debit', 'transfer_in', 'transfer_out', 'adjustment')
            amount: Transaction amount (always positive)
            balance_before: Balance before transaction
            balance_after: Balance after transaction
            description: Human-readable description
            reference_type: Type of related entity ('daily_collection', 'order', 'payment', 'transfer', etc.)
            reference_id: ID of related entity
            initiated_by_type: Type of user who initiated ('distributor', 'order_booker', 'delivery_man', 'system')
            initiated_by_id: ID of user who initiated
            related_wallet_id: For transfers, the other wallet involved
            transaction_metadata: Additional JSON data
        
        Returns:
            Created transaction instance
        """
        transaction = WalletTransaction(
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            initiated_by_type=initiated_by_type,
            initiated_by_id=initiated_by_id,
            related_wallet_id=related_wallet_id,
            transaction_metadata=transaction_metadata
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction
    
    @staticmethod
    def get_transactions(db: Session, wallet_id: int, limit: int = 100) -> List[WalletTransaction]:
        """
        Get transaction history for a wallet.
        
        Args:
            db: Database session
            wallet_id: Wallet ID
            limit: Maximum number of transactions to return
        
        Returns:
            List of transactions, ordered by most recent first
        """
        return db.query(WalletTransaction).filter(
            WalletTransaction.wallet_id == wallet_id
        ).order_by(WalletTransaction.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_transactions_by_reference(
        db: Session,
        reference_type: str,
        reference_id: int
    ) -> List[WalletTransaction]:
        """
        Get transactions by reference (e.g., all transactions for a specific collection).
        
        Args:
            db: Database session
            reference_type: Type of reference ('daily_collection', 'order', etc.)
            reference_id: ID of the reference entity
        
        Returns:
            List of transactions
        """
        return db.query(WalletTransaction).filter(
            WalletTransaction.reference_type == reference_type,
            WalletTransaction.reference_id == reference_id
        ).order_by(WalletTransaction.created_at.desc()).all()

