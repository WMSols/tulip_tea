"""
Shop business logic service.
"""
from sqlalchemy.orm import Session
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.zone_repository import ZoneRepository
from repositories.credit_limit_request_repository import CreditLimitRequestRepository
from repositories.route_repository import RouteRepository
from repositories.route_shop_repository import RouteShopRepository
from models.route_shop import RouteShop
from decimal import Decimal
from typing import Dict, List, Optional


class ShopService:
    """Service for Shop business logic."""
    
    @staticmethod
    def register_shop(db: Session, name: str, owner_name: str, owner_phone: str,
                      gps_lat: Decimal, gps_lng: Decimal, order_booker_id: int,
                      zone_id: int = None, route_id: int = None, credit_limit: Decimal = None,
                      legacy_balance: Decimal = None, owner_cnic_front_photo: str = None,
                      owner_cnic_back_photo: str = None) -> Dict:
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
        
        # Validate GPS coordinates
        if gps_lat is None or gps_lng is None:
            raise ValueError("GPS coordinates are required")
        
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
            
            # Get next sequence number for this route
            existing_assignments = RouteShopRepository.get_shops_by_route(db, route_id)
            next_sequence = len(existing_assignments) + 1 if existing_assignments else 1
            
            # Assign shop to route
            RouteShopRepository.assign_shop_to_route(
                db=db,
                shop_id=shop.id,
                route_id=route_id,
                sequence=next_sequence
            )
        
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
        
        # Get routes this shop belongs to (should include the route we just assigned)
        route_shops = db.query(RouteShop).filter(RouteShop.shop_id == shop.id).all()
        routes_info = []
        for route_shop in route_shops:
            route = RouteRepository.get_by_id(db, route_shop.route_id)
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
                    "sequence": route_shop.sequence
                })
        
        return {
            "id": shop.id,
            "name": shop.name,
            "owner_name": shop.owner_name,
            "owner_phone": shop.owner_phone,
            "gps_lat": float(shop.gps_lat) if shop.gps_lat else None,
            "gps_lng": float(shop.gps_lng) if shop.gps_lng else None,
            "credit_limit": float(shop.credit_limit) if shop.credit_limit else 0,
            "legacy_balance": float(shop.legacy_balance) if shop.legacy_balance else 0,
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
        
        return [
            {
                "id": shop.id,
                "name": shop.name,
                "owner_name": shop.owner_name,
                "owner_phone": shop.owner_phone,
                "gps_lat": float(shop.gps_lat) if shop.gps_lat else None,
                "gps_lng": float(shop.gps_lng) if shop.gps_lng else None,
                "credit_limit": float(shop.credit_limit) if shop.credit_limit else 0,
                "legacy_balance": float(shop.legacy_balance) if shop.legacy_balance else 0,
                "is_registered": shop.is_registered,
                "registration_status": shop.registration_status,
                "verified_by_distributor": shop.verified_by_distributor,
                "verified_at": shop.verified_at.isoformat() if shop.verified_at else None,
                "zone_id": shop.zone_id,
                "created_by_order_booker": shop.created_by_order_booker,
                "created_by_order_booker_name": order_booker_name,
                "assigned_to_order_booker": shop.assigned_to_order_booker,
                "assigned_to_order_booker_name": OrderBookerRepository.get_by_id(db, shop.assigned_to_order_booker).name if shop.assigned_to_order_booker else None,
                "created_at": shop.created_at.isoformat() if shop.created_at else None
            }
            for shop in shops
        ]
    
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
                "legacy_balance": float(shop.legacy_balance) if shop.legacy_balance else 0,
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
        1. Gets all shops (optionally filtered by zone_id or route_id)
        2. For each shop, finds associated order_booker (via created_by_order_booker)
        3. For each shop, finds associated routes (via route_shops)
        4. For each route, finds assigned order_booker and zone info
        5. Returns formatted list with all associations
        
        Args:
            db: Database session
            distributor_id: Optional distributor ID (currently not used for filtering)
            zone_id: Optional zone ID to filter shops
            route_id: Optional route ID to filter shops
        
        Returns:
            List[Dict]: List of shops with order_booker and route info
        
        Note: Distributors are not assigned to zones, so distributor_id is not used for filtering.
        Use zone_id or route_id for filtering instead.
        """
        from models.route_shop import RouteShop
        from models.route import Route
        
        # Get all shops
        from models.shop import Shop
        
        # Apply filters - prioritize explicit zone_id and route_id over distributor_id
        # distributor_id is kept for potential future use but doesn't filter by default
        if route_id:
            # Filter by route
            shops = ShopRepository.get_by_route(db, route_id)
        elif zone_id:
            # Filter by zone
            shops = ShopRepository.get_by_zone(db, zone_id)
        else:
            # Return all shops - let UI filters handle zone/route filtering
            shops = db.query(Shop).all()
        
        result = []
        for shop in shops:
            # Get order booker who created the shop (historical)
            created_order_booker = None
            created_order_booker_name = None
            if shop.created_by_order_booker:
                created_order_booker = OrderBookerRepository.get_by_id(db, shop.created_by_order_booker)
                created_order_booker_name = created_order_booker.name if created_order_booker else None
            
            # Get order booker currently assigned to the shop
            assigned_order_booker = None
            assigned_order_booker_name = None
            if shop.assigned_to_order_booker:
                assigned_order_booker = OrderBookerRepository.get_by_id(db, shop.assigned_to_order_booker)
                assigned_order_booker_name = assigned_order_booker.name if assigned_order_booker else None
            
            # Get routes this shop belongs to
            route_shops = db.query(RouteShop).filter(RouteShop.shop_id == shop.id).all()
            routes_info = []
            for route_shop in route_shops:
                route = RouteRepository.get_by_id(db, route_shop.route_id)
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
                        "sequence": route_shop.sequence
                    })
            
            result.append({
                "id": shop.id,
                "name": shop.name,
                "owner_name": shop.owner_name,
                "owner_phone": shop.owner_phone,
                "gps_lat": float(shop.gps_lat) if shop.gps_lat else None,
                "gps_lng": float(shop.gps_lng) if shop.gps_lng else None,
                "credit_limit": float(shop.credit_limit) if shop.credit_limit else 0,
                "legacy_balance": float(shop.legacy_balance) if shop.legacy_balance else 0,
                "is_registered": shop.is_registered,
                "registration_status": shop.registration_status,
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
            
            # Assign shop to route
            RouteShopRepository.assign_shop_to_route(db, route_id, shop_id)
        
        return updated_shop

