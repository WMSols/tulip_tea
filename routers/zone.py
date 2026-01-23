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


@router.post("/", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(
    zone: ZoneCreate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Create a new zone. Only distributors can create zones."""
    try:
        result = ZoneService.create_zone(db=db, name=zone.name)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[ZoneResponse])
async def list_zones(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all zones. Requires authentication."""
    zones = ZoneService.get_all_zones(db=db)
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


@router.put("/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: int,
    zone: ZoneUpdate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Update zone name. Only distributors can update zones."""
    try:
        result = ZoneService.update_zone(db=db, zone_id=zone_id, name=zone.name)
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
    """Delete a zone. Only distributors can delete zones."""
    try:
        ZoneService.delete_zone(db=db, zone_id=zone_id)
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )



