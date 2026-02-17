"""
Shop Visit Router
=================
Handles API endpoints for shop visit operations.

API ENDPOINTS:
- POST /shop-visits/order-booker/{order_booker_id} - Register a visit (Order Booker)
- GET /shop-visits/order-booker/{order_booker_id} - List visits by order booker
- GET /shop-visits/shop/{shop_id} - List visits to a shop

FLOW:
1. Order Booker visits a shop
2. Captures GPS coordinates (from device)
3. Optionally takes photo
4. Registers visit via API
5. Visit is stored with timestamp and location
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from config.database import get_db
from models.schemas import ShopVisitCreate, ShopVisitResponse
from services.shop_visit_service import ShopVisitService
from services.activity_log_service import ActivityLogService
from utils.dependencies import get_current_user, get_current_distributor, get_current_order_booker
from typing import Dict

router = APIRouter(prefix="/shop-visits", tags=["Shop Visits"])


@router.post("/order-booker/{order_booker_id}", response_model=ShopVisitResponse, status_code=status.HTTP_201_CREATED, tags=["Shop Visits", "Order Booker APIs"])
async def register_visit(
    order_booker_id: int,
    visit: ShopVisitCreate,
    request: Request,
    order_booker: Dict = Depends(get_current_order_booker),
    db: Session = Depends(get_db)
):
    """
    Register a shop visit (by Order Booker).
    
    API: POST /shop-visits/order-booker/{order_booker_id}
    
    FLOW:
    1. Order Booker visits a shop
    2. Captures GPS coordinates (from device)
    3. Optionally takes photo
    4. Fills visit form with details
    5. Service creates visit record
    6. Returns visit data
    
    Request Body:
        {
            "shop_id": 1,  // Optional
            "visit_type": "order_booking",  // Optional: "order_booking", "delivery", "collection", "inspection", "other"
            "gps_lat": 33.6844,  // Optional
            "gps_lng": 73.0479,  // Optional
            "visit_time": "2026-01-07T10:30:00",  // Optional (ISO format)
            "photo": "data:image/jpeg;base64,...",  // Optional (base64 or URL)
            "reason": "Regular order booking visit"  // Optional
        }
    
    Response (201):
        Visit data with ID and timestamps
    """
    # Verify order booker can only register visits for themselves
    if order_booker['user_id'] != order_booker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only register visits for your own account"
        )
    
    try:
        # Convert order_items from Pydantic models to dicts
        order_items_dicts = None
        if visit.order_items and len(visit.order_items) > 0:
            order_items_dicts = []
            for item in visit.order_items:
                # Convert Pydantic model to dict
                # Try model_dump() first (Pydantic v2), fallback to dict() (Pydantic v1)
                if hasattr(item, 'model_dump'):
                    item_dict = item.model_dump(exclude_unset=True)
                elif hasattr(item, 'dict'):
                    item_dict = item.dict(exclude_unset=True)
                else:
                    # If it's already a dict, use it directly
                    item_dict = dict(item) if not isinstance(item, dict) else item
                
                # Remove total_price if present (not in schema, calculated by backend)
                item_dict.pop('total_price', None)
                order_items_dicts.append(item_dict)
        
        # Convert final_total_amount to Decimal if provided
        final_total_decimal = None
        if visit.final_total_amount is not None:
            from decimal import Decimal
            final_total_decimal = Decimal(str(visit.final_total_amount))
        
        result = ShopVisitService.register_visit(
            db=db,
            shop_id=visit.shop_id,
            order_booker_id=order_booker_id,
            delivery_man_id=None,  # Order booker visits only
            visit_types=visit.visit_types or [],
            gps_lat=visit.gps_lat,
            gps_lng=visit.gps_lng,
            visit_time=visit.visit_time,  # API uses visit_time, service maps it to visit_date internally
            photo=visit.photo,
            reason=visit.reason,
            order_items=order_items_dicts,
            scheduled_date=visit.scheduled_date,
            collection_amount=visit.collection_amount,
            collection_remarks=visit.collection_remarks,
            final_total_amount=final_total_decimal,
            order_resolution_type=visit.order_resolution_type,
            subsidy_id=visit.subsidy_id
        )
        
        # Log visit registration
        ActivityLogService.log_create(
            db=db,
            user_id=order_booker_id,
            user_role='order_booker',
            entity_type='shop_visit',
            entity_id=result['id'],
            new_values={
                'shop_id': result.get('shop_id'),
                'shop_name': result.get('shop_name'),
                'visit_types': result.get('visit_types', [])
            },
            metadata={
                'order_id': result.get('order_id'),
                'collection_id': result.get('collection_id'),
                'gps_lat': str(result.get('gps_lat', '')) if result.get('gps_lat') else None,
                'gps_lng': str(result.get('gps_lng', '')) if result.get('gps_lng') else None,
                'has_photo': bool(result.get('photo'))
            },
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=order_booker['user_id'],
            user_role='order_booker',
            action_type='CREATE',
            entity_type='shop_visit',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        error_detail = f"Error registering visit: {str(e)}"
        print(f"ERROR in register_visit: {error_detail}")
        print(traceback.format_exc())
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=order_booker['user_id'],
            user_role='order_booker',
            action_type='CREATE',
            entity_type='shop_visit',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get("/order-booker/{order_booker_id}", response_model=List[ShopVisitResponse])
async def list_visits_by_order_booker(
    order_booker_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    order_booker: Dict = Depends(get_current_order_booker),
    db: Session = Depends(get_db)
):
    """
    List all visits made by an order booker.
    
    API: GET /shop-visits/order-booker/{order_booker_id}?skip=0&limit=100
    
    FLOW:
    1. Order Booker views their visit history
    2. Service gets all visits for this order booker
    3. Returns list with shop information
    
    Query Parameters:
        skip: Number of records to skip (for pagination, default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
    
    Response (200):
        List of visits with shop and order booker info
    """
    # Verify order booker can only view their own visits
    if order_booker['user_id'] != order_booker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view visits for your own account"
        )
    
    try:
        visits = ShopVisitService.get_visits_by_order_booker(
            db=db,
            order_booker_id=order_booker_id,
            skip=skip,
            limit=limit
        )
        return visits
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching visits: {str(e)}"
        )


@router.get("/shop/{shop_id}", response_model=List[ShopVisitResponse])
async def list_visits_by_shop(
    shop_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all visits to a specific shop.
    
    API: GET /shop-visits/shop/{shop_id}?skip=0&limit=100
    
    FLOW:
    1. View visit history for a specific shop
    2. Service gets all visits to this shop
    3. Returns list with visitor information
    
    Query Parameters:
        skip: Number of records to skip (for pagination, default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
    
    Response (200):
        List of visits with shop and visitor info
    """
    try:
        visits = ShopVisitService.get_visits_by_shop(
            db=db,
            shop_id=shop_id,
            skip=skip,
            limit=limit
        )
        return visits
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching visits: {str(e)}"
        )


