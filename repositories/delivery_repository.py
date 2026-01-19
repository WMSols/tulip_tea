"""
Delivery Repository
==================
Data access layer for Delivery database operations.
"""
from sqlalchemy.orm import Session
from models.delivery import Delivery
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class DeliveryRepository:
    """Repository for Delivery database operations."""
    
    @staticmethod
    def create(db: Session, order_id: int, delivery_man_id: int, warehouse_id: int,
              status: str = 'pending_pickup') -> Delivery:
        """Create a new delivery record."""
        delivery = Delivery(
            order_id=order_id,
            delivery_man_id=delivery_man_id,
            warehouse_id=warehouse_id,
            status=status
        )
        db.add(delivery)
        db.commit()
        db.refresh(delivery)
        return delivery
    
    @staticmethod
    def get_by_id(db: Session, delivery_id: int, include_deleted: bool = False) -> Optional[Delivery]:
        """Get delivery by ID."""
        query = db.query(Delivery).filter(Delivery.id == delivery_id)
        if not include_deleted:
            query = query.filter(Delivery.deleted_at.is_(None))
        return query.first()
    
    @staticmethod
    def get_by_order(db: Session, order_id: int, include_deleted: bool = False) -> Optional[Delivery]:
        """Get delivery by order ID."""
        query = db.query(Delivery).filter(Delivery.order_id == order_id)
        if not include_deleted:
            query = query.filter(Delivery.deleted_at.is_(None))
        return query.order_by(Delivery.created_at.desc()).first()
    
    @staticmethod
    def get_by_delivery_man(db: Session, delivery_man_id: int,
                            skip: int = 0, limit: int = 100,
                            include_deleted: bool = False) -> List[Delivery]:
        """Get all deliveries by delivery man."""
        query = db.query(Delivery).filter(Delivery.delivery_man_id == delivery_man_id)
        if not include_deleted:
            query = query.filter(Delivery.deleted_at.is_(None))
        return query.order_by(Delivery.created_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_pickup(db: Session, delivery_id: int, picked_up_at: datetime,
                     pickup_gps_lat: Decimal = None, pickup_gps_lng: Decimal = None,
                     status: str = 'picked_up') -> Optional[Delivery]:
        """Update delivery with pickup information."""
        delivery = DeliveryRepository.get_by_id(db, delivery_id)
        if not delivery:
            return None
        
        delivery.status = status
        delivery.picked_up_at = picked_up_at
        if pickup_gps_lat is not None:
            delivery.pickup_gps_lat = pickup_gps_lat
        if pickup_gps_lng is not None:
            delivery.pickup_gps_lng = pickup_gps_lng
        
        db.commit()
        db.refresh(delivery)
        return delivery
    
    @staticmethod
    def update_delivery(db: Session, delivery_id: int, delivered_at: datetime,
                       delivery_gps_lat: Decimal = None, delivery_gps_lng: Decimal = None,
                       delivery_remarks: str = None, delivery_images: str = None,
                       status: str = 'delivered') -> Optional[Delivery]:
        """Update delivery with delivery information."""
        delivery = DeliveryRepository.get_by_id(db, delivery_id)
        if not delivery:
            return None
        
        delivery.status = status
        delivery.delivered_at = delivered_at
        if delivery_gps_lat is not None:
            delivery.delivery_gps_lat = delivery_gps_lat
        if delivery_gps_lng is not None:
            delivery.delivery_gps_lng = delivery_gps_lng
        if delivery_remarks is not None:
            delivery.delivery_remarks = delivery_remarks
        if delivery_images is not None:
            delivery.delivery_images = delivery_images
        
        db.commit()
        db.refresh(delivery)
        return delivery
    
    @staticmethod
    def update_return(db: Session, delivery_id: int, returned_at: datetime,
                     return_gps_lat: Decimal = None, return_gps_lng: Decimal = None,
                     return_reason: str = None, status: str = 'returned') -> Optional[Delivery]:
        """Update delivery with return information."""
        delivery = DeliveryRepository.get_by_id(db, delivery_id)
        if not delivery:
            return None
        
        delivery.status = status
        delivery.returned_at = returned_at
        if return_gps_lat is not None:
            delivery.return_gps_lat = return_gps_lat
        if return_gps_lng is not None:
            delivery.return_gps_lng = return_gps_lng
        if return_reason is not None:
            delivery.return_reason = return_reason
        
        db.commit()
        db.refresh(delivery)
        return delivery
    
    @staticmethod
    def update_status(db: Session, delivery_id: int, status: str) -> Optional[Delivery]:
        """Update delivery status."""
        delivery = DeliveryRepository.get_by_id(db, delivery_id)
        if not delivery:
            return None
        
        delivery.status = status
        db.commit()
        db.refresh(delivery)
        return delivery

