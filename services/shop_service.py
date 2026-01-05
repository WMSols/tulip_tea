"""
Shop business logic service.
"""
from sqlalchemy.orm import Session
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.zone_repository import ZoneRepository
from repositories.credit_limit_request_repository import CreditLimitRequestRepository
from decimal import Decimal
from typing import Dict, List, Optional


class ShopService:
    """Service for Shop business logic."""
    
    @staticmethod
    def register_shop(db: Session, name: str, owner_name: str, owner_phone: str,
                      gps_lat: Decimal, gps_lng: Decimal, order_booker_id: int,
                      zone_id: int = None, credit_limit: Decimal = None,
                      legacy_balance: Decimal = None) -> Dict:
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
            "created_by_order_booker_name": order_booker.name,  # Include order booker name
            "credit_limit_request_id": credit_limit_request_id,  # Include request ID if created
            "created_at": shop.created_at.isoformat() if shop.created_at else None
        }
    
    @staticmethod
    def get_shops_by_order_booker(db: Session, order_booker_id: int) -> List[Dict]:
        """Get all shops registered by an order booker."""
        shops = ShopRepository.get_by_order_booker(db, order_booker_id)
        
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
                "created_at": shop.created_at.isoformat() if shop.created_at else None
            }
            for shop in shops
        ]

