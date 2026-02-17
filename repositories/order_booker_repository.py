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
    def get_by_id(db: Session, order_booker_id: int, include_deleted: bool = False) -> Optional[OrderBooker]:
        """Get order booker by ID (excludes soft-deleted and inactive by default)."""
        query = db.query(OrderBooker).filter(OrderBooker.id == order_booker_id)
        if not include_deleted:
            query = query.filter(OrderBooker.deleted_at.is_(None), OrderBooker.is_active == True)
        return query.first()
    
    @staticmethod
    def get_by_ids(db: Session, order_booker_ids: List[int], include_deleted: bool = False) -> List[OrderBooker]:
        """
        Batch load multiple order bookers by IDs (optimized to avoid N+1 queries).
        
        Args:
            db: Database session
            order_booker_ids: List of order booker IDs to fetch
            include_deleted: If True, includes soft-deleted and inactive records
        
        Returns:
            List of order bookers
        """
        if not order_booker_ids:
            return []
        
        query = db.query(OrderBooker).filter(OrderBooker.id.in_(order_booker_ids))
        if not include_deleted:
            query = query.filter(OrderBooker.deleted_at.is_(None), OrderBooker.is_active == True)
        return query.all()
    
    @staticmethod
    def get_by_phone(db: Session, phone: str, include_deleted: bool = False) -> Optional[OrderBooker]:
        """Get order booker by phone number (excludes soft-deleted and inactive by default)."""
        query = db.query(OrderBooker).filter(OrderBooker.phone == phone)
        if not include_deleted:
            query = query.filter(OrderBooker.deleted_at.is_(None), OrderBooker.is_active == True)
        return query.first()
    
    @staticmethod
    def get_by_distributor(db: Session, distributor_id: int, 
                          skip: int = 0, limit: int = 100, include_deleted: bool = False) -> List[OrderBooker]:
        """Get all order bookers for a distributor (excludes soft-deleted and inactive by default)."""
        query = db.query(OrderBooker).filter(OrderBooker.distributor_id == distributor_id)
        if not include_deleted:
            query = query.filter(OrderBooker.deleted_at.is_(None), OrderBooker.is_active == True)
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_zone(db: Session, zone_id: int, distributor_id: int = None, include_deleted: bool = False) -> List[OrderBooker]:
        """
        Get all order bookers assigned to a specific zone (excludes soft-deleted and inactive by default).
        
        Args:
            db: Database session
            zone_id: Zone ID to filter by
            distributor_id: Optional distributor ID to further filter
            include_deleted: If True, includes soft-deleted and inactive records
        
        Returns:
            List of order bookers in the specified zone
        """
        query = db.query(OrderBooker).filter(OrderBooker.zone_id == zone_id)
        if distributor_id:
            query = query.filter(OrderBooker.distributor_id == distributor_id)
        if not include_deleted:
            query = query.filter(OrderBooker.deleted_at.is_(None), OrderBooker.is_active == True)
        return query.all()
    
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
        """Soft delete an order booker (sets deleted_at timestamp)."""
        from datetime import datetime
        order_booker = db.query(OrderBooker).filter(
            OrderBooker.id == order_booker_id,
            OrderBooker.deleted_at.is_(None)
        ).first()
        if not order_booker:
            return False
        order_booker.deleted_at = datetime.utcnow()
        order_booker.is_active = False  # Also deactivate when soft deleting
        db.commit()
        db.refresh(order_booker)
        return True

