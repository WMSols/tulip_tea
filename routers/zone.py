"""
Zone router.
Handles zone CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict
from config.database import get_db
from models.schemas import ZoneCreate, ZoneUpdate, ZoneResponse
from services.zone_service import ZoneService
from utils.dependencies import get_current_user, get_current_distributor
from services.activity_log_service import ActivityLogService
from utils.auth_helpers import get_current_user_from_request

router = APIRouter(prefix="/zones", tags=["Zones"])


@router.post("/", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED, tags=["Zones", "Distributor APIs"])
async def create_zone(
    zone: ZoneCreate,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Create a new zone. Only distributors can create zones."""
    try:
        result = ZoneService.create_zone(db=db, name=zone.name)
        
        # Log creation
        ActivityLogService.log_create(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='zone',
            entity_id=result['id'],
            new_values={
                'name': result.get('name')
            },
            user_name=distributor.get('user_name'),
            changes_summary=f"Zone created: {result.get('name')}",
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            action_type='CREATE',
            entity_type='zone',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[ZoneResponse], tags=["Zones", "Distributor APIs", "Order Booker APIs"])
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


@router.put("/{zone_id}", response_model=ZoneResponse, tags=["Zones", "Distributor APIs"])
async def update_zone(
    zone_id: int,
    zone: ZoneUpdate,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Update zone name. Only distributors can update zones."""
    try:
        # Get old values
        from repositories.zone_repository import ZoneRepository
        old_zone = ZoneRepository.get_by_id(db, zone_id)
        old_values = {'name': old_zone.name} if old_zone else {}
        
        result = ZoneService.update_zone(db=db, zone_id=zone_id, name=zone.name)
        
        # Log update
        ActivityLogService.log_update(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='zone',
            entity_id=zone_id,
            old_values=old_values,
            new_values={'name': result.get('name')},
            user_name=distributor.get('user_name'),
            changes_summary=f"Zone updated: {old_values.get('name', 'N/A')} → {result.get('name')}",
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            action_type='UPDATE',
            entity_type='zone',
            entity_id=zone_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: int,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Delete a zone. Only distributors can delete zones."""
    try:
        # Get old values
        from repositories.zone_repository import ZoneRepository
        old_zone = ZoneRepository.get_by_id(db, zone_id)
        old_values = {'name': old_zone.name} if old_zone else {}
        
        ZoneService.delete_zone(db=db, zone_id=zone_id)
        
        # Log delete
        ActivityLogService.log_delete(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='zone',
            entity_id=zone_id,
            old_values=old_values,
            user_name=distributor.get('user_name'),
            changes_summary=f"Zone deleted: {old_values.get('name', 'N/A')}",
            request=request
        )
        
        return None
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            action_type='DELETE',
            entity_type='zone',
            entity_id=zone_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )



