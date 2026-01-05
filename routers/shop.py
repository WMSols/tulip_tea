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
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from config.database import get_db
from models.schemas import ShopRegister, ShopResponse, ShopUpdate, ShopVerify
from services.shop_service import ShopService
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository

router = APIRouter(prefix="/shops", tags=["Shops"])


@router.post("/order-booker/{order_booker_id}", response_model=ShopResponse, status_code=status.HTTP_201_CREATED)
async def register_shop(
    order_booker_id: int,
    shop: ShopRegister,
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
        result = ShopService.register_shop(
            db=db,
            name=shop.name,
            owner_name=shop.owner_name,
            owner_phone=shop.owner_phone,
            gps_lat=Decimal(str(shop.gps_lat)),
            gps_lng=Decimal(str(shop.gps_lng)),
            order_booker_id=order_booker_id,
            zone_id=shop.zone_id,
            credit_limit=Decimal(str(shop.credit_limit)) if shop.credit_limit else None,
            legacy_balance=Decimal(str(shop.legacy_balance)) if shop.legacy_balance else None
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/order-booker/{order_booker_id}", response_model=List[ShopResponse])
async def list_shops_by_order_booker(order_booker_id: int, db: Session = Depends(get_db)):
    """
    List all shops registered by an order booker.
    
    API: GET /shops/order-booker/{order_booker_id}
    
    Response (200):
        List of shops with their details
    """
    shops = ShopService.get_shops_by_order_booker(db=db, order_booker_id=order_booker_id)
    return shops


@router.get("/pending", response_model=List[ShopResponse])
async def list_pending_shops(db: Session = Depends(get_db)):
    """
    List all shops with pending registration status.
    
    API: GET /shops/pending
    
    FLOW:
    1. Distributor views pending shop registrations
    2. Service gets all shops with registration_status="pending"
    3. Returns list for review
    
    Response (200):
        List of pending shops awaiting verification
    """
    try:
        shops = ShopRepository.get_by_registration_status(db=db, status="pending")
        result = []
        for shop in shops:
            # Get order booker name if exists
            created_by_name = None
            if shop.created_by_order_booker:
                order_booker = OrderBookerRepository.get_by_id(db, shop.created_by_order_booker)
                created_by_name = order_booker.name if order_booker else None
            
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
                "zone_id": shop.zone_id,
                "created_by_order_booker": shop.created_by_order_booker,
                "created_by_order_booker_name": created_by_name,
                "created_at": shop.created_at.isoformat() if shop.created_at else None
            })
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pending shops: {str(e)}"
        )


@router.put("/{shop_id}", response_model=ShopResponse)
async def update_shop(
    shop_id: int,
    shop_update: ShopUpdate,
    db: Session = Depends(get_db)
):
    """
    Update shop data (by Distributor).
    
    API: PUT /shops/{shop_id}
    
    FLOW:
    1. Distributor views pending shop
    2. Edits shop details (name, owner, GPS, credit_limit, etc.)
    3. Service updates shop fields
    4. Returns updated shop
    
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
        
        updated_shop = ShopRepository.update(db=db, shop_id=shop_id, **update_data)
        if not updated_shop:
            raise ValueError("Shop not found")
        
        # Get order booker name if exists
        created_by_name = None
        if updated_shop.created_by_order_booker:
            order_booker = OrderBookerRepository.get_by_id(db, updated_shop.created_by_order_booker)
            created_by_name = order_booker.name if order_booker else None
        
        return {
            "id": updated_shop.id,
            "name": updated_shop.name,
            "owner_name": updated_shop.owner_name,
            "owner_phone": updated_shop.owner_phone,
            "gps_lat": float(updated_shop.gps_lat) if updated_shop.gps_lat else None,
            "gps_lng": float(updated_shop.gps_lng) if updated_shop.gps_lng else None,
            "credit_limit": float(updated_shop.credit_limit) if updated_shop.credit_limit else 0,
            "legacy_balance": float(updated_shop.legacy_balance) if updated_shop.legacy_balance else 0,
            "is_registered": updated_shop.is_registered,
            "registration_status": updated_shop.registration_status,
            "verified_by_distributor": updated_shop.verified_by_distributor,
            "verified_at": updated_shop.verified_at.isoformat() if updated_shop.verified_at else None,
            "zone_id": updated_shop.zone_id,
            "created_by_order_booker": updated_shop.created_by_order_booker,
            "created_by_order_booker_name": created_by_name,
            "created_at": updated_shop.created_at.isoformat() if updated_shop.created_at else None
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{shop_id}/verify", response_model=ShopResponse)
async def verify_shop(
    shop_id: int,
    verification: ShopVerify,
    distributor_id: int,
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
    try:
        verified_shop = ShopRepository.verify_shop(
            db=db,
            shop_id=shop_id,
            distributor_id=distributor_id,
            registration_status=verification.registration_status
        )
        if not verified_shop:
            raise ValueError("Shop not found")
        
        # Get order booker name if exists
        created_by_name = None
        if verified_shop.created_by_order_booker:
            order_booker = OrderBookerRepository.get_by_id(db, verified_shop.created_by_order_booker)
            created_by_name = order_booker.name if order_booker else None
        
        return {
            "id": verified_shop.id,
            "name": verified_shop.name,
            "owner_name": verified_shop.owner_name,
            "owner_phone": verified_shop.owner_phone,
            "gps_lat": float(verified_shop.gps_lat) if verified_shop.gps_lat else None,
            "gps_lng": float(verified_shop.gps_lng) if verified_shop.gps_lng else None,
            "credit_limit": float(verified_shop.credit_limit) if verified_shop.credit_limit else 0,
            "legacy_balance": float(verified_shop.legacy_balance) if verified_shop.legacy_balance else 0,
            "is_registered": verified_shop.is_registered,
            "registration_status": verified_shop.registration_status,
            "verified_by_distributor": verified_shop.verified_by_distributor,
            "verified_at": verified_shop.verified_at.isoformat() if verified_shop.verified_at else None,
            "zone_id": verified_shop.zone_id,
            "created_by_order_booker": verified_shop.created_by_order_booker,
            "created_by_order_booker_name": created_by_name,
            "created_at": verified_shop.created_at.isoformat() if verified_shop.created_at else None
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

