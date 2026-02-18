"""
Order Repository
===============
Data access layer for Order operations.
"""
from sqlalchemy.orm import Session
from models.order import Order, OrderStatus
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime


class OrderRepository:
    """Repository for Order database operations."""
    
    @staticmethod
    def create(db: Session, shop_id: int, order_booker_id: int,
              total_amount: Decimal, distributor_id: int = None,
              delivery_man_id: int = None, visit_id: int = None,
              status: OrderStatus = OrderStatus.PENDING, scheduled_date: date = None,
              original_amount: Decimal = None, final_total_amount: Decimal = None,
              subsidy_status: str = None, subsidy_approved_by: int = None,
              subsidy_approved_at: datetime = None, subsidy_rejection_reason: str = None,
              order_resolution_type: str = None, subsidy_id: int = None, auto_commit: bool = True) -> Order:
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
            order_resolution_type: How order was resolved ('normal', 'subsidy', 'payment_before_delivery')
            subsidy_id: Subsidy ID applied (if order_resolution_type='subsidy')
            original_amount: Original amount before subsidy (only for subsidy orders)
        
        Returns:
            Created order instance
        """
        # Ensure status is the enum value (lowercase string) not the enum name
        # SQLAlchemy's PostgreSQL ENUM sometimes converts to uppercase, so we need to ensure
        # we're using the enum value correctly. The enum value is lowercase ("pending")
        if isinstance(status, OrderStatus):
            # Already an enum, use it directly
            status_enum = status
            print(f"[DEBUG OrderRepository.create] Status is enum: {status_enum}, value: {status_enum.value}")
        else:
            # Convert string to enum
            status_str = str(status).lower()
            if status_str == 'pending':
                status_enum = OrderStatus.PENDING
            elif status_str == 'delivered':
                status_enum = OrderStatus.DELIVERED
            elif status_str == 'disapproved':
                status_enum = OrderStatus.DISAPPROVED
            else:
                status_enum = OrderStatus.PENDING
            print(f"[DEBUG OrderRepository.create] Converted string {status} to enum: {status_enum}, value: {status_enum.value}")
        
        # Create order - TypeDecorator should handle the conversion
        print(f"[DEBUG OrderRepository.create] Creating order with status: {status_enum} (value: {status_enum.value})")
        order = Order(
            shop_id=shop_id,
            order_booker_id=order_booker_id,
            distributor_id=distributor_id,
            delivery_man_id=delivery_man_id,
            visit_id=visit_id,
            total_amount=total_amount,
            status=status_enum,
            scheduled_date=scheduled_date,
            original_amount=original_amount,
            final_total_amount=final_total_amount,
            subsidy_status=subsidy_status,
            subsidy_approved_by=subsidy_approved_by,
            subsidy_approved_at=subsidy_approved_at,
            subsidy_rejection_reason=subsidy_rejection_reason,
            # Legacy fields (for backward compatibility)
            order_resolution_type=order_resolution_type,
            subsidy_id=subsidy_id
        )
        print(f"[DEBUG OrderRepository.create] Order created, status attribute: {order.status}, type: {type(order.status)}")
        db.add(order)
        db.flush()
        db.refresh(order)
        
        # Commit transaction if auto_commit is True
        if auto_commit:
            db.commit()
        
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
        query = db.query(Order).filter(Order.status == OrderStatus.PENDING)
        if distributor_id:
            query = query.filter(Order.distributor_id == distributor_id)
        return query.order_by(Order.created_at.desc()).all()
    
    @staticmethod
    def assign_delivery_man(db: Session, order_id: int, delivery_man_id: int, auto_commit: bool = True) -> Optional[Order]:
        """
        Assign order to a delivery man.
        
        Args:
            db: Database session
            order_id: Order ID
            delivery_man_id: Delivery man ID
            auto_commit: If True, commits immediately. If False, caller must commit.
        
        Returns:
            Updated order or None if not found
        """
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None
        order.delivery_man_id = delivery_man_id
        # Status remains "pending" until delivery man marks it as delivered or disapproved
        # order.status = "pending"  # Already pending, no need to change
        db.flush()
        db.refresh(order)
        if auto_commit:
            db.commit()
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
    def update_delivery_proof(db: Session, order_id: int, status: OrderStatus,
                              delivery_gps_lat: Decimal = None,
                              delivery_gps_lng: Decimal = None,
                              delivery_remarks: str = None,
                              delivery_images: str = None) -> Optional[Order]:
        """
        Update order with delivery proof information.
        
        Args:
            db: Database session
            order_id: Order ID
            status: Order status (OrderStatus.DELIVERED or OrderStatus.DISAPPROVED)
            delivery_gps_lat: GPS latitude when delivered/disapproved
            delivery_gps_lng: GPS longitude when delivered/disapproved
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















