"""
Activity Log Repository
=======================
Data access layer for ActivityLog operations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.activity_log import ActivityLog
from typing import Optional, List, Dict, Any
from datetime import datetime


class ActivityLogRepository:
    """Repository for ActivityLog database operations."""
    
    @staticmethod
    def create(
        db: Session,
        user_id: Optional[int],
        user_role: str,
        action_type: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        user_name: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        changes_summary: Optional[str] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> ActivityLog:
        """
        Create a new activity log entry.
        
        Args:
            user_id: ID of the user (distributor_id, order_booker_id, or delivery_man_id)
            user_role: Role of the user ('distributor', 'order_booker', 'delivery_man', 'system')
            action_type: Type of action ('CREATE', 'UPDATE', 'DELETE', 'APPROVE', etc.)
            entity_type: Type of entity ('shop', 'order', 'payment', etc.)
            entity_id: ID of the affected entity
            user_name: Name of the user (optional, for quick access)
            old_values: Previous state (for UPDATE operations)
            new_values: New state (for CREATE/UPDATE operations)
            changes_summary: Human-readable summary of changes
            reason: Reason for the action
            notes: Additional notes
            status: Status of the action ('success', 'failure', 'pending')
            error_message: Error message if status is 'failure'
            metadata: Additional context data (JSONB)
            ip_address: IP address of the client
            user_agent: User agent string
            timestamp: Timestamp (defaults to now if not provided)
        
        Returns:
            ActivityLog: The created log entry
        """
        log = ActivityLog(
            user_id=user_id,
            user_role=user_role,
            user_name=user_name,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            changes_summary=changes_summary,
            reason=reason,
            notes=notes,
            status=status,
            error_message=error_message,
            additional_metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=timestamp or datetime.now()
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def get_by_id(db: Session, log_id: int) -> Optional[ActivityLog]:
        """Get activity log by ID."""
        return db.query(ActivityLog).filter(ActivityLog.id == log_id).first()
    
    @staticmethod
    def get_by_user(
        db: Session,
        user_id: int,
        user_role: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[ActivityLog]:
        """Get activity logs for a specific user."""
        return db.query(ActivityLog)\
            .filter(ActivityLog.user_id == user_id, ActivityLog.user_role == user_role)\
            .order_by(desc(ActivityLog.timestamp))\
            .limit(limit)\
            .offset(offset)\
            .all()
    
    @staticmethod
    def get_by_entity(
        db: Session,
        entity_type: str,
        entity_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[ActivityLog]:
        """Get activity logs for a specific entity."""
        return db.query(ActivityLog)\
            .filter(ActivityLog.entity_type == entity_type, ActivityLog.entity_id == entity_id)\
            .order_by(desc(ActivityLog.timestamp))\
            .limit(limit)\
            .offset(offset)\
            .all()
    
    @staticmethod
    def get_by_action_type(
        db: Session,
        action_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[ActivityLog]:
        """Get activity logs by action type."""
        return db.query(ActivityLog)\
            .filter(ActivityLog.action_type == action_type)\
            .order_by(desc(ActivityLog.timestamp))\
            .limit(limit)\
            .offset(offset)\
            .all()
    
    @staticmethod
    def get_recent(
        db: Session,
        limit: int = 100,
        offset: int = 0
    ) -> List[ActivityLog]:
        """Get recent activity logs."""
        return db.query(ActivityLog)\
            .order_by(desc(ActivityLog.timestamp))\
            .limit(limit)\
            .offset(offset)\
            .all()
    
    @staticmethod
    def get_failed_operations(
        db: Session,
        limit: int = 100,
        offset: int = 0
    ) -> List[ActivityLog]:
        """Get failed operations."""
        return db.query(ActivityLog)\
            .filter(ActivityLog.status == 'failure')\
            .order_by(desc(ActivityLog.timestamp))\
            .limit(limit)\
            .offset(offset)\
            .all()

