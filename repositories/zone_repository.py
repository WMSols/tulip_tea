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
    def get_by_ids(db: Session, zone_ids: List[int], include_deleted: bool = False) -> List[Zone]:
        """
        Batch load multiple zones by IDs (optimized to avoid N+1 queries).
        
        Args:
            db: Database session
            zone_ids: List of zone IDs to fetch
            include_deleted: If True, includes soft-deleted and inactive records
        
        Returns:
            List of zones
        """
        if not zone_ids:
            return []
        
        query = db.query(Zone).filter(Zone.id.in_(zone_ids))
        if not include_deleted:
            query = query.filter(Zone.deleted_at.is_(None), Zone.is_active == True)
        return query.all()
    
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
        """Soft delete a zone (sets deleted_at timestamp and is_active=False)."""
        from datetime import datetime
        zone = db.query(Zone).filter(
            Zone.id == zone_id,
            Zone.deleted_at.is_(None)
        ).first()
        if not zone:
            return False
        zone.deleted_at = datetime.utcnow()
        zone.is_active = False
        db.commit()
        db.refresh(zone)
        return True



