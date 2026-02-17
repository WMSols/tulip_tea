"""
Visit Task Router
================
Handles visit task operations for order bookers and task generation for distributors.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import date
from config.database import get_db
from models.schemas import (
    VisitTaskResponse, VisitTaskStatusUpdate, TaskGenerationRequest
)
from services.visit_task_service import VisitTaskService
from utils.dependencies import get_current_user, get_current_distributor

router = APIRouter(prefix="/visit-tasks", tags=["Visit Tasks"])


@router.post("/generate", status_code=status.HTTP_200_OK, tags=["Visit Tasks", "Distributor APIs"])
async def generate_tasks(
    request: TaskGenerationRequest,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Generate visit tasks from active schedules. Only distributors can generate tasks."""
    try:
        result = VisitTaskService.generate_tasks_from_schedules(
            db=db,
            weeks_ahead=request.weeks_ahead or 4,
            assignee_type=request.assignee_type
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/order-booker/{order_booker_id}/today", response_model=List[VisitTaskResponse])
async def get_tasks_for_today(
    order_booker_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get today's tasks for an order booker."""
    # Verify order booker can only view their own tasks
    if current_user['user_role'] == 'order_booker' and current_user['user_id'] != order_booker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view tasks for your own account"
        )
    today = date.today()
    tasks = VisitTaskService.get_tasks_for_order_booker(
        db=db,
        order_booker_id=order_booker_id,
        task_date=today
    )
    return tasks


@router.get("/order-booker/{order_booker_id}/date/{task_date}", response_model=List[VisitTaskResponse])
async def get_tasks_for_date(
    order_booker_id: int,
    task_date: date,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get tasks for an order booker for a specific date."""
    # Verify order booker can only view their own tasks
    if current_user['user_role'] == 'order_booker' and current_user['user_id'] != order_booker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view tasks for your own account"
        )
    tasks = VisitTaskService.get_tasks_for_order_booker(
        db=db,
        order_booker_id=order_booker_id,
        task_date=task_date
    )
    return tasks


@router.get("/order-booker/{order_booker_id}/week", response_model=List[VisitTaskResponse])
async def get_tasks_for_week(
    order_booker_id: int,
    week_start: Optional[date] = Query(None, description="Week start date (Monday). Defaults to current week."),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get tasks for an order booker for a week."""
    # Verify order booker can only view their own tasks
    if current_user['user_role'] == 'order_booker' and current_user['user_id'] != order_booker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view tasks for your own account"
        )
    tasks = VisitTaskService.get_tasks_for_order_booker_week(
        db=db,
        order_booker_id=order_booker_id,
        week_start=week_start
    )
    return tasks


@router.get("/order-booker/{order_booker_id}/schedule-view", tags=["Visit Tasks", "Order Booker APIs"])
async def get_schedule_view(
    order_booker_id: int,
    date: Optional[date] = Query(None, description="Date to view schedule for (defaults to today)"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get schedule view for an order booker showing shops grouped by route with visit status.
    
    Returns shops scheduled for the specified date, grouped by route, with visit status
    (visited/pending) for each shop.
    """
    # If user is order booker, verify they can only view their own schedule
    if current_user.get('user_role') == 'order_booker':
        if current_user.get('user_id') != order_booker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own schedule"
            )
    
    try:
        result = VisitTaskService.get_schedule_view_data(
            db=db,
            order_booker_id=order_booker_id,
            view_date=date
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching schedule view: {str(e)}"
        )


@router.put("/{task_id}/status", response_model=VisitTaskResponse)
async def update_task_status(
    task_id: int,
    update: VisitTaskStatusUpdate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update task status. Order bookers can update their own tasks."""
    try:
        # Verify task exists and belongs to the user
        from repositories.visit_task_repository import VisitTaskRepository
        task = VisitTaskRepository.get_by_id(db, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # If user is order booker, verify they own this task
        if current_user.get('user_type') == 'order_booker':
            if task.assignee_type != 'order_booker' or task.assignee_id != current_user.get('user_id'):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own tasks"
                )
        
        result = VisitTaskService.update_task_status(
            db=db,
            task_id=task_id,
            status=update.status,
            shop_visit_id=update.shop_visit_id,
            notes=update.notes
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

