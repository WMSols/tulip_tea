"""
Order Repository
===============
Data access layer for Order operations.
"""
from sqlalchemy.orm import Session
from models.order import Order
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime


class OrderRepository:
    """Repository for Order database operations."""
    
    @staticmethod
    def create(db: Session, shop_id: int, order_booker_id: int,
              total_amount: Decimal, distributor_id: int = None,
              delivery_man_id: int = None, visit_id: int = None,
              status: str = "pending", scheduled_date: date = None) -> Order:
        """
        Create a new order.
        
        Args:
            db: Database session
            shop_id: Shop ID where order was placed
            order_booker_id: Order booker ID who placed the order
            total_amount: Total order amount
            distributor_id: Distributor ID (optional)
            delivery_man_id: Delivery man ID (optional, assigned later)
            visit_id: Visit ID where order was placed (optional)
            status: Order status (default: "pending")
            scheduled_date: Scheduled delivery date (optional)
        
        Returns:
            Created order instance
        """
        order = Order(
            shop_id=shop_id,
            order_booker_id=order_booker_id,
            distributor_id=distributor_id,
            delivery_man_id=delivery_man_id,
            visit_id=visit_id,
            total_amount=total_amount,
            status=status,
            scheduled_date=scheduled_date
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def get_by_id(db: Session, order_id: int) -> Optional[Order]:
        """Get order by ID."""
        return db.query(Order).filter(Order.id == order_id).first()
    
    @staticmethod
    def get_by_shop(db: Session, shop_id: int) -> List[Order]:
        """Get all orders for a shop."""
        return db.query(Order).filter(Order.shop_id == shop_id).order_by(Order.created_at.desc()).all()
    
    @staticmethod
    def get_by_order_booker(db: Session, order_booker_id: int) -> List[Order]:
        """Get all orders placed by an order booker."""
        return db.query(Order).filter(Order.order_booker_id == order_booker_id).order_by(Order.created_at.desc()).all()
    
    @staticmethod
    def get_by_delivery_man(db: Session, delivery_man_id: int) -> List[Order]:
        """Get all orders assigned to a delivery man."""
        return db.query(Order).filter(Order.delivery_man_id == delivery_man_id).order_by(Order.created_at.desc()).all()
    
    @staticmethod
    def get_by_visit(db: Session, visit_id: int) -> List[Order]:
        """Get all orders linked to a visit."""
        return db.query(Order).filter(Order.visit_id == visit_id).all()
    
    @staticmethod
    def get_pending(db: Session, distributor_id: int = None) -> List[Order]:
        """Get all pending orders."""
        query = db.query(Order).filter(Order.status == "pending")
        if distributor_id:
            query = query.filter(Order.distributor_id == distributor_id)
        return query.order_by(Order.created_at.desc()).all()
    
    @staticmethod
    def assign_delivery_man(db: Session, order_id: int, delivery_man_id: int) -> Optional[Order]:
        """Assign order to a delivery man."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None
        order.delivery_man_id = delivery_man_id
        order.status = "confirmed"
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def update_status(db: Session, order_id: int, status: str) -> Optional[Order]:
        """Update order status."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None
        order.status = status
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def update_delivery_proof(db: Session, order_id: int, status: str,
                              delivery_gps_lat: Decimal = None,
                              delivery_gps_lng: Decimal = None,
                              delivery_remarks: str = None,
                              delivery_images: str = None) -> Optional[Order]:
        """
        Update order with delivery proof information.
        
        Args:
            db: Database session
            order_id: Order ID
            status: Order status ("delivered" or "cancelled")
            delivery_gps_lat: GPS latitude when delivered/cancelled
            delivery_gps_lng: GPS longitude when delivered/cancelled
            delivery_remarks: Remarks/notes from delivery man
            delivery_images: JSON string or list of image URLs (PostgreSQL TEXT[] array)
        
        Returns:
            Updated order instance or None if not found
        """
        import json
        from sqlalchemy import text
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None
        
        order.status = status
        # GPS removed from orders - stored in shop_visits instead
        # if delivery_gps_lat is not None:
        #     order.delivery_gps_lat = delivery_gps_lat
        # if delivery_gps_lng is not None:
        #     order.delivery_gps_lng = delivery_gps_lng
        if delivery_remarks is not None:
            order.delivery_remarks = delivery_remarks
        if delivery_images is not None:
            # Store as JSON string in TEXT column
            if isinstance(delivery_images, list):
                # Convert list to JSON string
                order.delivery_images = json.dumps(delivery_images)
            else:
                # If it's already a string (JSON format), store directly
                order.delivery_images = delivery_images
        
        db.commit()
        db.refresh(order)
        return order















