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
              password_hash: str) -> DeliveryMan:
        """Create a new delivery man."""
        delivery_man = DeliveryMan(
            distributor_id=distributor_id,
            name=name,
            phone=phone,
            password_hash=password_hash
        )
        db.add(delivery_man)
        db.commit()
        db.refresh(delivery_man)
        return delivery_man
    
    @staticmethod
    def get_by_id(db: Session, delivery_man_id: int) -> Optional[DeliveryMan]:
        """Get delivery man by ID."""
        return db.query(DeliveryMan).filter(DeliveryMan.id == delivery_man_id).first()
    
    @staticmethod
    def get_by_phone(db: Session, phone: str) -> Optional[DeliveryMan]:
        """Get delivery man by phone number."""
        return db.query(DeliveryMan).filter(DeliveryMan.phone == phone).first()
    
    @staticmethod
    def get_by_distributor(db: Session, distributor_id: int,
                          skip: int = 0, limit: int = 100) -> List[DeliveryMan]:
        """Get all delivery men for a distributor."""
        return db.query(DeliveryMan).filter(
            DeliveryMan.distributor_id == distributor_id
        ).offset(skip).limit(limit).all()

