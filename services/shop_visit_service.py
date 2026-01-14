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
                # Get shop routes
                from models.route_shop import RouteShop
                from repositories.route_repository import RouteRepository
                route_shops = db.query(RouteShop).filter(RouteShop.shop_id == shop.id).all()
                for route_shop in route_shops:
                    route = RouteRepository.get_by_id(db, route_shop.route_id)
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
            orders = OrderRepository.get_by_visit(db, visit.id)
            order_id = orders[0].id if orders else None
            
            from models.daily_collection import DailyCollection
            collections = db.query(DailyCollection).filter(DailyCollection.visit_id == visit.id).all()
            collection_id = collections[0].id if collections else None
        
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
            "visit_time": visit.visit_time.isoformat() if visit.visit_time else None,
            "photo": visit.photo,  # Legacy single photo
            "photos": photos_list,  # Multiple photos (JSON array)
            "reason": visit.reason,
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
                      collection_remarks: str = None) -> Dict:
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
            raise ValueError("Either order_booker_id or delivery_man_id must be provided")
        
        # Validate shop exists and is approved if shop_id provided
        if shop_id:
            shop = ShopRepository.get_by_id(db, shop_id)
            if not shop:
                raise ValueError("Shop not found")
            # Only approved shops can have visits registered
            if shop.registration_status != "approved":
                raise ValueError(f"Visits can only be registered for approved shops. This shop status is: {shop.registration_status}")
        
        # Validate order booker exists if order_booker_id provided
        if order_booker_id:
            order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
            if not order_booker:
                raise ValueError("Order Booker not found")
        
        # Convert GPS coordinates to Decimal
        gps_lat_decimal = Decimal(str(gps_lat)) if gps_lat is not None else None
        gps_lng_decimal = Decimal(str(gps_lng)) if gps_lng is not None else None
        
        # Parse visit_time if provided
        visit_time_datetime = None
        if visit_time:
            try:
                # Try parsing ISO format
                visit_time_datetime = datetime.fromisoformat(visit_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError("Invalid visit_time format. Use ISO format (e.g., 2026-01-07T10:30:00)")
        
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
        
        # Create visit (visit_type is deprecated, but keep for backward compatibility)
        # We'll use visit_types table instead
        visit_type_legacy = visit_types[0] if visit_types and len(visit_types) > 0 else None
        
        visit = ShopVisitRepository.create(
            db=db,
            shop_id=shop_id,
            order_booker_id=order_booker_id,
            delivery_man_id=delivery_man_id,
            visit_type=visit_type_legacy,  # Keep for backward compatibility
            gps_lat=gps_lat_decimal,
            gps_lng=gps_lng_decimal,
            visit_time=visit_time_datetime,
            photo=photo_url,  # Will be None if base64, URL if already uploaded
            reason=reason
        )
        
        # Create visit types in junction table
        created_visit_types = []
        if visit_types:
            for vt in visit_types:
                try:
                    visit_type_obj = VisitTypeRepository.create(db, visit.id, vt)
                    created_visit_types.append(vt)
                except Exception as e:
                    print(f"Warning: Failed to create visit type '{vt}': {e}")
        
        # Upload photo to Supabase Storage if it's base64
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
                    # Update visit with photo URL
                    visit.photo = uploaded_url
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
        
        # Handle order_booking type - create order
        order_id = None
        if visit_types and "order_booking" in visit_types:
            if not shop_id:
                raise ValueError("shop_id is required when visit_type includes 'order_booking'")
            if not order_items or len(order_items) == 0:
                raise ValueError("order_items are required when visit_type includes 'order_booking'")
            
            # Parse scheduled_date if provided
            scheduled_date_obj = None
            if scheduled_date:
                try:
                    scheduled_date_obj = datetime.fromisoformat(scheduled_date).date()
                except (ValueError, AttributeError):
                    try:
                        scheduled_date_obj = date.fromisoformat(scheduled_date)
                    except (ValueError, AttributeError):
                        raise ValueError("Invalid scheduled_date format. Use ISO date format (e.g., 2026-01-10)")
            
            # Get distributor_id from order_booker
            distributor_id = None
            if order_booker_id:
                order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
                if order_booker:
                    distributor_id = order_booker.distributor_id
            
            # Create order
            try:
                order_data = OrderService.create_order(
                    db=db,
                    shop_id=shop_id,
                    order_booker_id=order_booker_id,
                    order_items=order_items,
                    distributor_id=distributor_id,
                    visit_id=visit.id,
                    scheduled_date=scheduled_date_obj
                )
                order_id = order_data["id"]
            except Exception as e:
                print(f"Error creating order during visit: {e}")
                # Visit is still created, but order creation failed
                raise ValueError(f"Failed to create order: {str(e)}")
        
        # Handle daily_collections type - create collection
        collection_id = None
        if visit_types and "daily_collections" in visit_types:
            if not shop_id:
                raise ValueError("shop_id is required when visit_type includes 'daily_collections'")
            if not collection_amount or collection_amount <= 0:
                raise ValueError("collection_amount is required and must be greater than 0 when visit_type includes 'daily_collections'")
            if not order_booker_id:
                raise ValueError("order_booker_id is required when visit_type includes 'daily_collections'")
            
            # Create daily collection
            try:
                collection_data = DailyCollectionService.create_collection(
                    db=db,
                    shop_id=shop_id,
                    order_booker_id=order_booker_id,
                    amount=collection_amount,
                    collected_at=visit_time_datetime,
                    remarks=collection_remarks,
                    visit_id=visit.id  # Link collection to visit directly
                )
                collection_id = collection_data["id"]
            except Exception as e:
                print(f"Error creating collection during visit: {e}")
                # Visit is still created, but collection creation failed
                raise ValueError(f"Failed to create collection: {str(e)}")
        
        # Format and return visit data
        return ShopVisitService._format_visit_data(db, visit, include_linked_data=True)
    
    @staticmethod
    def get_visits_by_order_booker(db: Session, order_booker_id: int,
                                   skip: int = 0, limit: int = 100) -> List[Dict]:
        """
        Get all visits made by an order booker.
        
        FLOW:
        1. Gets visits from repository
        2. For each visit, fetches shop and order booker information
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
        
        result = []
        for visit in visits:
            # Get shop name
            shop_name = None
            if visit.shop_id:
                shop = ShopRepository.get_by_id(db, visit.shop_id)
                shop_name = shop.name if shop else None
            
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
            
            # Get shop zone_id
            shop_zone_id = None
            if visit.shop_id:
                shop = ShopRepository.get_by_id(db, visit.shop_id)
                shop_zone_id = shop.zone_id if shop else None
            
            result.append(ShopVisitService._format_visit_data(db, visit, include_linked_data=True))
        
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
        
        result = []
        for visit in visits:
            # Get shop name
            shop = ShopRepository.get_by_id(db, visit.shop_id)
            shop_name = shop.name if shop else None
            
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
            
            # Get shop zone_id
            shop_zone_id = None
            if visit.shop_id:
                shop = ShopRepository.get_by_id(db, visit.shop_id)
                shop_zone_id = shop.zone_id if shop else None
            
            result.append(ShopVisitService._format_visit_data(db, visit, include_linked_data=True))
        
        return result
    
    @staticmethod
    def get_all_visits(db: Session, skip: int = 0, limit: int = 1000) -> List[Dict]:
        """
        Get all shop visits with shop and visitor information.
        
        FLOW:
        1. Gets all visits from repository
        2. For each visit, fetches shop, order booker, and delivery man information
        3. Returns formatted list with zone information and linked order/collection IDs
        
        Args:
            db: Database session
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[Dict]: List of visits with shop, visitor, zone info, and linked order/collection IDs
        """
        visits = ShopVisitRepository.get_all(db, skip, limit)
        
        result = []
        for visit in visits:
            # Use the helper method to format visit data consistently
            # This ensures order_id and collection_id are included
            result.append(ShopVisitService._format_visit_data(db, visit, include_linked_data=True))
        
        return result

