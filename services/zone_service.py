"""
Zone business logic service.
"""
from sqlalchemy.orm import Session
from repositories.zone_repository import ZoneRepository
from typing import Dict, List


class ZoneService:
    """Service for Zone business logic."""
    
    @staticmethod
    def create_zone(db: Session, name: str) -> Dict:
        """Create a new zone."""
        # Check if zone with same name exists
        existing = ZoneRepository.get_by_name(db, name)
        if existing:
            raise ValueError("Zone with this name already exists")
        
        zone = ZoneRepository.create(db=db, name=name)
        
        return {
            "id": zone.id,
            "name": zone.name,
            "created_at": zone.created_at.isoformat() if zone.created_at else None
        }
    
    @staticmethod
    def get_all_zones(db: Session) -> List[Dict]:
        """Get all zones."""
        zones = ZoneRepository.get_all(db)
        return [
            {
                "id": zone.id,
                "name": zone.name,
                "created_at": zone.created_at.isoformat() if zone.created_at else None
            }
            for zone in zones
        ]
    
    @staticmethod
    def get_zone_by_id(db: Session, zone_id: int) -> Dict:
        """Get zone by ID."""
        zone = ZoneRepository.get_by_id(db, zone_id)
        if not zone:
            raise ValueError("Zone not found")
        
        return {
            "id": zone.id,
            "name": zone.name,
            "created_at": zone.created_at.isoformat() if zone.created_at else None
        }
    
    @staticmethod
    def update_zone(db: Session, zone_id: int, name: str) -> Dict:
        """Update zone name."""
        # Check if zone exists
        zone = ZoneRepository.get_by_id(db, zone_id)
        if not zone:
            raise ValueError("Zone not found")
        
        # Check if another zone with the same name exists (excluding current zone)
        existing = ZoneRepository.get_by_name(db, name)
        if existing and existing.id != zone_id:
            raise ValueError("Zone with this name already exists")
        
        updated_zone = ZoneRepository.update(db, zone_id, name)
        if not updated_zone:
            raise ValueError("Failed to update zone")
        
        return {
            "id": updated_zone.id,
            "name": updated_zone.name,
            "created_at": updated_zone.created_at.isoformat() if updated_zone.created_at else None
        }
    
    @staticmethod
    def delete_zone(db: Session, zone_id: int) -> bool:
        """Delete a zone."""
        zone = ZoneRepository.get_by_id(db, zone_id)
        if not zone:
            raise ValueError("Zone not found")
        
        return ZoneRepository.delete(db, zone_id)



