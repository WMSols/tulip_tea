"""
Route-Shop Repository
=====================
Data access layer for Route-Shop junction table operations.
"""
from sqlalchemy.orm import Session
from models.route_shop import RouteShop
from typing import Optional, List


class RouteShopRepository:
    """Repository for Route-Shop junction table operations."""
    
    @staticmethod
    def assign_shop_to_route(db: Session, shop_id: int, route_id: int, sequence: int = None) -> RouteShop:
        """
        Assign a shop to a route.
        
        Args:
            db: Database session
            shop_id: Shop ID to assign
            route_id: Route ID to assign to
            sequence: Optional sequence number for visit order
        
        Returns:
            Created RouteShop instance
        """
        # Check if assignment already exists
        existing = db.query(RouteShop).filter(
            RouteShop.shop_id == shop_id,
            RouteShop.route_id == route_id
        ).first()
        
        if existing:
            # Update sequence if provided
            if sequence is not None:
                existing.sequence = sequence
                db.commit()
                db.refresh(existing)
            return existing
        
        # Create new assignment
        route_shop = RouteShop(
            shop_id=shop_id,
            route_id=route_id,
            sequence=sequence
        )
        db.add(route_shop)
        db.commit()
        db.refresh(route_shop)
        return route_shop
    
    @staticmethod
    def get_shops_by_route(db: Session, route_id: int) -> List[RouteShop]:
        """Get all shop assignments for a route."""
        return db.query(RouteShop).filter(
            RouteShop.route_id == route_id
        ).order_by(RouteShop.sequence.asc()).all()
    
    @staticmethod
    def get_routes_by_shop(db: Session, shop_id: int) -> List[RouteShop]:
        """Get all route assignments for a shop."""
        return db.query(RouteShop).filter(
            RouteShop.shop_id == shop_id
        ).all()
    
    @staticmethod
    def remove_shop_from_route(db: Session, shop_id: int, route_id: int) -> bool:
        """
        Remove a shop from a route.
        
        Args:
            db: Database session
            shop_id: Shop ID
            route_id: Route ID
        
        Returns:
            True if removed, False if not found
        """
        route_shop = db.query(RouteShop).filter(
            RouteShop.shop_id == shop_id,
            RouteShop.route_id == route_id
        ).first()
        
        if not route_shop:
            return False
        
        db.delete(route_shop)
        db.commit()
        return True




