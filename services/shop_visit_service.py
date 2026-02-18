"""
Shop Visit Business Logic Service
==================================
Business logic layer for Shop Visit operations.

This service handles:
- Validation of visit data
- Business rules (e.g., GPS validation)
- Formatting responses
- Error handling

ARCHITECTURE:
Router → Service → Repository → Database

This layer:
- Receives requests from Router layer
- Validates business rules
- Calls Repository layer for database operations
- Formats data for responses
- Handles errors and raises appropriate exceptions
"""
from sqlalchemy.orm import Session
from repositories.shop_visit_repository import ShopVisitRepository
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.delivery_man_repository import DeliveryManRepository
from repositories.visit_type_repository import VisitTypeRepository
from repositories.order_repository import OrderRepository
from repositories.daily_collection_repository import DailyCollectionRepository
from services.image_service import ImageService
from services.order_service import OrderService
from services.daily_collection_service import DailyCollectionService
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime, date
import json


class ShopVisitService:
    """Service for Shop Visit business logic."""
    
    @staticmethod
    def _format_visit_data(db: Session, visit, include_linked_data: bool = True) -> Dict:
        """
        Helper method to format visit data consistently.
        
        Args:
            db: Database session
            visit: ShopVisit instance
            include_linked_data: Whether to include order_id and collection_id
        
        Returns:
            Dict: Formatted visit data
        """
        # Get shop name, zone, and routes
        shop_name = None
        shop_zone_id = None
        shop_routes = []
        if visit.shop_id:
            shop = ShopRepository.get_by_id(db, visit.shop_id)
            if shop:
                shop_name = shop.name
                shop_zone_id = shop.zone_id
                # Get shop route (using shop.route_id directly)
                from repositories.route_repository import RouteRepository
                if shop.route_id:
                    route = RouteRepository.get_by_id(db, shop.route_id)
                    if route:
                        shop_routes.append({
                            "route_id": route.id,
                            "route_name": route.name,
                            "zone_id": route.zone_id
                        })
        
        # Get order booker name
        order_booker_name = None
        if visit.order_booker_id:
            order_booker = OrderBookerRepository.get_by_id(db, visit.order_booker_id)
            order_booker_name = order_booker.name if order_booker else None
        
        # Get delivery man name
        delivery_man_name = None
        if visit.delivery_man_id:
            delivery_man = DeliveryManRepository.get_by_id(db, visit.delivery_man_id)
            delivery_man_name = delivery_man.name if delivery_man else None
        
        # Get visit types from junction table
        visit_types_list = [vt.visit_type for vt in VisitTypeRepository.get_by_visit(db, visit.id)]
        if not visit_types_list and visit.visit_type:
            # Fallback to legacy visit_type field
            visit_types_list = [visit.visit_type]
        
        # Get linked order and collection if requested
        order_id = None
        collection_id = None
        if include_linked_data:
            try:
                # Query only the ID to avoid enum serialization issues
                from models.order import Order
                order_id = db.query(Order.id).filter(Order.visit_id == visit.id).scalar()
            except Exception as e:
                print(f"Error fetching order ID for visit {visit.id}: {e}")
                import traceback
                traceback.print_exc()
                order_id = None
            
            try:
                # Query only the ID to avoid any serialization issues
                from models.daily_collection import DailyCollection
                collection_id = db.query(DailyCollection.id).filter(DailyCollection.visit_id == visit.id).scalar()
            except Exception as e:
                print(f"Error fetching collection ID for visit {visit.id}: {e}")
                import traceback
                traceback.print_exc()
                collection_id = None
        
        # Parse photos JSON string to list
        photos_list = []
        if visit.photos:
            try:
                import json
                if isinstance(visit.photos, str):
                    photos_list = json.loads(visit.photos)
                elif isinstance(visit.photos, list):
                    photos_list = visit.photos
            except Exception as e:
                print(f"Error parsing photos: {e}")
                photos_list = []
        
        return {
            "id": visit.id,
            "shop_id": visit.shop_id,
            "shop_name": shop_name,
            "shop_zone_id": shop_zone_id,
            "shop_routes": shop_routes,  # List of routes this shop belongs to
            "order_booker_id": visit.order_booker_id,
            "order_booker_name": order_booker_name,
            "delivery_man_id": visit.delivery_man_id,
            "delivery_man_name": delivery_man_name,
            "visit_types": visit_types_list,
            "gps_lat": float(visit.gps_lat) if visit.gps_lat else None,
            "gps_lng": float(visit.gps_lng) if visit.gps_lng else None,
            "visit_time": visit.visit_date.isoformat() if visit.visit_date else None,  # API uses visit_time for backward compatibility
            "photo": photos_list[0] if photos_list and len(photos_list) > 0 else None,  # Legacy single photo (first from array)
            "photos": photos_list,  # Multiple photos (JSON array)
            "reason": visit.remarks,  # Model uses 'remarks', API uses 'reason' for backward compatibility
            "order_id": order_id,
            "collection_id": collection_id
        }
    
    @staticmethod
    def register_visit(db: Session, shop_id: int = None, order_booker_id: int = None,
                      delivery_man_id: int = None, visit_types: List[str] = None,
                      gps_lat: float = None, gps_lng: float = None,
                      visit_time: str = None, photo: str = None,
                      reason: str = None, order_items: List[Dict] = None,
                      scheduled_date: str = None, collection_amount: float = None,
                      collection_remarks: str = None, final_total_amount: Decimal = None,
                      order_resolution_type: str = None, subsidy_id: int = None) -> Dict:
        """
        Register a new shop visit.
        
        FLOW:
        1. Validates that at least one of order_booker_id or delivery_man_id is provided
        2. Validates shop exists (if shop_id provided)
        3. Validates order booker exists (if order_booker_id provided)
        4. Converts GPS coordinates to Decimal
        5. Parses visit_time if provided
        6. Creates visit record
        7. Returns formatted visit data
        
        Args:
            db: Database session
            shop_id: Shop ID that was visited (optional)
            order_booker_id: Order booker ID who made the visit (optional)
            delivery_man_id: Delivery man ID who made the visit (optional)
            visit_type: Type of visit (e.g., "order_booking", "delivery", "collection")
            gps_lat: GPS latitude where visit was recorded
            gps_lng: GPS longitude where visit was recorded
            visit_time: Timestamp when visit occurred (ISO format string, optional)
            photo: Photo proof as base64 string or URL (optional)
            reason: Reason or notes for the visit (optional)
        
        Returns:
            Dict: Visit data with ID and timestamps
        
        Raises:
            ValueError: If validation fails
        """
        # Validate that at least one of order_booker_id or delivery_man_id is provided
        if not order_booker_id and not delivery_man_id:
            raise ValueError("Provide order booker ID or delivery man ID")
        
        # Validate shop exists and is approved if shop_id provided
        if shop_id:
            shop = ShopRepository.get_by_id(db, shop_id)
            if not shop:
                raise ValueError("Shop not found")
            # Only approved shops can have visits registered
            if shop.registration_status != "approved":
                raise ValueError(f"Shop is not approved. Status: {shop.registration_status}")
            
            # Validate GPS location if both shop and visit GPS coordinates are provided
            # This ensures order booker/delivery man is within 100m of shop location
            if shop.gps_lat and shop.gps_lng and gps_lat and gps_lng:
                from services.geolocation_service import GeolocationService
                is_valid, distance_km, message = GeolocationService.validate_visit_location(
                    target_lat=shop.gps_lat,
                    target_lng=shop.gps_lng,
                    visit_lat=Decimal(str(gps_lat)),
                    visit_lng=Decimal(str(gps_lng)),
                    entity_type="shop"
                )
                if not is_valid:
                    raise ValueError(message)
        
        # Validate order booker exists if order_booker_id provided
        if order_booker_id:
            order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
            if not order_booker:
                raise ValueError("Order booker not found")
        
        # Convert GPS coordinates to Decimal
        gps_lat_decimal = Decimal(str(gps_lat)) if gps_lat is not None else None
        gps_lng_decimal = Decimal(str(gps_lng)) if gps_lng is not None else None
        
        # Parse visit_time (required from frontend - API uses visit_time, model uses visit_date)
        if not visit_time:
            raise ValueError("visit_time is required")
        
        visit_date_datetime = None
        try:
            # Try parsing ISO format
            visit_date_datetime = datetime.fromisoformat(visit_time.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            raise ValueError("Invalid visit time format. Use ISO format: 2026-01-07T10:30:00")
        
        # Store original photo (base64) temporarily - we'll upload it after creating the visit
        photo_base64 = photo
        photo_url = None
        
        # Create visit (initially without photo URL if it's base64)
        # If photo is already a URL (not base64), use it directly
        if photo and not photo.startswith('data:image'):
            # Photo is already a URL
            photo_url = photo
        else:
            # Photo is base64, will upload after visit creation
            photo_url = None
        
        # Validate required fields based on visit types BEFORE creating visit
        if visit_types:
            # Check if any visit type requires shop_id
            visit_types_requiring_shop = ["order_booking", "daily_collections"]
            requires_shop = any(vt in visit_types_requiring_shop for vt in visit_types)
            
            if requires_shop and not shop_id:
                visit_type_names = ", ".join(visit_types_requiring_shop)
                raise ValueError(f"Shop ID is required for visit types: {visit_type_names}")
            
            # Validate order_booking specific requirements
            if "order_booking" in visit_types:
                if not shop_id:
                    raise ValueError("Shop ID is required for order booking")
                if not order_items or len(order_items) == 0:
                    raise ValueError("Order items are required for order booking")
            
            # Validate daily_collections specific requirements
            if "daily_collections" in visit_types:
                if not shop_id:
                    raise ValueError("Shop ID is required for daily collections")
                if not collection_amount or collection_amount <= 0:
                    raise ValueError("Collection amount must be greater than 0")
                if not order_booker_id:
                    raise ValueError("Order booker ID is required for daily collections")
        
        # Create visit (visit_type is deprecated, but keep for backward compatibility)
        # We'll use visit_types table instead
        visit_type_legacy = visit_types[0] if visit_types and len(visit_types) > 0 else None
        
        # Wrap all database operations in a single transaction to prevent partial execution
        # If any operation fails, all changes will be rolled back
        try:
            # Create visit (don't commit yet - auto_commit=False)
            visit = ShopVisitRepository.create(
                db=db,
                shop_id=shop_id,
                order_booker_id=order_booker_id,
                delivery_man_id=delivery_man_id,
                visit_type=visit_type_legacy,  # Keep for backward compatibility
                gps_lat=gps_lat_decimal,
                gps_lng=gps_lng_decimal,
                visit_date=visit_date_datetime,
                photo=photo_url,  # Will be None if base64, URL if already uploaded
                reason=reason,
                auto_commit=False  # Don't commit yet - wait for all operations
            )
            
            # Create visit types in junction table
            created_visit_types = []
            if visit_types:
                for vt in visit_types:
                    # Create visit type without committing (auto_commit=False)
                    # If this fails, the outer transaction will rollback everything
                    visit_type_obj = VisitTypeRepository.create(
                        db=db, 
                        visit_id=visit.id, 
                        visit_type=vt,
                        auto_commit=False  # Don't commit yet - wait for outer transaction
                    )
                    created_visit_types.append(vt)
            
            # Handle order_booking type - create order
            # Note: shop_id and order_items are already validated above before visit creation
            order_id = None
            if visit_types and "order_booking" in visit_types:
                
                # Parse scheduled_date if provided
                scheduled_date_obj = None
                if scheduled_date:
                    try:
                        scheduled_date_obj = datetime.fromisoformat(scheduled_date).date()
                    except (ValueError, AttributeError):
                        try:
                            scheduled_date_obj = date.fromisoformat(scheduled_date)
                        except (ValueError, AttributeError):
                            raise ValueError("Invalid scheduled date format. Use ISO format: 2026-01-10")
                
                # Get distributor_id from order_booker
                distributor_id = None
                if order_booker_id:
                    order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
                    if order_booker:
                        distributor_id = order_booker.distributor_id
                
                # Convert final_total_amount to Decimal if provided
                final_total_decimal = None
                if final_total_amount is not None:
                    final_total_decimal = Decimal(str(final_total_amount))
                
                # Create order (don't commit yet - auto_commit=False)
                order_data = OrderService.create_order(
                    db=db,
                    shop_id=shop_id,
                    order_booker_id=order_booker_id,
                    order_items=order_items,
                    distributor_id=distributor_id,
                    visit_id=visit.id,
                    scheduled_date=scheduled_date_obj,
                    final_total_amount=final_total_decimal,
                    order_resolution_type=order_resolution_type,
                    subsidy_id=subsidy_id,
                    auto_commit=False  # Don't commit yet - wait for all operations
                )
                order_id = order_data["id"]
            
            # Handle daily_collections type - create collection
            # Note: shop_id, collection_amount, and order_booker_id are already validated above before visit creation
            collection_id = None
            collection_credit_info = None  # Store collection credit info to include in response
            if visit_types and "daily_collections" in visit_types:
                
                # Create daily collection (don't commit yet - auto_commit=False)
                collection_data = DailyCollectionService.create_collection(
                    db=db,
                    shop_id=shop_id,
                    order_booker_id=order_booker_id,
                    amount=collection_amount,
                    collected_at=visit_date_datetime,
                    remarks=collection_remarks,
                    visit_id=visit.id,  # Link collection to visit directly
                    auto_commit=False  # Don't commit yet - wait for all operations
                )
                collection_id = collection_data["id"]
                
                # Store collection credit info to include in response
                collection_credit_info = {
                    "shop_outstanding_balance": collection_data.get("shop_outstanding_balance"),
                    "shop_credit_limit": collection_data.get("shop_credit_limit"),
                    "shop_available_credit": collection_data.get("shop_available_credit")
                }
            
            # Auto-link visit to visit task if shop_id and order_booker_id are provided
            visit_task_id = None
            if shop_id and order_booker_id:
                try:
                    from repositories.visit_task_repository import VisitTaskRepository
                    # Get the visit date (use visit_date if available, otherwise today)
                    visit_date_obj = visit_date_datetime.date() if visit_date_datetime else date.today()
                    
                    # Find matching visit task
                    matching_task = VisitTaskRepository.check_existing_task(
                        db=db,
                        shop_id=shop_id,
                        scheduled_date=visit_date_obj,
                        assignee_type='order_booker',
                        assignee_id=order_booker_id
                    )
                    
                    if matching_task and matching_task.status != 'completed':
                        # Link visit to task and mark as completed
                        VisitTaskRepository.update_status(
                            db=db,
                            task_id=matching_task.id,
                            status='completed',
                            shop_visit_id=visit.id,
                            notes=f"Auto-linked to visit {visit.id}"
                        )
                        visit_task_id = matching_task.id
                except Exception as e:
                    # Don't fail the visit registration if task linking fails
                    print(f"Warning: Failed to link visit to task: {e}")
            
            # Commit all database operations at once (atomic transaction)
            db.commit()
            
        except Exception as e:
            # Rollback all changes if any operation fails
            db.rollback()
            print(f"Error in register_visit transaction: {e}")
            raise
        
        # Upload photo to Supabase Storage if it's base64 (external operation, not part of transaction)
        # This happens after commit, so if it fails, the visit is still created
        if photo_base64 and photo_base64.startswith('data:image'):
            try:
                # Upload to Supabase Storage
                uploaded_url = ImageService.upload_shop_visit_photo(
                    visit_id=visit.id,
                    order_booker_id=order_booker_id,
                    delivery_man_id=delivery_man_id,
                    base64_image=photo_base64
                )
                
                if uploaded_url:
                    # Update visit with photo URL (store as JSON array in photos field)
                    import json
                    photos_list = []
                    if visit.photos:
                        try:
                            photos_list = json.loads(visit.photos) if isinstance(visit.photos, str) else visit.photos
                        except:
                            photos_list = []
                    photos_list.append(uploaded_url)
                    visit.photos = json.dumps(photos_list)
                    db.commit()
                    db.refresh(visit)
                    photo_url = uploaded_url
                else:
                    # Upload failed, but visit was created - log warning
                    print(f"Warning: Failed to upload visit photo for visit ID {visit.id}")
            except Exception as e:
                # Upload failed, but visit was created - log error
                print(f"Error uploading visit photo: {e}")
                # Visit is still created, just without photo URL
        
        # Format and return visit data
        result = ShopVisitService._format_visit_data(db, visit, include_linked_data=True)
        
        # Include collection credit info if collection was created
        if collection_credit_info:
            result.update(collection_credit_info)
        
        # Include visit_task_id if visit was linked to a task
        if visit_task_id:
            result['visit_task_id'] = visit_task_id
        
        return result
    
    @staticmethod
    def get_visits_by_order_booker(db: Session, order_booker_id: int,
                                   skip: int = 0, limit: int = 100) -> List[Dict]:
        """
        Get all visits made by an order booker.
        
        FLOW:
        1. Gets visits from repository
        2. Batch loads all related data (shops, order bookers, delivery men, routes, etc.)
        3. Returns formatted list
        
        Args:
            db: Database session
            order_booker_id: Order booker ID
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[Dict]: List of visits with shop and order booker info
        """
        visits = ShopVisitRepository.get_by_order_booker(db, order_booker_id, skip, limit)
        
        if not visits:
            return []
        
        # Batch load all related data to avoid N+1 queries
        visit_ids = [visit.id for visit in visits]
        shop_ids = list(set([visit.shop_id for visit in visits if visit.shop_id]))
        order_booker_ids = list(set([visit.order_booker_id for visit in visits if visit.order_booker_id]))
        delivery_man_ids = list(set([visit.delivery_man_id for visit in visits if visit.delivery_man_id]))
        
        # Batch load shops
        shops = {}
        if shop_ids:
            shops_list = ShopRepository.get_by_ids(db, shop_ids)
            shops = {s.id: s for s in shops_list}
        
        # Batch load order bookers
        order_bookers = {}
        if order_booker_ids:
            order_bookers_list = OrderBookerRepository.get_by_ids(db, order_booker_ids)
            order_bookers = {ob.id: ob for ob in order_bookers_list}
        
        # Batch load delivery men
        delivery_men = {}
        if delivery_man_ids:
            delivery_men_list = DeliveryManRepository.get_by_ids(db, delivery_man_ids)
            delivery_men = {dm.id: dm for dm in delivery_men_list}
        
        # Batch load routes (for shops)
        route_ids = list(set([shop.route_id for shop in shops.values() if shop.route_id]))
        routes = {}
        if route_ids:
            from repositories.route_repository import RouteRepository
            routes_list = RouteRepository.get_by_ids(db, route_ids)
            routes = {r.id: r for r in routes_list}
        
        # Batch load visit types
        from repositories.visit_type_repository import VisitTypeRepository
        visit_types_map = {}
        if visit_ids:
            all_visit_types = VisitTypeRepository.get_by_visits(db, visit_ids)
            for vt in all_visit_types:
                if vt.visit_id not in visit_types_map:
                    visit_types_map[vt.visit_id] = []
                visit_types_map[vt.visit_id].append(vt.visit_type)
        
        # Batch load orders (for visit_id lookup)
        from models.order import Order
        orders_map = {}
        if visit_ids:
            orders = db.query(Order.id, Order.visit_id).filter(Order.visit_id.in_(visit_ids)).all()
            for order_id, visit_id in orders:
                orders_map[visit_id] = order_id
        
        # Batch load collections (for visit_id lookup)
        from models.daily_collection import DailyCollection
        collections_map = {}
        if visit_ids:
            collections = db.query(DailyCollection.id, DailyCollection.visit_id).filter(DailyCollection.visit_id.in_(visit_ids)).all()
            for collection_id, visit_id in collections:
                collections_map[visit_id] = collection_id
        
        # Format visits using batch-loaded data
        result = []
        for visit in visits:
            # Get shop data from batch-loaded shops
            shop = shops.get(visit.shop_id) if visit.shop_id else None
            shop_name = shop.name if shop else None
            shop_zone_id = shop.zone_id if shop else None
            
            # Get route data from batch-loaded routes
            shop_routes = []
            if shop and shop.route_id and shop.route_id in routes:
                route = routes[shop.route_id]
                shop_routes.append({
                    "route_id": route.id,
                    "route_name": route.name,
                    "zone_id": route.zone_id
                })
            
            # Get order booker name from batch-loaded order bookers
            order_booker_name = None
            if visit.order_booker_id and visit.order_booker_id in order_bookers:
                order_booker_name = order_bookers[visit.order_booker_id].name
            
            # Get delivery man name from batch-loaded delivery men
            delivery_man_name = None
            if visit.delivery_man_id and visit.delivery_man_id in delivery_men:
                delivery_man_name = delivery_men[visit.delivery_man_id].name
            
            # Get visit types from batch-loaded visit types
            visit_types_list = visit_types_map.get(visit.id, [])
            if not visit_types_list and visit.visit_type:
                # Fallback to legacy visit_type field
                visit_types_list = [visit.visit_type]
            
            # Get linked order and collection IDs from batch-loaded data
            order_id = orders_map.get(visit.id)
            collection_id = collections_map.get(visit.id)
            
            # Parse photos JSON string to list
            photos_list = []
            if visit.photos:
                try:
                    import json
                    if isinstance(visit.photos, str):
                        photos_list = json.loads(visit.photos)
                    elif isinstance(visit.photos, list):
                        photos_list = visit.photos
                except Exception as e:
                    print(f"Error parsing photos: {e}")
                    photos_list = []
            
            result.append({
                "id": visit.id,
                "shop_id": visit.shop_id,
                "shop_name": shop_name,
                "shop_zone_id": shop_zone_id,
                "shop_routes": shop_routes,
                "order_booker_id": visit.order_booker_id,
                "order_booker_name": order_booker_name,
                "delivery_man_id": visit.delivery_man_id,
                "delivery_man_name": delivery_man_name,
                "visit_types": visit_types_list,
                "gps_lat": float(visit.gps_lat) if visit.gps_lat else None,
                "gps_lng": float(visit.gps_lng) if visit.gps_lng else None,
                "visit_time": visit.visit_date.isoformat() if visit.visit_date else None,  # API uses visit_time for backward compatibility
                "photo": photos_list[0] if photos_list and len(photos_list) > 0 else None,  # Legacy single photo (first from array)
                "photos": photos_list,  # Multiple photos (JSON array)
                "reason": visit.remarks,  # Model uses 'remarks', API uses 'reason' for backward compatibility
                "order_id": order_id,
                "collection_id": collection_id
            })
        
        return result
    
    @staticmethod
    def get_visits_by_shop(db: Session, shop_id: int,
                           skip: int = 0, limit: int = 100) -> List[Dict]:
        """
        Get all visits to a specific shop.
        
        FLOW:
        1. Gets visits from repository
        2. For each visit, fetches shop and order booker/delivery man information
        3. Returns formatted list
        
        Args:
            db: Database session
            shop_id: Shop ID
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[Dict]: List of visits with shop and visitor info
        """
        visits = ShopVisitRepository.get_by_shop(db, shop_id, skip, limit)
        
        # Batch load all shops, order bookers, and delivery men to avoid N+1 queries
        shop_ids = list(set([visit.shop_id for visit in visits if visit.shop_id]))
        order_booker_ids = list(set([visit.order_booker_id for visit in visits if visit.order_booker_id]))
        delivery_man_ids = list(set([visit.delivery_man_id for visit in visits if visit.delivery_man_id]))
        
        # Batch load shops
        shops = {}
        if shop_ids:
            shops_list = ShopRepository.get_by_ids(db, shop_ids)
            shops = {s.id: s for s in shops_list}
        
        # Batch load order bookers
        order_bookers = {}
        if order_booker_ids:
            order_bookers_list = OrderBookerRepository.get_by_ids(db, order_booker_ids)
            order_bookers = {ob.id: ob for ob in order_bookers_list}
        
        # Batch load delivery men
        delivery_men = {}
        if delivery_man_ids:
            delivery_men_list = DeliveryManRepository.get_by_ids(db, delivery_man_ids)
            delivery_men = {dm.id: dm for dm in delivery_men_list}
        
        result = []
        for visit in visits:
            # Use batch-loaded data instead of individual queries
            # The _format_visit_data method will use the visit object which already has relationships
            # But we need to ensure the related objects are available in the session
            result.append(ShopVisitService._format_visit_data(db, visit, include_linked_data=True))
        
        return result
    
    @staticmethod
    def get_all_visits(db: Session, distributor_id: int = None, skip: int = 0, limit: int = 1000) -> List[Dict]:
        """
        Get all shop visits with shop and visitor information.
        OPTIMIZED: Uses batch loading to avoid N+1 queries.
        
        FLOW:
        1. Gets all visits from repository (1 query)
        2. If distributor_id is provided, filters to visits by order bookers/delivery men belonging to this distributor
        3. Batch loads all related data (shops, routes, order bookers, delivery men, visit types, orders, collections)
        4. Formats visits using pre-loaded data (no additional queries)
        
        Args:
            db: Database session
            distributor_id: Optional distributor ID to filter visits
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[Dict]: List of visits with shop, visitor, zone info, and linked order/collection IDs
        """
        if distributor_id:
            # OPTIMIZED: Filter visits by distributor using JOINs (more efficient than subqueries)
            from models.order_booker import OrderBooker
            from models.delivery_man import DeliveryMan
            from models.shop_visit import ShopVisit
            from sqlalchemy import or_
            
            # Use JOINs to filter visits by order bookers/delivery men belonging to this distributor
            # This is more efficient than subqueries + IN clauses
            visits = db.query(ShopVisit).join(
                OrderBooker,
                (ShopVisit.order_booker_id == OrderBooker.id) &
                (OrderBooker.distributor_id == distributor_id) &
                (OrderBooker.deleted_at.is_(None)) &
                (OrderBooker.is_active == True),
                isouter=True
            ).join(
                DeliveryMan,
                (ShopVisit.delivery_man_id == DeliveryMan.id) &
                (DeliveryMan.distributor_id == distributor_id) &
                (DeliveryMan.deleted_at.is_(None)) &
                (DeliveryMan.is_active == True),
                isouter=True
            ).filter(
                or_(
                    OrderBooker.id.isnot(None),
                    DeliveryMan.id.isnot(None)
                )
            ).order_by(ShopVisit.visit_date.desc()).offset(skip).limit(limit).all()
        else:
            visits = ShopVisitRepository.get_all(db, skip, limit)
        
        if not visits:
            return []
        
        # Batch load all related data in single queries to avoid N+1 problem
        from models.shop import Shop
        from models.order_booker import OrderBooker
        from models.delivery_man import DeliveryMan
        from models.route import Route
        from models.order import Order
        from models.daily_collection import DailyCollection
        from models.visit_type import VisitType
        
        # Collect all unique IDs
        shop_ids = list(set([v.shop_id for v in visits if v.shop_id]))
        order_booker_ids = list(set([v.order_booker_id for v in visits if v.order_booker_id]))
        delivery_man_ids = list(set([v.delivery_man_id for v in visits if v.delivery_man_id]))
        visit_ids = [v.id for v in visits]
        
        # Batch load shops (1 query for all shops)
        shops = {}
        if shop_ids:
            shops_query = db.query(Shop).filter(Shop.id.in_(shop_ids)).all()
            shops = {shop.id: shop for shop in shops_query}
        
        # Batch load routes (get all routes for shops that have route_id)
        routes = {}
        route_ids = list(set([s.route_id for s in shops.values() if s.route_id]))
        if route_ids:
            routes_query = db.query(Route).filter(Route.id.in_(route_ids)).all()
            routes = {route.id: route for route in routes_query}
        
        # Batch load order bookers (1 query for all order bookers)
        order_bookers = {}
        if order_booker_ids:
            ob_query = db.query(OrderBooker).filter(OrderBooker.id.in_(order_booker_ids)).all()
            order_bookers = {ob.id: ob for ob in ob_query}
        
        # Batch load delivery men (1 query for all delivery men)
        delivery_men = {}
        if delivery_man_ids:
            dm_query = db.query(DeliveryMan).filter(DeliveryMan.id.in_(delivery_man_ids)).all()
            delivery_men = {dm.id: dm for dm in dm_query}
        
        # Batch load visit types for all visits (1 query for all visit types)
        visit_types_map = {}
        if visit_ids:
            visit_types = db.query(VisitType).filter(VisitType.visit_id.in_(visit_ids)).all()
            for vt in visit_types:
                if vt.visit_id not in visit_types_map:
                    visit_types_map[vt.visit_id] = []
                visit_types_map[vt.visit_id].append(vt.visit_type)
        
        # Batch load order IDs (1 query for all orders linked to visits)
        orders_map = {}
        if visit_ids:
            orders_query = db.query(Order.visit_id, Order.id).filter(
                Order.visit_id.in_(visit_ids),
                Order.visit_id.isnot(None)
            ).all()
            for visit_id, order_id in orders_query:
                orders_map[visit_id] = order_id
        
        # Batch load collection IDs (1 query for all collections linked to visits)
        collections_map = {}
        if visit_ids:
            collections_query = db.query(DailyCollection.visit_id, DailyCollection.id).filter(
                DailyCollection.visit_id.in_(visit_ids),
                DailyCollection.visit_id.isnot(None)
            ).all()
            for visit_id, collection_id in collections_query:
                collections_map[visit_id] = collection_id
        
        # Format visits using pre-loaded data (no additional queries)
        result = []
        for visit in visits:
            # Get shop info from batch-loaded data
            shop_name = None
            shop_zone_id = None
            shop_routes = []
            if visit.shop_id and visit.shop_id in shops:
                shop = shops[visit.shop_id]
                shop_name = shop.name
                shop_zone_id = shop.zone_id
                if shop.route_id and shop.route_id in routes:
                    route = routes[shop.route_id]
                    shop_routes.append({
                        "route_id": route.id,
                        "route_name": route.name,
                        "zone_id": route.zone_id
                    })
            
            # Get order booker name from batch-loaded data
            order_booker_name = None
            if visit.order_booker_id and visit.order_booker_id in order_bookers:
                order_booker_name = order_bookers[visit.order_booker_id].name
            
            # Get delivery man name from batch-loaded data
            delivery_man_name = None
            if visit.delivery_man_id and visit.delivery_man_id in delivery_men:
                delivery_man_name = delivery_men[visit.delivery_man_id].name
            
            # Get visit types from batch-loaded data
            visit_types_list = visit_types_map.get(visit.id, [])
            if not visit_types_list and visit.visit_type:
                # Fallback to legacy visit_type field
                visit_types_list = [visit.visit_type]
            
            # Get linked order and collection IDs from batch-loaded data
            order_id = orders_map.get(visit.id)
            collection_id = collections_map.get(visit.id)
            
            # Parse photos JSON string to list
            photos_list = []
            if visit.photos:
                try:
                    import json
                    if isinstance(visit.photos, str):
                        photos_list = json.loads(visit.photos)
                    elif isinstance(visit.photos, list):
                        photos_list = visit.photos
                except Exception as e:
                    print(f"Error parsing photos: {e}")
                    photos_list = []
            
            result.append({
                "id": visit.id,
                "shop_id": visit.shop_id,
                "shop_name": shop_name,
                "shop_zone_id": shop_zone_id,
                "shop_routes": shop_routes,
                "order_booker_id": visit.order_booker_id,
                "order_booker_name": order_booker_name,
                "delivery_man_id": visit.delivery_man_id,
                "delivery_man_name": delivery_man_name,
                "visit_types": visit_types_list,
                "gps_lat": float(visit.gps_lat) if visit.gps_lat else None,
                "gps_lng": float(visit.gps_lng) if visit.gps_lng else None,
                "visit_time": visit.visit_date.isoformat() if visit.visit_date else None,
                "photo": photos_list[0] if photos_list and len(photos_list) > 0 else None,
                "photos": photos_list,
                "reason": visit.remarks,
                "order_id": order_id,
                "collection_id": collection_id
            })
        
        return result

