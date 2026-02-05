"""
Warehouse repository.
Data access layer for Warehouse operations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.warehouse import Warehouse
from typing import Optional, List


class WarehouseRepository:
    """Repository for Warehouse database operations."""
    
    @staticmethod
    def create(db: Session, name: str, distributor_id: int, zone_id: int = None, address: str = None) -> Warehouse:
        """Create a new warehouse. One warehouse per distributor."""
        warehouse = Warehouse(
            name=name,
            distributor_id=distributor_id,
            zone_id=zone_id,
            address=address,
            is_active=True
        )
        db.add(warehouse)
        db.commit()
        db.refresh(warehouse)
        return warehouse
    
    @staticmethod
    def get_by_id(db: Session, warehouse_id: int, include_deleted: bool = False) -> Optional[Warehouse]:
        """Get warehouse by ID (excludes soft-deleted and inactive by default)."""
        query = db.query(Warehouse).filter(Warehouse.id == warehouse_id)
        if not include_deleted:
            query = query.filter(Warehouse.deleted_at.is_(None), Warehouse.is_active == True)
        return query.first()
    
    @staticmethod
    def get_all(db: Session, include_deleted: bool = False) -> List[Warehouse]:
        """Get all warehouses (excludes soft-deleted and inactive by default)."""
        query = db.query(Warehouse)
        if not include_deleted:
            query = query.filter(Warehouse.deleted_at.is_(None), Warehouse.is_active == True)
        return query.all()
    
    @staticmethod
    def get_by_distributor(db: Session, distributor_id: int, include_deleted: bool = False) -> Optional[Warehouse]:
        """Get warehouse by distributor (one warehouse per distributor)."""
        query = db.query(Warehouse).filter(Warehouse.distributor_id == distributor_id)
        if not include_deleted:
            query = query.filter(Warehouse.deleted_at.is_(None), Warehouse.is_active == True)
        return query.first()
    
    @staticmethod
    def get_by_zone(db: Session, zone_id: int, include_deleted: bool = False) -> List[Warehouse]:
        """Get warehouses by zone."""
        query = db.query(Warehouse).filter(Warehouse.zone_id == zone_id)
        if not include_deleted:
            query = query.filter(Warehouse.deleted_at.is_(None), Warehouse.is_active == True)
        return query.all()
    
    @staticmethod
    def update(db: Session, warehouse_id: int, name: str = None, zone_id: int = None, 
               address: str = None, is_active: bool = None) -> Optional[Warehouse]:
        """Update warehouse."""
        warehouse = WarehouseRepository.get_by_id(db, warehouse_id, include_deleted=True)
        if not warehouse:
            return None
        
        if name is not None:
            warehouse.name = name
        if zone_id is not None:
            warehouse.zone_id = zone_id
        if address is not None:
            warehouse.address = address
        if is_active is not None:
            warehouse.is_active = is_active
        
        db.commit()
        db.refresh(warehouse)
        return warehouse
    
    @staticmethod
    def soft_delete(db: Session, warehouse_id: int) -> bool:
        """Soft delete warehouse."""
        warehouse = WarehouseRepository.get_by_id(db, warehouse_id, include_deleted=True)
        if not warehouse:
            return False
        
        from datetime import datetime
        warehouse.deleted_at = datetime.now()
        warehouse.is_active = False
        db.commit()
        return True

