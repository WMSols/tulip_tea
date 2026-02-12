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
        # Legacy balance input is now added directly to outstanding_balance
        # (legacy_balance column has been removed from database)
        legacy_balance_val = legacy_balance or Decimal('0')
        shop = Shop(
            name=name,
            owner_name=owner_name,
            owner_phone=owner_phone,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            credit_limit=credit_limit or Decimal('0'),
            outstanding_balance=legacy_balance_val,  # Legacy balance input goes directly to outstanding_balance
            is_registered=False,  # Start as not registered
            registration_status=registration_status,  # New field
            created_by_order_booker=created_by_order_booker,
            assigned_to_order_booker=created_by_order_booker,  # Initially same as creator
            zone_id=zone_id
        )
        db.add(shop)
        # Do NOT commit - let service layer handle transaction
        # Note: shop.id will be available after flush, but commit happens in service
        db.flush()  # Flush to get shop.id without committing
        return shop
    
    @staticmethod
    def get_by_id(db: Session, shop_id: int, include_deleted: bool = False) -> Optional[Shop]:
        """Get shop by ID (excludes soft-deleted and inactive by default)."""
        query = db.query(Shop).filter(Shop.id == shop_id)
        if not include_deleted:
            query = query.filter(Shop.deleted_at.is_(None), Shop.is_active == True)
        return query.first()
    
    @staticmethod
    def get_by_order_booker(db: Session, order_booker_id: int, include_deleted: bool = False) -> List[Shop]:
        """
        Get all shops created by an order booker (excludes soft-deleted and inactive by default).
        
        Note: This returns shops based on created_by_order_booker (historical).
        For current assignments, use get_by_assigned_order_booker().
        """
        query = db.query(Shop).filter(Shop.created_by_order_booker == order_booker_id)
        if not include_deleted:
            query = query.filter(Shop.deleted_at.is_(None), Shop.is_active == True)
        return query.all()
    
    @staticmethod
    def get_by_assigned_order_booker(db: Session, order_booker_id: int, include_deleted: bool = False) -> List[Shop]:
        """
        Get all shops currently assigned to an order booker (excludes soft-deleted and inactive by default).
        
        This method returns shops based on assigned_to_order_booker, which represents
        the current responsibility. This is different from get_by_order_booker() which
        returns shops based on who originally created them.
        
        Args:
            db: Database session
            order_booker_id: Order booker ID to filter by
            include_deleted: If True, includes soft-deleted and inactive records
        
        Returns:
            List of shops currently assigned to this order booker
        """
        query = db.query(Shop).filter(Shop.assigned_to_order_booker == order_booker_id)
        if not include_deleted:
            query = query.filter(Shop.deleted_at.is_(None), Shop.is_active == True)
        return query.all()
    
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
    def get_by_zone(db: Session, zone_id: int, include_deleted: bool = False) -> List[Shop]:
        """Get all shops in a zone (excludes soft-deleted and inactive by default)."""
        query = db.query(Shop).filter(Shop.zone_id == zone_id)
        if not include_deleted:
            query = query.filter(Shop.deleted_at.is_(None), Shop.is_active == True)
        return query.all()
    
    @staticmethod
    def get_by_route(db: Session, route_id: int, include_deleted: bool = False) -> List[Shop]:
        """
        Get all shops in a route (excludes soft-deleted and inactive by default).
        
        NOTE: Shops now have route_id directly on the shops table (not via route_shops junction table).
        """
        query = db.query(Shop).filter(Shop.route_id == route_id)
        if not include_deleted:
            query = query.filter(Shop.deleted_at.is_(None), Shop.is_active == True)
        return query.order_by(Shop.route_sequence.asc()).all()
    
    @staticmethod
    def get_by_routes(db: Session, route_ids: List[int], include_deleted: bool = False) -> List[Shop]:
        """
        Batch load all shops for multiple routes (optimized to avoid N+1 queries).
        
        Args:
            db: Database session
            route_ids: List of route IDs to fetch shops for
            include_deleted: If True, includes soft-deleted and inactive records
        
        Returns:
            List of shops from all specified routes
        """
        if not route_ids:
            return []
        
        query = db.query(Shop).filter(Shop.route_id.in_(route_ids))
        if not include_deleted:
            query = query.filter(Shop.deleted_at.is_(None), Shop.is_active == True)
        return query.order_by(Shop.route_id, Shop.route_sequence.asc()).all()
    
    @staticmethod
    def get_by_registration_status(db: Session, status: str, include_deleted: bool = False) -> List[Shop]:
        """
        Get all shops by registration status (excludes soft-deleted and inactive by default).
        
        Args:
            db: Database session
            status: Registration status ("pending", "approved", "rejected")
            include_deleted: If True, includes soft-deleted and inactive records
        
        Returns:
            List of shops with the specified status
        """
        query = db.query(Shop).filter(Shop.registration_status == status)
        if not include_deleted:
            query = query.filter(Shop.deleted_at.is_(None), Shop.is_active == True)
        return query.order_by(Shop.created_at.desc()).all()
    
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
        
        Note: Does NOT commit - caller must commit transaction
        """
        shop = db.query(Shop).filter(Shop.id == shop_id).first()
        if not shop:
            return None
        
        # Update only provided fields
        for key, value in kwargs.items():
            if hasattr(shop, key) and value is not None:
                setattr(shop, key, value)
        
        # Do NOT commit - let service layer handle transaction
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
    
    @staticmethod
    def delete(db: Session, shop_id: int) -> bool:
        """Soft delete a shop (sets deleted_at timestamp)."""
        from datetime import datetime
        shop = db.query(Shop).filter(
            Shop.id == shop_id,
            Shop.deleted_at.is_(None)
        ).first()
        if not shop:
            return False
        shop.deleted_at = datetime.utcnow()
        shop.is_active = False  # Also deactivate when soft deleting
        db.commit()
        db.refresh(shop)
        return True

