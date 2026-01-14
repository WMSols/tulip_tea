"""
Delivery Man-Warehouse repository.
Data access layer for Delivery Man-Warehouse junction table operations.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from models.delivery_man_warehouse import DeliveryManWarehouse
from typing import Optional, List


class DeliveryManWarehouseRepository:
    """Repository for Delivery Man-Warehouse database operations."""
    
    @staticmethod
    def assign(db: Session, delivery_man_id: int, warehouse_id: int) -> DeliveryManWarehouse:
        """Assign a delivery man to a warehouse."""
        # Check if assignment already exists
        existing = db.query(DeliveryManWarehouse).filter(
            DeliveryManWarehouse.delivery_man_id == delivery_man_id,
            DeliveryManWarehouse.warehouse_id == warehouse_id,
            DeliveryManWarehouse.deleted_at.is_(None)
        ).first()
        
        if existing:
            # Reactivate if soft-deleted
            existing.deleted_at = None
            db.commit()
            db.refresh(existing)
            return existing
        
        assignment = DeliveryManWarehouse(
            delivery_man_id=delivery_man_id,
            warehouse_id=warehouse_id
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment
    
    @staticmethod
    def unassign(db: Session, delivery_man_id: int, warehouse_id: int) -> bool:
        """Unassign a delivery man from a warehouse (soft delete)."""
        assignment = db.query(DeliveryManWarehouse).filter(
            DeliveryManWarehouse.delivery_man_id == delivery_man_id,
            DeliveryManWarehouse.warehouse_id == warehouse_id,
            DeliveryManWarehouse.deleted_at.is_(None)
        ).first()
        
        if not assignment:
            return False
        
        assignment.deleted_at = datetime.now()
        db.commit()
        return True
    
    @staticmethod
    def get_by_warehouse(db: Session, warehouse_id: int) -> List[DeliveryManWarehouse]:
        """Get all delivery men assigned to a warehouse."""
        return db.query(DeliveryManWarehouse).filter(
            DeliveryManWarehouse.warehouse_id == warehouse_id,
            DeliveryManWarehouse.deleted_at.is_(None)
        ).all()
    
    @staticmethod
    def get_by_delivery_man(db: Session, delivery_man_id: int) -> List[DeliveryManWarehouse]:
        """Get all warehouses assigned to a delivery man."""
        return db.query(DeliveryManWarehouse).filter(
            DeliveryManWarehouse.delivery_man_id == delivery_man_id,
            DeliveryManWarehouse.deleted_at.is_(None)
        ).all()

