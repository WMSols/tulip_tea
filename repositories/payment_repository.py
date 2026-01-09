"""
Payment Repository
==================
Data access layer for Payment operations.
"""
from sqlalchemy.orm import Session
from models.payment import Payment
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class PaymentRepository:
    """Repository for Payment database operations."""
    
    @staticmethod
    def create(db: Session, shop_id: int, amount: Decimal,
              order_id: int = None, received_by_distributor: int = None,
              payment_date: datetime = None) -> Payment:
        """
        Create a new payment record.
        
        Note: Payments are created when distributors verify daily collections.
        The daily_collection table has the details about who collected and who approved.
        
        Args:
            db: Database session
            shop_id: Shop ID where payment was collected
            amount: Payment amount
            order_id: Optional order ID this payment is for
            received_by_distributor: Optional distributor ID who received the payment
            payment_date: Optional timestamp when payment was received
        
        Returns:
            Created payment instance
        """
        payment = Payment(
            shop_id=shop_id,
            amount=amount,
            order_id=order_id,
            received_by_distributor=received_by_distributor,
            payment_date=payment_date or datetime.utcnow()
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment
    
    @staticmethod
    def get_by_id(db: Session, payment_id: int) -> Optional[Payment]:
        """Get payment by ID."""
        return db.query(Payment).filter(Payment.id == payment_id).first()
    
    @staticmethod
    def get_by_shop(db: Session, shop_id: int) -> List[Payment]:
        """Get all payments for a shop."""
        return db.query(Payment).filter(
            Payment.shop_id == shop_id
        ).order_by(Payment.payment_date.desc() if Payment.payment_date else Payment.id.desc()).all()
    
    # Note: get_by_order_booker and get_by_distributor removed
    # Payment table doesn't have these columns. Use daily_collections table instead
    # to track who collected and who approved.





