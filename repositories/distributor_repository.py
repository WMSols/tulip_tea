"""
Distributor repository.
Data access layer for Distributor operations.
"""
from sqlalchemy.orm import Session
from models.distributor import Distributor
from typing import Optional, List


class DistributorRepository:
    """Repository for Distributor database operations."""
    
    @staticmethod
    def create(db: Session, name: str, email: str, phone: str, 
              password_hash: str, zone_id: int = None) -> Distributor:
        """Create a new distributor."""
        distributor = Distributor(
            name=name,
            email=email,
            phone=phone,
            password_hash=password_hash,
            zone_id=zone_id
        )
        db.add(distributor)
        db.commit()
        db.refresh(distributor)
        return distributor
    
    @staticmethod
    def get_by_id(db: Session, distributor_id: int) -> Optional[Distributor]:
        """Get distributor by ID."""
        return db.query(Distributor).filter(Distributor.id == distributor_id).first()
    
    @staticmethod
    def get_by_phone(db: Session, phone: str) -> Optional[Distributor]:
        """Get distributor by phone number."""
        return db.query(Distributor).filter(Distributor.phone == phone).first()
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[Distributor]:
        """Get distributor by email."""
        return db.query(Distributor).filter(Distributor.email == email).first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Distributor]:
        """Get all distributors with pagination."""
        return db.query(Distributor).offset(skip).limit(limit).all()

