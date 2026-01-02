"""
Order Booker router.
Handles order booker CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import OrderBookerCreate, OrderBookerResponse
from services.order_booker_service import OrderBookerService

router = APIRouter(prefix="/order-bookers", tags=["Order Bookers"])


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
            assigned_zone=order_booker.assigned_zone,
            password=order_booker.password,
            email=order_booker.email
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/distributor/{distributor_id}", response_model=List[OrderBookerResponse])
async def list_order_bookers_by_distributor(
    distributor_id: int,
    db: Session = Depends(get_db)
):
    """List all order bookers for a specific distributor."""
    order_bookers = OrderBookerService.get_order_bookers_by_distributor(
        db=db,
        distributor_id=distributor_id
    )
    return order_bookers

