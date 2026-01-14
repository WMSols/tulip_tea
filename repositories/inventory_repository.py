"""
Inventory repository.
Data access layer for Inventory operations.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from models.inventory import Inventory
from typing import Optional, List


class InventoryRepository:
    """Repository for Inventory database operations."""
    
    @staticmethod
    def create(db: Session, warehouse_id: int, product_id: int = None, 
               item_name: str = None, item_code: str = None,
               unit: str = None, quantity: int = 0) -> Inventory:
        """Create a new inventory item.
        
        Args:
            warehouse_id: Warehouse ID
            product_id: Product ID from products table (required for new inventory)
            item_name: Item name (auto-filled from product if product_id provided)
            item_code: Item code (auto-filled from product if product_id provided)
            unit: Unit (auto-filled from product if product_id provided)
            quantity: Initial quantity
        """
        inventory = Inventory(
            warehouse_id=warehouse_id,
            product_id=product_id,
            item_name=item_name,
            item_code=item_code,
            unit=unit,
            quantity=quantity
        )
        db.add(inventory)
        db.commit()
        db.refresh(inventory)
        return inventory
    
    @staticmethod
    def get_by_id(db: Session, inventory_id: int, include_deleted: bool = False) -> Optional[Inventory]:
        """Get inventory item by ID."""
        query = db.query(Inventory).filter(Inventory.id == inventory_id)
        if not include_deleted:
            query = query.filter(Inventory.deleted_at.is_(None))
        return query.first()
    
    @staticmethod
    def get_by_warehouse(db: Session, warehouse_id: int, include_deleted: bool = False) -> List[Inventory]:
        """Get all inventory items for a warehouse."""
        query = db.query(Inventory).filter(Inventory.warehouse_id == warehouse_id)
        if not include_deleted:
            query = query.filter(Inventory.deleted_at.is_(None))
        return query.all()
    
    @staticmethod
    def update(db: Session, inventory_id: int, product_id: int = None,
              item_name: str = None, item_code: str = None,
              unit: str = None, quantity: int = None) -> Optional[Inventory]:
        """Update inventory item.
        
        Args:
            inventory_id: Inventory item ID
            product_id: Product ID (if changed, item_name/item_code/unit will be updated from product)
            item_name: Item name (auto-updated from product if product_id changes)
            item_code: Item code (auto-updated from product if product_id changes)
            unit: Unit (auto-updated from product if product_id changes)
            quantity: Quantity
        """
        inventory = InventoryRepository.get_by_id(db, inventory_id, include_deleted=True)
        if not inventory:
            return None
        
        if product_id is not None:
            inventory.product_id = product_id
        if item_name is not None:
            inventory.item_name = item_name
        if item_code is not None:
            inventory.item_code = item_code
        if unit is not None:
            inventory.unit = unit
        if quantity is not None:
            inventory.quantity = quantity
        
        db.commit()
        db.refresh(inventory)
        return inventory
    
    @staticmethod
    def soft_delete(db: Session, inventory_id: int) -> bool:
        """Soft delete inventory item."""
        inventory = InventoryRepository.get_by_id(db, inventory_id, include_deleted=True)
        if not inventory:
            return False
        
        inventory.deleted_at = datetime.now()
        db.commit()
        return True

