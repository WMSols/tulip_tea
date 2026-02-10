"""
Weekly Route Schedule repository.
Data access layer for WeeklyRouteSchedule operations.
"""
from sqlalchemy.orm import Session
from models.weekly_route_schedule import WeeklyRouteSchedule
from typing import Optional, List


class WeeklyRouteScheduleRepository:
    """Repository for WeeklyRouteSchedule database operations."""
    
    @staticmethod
    def create(db: Session, assignee_type: str, assignee_id: int, route_id: int,
              day_of_week: int, created_by_distributor: int, is_active: bool = True) -> WeeklyRouteSchedule:
        """Create a new weekly route schedule."""
        schedule = WeeklyRouteSchedule(
            assignee_type=assignee_type,
            assignee_id=assignee_id,
            route_id=route_id,
            day_of_week=day_of_week,
            created_by_distributor=created_by_distributor,
            is_active=is_active
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule
    
    @staticmethod
    def get_by_id(db: Session, schedule_id: int, include_deleted: bool = False) -> Optional[WeeklyRouteSchedule]:
        """Get schedule by ID (excludes soft-deleted by default)."""
        query = db.query(WeeklyRouteSchedule).filter(WeeklyRouteSchedule.id == schedule_id)
        if not include_deleted:
            query = query.filter(WeeklyRouteSchedule.deleted_at.is_(None))
        return query.first()
    
    @staticmethod
    def get_by_assignee(db: Session, assignee_type: str, assignee_id: int, 
                       include_deleted: bool = False, include_inactive: bool = False) -> List[WeeklyRouteSchedule]:
        """Get all schedules for an assignee (order_booker or delivery_man)."""
        query = db.query(WeeklyRouteSchedule).filter(
            WeeklyRouteSchedule.assignee_type == assignee_type,
            WeeklyRouteSchedule.assignee_id == assignee_id
        )
        if not include_deleted:
            query = query.filter(WeeklyRouteSchedule.deleted_at.is_(None))
        if not include_inactive:
            query = query.filter(WeeklyRouteSchedule.is_active == True)
        return query.order_by(WeeklyRouteSchedule.day_of_week).all()
    
    @staticmethod
    def get_by_assignee_and_day(db: Session, assignee_type: str, assignee_id: int, 
                                day_of_week: int, include_deleted: bool = False) -> List[WeeklyRouteSchedule]:
        """Get schedules for an assignee on a specific day of week."""
        query = db.query(WeeklyRouteSchedule).filter(
            WeeklyRouteSchedule.assignee_type == assignee_type,
            WeeklyRouteSchedule.assignee_id == assignee_id,
            WeeklyRouteSchedule.day_of_week == day_of_week
        )
        if not include_deleted:
            query = query.filter(WeeklyRouteSchedule.deleted_at.is_(None))
        return query.all()
    
    @staticmethod
    def get_by_distributor(db: Session, distributor_id: int, 
                          include_deleted: bool = False) -> List[WeeklyRouteSchedule]:
        """Get all schedules created by a distributor."""
        query = db.query(WeeklyRouteSchedule).filter(
            WeeklyRouteSchedule.created_by_distributor == distributor_id
        )
        if not include_deleted:
            query = query.filter(WeeklyRouteSchedule.deleted_at.is_(None))
        return query.order_by(WeeklyRouteSchedule.assignee_type, WeeklyRouteSchedule.assignee_id, 
                             WeeklyRouteSchedule.day_of_week).all()
    
    @staticmethod
    def get_by_route(db: Session, route_id: int, include_deleted: bool = False) -> List[WeeklyRouteSchedule]:
        """Get all schedules for a route."""
        query = db.query(WeeklyRouteSchedule).filter(WeeklyRouteSchedule.route_id == route_id)
        if not include_deleted:
            query = query.filter(WeeklyRouteSchedule.deleted_at.is_(None))
        return query.all()
    
    @staticmethod
    def get_active_schedules(db: Session, assignee_type: Optional[str] = None) -> List[WeeklyRouteSchedule]:
        """Get all active schedules (for task generation)."""
        query = db.query(WeeklyRouteSchedule).filter(
            WeeklyRouteSchedule.is_active == True,
            WeeklyRouteSchedule.deleted_at.is_(None)
        )
        if assignee_type:
            query = query.filter(WeeklyRouteSchedule.assignee_type == assignee_type)
        return query.all()
    
    @staticmethod
    def check_conflict(db: Session, assignee_type: str, assignee_id: int, route_id: int,
                      day_of_week: int, exclude_schedule_id: Optional[int] = None) -> Optional[WeeklyRouteSchedule]:
        """Check if a schedule already exists for the same assignee, route, and day."""
        query = db.query(WeeklyRouteSchedule).filter(
            WeeklyRouteSchedule.assignee_type == assignee_type,
            WeeklyRouteSchedule.assignee_id == assignee_id,
            WeeklyRouteSchedule.route_id == route_id,
            WeeklyRouteSchedule.day_of_week == day_of_week,
            WeeklyRouteSchedule.deleted_at.is_(None)
        )
        if exclude_schedule_id:
            query = query.filter(WeeklyRouteSchedule.id != exclude_schedule_id)
        return query.first()
    
    @staticmethod
    def update(db: Session, schedule_id: int, route_id: Optional[int] = None,
              day_of_week: Optional[int] = None, is_active: Optional[bool] = None) -> Optional[WeeklyRouteSchedule]:
        """Update schedule fields."""
        schedule = db.query(WeeklyRouteSchedule).filter(
            WeeklyRouteSchedule.id == schedule_id,
            WeeklyRouteSchedule.deleted_at.is_(None)
        ).first()
        if not schedule:
            return None
        
        if route_id is not None:
            schedule.route_id = route_id
        if day_of_week is not None:
            schedule.day_of_week = day_of_week
        if is_active is not None:
            schedule.is_active = is_active
        
        db.commit()
        db.refresh(schedule)
        return schedule
    
    @staticmethod
    def delete(db: Session, schedule_id: int) -> bool:
        """Soft delete a schedule (sets deleted_at timestamp)."""
        from datetime import datetime
        schedule = db.query(WeeklyRouteSchedule).filter(
            WeeklyRouteSchedule.id == schedule_id,
            WeeklyRouteSchedule.deleted_at.is_(None)
        ).first()
        if not schedule:
            return False
        schedule.deleted_at = datetime.utcnow()
        schedule.is_active = False
        db.commit()
        db.refresh(schedule)
        return True




