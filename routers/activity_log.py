"""
Activity Log Router
===================
Handles API endpoints for activity logs.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from config.database import get_db
from repositories.activity_log_repository import ActivityLogRepository
from models.schemas import ActivityLogResponse

router = APIRouter(prefix="/activity-logs", tags=["Activity Logs"])


@router.get("/", response_model=List[ActivityLogResponse])
async def get_activity_logs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    user_role: Optional[str] = Query(None, description="Filter by user role"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    Get activity logs with optional filters.
    
    API: GET /activity-logs?skip=0&limit=100&user_id=1&user_role=distributor&action_type=CREATE&entity_type=shop&status=success
    
    Query Parameters:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return (1-1000)
        user_id: Filter by user ID
        user_role: Filter by user role (distributor, order_booker, delivery_man, system, super_admin)
        action_type: Filter by action type (CREATE, UPDATE, DELETE, APPROVE, REJECT, LOGIN, etc.)
        entity_type: Filter by entity type (shop, order, payment, etc.)
        entity_id: Filter by entity ID
        status: Filter by status (success, failure, pending)
    
    Response (200):
        List of activity log entries
    """
    try:
        from sqlalchemy import and_
        from models.activity_log import ActivityLog
        from sqlalchemy import desc
        
        # Build query with filters
        query = db.query(ActivityLog)
        
        # Apply filters
        filters = []
        if user_id is not None:
            filters.append(ActivityLog.user_id == user_id)
        if user_role:
            filters.append(ActivityLog.user_role == user_role)
        if action_type:
            filters.append(ActivityLog.action_type == action_type)
        if entity_type:
            filters.append(ActivityLog.entity_type == entity_type)
        if entity_id is not None:
            filters.append(ActivityLog.entity_id == entity_id)
        if status_filter:
            filters.append(ActivityLog.status == status_filter)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(desc(ActivityLog.timestamp))
        
        # Apply pagination
        logs = query.offset(skip).limit(limit).all()
        
        # Format response
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "user_id": log.user_id,
                "user_role": log.user_role,
                "user_name": log.user_name,
                "action_type": log.action_type,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "user_agent": log.user_agent,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "changes_summary": log.changes_summary,
                "reason": log.reason,
                "notes": log.notes,
                "status": log.status,
                "error_message": log.error_message,
                "metadata": log.additional_metadata
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching activity logs: {str(e)}"
        )


@router.get("/recent", response_model=List[ActivityLogResponse])
async def get_recent_logs(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get recent activity logs (most recent first).
    
    API: GET /activity-logs/recent?limit=50
    
    Response (200):
        List of recent activity log entries
    """
    try:
        logs = ActivityLogRepository.get_recent(db=db, limit=limit, offset=0)
        
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "user_id": log.user_id,
                "user_role": log.user_role,
                "user_name": log.user_name,
                "action_type": log.action_type,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "user_agent": log.user_agent,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "changes_summary": log.changes_summary,
                "reason": log.reason,
                "notes": log.notes,
                "status": log.status,
                "error_message": log.error_message,
                "metadata": log.additional_metadata
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching recent activity logs: {str(e)}"
        )


@router.get("/failed", response_model=List[ActivityLogResponse])
async def get_failed_logs(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get failed activity logs (operations that failed).
    
    API: GET /activity-logs/failed?limit=50
    
    Response (200):
        List of failed activity log entries
    """
    try:
        logs = ActivityLogRepository.get_failed_operations(db=db, limit=limit, offset=0)
        
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "user_id": log.user_id,
                "user_role": log.user_role,
                "user_name": log.user_name,
                "action_type": log.action_type,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "user_agent": log.user_agent,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "changes_summary": log.changes_summary,
                "reason": log.reason,
                "notes": log.notes,
                "status": log.status,
                "error_message": log.error_message,
                "metadata": log.additional_metadata
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching failed activity logs: {str(e)}"
        )


@router.get("/{log_id}", response_model=ActivityLogResponse)
async def get_activity_log(
    log_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific activity log by ID.
    
    API: GET /activity-logs/{log_id}
    
    Response (200):
        Activity log entry
    """
    try:
        log = ActivityLogRepository.get_by_id(db=db, log_id=log_id)
        
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity log with ID {log_id} not found"
            )
        
        return {
            "id": log.id,
            "user_id": log.user_id,
            "user_role": log.user_role,
            "user_name": log.user_name,
            "action_type": log.action_type,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "ip_address": str(log.ip_address) if log.ip_address else None,
            "user_agent": log.user_agent,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "changes_summary": log.changes_summary,
            "reason": log.reason,
            "notes": log.notes,
            "status": log.status,
            "error_message": log.error_message,
            "metadata": log.additional_metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching activity log: {str(e)}"
        )