@router.get("/all", response_model=List[ShopVisitResponse], tags=["Shop Visits", "Distributor APIs"])
async def list_all_visits(
    distributor_id: int = Query(None, description="Optional distributor ID to filter visits"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of records to return"),
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    List all shop visits (for distributor view).
    
    API: GET /shop-visits/all?distributor_id={id}&skip=0&limit=1000
    
    FLOW:
    1. Distributor views all visits across all shops
    2. If distributor_id is provided, filters to visits by order bookers/delivery men belonging to this distributor
    3. Service gets all visits with shop and visitor information
    4. Returns list categorized by zone (frontend handles grouping)
    
    Query Parameters:
        distributor_id: Optional - Filter visits by distributor (visits by their order bookers/delivery men)
        skip: Number of records to skip (for pagination, default: 0)
        limit: Maximum number of records to return (default: 1000, max: 5000)
    
    Response (200):
        List of all visits with shop, visitor, and zone info
    """
    # Verify distributor can only view visits for their own account if distributor_id is provided
    if distributor_id is not None and distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view visits for your own distributor account"
        )
    
    try:
        visits = ShopVisitService.get_all_visits(
            db=db,
            distributor_id=distributor_id,
            skip=skip,
            limit=limit
        )
        return visits
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching visits: {str(e)}"
        )

