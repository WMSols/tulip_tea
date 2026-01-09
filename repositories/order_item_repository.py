"""
Order Item Repository
====================
Data access layer for Order Item operations.
"""
from sqlalchemy.orm import Session
from models.order_item import OrderItem
from typing import List, Optional
from decimal import Decimal


class OrderItemRepository:
    """Repository for Order Item database operations."""
    
    @staticmethod
    def create(db: Session, order_id: int, product_name: str,
              quantity: int, unit_price: Decimal, total_price: Decimal) -> OrderItem:
        """
        Create a new order item.
        
        Args:
            db: Database session
            order_id: Order ID this item belongs to
            product_name: Product name
            quantity: Quantity ordered
            unit_price: Price per unit
            total_price: Total price (quantity × unit_price)
        
        Returns:
            Created order item instance
        """
        item = OrderItem(
            order_id=order_id,
            product_name=product_name,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    
    @staticmethod
    def get_by_order(db: Session, order_id: int) -> List[OrderItem]:
        """Get all items for an order."""
        return db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    
    @staticmethod
    def delete_by_order(db: Session, order_id: int) -> int:
        """Delete all items for an order."""
        count = db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()
        db.commit()
        return count



