"""
Shop Visit Business Logic Service
==================================
Business logic layer for Shop Visit operations.

This service handles:
- Validation of visit data
- Business rules (e.g., GPS validation)
- Formatting responses
- Error handling

ARCHITECTURE:
Router → Service → Repository → Database

This layer:
- Receives requests from Router layer
- Validates business rules
- Calls Repository layer for database operations
- Formats data for responses
- Handles errors and raises appropriate exceptions
"""
from sqlalchemy.orm import Session
from repositories.shop_visit_repository import ShopVisitRepository
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.delivery_man_repository import DeliveryManRepository
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime


class ShopVisitService:
    """Service for Shop Visit business logic."""
    
    @staticmethod
    def register_visit(db: Session, shop_id: int = None, order_booker_id: int = None,
                      delivery_man_id: int = None, visit_type: str = None,
                      gps_lat: float = None, gps_lng: float = None,
                      visit_time: str = None, photo: str = None,
                      reason: str = None) -> Dict:
        """
        Register a new shop visit.
        
        FLOW:
        1. Validates that at least one of order_booker_id or delivery_man_id is provided
        2. Validates shop exists (if shop_id provided)
        3. Validates order booker exists (if order_booker_id provided)
        4. Converts GPS coordinates to Decimal
        5. Parses visit_time if provided
        6. Creates visit record
        7. Returns formatted visit data
        
        Args:
            db: Database session
            shop_id: Shop ID that was visited (optional)
            order_booker_id: Order booker ID who made the visit (optional)
            delivery_man_id: Delivery man ID who made the visit (optional)
            visit_type: Type of visit (e.g., "order_booking", "delivery", "collection")
            gps_lat: GPS latitude where visit was recorded
            gps_lng: GPS longitude where visit was recorded
            visit_time: Timestamp when visit occurred (ISO format string, optional)
            photo: Photo proof as base64 string or URL (optional)
            reason: Reason or notes for the visit (optional)
        
        Returns:
            Dict: Visit data with ID and timestamps
        
        Raises:
            ValueError: If validation fails
        """
        # Validate that at least one of order_booker_id or delivery_man_id is provided
        if not order_booker_id and not delivery_man_id:
            raise ValueError("Either order_booker_id or delivery_man_id must be provided")
        
        # Validate shop exists if shop_id provided
        if shop_id:
            shop = ShopRepository.get_by_id(db, shop_id)
            if not shop:
                raise ValueError("Shop not found")
        
        # Validate order booker exists if order_booker_id provided
        if order_booker_id:
            order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
            if not order_booker:
                raise ValueError("Order Booker not found")
        
        # Convert GPS coordinates to Decimal
        gps_lat_decimal = Decimal(str(gps_lat)) if gps_lat is not None else None
        gps_lng_decimal = Decimal(str(gps_lng)) if gps_lng is not None else None
        
        # Parse visit_time if provided
        visit_time_datetime = None
        if visit_time:
            try:
                # Try parsing ISO format
                visit_time_datetime = datetime.fromisoformat(visit_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError("Invalid visit_time format. Use ISO format (e.g., 2026-01-07T10:30:00)")
        
        # Create visit
        visit = ShopVisitRepository.create(
            db=db,
            shop_id=shop_id,
            order_booker_id=order_booker_id,
            delivery_man_id=delivery_man_id,
            visit_type=visit_type,
            gps_lat=gps_lat_decimal,
            gps_lng=gps_lng_decimal,
            visit_time=visit_time_datetime,
            photo=photo,
            reason=reason
        )
        
        # Get shop name for response
        shop_name = None
        if visit.shop_id:
            shop = ShopRepository.get_by_id(db, visit.shop_id)
            shop_name = shop.name if shop else None
        
        # Get order booker name for response
        order_booker_name = None
        if visit.order_booker_id:
            order_booker = OrderBookerRepository.get_by_id(db, visit.order_booker_id)
            order_booker_name = order_booker.name if order_booker else None
        
        # Get delivery man name for response
        delivery_man_name = None
        if visit.delivery_man_id:
            delivery_man = DeliveryManRepository.get_by_id(db, visit.delivery_man_id)
            delivery_man_name = delivery_man.name if delivery_man else None
        
        # Get shop zone_id for response
        shop_zone_id = None
        if visit.shop_id:
            shop = ShopRepository.get_by_id(db, visit.shop_id)
            shop_zone_id = shop.zone_id if shop else None
        
        return {
            "id": visit.id,
            "shop_id": visit.shop_id,
            "shop_name": shop_name,
            "shop_zone_id": shop_zone_id,
            "order_booker_id": visit.order_booker_id,
            "order_booker_name": order_booker_name,
            "delivery_man_id": visit.delivery_man_id,
            "delivery_man_name": delivery_man_name,
            "visit_type": visit.visit_type,
            "gps_lat": float(visit.gps_lat) if visit.gps_lat else None,
            "gps_lng": float(visit.gps_lng) if visit.gps_lng else None,
            "visit_time": visit.visit_time.isoformat() if visit.visit_time else None,
            "photo": visit.photo,
            "reason": visit.reason
            # Note: created_at is not in the database schema, using visit_time for timestamp
        }
    
    @staticmethod
    def get_visits_by_order_booker(db: Session, order_booker_id: int,
                                   skip: int = 0, limit: int = 100) -> List[Dict]:
        """
        Get all visits made by an order booker.
        
        FLOW:
        1. Gets visits from repository
        2. For each visit, fetches shop and order booker information
        3. Returns formatted list
        
        Args:
            db: Database session
            order_booker_id: Order booker ID
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[Dict]: List of visits with shop and order booker info
        """
        visits = ShopVisitRepository.get_by_order_booker(db, order_booker_id, skip, limit)
        
        result = []
        for visit in visits:
            # Get shop name
            shop_name = None
            if visit.shop_id:
                shop = ShopRepository.get_by_id(db, visit.shop_id)
                shop_name = shop.name if shop else None
            
            # Get order booker name
            order_booker_name = None
            if visit.order_booker_id:
                order_booker = OrderBookerRepository.get_by_id(db, visit.order_booker_id)
                order_booker_name = order_booker.name if order_booker else None
            
            # Get delivery man name
            delivery_man_name = None
            if visit.delivery_man_id:
                delivery_man = DeliveryManRepository.get_by_id(db, visit.delivery_man_id)
                delivery_man_name = delivery_man.name if delivery_man else None
            
            # Get shop zone_id
            shop_zone_id = None
            if visit.shop_id:
                shop = ShopRepository.get_by_id(db, visit.shop_id)
                shop_zone_id = shop.zone_id if shop else None
            
            result.append({
                "id": visit.id,
                "shop_id": visit.shop_id,
                "shop_name": shop_name,
                "shop_zone_id": shop_zone_id,
                "order_booker_id": visit.order_booker_id,
                "order_booker_name": order_booker_name,
                "delivery_man_id": visit.delivery_man_id,
                "delivery_man_name": delivery_man_name,
                "visit_type": visit.visit_type,
                "gps_lat": float(visit.gps_lat) if visit.gps_lat else None,
                "gps_lng": float(visit.gps_lng) if visit.gps_lng else None,
                "visit_time": visit.visit_time.isoformat() if visit.visit_time else None,
                "photo": visit.photo,
                "reason": visit.reason
                # Note: created_at is not in the database schema, using visit_time for timestamp
            })
        
        return result
    
    @staticmethod
    def get_visits_by_shop(db: Session, shop_id: int,
                           skip: int = 0, limit: int = 100) -> List[Dict]:
        """
        Get all visits to a specific shop.
        
        FLOW:
        1. Gets visits from repository
        2. For each visit, fetches shop and order booker/delivery man information
        3. Returns formatted list
        
        Args:
            db: Database session
            shop_id: Shop ID
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[Dict]: List of visits with shop and visitor info
        """
        visits = ShopVisitRepository.get_by_shop(db, shop_id, skip, limit)
        
        result = []
        for visit in visits:
            # Get shop name
            shop = ShopRepository.get_by_id(db, visit.shop_id)
            shop_name = shop.name if shop else None
            
            # Get order booker name
            order_booker_name = None
            if visit.order_booker_id:
                order_booker = OrderBookerRepository.get_by_id(db, visit.order_booker_id)
                order_booker_name = order_booker.name if order_booker else None
            
            # Get delivery man name
            delivery_man_name = None
            if visit.delivery_man_id:
                delivery_man = DeliveryManRepository.get_by_id(db, visit.delivery_man_id)
                delivery_man_name = delivery_man.name if delivery_man else None
            
            # Get shop zone_id
            shop_zone_id = None
            if visit.shop_id:
                shop = ShopRepository.get_by_id(db, visit.shop_id)
                shop_zone_id = shop.zone_id if shop else None
            
            result.append({
                "id": visit.id,
                "shop_id": visit.shop_id,
                "shop_name": shop_name,
                "shop_zone_id": shop_zone_id,
                "order_booker_id": visit.order_booker_id,
                "order_booker_name": order_booker_name,
                "delivery_man_id": visit.delivery_man_id,
                "delivery_man_name": delivery_man_name,
                "visit_type": visit.visit_type,
                "gps_lat": float(visit.gps_lat) if visit.gps_lat else None,
                "gps_lng": float(visit.gps_lng) if visit.gps_lng else None,
                "visit_time": visit.visit_time.isoformat() if visit.visit_time else None,
                "photo": visit.photo,
                "reason": visit.reason
                # Note: created_at is not in the database schema, using visit_time for timestamp
            })
        
        return result
    
    @staticmethod
    def get_all_visits(db: Session, skip: int = 0, limit: int = 1000) -> List[Dict]:
        """
        Get all shop visits with shop and visitor information.
        
        FLOW:
        1. Gets all visits from repository
        2. For each visit, fetches shop, order booker, and delivery man information
        3. Returns formatted list with zone information
        
        Args:
            db: Database session
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[Dict]: List of visits with shop, visitor, and zone info
        """
        visits = ShopVisitRepository.get_all(db, skip, limit)
        
        result = []
        for visit in visits:
            # Get shop name and zone
            shop_name = None
            shop_zone_id = None
            if visit.shop_id:
                shop = ShopRepository.get_by_id(db, visit.shop_id)
                if shop:
                    shop_name = shop.name
                    shop_zone_id = shop.zone_id
            
            # Get order booker name
            order_booker_name = None
            if visit.order_booker_id:
                order_booker = OrderBookerRepository.get_by_id(db, visit.order_booker_id)
                order_booker_name = order_booker.name if order_booker else None
            
            # Get delivery man name
            delivery_man_name = None
            if visit.delivery_man_id:
                delivery_man = DeliveryManRepository.get_by_id(db, visit.delivery_man_id)
                delivery_man_name = delivery_man.name if delivery_man else None
            
            result.append({
                "id": visit.id,
                "shop_id": visit.shop_id,
                "shop_name": shop_name,
                "shop_zone_id": shop_zone_id,
                "order_booker_id": visit.order_booker_id,
                "order_booker_name": order_booker_name,
                "delivery_man_id": visit.delivery_man_id,
                "delivery_man_name": delivery_man_name,
                "visit_type": visit.visit_type,
                "gps_lat": float(visit.gps_lat) if visit.gps_lat else None,
                "gps_lng": float(visit.gps_lng) if visit.gps_lng else None,
                "visit_time": visit.visit_time.isoformat() if visit.visit_time else None,
                "photo": visit.photo,
                "reason": visit.reason
            })
        
        return result

