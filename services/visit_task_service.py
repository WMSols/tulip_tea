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
    
    @staticmethod
    def get_schedule_view_data(db: Session, order_booker_id: int, 
                               view_date: Optional[date] = None) -> Dict:
        """
        Get schedule view data for an order booker showing shops grouped by route with visit status.
        
        This method:
        1. Gets active schedules for the order booker for the specified date's day of week
        2. For each schedule, gets all shops in the route
        3. For each shop, checks if a visit_task exists and its status
        4. Returns data grouped by route with visit status for each shop
        
        Args:
            db: Database session
            order_booker_id: Order booker ID
            view_date: Date to view schedule for (defaults to today)
        
        Returns:
            Dict with routes, shops, and visit status
        """
        if not view_date:
            view_date = date.today()
        
        day_of_week = view_date.weekday()  # 0=Monday, 6=Sunday
        
        # Get active schedules for this order booker for today's day of week
        schedules = WeeklyRouteScheduleRepository.get_by_assignee_and_day(
            db, 'order_booker', order_booker_id, day_of_week
        )
        
        # Filter to only active schedules
        active_schedules = [s for s in schedules if s.is_active and s.deleted_at is None]
        
        if not active_schedules:
            return {
                "date": view_date.isoformat(),
                "day_of_week": day_of_week,
                "routes": [],
                "summary": {
                    "total_shops": 0,
                    "visited_shops": 0,
                    "remaining_shops": 0
                }
            }
        
        # Get all route IDs
        route_ids = [s.route_id for s in active_schedules]
        
        # Get all shops for these routes (batch load to avoid N+1)
        all_shops = []
        route_shops_map = {}  # route_id -> [shops]
        
        for route_id in route_ids:
            shops = ShopRepository.get_by_route(db, route_id)
            route_shops_map[route_id] = shops
            all_shops.extend(shops)
        
        # Get all shop IDs
        shop_ids = [shop.id for shop in all_shops] if all_shops else []
        
        # Batch load visit tasks for today (or create them if they don't exist - lazy creation)
        tasks_by_shop = {}
        if shop_ids:
            tasks = VisitTaskRepository.get_by_assignee_and_date(
                db, 'order_booker', order_booker_id, view_date
            )
            # Filter to only tasks for shops in our routes
            tasks = [t for t in tasks if t.shop_id in shop_ids]
            tasks_by_shop = {task.shop_id: task for task in tasks}
            
            # For shops without tasks, create them on-the-fly (lazy creation)
            shops_without_tasks = [shop_id for shop_id in shop_ids if shop_id not in tasks_by_shop]
            if shops_without_tasks:
                # Create tasks for shops that don't have them yet
                # Use a set to track which shops we've already created tasks for (avoid duplicates)
                shops_processed = set()
                new_tasks = []
                
                for schedule in active_schedules:
                    route_shops = route_shops_map.get(schedule.route_id, [])
                    for shop in route_shops:
                        if shop.id in shops_without_tasks and shop.id not in shops_processed:
                            # Check if task already exists (race condition check)
                            existing = VisitTaskRepository.check_existing_task(
                                db, shop.id, view_date, 'order_booker', order_booker_id
                            )
                            if not existing:
                                task_data = {
                                    'weekly_schedule_id': schedule.id,
                                    'assignee_type': 'order_booker',
                                    'assignee_id': order_booker_id,
                                    'route_id': schedule.route_id,
                                    'shop_id': shop.id,
                                    'scheduled_date': view_date,
                                    'day_of_week': day_of_week
                                }
                                new_tasks.append(task_data)
                                shops_processed.add(shop.id)
                
                if new_tasks:
                    # Bulk create new tasks
                    created_tasks = VisitTaskRepository.create_bulk(db, new_tasks)
                    # Re-query to get all tasks including newly created ones
                    tasks = VisitTaskRepository.get_by_assignee_and_date(
                        db, 'order_booker', order_booker_id, view_date
                    )
                    tasks = [t for t in tasks if t.shop_id in shop_ids]
                    tasks_by_shop = {task.shop_id: task for task in tasks}
        
        # Build response grouped by route
        routes_data = []
        total_shops = 0
        visited_shops = 0
        
        # Create a map of schedule_id -> route_id for quick lookup
        schedule_route_map = {s.id: s.route_id for s in active_schedules}
        
        # Group schedules by route_id
        routes_schedules_map = {}
        for schedule in active_schedules:
            if schedule.route_id not in routes_schedules_map:
                routes_schedules_map[schedule.route_id] = []
            routes_schedules_map[schedule.route_id].append(schedule)
        
        for route_id, schedules_for_route in routes_schedules_map.items():
            route = RouteRepository.get_by_id(db, route_id)
            if not route:
                continue
            
            shops_in_route = route_shops_map.get(route_id, [])
            shops_data = []
            route_visited = 0
            
            for shop in shops_in_route:
                task = tasks_by_shop.get(shop.id)
                task_status = 'pending'
                task_id = None
                shop_visit_id = None
                visited_at = None
                
                if task:
                    task_id = task.id
                    task_status = task.status
                    shop_visit_id = task.shop_visit_id
                    if task.completed_at:
                        visited_at = task.completed_at.isoformat()
                
                shops_data.append({
                    "shop_id": shop.id,
                    "shop_name": shop.name,
                    "shop_owner": shop.owner_name,
                    "shop_phone": shop.owner_phone,
                    "shop_gps_lat": float(shop.gps_lat) if shop.gps_lat else None,
                    "shop_gps_lng": float(shop.gps_lng) if shop.gps_lng else None,
                    "task_id": task_id,
                    "status": task_status,
                    "shop_visit_id": shop_visit_id,
                    "visited_at": visited_at
                })
                
                if task_status == 'completed':
                    route_visited += 1
                    visited_shops += 1
                
                total_shops += 1
            
            routes_data.append({
                "route_id": route_id,
                "route_name": route.name if route else f"Route {route_id}",
                "shops": shops_data,
                "visited_count": route_visited,
                "total_count": len(shops_data)
            })
        
        return {
            "date": view_date.isoformat(),
            "day_of_week": day_of_week,
            "routes": routes_data,
            "summary": {
                "total_shops": total_shops,
                "visited_shops": visited_shops,
                "remaining_shops": total_shops - visited_shops
            }
        }




