"""
Delivery Item Repository
========================
Data access layer for DeliveryItem database operations.
"""
from sqlalchemy.orm import Session
from models.delivery_item import DeliveryItem
from typing import Optional, List


class DeliveryItemRepository:
    """Repository for DeliveryItem database operations."""
    
    @staticmethod
    def create(db: Session, delivery_id: int, order_item_id: int,
              product_id: int = None, inventory_item_id: int = None,
              quantity_picked_up: int = 0) -> DeliveryItem:
        """Create a new delivery item."""
        delivery_item = DeliveryItem(
            delivery_id=delivery_id,
            order_item_id=order_item_id,
            product_id=product_id,
            inventory_item_id=inventory_item_id,
            quantity_picked_up=quantity_picked_up
        )
        db.add(delivery_item)
        db.commit()
        db.refresh(delivery_item)
        return delivery_item
    
    @staticmethod
    def get_by_id(db: Session, delivery_item_id: int,
                 include_deleted: bool = False) -> Optional[DeliveryItem]:
        """Get delivery item by ID."""
        query = db.query(DeliveryItem).filter(DeliveryItem.id == delivery_item_id)
        if not include_deleted:
            query = query.filter(DeliveryItem.deleted_at.is_(None))
        return query.first()
    
    @staticmethod
    def get_by_delivery(db: Session, delivery_id: int,
                       include_deleted: bool = False) -> List[DeliveryItem]:
        """Get all delivery items for a delivery."""
        try:
            query = db.query(DeliveryItem).filter(DeliveryItem.delivery_id == delivery_id)
            if not include_deleted:
                # Check if deleted_at column exists before filtering
                if hasattr(DeliveryItem, 'deleted_at'):
                    query = query.filter(DeliveryItem.deleted_at.is_(None))
            return query.all()
        except Exception as e:
            # If there's an error, try without deleted_at filter
            try:
                query = db.query(DeliveryItem).filter(DeliveryItem.delivery_id == delivery_id)
                return query.all()
            except:
                raise e
    
    @staticmethod
    def get_by_order_item(db: Session, order_item_id: int,
                         include_deleted: bool = False) -> Optional[DeliveryItem]:
        """Get delivery item by order item ID."""
        query = db.query(DeliveryItem).filter(DeliveryItem.order_item_id == order_item_id)
        if not include_deleted:
            query = query.filter(DeliveryItem.deleted_at.is_(None))
        return query.order_by(DeliveryItem.created_at.desc()).first()
    
    @staticmethod
    def update_quantities(db: Session, delivery_item_id: int,
                          quantity_delivered: int = None,
                          quantity_returned: int = None) -> Optional[DeliveryItem]:
        """Update delivery item quantities."""
        delivery_item = DeliveryItemRepository.get_by_id(db, delivery_item_id)
        if not delivery_item:
            return None
        
        if quantity_delivered is not None:
            delivery_item.quantity_delivered = quantity_delivered
        if quantity_returned is not None:
            delivery_item.quantity_returned = quantity_returned
        
        db.commit()
        db.refresh(delivery_item)
        return delivery_item
    
    @staticmethod
    def update_pickup_quantity(db: Session, delivery_item_id: int,
                               quantity_picked_up: int) -> Optional[DeliveryItem]:
        """Update picked up quantity."""
        delivery_item = DeliveryItemRepository.get_by_id(db, delivery_item_id)
        if not delivery_item:
            return None
        
        delivery_item.quantity_picked_up = quantity_picked_up
        db.commit()
        db.refresh(delivery_item)
        return delivery_item

