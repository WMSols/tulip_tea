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
        """Get tasks for an order booker, optionally filtered by date."""
        tasks = VisitTaskRepository.get_by_assignee_and_date(
            db, 'order_booker', order_booker_id, task_date
        )
        
        result = []
        for task in tasks:
            shop = ShopRepository.get_by_id(db, task.shop_id)
            route = RouteRepository.get_by_id(db, task.route_id)
            
            result.append({
                "id": task.id,
                "shop_id": task.shop_id,
                "shop_name": shop.name if shop else None,
                "shop_owner": shop.owner_name if shop else None,
                "shop_phone": shop.owner_phone if shop else None,
                "shop_gps_lat": float(shop.gps_lat) if shop and shop.gps_lat else None,
                "shop_gps_lng": float(shop.gps_lng) if shop and shop.gps_lng else None,
                "route_id": task.route_id,
                "route_name": route.name if route else None,
                "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
                "day_of_week": task.day_of_week,
                "status": task.status,
                "shop_visit_id": task.shop_visit_id,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "notes": task.notes,
                "created_at": task.created_at.isoformat() if task.created_at else None
            })
        
        return result
    
    @staticmethod
    def get_tasks_for_order_booker_week(db: Session, order_booker_id: int,
                                       week_start: Optional[date] = None) -> List[Dict]:
        """Get tasks for an order booker for a week."""
        if not week_start:
            # Default to current week (Monday)
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        tasks = VisitTaskRepository.get_by_assignee_date_range(
            db, 'order_booker', order_booker_id, week_start, week_end
        )
        
        result = []
        for task in tasks:
            shop = ShopRepository.get_by_id(db, task.shop_id)
            route = RouteRepository.get_by_id(db, task.route_id)
            
            result.append({
                "id": task.id,
                "shop_id": task.shop_id,
                "shop_name": shop.name if shop else None,
                "shop_owner": shop.owner_name if shop else None,
                "shop_phone": shop.owner_phone if shop else None,
                "shop_gps_lat": float(shop.gps_lat) if shop and shop.gps_lat else None,
                "shop_gps_lng": float(shop.gps_lng) if shop and shop.gps_lng else None,
                "route_id": task.route_id,
                "route_name": route.name if route else None,
                "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
                "day_of_week": task.day_of_week,
                "status": task.status,
                "shop_visit_id": task.shop_visit_id,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "notes": task.notes,
                "created_at": task.created_at.isoformat() if task.created_at else None
            })
        
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
            "notes": updated.notes
        }




