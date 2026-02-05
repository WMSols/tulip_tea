"""
Warehouse router.
Handles warehouse CRUD operations, inventory management, and delivery man assignments.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict
from config.database import get_db
from models.schemas import (
    WarehouseCreate, WarehouseResponse, WarehouseUpdate,
    InventoryCreate, InventoryResponse, InventoryUpdate
)
from services.warehouse_service import WarehouseService
from utils.dependencies import get_current_user, get_current_distributor

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])


# Warehouse creation endpoint removed - warehouses are automatically created when distributors are created
# One warehouse per distributor is automatically assigned


@router.get("/", response_model=List[WarehouseResponse])
async def list_warehouses(
    distributor_id: int = Query(None, description="Optional distributor ID to filter warehouses"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all warehouses. Requires authentication. Filter by distributor_id if provided."""
    try:
        if distributor_id:
            warehouses = WarehouseService.get_warehouses_by_distributor(db, distributor_id)
        else:
            warehouses = WarehouseService.get_all_warehouses(db)
        return warehouses
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching warehouses: {str(e)}"
        )


@router.get("/{warehouse_id}/inventory", response_model=List[InventoryResponse])
async def get_warehouse_inventory(
    warehouse_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all inventory items for a warehouse. Requires authentication."""
    try:
        inventory = WarehouseService.get_warehouse_inventory(db, warehouse_id)
        return inventory
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching inventory: {str(e)}"
        )


@router.post("/{warehouse_id}/inventory", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def add_inventory_item(
    warehouse_id: int,
    inventory: InventoryCreate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Add inventory item to warehouse from active product. Only distributors can add inventory."""
    try:
        result = WarehouseService.add_inventory_item(
            db=db,
            warehouse_id=warehouse_id,
            product_id=inventory.product_id,
            quantity=inventory.quantity
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding inventory item: {str(e)}"
        )


@router.put("/{warehouse_id}/inventory/{inventory_id}", response_model=InventoryResponse)
async def update_inventory_item(
    warehouse_id: int,
    inventory_id: int,
    inventory: InventoryUpdate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Update inventory item (can change product or quantity). Only distributors can update inventory."""
    try:
        result = WarehouseService.update_inventory_item(
            db=db,
            warehouse_id=warehouse_id,
            inventory_id=inventory_id,
            product_id=inventory.product_id,
            quantity=inventory.quantity
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating inventory item: {str(e)}"
        )


@router.delete("/{warehouse_id}/inventory/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    warehouse_id: int,
    inventory_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Delete inventory item. Only distributors can delete inventory."""
    try:
        success = WarehouseService.delete_inventory_item(db, warehouse_id, inventory_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{warehouse_id}/delivery-men", response_model=List[dict])
async def get_warehouse_delivery_men(
    warehouse_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all delivery men assigned to a warehouse. Requires authentication."""
    try:
        delivery_men = WarehouseService.get_warehouse_delivery_men(db, warehouse_id)
        return delivery_men
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching delivery men: {str(e)}"
        )


@router.post("/{warehouse_id}/delivery-men/{delivery_man_id}", status_code=status.HTTP_201_CREATED)
async def assign_delivery_man(
    warehouse_id: int,
    delivery_man_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Assign a delivery man to a warehouse. Only distributors can assign delivery men."""
    try:
        result = WarehouseService.assign_delivery_man(db, warehouse_id, delivery_man_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{warehouse_id}/delivery-men/{delivery_man_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_delivery_man(
    warehouse_id: int,
    delivery_man_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Unassign a delivery man from a warehouse. Only distributors can unassign delivery men."""
    try:
        success = WarehouseService.unassign_delivery_man(db, warehouse_id, delivery_man_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Warehouse deletion endpoint removed - warehouses cannot be deleted
# They are automatically managed with distributors (one warehouse per distributor)


