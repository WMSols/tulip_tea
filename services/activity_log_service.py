"""
Activity Log Service
====================
Business logic layer for activity logging.
"""
from sqlalchemy.orm import Session
from repositories.activity_log_repository import ActivityLogRepository
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Request


class ActivityLogService:
    """Service for activity logging business logic."""
    
    @staticmethod
    def log_activity(
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
        request: Optional[Request] = None
    ) -> None:
        """
        Universal method to log any activity.
        
        This method should be used throughout the application to log all operations.
        It handles errors gracefully to ensure logging failures don't break the application.
        
        Args:
            db: Database session
            user_id: ID of the user performing the action
            user_role: Role of the user
            action_type: Type of action (CREATE, UPDATE, DELETE, APPROVE, etc.)
            entity_type: Type of entity (shop, order, payment, etc.)
            entity_id: ID of the affected entity
            user_name: Name of the user (optional)
            old_values: Previous state (for updates)
            new_values: New state (for creates/updates)
            changes_summary: Human-readable summary
            reason: Reason for the action
            notes: Additional notes
            status: Status ('success', 'failure', 'pending')
            error_message: Error message if failed
            metadata: Additional context data
            request: FastAPI Request object (for IP and user agent)
        """
        try:
            # Extract IP and user agent from request if provided
            ip_address = None
            user_agent = None
            if request:
                if request.client:
                    ip_address = request.client.host
                user_agent = request.headers.get('user-agent')
            
            ActivityLogRepository.create(
                db=db,
                user_id=user_id,
                user_role=user_role,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                user_name=user_name,
                old_values=old_values,
                new_values=new_values,
                changes_summary=changes_summary,
                reason=reason,
                notes=notes,
                status=status,
                error_message=error_message,
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            # Logging failures should not break the application
            # Print error for debugging but don't raise
            print(f"⚠️ Failed to log activity: {e}")
            import traceback
            traceback.print_exc()
    
    @staticmethod
    def log_create(
        db: Session,
        user_id: Optional[int],
        user_role: str,
        entity_type: str,
        entity_id: int,
        new_values: Dict[str, Any],
        user_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> None:
        """Helper method to log CREATE operations."""
        ActivityLogService.log_activity(
            db=db,
            user_id=user_id,
            user_role=user_role,
            action_type='CREATE',
            entity_type=entity_type,
            entity_id=entity_id,
            user_name=user_name,
            new_values=new_values,
            metadata=metadata,
            request=request
        )
    
    @staticmethod
    def log_update(
        db: Session,
        user_id: Optional[int],
        user_role: str,
        entity_type: str,
        entity_id: int,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        changes_summary: Optional[str] = None,
        user_name: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> None:
        """Helper method to log UPDATE operations."""
        ActivityLogService.log_activity(
            db=db,
            user_id=user_id,
            user_role=user_role,
            action_type='UPDATE',
            entity_type=entity_type,
            entity_id=entity_id,
            user_name=user_name,
            old_values=old_values,
            new_values=new_values,
            changes_summary=changes_summary,
            reason=reason,
            metadata=metadata,
            request=request
        )
    
    @staticmethod
    def log_delete(
        db: Session,
        user_id: Optional[int],
        user_role: str,
        entity_type: str,
        entity_id: int,
        old_values: Dict[str, Any],
        user_name: Optional[str] = None,
        reason: Optional[str] = None,
        request: Optional[Request] = None
    ) -> None:
        """Helper method to log DELETE operations."""
        ActivityLogService.log_activity(
            db=db,
            user_id=user_id,
            user_role=user_role,
            action_type='DELETE',
            entity_type=entity_type,
            entity_id=entity_id,
            user_name=user_name,
            old_values=old_values,
            reason=reason,
            request=request
        )
    
    @staticmethod
    def log_approve(
        db: Session,
        user_id: Optional[int],
        user_role: str,
        entity_type: str,
        entity_id: int,
        old_values: Optional[Dict[str, Any]],
        new_values: Optional[Dict[str, Any]],
        changes_summary: Optional[str] = None,
        user_name: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> None:
        """Helper method to log APPROVE operations."""
        ActivityLogService.log_activity(
            db=db,
            user_id=user_id,
            user_role=user_role,
            action_type='APPROVE',
            entity_type=entity_type,
            entity_id=entity_id,
            user_name=user_name,
            old_values=old_values,
            new_values=new_values,
            changes_summary=changes_summary,
            reason=reason,
            metadata=metadata,
            request=request
        )
    
    @staticmethod
    def log_reject(
        db: Session,
        user_id: Optional[int],
        user_role: str,
        entity_type: str,
        entity_id: int,
        old_values: Optional[Dict[str, Any]],
        new_values: Optional[Dict[str, Any]],
        changes_summary: Optional[str] = None,
        user_name: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> None:
        """Helper method to log REJECT operations."""
        ActivityLogService.log_activity(
            db=db,
            user_id=user_id,
            user_role=user_role,
            action_type='REJECT',
            entity_type=entity_type,
            entity_id=entity_id,
            user_name=user_name,
            old_values=old_values,
            new_values=new_values,
            changes_summary=changes_summary,
            reason=reason,
            metadata=metadata,
            request=request
        )
    
    @staticmethod
    def log_login(
        db: Session,
        user_id: int,
        user_role: str,
        user_name: Optional[str] = None,
        request: Optional[Request] = None
    ) -> None:
        """Helper method to log LOGIN operations."""
        ActivityLogService.log_activity(
            db=db,
            user_id=user_id,
            user_role=user_role,
            action_type='LOGIN',
            entity_type='user',
            entity_id=user_id,
            user_name=user_name,
            request=request
        )
    
    @staticmethod
    def log_failure(
        db: Session,
        user_id: Optional[int],
        user_role: str,
        action_type: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        error_message: str = None,
        user_name: Optional[str] = None,
        request: Optional[Request] = None
    ) -> None:
        """Helper method to log failed operations."""
        ActivityLogService.log_activity(
            db=db,
            user_id=user_id,
            user_role=user_role,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_name=user_name,
            status='failure',
            error_message=error_message,
            request=request
        )






