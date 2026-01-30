"""
Route repository.
Data access layer for Route operations.
"""
from sqlalchemy.orm import Session
from models.route import Route
from models.zone import Zone
from typing import Optional, List


class RouteRepository:
    """Repository for Route database operations."""
    
    @staticmethod
    def create(db: Session, name: str, 
              created_by_distributor: int, zone_id: int,
              order_booker_id: int = None) -> Route:
        """Create a new route."""
        route = Route(
            name=name,
            created_by_distributor=created_by_distributor,
            zone_id=zone_id,
            order_booker_id=order_booker_id
        )
        db.add(route)
        db.commit()
        db.refresh(route)
        return route
    
    @staticmethod
    def get_by_id(db: Session, route_id: int, include_deleted: bool = False) -> Optional[Route]:
        """Get route by ID (excludes soft-deleted and inactive by default)."""
        query = db.query(Route).outerjoin(Zone, Route.zone_id == Zone.id).filter(Route.id == route_id)
        if not include_deleted:
            query = query.filter(
                Route.deleted_at.is_(None), 
                Route.is_active == True
            ).filter(
                # Zone must be active (or NULL if route has no zone)
                (Route.zone_id.is_(None)) | 
                ((Zone.deleted_at.is_(None)) & (Zone.is_active == True))
            )
        return query.first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, include_deleted: bool = False) -> List[Route]:
        """Get all routes with pagination (excludes soft-deleted and inactive by default)."""
        query = db.query(Route).outerjoin(Zone, Route.zone_id == Zone.id)
        if not include_deleted:
            query = query.filter(
                Route.deleted_at.is_(None), 
                Route.is_active == True
            ).filter(
                # Zone must be active (or NULL if route has no zone)
                (Route.zone_id.is_(None)) | 
                ((Zone.deleted_at.is_(None)) & (Zone.is_active == True))
            )
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_zone(db: Session, zone_id: int, include_deleted: bool = False) -> List[Route]:
        """Get all routes for a zone (excludes soft-deleted and inactive by default)."""
        query = db.query(Route).join(Zone, Route.zone_id == Zone.id).filter(Route.zone_id == zone_id)
        if not include_deleted:
            query = query.filter(
                Route.deleted_at.is_(None), 
                Route.is_active == True,
                Zone.deleted_at.is_(None),
                Zone.is_active == True
            )
        return query.all()
    
    @staticmethod
    def get_by_distributor(db: Session, distributor_id: int, include_deleted: bool = False) -> List[Route]:
        """Get all routes created by a distributor (excludes soft-deleted and inactive by default)."""
        query = db.query(Route).outerjoin(Zone, Route.zone_id == Zone.id).filter(Route.created_by_distributor == distributor_id)
        if not include_deleted:
            query = query.filter(
                Route.deleted_at.is_(None), 
                Route.is_active == True
            ).filter(
                # Zone must be active (or NULL if route has no zone)
                (Route.zone_id.is_(None)) | 
                ((Zone.deleted_at.is_(None)) & (Zone.is_active == True))
            )
        return query.all()
    
    @staticmethod
    def get_by_order_booker(db: Session, order_booker_id: int, include_deleted: bool = False) -> List[Route]:
        """Get all routes assigned to an order booker (excludes soft-deleted and inactive by default)."""
        query = db.query(Route).outerjoin(Zone, Route.zone_id == Zone.id).filter(Route.order_booker_id == order_booker_id)
        if not include_deleted:
            query = query.filter(
                Route.deleted_at.is_(None), 
                Route.is_active == True
            ).filter(
                # Zone must be active (or NULL if route has no zone)
                (Route.zone_id.is_(None)) | 
                ((Zone.deleted_at.is_(None)) & (Zone.is_active == True))
            )
        return query.all()
    
    @staticmethod
    def assign_to_order_booker(db: Session, route_id: int, order_booker_id: int = None) -> bool:
        """
        Assign or unassign a route to/from an order booker.
        
        Args:
            db: Database session
            route_id: Route ID
            order_booker_id: Order booker ID to assign, or None to unassign
        
        Returns:
            True if successful, False if route not found
        """
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route:
            return False
        route.order_booker_id = order_booker_id
        db.commit()
        db.refresh(route)
        return True
    
    @staticmethod
    def update(db: Session, route_id: int, name: str = None, zone_id: int = None) -> Optional[Route]:
        """
        Update route name and/or zone.
        
        Args:
            db: Database session
            route_id: Route ID
            name: Optional new name for the route
            zone_id: Optional new zone ID for the route
        
        Returns:
            Updated Route object, or None if route not found
        """
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route:
            return None
        
        if name is not None:
            route.name = name
        if zone_id is not None:
            route.zone_id = zone_id
        
        db.commit()
        db.refresh(route)
        return route
    
    @staticmethod
    def delete(db: Session, route_id: int) -> bool:
        """Soft delete a route (sets deleted_at timestamp and is_active=False)."""
        from datetime import datetime
        route = db.query(Route).filter(
            Route.id == route_id,
            Route.deleted_at.is_(None)
        ).first()
        if not route:
            return False
        route.deleted_at = datetime.utcnow()
        route.is_active = False
        db.commit()
        db.refresh(route)
        return True

