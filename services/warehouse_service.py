"""
Warehouse business logic service.
"""
from sqlalchemy.orm import Session
from repositories.warehouse_repository import WarehouseRepository
from repositories.zone_repository import ZoneRepository
from repositories.inventory_repository import InventoryRepository
from repositories.delivery_man_warehouse_repository import DeliveryManWarehouseRepository
from repositories.delivery_man_repository import DeliveryManRepository
from typing import Dict, List, Optional


class WarehouseService:
    """Service for Warehouse business logic."""
    
    @staticmethod
    def create_warehouse(db: Session, name: str, zone_id: int, address: str = None) -> Dict:
        """Create a new warehouse."""
        # Verify zone exists
        zone = ZoneRepository.get_by_id(db, zone_id)
        if not zone:
            raise ValueError(f"Zone with ID {zone_id} not found")
        
        warehouse = WarehouseRepository.create(
            db=db,
            name=name,
            zone_id=zone_id,
            address=address
        )
        
        return {
            "id": warehouse.id,
            "name": warehouse.name,
            "zone_id": warehouse.zone_id,
            "address": warehouse.address,
            "is_active": warehouse.is_active,
            "created_at": warehouse.created_at.isoformat() if warehouse.created_at else None
        }
    
    @staticmethod
    def get_all_warehouses(db: Session) -> List[Dict]:
        """Get all warehouses."""
        warehouses = WarehouseRepository.get_all(db)
        
        result = []
        for warehouse in warehouses:
            result.append({
                "id": warehouse.id,
                "name": warehouse.name,
                "zone_id": warehouse.zone_id,
                "address": warehouse.address,
                "is_active": warehouse.is_active,
                "created_at": warehouse.created_at.isoformat() if warehouse.created_at else None,
                "updated_at": warehouse.updated_at.isoformat() if warehouse.updated_at else None
            })
        
        return result
    
    @staticmethod
    def get_warehouse_inventory(db: Session, warehouse_id: int) -> List[Dict]:
        """Get all inventory items for a warehouse."""
        from repositories.product_repository import ProductRepository
        
        # Verify warehouse exists
        warehouse = WarehouseRepository.get_by_id(db, warehouse_id)
        if not warehouse:
            raise ValueError(f"Warehouse with ID {warehouse_id} not found")
        
        inventory_items = InventoryRepository.get_by_warehouse(db, warehouse_id)
        result = []
        
        for item in inventory_items:
            # Get product info if product_id exists
            product_name = None
            product_code = None
            if item.product_id:
                product = ProductRepository.get_by_id(db, item.product_id)
                if product:
                    product_name = product.name
                    product_code = product.code
            
            result.append({
                "id": item.id,
                "warehouse_id": item.warehouse_id,
                "product_id": item.product_id,
                "product_name": product_name,
                "product_code": product_code,
                "item_name": item.item_name,
                "item_code": item.item_code,
                "unit": item.unit,
                "quantity": item.quantity,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            })
        
        return result
    
    @staticmethod
    def add_inventory_item(db: Session, warehouse_id: int, product_id: int, 
                          quantity: int = 0) -> Dict:
        """Add inventory item to warehouse from active product."""
        from repositories.product_repository import ProductRepository
        
        # Verify warehouse exists
        warehouse = WarehouseRepository.get_by_id(db, warehouse_id)
        if not warehouse:
            raise ValueError(f"Warehouse with ID {warehouse_id} not found")
        
        # Verify product exists and is active
        product = ProductRepository.get_by_id(db, product_id, include_deleted=False)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")
        if not product.is_active:
            raise ValueError(f"Product '{product.name}' is not active. Only active products can be added to inventory.")
        
        # Check if inventory item for this product already exists in this warehouse
        existing_inventory = InventoryRepository.get_by_warehouse(db, warehouse_id)
        for inv in existing_inventory:
            if inv.product_id == product_id and inv.deleted_at is None:
                raise ValueError(f"Product '{product.name}' already exists in this warehouse inventory. Use update to modify quantity.")
        
        # Create inventory item with product information
        inventory = InventoryRepository.create(
            db=db,
            warehouse_id=warehouse_id,
            product_id=product_id,
            item_name=product.name,  # Auto-fill from product
            item_code=product.code,  # Auto-fill from product
            unit=product.unit,  # Auto-fill from product
            quantity=quantity
        )
        
        return {
            "id": inventory.id,
            "warehouse_id": inventory.warehouse_id,
            "product_id": inventory.product_id,
            "product_name": product.name,
            "product_code": product.code,
            "item_name": inventory.item_name,
            "item_code": inventory.item_code,
            "unit": inventory.unit,
            "quantity": inventory.quantity,
            "created_at": inventory.created_at.isoformat() if inventory.created_at else None
        }
    
    @staticmethod
    def update_inventory_item(db: Session, warehouse_id: int, inventory_id: int,
                             product_id: int = None, quantity: int = None) -> Dict:
        """Update inventory item (can change product or quantity)."""
        from repositories.product_repository import ProductRepository
        
        # Verify warehouse exists
        warehouse = WarehouseRepository.get_by_id(db, warehouse_id)
        if not warehouse:
            raise ValueError(f"Warehouse with ID {warehouse_id} not found")
        
        # Verify inventory item exists and belongs to warehouse
        inventory = InventoryRepository.get_by_id(db, inventory_id)
        if not inventory:
            raise ValueError(f"Inventory item with ID {inventory_id} not found")
        if inventory.warehouse_id != warehouse_id:
            raise ValueError(f"Inventory item does not belong to warehouse {warehouse_id}")
        
        # If product_id is being changed, verify new product exists and is active
        item_name = None
        item_code = None
        unit = None
        if product_id is not None:
            product = ProductRepository.get_by_id(db, product_id, include_deleted=False)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")
            if not product.is_active:
                raise ValueError(f"Product '{product.name}' is not active. Only active products can be used.")
            
            # Check if another inventory item for this product already exists in this warehouse
            existing_inventory = InventoryRepository.get_by_warehouse(db, warehouse_id)
            for inv in existing_inventory:
                if inv.id != inventory_id and inv.product_id == product_id and inv.deleted_at is None:
                    raise ValueError(f"Product '{product.name}' already exists in this warehouse inventory.")
            
            # Auto-update item_name, item_code, unit from product
            item_name = product.name
            item_code = product.code
            unit = product.unit
        
        updated = InventoryRepository.update(
            db=db,
            inventory_id=inventory_id,
            product_id=product_id,
            item_name=item_name,
            item_code=item_code,
            unit=unit,
            quantity=quantity
        )
        
        if not updated:
            raise ValueError("Failed to update inventory item")
        
        # Get product info for response
        product_name = None
        product_code = None
        if updated.product_id:
            product = ProductRepository.get_by_id(db, updated.product_id)
            if product:
                product_name = product.name
                product_code = product.code
        
        return {
            "id": updated.id,
            "warehouse_id": updated.warehouse_id,
            "product_id": updated.product_id,
            "product_name": product_name,
            "product_code": product_code,
            "item_name": updated.item_name,
            "item_code": updated.item_code,
            "unit": updated.unit,
            "quantity": updated.quantity,
            "created_at": updated.created_at.isoformat() if updated.created_at else None,
            "updated_at": updated.updated_at.isoformat() if updated.updated_at else None
        }
    
    @staticmethod
    def delete_inventory_item(db: Session, warehouse_id: int, inventory_id: int) -> bool:
        """Delete inventory item."""
        # Verify warehouse exists
        warehouse = WarehouseRepository.get_by_id(db, warehouse_id)
        if not warehouse:
            raise ValueError(f"Warehouse with ID {warehouse_id} not found")
        
        # Verify inventory item exists and belongs to warehouse
        inventory = InventoryRepository.get_by_id(db, inventory_id)
        if not inventory:
            raise ValueError(f"Inventory item with ID {inventory_id} not found")
        if inventory.warehouse_id != warehouse_id:
            raise ValueError(f"Inventory item does not belong to warehouse {warehouse_id}")
        
        return InventoryRepository.soft_delete(db, inventory_id)
    
    @staticmethod
    def get_warehouse_delivery_men(db: Session, warehouse_id: int) -> List[Dict]:
        """Get all delivery men assigned to a warehouse."""
        # Verify warehouse exists
        warehouse = WarehouseRepository.get_by_id(db, warehouse_id)
        if not warehouse:
            raise ValueError(f"Warehouse with ID {warehouse_id} not found")
        
        assignments = DeliveryManWarehouseRepository.get_by_warehouse(db, warehouse_id)
        
        result = []
        for assignment in assignments:
            delivery_man = DeliveryManRepository.get_by_id(db, assignment.delivery_man_id)
            if delivery_man:
                result.append({
                    "id": delivery_man.id,
                    "name": delivery_man.name,
                    "phone": delivery_man.phone,
                    "zone_id": delivery_man.zone_id,
                    "assigned_at": assignment.created_at.isoformat() if assignment.created_at else None
                })
        
        return result
    
    @staticmethod
    def assign_delivery_man(db: Session, warehouse_id: int, delivery_man_id: int) -> Dict:
        """Assign a delivery man to a warehouse."""
        # Verify warehouse exists
        warehouse = WarehouseRepository.get_by_id(db, warehouse_id)
        if not warehouse:
            raise ValueError(f"Warehouse with ID {warehouse_id} not found")
        
        # Verify delivery man exists
        delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id)
        if not delivery_man:
            raise ValueError(f"Delivery man with ID {delivery_man_id} not found")
        
        assignment = DeliveryManWarehouseRepository.assign(
            db=db,
            delivery_man_id=delivery_man_id,
            warehouse_id=warehouse_id
        )
        
        return {
            "id": assignment.id,
            "delivery_man_id": assignment.delivery_man_id,
            "warehouse_id": assignment.warehouse_id,
            "created_at": assignment.created_at.isoformat() if assignment.created_at else None
        }
    
    @staticmethod
    def unassign_delivery_man(db: Session, warehouse_id: int, delivery_man_id: int) -> bool:
        """Unassign a delivery man from a warehouse."""
        # Verify warehouse exists
        warehouse = WarehouseRepository.get_by_id(db, warehouse_id)
        if not warehouse:
            raise ValueError(f"Warehouse with ID {warehouse_id} not found")
        
        return DeliveryManWarehouseRepository.unassign(
            db=db,
            delivery_man_id=delivery_man_id,
            warehouse_id=warehouse_id
        )
    
    @staticmethod
    def delete_warehouse(db: Session, warehouse_id: int) -> bool:
        """Soft delete warehouse."""
        warehouse = WarehouseRepository.get_by_id(db, warehouse_id)
        if not warehouse:
            raise ValueError(f"Warehouse with ID {warehouse_id} not found")
        
        return WarehouseRepository.soft_delete(db, warehouse_id)


