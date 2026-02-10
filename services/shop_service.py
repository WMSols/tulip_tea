"""
Shop business logic service.
"""
from sqlalchemy.orm import Session
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.zone_repository import ZoneRepository
from repositories.credit_limit_request_repository import CreditLimitRequestRepository
from repositories.route_repository import RouteRepository
# RouteShopRepository and RouteShop model removed - shops now use route_id directly
from decimal import Decimal
from typing import Dict, List, Optional
from fastapi import Request


class ShopService:
    """Service for Shop business logic."""
    
    @staticmethod
    def register_shop(db: Session, name: str, owner_name: str, owner_phone: str,
                      gps_lat: Decimal, gps_lng: Decimal, order_booker_id: int,
                      zone_id: int = None, route_id: int = None, credit_limit: Decimal = None,
                      legacy_balance: Decimal = None, owner_cnic_front_photo: str = None,
                      owner_cnic_back_photo: str = None, owner_photo: str = None,
                      shop_exterior_photo: str = None, user_gps_lat: Decimal = None,
                      user_gps_lng: Decimal = None) -> Dict:
        """
        Register a new shop.
        
        FLOW:
        1. Validates order booker exists
        2. Validates zone exists (if provided)
        3. Validates GPS coordinates are provided
        4. Creates shop with registration_status="pending"
        5. If credit_limit > 0, creates credit limit request
        6. Returns shop data with request info
        
        Args:
            db: Database session
            name: Shop name
            owner_name: Owner name
            owner_phone: Owner phone
            gps_lat: GPS latitude
            gps_lng: GPS longitude
            order_booker_id: Order booker ID who is registering
            zone_id: Optional zone ID
            credit_limit: Requested credit limit (creates request if > 0)
            legacy_balance: Legacy balance
        
        Returns:
            Dict: Shop data with credit_limit_request_id if request was created
        """
        # Verify order booker exists
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        # Verify zone exists if provided
        if zone_id:
            zone = ZoneRepository.get_by_id(db, zone_id)
            if not zone:
                raise ValueError("Zone not found")
        
        # Validate GPS coordinates format and range before saving
        if gps_lat is None or gps_lng is None:
            raise ValueError("GPS coordinates are required")
        
        # Validate GPS coordinates format and range (first use case)
        from services.geolocation_service import GeolocationService
        is_valid_coords, coord_message = GeolocationService.validate_coordinates(
            float(gps_lat), float(gps_lng)
        )
        if not is_valid_coords:
            raise ValueError(coord_message)
        
        # Validate location if user GPS coordinates are provided (order booker's current location)
        # This ensures the order booker is physically at the shop location when registering
        if user_gps_lat is not None and user_gps_lng is not None:
            is_valid, distance_km, message = GeolocationService.validate_creation_location(
                target_lat=gps_lat,
                target_lng=gps_lng,
                user_lat=user_gps_lat,
                user_lng=user_gps_lng,
                entity_type="shop"
            )
            if not is_valid:
                raise ValueError(message)
        
        # Create shop with pending status
        # Note: assigned_to_order_booker is automatically set to order_booker_id
        # in ShopRepository.create() to match created_by_order_booker initially
        shop = ShopRepository.create(
            db=db,
            name=name,
            owner_name=owner_name,
            owner_phone=owner_phone,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            credit_limit=Decimal('0'),  # Start with 0, will be set after approval
            legacy_balance=legacy_balance or Decimal('0'),
            created_by_order_booker=order_booker_id,
            zone_id=zone_id,
            registration_status="pending"  # New shop starts as pending
        )
        
        # Upload CNIC photos to Supabase Storage if provided
        from services.image_service import ImageService
        cnic_front_url = None
        cnic_back_url = None
        
        if owner_cnic_front_photo:
            print(f"INFO: Attempting to upload CNIC front photo for shop {shop.id}")
            try:
                cnic_front_url = ImageService.upload_shop_cnic_front(
                    shop_id=shop.id,
                    order_booker_id=order_booker_id,
                    base64_image=owner_cnic_front_photo
                )
                if cnic_front_url:
                    print(f"SUCCESS: CNIC front photo uploaded: {cnic_front_url}")
                    shop.owner_cnic_front_photo = cnic_front_url
                    db.commit()
                    db.refresh(shop)
                else:
                    print(f"ERROR: Failed to upload CNIC front photo for shop {shop.id}")
            except Exception as e:
                print(f"ERROR: Exception uploading CNIC front photo for shop {shop.id}: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        if owner_cnic_back_photo:
            print(f"INFO: Attempting to upload CNIC back photo for shop {shop.id}")
            try:
                cnic_back_url = ImageService.upload_shop_cnic_back(
                    shop_id=shop.id,
                    order_booker_id=order_booker_id,
                    base64_image=owner_cnic_back_photo
                )
                if cnic_back_url:
                    print(f"SUCCESS: CNIC back photo uploaded: {cnic_back_url}")
                    shop.owner_cnic_back_photo = cnic_back_url
                    db.commit()
                    db.refresh(shop)
                else:
                    print(f"ERROR: Failed to upload CNIC back photo for shop {shop.id}")
            except Exception as e:
                print(f"ERROR: Exception uploading CNIC back photo for shop {shop.id}: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Upload owner photo to Supabase Storage if provided
        if owner_photo:
            print(f"INFO: Attempting to upload owner photo for shop {shop.id}")
            try:
                owner_photo_url = ImageService.upload_shop_owner_photo(
                    shop_id=shop.id,
                    order_booker_id=order_booker_id,
                    base64_image=owner_photo
                )
                if owner_photo_url:
                    print(f"SUCCESS: Owner photo uploaded: {owner_photo_url}")
                    shop.owner_photo = owner_photo_url
                    db.commit()
                    db.refresh(shop)
                else:
                    print(f"ERROR: Failed to upload owner photo for shop {shop.id}")
            except Exception as e:
                print(f"ERROR: Exception uploading owner photo for shop {shop.id}: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Upload shop exterior photo to Supabase Storage if provided
        if shop_exterior_photo:
            print(f"INFO: Attempting to upload shop exterior photo for shop {shop.id}")
            try:
                shop_exterior_url = ImageService.upload_shop_exterior(
                    shop_id=shop.id,
                    order_booker_id=order_booker_id,
                    base64_image=shop_exterior_photo
                )
                if shop_exterior_url:
                    print(f"SUCCESS: Shop exterior photo uploaded: {shop_exterior_url}")
                    shop.shop_exterior_photo = shop_exterior_url
                    db.commit()
                    db.refresh(shop)
                else:
                    print(f"ERROR: Failed to upload shop exterior photo for shop {shop.id}")
            except Exception as e:
                print(f"ERROR: Exception uploading shop exterior photo for shop {shop.id}: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Assign shop to route if route_id is provided
        if route_id:
            # Verify route exists
            route = RouteRepository.get_by_id(db, route_id)
            if not route:
                raise ValueError("Route not found")
            
            # Verify route is assigned to this order booker
            if route.order_booker_id != order_booker_id:
                raise ValueError("Route is not assigned to this order booker")
            
            # If zone_id is provided, verify route belongs to that zone
            if zone_id and route.zone_id != zone_id:
                raise ValueError(f"Route belongs to zone {route.zone_id}, but shop zone is {zone_id}. They must match.")
            
            # If no zone_id provided but route has zone, update shop's zone_id to match route
            if not zone_id and route.zone_id:
                shop.zone_id = route.zone_id
                db.commit()
                db.refresh(shop)
            
            # Get next sequence number for this route (count shops already on this route)
            existing_shops = ShopRepository.get_by_route(db, route_id)
            next_sequence = len(existing_shops) + 1 if existing_shops else 1
            
            # Assign shop to route directly (using shop.route_id)
            shop.route_id = route_id
            shop.route_sequence = next_sequence
            db.commit()
            db.refresh(shop)
        
        # Create credit limit request if credit_limit is provided and > 0
        credit_limit_request_id = None
        if credit_limit and credit_limit > 0:
            request = CreditLimitRequestRepository.create(
                db=db,
                shop_id=shop.id,
                requested_by_role="order_booker",
                requested_by_id=order_booker_id,
                requested_credit_limit=float(credit_limit),
                old_credit_limit=None,  # New shop, no old limit
                remarks=f"Initial credit limit request for new shop: {name}"
            )
            credit_limit_request_id = request.id
        
        # Get assigned order booker name (initially same as creator)
        assigned_order_booker_name = order_booker.name if order_booker else None
        
        # Get route this shop belongs to (using shop.route_id directly)
        routes_info = []
        if shop.route_id:
            route = RouteRepository.get_by_id(db, shop.route_id)
            if route:
                route_order_booker = None
                route_order_booker_name = None
                if route.order_booker_id:
                    route_order_booker = OrderBookerRepository.get_by_id(db, route.order_booker_id)
                    route_order_booker_name = route_order_booker.name if route_order_booker else None
                
                # Get zone name for route
                route_zone_name = None
                if route.zone_id:
                    route_zone = ZoneRepository.get_by_id(db, route.zone_id)
                    route_zone_name = route_zone.name if route_zone else None
                
                routes_info.append({
                    "route_id": route.id,
                    "route_name": route.name,
                    "route_zone_id": route.zone_id,
                    "route_zone_name": route_zone_name,
                    "order_booker_id": route.order_booker_id,
                    "order_booker_name": route_order_booker_name,
                    "sequence": shop.route_sequence
                })
        
        return {
            "id": shop.id,
            "name": shop.name,
            "owner_name": shop.owner_name,
            "owner_phone": shop.owner_phone,
            "gps_lat": float(shop.gps_lat) if shop.gps_lat else None,
            "gps_lng": float(shop.gps_lng) if shop.gps_lng else None,
            "credit_limit": float(shop.credit_limit) if shop.credit_limit else 0,
            # legacy_balance removed (column no longer exists - was merged into outstanding_balance)
            "outstanding_balance": float(shop.outstanding_balance) if shop.outstanding_balance else 0,
            "is_registered": shop.is_registered,
            "registration_status": shop.registration_status,
            "verified_by_distributor": shop.verified_by_distributor,
            "verified_at": shop.verified_at.isoformat() if shop.verified_at else None,
            "zone_id": shop.zone_id,
            "created_by_order_booker": shop.created_by_order_booker,
            "created_by_order_booker_name": order_booker.name,  # Historical creator name
            "assigned_to_order_booker": shop.assigned_to_order_booker,  # Current assignee
            "assigned_to_order_booker_name": assigned_order_booker_name,  # Current assignee name
            "routes": routes_info,  # List of routes this shop belongs to
            "owner_cnic_front_photo": shop.owner_cnic_front_photo,  # URL to CNIC front photo
            "owner_cnic_back_photo": shop.owner_cnic_back_photo,  # URL to CNIC back photo
            "shop_exterior_photo": shop.shop_exterior_photo,
            "owner_photo": shop.owner_photo,
            "credit_limit_request_id": credit_limit_request_id,  # Include request ID if created
            "created_at": shop.created_at.isoformat() if shop.created_at else None
        }
    
    @staticmethod
    def get_shops_by_order_booker(db: Session, order_booker_id: int, approved_only: bool = False) -> List[Dict]:
        """
        Get all shops registered by an order booker (historical).
        
        Note: This returns shops based on created_by_order_booker.
        For shops currently assigned to an order booker, use get_shops_assigned_to_order_booker().
        
        Args:
            db: Database session
            order_booker_id: Order booker ID
            approved_only: If True, only return shops with registration_status="approved"
        """
        shops = ShopRepository.get_by_order_booker(db, order_booker_id)
        
        # Filter to approved shops only if requested
        if approved_only:
            shops = [shop for shop in shops if shop.registration_status == "approved"]
        
        # Get order booker name once
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        order_booker_name = order_booker.name if order_booker else None
        
        result = []
        for shop in shops:
            # Get route information for this shop
            routes_info = []
            route_id = None
            if shop.route_id:
                route_id = shop.route_id
                route = RouteRepository.get_by_id(db, shop.route_id)
                if route:
                    route_order_booker = None
                    route_order_booker_name = None
                    if route.order_booker_id:
                        route_order_booker = OrderBookerRepository.get_by_id(db, route.order_booker_id)
                        route_order_booker_name = route_order_booker.name if route_order_booker else None
                    
                    # Get zone name for route
                    route_zone_name = None
                    if route.zone_id:
                        route_zone = ZoneRepository.get_by_id(db, route.zone_id)
                        route_zone_name = route_zone.name if route_zone else None
                    
                    routes_info.append({
                        "route_id": route.id,
                        "route_name": route.name,
                        "route_zone_id": route.zone_id,
                        "route_zone_name": route_zone_name,
                        "order_booker_id": route.order_booker_id,
                        "order_booker_name": route_order_booker_name,
                        "sequence": shop.route_sequence
                    })
            
            result.append({
                "id": shop.id,
                "name": shop.name,
                "owner_name": shop.owner_name,
                "owner_phone": shop.owner_phone,
                "gps_lat": float(shop.gps_lat) if shop.gps_lat else None,
                "gps_lng": float(shop.gps_lng) if shop.gps_lng else None,
                "credit_limit": float(shop.credit_limit) if shop.credit_limit else 0,
                # legacy_balance removed (column no longer exists - was merged into outstanding_balance)
                "outstanding_balance": float(shop.outstanding_balance) if shop.outstanding_balance else 0,
                "is_registered": shop.is_registered,
                "registration_status": shop.registration_status,
                "verified_by_distributor": shop.verified_by_distributor,
                "verified_at": shop.verified_at.isoformat() if shop.verified_at else None,
                "zone_id": shop.zone_id,
                "route_id": route_id,  # Include route_id directly for easy filtering
                "created_by_order_booker": shop.created_by_order_booker,
                "created_by_order_booker_name": order_booker_name,
                "assigned_to_order_booker": shop.assigned_to_order_booker,
                "assigned_to_order_booker_name": OrderBookerRepository.get_by_id(db, shop.assigned_to_order_booker).name if shop.assigned_to_order_booker else None,
                "routes": routes_info,  # Include routes array for detailed route info
                "created_at": shop.created_at.isoformat() if shop.created_at else None
            })
        
        return result
    
    @staticmethod
    def get_shops_assigned_to_order_booker(db: Session, order_booker_id: int, approved_only: bool = False) -> List[Dict]:
        """
        Get all shops currently assigned to an order booker.
        
        This returns shops based on assigned_to_order_booker, which represents
        the current responsibility. This is different from get_shops_by_order_booker()
        which returns shops based on who originally created them.
        
        Args:
            db: Database session
            order_booker_id: Order booker ID
            approved_only: If True, only return shops with registration_status="approved"
        """
        shops = ShopRepository.get_by_assigned_order_booker(db, order_booker_id)
        
        # Filter to approved shops only if requested
        if approved_only:
            shops = [shop for shop in shops if shop.registration_status == "approved"]
        
        # Get order booker name once
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        order_booker_name = order_booker.name if order_booker else None
        
        return [
            {
                "id": shop.id,
                "name": shop.name,
                "owner_name": shop.owner_name,
                "owner_phone": shop.owner_phone,
                "gps_lat": float(shop.gps_lat) if shop.gps_lat else None,
                "gps_lng": float(shop.gps_lng) if shop.gps_lng else None,
                "credit_limit": float(shop.credit_limit) if shop.credit_limit else 0,
                # legacy_balance removed (column no longer exists - was merged into outstanding_balance)
                "outstanding_balance": float(shop.outstanding_balance) if shop.outstanding_balance else 0,
                "is_registered": shop.is_registered,
                "registration_status": shop.registration_status,
                "verified_by_distributor": shop.verified_by_distributor,
                "verified_at": shop.verified_at.isoformat() if shop.verified_at else None,
                "zone_id": shop.zone_id,
                "created_by_order_booker": shop.created_by_order_booker,
                "created_by_order_booker_name": OrderBookerRepository.get_by_id(db, shop.created_by_order_booker).name if shop.created_by_order_booker else None,
                "assigned_to_order_booker": shop.assigned_to_order_booker,
                "assigned_to_order_booker_name": order_booker_name,
                "owner_cnic_front_photo": shop.owner_cnic_front_photo,
                "owner_cnic_back_photo": shop.owner_cnic_back_photo,
                "shop_exterior_photo": shop.shop_exterior_photo,
                "owner_photo": shop.owner_photo,
                "created_at": shop.created_at.isoformat() if shop.created_at else None
            }
            for shop in shops
        ]
    
    @staticmethod
    def get_all_shops_with_associations(db: Session, distributor_id: int = None, 
                                       zone_id: int = None, route_id: int = None) -> List[Dict]:
        """
        Get all shops with their associated order_booker and route information.
        
        FLOW:
        1. Gets all shops (optionally filtered by distributor_id, zone_id, or route_id)
        2. For each shop, finds associated order_booker (via created_by_order_booker)
        3. For each shop, finds associated route (via shop.route_id)
        4. For each route, finds assigned order_booker and zone info
        5. Returns formatted list with all associations
        
        Args:
            db: Database session
            distributor_id: Optional distributor ID - filters shops by order bookers belonging to this distributor
            zone_id: Optional zone ID to filter shops
            route_id: Optional route ID to filter shops
        
        Returns:
            List[Dict]: List of shops with order_booker and route info
        
        Note: When distributor_id is provided, returns shops where:
            - Shop was created by an order booker belonging to this distributor, OR
            - Shop is assigned to an order booker belonging to this distributor, OR
            - Shop was verified/approved by this distributor
        """
# RouteShop model removed - shops now use route_id directly
        from models.route import Route
        from models.order_booker import OrderBooker
        
        # Get all shops
        from models.shop import Shop
        
        # Apply filters - prioritize explicit zone_id and route_id over distributor_id
        if route_id:
            # Filter by route
            shops = ShopRepository.get_by_route(db, route_id)
        elif zone_id:
            # Filter by zone
            shops = ShopRepository.get_by_zone(db, zone_id)
        elif distributor_id:
            # Filter by distributor: get shops where order booker belongs to this distributor
            # OR shops verified by this distributor
            from sqlalchemy import or_
            
            # Get all order booker IDs for this distributor
            order_booker_ids_query = db.query(OrderBooker.id).filter(
                OrderBooker.distributor_id == distributor_id,
                OrderBooker.deleted_at.is_(None),
                OrderBooker.is_active == True
            )
            order_booker_id_list = [row[0] for row in order_booker_ids_query.all()]
            
            # Build filter conditions
            conditions = []
            
            # Shop created by order booker belonging to this distributor
            if order_booker_id_list:
                conditions.append(Shop.created_by_order_booker.in_(order_booker_id_list))
                # Shop assigned to order booker belonging to this distributor
                conditions.append(Shop.assigned_to_order_booker.in_(order_booker_id_list))
            
            # Shop verified by this distributor
            conditions.append(Shop.verified_by_distributor == distributor_id)
            
            shops = db.query(Shop).filter(
                Shop.deleted_at.is_(None),
                Shop.is_active == True
            ).filter(
                or_(*conditions) if conditions else False
            ).all()
        else:
            # Return all active shops (exclude soft-deleted and inactive) - let UI filters handle zone/route filtering
            try:
                shops = db.query(Shop).filter(
                    Shop.deleted_at.is_(None),
                    Shop.is_active == True
                ).all()
            except Exception as e:
                print(f"ERROR querying shops: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
        
        # Batch load all related entities to avoid N+1 queries
        # Collect all unique IDs
        created_order_booker_ids = set()
        assigned_order_booker_ids = set()
        route_ids = set()
        zone_ids = set()
        route_order_booker_ids = set()
        
        for shop in shops:
            if shop.created_by_order_booker:
                created_order_booker_ids.add(shop.created_by_order_booker)
            if shop.assigned_to_order_booker:
                assigned_order_booker_ids.add(shop.assigned_to_order_booker)
            if shop.route_id:
                route_ids.add(shop.route_id)
        
        # Batch load all routes (1 query for all routes)
        routes_map = {}
        if route_ids:
            routes = RouteRepository.get_by_ids(db, list(route_ids), include_deleted=False)
            routes_map = {route.id: route for route in routes}
            # Collect zone IDs and route order booker IDs from routes
            for route in routes:
                if route.zone_id:
                    zone_ids.add(route.zone_id)
                if route.order_booker_id:
                    route_order_booker_ids.add(route.order_booker_id)
        
        # Batch load all order bookers (created, assigned, and route order bookers) - 1 query
        all_order_booker_ids = created_order_booker_ids | assigned_order_booker_ids | route_order_booker_ids
        order_bookers_map = {}
        if all_order_booker_ids:
            from models.order_booker import OrderBooker
            # Load active order bookers (for assigned and route order bookers)
            active_order_bookers = db.query(OrderBooker).filter(
                OrderBooker.id.in_(list(all_order_booker_ids)),
                OrderBooker.deleted_at.is_(None)
            ).all()
            order_bookers_map.update({ob.id: ob for ob in active_order_bookers})
            
            # Load deleted order bookers for created_by (historical data)
            deleted_order_booker_ids = created_order_booker_ids - set(order_bookers_map.keys())
            if deleted_order_booker_ids:
                deleted_order_bookers = db.query(OrderBooker).filter(
                    OrderBooker.id.in_(list(deleted_order_booker_ids))
                ).all()
                order_bookers_map.update({ob.id: ob for ob in deleted_order_bookers})
        
        # Batch load all zones (1 query for all zones)
        zones_map = {}
        if zone_ids:
            from models.zone import Zone
            zones = db.query(Zone).filter(
                Zone.id.in_(list(zone_ids)),
                Zone.deleted_at.is_(None)
            ).all()
            zones_map = {zone.id: zone for zone in zones}
        
        # Build result using lookup maps (no additional queries)
        result = []
        for shop in shops:
            # Get order booker who created the shop (historical) from lookup map
            created_order_booker_name = None
            if shop.created_by_order_booker:
                created_order_booker = order_bookers_map.get(shop.created_by_order_booker)
                created_order_booker_name = created_order_booker.name if created_order_booker else None
            
            # Get order booker currently assigned to the shop from lookup map
            assigned_order_booker_name = None
            if shop.assigned_to_order_booker:
                assigned_order_booker = order_bookers_map.get(shop.assigned_to_order_booker)
                assigned_order_booker_name = assigned_order_booker.name if assigned_order_booker else None
            
            # Get route this shop belongs to from lookup map
            routes_info = []
            if shop.route_id:
                route = routes_map.get(shop.route_id)
                if route:
                    # Get route order booker from lookup map
                    route_order_booker_name = None
                    if route.order_booker_id:
                        route_order_booker = order_bookers_map.get(route.order_booker_id)
                        route_order_booker_name = route_order_booker.name if route_order_booker else None
                    
                    # Get zone name from lookup map
                    route_zone_name = None
                    if route.zone_id:
                        route_zone = zones_map.get(route.zone_id)
                        route_zone_name = route_zone.name if route_zone else None
                    
                    routes_info.append({
                        "route_id": route.id,
                        "route_name": route.name,
                        "route_zone_id": route.zone_id,
                        "route_zone_name": route_zone_name,
                        "order_booker_id": route.order_booker_id,
                        "order_booker_name": route_order_booker_name,
                        "sequence": shop.route_sequence
                    })
            
            # Safely build result dictionary with error handling
            try:
                # Safely convert Decimal to float
                gps_lat_val = None
                if shop.gps_lat is not None:
                    try:
                        gps_lat_val = float(shop.gps_lat)
                    except (TypeError, ValueError):
                        gps_lat_val = None
                
                gps_lng_val = None
                if shop.gps_lng is not None:
                    try:
                        gps_lng_val = float(shop.gps_lng)
                    except (TypeError, ValueError):
                        gps_lng_val = None
                
                credit_limit_val = 0.0
                if shop.credit_limit is not None:
                    try:
                        credit_limit_val = float(shop.credit_limit)
                    except (TypeError, ValueError):
                        credit_limit_val = 0.0
                
                # legacy_balance removed (column no longer exists - was merged into outstanding_balance)
                
                outstanding_balance_val = 0.0
                if shop.outstanding_balance is not None:
                    try:
                        outstanding_balance_val = float(shop.outstanding_balance)
                    except (TypeError, ValueError):
                        outstanding_balance_val = 0.0
                
                result.append({
                    "id": shop.id,
                    "name": shop.name,
                    "owner_name": shop.owner_name,
                    "owner_phone": shop.owner_phone,
                    "gps_lat": gps_lat_val,
                    "gps_lng": gps_lng_val,
                    "credit_limit": credit_limit_val,
                    # legacy_balance removed (column no longer exists - was merged into outstanding_balance)
                    "outstanding_balance": outstanding_balance_val,
                    "is_registered": shop.is_registered if shop.is_registered is not None else False,
                    "registration_status": shop.registration_status if shop.registration_status else "pending",
                    "verified_by_distributor": shop.verified_by_distributor,
                    "verified_at": shop.verified_at.isoformat() if shop.verified_at else None,
                    "zone_id": shop.zone_id,
                    "created_by_order_booker": shop.created_by_order_booker,
                    "created_by_order_booker_name": created_order_booker_name,  # Historical creator
                    "assigned_to_order_booker": shop.assigned_to_order_booker,  # Current assignee
                    "assigned_to_order_booker_name": assigned_order_booker_name,  # Current assignee name
                    "routes": routes_info,  # List of routes this shop belongs to
                    "owner_cnic_front_photo": shop.owner_cnic_front_photo,
                    "owner_cnic_back_photo": shop.owner_cnic_back_photo,
                    "shop_exterior_photo": shop.shop_exterior_photo,
                    "owner_photo": shop.owner_photo,
                    "created_at": shop.created_at.isoformat() if shop.created_at else None
                })
            except Exception as e:
                print(f"ERROR building result for shop {shop.id}: {str(e)}")
                import traceback
                traceback.print_exc()
                # Skip this shop and continue with others
                continue
        
        return result
    
    @staticmethod
    def update_and_resubmit_shop(db: Session, shop_id: int, route_id: int = None, **update_data):
        """
        Update a rejected shop and resubmit it for approval.
        
        Args:
            db: Database session
            shop_id: Shop ID to update
            route_id: Optional route ID to assign shop to
            **update_data: Fields to update
        
        Returns:
            Updated shop instance or None if not found
        """
        # Get shop
        shop = ShopRepository.get_by_id(db, shop_id)
        if not shop:
            return None
        
        # Update shop fields
        updated_shop = ShopRepository.update(db=db, shop_id=shop_id, **update_data)
        if not updated_shop:
            return None
        
        # Handle route assignment if route_id is provided
        if route_id:
            # Verify route exists
            route = RouteRepository.get_by_id(db, route_id)
            if not route:
                raise ValueError("Route not found")
            
            # Verify route belongs to the order booker (if shop has order booker)
            if shop.created_by_order_booker:
                order_booker_routes = RouteRepository.get_by_order_booker(db, shop.created_by_order_booker)
                if not any(r.id == route_id for r in order_booker_routes):
                    raise ValueError("Route does not belong to this order booker")
            
            # Verify zone matches if both are provided
            if updated_shop.zone_id and route.zone_id:
                if updated_shop.zone_id != route.zone_id:
                    raise ValueError("Route zone does not match shop zone")
            
            # Assign shop to route directly (using shop.route_id)
            # Get next sequence number for this route
            existing_shops = ShopRepository.get_by_route(db, route_id)
            next_sequence = len(existing_shops) + 1 if existing_shops else 1
            
            updated_shop.route_id = route_id
            updated_shop.route_sequence = next_sequence
            db.commit()
            db.refresh(updated_shop)
        
        return updated_shop
    
    @staticmethod
    def delete_shop(db: Session, shop_id: int, deleter_id: int = None, request: Optional[Request] = None) -> bool:
        """
        Soft delete a shop and handle related credit limit requests.
        
        FLOW:
        1. Soft delete the shop (sets deleted_at and is_active=False)
        2. Soft delete all pending credit limit requests for this shop
        3. Preserve credit_limit (so it can be restored when reactivated)
        4. Log the operation
        
        Args:
            db: Database session
            shop_id: Shop ID to soft delete
            deleter_id: ID of the user performing the deletion (for logging)
            request: Optional FastAPI request object for logging context
        
        Returns:
            bool: True if successful
        
        Raises:
            ValueError: If shop not found
        """
        from datetime import datetime
        from models.credit_limit_request import CreditLimitRequest
        
        shop = ShopRepository.get_by_id(db, shop_id)
        if not shop:
            raise ValueError("Shop not found")
        
        # Preserve credit_limit before deletion (for logging and potential reactivation)
        preserved_credit_limit = shop.credit_limit
        
        # Soft delete all pending credit limit requests for this shop
        pending_requests = db.query(CreditLimitRequest).filter(
            CreditLimitRequest.shop_id == shop_id,
            CreditLimitRequest.status == "pending",
            CreditLimitRequest.deleted_at.is_(None)
        ).all()
        
        requests_deleted = 0
        for req in pending_requests:
            req.deleted_at = datetime.utcnow()
            requests_deleted += 1
        
        # Soft delete the shop (sets deleted_at and is_active=False)
        # NOTE: credit_limit is preserved (not reset to 0) so it can be restored when reactivated
        success = ShopRepository.delete(db, shop_id)
        
        if success:
            db.commit()  # Commit credit limit requests and shop deletion
            
            # Log the soft delete operation
            from services.activity_log_service import ActivityLogService
            ActivityLogService.log_delete(
                db=db,
                user_id=deleter_id,
                user_role='distributor',
                entity_type='shop',
                entity_id=shop_id,
                changes_summary=f"Soft deleted shop '{shop.name}' (ID: {shop_id}). Credit limit preserved: {preserved_credit_limit}. {requests_deleted} pending credit limit request(s) soft deleted.",
                metadata={
                    'preserved_credit_limit': str(preserved_credit_limit),
                    'pending_requests_deleted': requests_deleted
                },
                request=request
            )
        
        return success
    
    @staticmethod
    def get_unassigned_shops(db: Session, zone_id: int = None) -> List[Dict]:
        """
        Get all shops that are unassigned (assigned_to_order_booker is NULL or points to inactive/deleted order booker).
        
        FLOW:
        1. Gets all active shops
        2. Filters shops where assigned_to_order_booker is NULL or points to inactive/deleted order booker
        3. Optionally filters by zone_id
        4. Returns formatted list with zone information
        
        Args:
            db: Database session
            zone_id: Optional zone ID to filter shops
        
        Returns:
            List[Dict]: List of unassigned shops with zone info
        """
        from models.shop import Shop
        
        # Get all active, non-deleted shops
        query = db.query(Shop).filter(
            Shop.deleted_at.is_(None),
            Shop.is_active == True
        )
        
        # Filter by zone if provided
        if zone_id:
            query = query.filter(Shop.zone_id == zone_id)
        
        shops = query.all()
        
        result = []
        for shop in shops:
            # Check if shop is unassigned
            is_unassigned = False
            assigned_order_booker_name = None
            
            if shop.assigned_to_order_booker is None:
                is_unassigned = True
            else:
                # Check if assigned order booker is active
                assigned_order_booker = OrderBookerRepository.get_by_id(db, shop.assigned_to_order_booker, include_deleted=False)
                if not assigned_order_booker:
                    # Order booker is deleted or inactive
                    is_unassigned = True
                else:
                    assigned_order_booker_name = assigned_order_booker.name
            
            # Only include unassigned shops
            if is_unassigned:
                # Get zone name
                zone_name = None
                if shop.zone_id:
                    zone = ZoneRepository.get_by_id(db, shop.zone_id, include_deleted=False)
                    zone_name = zone.name if zone else None
                
                # Get created by order booker name (historical)
                created_order_booker_name = None
                if shop.created_by_order_booker:
                    created_order_booker = OrderBookerRepository.get_by_id(db, shop.created_by_order_booker, include_deleted=True)
                    created_order_booker_name = created_order_booker.name if created_order_booker else None
                
                # Safely convert Decimal to float
                try:
                    gps_lat_val = float(shop.gps_lat) if shop.gps_lat is not None else None
                except (TypeError, ValueError):
                    gps_lat_val = None
                
                try:
                    gps_lng_val = float(shop.gps_lng) if shop.gps_lng is not None else None
                except (TypeError, ValueError):
                    gps_lng_val = None
                
                try:
                    credit_limit_val = float(shop.credit_limit) if shop.credit_limit is not None else 0.0
                except (TypeError, ValueError):
                    credit_limit_val = 0.0
                
                # legacy_balance removed (column no longer exists - was merged into outstanding_balance)
                
                result.append({
                    "id": shop.id,
                    "name": shop.name,
                    "owner_name": shop.owner_name,
                    "owner_phone": shop.owner_phone,
                    "gps_lat": gps_lat_val,
                    "gps_lng": gps_lng_val,
                    "credit_limit": credit_limit_val,
                    # legacy_balance removed (column no longer exists - was merged into outstanding_balance)
                    "is_registered": shop.is_registered if shop.is_registered is not None else False,
                    "registration_status": shop.registration_status if shop.registration_status else "pending",
                    "verified_by_distributor": shop.verified_by_distributor,
                    "verified_at": shop.verified_at.isoformat() if shop.verified_at else None,
                    "zone_id": shop.zone_id,
                    "zone_name": zone_name,
                    "created_by_order_booker": shop.created_by_order_booker,
                    "created_by_order_booker_name": created_order_booker_name,  # Historical creator
                    "assigned_to_order_booker": shop.assigned_to_order_booker,  # NULL or inactive
                    "assigned_to_order_booker_name": assigned_order_booker_name,  # NULL or inactive
                    "is_unassigned": True,  # Flag to indicate this shop needs reassignment
                    "created_at": shop.created_at.isoformat() if shop.created_at else None
                })
        
        return result

