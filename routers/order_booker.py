"""
Order Booker router.
Handles order booker CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from config.database import get_db
from models.schemas import OrderBookerCreate, OrderBookerResponse, OrderBookerUpdate
from services.order_booker_service import OrderBookerService

router = APIRouter(prefix="/order-bookers", tags=["Order Bookers"])


# List routes first (more specific paths)
@router.get("/distributor/{distributor_id}", response_model=List[OrderBookerResponse])
async def list_order_bookers_by_distributor(
    distributor_id: int,
    db: Session = Depends(get_db)
):
    """List all order bookers for a specific distributor."""
    try:
        order_bookers = OrderBookerService.get_order_bookers_by_distributor(
            db=db,
            distributor_id=distributor_id
        )
        return order_bookers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching order bookers: {str(e)}"
        )


@router.get("/zone/{zone_id}", response_model=List[OrderBookerResponse])
async def list_order_bookers_by_zone(
    zone_id: int,
    distributor_id: Optional[int] = Query(None, description="Optional distributor ID to filter order bookers"),
    db: Session = Depends(get_db)
):
    """
    List all order bookers assigned to a specific zone.
    
    Query Parameters:
        distributor_id: Optional - Filter order bookers by distributor
    
    This endpoint is useful when assigning routes to order bookers,
    as routes and order bookers must be in the same zone.
    """
    try:
        order_bookers = OrderBookerService.get_order_bookers_by_zone(
            db=db,
            zone_id=zone_id,
            distributor_id=distributor_id
        )
        return order_bookers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching order bookers: {str(e)}"
        )


# Update and Delete routes (before create to avoid conflicts)
@router.put("/{order_booker_id}", response_model=OrderBookerResponse)
async def update_order_booker(
    order_booker_id: int,
    update_data: OrderBookerUpdate,
    db: Session = Depends(get_db)
):
    """Update an order booker."""
    try:
        result = OrderBookerService.update_order_booker(
            db=db,
            order_booker_id=order_booker_id,
            name=update_data.name,
            phone=update_data.phone,
            email=update_data.email,
            zone_id=update_data.zone_id,
            password=update_data.password
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{order_booker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order_booker(
    order_booker_id: int,
    reassign_shops_to: int = None,
    reassign_routes_to: int = None,
    db: Session = Depends(get_db)
):
    """
    Delete an order booker with optional reassignment of shops and routes.
    
    This endpoint allows deleting an order booker while preserving data integrity.
    Shops and routes can be automatically reassigned to another order booker.
    
    QUERY PARAMETERS:
        reassign_shops_to: Optional - Order booker ID to reassign shops to
        reassign_routes_to: Optional - Order booker ID to reassign routes to
    
    BEHAVIOR:
    - If shops exist and reassign_shops_to is provided:
      * All shops' assigned_to_order_booker is updated to new order booker
      * created_by_order_booker remains unchanged (for audit trail)
    - If routes exist and reassign_routes_to is provided:
      * All routes' order_booker_id is updated to new order booker
    - If shops/routes exist but no reassignment is provided:
      * Returns 400 Bad Request with error message
    
    EXAMPLE USAGE:
        DELETE /order-bookers/1?reassign_shops_to=2&reassign_routes_to=2
        This will delete order booker 1 and reassign all shops and routes to order booker 2.
    
    Returns:
        204 No Content on success
        400 Bad Request if shops/routes exist without reassignment
        404 Not Found if order booker doesn't exist
    """
    try:
        OrderBookerService.delete_order_booker(
            db=db, 
            order_booker_id=order_booker_id,
            reassign_shops_to=reassign_shops_to,
            reassign_routes_to=reassign_routes_to
        )
        return None
    except ValueError as e:
        # Check if it's a "not found" error or a "cannot delete" error
        error_msg = str(e)
        if "not found" in error_msg.lower():
            status_code = status.HTTP_404_NOT_FOUND
        else:
            # It's a constraint violation or reassignment error
            status_code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=error_msg
        )


# Create route last (less specific path)
@router.post("/{distributor_id}", response_model=OrderBookerResponse, status_code=status.HTTP_201_CREATED)
async def create_order_booker(
    distributor_id: int,
    order_booker: OrderBookerCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new order booker.
    Only distributors can create order bookers.
    """
    try:
        result = OrderBookerService.create_order_booker(
            db=db,
            distributor_id=distributor_id,
            name=order_booker.name,
            phone=order_booker.phone,
            password=order_booker.password,
            email=order_booker.email,
            zone_id=order_booker.zone_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

