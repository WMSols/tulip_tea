"""
Zone router.
Handles zone CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import ZoneCreate, ZoneResponse
from services.zone_service import ZoneService

router = APIRouter(prefix="/zones", tags=["Zones"])


@router.post("/", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(zone: ZoneCreate, db: Session = Depends(get_db)):
    """Create a new zone."""
    try:
        result = ZoneService.create_zone(db=db, name=zone.name)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[ZoneResponse])
async def list_zones(db: Session = Depends(get_db)):
    """List all zones."""
    zones = ZoneService.get_all_zones(db=db)
    return zones


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(zone_id: int, db: Session = Depends(get_db)):
    """Get zone by ID."""
    try:
        zone = ZoneService.get_zone_by_id(db=db, zone_id=zone_id)
        return zone
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(zone_id: int, db: Session = Depends(get_db)):
    """Delete a zone."""
    try:
        ZoneService.delete_zone(db=db, zone_id=zone_id)
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

