"""
Shop repository.
Data access layer for Shop operations.
"""
from sqlalchemy.orm import Session
from models.shop import Shop
from typing import Optional, List
from decimal import Decimal


class ShopRepository:
    """Repository for Shop database operations."""
    
    @staticmethod
    def create(db: Session, name: str, owner_name: str = None, owner_phone: str = None,
              gps_lat: Decimal = None, gps_lng: Decimal = None, credit_limit: Decimal = None,
              legacy_balance: Decimal = None, created_by_order_booker: int = None,
              zone_id: int = None) -> Shop:
        """Create a new shop."""
        shop = Shop(
            name=name,
            owner_name=owner_name,
            owner_phone=owner_phone,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            credit_limit=credit_limit or Decimal('0'),
            legacy_balance=legacy_balance or Decimal('0'),
            is_registered=True,
            created_by_order_booker=created_by_order_booker,
            zone_id=zone_id
        )
        db.add(shop)
        db.commit()
        db.refresh(shop)
        return shop
    
    @staticmethod
    def get_by_id(db: Session, shop_id: int) -> Optional[Shop]:
        """Get shop by ID."""
        return db.query(Shop).filter(Shop.id == shop_id).first()
    
    @staticmethod
    def get_by_order_booker(db: Session, order_booker_id: int) -> List[Shop]:
        """Get all shops created by an order booker."""
        return db.query(Shop).filter(Shop.created_by_order_booker == order_booker_id).all()
    
    @staticmethod
    def get_by_zone(db: Session, zone_id: int) -> List[Shop]:
        """Get all shops in a zone."""
        return db.query(Shop).filter(Shop.zone_id == zone_id).all()
    
    @staticmethod
    def get_by_route(db: Session, route_id: int) -> List[Shop]:
        """Get all shops in a route."""
        from models.route_shop import RouteShop
        route_shops = db.query(RouteShop).filter(RouteShop.route_id == route_id).all()
        shop_ids = [rs.shop_id for rs in route_shops]
        return db.query(Shop).filter(Shop.id.in_(shop_ids)).all() if shop_ids else []
    
    @staticmethod
    def update_registration_status(db: Session, shop_id: int, is_registered: bool) -> bool:
        """Update shop registration status."""
        shop = db.query(Shop).filter(Shop.id == shop_id).first()
        if not shop:
            return False
        shop.is_registered = is_registered
        db.commit()
        db.refresh(shop)
        return True

