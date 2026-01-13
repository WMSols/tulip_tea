"""
Delivery Man router.
Handles delivery man CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import DeliveryManCreate, DeliveryManResponse, DeliveryManUpdate
from services.delivery_man_service import DeliveryManService

router = APIRouter(prefix="/delivery-men", tags=["Delivery Men"])


# List routes first (more specific paths)
@router.get("/distributor/{distributor_id}", response_model=List[DeliveryManResponse])
async def list_delivery_men_by_distributor(
    distributor_id: int,
    db: Session = Depends(get_db)
):
    """List all delivery men for a specific distributor."""
    try:
        delivery_men = DeliveryManService.get_delivery_men_by_distributor(
            db=db,
            distributor_id=distributor_id
        )
        return delivery_men
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching delivery men: {str(e)}"
        )


# Update and Delete routes (before create to avoid conflicts)
@router.put("/{delivery_man_id}", response_model=DeliveryManResponse)
async def update_delivery_man(
    delivery_man_id: int,
    update_data: DeliveryManUpdate,
    db: Session = Depends(get_db)
):
    """Update a delivery man."""
    try:
        result = DeliveryManService.update_delivery_man(
            db=db,
            delivery_man_id=delivery_man_id,
            name=update_data.name,
            phone=update_data.phone,
            zone_id=update_data.zone_id,
            password=update_data.password
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{delivery_man_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery_man(
    delivery_man_id: int,
    db: Session = Depends(get_db)
):
    """Delete a delivery man."""
    try:
        DeliveryManService.delete_delivery_man(db=db, delivery_man_id=delivery_man_id)
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# Create route last (less specific path)
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
            password=delivery_man.password,
            zone_id=delivery_man.zone_id,
            route_ids=delivery_man.route_ids
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

