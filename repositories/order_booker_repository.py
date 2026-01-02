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
              password_hash: str, email: str = None, zone_id: int = None) -> OrderBooker:
        """Create a new order booker."""
        order_booker = OrderBooker(
            distributor_id=distributor_id,
            name=name,
            email=email,
            phone=phone,
            password_hash=password_hash,
            zone_id=zone_id
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
    
    @staticmethod
    def update(db: Session, order_booker_id: int, name: str = None, 
              phone: str = None, email: str = None, zone_id: int = None,
              password_hash: str = None) -> Optional[OrderBooker]:
        """Update an order booker."""
        order_booker = db.query(OrderBooker).filter(OrderBooker.id == order_booker_id).first()
        if not order_booker:
            return None
        
        if name is not None:
            order_booker.name = name
        if phone is not None:
            order_booker.phone = phone
        if email is not None:
            order_booker.email = email
        if zone_id is not None:
            order_booker.zone_id = zone_id
        if password_hash is not None:
            order_booker.password_hash = password_hash
        
        db.commit()
        db.refresh(order_booker)
        return order_booker
    
    @staticmethod
    def delete(db: Session, order_booker_id: int) -> bool:
        """Delete an order booker."""
        order_booker = db.query(OrderBooker).filter(OrderBooker.id == order_booker_id).first()
        if not order_booker:
            return False
        db.delete(order_booker)
        db.commit()
        return True

