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
        """
        Assign a route to an order booker.
        
        Validates that the order booker's zone matches the route's zone.
        """
        # Verify route exists
        route = RouteRepository.get_by_id(db, route_id)
        if not route:
            raise ValueError("Route not found")
        
        # Verify order booker exists
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        # Validate zone matching: order booker's zone must match route's zone
        if route.zone_id and order_booker.zone_id:
            if route.zone_id != order_booker.zone_id:
                raise ValueError(
                    f"Cannot assign route: Route belongs to zone {route.zone_id}, "
                    f"but order booker is assigned to zone {order_booker.zone_id}. "
                    f"They must be in the same zone."
                )
        elif route.zone_id and not order_booker.zone_id:
            raise ValueError(
                f"Cannot assign route: Route belongs to zone {route.zone_id}, "
                f"but order booker has no zone assigned. "
                f"Please assign the order booker to zone {route.zone_id} first."
            )
        elif not route.zone_id and order_booker.zone_id:
            raise ValueError(
                f"Cannot assign route: Route has no zone assigned, "
                f"but order booker is assigned to zone {order_booker.zone_id}. "
                f"Please assign the route to a zone first."
            )
        # If both are None, allow assignment (though this is unusual)
        
        success = RouteRepository.assign_to_order_booker(db, route_id, order_booker_id)
        if not success:
            raise ValueError("Failed to assign route")
        
        # Refresh route to get updated order_booker_id
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
    def update_route(db: Session, route_id: int, name: str) -> Dict:
        """Update route name."""
        # Check if route exists
        route = RouteRepository.get_by_id(db, route_id)
        if not route:
            raise ValueError("Route not found")
        
        updated_route = RouteRepository.update(db, route_id, name)
        if not updated_route:
            raise ValueError("Failed to update route")
        
        return {
            "id": updated_route.id,
            "name": updated_route.name,
            "zone_id": updated_route.zone_id,
            "order_booker_id": updated_route.order_booker_id,
            "created_by_distributor": updated_route.created_by_distributor,
            "created_at": updated_route.created_at.isoformat() if updated_route.created_at else None
        }
    
    @staticmethod
    def delete_route(db: Session, route_id: int) -> bool:
        """Delete a route."""
        route = RouteRepository.get_by_id(db, route_id)
        if not route:
            raise ValueError("Route not found")
        
        return RouteRepository.delete(db, route_id)

