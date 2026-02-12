"""
Weekly Route Schedule business logic service.
"""
from sqlalchemy.orm import Session
from repositories.weekly_route_schedule_repository import WeeklyRouteScheduleRepository
from repositories.route_repository import RouteRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.distributor_repository import DistributorRepository
from repositories.shop_repository import ShopRepository
from typing import Dict, List, Optional


class WeeklyRouteScheduleService:
    """Service for WeeklyRouteSchedule business logic."""
    
    @staticmethod
    def create_schedule(db: Session, assignee_type: str, assignee_id: int, route_id: int,
                       day_of_week: int, distributor_id: int) -> Dict:
        """Create a new weekly route schedule."""
        # Validate assignee_type
        if assignee_type not in ['order_booker', 'delivery_man']:
            raise ValueError("assignee_type must be 'order_booker' or 'delivery_man'")
        
        # Validate day_of_week
        if day_of_week < 0 or day_of_week > 6:
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday)")
        
        # Verify distributor exists
        distributor = DistributorRepository.get_by_id(db, distributor_id)
        if not distributor:
            raise ValueError("Distributor not found")
        
        # Verify route exists
        route = RouteRepository.get_by_id(db, route_id)
        if not route:
            raise ValueError("Route not found")
        
        # Verify assignee exists and belongs to distributor
        if assignee_type == 'order_booker':
            assignee = OrderBookerRepository.get_by_id(db, assignee_id)
            if not assignee:
                raise ValueError("Order Booker not found")
            if assignee.distributor_id != distributor_id:
                raise ValueError("Order Booker does not belong to this distributor")
            
            # Validate that route is assigned to this order booker
            # Order bookers can only be scheduled on routes that are already assigned to them
            if route.order_booker_id != assignee_id:
                raise ValueError(
                    f"Cannot create schedule: Route '{route.name}' (ID: {route_id}) is not assigned to "
                    f"order booker '{assignee.name}' (ID: {assignee_id}). "
                    f"Only routes assigned to the order booker can be scheduled."
                )
        else:
            # For delivery_man, we'll add validation later
            # For now, just check if it exists
            from repositories.delivery_man_repository import DeliveryManRepository
            assignee = DeliveryManRepository.get_by_id(db, assignee_id)
            if not assignee:
                raise ValueError("Delivery Man not found")
            if assignee.distributor_id != distributor_id:
                raise ValueError("Delivery Man does not belong to this distributor")
        
        # Check for conflicts (same assignee, route, and day)
        existing = WeeklyRouteScheduleRepository.check_conflict(
            db, assignee_type, assignee_id, route_id, day_of_week
        )
        if existing:
            raise ValueError(
                f"Schedule already exists for {assignee_type} {assignee_id} "
                f"on route {route_id} for day {day_of_week}"
            )
        
        # Create schedule
        schedule = WeeklyRouteScheduleRepository.create(
            db=db,
            assignee_type=assignee_type,
            assignee_id=assignee_id,
            route_id=route_id,
            day_of_week=day_of_week,
            created_by_distributor=distributor_id
        )
        
        # Get denormalized names
        route_name = route.name
        assignee_name = assignee.name if assignee else None
        
        return {
            "id": schedule.id,
            "assignee_type": schedule.assignee_type,
            "assignee_id": schedule.assignee_id,
            "assignee_name": assignee_name,
            "route_id": schedule.route_id,
            "route_name": route_name,
            "day_of_week": schedule.day_of_week,
            "is_active": schedule.is_active,
            "created_by_distributor": schedule.created_by_distributor,
            "created_at": schedule.created_at.isoformat() if schedule.created_at else None
        }
    
    @staticmethod
    def get_schedules_by_order_booker(db: Session, order_booker_id: int) -> List[Dict]:
        """
        Get all schedules for an order booker.
        OPTIMIZED: Uses batch loading to avoid N+1 queries.
        """
        schedules = WeeklyRouteScheduleRepository.get_by_assignee(
            db, 'order_booker', order_booker_id
        )
        
        if not schedules:
            return []
        
        # Batch load all routes (1 query instead of N queries)
        from models.route import Route
        route_ids = list(set([schedule.route_id for schedule in schedules if schedule.route_id]))
        routes_map = {}
        if route_ids:
            routes = db.query(Route).filter(Route.id.in_(route_ids)).all()
            routes_map = {route.id: route for route in routes}
        
        # Batch load order booker (already have order_booker_id, but get it once)
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        order_booker_name = order_booker.name if order_booker else None
        
        # Build result using lookup map (no additional queries)
        result = []
        for schedule in schedules:
            route = routes_map.get(schedule.route_id) if schedule.route_id else None
            
            result.append({
                "id": schedule.id,
                "assignee_type": schedule.assignee_type,
                "assignee_id": schedule.assignee_id,
                "assignee_name": order_booker_name,
                "route_id": schedule.route_id,
                "route_name": route.name if route else None,
                "day_of_week": schedule.day_of_week,
                "is_active": schedule.is_active,
                "created_by_distributor": schedule.created_by_distributor,
                "created_at": schedule.created_at.isoformat() if schedule.created_at else None
            })
        
        return result
    
    @staticmethod
    def get_schedules_by_distributor(db: Session, distributor_id: int) -> List[Dict]:
        """
        Get all schedules created by a distributor.
        OPTIMIZED: Uses batch loading to avoid N+1 queries.
        """
        schedules = WeeklyRouteScheduleRepository.get_by_distributor(db, distributor_id)
        
        if not schedules:
            return []
        
        # Batch load all routes (1 query instead of N queries)
        from models.route import Route
        route_ids = list(set([schedule.route_id for schedule in schedules if schedule.route_id]))
        routes_map = {}
        if route_ids:
            routes = db.query(Route).filter(Route.id.in_(route_ids)).all()
            routes_map = {route.id: route for route in routes}
        
        # Batch load all order bookers (1 query instead of N queries)
        from models.order_booker import OrderBooker
        order_booker_ids = list(set([
            schedule.assignee_id for schedule in schedules 
            if schedule.assignee_type == 'order_booker' and schedule.assignee_id
        ]))
        order_bookers_map = {}
        if order_booker_ids:
            order_bookers = db.query(OrderBooker).filter(OrderBooker.id.in_(order_booker_ids)).all()
            order_bookers_map = {ob.id: ob for ob in order_bookers}
        
        # Batch load all delivery men (1 query instead of N queries)
        from models.delivery_man import DeliveryMan
        delivery_man_ids = list(set([
            schedule.assignee_id for schedule in schedules 
            if schedule.assignee_type == 'delivery_man' and schedule.assignee_id
        ]))
        delivery_men_map = {}
        if delivery_man_ids:
            delivery_men = db.query(DeliveryMan).filter(DeliveryMan.id.in_(delivery_man_ids)).all()
            delivery_men_map = {dm.id: dm for dm in delivery_men}
        
        # Build result using lookup maps (no additional queries)
        result = []
        for schedule in schedules:
            route = routes_map.get(schedule.route_id) if schedule.route_id else None
            
            assignee_name = None
            if schedule.assignee_type == 'order_booker' and schedule.assignee_id:
                assignee = order_bookers_map.get(schedule.assignee_id)
                assignee_name = assignee.name if assignee else None
            elif schedule.assignee_type == 'delivery_man' and schedule.assignee_id:
                assignee = delivery_men_map.get(schedule.assignee_id)
                assignee_name = assignee.name if assignee else None
            
            result.append({
                "id": schedule.id,
                "assignee_type": schedule.assignee_type,
                "assignee_id": schedule.assignee_id,
                "assignee_name": assignee_name,
                "route_id": schedule.route_id,
                "route_name": route.name if route else None,
                "day_of_week": schedule.day_of_week,
                "is_active": schedule.is_active,
                "created_by_distributor": schedule.created_by_distributor,
                "created_at": schedule.created_at.isoformat() if schedule.created_at else None
            })
        
        return result
    
    @staticmethod
    def update_schedule(db: Session, schedule_id: int, route_id: Optional[int] = None,
                       day_of_week: Optional[int] = None, is_active: Optional[bool] = None) -> Dict:
        """Update a schedule."""
        schedule = WeeklyRouteScheduleRepository.get_by_id(db, schedule_id)
        if not schedule:
            raise ValueError("Schedule not found")
        
        # Validate day_of_week if provided
        if day_of_week is not None and (day_of_week < 0 or day_of_week > 6):
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday)")
        
        # If updating route_id, validate that route is assigned to the order booker
        if route_id is not None and schedule.assignee_type == 'order_booker':
            new_route = RouteRepository.get_by_id(db, route_id)
            if not new_route:
                raise ValueError("Route not found")
            
            # Validate that the new route is assigned to this order booker
            if new_route.order_booker_id != schedule.assignee_id:
                order_booker = OrderBookerRepository.get_by_id(db, schedule.assignee_id)
                order_booker_name = order_booker.name if order_booker else f"ID {schedule.assignee_id}"
                raise ValueError(
                    f"Cannot update schedule: Route '{new_route.name}' (ID: {route_id}) is not assigned to "
                    f"order booker '{order_booker_name}' (ID: {schedule.assignee_id}). "
                    f"Only routes assigned to the order booker can be scheduled."
                )
        
        # Check for conflicts if updating route or day
        if route_id is not None or day_of_week is not None:
            final_route_id = route_id if route_id is not None else schedule.route_id
            final_day = day_of_week if day_of_week is not None else schedule.day_of_week
            
            existing = WeeklyRouteScheduleRepository.check_conflict(
                db, schedule.assignee_type, schedule.assignee_id,
                final_route_id, final_day, exclude_schedule_id=schedule_id
            )
            if existing:
                raise ValueError(
                    f"Schedule already exists for {schedule.assignee_type} {schedule.assignee_id} "
                    f"on route {final_route_id} for day {final_day}"
                )
        
        # Update schedule
        updated = WeeklyRouteScheduleRepository.update(
            db, schedule_id, route_id=route_id, day_of_week=day_of_week, is_active=is_active
        )
        if not updated:
            raise ValueError("Failed to update schedule")
        
        # Get denormalized names
        route = RouteRepository.get_by_id(db, updated.route_id)
        route_name = route.name if route else None
        
        assignee_name = None
        if updated.assignee_type == 'order_booker':
            assignee = OrderBookerRepository.get_by_id(db, updated.assignee_id)
            assignee_name = assignee.name if assignee else None
        else:
            from repositories.delivery_man_repository import DeliveryManRepository
            assignee = DeliveryManRepository.get_by_id(db, updated.assignee_id)
            assignee_name = assignee.name if assignee else None
        
        return {
            "id": updated.id,
            "assignee_type": updated.assignee_type,
            "assignee_id": updated.assignee_id,
            "assignee_name": assignee_name,
            "route_id": updated.route_id,
            "route_name": route_name,
            "day_of_week": updated.day_of_week,
            "is_active": updated.is_active,
            "created_by_distributor": updated.created_by_distributor,
            "created_at": updated.created_at.isoformat() if updated.created_at else None
        }
    
    @staticmethod
    def delete_schedule(db: Session, schedule_id: int) -> bool:
        """Delete a schedule."""
        schedule = WeeklyRouteScheduleRepository.get_by_id(db, schedule_id)
        if not schedule:
            raise ValueError("Schedule not found")
        
        return WeeklyRouteScheduleRepository.delete(db, schedule_id)




