"""
Delivery Man repository.
Data access layer for Delivery Man operations.
"""
from sqlalchemy.orm import Session
from models.delivery_man import DeliveryMan
from typing import Optional, List


class DeliveryManRepository:
    """Repository for Delivery Man database operations."""
    
    @staticmethod
    def create(db: Session, distributor_id: int, name: str, phone: str,
              password_hash: str, zone_id: int = None) -> DeliveryMan:
        """Create a new delivery man."""
        delivery_man = DeliveryMan(
            distributor_id=distributor_id,
            name=name,
            phone=phone,
            password_hash=password_hash,
            zone_id=zone_id
        )
        db.add(delivery_man)
        db.commit()
        db.refresh(delivery_man)
        return delivery_man
    
    @staticmethod
    def get_by_id(db: Session, delivery_man_id: int, include_deleted: bool = False) -> Optional[DeliveryMan]:
        """Get delivery man by ID (excludes soft-deleted and inactive by default)."""
        query = db.query(DeliveryMan).filter(DeliveryMan.id == delivery_man_id)
        if not include_deleted:
            query = query.filter(DeliveryMan.deleted_at.is_(None), DeliveryMan.is_active == True)
        return query.first()
    
    @staticmethod
    def get_by_phone(db: Session, phone: str, include_deleted: bool = False) -> Optional[DeliveryMan]:
        """Get delivery man by phone number (excludes soft-deleted and inactive by default)."""
        query = db.query(DeliveryMan).filter(DeliveryMan.phone == phone)
        if not include_deleted:
            query = query.filter(DeliveryMan.deleted_at.is_(None), DeliveryMan.is_active == True)
        return query.first()
    
    @staticmethod
    def get_by_distributor(db: Session, distributor_id: int,
                          skip: int = 0, limit: int = 100, include_deleted: bool = False) -> List[DeliveryMan]:
        """Get all delivery men for a distributor (excludes soft-deleted and inactive by default)."""
        query = db.query(DeliveryMan).filter(DeliveryMan.distributor_id == distributor_id)
        if not include_deleted:
            query = query.filter(DeliveryMan.deleted_at.is_(None), DeliveryMan.is_active == True)
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, delivery_man_id: int, name: str = None,
              phone: str = None, zone_id: int = None,
              password_hash: str = None) -> Optional[DeliveryMan]:
        """Update a delivery man."""
        delivery_man = db.query(DeliveryMan).filter(DeliveryMan.id == delivery_man_id).first()
        if not delivery_man:
            return None
        
        if name is not None:
            delivery_man.name = name
        if phone is not None:
            delivery_man.phone = phone
        if zone_id is not None:
            delivery_man.zone_id = zone_id
        if password_hash is not None:
            delivery_man.password_hash = password_hash
        
        db.commit()
        db.refresh(delivery_man)
        return delivery_man
    
    @staticmethod
    def delete(db: Session, delivery_man_id: int) -> bool:
        """Soft delete a delivery man (sets deleted_at timestamp)."""
        from datetime import datetime
        delivery_man = db.query(DeliveryMan).filter(
            DeliveryMan.id == delivery_man_id,
            DeliveryMan.deleted_at.is_(None)
        ).first()
        if not delivery_man:
            return False
        delivery_man.deleted_at = datetime.utcnow()
        delivery_man.is_active = False  # Also deactivate when soft deleting
        db.commit()
        db.refresh(delivery_man)
        return True

