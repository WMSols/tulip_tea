"""
Weekly Route Schedule Router
============================
Handles weekly route schedule CRUD operations for distributors.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import (
    WeeklyRouteScheduleCreate, WeeklyRouteScheduleUpdate, WeeklyRouteScheduleResponse
)
from services.weekly_route_schedule_service import WeeklyRouteScheduleService
from utils.dependencies import get_current_distributor, get_current_user
from typing import Dict
from services.activity_log_service import ActivityLogService

router = APIRouter(prefix="/weekly-route-schedules", tags=["Weekly Route Schedules"])


@router.post("/distributor/{distributor_id}", response_model=WeeklyRouteScheduleResponse, status_code=status.HTTP_201_CREATED, tags=["Weekly Route Schedules", "Distributor APIs"])
async def create_schedule(
    distributor_id: int,
    schedule: WeeklyRouteScheduleCreate,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Create a new weekly route schedule. Only distributors can create schedules."""
    # Verify distributor can only create schedules for their own account
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create schedules for your own distributor account"
        )
    
    try:
        result = WeeklyRouteScheduleService.create_schedule(
            db=db,
            assignee_type=schedule.assignee_type,
            assignee_id=schedule.assignee_id,
            route_id=schedule.route_id,
            day_of_week=schedule.day_of_week,
            distributor_id=distributor_id
        )
        
        # Log creation
        ActivityLogService.log_create(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='weekly_route_schedule',
            entity_id=result['id'],
            new_values={
                'assignee_type': result.get('assignee_type'),
                'assignee_id': result.get('assignee_id'),
                'route_id': result.get('route_id'),
                'day_of_week': result.get('day_of_week'),
                'is_active': result.get('is_active', True)
            },
            user_name=distributor.get('user_name'),
            changes_summary=f"Weekly route schedule created: {result.get('day_of_week')} for route {result.get('route_id')}",
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
            entity_type='weekly_route_schedule',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor.get('user_id'),
            user_role='distributor',
            action_type='CREATE',
            entity_type='weekly_route_schedule',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating schedule: {str(e)}"
        )


@router.get("/distributor/{distributor_id}", response_model=List[WeeklyRouteScheduleResponse], tags=["Weekly Route Schedules", "Distributor APIs"])
async def list_schedules_by_distributor(
    distributor_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """List all schedules created by a distributor."""
    # Verify distributor can only view their own schedules
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view schedules for your own distributor account"
        )
    
    schedules = WeeklyRouteScheduleService.get_schedules_by_distributor(db=db, distributor_id=distributor_id)
    return schedules


@router.get("/order-booker/{order_booker_id}", response_model=List[WeeklyRouteScheduleResponse], tags=["Weekly Route Schedules", "Order Booker APIs"])
async def list_schedules_by_order_booker(
    order_booker_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all schedules for an order booker. 
    Order bookers can only view their own schedules.
    Distributors can view any order booker's schedules.
    """
    # If user is order booker, they can only view their own schedule
    if current_user['user_role'] == 'order_booker':
        if current_user['user_id'] != order_booker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own schedule"
            )
    # Distributors can view any order booker's schedule
    
    schedules = WeeklyRouteScheduleService.get_schedules_by_order_booker(db=db, order_booker_id=order_booker_id)
    return schedules


@router.put("/{schedule_id}", response_model=WeeklyRouteScheduleResponse, tags=["Weekly Route Schedules", "Distributor APIs"])
async def update_schedule(
    schedule_id: int,
    schedule: WeeklyRouteScheduleUpdate,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Update a weekly route schedule. Only distributors can update schedules."""
    try:
        # Verify schedule exists and belongs to distributor
        from repositories.weekly_route_schedule_repository import WeeklyRouteScheduleRepository
        existing_schedule = WeeklyRouteScheduleRepository.get_by_id(db, schedule_id)
        if not existing_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )
        
        if existing_schedule.created_by_distributor != distributor['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update schedules that you created"
            )
        
        # Get old values
        old_values = {
            'route_id': existing_schedule.route_id,
            'day_of_week': existing_schedule.day_of_week,
            'is_active': existing_schedule.is_active
        }
        
        result = WeeklyRouteScheduleService.update_schedule(
            db=db,
            schedule_id=schedule_id,
            route_id=schedule.route_id,
            day_of_week=schedule.day_of_week,
            is_active=schedule.is_active
        )
        
        # Log update
        ActivityLogService.log_update(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='weekly_route_schedule',
            entity_id=schedule_id,
            old_values=old_values,
            new_values={
                'route_id': result.get('route_id'),
                'day_of_week': result.get('day_of_week'),
                'is_active': result.get('is_active', True)
            },
            user_name=distributor.get('user_name'),
            changes_summary=f"Weekly route schedule updated: {result.get('day_of_week')}",
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
            entity_type='weekly_route_schedule',
            entity_id=schedule_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Delete a weekly route schedule. Only distributors can delete schedules."""
    try:
        # Verify schedule exists and belongs to distributor
        from repositories.weekly_route_schedule_repository import WeeklyRouteScheduleRepository
        existing_schedule = WeeklyRouteScheduleRepository.get_by_id(db, schedule_id)
        if not existing_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )
        
        if existing_schedule.created_by_distributor != distributor['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete schedules that you created"
            )
        
        # Get old values
        old_values = {
            'route_id': existing_schedule.route_id,
            'day_of_week': existing_schedule.day_of_week,
            'is_active': existing_schedule.is_active
        }
        
        WeeklyRouteScheduleService.delete_schedule(db=db, schedule_id=schedule_id)
        
        # Log delete
        ActivityLogService.log_delete(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='weekly_route_schedule',
            entity_id=schedule_id,
            old_values=old_values,
            user_name=distributor.get('user_name'),
            changes_summary=f"Weekly route schedule deleted: {existing_schedule.day_of_week}",
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
            entity_type='weekly_route_schedule',
            entity_id=schedule_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

