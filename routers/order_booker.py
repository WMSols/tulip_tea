"""
Order Booker router.
Handles order booker CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
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
    db: Session = Depends(get_db)
):
    """Delete an order booker."""
    try:
        OrderBookerService.delete_order_booker(db=db, order_booker_id=order_booker_id)
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
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

