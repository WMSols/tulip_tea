"""
Daily Collection Business Logic Service
========================================
Handles business logic for daily collections.
"""
from sqlalchemy.orm import Session
from repositories.daily_collection_repository import DailyCollectionRepository
from repositories.payment_repository import PaymentRepository
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.distributor_repository import DistributorRepository
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime


class DailyCollectionService:
    """Service for Daily Collection business logic."""
    
    @staticmethod
    def create_collection(db: Session, shop_id: int, order_booker_id: int,
                         amount: float, collected_at: datetime = None,
                         remarks: str = None) -> Dict:
        """
        Create a daily collection entry.
        
        FLOW:
        1. Validates shop exists
        2. Validates order booker exists
        3. Creates collection with status="pending"
        4. Returns collection data
        
        Args:
            db: Database session
            shop_id: Shop ID where collection was made
            order_booker_id: Order booker ID who collected
            amount: Collection amount
            collected_at: Timestamp when collection was made
            remarks: Optional remarks
        
        Returns:
            Dict: Collection data
        """
        # Validate shop exists
        shop = ShopRepository.get_by_id(db, shop_id)
        if not shop:
            raise ValueError("Shop not found")
        
        # Validate order booker exists
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        # Create collection
        collection = DailyCollectionRepository.create(
            db=db,
            shop_id=shop_id,
            collected_by_order_booker=order_booker_id,
            amount=Decimal(str(amount)),
            collected_at=collected_at,
            remarks=remarks
        )
        
        return {
            "id": collection.id,
            "shop_id": collection.shop_id,
            "collected_by_order_booker": collection.collected_by_order_booker,
            "amount": float(collection.amount),
            "status": collection.status,
            "collected_at": collection.collected_at.isoformat() if collection.collected_at else None,
            "remarks": collection.remarks,
            "created_at": collection.created_at.isoformat() if collection.created_at else None
        }
    
    @staticmethod
    def get_pending_collections(db: Session, distributor_id: int = None) -> List[Dict]:
        """
        Get all pending daily collections.
        
        FLOW:
        1. Gets all pending collections from repository
        2. Includes shop and order booker information
        3. Returns formatted list
        
        Args:
            db: Database session
            distributor_id: Optional distributor ID (currently not used for filtering)
        
        Returns:
            List[Dict]: List of pending collections with shop and order booker info
        
        Note: Distributors are not assigned to zones, so distributor_id is not used for filtering.
        All pending collections are returned regardless of distributor.
        """
        collections = DailyCollectionRepository.get_pending(db, distributor_id)
        
        result = []
        for collection in collections:
            shop = ShopRepository.get_by_id(db, collection.shop_id)
            order_booker = OrderBookerRepository.get_by_id(db, collection.collected_by_order_booker)
            
            result.append({
                "id": collection.id,
                "shop_id": collection.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "shop_owner": shop.owner_name if shop else None,
                "collected_by_order_booker": collection.collected_by_order_booker,
                "order_booker_name": order_booker.name if order_booker else None,
                "amount": float(collection.amount),
                "status": collection.status,
                "collected_at": collection.collected_at.isoformat() if collection.collected_at else None,
                "remarks": collection.remarks,
                "created_at": collection.created_at.isoformat() if collection.created_at else None
            })
        
        return result
    
    @staticmethod
    def get_collections_by_order_booker(db: Session, order_booker_id: int) -> List[Dict]:
        """
        Get all collections by an order booker.
        
        Args:
            db: Database session
            order_booker_id: Order booker ID
        
        Returns:
            List[Dict]: List of collections with shop info
        """
        collections = DailyCollectionRepository.get_by_order_booker(db, order_booker_id)
        
        result = []
        for collection in collections:
            shop = ShopRepository.get_by_id(db, collection.shop_id)
            
            result.append({
                "id": collection.id,
                "shop_id": collection.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "amount": float(collection.amount),
                "status": collection.status,
                "collected_at": collection.collected_at.isoformat() if collection.collected_at else None,
                "remarks": collection.remarks,
                "created_at": collection.created_at.isoformat() if collection.created_at else None
            })
        
        return result
    
    @staticmethod
    def approve_collection(db: Session, collection_id: int, distributor_id: int,
                         remarks: str = None) -> Dict:
        """
        Approve a daily collection and create payment record.
        
        FLOW:
        1. Validates collection exists and is pending
        2. Validates distributor exists
        3. Approves collection (sets status, reviewed_by, reviewed_at)
        4. Creates payment record from collection
        5. Links collection to payment
        6. Returns approved collection and payment data
        
        Args:
            db: Database session
            collection_id: Collection ID to approve
            distributor_id: Distributor ID who is approving
            remarks: Optional remarks
        
        Returns:
            Dict: Approved collection and payment data
        """
        # Validate collection
        collection = DailyCollectionRepository.get_by_id(db, collection_id)
        if not collection:
            raise ValueError("Daily collection not found")
        
        if collection.status != "pending":
            raise ValueError("Collection is not pending")
        
        # Validate distributor
        distributor = DistributorRepository.get_by_id(db, distributor_id)
        if not distributor:
            raise ValueError("Distributor not found")
        
        # Approve collection
        approved = DailyCollectionRepository.approve(
            db=db,
            collection_id=collection_id,
            distributor_id=distributor_id,
            remarks=remarks
        )
        
        # Create payment record
        payment = PaymentRepository.create(
            db=db,
            shop_id=approved.shop_id,
            collected_by_order_booker=approved.collected_by_order_booker,
            approved_by_distributor=distributor_id,
            amount=approved.amount,
            daily_collection_id=approved.id,
            collected_at=approved.collected_at,
            remarks=remarks or approved.remarks
        )
        
        # Link collection to payment
        DailyCollectionRepository.update_payment_id(db, approved.id, payment.id)
        
        # Get shop name for response
        shop = ShopRepository.get_by_id(db, approved.shop_id)
        order_booker = OrderBookerRepository.get_by_id(db, approved.collected_by_order_booker)
        
        return {
            "collection": {
                "id": approved.id,
                "shop_id": approved.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "collected_by_order_booker": approved.collected_by_order_booker,
                "order_booker_name": order_booker.name if order_booker else None,
                "amount": float(approved.amount),
                "status": approved.status,
                "reviewed_by_distributor": approved.reviewed_by_distributor,
                "reviewed_at": approved.reviewed_at.isoformat() if approved.reviewed_at else None,
                "payment_id": approved.payment_id,
                "remarks": approved.remarks,
                "created_at": approved.created_at.isoformat() if approved.created_at else None
            },
            "payment": {
                "id": payment.id,
                "shop_id": payment.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "amount": float(payment.amount),
                "daily_collection_id": payment.daily_collection_id,
                "collected_by_order_booker": payment.collected_by_order_booker,
                "order_booker_name": order_booker.name if order_booker else None,
                "approved_by_distributor": payment.approved_by_distributor,
                "collected_at": payment.collected_at.isoformat() if payment.collected_at else None,
                "created_at": payment.created_at.isoformat() if payment.created_at else None
            }
        }
    
    @staticmethod
    def reject_collection(db: Session, collection_id: int, distributor_id: int,
                         remarks: str = None) -> Dict:
        """
        Reject a daily collection.
        
        FLOW:
        1. Validates collection exists and is pending
        2. Validates distributor exists
        3. Rejects collection (sets status, reviewed_by, reviewed_at)
        4. Returns rejected collection data
        
        Args:
            db: Database session
            collection_id: Collection ID to reject
            distributor_id: Distributor ID who is rejecting
            remarks: Reason for rejection
        
        Returns:
            Dict: Rejected collection data
        """
        # Validate collection
        collection = DailyCollectionRepository.get_by_id(db, collection_id)
        if not collection:
            raise ValueError("Daily collection not found")
        
        if collection.status != "pending":
            raise ValueError("Collection is not pending")
        
        # Validate distributor
        distributor = DistributorRepository.get_by_id(db, distributor_id)
        if not distributor:
            raise ValueError("Distributor not found")
        
        # Reject collection
        rejected = DailyCollectionRepository.reject(
            db=db,
            collection_id=collection_id,
            distributor_id=distributor_id,
            remarks=remarks
        )
        
        # Get shop and order booker names for response
        shop = ShopRepository.get_by_id(db, rejected.shop_id)
        order_booker = OrderBookerRepository.get_by_id(db, rejected.collected_by_order_booker)
        
        return {
            "id": rejected.id,
            "shop_id": rejected.shop_id,
            "shop_name": shop.name if shop else "Unknown",
            "collected_by_order_booker": rejected.collected_by_order_booker,
            "order_booker_name": order_booker.name if order_booker else None,
            "amount": float(rejected.amount),
            "status": rejected.status,
            "reviewed_by_distributor": rejected.reviewed_by_distributor,
            "reviewed_at": rejected.reviewed_at.isoformat() if rejected.reviewed_at else None,
            "remarks": rejected.remarks,
            "created_at": rejected.created_at.isoformat() if rejected.created_at else None
        }

