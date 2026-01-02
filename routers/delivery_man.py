"""
Delivery Man router.
Handles delivery man CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import DeliveryManCreate, DeliveryManResponse
from services.delivery_man_service import DeliveryManService

router = APIRouter(prefix="/delivery-men", tags=["Delivery Men"])


@router.post("/{distributor_id}", response_model=DeliveryManResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_man(
    distributor_id: int,
    delivery_man: DeliveryManCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new delivery man.
    Only distributors can create delivery men.
    """
    try:
        result = DeliveryManService.create_delivery_man(
            db=db,
            distributor_id=distributor_id,
            name=delivery_man.name,
            phone=delivery_man.phone,
            password=delivery_man.password
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/distributor/{distributor_id}", response_model=List[DeliveryManResponse])
async def list_delivery_men_by_distributor(
    distributor_id: int,
    db: Session = Depends(get_db)
):
    """List all delivery men for a specific distributor."""
    delivery_men = DeliveryManService.get_delivery_men_by_distributor(
        db=db,
        distributor_id=distributor_id
    )
    return delivery_men

