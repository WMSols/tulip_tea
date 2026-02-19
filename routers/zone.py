"""
Zone router.
Handles zone CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from config.database import get_db
from models.schemas import ZoneCreate, ZoneUpdate, ZoneResponse
from services.zone_service import ZoneService
from utils.dependencies import get_current_user, get_current_distributor

router = APIRouter(prefix="/zones", tags=["Zones"])


@router.post("/", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED, tags=["Zones", "Distributor APIs"])
async def create_zone(
    zone: ZoneCreate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Create a new zone. Only distributors can create zones."""
    try:
        result = ZoneService.create_zone(
            db=db, 
            name=zone.name,
            distributor_id=distributor['user_id']  # Store distributor_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[ZoneResponse], tags=["Zones", "Distributor APIs", "Order Booker APIs"])
async def list_zones(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List zones. Filters by distributor for distributors, shows zones from their distributor for order bookers/delivery men."""
    distributor_id = None
    
    # If user is a distributor, filter by their zones
    if current_user.get('role') == 'distributor':
        distributor_id = current_user.get('user_id')
    # If user is an order booker, filter by their distributor's zones
    elif current_user.get('role') == 'order_booker':
        from repositories.order_booker_repository import OrderBookerRepository
        order_booker = OrderBookerRepository.get_by_id(db, current_user.get('user_id'))
        if order_booker and order_booker.distributor_id:
            distributor_id = order_booker.distributor_id
    # If user is a delivery man, filter by their distributor's zones
    elif current_user.get('role') == 'delivery_man':
        from repositories.delivery_man_repository import DeliveryManRepository
        delivery_man = DeliveryManRepository.get_by_id(db, current_user.get('user_id'))
        if delivery_man and delivery_man.distributor_id:
            distributor_id = delivery_man.distributor_id
    
    zones = ZoneService.get_all_zones(db=db, distributor_id=distributor_id)
    return zones


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get zone by ID. Requires authentication."""
    try:
        zone = ZoneService.get_zone_by_id(db=db, zone_id=zone_id)
        return zone
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/{zone_id}", response_model=ZoneResponse, tags=["Zones", "Distributor APIs"])
async def update_zone(
    zone_id: int,
    zone: ZoneUpdate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Update zone name. Only the owning distributor can update."""
    try:
        result = ZoneService.update_zone(
            db=db, 
            zone_id=zone_id, 
            name=zone.name,
            distributor_id=distributor['user_id']  # Validate ownership
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Delete a zone. Only the owning distributor can delete."""
    try:
        ZoneService.delete_zone(
            db=db, 
            zone_id=zone_id,
            distributor_id=distributor['user_id']  # Validate ownership
        )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )



