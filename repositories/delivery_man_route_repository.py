"""
Delivery Man-Route Repository
==============================
Data access layer for Delivery Man-Route junction table operations.
"""
from sqlalchemy.orm import Session
from models.delivery_man_route import DeliveryManRoute
from typing import List, Optional


class DeliveryManRouteRepository:
    """Repository for Delivery Man-Route junction table operations."""

    @staticmethod
    def assign_route_to_delivery_man(db: Session, delivery_man_id: int, route_id: int) -> DeliveryManRoute:
        """
        Assign a route to a delivery man.
        
        Args:
            db: Database session
            delivery_man_id: Delivery man ID
            route_id: Route ID to assign
        
        Returns:
            Created DeliveryManRoute instance
        """
        # Check if assignment already exists
        existing = db.query(DeliveryManRoute).filter(
            DeliveryManRoute.delivery_man_id == delivery_man_id,
            DeliveryManRoute.route_id == route_id,
            DeliveryManRoute.deleted_at.is_(None)
        ).first()
        
        if existing:
            return existing
        
        # Create new assignment
        delivery_man_route = DeliveryManRoute(
            delivery_man_id=delivery_man_id,
            route_id=route_id
        )
        db.add(delivery_man_route)
        db.commit()
        db.refresh(delivery_man_route)
        return delivery_man_route

    @staticmethod
    def assign_routes_to_delivery_man(db: Session, delivery_man_id: int, route_ids: List[int]) -> List[DeliveryManRoute]:
        """
        Assign multiple routes to a delivery man.
        
        Args:
            db: Database session
            delivery_man_id: Delivery man ID
            route_ids: List of route IDs to assign
        
        Returns:
            List of created DeliveryManRoute instances
        """
        assignments = []
        for route_id in route_ids:
            assignment = DeliveryManRouteRepository.assign_route_to_delivery_man(
                db=db,
                delivery_man_id=delivery_man_id,
                route_id=route_id
            )
            assignments.append(assignment)
        return assignments

    @staticmethod
    def get_routes_by_delivery_man(db: Session, delivery_man_id: int) -> List[DeliveryManRoute]:
        """Get all route assignments for a delivery man."""
        return db.query(DeliveryManRoute).filter(
            DeliveryManRoute.delivery_man_id == delivery_man_id,
            DeliveryManRoute.deleted_at.is_(None)
        ).all()

    @staticmethod
    def get_delivery_men_by_route(db: Session, route_id: int) -> List[DeliveryManRoute]:
        """Get all delivery men assigned to a route."""
        return db.query(DeliveryManRoute).filter(
            DeliveryManRoute.route_id == route_id,
            DeliveryManRoute.deleted_at.is_(None)
        ).all()

    @staticmethod
    def unassign_route(db: Session, delivery_man_id: int, route_id: int) -> bool:
        """
        Soft delete (unassign) a route from a delivery man.
        
        Args:
            db: Database session
            delivery_man_id: Delivery man ID
            route_id: Route ID to unassign
        
        Returns:
            True if successful, False otherwise
        """
        from datetime import datetime
        assignment = db.query(DeliveryManRoute).filter(
            DeliveryManRoute.delivery_man_id == delivery_man_id,
            DeliveryManRoute.route_id == route_id,
            DeliveryManRoute.deleted_at.is_(None)
        ).first()
        
        if not assignment:
            return False
        
        assignment.deleted_at = datetime.utcnow()
        db.commit()
        db.refresh(assignment)
        return True






