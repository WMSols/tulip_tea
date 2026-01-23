"""
Route repository.
Data access layer for Route operations.
"""
from sqlalchemy.orm import Session
from models.route import Route
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
        query = db.query(Route).filter(Route.id == route_id)
        if not include_deleted:
            query = query.filter(Route.deleted_at.is_(None), Route.is_active == True)
        return query.first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, include_deleted: bool = False) -> List[Route]:
        """Get all routes with pagination (excludes soft-deleted and inactive by default)."""
        query = db.query(Route)
        if not include_deleted:
            query = query.filter(Route.deleted_at.is_(None), Route.is_active == True)
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_zone(db: Session, zone_id: int, include_deleted: bool = False) -> List[Route]:
        """Get all routes for a zone (excludes soft-deleted and inactive by default)."""
        query = db.query(Route).filter(Route.zone_id == zone_id)
        if not include_deleted:
            query = query.filter(Route.deleted_at.is_(None), Route.is_active == True)
        return query.all()
    
    @staticmethod
    def get_by_distributor(db: Session, distributor_id: int, include_deleted: bool = False) -> List[Route]:
        """Get all routes created by a distributor (excludes soft-deleted and inactive by default)."""
        query = db.query(Route).filter(Route.created_by_distributor == distributor_id)
        if not include_deleted:
            query = query.filter(Route.deleted_at.is_(None), Route.is_active == True)
        return query.all()
    
    @staticmethod
    def get_by_order_booker(db: Session, order_booker_id: int, include_deleted: bool = False) -> List[Route]:
        """Get all routes assigned to an order booker (excludes soft-deleted and inactive by default)."""
        query = db.query(Route).filter(Route.order_booker_id == order_booker_id)
        if not include_deleted:
            query = query.filter(Route.deleted_at.is_(None), Route.is_active == True)
        return query.all()
    
    @staticmethod
    def assign_to_order_booker(db: Session, route_id: int, order_booker_id: int) -> bool:
        """Assign a route to an order booker."""
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route:
            return False
        route.order_booker_id = order_booker_id
        db.commit()
        db.refresh(route)
        return True
    
    @staticmethod
    def update(db: Session, route_id: int, name: str) -> Optional[Route]:
        """Update route name."""
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route:
            return None
        route.name = name
        db.commit()
        db.refresh(route)
        return route
    
    @staticmethod
    def delete(db: Session, route_id: int) -> bool:
        """Delete a route."""
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route:
            return False
        db.delete(route)
        db.commit()
        return True

