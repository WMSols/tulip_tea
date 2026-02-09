"""
Visit Task business logic service.
"""
from sqlalchemy.orm import Session
from repositories.visit_task_repository import VisitTaskRepository
from repositories.weekly_route_schedule_repository import WeeklyRouteScheduleRepository
from repositories.shop_repository import ShopRepository
from repositories.route_repository import RouteRepository
from repositories.order_booker_repository import OrderBookerRepository
from typing import Dict, List, Optional
from datetime import date, datetime, timedelta


class VisitTaskService:
    """Service for VisitTask business logic."""
    
    @staticmethod
    def generate_tasks_from_schedules(db: Session, weeks_ahead: int = 4,
                                     assignee_type: Optional[str] = None) -> Dict:
        """
        Generate visit tasks from active schedules for the next N weeks.
        
        Args:
            db: Database session
            weeks_ahead: Number of weeks to generate tasks for (default: 4)
            assignee_type: Optional filter by assignee_type ('order_booker' or 'delivery_man')
        
        Returns:
            Dict with count of tasks generated
        """
        # Get all active schedules
        schedules = WeeklyRouteScheduleRepository.get_active_schedules(db, assignee_type)
        
        if not schedules:
            return {"message": "No active schedules found", "tasks_generated": 0}
        
        # Calculate date range
        today = date.today()
        end_date = today + timedelta(weeks=weeks_ahead)
        
        tasks_created = []
        tasks_skipped = 0
        
        for schedule in schedules:
            # Get all shops in the route
            shops = ShopRepository.get_by_route(db, schedule.route_id)
            
            if not shops:
                continue  # No shops in route, skip
            
            # Generate tasks for each week in the range
            current_date = today
            while current_date <= end_date:
                # Check if this date matches the schedule's day of week
                if current_date.weekday() == schedule.day_of_week:
                    # Generate task for each shop
                    for shop in shops:
                        # Check if task already exists
                        existing = VisitTaskRepository.check_existing_task(
                            db, shop.id, current_date,
                            schedule.assignee_type, schedule.assignee_id
                        )
                        if existing:
                            tasks_skipped += 1
                            continue
                        
                        # Create task
                        task_data = {
                            'weekly_schedule_id': schedule.id,
                            'assignee_type': schedule.assignee_type,
                            'assignee_id': schedule.assignee_id,
                            'route_id': schedule.route_id,
                            'shop_id': shop.id,
                            'scheduled_date': current_date,
                            'day_of_week': schedule.day_of_week
                        }
                        tasks_created.append(task_data)
                
                current_date += timedelta(days=1)
        
        # Bulk create tasks
        if tasks_created:
            VisitTaskRepository.create_bulk(db, tasks_created)
        
        return {
            "message": f"Generated {len(tasks_created)} tasks, skipped {tasks_skipped} duplicates",
            "tasks_generated": len(tasks_created),
            "tasks_skipped": tasks_skipped
        }
    
    @staticmethod
    def get_tasks_for_order_booker(db: Session, order_booker_id: int,
                                   task_date: Optional[date] = None) -> List[Dict]:
        """
        Get tasks for an order booker, dynamically generated from schedules.
        Tasks are created on-demand (lazy creation) when viewing.
        This ensures schedules automatically recur every week without manual generation.
        """
        if not task_date:
            task_date = date.today()
        
        # Get active schedules for this order booker
        schedules = WeeklyRouteScheduleRepository.get_by_assignee(
            db, 'order_booker', order_booker_id, include_deleted=False, include_inactive=False
        )
        
        # Filter schedules that match the requested day of week
        matching_schedules = [
            s for s in schedules 
            if s.day_of_week == task_date.weekday()
        ]
        
        result = []
        for schedule in matching_schedules:
            # Get all shops in the route
            shops = ShopRepository.get_by_route(db, schedule.route_id)
            
            if not shops:
                continue  # No shops in route, skip
            
            for shop in shops:
                # Check if task already exists (for status tracking)
                existing_task = VisitTaskRepository.check_existing_task(
                    db, shop.id, task_date, 'order_booker', order_booker_id
                )
                
                # If no task exists, create one with 'pending' status (lazy creation)
                # This ensures we can track status changes later
                if not existing_task:
                    existing_task = VisitTaskRepository.create(
                        db,
                        weekly_schedule_id=schedule.id,
                        assignee_type='order_booker',
                        assignee_id=order_booker_id,
                        route_id=schedule.route_id,
                        shop_id=shop.id,
                        scheduled_date=task_date,
                        day_of_week=schedule.day_of_week
                    )
                
                route = RouteRepository.get_by_id(db, schedule.route_id)
                
                result.append({
                    "id": existing_task.id,
                    "shop_id": shop.id,
                    "shop_name": shop.name if shop else None,
                    "shop_owner": shop.owner_name if shop else None,
                    "shop_phone": shop.owner_phone if shop else None,
                    "shop_gps_lat": float(shop.gps_lat) if shop and shop.gps_lat else None,
                    "shop_gps_lng": float(shop.gps_lng) if shop and shop.gps_lng else None,
                    "route_id": schedule.route_id,
                    "route_name": route.name if route else None,
                    "scheduled_date": task_date.isoformat(),
                    "day_of_week": schedule.day_of_week,
                    "status": existing_task.status,
                    "shop_visit_id": existing_task.shop_visit_id,
                    "completed_at": existing_task.completed_at.isoformat() if existing_task.completed_at else None,
                    "notes": existing_task.notes,
                    "created_at": existing_task.created_at.isoformat() if existing_task.created_at else None,
                    "weekly_schedule_id": schedule.id
                })
        
        return result
    
    @staticmethod
    def get_tasks_for_order_booker_week(db: Session, order_booker_id: int,
                                       week_start: Optional[date] = None) -> List[Dict]:
        """
        Get tasks for an order booker for a week, dynamically generated from schedules.
        Tasks are created on-demand (lazy creation) when viewing.
        This ensures schedules automatically recur every week without manual generation.
        """
        if not week_start:
            # Default to current week (Monday)
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        # Get active schedules for this order booker
        schedules = WeeklyRouteScheduleRepository.get_by_assignee(
            db, 'order_booker', order_booker_id, include_deleted=False, include_inactive=False
        )
        
        result = []
        current_date = week_start
        
        # Generate tasks for each day in the week
        while current_date <= week_end:
            # Find schedules matching this day of week
            matching_schedules = [
                s for s in schedules 
                if s.day_of_week == current_date.weekday()
            ]
            
            for schedule in matching_schedules:
                shops = ShopRepository.get_by_route(db, schedule.route_id)
                
                if not shops:
                    continue  # No shops in route, skip
                
                for shop in shops:
                    # Check for existing task (for status tracking)
                    existing_task = VisitTaskRepository.check_existing_task(
                        db, shop.id, current_date, 'order_booker', order_booker_id
                    )
                    
                    # If no task exists, create one with 'pending' status (lazy creation)
                    if not existing_task:
                        existing_task = VisitTaskRepository.create(
                            db,
                            weekly_schedule_id=schedule.id,
                            assignee_type='order_booker',
                            assignee_id=order_booker_id,
                            route_id=schedule.route_id,
                            shop_id=shop.id,
                            scheduled_date=current_date,
                            day_of_week=schedule.day_of_week
                        )
                    
                    route = RouteRepository.get_by_id(db, schedule.route_id)
                    
                    result.append({
                        "id": existing_task.id,
                        "shop_id": shop.id,
                        "shop_name": shop.name if shop else None,
                        "shop_owner": shop.owner_name if shop else None,
                        "shop_phone": shop.owner_phone if shop else None,
                        "shop_gps_lat": float(shop.gps_lat) if shop and shop.gps_lat else None,
                        "shop_gps_lng": float(shop.gps_lng) if shop and shop.gps_lng else None,
                        "route_id": schedule.route_id,
                        "route_name": route.name if route else None,
                        "scheduled_date": current_date.isoformat(),
                        "day_of_week": schedule.day_of_week,
                        "status": existing_task.status,
                        "shop_visit_id": existing_task.shop_visit_id,
                        "completed_at": existing_task.completed_at.isoformat() if existing_task.completed_at else None,
                        "notes": existing_task.notes,
                        "created_at": existing_task.created_at.isoformat() if existing_task.created_at else None,
                        "weekly_schedule_id": schedule.id
                    })
            
            current_date += timedelta(days=1)
        
        return result
    
    @staticmethod
    def update_task_status(db: Session, task_id: int, status: str,
                          shop_visit_id: Optional[int] = None,
                          notes: Optional[str] = None) -> Dict:
        """Update task status."""
        valid_statuses = ['pending', 'in_progress', 'completed', 'skipped', 'cancelled']
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        
        task = VisitTaskRepository.get_by_id(db, task_id)
        if not task:
            raise ValueError("Task not found")
        
        updated = VisitTaskRepository.update_status(
            db, task_id, status, shop_visit_id, notes
        )
        if not updated:
            raise ValueError("Failed to update task")
        
        shop = ShopRepository.get_by_id(db, updated.shop_id)
        route = RouteRepository.get_by_id(db, updated.route_id)
        
        return {
            "id": updated.id,
            "shop_id": updated.shop_id,
            "shop_name": shop.name if shop else None,
            "route_id": updated.route_id,
            "route_name": route.name if route else None,
            "scheduled_date": updated.scheduled_date.isoformat() if updated.scheduled_date else None,
            "status": updated.status,
            "shop_visit_id": updated.shop_visit_id,
            "completed_at": updated.completed_at.isoformat() if updated.completed_at else None,
            "notes": updated.notes,
            "weekly_schedule_id": updated.weekly_schedule_id
        }




