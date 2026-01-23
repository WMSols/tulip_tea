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
    def get_by_id(db: Session, zone_id: int, include_deleted: bool = False) -> Optional[Zone]:
        """Get zone by ID (excludes soft-deleted and inactive by default)."""
        query = db.query(Zone).filter(Zone.id == zone_id)
        if not include_deleted:
            query = query.filter(Zone.deleted_at.is_(None), Zone.is_active == True)
        return query.first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, include_deleted: bool = False) -> List[Zone]:
        """Get all zones with pagination (excludes soft-deleted and inactive by default)."""
        query = db.query(Zone)
        if not include_deleted:
            query = query.filter(Zone.deleted_at.is_(None), Zone.is_active == True)
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Zone]:
        """Get zone by name."""
        return db.query(Zone).filter(Zone.name == name).first()
    
    @staticmethod
    def update(db: Session, zone_id: int, name: str) -> Optional[Zone]:
        """Update zone name."""
        zone = db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return None
        zone.name = name
        db.commit()
        db.refresh(zone)
        return zone
    
    @staticmethod
    def delete(db: Session, zone_id: int) -> bool:
        """Delete a zone."""
        zone = db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return False
        db.delete(zone)
        db.commit()
        return True



