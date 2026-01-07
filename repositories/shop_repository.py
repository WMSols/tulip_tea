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
              zone_id: int = None, registration_status: str = "pending") -> Shop:
        """
        Create a new shop.
        
        IMPORTANT: When a shop is created, assigned_to_order_booker is automatically
        set to the same value as created_by_order_booker. This ensures the shop is
        initially assigned to its creator, but can be reassigned later without losing
        the historical record of who originally created it.
        
        Args:
            registration_status: Status of registration ("pending", "approved", "rejected")
            created_by_order_booker: Order booker who is registering the shop
        """
        shop = Shop(
            name=name,
            owner_name=owner_name,
            owner_phone=owner_phone,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            credit_limit=credit_limit or Decimal('0'),
            legacy_balance=legacy_balance or Decimal('0'),
            is_registered=False,  # Start as not registered
            registration_status=registration_status,  # New field
            created_by_order_booker=created_by_order_booker,
            assigned_to_order_booker=created_by_order_booker,  # Initially same as creator
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
        """
        Get all shops created by an order booker.
        
        Note: This returns shops based on created_by_order_booker (historical).
        For current assignments, use get_by_assigned_order_booker().
        """
        return db.query(Shop).filter(Shop.created_by_order_booker == order_booker_id).all()
    
    @staticmethod
    def get_by_assigned_order_booker(db: Session, order_booker_id: int) -> List[Shop]:
        """
        Get all shops currently assigned to an order booker.
        
        This method returns shops based on assigned_to_order_booker, which represents
        the current responsibility. This is different from get_by_order_booker() which
        returns shops based on who originally created them.
        
        Args:
            db: Database session
            order_booker_id: Order booker ID to filter by
        
        Returns:
            List of shops currently assigned to this order booker
        """
        return db.query(Shop).filter(Shop.assigned_to_order_booker == order_booker_id).all()
    
    @staticmethod
    def reassign_shops_to_order_booker(db: Session, from_order_booker_id: int, 
                                      to_order_booker_id: int) -> int:
        """
        Reassign all shops from one order booker to another.
        
        This updates assigned_to_order_booker for all shops currently assigned
        to from_order_booker_id, changing them to to_order_booker_id.
        The created_by_order_booker field remains unchanged for audit purposes.
        
        Args:
            db: Database session
            from_order_booker_id: Current order booker ID
            to_order_booker_id: New order booker ID to reassign to
        
        Returns:
            Number of shops reassigned
        """
        shops = db.query(Shop).filter(Shop.assigned_to_order_booker == from_order_booker_id).all()
        count = len(shops)
        
        for shop in shops:
            shop.assigned_to_order_booker = to_order_booker_id
        
        db.commit()
        return count
    
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
    def get_by_registration_status(db: Session, status: str) -> List[Shop]:
        """
        Get all shops by registration status.
        
        Args:
            db: Database session
            status: Registration status ("pending", "approved", "rejected")
        
        Returns:
            List of shops with the specified status
        """
        return db.query(Shop).filter(Shop.registration_status == status).order_by(Shop.created_at.desc()).all()
    
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
    
    @staticmethod
    def update(db: Session, shop_id: int, **kwargs) -> Optional[Shop]:
        """
        Update shop fields.
        
        Args:
            db: Database session
            shop_id: Shop ID to update
            **kwargs: Fields to update (name, owner_name, credit_limit, etc.)
        
        Returns:
            Updated shop instance or None if not found
        """
        shop = db.query(Shop).filter(Shop.id == shop_id).first()
        if not shop:
            return None
        
        # Update only provided fields
        for key, value in kwargs.items():
            if hasattr(shop, key) and value is not None:
                setattr(shop, key, value)
        
        db.commit()
        db.refresh(shop)
        return shop
    
    @staticmethod
    def verify_shop(db: Session, shop_id: int, distributor_id: int, 
                   registration_status: str = "approved") -> Optional[Shop]:
        """
        Verify/approve a shop registration.
        
        Args:
            db: Database session
            shop_id: Shop ID to verify
            distributor_id: Distributor ID who is verifying
            registration_status: Status to set ("approved" or "rejected")
        
        Returns:
            Updated shop instance or None if not found
        """
        from datetime import datetime
        
        shop = db.query(Shop).filter(Shop.id == shop_id).first()
        if not shop:
            return None
        
        shop.registration_status = registration_status
        shop.verified_by_distributor = distributor_id
        shop.verified_at = datetime.utcnow()
        shop.is_registered = (registration_status == "approved")
        
        db.commit()
        db.refresh(shop)
        return shop

