"""
Shop Visit Repository
=====================
Data access layer for Shop Visit database operations.

This repository handles all direct database interactions for the ShopVisit model.
It uses SQLAlchemy ORM to perform CRUD operations on the 'shop_visits' table.

ARCHITECTURE:
Router → Service → Repository → Database

This layer:
- Receives database session from Service layer
- Performs SQL queries via SQLAlchemy ORM
- Returns model instances or None
- No business logic (validation, etc.) - that's in Service layer
"""
from sqlalchemy.orm import Session
from models.shop_visit import ShopVisit
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class ShopVisitRepository:
    """
    Repository for Shop Visit database operations.
    
    This class contains static methods for all database operations on shop_visits table.
    Each method:
    1. Takes a database session and parameters
    2. Performs SQL query via SQLAlchemy
    3. Returns ShopVisit model instance(s) or None
    """
    
    @staticmethod
    def create(db: Session, shop_id: int = None, order_booker_id: int = None,
              delivery_man_id: int = None, visit_type: str = None,
              gps_lat: Decimal = None, gps_lng: Decimal = None,
              visit_time: datetime = None, photo: str = None,
              reason: str = None) -> ShopVisit:
        """
        Create a new shop visit record in the database.
        
        FLOW:
        1. Creates ShopVisit model instance with provided data
        2. Adds to database session (staged for commit)
        3. Commits transaction (saves to database)
        4. Refreshes instance to get auto-generated ID and timestamps
        5. Returns the created visit
        
        Args:
            db: SQLAlchemy database session
            shop_id: Shop ID that was visited (optional)
            order_booker_id: Order booker ID who made the visit (optional)
            delivery_man_id: Delivery man ID who made the visit (optional)
            visit_type: Type of visit (e.g., "order_booking", "delivery", "collection")
            gps_lat: GPS latitude where visit was recorded
            gps_lng: GPS longitude where visit was recorded
            visit_time: Timestamp when visit occurred (defaults to now if not provided)
            photo: Photo proof as base64 string or URL (optional)
            reason: Reason or notes for the visit (optional)
        
        Returns:
            ShopVisit: Created visit model instance with ID and timestamps
        
        Note:
            - At least one of order_booker_id or delivery_man_id should be provided
            - visit_time defaults to current time if not provided
        """
        # Use current time if visit_time not provided
        if visit_time is None:
            visit_time = datetime.utcnow()
        
        # Create model instance (maps to shop_visits table)
        visit = ShopVisit(
            shop_id=shop_id,
            order_booker_id=order_booker_id,
            delivery_man_id=delivery_man_id,
            visit_type=visit_type,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            visit_time=visit_time,
            photo=photo,
            reason=reason
        )
        # Add to session (staged, not yet saved)
        db.add(visit)
        # Commit transaction (saves to database)
        db.commit()
        # Refresh to get auto-generated fields (id)
        db.refresh(visit)
        return visit
    
    @staticmethod
    def get_by_id(db: Session, visit_id: int) -> Optional[ShopVisit]:
        """
        Get a shop visit by its ID.
        
        FLOW:
        1. Queries shop_visits table
        2. Filters by id = visit_id
        3. Returns first match or None
        
        Args:
            db: SQLAlchemy database session
            visit_id: Visit ID (primary key)
        
        Returns:
            Optional[ShopVisit]: Visit instance if found, None otherwise
        """
        # SQL: SELECT * FROM shop_visits WHERE id = visit_id LIMIT 1
        return db.query(ShopVisit).filter(ShopVisit.id == visit_id).first()
    
    @staticmethod
    def get_by_order_booker(db: Session, order_booker_id: int, 
                            skip: int = 0, limit: int = 100) -> List[ShopVisit]:
        """
        Get all visits made by an order booker.
        
        FLOW:
        1. Queries shop_visits table
        2. Filters by order_booker_id = order_booker_id
        3. Orders by visit_time descending (most recent first)
        4. Applies pagination (skip, limit)
        5. Returns list of visits
        
        Args:
            db: SQLAlchemy database session
            order_booker_id: Order booker ID
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[ShopVisit]: List of visit instances
        
        Usage:
            Used to show order booker's visit history
        """
        # SQL: SELECT * FROM shop_visits WHERE order_booker_id = order_booker_id 
        #      ORDER BY visit_time DESC OFFSET skip LIMIT limit
        return db.query(ShopVisit).filter(
            ShopVisit.order_booker_id == order_booker_id
        ).order_by(ShopVisit.visit_time.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_shop(db: Session, shop_id: int, skip: int = 0, limit: int = 100) -> List[ShopVisit]:
        """
        Get all visits to a specific shop.
        
        FLOW:
        1. Queries shop_visits table
        2. Filters by shop_id = shop_id
        3. Orders by visit_time descending (most recent first)
        4. Applies pagination (skip, limit)
        5. Returns list of visits
        
        Args:
            db: SQLAlchemy database session
            shop_id: Shop ID
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[ShopVisit]: List of visit instances
        
        Usage:
            Used to show shop's visit history
        """
        # SQL: SELECT * FROM shop_visits WHERE shop_id = shop_id 
        #      ORDER BY visit_time DESC OFFSET skip LIMIT limit
        return db.query(ShopVisit).filter(
            ShopVisit.shop_id == shop_id
        ).order_by(ShopVisit.visit_time.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_delivery_man(db: Session, delivery_man_id: int,
                            skip: int = 0, limit: int = 100) -> List[ShopVisit]:
        """
        Get all visits made by a delivery man.
        
        FLOW:
        1. Queries shop_visits table
        2. Filters by delivery_man_id = delivery_man_id
        3. Orders by visit_time descending (most recent first)
        4. Applies pagination (skip, limit)
        5. Returns list of visits
        
        Args:
            db: SQLAlchemy database session
            delivery_man_id: Delivery man ID
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[ShopVisit]: List of visit instances
        
        Usage:
            Used to show delivery man's visit history
        """
        # SQL: SELECT * FROM shop_visits WHERE delivery_man_id = delivery_man_id 
        #      ORDER BY visit_time DESC OFFSET skip LIMIT limit
        return db.query(ShopVisit).filter(
            ShopVisit.delivery_man_id == delivery_man_id
        ).order_by(ShopVisit.visit_time.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 1000) -> List[ShopVisit]:
        """
        Get all shop visits (for distributor view).
        
        FLOW:
        1. Queries shop_visits table
        2. Orders by visit_time descending (most recent first)
        3. Applies pagination (skip, limit)
        4. Returns list of visits
        
        Args:
            db: SQLAlchemy database session
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[ShopVisit]: List of visit instances
        
        Usage:
            Used by distributor to view all visits across all shops
        """
        # SQL: SELECT * FROM shop_visits 
        #      ORDER BY visit_time DESC OFFSET skip LIMIT limit
        return db.query(ShopVisit).order_by(
            ShopVisit.visit_time.desc()
        ).offset(skip).limit(limit).all()

