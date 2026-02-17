"""
Shop Router
===========
Handles shop registration, management, and verification.

API ENDPOINTS:
- POST /shops/order-booker/{id} - Register new shop (Order Booker)
- GET /shops/order-booker/{id} - List shops by order booker
- GET /shops/pending - List pending shops (Distributor)
- PUT /shops/{id} - Update shop data (Distributor)
- POST /shops/{id}/verify - Verify/approve shop (Distributor)
- DELETE /shops/{id} - Soft delete shop (Distributor)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from config.database import get_db
from models.schemas import ShopRegister, ShopResponse, ShopUpdate, ShopVerify
from services.shop_service import ShopService
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from services.activity_log_service import ActivityLogService
from utils.auth_helpers import get_current_user_from_request
from utils.dependencies import get_current_distributor, get_current_order_booker, get_current_user
from typing import Dict

router = APIRouter(prefix="/shops", tags=["Shops"])


@router.post("/order-booker/{order_booker_id}", response_model=ShopResponse, status_code=status.HTTP_201_CREATED, tags=["Shops", "Order Booker APIs"])
async def register_shop(
    order_booker_id: int,
    shop: ShopRegister,
    request: Request,
    order_booker: Dict = Depends(get_current_order_booker),
    db: Session = Depends(get_db)
):
    """
    Register a new shop (by Order Booker).
    
    API: POST /shops/order-booker/{order_booker_id}
    
    FLOW:
    1. Order Booker fills shop registration form
    2. Provides shop details + requested credit_limit
    3. Service creates shop with registration_status="pending"
    4. If credit_limit > 0, creates credit_limit_request
    5. Returns shop data with request info
    
    Request Body:
        {
            "name": "Ali General Store",
            "owner_name": "Ahmed Ali",
            "owner_phone": "03001234567",
            "gps_lat": 33.6844,
            "gps_lng": 73.0479,
            "zone_id": 1,
            "credit_limit": 50000.00,
            "legacy_balance": 0
        }
    
    Response (201):
        Shop data with credit_limit_request_id if request was created
    """
    try:
        # Verify order booker can only register shops for themselves
        if order_booker['user_id'] != order_booker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only register shops for your own account"
            )
        
        # Convert user GPS coordinates if provided (for location validation)
        user_gps_lat = None
        user_gps_lng = None
        if shop.user_gps_lat is not None and shop.user_gps_lng is not None:
            user_gps_lat = Decimal(str(shop.user_gps_lat))
            user_gps_lng = Decimal(str(shop.user_gps_lng))
        
        result = ShopService.register_shop(
            db=db,
            name=shop.name,
            owner_name=shop.owner_name,
            owner_phone=shop.owner_phone,
            gps_lat=Decimal(str(shop.gps_lat)),
            gps_lng=Decimal(str(shop.gps_lng)),
            order_booker_id=order_booker_id,
            zone_id=shop.zone_id,
            route_id=shop.route_id,
            credit_limit=Decimal(str(shop.credit_limit)) if shop.credit_limit else None,
            legacy_balance=Decimal(str(shop.legacy_balance)) if shop.legacy_balance else None,
            owner_cnic_front_photo=shop.owner_cnic_front_photo,
            owner_cnic_back_photo=shop.owner_cnic_back_photo,
            owner_photo=shop.owner_photo,
            shop_exterior_photo=shop.shop_exterior_photo,
            user_gps_lat=user_gps_lat,
            user_gps_lng=user_gps_lng
        )
        
        # Log shop creation
        ActivityLogService.log_create(
            db=db,
            user_id=order_booker_id,
            user_role='order_booker',
            entity_type='shop',
            entity_id=result['id'],
            new_values={
                'name': result.get('name'),
                'owner_name': result.get('owner_name'),
                'registration_status': result.get('registration_status'),
                'credit_limit': str(result.get('credit_limit', 0))
            },
            user_name=result.get('created_by_order_booker_name'),
            metadata={
                'zone_id': result.get('zone_id'),
                'gps_lat': str(result.get('gps_lat', '')),
                'gps_lng': str(result.get('gps_lng', '')),
                'credit_limit_request_id': result.get('credit_limit_request_id')
            },
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        user_info = get_current_user_from_request(request)
        ActivityLogService.log_failure(
            db=db,
            user_id=user_info['user_id'] if user_info else order_booker_id,
            user_role=user_info['user_role'] if user_info else 'order_booker',
            action_type='CREATE',
            entity_type='shop',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/order-booker/{order_booker_id}", response_model=List[ShopResponse], tags=["Shops", "Order Booker APIs"])
async def list_shops_by_order_booker(
    order_booker_id: int, 
    approved_only: bool = Query(False, description="Filter to show only approved shops (for visit registration)"),
    order_booker: Dict = Depends(get_current_order_booker),
    db: Session = Depends(get_db)
):
    """
    List all shops registered by an order booker.
    
    API: GET /shops/order-booker/{order_booker_id}?approved_only=true
    
    Query Parameters:
        approved_only: If true, returns only shops with registration_status="approved" (useful for visit registration)
    
    Response (200):
        List of shops with their details
    """
    # Verify order booker can only view their own shops
    if order_booker['user_id'] != order_booker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view shops for your own account"
        )
    
    shops = ShopService.get_shops_by_order_booker(db=db, order_booker_id=order_booker_id, approved_only=approved_only)
    return shops


@router.get("/{shop_id}/credit-info", tags=["Shops", "Order Booker APIs", "Delivery Man APIs"])
async def get_shop_credit_info(
    shop_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get shop's credit limit information including outstanding balance and available credit.
    
    API: GET /shops/{shop_id}/credit-info
    
    Response (200):
        {
            "shop_id": 1,
            "credit_limit": 50000.00,
            "legacy_balance": 0.00,
            "outstanding_balance": 1000.00,
            "total_outstanding": 1000.00,
            "available_credit": 49000.00
        }
    """
    from services.order_service import OrderService
    
    shop = ShopRepository.get_by_id(db, shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    
    # Explicitly refresh the shop object to get the latest outstanding_balance
    # This ensures we get the most recent value after any updates (e.g., from daily collections)
    db.refresh(shop)
    
    credit_limit = float(shop.credit_limit or 0)
    
    # Use shop's outstanding_balance field (maintained automatically)
    # Note: outstanding_balance already includes any legacy balance that was added during shop creation
    outstanding_balance = float(shop.outstanding_balance or 0)
    
    # Total outstanding = outstanding_balance (which includes orders - payments + any initial legacy balance)
    total_outstanding = outstanding_balance
    available_credit = credit_limit - total_outstanding if credit_limit > 0 else 0.0
    
    return {
        "shop_id": shop_id,
        "shop_name": shop.name,
        "credit_limit": credit_limit,
        "outstanding_balance": outstanding_balance,
        "total_outstanding": total_outstanding,
        "available_credit": available_credit
    }


@router.get("/pending", response_model=List[ShopResponse], tags=["Shops", "Distributor APIs"])
async def list_pending_shops(
    distributor_id: int = Query(..., description="Distributor ID to filter pending shops"),
    distributor: Dict = Depends(get_current_distributor),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    List all shops with pending registration status for the authenticated distributor.
    
    API: GET /shops/pending?distributor_id={id}
    
    FLOW:
    1. Distributor views pending shop registrations
    2. Service gets all shops with registration_status="pending"
    3. Filters to shops created by order bookers belonging to the authenticated distributor
    4. Returns list for review
    
    Query Parameters:
        distributor_id: Required - Distributor ID
    
    Response (200):
        List of pending shops awaiting verification
    """
    # Verify distributor can only view their own pending shops
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view pending shops for your own distributor account"
        )
    
    try:
        from models.order_booker import OrderBooker
        # Filter pending shops by distributor: get shops created by order bookers belonging to this distributor
        order_booker_ids = db.query(OrderBooker.id).filter(
            OrderBooker.distributor_id == distributor_id,
            OrderBooker.deleted_at.is_(None),
            OrderBooker.is_active == True
        ).subquery()
        
        from models.shop import Shop
        shops = db.query(Shop).filter(
            Shop.registration_status == "pending",
            Shop.deleted_at.is_(None),
            Shop.is_active == True,
            Shop.created_by_order_booker.in_(db.query(order_booker_ids.c.id))
        ).all()
        result = []
        for shop in shops:
            # Get order booker name who created the shop (historical)
            created_by_name = None
            if shop.created_by_order_booker:
                order_booker = OrderBookerRepository.get_by_id(db, shop.created_by_order_booker)
                created_by_name = order_booker.name if order_booker else None
            
            # Get order booker name currently assigned to the shop
            assigned_to_name = None
            if shop.assigned_to_order_booker:
                assigned_order_booker = OrderBookerRepository.get_by_id(db, shop.assigned_to_order_booker)
                assigned_to_name = assigned_order_booker.name if assigned_order_booker else None
            
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
                "zone_id": shop.zone_id,
                "created_by_order_booker": shop.created_by_order_booker,
                "created_by_order_booker_name": created_by_name,  # Historical creator
                "assigned_to_order_booker": shop.assigned_to_order_booker,  # Current assignee
                "assigned_to_order_booker_name": assigned_to_name,  # Current assignee name
                "owner_cnic_front_photo": shop.owner_cnic_front_photo,
                "owner_cnic_back_photo": shop.owner_cnic_back_photo,
                "shop_exterior_photo": shop.shop_exterior_photo,
                "owner_photo": shop.owner_photo,
                "created_at": shop.created_at.isoformat() if shop.created_at else None
            })
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pending shops: {str(e)}"
        )


@router.get("/unassigned", response_model=List[ShopResponse])
async def get_unassigned_shops(
    zone_id: int = Query(None, description="Optional zone ID to filter unassigned shops"),
    distributor: Dict = Depends(get_current_distributor),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Get all unassigned shops (shops without an active order booker).
    
    API: GET /shops/unassigned?zone_id={id}
    
    FLOW:
    1. Distributor views shops that need to be reassigned
    2. Shops are unassigned if:
       - assigned_to_order_booker is NULL, OR
       - assigned_to_order_booker points to an inactive/deleted order booker
    3. Optionally filters by zone_id
    4. Returns list of unassigned shops with zone information
    
    Query Parameters:
        zone_id: Optional zone ID to filter shops by zone
    
    Response (200):
        List of unassigned shops with zone info
    
    Note:
        - Shops remain active and visible, but need reassignment
        - Zone matching is required when reassigning shops to order bookers
    """
    try:
        shops = ShopService.get_unassigned_shops(db=db, zone_id=zone_id)
        return shops
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching unassigned shops: {str(e)}"
        )


@router.get("/all", response_model=List[ShopResponse], tags=["Shops", "Distributor APIs"])
async def get_all_shops(
    distributor_id: int = Query(..., description="Distributor ID"),
    zone_id: int = Query(None, description="Optional zone filter"),
    route_id: int = Query(None, description="Optional route filter"),
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Get all shops with their associated order_booker and route information for the authenticated distributor.
    
    API: GET /shops/all?distributor_id={id}&zone_id={id}&route_id={id}
    
    FLOW:
    1. Gets all shops for the authenticated distributor (optionally filtered by zone_id or route_id)
    2. For each shop, includes order_booker who created it
    3. For each shop, includes routes it belongs to and their order_bookers
    4. Returns formatted list with all associations
    
    Query Parameters:
        distributor_id: Required - Distributor ID
        zone_id: Optional - Filter shops by zone
        route_id: Optional - Filter shops by route
    
    Response (200):
        List of shops with order_booker and route information
    """
    # Verify distributor can only view their own shops
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view shops for your own distributor account"
        )
    
    try:
        shops = ShopService.get_all_shops_with_associations(
            db=db,
            distributor_id=distributor_id,
            zone_id=zone_id,
            route_id=route_id
        )
        return shops
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in get_all_shops: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching shops: {str(e)}"
        )


@router.put("/{shop_id}", response_model=ShopResponse)
async def update_shop(
    shop_id: int,
    shop_update: ShopUpdate,
    distributor: Dict = Depends(get_current_distributor),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Update shop data (by Distributor).
    
    API: PUT /shops/{shop_id}
    
    FLOW:
    1. Distributor views pending shop
    2. Edits shop details (name, owner, GPS, credit_limit, etc.)
    3. Service updates shop fields
    4. Logs activity if credit_limit changed
    5. Returns updated shop
    
    Request Body:
        {
            "name": "Updated Shop Name",
            "owner_name": "Updated Owner",
            "credit_limit": 60000.00,
            ...
        }
    
    Response (200):
        Updated shop data
    """
    try:
        # Get shop before update for logging
        shop_before = ShopRepository.get_by_id(db, shop_id)
        if not shop_before:
            raise ValueError("Shop not found")
        
        old_credit_limit = float(shop_before.credit_limit) if shop_before.credit_limit else 0
        
        update_data = {}
        if shop_update.name:
            update_data["name"] = shop_update.name
        if shop_update.owner_name:
            update_data["owner_name"] = shop_update.owner_name
        if shop_update.owner_phone:
            update_data["owner_phone"] = shop_update.owner_phone
        if shop_update.gps_lat:
            update_data["gps_lat"] = Decimal(str(shop_update.gps_lat))
        if shop_update.gps_lng:
            update_data["gps_lng"] = Decimal(str(shop_update.gps_lng))
        if shop_update.credit_limit is not None:
            update_data["credit_limit"] = Decimal(str(shop_update.credit_limit))
        # legacy_balance removed from updates - column no longer exists
        # (legacy_balance input is only used during shop creation, where it's added to outstanding_balance)
        if shop_update.zone_id:
            update_data["zone_id"] = shop_update.zone_id
        
        updated_shop = ShopRepository.update(db=db, shop_id=shop_id, **update_data)
        if not updated_shop:
            raise ValueError("Shop not found")
        
        new_credit_limit = float(updated_shop.credit_limit) if updated_shop.credit_limit else 0
        
        # Log activity if credit_limit was changed
        if shop_update.credit_limit is not None and old_credit_limit != new_credit_limit:
            ActivityLogService.log_update(
                db=db,
                user_id=distributor['user_id'],
                user_role='distributor',
                entity_type='shop',
                entity_id=shop_id,
                old_values={
                    'credit_limit': str(old_credit_limit)
                },
                new_values={
                    'credit_limit': str(new_credit_limit)
                },
                changes_summary=f"Shop credit limit updated: {shop_before.name} - {old_credit_limit} → {new_credit_limit}",
                user_name=distributor.get('name'),
                request=request
            )
        
        # Get order booker name who created the shop (historical)
        created_by_name = None
        if updated_shop.created_by_order_booker:
            order_booker = OrderBookerRepository.get_by_id(db, updated_shop.created_by_order_booker)
            created_by_name = order_booker.name if order_booker else None
        
        # Get order booker name currently assigned to the shop
        assigned_to_name = None
        if updated_shop.assigned_to_order_booker:
            assigned_order_booker = OrderBookerRepository.get_by_id(db, updated_shop.assigned_to_order_booker)
            assigned_to_name = assigned_order_booker.name if assigned_order_booker else None
        
        return {
            "id": updated_shop.id,
            "name": updated_shop.name,
            "owner_name": updated_shop.owner_name,
            "owner_phone": updated_shop.owner_phone,
            "gps_lat": float(updated_shop.gps_lat) if updated_shop.gps_lat else None,
            "gps_lng": float(updated_shop.gps_lng) if updated_shop.gps_lng else None,
            "credit_limit": float(updated_shop.credit_limit) if updated_shop.credit_limit else 0,
            # legacy_balance removed (column no longer exists - was merged into outstanding_balance)
            "is_registered": updated_shop.is_registered,
            "registration_status": updated_shop.registration_status,
            "verified_by_distributor": updated_shop.verified_by_distributor,
            "verified_at": updated_shop.verified_at.isoformat() if updated_shop.verified_at else None,
            "zone_id": updated_shop.zone_id,
            "created_by_order_booker": updated_shop.created_by_order_booker,
            "created_by_order_booker_name": created_by_name,  # Historical creator
            "assigned_to_order_booker": updated_shop.assigned_to_order_booker,  # Current assignee
            "assigned_to_order_booker_name": assigned_to_name,  # Current assignee name
            "created_at": updated_shop.created_at.isoformat() if updated_shop.created_at else None
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{shop_id}/resubmit", response_model=ShopResponse)
async def resubmit_rejected_shop(
    shop_id: int,
    shop_update: ShopUpdate,
    request: Request,
    order_booker: Dict = Depends(get_current_order_booker),
    db: Session = Depends(get_db)
):
    """
    Resubmit a rejected shop for approval (by Order Booker).
    
    API: PUT /shops/{shop_id}/resubmit
    
    FLOW:
    1. Order Booker views rejected shop
    2. Edits shop details
    3. Resubmits for approval (status changes from "rejected" to "pending")
    4. Returns updated shop
    
    Request Body:
        {
            "name": "Updated Shop Name",
            "owner_name": "Updated Owner",
            "gps_lat": 33.6844,
            "gps_lng": 73.0479,
            "zone_id": 1,
            "route_id": 1,
            "credit_limit": 50000.00,
            ...
        }
    
    Response (200):
        Updated shop data with status "pending"
    """
    try:
        # Check if shop exists and is rejected
        shop = ShopRepository.get_by_id(db, shop_id)
        if not shop:
            raise ValueError("Shop not found")
        
        if shop.registration_status != "rejected":
            raise ValueError("Only rejected shops can be resubmitted")
        
        # Update shop data
        update_data = {}
        if shop_update.name:
            update_data["name"] = shop_update.name
        if shop_update.owner_name:
            update_data["owner_name"] = shop_update.owner_name
        if shop_update.owner_phone:
            update_data["owner_phone"] = shop_update.owner_phone
        if shop_update.gps_lat:
            update_data["gps_lat"] = Decimal(str(shop_update.gps_lat))
        if shop_update.gps_lng:
            update_data["gps_lng"] = Decimal(str(shop_update.gps_lng))
        if shop_update.credit_limit is not None:
            update_data["credit_limit"] = Decimal(str(shop_update.credit_limit))
        if shop_update.legacy_balance is not None:
            update_data["legacy_balance"] = Decimal(str(shop_update.legacy_balance))
        if shop_update.zone_id:
            update_data["zone_id"] = shop_update.zone_id
        
        # Change status back to pending
        update_data["registration_status"] = "pending"
        update_data["verified_by_distributor"] = None
        update_data["verified_at"] = None
        
        # Handle route assignment if route_id is provided
        route_id = None
        if hasattr(shop_update, 'route_id') and shop_update.route_id:
            route_id = shop_update.route_id
        
        # Store old values for logging
        old_values = {
            'name': shop.name,
            'registration_status': shop.registration_status,
            'credit_limit': str(shop.credit_limit) if shop.credit_limit else '0'
        }
        
        updated_shop = ShopService.update_and_resubmit_shop(
            db=db,
            shop_id=shop_id,
            route_id=route_id,
            **update_data
        )
        
        if not updated_shop:
            raise ValueError("Failed to update shop")
        
        # Get order booker name who created the shop (historical)
        created_by_name = None
        if updated_shop.created_by_order_booker:
            order_booker = OrderBookerRepository.get_by_id(db, updated_shop.created_by_order_booker)
            created_by_name = order_booker.name if order_booker else None
        
        # Get order booker name currently assigned to the shop
        assigned_to_name = None
        if updated_shop.assigned_to_order_booker:
            assigned_order_booker = OrderBookerRepository.get_by_id(db, updated_shop.assigned_to_order_booker)
            assigned_to_name = assigned_order_booker.name if assigned_order_booker else None
        
        # Log shop resubmission
        user_info = get_current_user_from_request(request)
        ActivityLogService.log_update(
            db=db,
            user_id=user_info['user_id'] if user_info else updated_shop.created_by_order_booker,
            user_role=user_info['user_role'] if user_info else 'order_booker',
            entity_type='shop',
            entity_id=shop_id,
            old_values=old_values,
            new_values={
                'name': updated_shop.name,
                'registration_status': updated_shop.registration_status,
                'credit_limit': str(updated_shop.credit_limit) if updated_shop.credit_limit else '0'
            },
            changes_summary=f"Shop resubmitted: {old_values['registration_status']} → {updated_shop.registration_status}",
            request=request
        )
        
        return {
            "id": updated_shop.id,
            "name": updated_shop.name,
            "owner_name": updated_shop.owner_name,
            "owner_phone": updated_shop.owner_phone,
            "gps_lat": float(updated_shop.gps_lat) if updated_shop.gps_lat else None,
            "gps_lng": float(updated_shop.gps_lng) if updated_shop.gps_lng else None,
            "credit_limit": float(updated_shop.credit_limit) if updated_shop.credit_limit else 0,
            # legacy_balance removed (column no longer exists - was merged into outstanding_balance)
            "is_registered": updated_shop.is_registered,
            "registration_status": updated_shop.registration_status,
            "verified_by_distributor": updated_shop.verified_by_distributor,
            "verified_at": updated_shop.verified_at.isoformat() if updated_shop.verified_at else None,
            "zone_id": updated_shop.zone_id,
            "created_by_order_booker": updated_shop.created_by_order_booker,
            "created_by_order_booker_name": created_by_name,  # Historical creator
            "assigned_to_order_booker": updated_shop.assigned_to_order_booker,  # Current assignee
            "assigned_to_order_booker_name": assigned_to_name,  # Current assignee name
            "created_at": updated_shop.created_at.isoformat() if updated_shop.created_at else None
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{shop_id}/verify", response_model=ShopResponse, tags=["Shops", "Distributor APIs"])
async def verify_shop(
    shop_id: int,
    verification: ShopVerify,
    distributor_id: int,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Verify/approve a shop registration (by Distributor).
    
    API: POST /shops/{shop_id}/verify?distributor_id={id}
    
    FLOW:
    1. Distributor reviews pending shop
    2. Can edit shop data before verifying
    3. Approves or rejects shop registration
    4. Service updates registration_status and sets verified_by/verified_at
    5. Returns verified shop
    
    Request Body:
        {
            "registration_status": "approved",  // or "rejected"
            "remarks": "Shop verified, all documents checked"
        }
    
    Response (200):
        Verified shop data with verified_by_distributor and verified_at
    """
    # Verify distributor can only verify shops for their own account
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only verify shops for your own distributor account"
        )
    
    try:
        # Get shop before verification for logging
        shop_before = ShopRepository.get_by_id(db, shop_id)
        if not shop_before:
            raise ValueError("Shop not found")
        
        old_status = shop_before.registration_status
        
        verified_shop = ShopRepository.verify_shop(
            db=db,
            shop_id=shop_id,
            distributor_id=distributor_id,
            registration_status=verification.registration_status
        )
        if not verified_shop:
            raise ValueError("Shop not found")
        
        # Get order booker name who created the shop (historical)
        created_by_name = None
        if verified_shop.created_by_order_booker:
            order_booker = OrderBookerRepository.get_by_id(db, verified_shop.created_by_order_booker)
            created_by_name = order_booker.name if order_booker else None
        
        # Get order booker name currently assigned to the shop
        assigned_to_name = None
        if verified_shop.assigned_to_order_booker:
            assigned_order_booker = OrderBookerRepository.get_by_id(db, verified_shop.assigned_to_order_booker)
            assigned_to_name = assigned_order_booker.name if assigned_order_booker else None
        
        # Log shop verification
        action_type = 'APPROVE' if verification.registration_status == 'approved' else 'REJECT'
        ActivityLogService.log_activity(
            db=db,
            user_id=distributor_id,
            user_role='distributor',
            action_type=action_type,
            entity_type='shop',
            entity_id=shop_id,
            old_values={'registration_status': old_status},
            new_values={'registration_status': verification.registration_status},
            changes_summary=f"Shop {action_type.lower()}d: {old_status} → {verification.registration_status}",
            reason=verification.remarks,
            request=request
        )
        
        return {
            "id": verified_shop.id,
            "name": verified_shop.name,
            "owner_name": verified_shop.owner_name,
            "owner_phone": verified_shop.owner_phone,
            "gps_lat": float(verified_shop.gps_lat) if verified_shop.gps_lat else None,
            "gps_lng": float(verified_shop.gps_lng) if verified_shop.gps_lng else None,
            "credit_limit": float(verified_shop.credit_limit) if verified_shop.credit_limit else 0,
            # legacy_balance removed (column no longer exists - was merged into outstanding_balance)
            "outstanding_balance": float(verified_shop.outstanding_balance) if verified_shop.outstanding_balance else 0,
            "is_registered": verified_shop.is_registered,
            "registration_status": verified_shop.registration_status,
            "verified_by_distributor": verified_shop.verified_by_distributor,
            "verified_at": verified_shop.verified_at.isoformat() if verified_shop.verified_at else None,
            "zone_id": verified_shop.zone_id,
            "created_by_order_booker": verified_shop.created_by_order_booker,
            "created_by_order_booker_name": created_by_name,  # Historical creator
            "assigned_to_order_booker": verified_shop.assigned_to_order_booker,  # Current assignee
            "assigned_to_order_booker_name": assigned_to_name,  # Current assignee name
            "created_at": verified_shop.created_at.isoformat() if verified_shop.created_at else None
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{shop_id}/reassign", response_model=ShopResponse)
async def reassign_shop_to_order_booker(
    shop_id: int,
    new_order_booker_id: int,
    distributor: Dict = Depends(get_current_distributor),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Manually reassign a shop to a different order booker.
    
    API: PUT /shops/{shop_id}/reassign?new_order_booker_id={id}
    
    FLOW:
    1. Distributor wants to reassign a shop to another order booker
    2. Updates assigned_to_order_booker field
    3. created_by_order_booker remains unchanged (for audit trail)
    4. Returns updated shop data
    
    Query Parameters:
        new_order_booker_id: Order booker ID to reassign shop to
    
    Response (200):
        Updated shop data with new assigned_to_order_booker
    
    Note: This is useful when shops need to be reassigned without deleting
    the original order booker, or for administrative reassignments.
    """
    try:
        # Verify shop exists
        shop = ShopRepository.get_by_id(db, shop_id)
        if not shop:
            raise ValueError("Shop not found")
        
        # Verify new order booker exists and is active
        new_order_booker = OrderBookerRepository.get_by_id(db, new_order_booker_id)
        if not new_order_booker:
            raise ValueError("Order Booker not found")
        
        # Validate zone matching: shop and order booker must be in the same zone
        if shop.zone_id and new_order_booker.zone_id:
            if shop.zone_id != new_order_booker.zone_id:
                raise ValueError(
                    f"Cannot reassign shop: Shop belongs to zone {shop.zone_id}, "
                    f"but order booker is assigned to zone {new_order_booker.zone_id}. "
                    f"They must be in the same zone."
                )
        elif shop.zone_id and not new_order_booker.zone_id:
            raise ValueError(
                f"Cannot reassign shop: Shop belongs to zone {shop.zone_id}, "
                f"but order booker has no zone assigned. "
                f"Please assign the order booker to zone {shop.zone_id} first."
            )
        elif not shop.zone_id and new_order_booker.zone_id:
            raise ValueError(
                f"Cannot reassign shop: Shop has no zone assigned, "
                f"but order booker is assigned to zone {new_order_booker.zone_id}. "
                f"Please assign the shop to a zone first."
            )
        # If both are None, allow assignment (though this is unusual)
        
        # Update assigned_to_order_booker (created_by_order_booker remains unchanged)
        updated_shop = ShopRepository.update(
            db=db,
            shop_id=shop_id,
            assigned_to_order_booker=new_order_booker_id
        )
        
        if not updated_shop:
            raise ValueError("Failed to update shop")
        
        # Get order booker names for response
        created_by_name = None
        if updated_shop.created_by_order_booker:
            created_order_booker = OrderBookerRepository.get_by_id(db, updated_shop.created_by_order_booker)
            created_by_name = created_order_booker.name if created_order_booker else None
        
        assigned_to_name = new_order_booker.name
        
        return {
            "id": updated_shop.id,
            "name": updated_shop.name,
            "owner_name": updated_shop.owner_name,
            "owner_phone": updated_shop.owner_phone,
            "gps_lat": float(updated_shop.gps_lat) if updated_shop.gps_lat else None,
            "gps_lng": float(updated_shop.gps_lng) if updated_shop.gps_lng else None,
            "credit_limit": float(updated_shop.credit_limit) if updated_shop.credit_limit else 0,
            "legacy_balance": float(updated_shop.legacy_balance) if updated_shop.legacy_balance else 0,
            "outstanding_balance": float(updated_shop.outstanding_balance) if updated_shop.outstanding_balance else 0,
            "is_registered": updated_shop.is_registered,
            "registration_status": updated_shop.registration_status,
            "verified_by_distributor": updated_shop.verified_by_distributor,
            "verified_at": updated_shop.verified_at.isoformat() if updated_shop.verified_at else None,
            "zone_id": updated_shop.zone_id,
            "created_by_order_booker": updated_shop.created_by_order_booker,
            "created_by_order_booker_name": created_by_name,  # Historical creator (unchanged)
            "assigned_to_order_booker": updated_shop.assigned_to_order_booker,  # Updated to new order booker
            "assigned_to_order_booker_name": assigned_to_name,  # New assignee name
            "created_at": updated_shop.created_at.isoformat() if updated_shop.created_at else None
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{shop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shop(
    shop_id: int,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Soft delete a shop (by Distributor).
    
    API: DELETE /shops/{shop_id}
    
    FLOW:
    1. Distributor requests to delete a shop
    2. Service soft deletes the shop (sets deleted_at timestamp)
    3. Shop is hidden from normal queries but data is preserved
    4. Activity is logged
    
    Response (204):
        No content on success
    
    Note:
        - This is a soft delete - data is preserved for audit
        - Shop will not appear in normal queries after deletion
        - Can be restored by setting deleted_at to NULL (manual DB operation)
    """
    try:
        ShopService.delete_shop(
            db=db,
            shop_id=shop_id,
            deleter_id=distributor['user_id'],
            request=request
        )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting shop: {str(e)}"
        )
