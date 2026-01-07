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
    def create(db: Session, shop_id: int, collected_by_order_booker: int,
              amount: Decimal, collected_at: datetime = None,
              remarks: str = None) -> DailyCollection:
        """
        Create a new daily collection entry.
        
        Args:
            db: Database session
            shop_id: Shop ID where collection was made
            collected_by_order_booker: Order booker ID who collected
            amount: Collection amount
            collected_at: Timestamp when collection was made (optional)
            remarks: Optional remarks
        
        Returns:
            Created daily collection instance
        """
        collection = DailyCollection(
            shop_id=shop_id,
            collected_by_order_booker=collected_by_order_booker,
            amount=amount,
            status="pending",
            collected_at=collected_at or datetime.utcnow(),
            remarks=remarks
        )
        db.add(collection)
        db.commit()
        db.refresh(collection)
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
        return db.query(DailyCollection).filter(
            DailyCollection.status == "pending"
        ).order_by(DailyCollection.created_at.desc()).all()
    
    @staticmethod
    def get_by_order_booker(db: Session, order_booker_id: int) -> List[DailyCollection]:
        """Get all collections by an order booker."""
        return db.query(DailyCollection).filter(
            DailyCollection.collected_by_order_booker == order_booker_id
        ).order_by(DailyCollection.created_at.desc()).all()
    
    @staticmethod
    def get_by_shop(db: Session, shop_id: int) -> List[DailyCollection]:
        """Get all collections for a shop."""
        return db.query(DailyCollection).filter(
            DailyCollection.shop_id == shop_id
        ).order_by(DailyCollection.created_at.desc()).all()
    
    @staticmethod
    def approve(db: Session, collection_id: int, distributor_id: int,
               remarks: str = None) -> Optional[DailyCollection]:
        """
        Approve a daily collection.
        
        Args:
            db: Database session
            collection_id: Collection ID to approve
            distributor_id: Distributor ID who is approving
            remarks: Optional remarks
        
        Returns:
            Updated collection instance or None if not found
        """
        collection = db.query(DailyCollection).filter(DailyCollection.id == collection_id).first()
        if not collection:
            return None
        
        collection.status = "approved"
        collection.reviewed_by_distributor = distributor_id
        collection.reviewed_at = datetime.utcnow()
        if remarks:
            collection.remarks = remarks
        
        db.commit()
        db.refresh(collection)
        return collection
    
    @staticmethod
    def reject(db: Session, collection_id: int, distributor_id: int,
              remarks: str = None) -> Optional[DailyCollection]:
        """
        Reject a daily collection.
        
        Args:
            db: Database session
            collection_id: Collection ID to reject
            distributor_id: Distributor ID who is rejecting
            remarks: Reason for rejection
        
        Returns:
            Updated collection instance or None if not found
        """
        collection = db.query(DailyCollection).filter(DailyCollection.id == collection_id).first()
        if not collection:
            return None
        
        collection.status = "rejected"
        collection.reviewed_by_distributor = distributor_id
        collection.reviewed_at = datetime.utcnow()
        if remarks:
            collection.remarks = remarks
        
        db.commit()
        db.refresh(collection)
        return collection
    
    @staticmethod
    def update_payment_id(db: Session, collection_id: int, payment_id: int) -> bool:
        """
        Update collection with payment ID after payment is created.
        
        Args:
            db: Database session
            collection_id: Collection ID
            payment_id: Payment ID to link
        
        Returns:
            True if updated, False if not found
        """
        collection = db.query(DailyCollection).filter(DailyCollection.id == collection_id).first()
        if not collection:
            return False
        
        collection.payment_id = payment_id
        db.commit()
        return True

