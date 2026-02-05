"""
Zone business logic service.
"""
from sqlalchemy.orm import Session
from repositories.zone_repository import ZoneRepository
from repositories.route_repository import RouteRepository
from repositories.shop_repository import ShopRepository
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
        
        # Get counts (will be 0 for new zone)
        routes = RouteRepository.get_by_zone(db, zone.id, include_deleted=False)
        shops = ShopRepository.get_by_zone(db, zone.id, include_deleted=False)
        
        return {
            "id": zone.id,
            "name": zone.name,
            "route_count": len(routes) if routes else 0,
            "shop_count": len(shops) if shops else 0,
            "created_at": zone.created_at.isoformat() if zone.created_at else None
        }
    
    @staticmethod
    def get_all_zones(db: Session) -> List[Dict]:
        """Get all zones."""
        zones = ZoneRepository.get_all(db)
        result = []
        for zone in zones:
            # Get counts for each zone
            routes = RouteRepository.get_by_zone(db, zone.id, include_deleted=False)
            shops = ShopRepository.get_by_zone(db, zone.id, include_deleted=False)
            
            result.append({
                "id": zone.id,
                "name": zone.name,
                "route_count": len(routes) if routes else 0,
                "shop_count": len(shops) if shops else 0,
                "created_at": zone.created_at.isoformat() if zone.created_at else None
            })
        return result
    
    @staticmethod
    def get_zone_by_id(db: Session, zone_id: int) -> Dict:
        """Get zone by ID."""
        zone = ZoneRepository.get_by_id(db, zone_id)
        if not zone:
            raise ValueError("Zone not found")
        
        # Get counts
        routes = RouteRepository.get_by_zone(db, zone.id, include_deleted=False)
        shops = ShopRepository.get_by_zone(db, zone.id, include_deleted=False)
        
        return {
            "id": zone.id,
            "name": zone.name,
            "route_count": len(routes) if routes else 0,
            "shop_count": len(shops) if shops else 0,
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
        
        # Get counts
        routes = RouteRepository.get_by_zone(db, updated_zone.id, include_deleted=False)
        shops = ShopRepository.get_by_zone(db, updated_zone.id, include_deleted=False)
        
        return {
            "id": updated_zone.id,
            "name": updated_zone.name,
            "route_count": len(routes) if routes else 0,
            "shop_count": len(shops) if shops else 0,
            "created_at": updated_zone.created_at.isoformat() if updated_zone.created_at else None
        }
    
    @staticmethod
    def delete_zone(db: Session, zone_id: int) -> bool:
        """Delete a zone."""
        zone = ZoneRepository.get_by_id(db, zone_id)
        if not zone:
            raise ValueError("Zone not found")
        
        return ZoneRepository.delete(db, zone_id)



