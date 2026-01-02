"""
Zone repository.
Data access layer for Zone operations.
"""
from sqlalchemy.orm import Session
from models.zone import Zone
from typing import Optional, List


class ZoneRepository:
    """Repository for Zone database operations."""
    
    @staticmethod
    def create(db: Session, name: str) -> Zone:
        """Create a new zone."""
        zone = Zone(name=name)
        db.add(zone)
        db.commit()
        db.refresh(zone)
        return zone
    
    @staticmethod
    def get_by_id(db: Session, zone_id: int) -> Optional[Zone]:
        """Get zone by ID."""
        return db.query(Zone).filter(Zone.id == zone_id).first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Zone]:
        """Get all zones with pagination."""
        return db.query(Zone).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Zone]:
        """Get zone by name."""
        return db.query(Zone).filter(Zone.name == name).first()
    
    @staticmethod
    def delete(db: Session, zone_id: int) -> bool:
        """Delete a zone."""
        zone = db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return False
        db.delete(zone)
        db.commit()
        return True

