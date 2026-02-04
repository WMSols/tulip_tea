"""
Visit Task repository.
Data access layer for VisitTask operations.
"""
from sqlalchemy.orm import Session
from models.visit_task import VisitTask
from typing import Optional, List
from datetime import date, datetime


class VisitTaskRepository:
    """Repository for VisitTask database operations."""
    
    @staticmethod
    def create(db: Session, weekly_schedule_id: int, assignee_type: str, assignee_id: int,
              route_id: int, shop_id: int, scheduled_date: date, day_of_week: int) -> VisitTask:
        """Create a new visit task."""
        task = VisitTask(
            weekly_schedule_id=weekly_schedule_id,
            assignee_type=assignee_type,
            assignee_id=assignee_id,
            route_id=route_id,
            shop_id=shop_id,
            scheduled_date=scheduled_date,
            day_of_week=day_of_week,
            status='pending'
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    
    @staticmethod
    def create_bulk(db: Session, tasks: List[dict]) -> List[VisitTask]:
        """Create multiple visit tasks in bulk."""
        task_objects = [
            VisitTask(
                weekly_schedule_id=task['weekly_schedule_id'],
                assignee_type=task['assignee_type'],
                assignee_id=task['assignee_id'],
                route_id=task['route_id'],
                shop_id=task['shop_id'],
                scheduled_date=task['scheduled_date'],
                day_of_week=task['day_of_week'],
                status='pending'
            )
            for task in tasks
        ]
        db.bulk_save_objects(task_objects)
        db.commit()
        return task_objects
    
    @staticmethod
    def get_by_id(db: Session, task_id: int, include_deleted: bool = False) -> Optional[VisitTask]:
        """Get task by ID (excludes soft-deleted by default)."""
        query = db.query(VisitTask).filter(VisitTask.id == task_id)
        if not include_deleted:
            query = query.filter(VisitTask.deleted_at.is_(None))
        return query.first()
    
    @staticmethod
    def get_by_assignee_and_date(db: Session, assignee_type: str, assignee_id: int,
                                 task_date: Optional[date] = None,
                                 include_deleted: bool = False) -> List[VisitTask]:
        """Get tasks for an assignee, optionally filtered by date."""
        query = db.query(VisitTask).filter(
            VisitTask.assignee_type == assignee_type,
            VisitTask.assignee_id == assignee_id
        )
        if task_date:
            query = query.filter(VisitTask.scheduled_date == task_date)
        if not include_deleted:
            query = query.filter(VisitTask.deleted_at.is_(None))
        return query.order_by(VisitTask.scheduled_date, VisitTask.route_id).all()
    
    @staticmethod
    def get_by_assignee_date_range(db: Session, assignee_type: str, assignee_id: int,
                                   start_date: date, end_date: date,
                                   include_deleted: bool = False) -> List[VisitTask]:
        """Get tasks for an assignee within a date range."""
        query = db.query(VisitTask).filter(
            VisitTask.assignee_type == assignee_type,
            VisitTask.assignee_id == assignee_id,
            VisitTask.scheduled_date >= start_date,
            VisitTask.scheduled_date <= end_date
        )
        if not include_deleted:
            query = query.filter(VisitTask.deleted_at.is_(None))
        return query.order_by(VisitTask.scheduled_date, VisitTask.route_id).all()
    
    @staticmethod
    def get_by_status(db: Session, assignee_type: str, assignee_id: int, status: str,
                    task_date: Optional[date] = None, include_deleted: bool = False) -> List[VisitTask]:
        """Get tasks by status for an assignee."""
        query = db.query(VisitTask).filter(
            VisitTask.assignee_type == assignee_type,
            VisitTask.assignee_id == assignee_id,
            VisitTask.status == status
        )
        if task_date:
            query = query.filter(VisitTask.scheduled_date == task_date)
        if not include_deleted:
            query = query.filter(VisitTask.deleted_at.is_(None))
        return query.order_by(VisitTask.scheduled_date).all()
    
    @staticmethod
    def get_by_shop_and_date(db: Session, shop_id: int, task_date: date,
                            include_deleted: bool = False) -> List[VisitTask]:
        """Get tasks for a shop on a specific date."""
        query = db.query(VisitTask).filter(
            VisitTask.shop_id == shop_id,
            VisitTask.scheduled_date == task_date
        )
        if not include_deleted:
            query = query.filter(VisitTask.deleted_at.is_(None))
        return query.all()
    
    @staticmethod
    def get_by_schedule(db: Session, weekly_schedule_id: int,
                       include_deleted: bool = False) -> List[VisitTask]:
        """Get all tasks generated from a schedule."""
        query = db.query(VisitTask).filter(VisitTask.weekly_schedule_id == weekly_schedule_id)
        if not include_deleted:
            query = query.filter(VisitTask.deleted_at.is_(None))
        return query.order_by(VisitTask.scheduled_date).all()
    
    @staticmethod
    def update_status(db: Session, task_id: int, status: str,
                     shop_visit_id: Optional[int] = None, notes: Optional[str] = None) -> Optional[VisitTask]:
        """Update task status and optionally link to shop_visit."""
        task = db.query(VisitTask).filter(
            VisitTask.id == task_id,
            VisitTask.deleted_at.is_(None)
        ).first()
        if not task:
            return None
        
        task.status = status
        if shop_visit_id is not None:
            task.shop_visit_id = shop_visit_id
        if notes is not None:
            task.notes = notes
        if status == 'completed':
            task.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(task)
        return task
    
    @staticmethod
    def delete_by_schedule(db: Session, weekly_schedule_id: int, 
                          before_date: Optional[date] = None) -> int:
        """Delete tasks generated from a schedule (soft delete)."""
        from datetime import datetime
        query = db.query(VisitTask).filter(
            VisitTask.weekly_schedule_id == weekly_schedule_id,
            VisitTask.deleted_at.is_(None)
        )
        if before_date:
            query = query.filter(VisitTask.scheduled_date < before_date)
        
        tasks = query.all()
        deleted_count = 0
        for task in tasks:
            task.deleted_at = datetime.utcnow()
            deleted_count += 1
        
        db.commit()
        return deleted_count
    
    @staticmethod
    def check_existing_task(db: Session, shop_id: int, scheduled_date: date,
                           assignee_type: str, assignee_id: int) -> Optional[VisitTask]:
        """Check if a task already exists for shop, date, and assignee."""
        return db.query(VisitTask).filter(
            VisitTask.shop_id == shop_id,
            VisitTask.scheduled_date == scheduled_date,
            VisitTask.assignee_type == assignee_type,
            VisitTask.assignee_id == assignee_id,
            VisitTask.deleted_at.is_(None)
        ).first()

