"""
Warehouse router.
Handles warehouse CRUD operations, inventory management, and delivery man assignments.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from config.database import get_db
from models.schemas import (
    WarehouseCreate, WarehouseResponse, WarehouseUpdate, WarehouseDetailsResponse,
    InventoryCreate, InventoryResponse, InventoryUpdate
)
from services.warehouse_service import WarehouseService
from utils.dependencies import get_current_user, get_current_distributor, get_current_super_admin

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])


# Warehouse creation endpoint removed - warehouses are automatically created when distributors are created
# One warehouse per distributor is automatically assigned


@router.get("/all", response_model=List[WarehouseDetailsResponse], tags=["Warehouses", "Super Admin APIs"])
async def get_all_warehouses_for_admin(
    current_user: Dict = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get all warehouses with active inventory details.
    Only accessible by super admin.
    Returns warehouses from all distributors with their inventory.
    """
    try:
        warehouses = WarehouseService.get_all_warehouses_with_inventory(db)
        return warehouses
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching warehouses: {str(e)}"
        )


@router.get("/", response_model=List[WarehouseResponse], tags=["Warehouses", "Distributor APIs"])
async def list_warehouses(
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """List all warehouses for the authenticated distributor. Distributors can only see their own warehouses."""
    try:
        warehouses = WarehouseService.get_warehouses_by_distributor(db, distributor['user_id'])
        return warehouses
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching warehouses: {str(e)}"
        )


@router.get("/{warehouse_id}", response_model=WarehouseDetailsResponse, tags=["Warehouses", "Distributor APIs", "Super Admin APIs"])
async def get_warehouse(
    warehouse_id: int,
    distributor_id: Optional[int] = Query(None, description="Distributor ID (optional for super admin to query any warehouse)"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific warehouse by ID with all details (inventory, delivery men).
    
    For distributors: Only accessible by the warehouse's distributor (distributor_id is auto-detected from token).
    For super admin: Can access any warehouse by providing distributor_id as query parameter.
    """
    try:
        user_role = current_user.get('user_role', 'distributor')
        
        if user_role == 'super_admin':
            # Super admin can query any warehouse
            if distributor_id:
                # Validate warehouse belongs to specified distributor
                warehouse = WarehouseService.get_warehouse_with_details(db, warehouse_id, distributor_id)
            else:
                # Get warehouse without distributor validation (super admin privilege)
                # Need to modify service to handle None distributor_id
                warehouse = WarehouseService.get_warehouse_with_details(db, warehouse_id, None)
        else:
            # Regular distributor - use their ID from token, validate ownership
            if user_role != 'distributor':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only distributors and super admins can access this endpoint"
                )
            warehouse = WarehouseService.get_warehouse_with_details(db, warehouse_id, current_user['user_id'])
        
        return warehouse
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching warehouse: {str(e)}"
        )


@router.get("/{warehouse_id}/details", response_model=WarehouseDetailsResponse, tags=["Warehouses", "Distributor APIs"])
async def get_warehouse_details(
    warehouse_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Get warehouse with all related items: inventory, delivery men, etc. Only accessible by the warehouse's distributor."""
    try:
        warehouse = WarehouseService.get_warehouse_with_details(db, warehouse_id, distributor['user_id'])
        return warehouse
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching warehouse details: {str(e)}"
        )


@router.get("/{warehouse_id}/inventory", response_model=List[InventoryResponse], tags=["Warehouses", "Distributor APIs"])
async def get_warehouse_inventory(
    warehouse_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Get all inventory items for a warehouse. Only accessible by the warehouse's distributor."""
    try:
        inventory = WarehouseService.get_warehouse_inventory(db, warehouse_id, distributor['user_id'])
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


@router.post("/{warehouse_id}/inventory", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED, tags=["Warehouses", "Distributor APIs"])
async def add_inventory_item(
    warehouse_id: int,
    inventory: InventoryCreate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Add inventory item to warehouse from active product. Only the warehouse's distributor can add inventory."""
    try:
        result = WarehouseService.add_inventory_item(
            db=db,
            warehouse_id=warehouse_id,
            product_id=inventory.product_id,
            quantity=inventory.quantity,
            distributor_id=distributor['user_id']
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


@router.put("/{warehouse_id}/inventory/{inventory_id}", response_model=InventoryResponse, tags=["Warehouses", "Distributor APIs"])
async def update_inventory_item(
    warehouse_id: int,
    inventory_id: int,
    inventory: InventoryUpdate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Update inventory item (can change product or quantity). Only the warehouse's distributor can update inventory."""
    try:
        result = WarehouseService.update_inventory_item(
            db=db,
            warehouse_id=warehouse_id,
            inventory_id=inventory_id,
            product_id=inventory.product_id,
            quantity=inventory.quantity,
            distributor_id=distributor['user_id']
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


@router.delete("/{warehouse_id}/inventory/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Warehouses", "Distributor APIs"])
async def delete_inventory_item(
    warehouse_id: int,
    inventory_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Delete inventory item. Only the warehouse's distributor can delete inventory."""
    try:
        success = WarehouseService.delete_inventory_item(db, warehouse_id, inventory_id, distributor['user_id'])
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


@router.get("/{warehouse_id}/delivery-men", response_model=List[dict], tags=["Warehouses", "Distributor APIs"])
async def get_warehouse_delivery_men(
    warehouse_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Get all delivery men assigned to a warehouse. Only accessible by the warehouse's distributor."""
    try:
        delivery_men = WarehouseService.get_warehouse_delivery_men(db, warehouse_id, distributor['user_id'])
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


@router.post("/{warehouse_id}/delivery-men/{delivery_man_id}", status_code=status.HTTP_201_CREATED, tags=["Warehouses", "Distributor APIs"])
async def assign_delivery_man(
    warehouse_id: int,
    delivery_man_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Assign a delivery man to a warehouse. Only the warehouse's distributor can assign delivery men."""
    try:
        result = WarehouseService.assign_delivery_man(db, warehouse_id, delivery_man_id, distributor['user_id'])
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{warehouse_id}/delivery-men/{delivery_man_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Warehouses", "Distributor APIs"])
async def unassign_delivery_man(
    warehouse_id: int,
    delivery_man_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Unassign a delivery man from a warehouse. Only the warehouse's distributor can unassign delivery men."""
    try:
        success = WarehouseService.unassign_delivery_man(db, warehouse_id, delivery_man_id, distributor['user_id'])
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


