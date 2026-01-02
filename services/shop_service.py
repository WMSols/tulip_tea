"""
Shop business logic service.
"""
from sqlalchemy.orm import Session
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.zone_repository import ZoneRepository
from decimal import Decimal
from typing import Dict, List


class ShopService:
    """Service for Shop business logic."""
    
    @staticmethod
    def register_shop(db: Session, name: str, owner_name: str, owner_phone: str,
                      gps_lat: Decimal, gps_lng: Decimal, order_booker_id: int,
                      zone_id: int = None, credit_limit: Decimal = None,
                      legacy_balance: Decimal = None) -> Dict:
        """Register a new shop."""
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
        
        shop = ShopRepository.create(
            db=db,
            name=name,
            owner_name=owner_name,
            owner_phone=owner_phone,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            credit_limit=credit_limit or Decimal('0'),
            legacy_balance=legacy_balance or Decimal('0'),
            created_by_order_booker=order_booker_id,
            zone_id=zone_id
        )
        
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
            "zone_id": shop.zone_id,
            "created_by_order_booker": shop.created_by_order_booker,
            "created_at": shop.created_at.isoformat() if shop.created_at else None
        }
    
    @staticmethod
    def get_shops_by_order_booker(db: Session, order_booker_id: int) -> List[Dict]:
        """Get all shops registered by an order booker."""
        shops = ShopRepository.get_by_order_booker(db, order_booker_id)
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
                "zone_id": shop.zone_id,
                "created_by_order_booker": shop.created_by_order_booker,
                "created_at": shop.created_at.isoformat() if shop.created_at else None
            }
            for shop in shops
        ]

