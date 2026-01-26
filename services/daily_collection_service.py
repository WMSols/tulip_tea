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
                         remarks: str = None, visit_id: int = None) -> Dict:
        """
        Create a daily collection entry.
        
        FLOW:
        1. Validates shop exists
        2. Validates order booker exists
        3. Creates collection with status="pending"
        4. **INSTANTLY reduces shop's outstanding_balance** (for immediate credit limit increase)
        5. Returns collection data
        
        Note: Outstanding balance is reduced immediately so shop can order right away.
        Payment record is created later when distributor approves.
        
        Args:
            db: Database session
            shop_id: Shop ID where collection was made
            order_booker_id: Order booker ID who collected
            amount: Collection amount
            collected_at: Timestamp when collection was made (will be stored as collection_date)
            remarks: Optional remarks (not stored in database, kept for API compatibility)
            visit_id: Optional visit ID this collection is linked to
        
        Returns:
            Dict: Collection data with updated outstanding balance
        """
        # Validate shop exists
        shop = ShopRepository.get_by_id(db, shop_id)
        if not shop:
            raise ValueError("Shop not found")
        
        # Validate order booker exists
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        # Create collection (database uses collection_date, not collected_at)
        collection = DailyCollectionRepository.create(
            db=db,
            shop_id=shop_id,
            collected_by_order_booker=order_booker_id,
            amount=Decimal(str(amount)),
            collection_date=collected_at,  # Use collection_date to match database
            visit_id=visit_id
        )
        
        # **INSTANTLY REDUCE OUTSTANDING BALANCE** (for immediate credit limit increase)
        # This allows shop to order immediately without waiting for distributor approval
        current_outstanding = Decimal(str(shop.outstanding_balance or 0))
        credit_limit = Decimal(str(shop.credit_limit or 0))
        payment_amount = Decimal(str(amount))
        
        # Calculate new outstanding balance (cannot go below 0)
        # If shop pays more than outstanding, outstanding becomes 0 (they've overpaid)
        new_outstanding = max(Decimal('0'), current_outstanding - payment_amount)
        
        # Calculate new available credit
        # Available credit = credit_limit - outstanding_balance
        # This will be between 0 and credit_limit automatically since outstanding >= 0
        new_available_credit = credit_limit - new_outstanding if credit_limit > 0 else Decimal('0')
        
        # Validation: Ensure the calculation is correct
        # new_available_credit should be between 0 and credit_limit
        # This is automatically satisfied, but we validate for safety
        if credit_limit > 0:
            if new_available_credit < 0:
                raise ValueError(
                    f"Calculation error: Available credit cannot be negative. "
                    f"This should not happen. Please contact support."
                )
            if new_available_credit > credit_limit:
                raise ValueError(
                    f"Calculation error: Available credit (Rs. {new_available_credit}) "
                    f"exceeds credit limit (Rs. {credit_limit}). "
                    f"This should not happen. Please contact support."
                )
        
        # Note: If payment_amount > current_outstanding, outstanding becomes 0 and available credit = credit_limit
        # This is correct behavior - shop can pay more than owed, and will have full credit limit available
        
        # Update shop's outstanding balance (this commits and refreshes automatically)
        updated_shop = ShopRepository.update(
            db=db,
            shop_id=shop_id,
            outstanding_balance=new_outstanding
        )
        
        if not updated_shop:
            raise ValueError("Shop not found after update")
        
        # Use the updated shop (already refreshed by update method)
        shop = updated_shop
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        
        return {
            "id": collection.id,
            "shop_id": collection.shop_id,
            "shop_name": shop.name if shop else None,
            "shop_owner": shop.owner_name if shop else None,
            "order_id": collection.order_id,
            "collected_by_order_booker": collection.collected_by_order_booker,
            "order_booker_name": order_booker.name if order_booker else None,
            "collected_by_delivery_man": collection.collected_by_delivery_man,
            "verified_by_distributor": collection.verified_by_distributor,
            "amount": float(collection.amount) if collection.amount else 0.0,
            "status": collection.status.value if hasattr(collection.status, 'value') else str(collection.status),
            "visit_id": collection.visit_id,
            "collection_date": collection.collection_date.isoformat() if collection.collection_date else None,
            "photo_proof": collection.photo_proof,
            # Include updated credit information in response
            "shop_outstanding_balance": float(shop.outstanding_balance) if shop.outstanding_balance else 0.0,
            "shop_credit_limit": float(shop.credit_limit) if shop.credit_limit else 0.0,
            "shop_available_credit": float(shop.credit_limit - shop.outstanding_balance) if shop.credit_limit and shop.outstanding_balance is not None else (float(shop.credit_limit) if shop.credit_limit else 0.0)
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
                "order_id": collection.order_id,
                "collected_by_order_booker": collection.collected_by_order_booker,
                "order_booker_name": order_booker.name if order_booker else None,
                "collected_by_delivery_man": collection.collected_by_delivery_man,
                "verified_by_distributor": collection.verified_by_distributor,
                "amount": float(collection.amount) if collection.amount else 0.0,
                "status": collection.status.value if hasattr(collection.status, 'value') else str(collection.status),
                "visit_id": collection.visit_id,
                "collection_date": collection.collection_date.isoformat() if collection.collection_date else None,
                "photo_proof": collection.photo_proof
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
                "shop_owner": shop.owner_name if shop else None,
                "order_id": collection.order_id,
                "collected_by_order_booker": collection.collected_by_order_booker,
                "order_booker_name": None,  # Could fetch if needed
                "collected_by_delivery_man": collection.collected_by_delivery_man,
                "verified_by_distributor": collection.verified_by_distributor,
                "amount": float(collection.amount) if collection.amount else 0.0,
                "status": collection.status.value if hasattr(collection.status, 'value') else str(collection.status),
                "visit_id": collection.visit_id,
                "collection_date": collection.collection_date.isoformat() if collection.collection_date else None,
                "photo_proof": collection.photo_proof
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
        3. Verifies collection (sets status="verified", verified_by_distributor)
        4. Creates payment record from collection (for accounting/audit)
        5. **Note: Outstanding balance was already reduced when collection was created**
        6. Returns verified collection and payment data
        
        Args:
            db: Database session
            collection_id: Collection ID to approve
            distributor_id: Distributor ID who is verifying
        
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
        
        # Approve/verify collection
        approved = DailyCollectionRepository.approve(
            db=db,
            collection_id=collection_id,
            distributor_id=distributor_id
        )
        
        # Create payment record (for accounting/audit trail)
        # Note: Outstanding balance was already reduced when collection was created
        payment = PaymentRepository.create(
            db=db,
            shop_id=approved.shop_id,
            amount=approved.amount,
            order_id=approved.order_id,  # Link to order if collection was for an order
            received_by_distributor=distributor_id,
            payment_date=approved.collection_date or datetime.utcnow()
        )
        
        # **DO NOT REDUCE OUTSTANDING BALANCE AGAIN** - it was already reduced when collection was created
        # This allows shop to order immediately after payment, while payment record is created later for audit
        
        # Get shop name for response
        shop = ShopRepository.get_by_id(db, approved.shop_id)
        order_booker = OrderBookerRepository.get_by_id(db, approved.collected_by_order_booker)
        
        return {
            "collection": {
                "id": approved.id,
                "shop_id": approved.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "shop_owner": shop.owner_name if shop else None,
                "order_id": approved.order_id,
                "collected_by_order_booker": approved.collected_by_order_booker,
                "order_booker_name": order_booker.name if order_booker else None,
                "collected_by_delivery_man": approved.collected_by_delivery_man,
                "verified_by_distributor": approved.verified_by_distributor,
                "amount": float(approved.amount) if approved.amount else 0.0,
                "status": approved.status.value if hasattr(approved.status, 'value') else str(approved.status),
                "visit_id": approved.visit_id,
                "collection_date": approved.collection_date.isoformat() if approved.collection_date else None,
                "photo_proof": approved.photo_proof
            },
            "payment": {
                "id": payment.id,
                "shop_id": payment.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "order_id": payment.order_id,
                "amount": float(payment.amount) if payment.amount else 0.0,
                "received_by_distributor": payment.received_by_distributor,
                "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
                # Note: collected_by_order_booker info comes from the daily_collection record
                "collected_by_order_booker": approved.collected_by_order_booker,
                "order_booker_name": order_booker.name if order_booker else None
            },
            "message": "Collection approved. Outstanding balance was already reduced when collection was created."
        }
    
    @staticmethod
    def reject_collection(db: Session, collection_id: int, distributor_id: int) -> Dict:
        """
        Reject a daily collection.
        
        FLOW:
        1. Validates collection exists and is pending
        2. Validates distributor exists
        3. **REVERSES outstanding balance reduction** (adds amount back)
        4. Rejects collection (sets status="rejected", verified_by_distributor)
        5. Returns rejected collection data
        
        Args:
            db: Database session
            collection_id: Collection ID to reject
            distributor_id: Distributor ID who is rejecting
        
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
        
        # **REVERSE OUTSTANDING BALANCE REDUCTION** (add amount back)
        # Since outstanding balance was reduced when collection was created, we need to reverse it
        shop = ShopRepository.get_by_id(db, collection.shop_id)
        if shop:
            current_outstanding = Decimal(str(shop.outstanding_balance or 0))
            collection_amount = Decimal(str(collection.amount or 0))
            new_outstanding = current_outstanding + collection_amount  # Add back the amount
            
            ShopRepository.update(
                db=db,
                shop_id=collection.shop_id,
                outstanding_balance=new_outstanding
            )
        
        # Reject collection
        rejected = DailyCollectionRepository.reject(
            db=db,
            collection_id=collection_id,
            distributor_id=distributor_id
        )
        
        # Get shop and order booker names for response
        shop = ShopRepository.get_by_id(db, rejected.shop_id)
        order_booker = OrderBookerRepository.get_by_id(db, rejected.collected_by_order_booker)
        
        return {
            "id": rejected.id,
            "shop_id": rejected.shop_id,
            "shop_name": shop.name if shop else "Unknown",
            "shop_owner": shop.owner_name if shop else None,
            "order_id": rejected.order_id,
            "collected_by_order_booker": rejected.collected_by_order_booker,
            "order_booker_name": order_booker.name if order_booker else None,
            "collected_by_delivery_man": rejected.collected_by_delivery_man,
            "verified_by_distributor": rejected.verified_by_distributor,
            "amount": float(rejected.amount) if rejected.amount else 0.0,
            "status": rejected.status.value if hasattr(rejected.status, 'value') else str(rejected.status),
            "visit_id": rejected.visit_id,
            "collection_date": rejected.collection_date.isoformat() if rejected.collection_date else None,
            "photo_proof": rejected.photo_proof,
            "message": "Collection rejected. Outstanding balance has been reversed."
        }

