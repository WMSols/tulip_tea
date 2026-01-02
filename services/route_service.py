"""
Route business logic service.
"""
from sqlalchemy.orm import Session
from repositories.route_repository import RouteRepository
from repositories.distributor_repository import DistributorRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.zone_repository import ZoneRepository
from typing import Dict, List


class RouteService:
    """Service for Route business logic."""
    
    @staticmethod
    def create_route(db: Session, name: str, 
                    distributor_id: int, zone_id: int,
                    order_booker_id: int = None) -> Dict:
        """Create a new route."""
        # Verify distributor exists
        distributor = DistributorRepository.get_by_id(db, distributor_id)
        if not distributor:
            raise ValueError("Distributor not found")
        
        # Verify zone exists
        zone = ZoneRepository.get_by_id(db, zone_id)
        if not zone:
            raise ValueError("Zone not found")
        
        route = RouteRepository.create(
            db=db,
            name=name,
            created_by_distributor=distributor_id,
            zone_id=zone_id,
            order_booker_id=order_booker_id
        )
        
        return {
            "id": route.id,
            "name": route.name,
            "zone_id": route.zone_id,
            "order_booker_id": route.order_booker_id,
            "created_by_distributor": route.created_by_distributor,
            "created_at": route.created_at.isoformat() if route.created_at else None
        }
    
    @staticmethod
    def get_routes_by_distributor(db: Session, distributor_id: int) -> List[Dict]:
        """Get all routes created by a distributor."""
        routes = RouteRepository.get_by_distributor(db, distributor_id)
        return [
            {
                "id": route.id,
                "name": route.name,
                "zone_id": route.zone_id,
                "order_booker_id": route.order_booker_id,
                "created_by_distributor": route.created_by_distributor,
                "created_at": route.created_at.isoformat() if route.created_at else None
            }
            for route in routes
        ]
    
    @staticmethod
    def get_routes_by_zone(db: Session, zone_id: int) -> List[Dict]:
        """Get all routes in a zone."""
        routes = RouteRepository.get_by_zone(db, zone_id)
        return [
            {
                "id": route.id,
                "name": route.name,
                "zone_id": route.zone_id,
                "order_booker_id": route.order_booker_id,
                "created_by_distributor": route.created_by_distributor,
                "created_at": route.created_at.isoformat() if route.created_at else None
            }
            for route in routes
        ]
    
    @staticmethod
    def assign_route_to_order_booker(db: Session, route_id: int, order_booker_id: int) -> Dict:
        """Assign a route to an order booker."""
        # Verify order booker exists
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        success = RouteRepository.assign_to_order_booker(db, route_id, order_booker_id)
        if not success:
            raise ValueError("Route not found")
        
        route = RouteRepository.get_by_id(db, route_id)
        return {
            "id": route.id,
            "name": route.name,
            "zone_id": route.zone_id,
            "order_booker_id": route.order_booker_id,
            "created_by_distributor": route.created_by_distributor,
            "created_at": route.created_at.isoformat() if route.created_at else None
        }
    
    @staticmethod
    def get_routes_by_order_booker(db: Session, order_booker_id: int) -> List[Dict]:
        """Get all routes assigned to an order booker."""
        routes = RouteRepository.get_by_order_booker(db, order_booker_id)
        return [
            {
                "id": route.id,
                "name": route.name,
                "zone_id": route.zone_id,
                "order_booker_id": route.order_booker_id,
                "created_by_distributor": route.created_by_distributor,
                "created_at": route.created_at.isoformat() if route.created_at else None
            }
            for route in routes
        ]
    
    @staticmethod
    def delete_route(db: Session, route_id: int) -> bool:
        """Delete a route."""
        route = RouteRepository.get_by_id(db, route_id)
        if not route:
            raise ValueError("Route not found")
        
        return RouteRepository.delete(db, route_id)

