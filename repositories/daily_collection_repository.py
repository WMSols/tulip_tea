"""
Daily Collection Repository
============================
Data access layer for Daily Collection operations.
"""
from sqlalchemy.orm import Session
from models.daily_collection import DailyCollection
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class DailyCollectionRepository:
    """Repository for Daily Collection database operations."""
    
    @staticmethod
    def create(db: Session, shop_id: int, collected_by_order_booker: int = None,
              amount: Decimal = None, collection_date: datetime = None,
              visit_id: int = None, order_id: int = None,
              collected_by_delivery_man: int = None, photo_proof: str = None) -> DailyCollection:
        """
        Create a new daily collection entry.
        
        Args:
            db: Database session
            shop_id: Shop ID where collection was made
            collected_by_order_booker: Order booker ID who collected (optional)
            amount: Collection amount
            collection_date: Timestamp when collection was made (optional)
            visit_id: Visit ID where collection was made (optional)
            order_id: Order ID this collection is for (optional)
            collected_by_delivery_man: Delivery man ID who collected (optional)
            photo_proof: Photo proof URL or base64 (optional)
        
        Returns:
            Created daily collection instance
        """
        collection = DailyCollection(
            shop_id=shop_id,
            collected_by_order_booker=collected_by_order_booker,
            collected_by_delivery_man=collected_by_delivery_man,
            amount=amount,
            status="pending",
            collection_date=collection_date or datetime.utcnow(),
            visit_id=visit_id,
            order_id=order_id,
            photo_proof=photo_proof
        )
        db.add(collection)
        # Do NOT commit - let service layer handle transaction
        return collection
    
    @staticmethod
    def get_by_id(db: Session, collection_id: int) -> Optional[DailyCollection]:
        """Get daily collection by ID."""
        return db.query(DailyCollection).filter(DailyCollection.id == collection_id).first()
    
    @staticmethod
    def get_pending(db: Session, distributor_id: int = None) -> List[DailyCollection]:
        """
        Get all pending daily collections.
        
        Note: Since distributors are not assigned to zones, this method returns
        all pending collections. If zone filtering is needed, it should be done
        at the service layer based on order booker or delivery man zones.
        
        Args:
            db: Database session
            distributor_id: Optional distributor ID (currently not used for filtering)
        
        Returns:
            List of pending collections
        """
        # Return all pending collections
        # Note: Distributors are not assigned to zones, so we return all pending collections
        # If zone filtering is needed, filter by order_booker.zone_id or delivery_man.zone_id
        # at the service layer instead
        # Order by collection_date if available, otherwise by id
        return db.query(DailyCollection).filter(
            DailyCollection.status == "pending"
        ).order_by(DailyCollection.id.desc()).all()
    
    @staticmethod
    def get_by_order_booker(db: Session, order_booker_id: int) -> List[DailyCollection]:
        """Get all collections by an order booker."""
        return db.query(DailyCollection).filter(
            DailyCollection.collected_by_order_booker == order_booker_id
        ).order_by(DailyCollection.id.desc()).all()
    
    @staticmethod
    def get_by_shop(db: Session, shop_id: int) -> List[DailyCollection]:
        """Get all collections for a shop."""
        return db.query(DailyCollection).filter(
            DailyCollection.shop_id == shop_id
        ).order_by(DailyCollection.id.desc()).all()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 1000, status: str = None) -> List[DailyCollection]:
        """
        Get all daily collections with optional status filter.
        
        Args:
            db: Database session
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            status: Optional status filter ("pending", "verified", "rejected")
        
        Returns:
            List of collections
        """
        query = db.query(DailyCollection)
        if status:
            query = query.filter(DailyCollection.status == status)
        return query.order_by(DailyCollection.id.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_delivery_man(db: Session, delivery_man_id: int) -> List[DailyCollection]:
        """Get all collections by a delivery man."""
        return db.query(DailyCollection).filter(
            DailyCollection.collected_by_delivery_man == delivery_man_id
        ).order_by(DailyCollection.id.desc()).all()
    
    @staticmethod
    def approve(db: Session, collection_id: int, distributor_id: int) -> Optional[DailyCollection]:
        """
        Approve/verify a daily collection.
        
        Args:
            db: Database session
            collection_id: Collection ID to approve
            distributor_id: Distributor ID who is verifying
        
        Returns:
            Updated collection instance or None if not found
        """
        collection = db.query(DailyCollection).filter(DailyCollection.id == collection_id).first()
        if not collection:
            return None
        
        collection.status = "verified"  # Use "verified" to match database convention
        collection.verified_by_distributor = distributor_id
        
        db.commit()
        db.refresh(collection)
        return collection
    
    @staticmethod
    def reject(db: Session, collection_id: int, distributor_id: int) -> Optional[DailyCollection]:
        """
        Reject a daily collection.
        
        Args:
            db: Database session
            collection_id: Collection ID to reject
            distributor_id: Distributor ID who is rejecting
        
        Returns:
            Updated collection instance or None if not found
        """
        collection = db.query(DailyCollection).filter(DailyCollection.id == collection_id).first()
        if not collection:
            return None
        
        collection.status = "rejected"
        collection.verified_by_distributor = distributor_id
        
        db.commit()
        db.refresh(collection)
        return collection
    
    # Note: update_payment_id method removed - payment_id column doesn't exist in database
    # Payments are linked to collections via the daily_collection service logic, not via a foreign key

