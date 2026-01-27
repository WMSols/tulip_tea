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
    def _validate_order_booker_zone_match(db: Session, route_zone_id: int, order_booker_id: int) -> None:
        """
        Validate that an order booker's zone matches the route's zone.
        
        Args:
            db: Database session
            route_zone_id: Zone ID of the route
            order_booker_id: ID of the order booker to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Verify order booker exists
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        # Validate zone matching: order booker's zone must match route's zone
        if route_zone_id and order_booker.zone_id:
            if route_zone_id != order_booker.zone_id:
                raise ValueError(
                    f"Cannot assign route: Route belongs to zone {route_zone_id}, "
                    f"but order booker is assigned to zone {order_booker.zone_id}. "
                    f"They must be in the same zone."
                )
        elif route_zone_id and not order_booker.zone_id:
            raise ValueError(
                f"Cannot assign route: Route belongs to zone {route_zone_id}, "
                f"but order booker has no zone assigned. "
                f"Please assign the order booker to zone {route_zone_id} first."
            )
        elif not route_zone_id and order_booker.zone_id:
            raise ValueError(
                f"Cannot assign route: Route has no zone assigned, "
                f"but order booker is assigned to zone {order_booker.zone_id}. "
                f"Please assign the route to a zone first."
            )
        # If both are None, allow assignment (though this is unusual)
    
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
        
        # Validate order booker zone match if order_booker_id is provided
        if order_booker_id is not None:
            RouteService._validate_order_booker_zone_match(db, zone_id, order_booker_id)
        
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
        
        DEPRECATED: Use update_route with order_booker_id instead.
        This method is kept for backward compatibility.
        
        Validates that the order booker's zone matches the route's zone.
        """
        # Verify route exists
        route = RouteRepository.get_by_id(db, route_id)
        if not route:
            raise ValueError("Route not found")
        
        # Validate zone matching using shared helper
        if route.zone_id:
            RouteService._validate_order_booker_zone_match(db, route.zone_id, order_booker_id)
        else:
            # If route has no zone, still validate order booker exists
            order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
            if not order_booker:
                raise ValueError("Order Booker not found")
        
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
    def update_route(db: Session, route_id: int, name: str = None, 
                    zone_id: int = None, order_booker_id: int = None, 
                    update_order_booker: bool = False, update_zone: bool = False) -> Dict:
        """
        Update route name, zone, and/or order booker assignment.
        
        Args:
            db: Database session
            route_id: ID of route to update
            name: Optional new name for the route (None means don't update name)
            zone_id: Optional new zone ID for the route
            order_booker_id: Order booker ID to assign (can be None to unassign)
            update_order_booker: If True, update order_booker_id (even if None to unassign)
            update_zone: If True, update zone_id
        
        Returns:
            Updated route dictionary
        """
        # Check if route exists
        route = RouteRepository.get_by_id(db, route_id)
        if not route:
            raise ValueError("Route not found")
        
        # Check if at least one field is being updated
        if name is None and not update_order_booker and not update_zone:
            raise ValueError("At least one field (name, zone_id, or order_booker_id) must be provided for update")
        
        # Validate zone exists if updating zone
        if update_zone and zone_id is not None:
            zone = ZoneRepository.get_by_id(db, zone_id)
            if not zone:
                raise ValueError("Zone not found")
        
        # If zone is being updated, we need to check order booker compatibility
        # If route has an assigned order booker, validate it's in the new zone
        final_zone_id = zone_id if update_zone else route.zone_id
        
        # Validate order booker zone match if assigning (order_booker_id is not None)
        if update_order_booker and order_booker_id is not None:
            if final_zone_id:
                RouteService._validate_order_booker_zone_match(db, final_zone_id, order_booker_id)
            else:
                # If route has no zone, still validate order booker exists
                order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
                if not order_booker:
                    raise ValueError("Order Booker not found")
        elif update_zone and route.order_booker_id:
            # If zone is being updated and route has an assigned order booker,
            # validate that the order booker is in the new zone
            if final_zone_id:
                RouteService._validate_order_booker_zone_match(db, final_zone_id, route.order_booker_id)
            else:
                # If zone is being set to None, we should unassign the order booker
                # as order bookers must be in a zone
                RouteRepository.assign_to_order_booker(db, route_id, None)
        
        # Update route name and/or zone if provided
        if name is not None or update_zone:
            updated_route = RouteRepository.update(db, route_id, name=name, zone_id=zone_id if update_zone else None)
            if not updated_route:
                raise ValueError("Failed to update route")
            # Refresh to get latest data
            route = RouteRepository.get_by_id(db, route_id)
        
        # Update order booker assignment if update_order_booker is True
        if update_order_booker:
            success = RouteRepository.assign_to_order_booker(db, route_id, order_booker_id)
            if not success:
                raise ValueError("Failed to update route order booker assignment")
            # Refresh to get latest data
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
    def delete_route(db: Session, route_id: int) -> bool:
        """Delete a route."""
        route = RouteRepository.get_by_id(db, route_id)
        if not route:
            raise ValueError("Route not found")
        
        return RouteRepository.delete(db, route_id)

