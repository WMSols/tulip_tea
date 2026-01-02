"""
Order Booker repository.
Data access layer for Order Booker operations.
"""
from sqlalchemy.orm import Session
from models.order_booker import OrderBooker
from typing import Optional, List


class OrderBookerRepository:
    """Repository for Order Booker database operations."""
    
    @staticmethod
    def create(db: Session, distributor_id: int, name: str, phone: str,
              assigned_zone: str, password_hash: str, email: str = None) -> OrderBooker:
        """Create a new order booker."""
        order_booker = OrderBooker(
            distributor_id=distributor_id,
            name=name,
            email=email,
            phone=phone,
            assigned_zone=assigned_zone,
            password_hash=password_hash
        )
        db.add(order_booker)
        db.commit()
        db.refresh(order_booker)
        return order_booker
    
    @staticmethod
    def get_by_id(db: Session, order_booker_id: int) -> Optional[OrderBooker]:
        """Get order booker by ID."""
        return db.query(OrderBooker).filter(OrderBooker.id == order_booker_id).first()
    
    @staticmethod
    def get_by_phone(db: Session, phone: str) -> Optional[OrderBooker]:
        """Get order booker by phone number."""
        return db.query(OrderBooker).filter(OrderBooker.phone == phone).first()
    
    @staticmethod
    def get_by_distributor(db: Session, distributor_id: int, 
                          skip: int = 0, limit: int = 100) -> List[OrderBooker]:
        """Get all order bookers for a distributor."""
        return db.query(OrderBooker).filter(
            OrderBooker.distributor_id == distributor_id
        ).offset(skip).limit(limit).all()

