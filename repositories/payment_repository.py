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
    def create(db: Session, shop_id: int, collected_by_order_booker: int,
              approved_by_distributor: int, amount: Decimal,
              daily_collection_id: int = None, collected_at: datetime = None,
              remarks: str = None) -> Payment:
        """
        Create a new payment record.
        
        Args:
            db: Database session
            shop_id: Shop ID where payment was collected
            collected_by_order_booker: Order booker ID who collected
            approved_by_distributor: Distributor ID who approved
            amount: Payment amount
            daily_collection_id: Optional daily collection ID this payment came from
            collected_at: Timestamp when payment was collected
            remarks: Optional remarks
        
        Returns:
            Created payment instance
        """
        payment = Payment(
            shop_id=shop_id,
            daily_collection_id=daily_collection_id,
            collected_by_order_booker=collected_by_order_booker,
            approved_by_distributor=approved_by_distributor,
            amount=amount,
            collected_at=collected_at or datetime.utcnow(),
            remarks=remarks
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
        ).order_by(Payment.created_at.desc()).all()
    
    @staticmethod
    def get_by_order_booker(db: Session, order_booker_id: int) -> List[Payment]:
        """Get all payments collected by an order booker."""
        return db.query(Payment).filter(
            Payment.collected_by_order_booker == order_booker_id
        ).order_by(Payment.created_at.desc()).all()
    
    @staticmethod
    def get_by_distributor(db: Session, distributor_id: int) -> List[Payment]:
        """Get all payments approved by a distributor."""
        return db.query(Payment).filter(
            Payment.approved_by_distributor == distributor_id
        ).order_by(Payment.created_at.desc()).all()




