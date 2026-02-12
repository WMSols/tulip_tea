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
from repositories.delivery_man_repository import DeliveryManRepository
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
        
        try:
            # Create collection (does not commit)
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
            
            # Update shop's outstanding balance (does not commit)
            updated_shop = ShopRepository.update(
                db=db,
                shop_id=shop_id,
                outstanding_balance=new_outstanding
            )
            
            if not updated_shop:
                raise ValueError("Shop not found after update")
            
            # Use the updated shop
            shop = updated_shop
            order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
            
            # **CREDIT WALLET IMMEDIATELY** when collection is created
            # The collector (order booker or delivery man) has collected the money, so they should see it in their wallet right away
            from services.wallet_service import WalletService
            from repositories.route_repository import RouteRepository
            from repositories.zone_repository import ZoneRepository
            
            # Get shop's route and zone information for complete trail
            route_id = shop.route_id if shop else None
            route_name = None
            zone_id = shop.zone_id if shop else None
            zone_name = None
            
            if route_id:
                route = RouteRepository.get_by_id(db, route_id)
                route_name = route.name if route else None
            
            if zone_id:
                zone = ZoneRepository.get_by_id(db, zone_id)
                zone_name = zone.name if zone else None
            
            # Determine who collected and credit their wallet (does not commit)
            if collection.collected_by_order_booker:
                WalletService.credit_wallet(
                    db=db,
                    user_type="order_booker",
                    user_id=collection.collected_by_order_booker,
                    amount=payment_amount,
                    description=f"Collection from shop {shop.name if shop else shop_id}",
                    reference_type="daily_collection",
                    reference_id=collection.id,
                    initiated_by_type="order_booker",
                    initiated_by_id=collection.collected_by_order_booker,
                    transaction_metadata={
                        "shop_id": shop_id,
                        "shop_name": shop.name if shop else None,
                        "shop_owner": shop.owner_name if shop else None,
                        "route_id": route_id,
                        "route_name": route_name,
                        "zone_id": zone_id,
                        "zone_name": zone_name,
                        "collection_id": collection.id,
                        "collection_date": collection.collection_date.isoformat() if collection.collection_date else None,
                        "status": "pending"  # Collection is pending distributor approval
                    }
                )
            elif collection.collected_by_delivery_man:
                WalletService.credit_wallet(
                    db=db,
                    user_type="delivery_man",
                    user_id=collection.collected_by_delivery_man,
                    amount=payment_amount,
                    description=f"Collection from shop {shop.name if shop else shop_id}",
                    reference_type="daily_collection",
                    reference_id=collection.id,
                    initiated_by_type="delivery_man",
                    initiated_by_id=collection.collected_by_delivery_man,
                    transaction_metadata={
                        "shop_id": shop_id,
                        "shop_name": shop.name if shop else None,
                        "shop_owner": shop.owner_name if shop else None,
                        "route_id": route_id,
                        "route_name": route_name,
                        "zone_id": zone_id,
                        "zone_name": zone_name,
                        "collection_id": collection.id,
                        "collection_date": collection.collection_date.isoformat() if collection.collection_date else None,
                        "status": "pending"  # Collection is pending distributor approval
                    }
                )
            
            # Commit all operations together (collection, shop update, wallet credit)
            db.commit()
            db.refresh(collection)
            db.refresh(shop)
            
        except Exception as e:
            # Rollback all operations on any error
            db.rollback()
            raise
        
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
            "shop_available_credit": max(0.0, float(shop.credit_limit - shop.outstanding_balance)) if shop.credit_limit and shop.outstanding_balance is not None else (float(shop.credit_limit) if shop.credit_limit else 0.0)
        }
    
    @staticmethod
    def get_pending_collections(db: Session, distributor_id: int = None) -> List[Dict]:
        """
        Get all pending daily collections with complete trail information.
        
        FLOW:
        1. Gets all pending collections from repository
        2. Includes shop, route, zone, and collector information
        3. Returns formatted list with complete trail
        
        Args:
            db: Database session
            distributor_id: Optional distributor ID (currently not used for filtering)
        
        Returns:
            List[Dict]: List of pending collections with complete trail info
        
        Note: Distributors are not assigned to zones, so distributor_id is not used for filtering.
        All pending collections are returned regardless of distributor.
        """
        from repositories.route_repository import RouteRepository
        from repositories.zone_repository import ZoneRepository
        from repositories.delivery_man_repository import DeliveryManRepository
        
        collections = DailyCollectionRepository.get_pending(db, distributor_id)
        
        result = []
        for collection in collections:
            shop = ShopRepository.get_by_id(db, collection.shop_id)
            
            # Get route and zone information
            route_id = shop.route_id if shop else None
            route_name = None
            zone_id = shop.zone_id if shop else None
            zone_name = None
            
            if route_id:
                route = RouteRepository.get_by_id(db, route_id)
                route_name = route.name if route else None
            
            if zone_id:
                zone = ZoneRepository.get_by_id(db, zone_id)
                zone_name = zone.name if zone else None
            
            # Get collector information
            order_booker_name = None
            delivery_man_name = None
            
            if collection.collected_by_order_booker:
                order_booker = OrderBookerRepository.get_by_id(db, collection.collected_by_order_booker)
                order_booker_name = order_booker.name if order_booker else None
            
            if collection.collected_by_delivery_man:
                delivery_man = DeliveryManRepository.get_by_id(db, collection.collected_by_delivery_man)
                delivery_man_name = delivery_man.name if delivery_man else None
            
            result.append({
                "id": collection.id,
                "shop_id": collection.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "shop_owner": shop.owner_name if shop else None,
                "route_id": route_id,
                "route_name": route_name,
                "zone_id": zone_id,
                "zone_name": zone_name,
                "order_id": collection.order_id,
                "collected_by_order_booker": collection.collected_by_order_booker,
                "order_booker_name": order_booker_name,
                "collected_by_delivery_man": collection.collected_by_delivery_man,
                "delivery_man_name": delivery_man_name,
                "verified_by_distributor": collection.verified_by_distributor,
                "amount": float(collection.amount) if collection.amount else 0.0,
                "status": collection.status.value if hasattr(collection.status, 'value') else str(collection.status),
                "visit_id": collection.visit_id,
                "collection_date": collection.collection_date.isoformat() if collection.collection_date else None,
                "photo_proof": collection.photo_proof
            })
        
        return result
    
    @staticmethod
    def get_all_collections(db: Session, distributor_id: int = None, status: str = None, skip: int = 0, limit: int = 1000) -> List[Dict]:
        """
        Get all daily collections with complete trail information for distributor.
        
        FLOW:
        1. Gets all collections (or filtered by status) from repository
        2. Includes shop, route, zone, and collector information
        3. Returns formatted list with complete trail
        
        Args:
            db: Database session
            distributor_id: Optional distributor ID (currently not used for filtering)
            status: Optional status filter ("pending", "verified", "rejected")
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[Dict]: List of collections with complete trail info
        """
        from repositories.route_repository import RouteRepository
        from repositories.zone_repository import ZoneRepository
        from repositories.delivery_man_repository import DeliveryManRepository
        from repositories.daily_collection_repository import DailyCollectionRepository
        
        collections = DailyCollectionRepository.get_all(db, skip=skip, limit=limit, status=status)
        
        result = []
        for collection in collections:
            shop = ShopRepository.get_by_id(db, collection.shop_id)
            
            # Get route and zone information
            route_id = shop.route_id if shop else None
            route_name = None
            zone_id = shop.zone_id if shop else None
            zone_name = None
            
            if route_id:
                route = RouteRepository.get_by_id(db, route_id)
                route_name = route.name if route else None
            
            if zone_id:
                zone = ZoneRepository.get_by_id(db, zone_id)
                zone_name = zone.name if zone else None
            
            # Get collector information
            order_booker_name = None
            delivery_man_name = None
            
            if collection.collected_by_order_booker:
                order_booker = OrderBookerRepository.get_by_id(db, collection.collected_by_order_booker)
                order_booker_name = order_booker.name if order_booker else None
            
            if collection.collected_by_delivery_man:
                delivery_man = DeliveryManRepository.get_by_id(db, collection.collected_by_delivery_man)
                delivery_man_name = delivery_man.name if delivery_man else None
            
            result.append({
                "id": collection.id,
                "shop_id": collection.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "shop_owner": shop.owner_name if shop else None,
                "route_id": route_id,
                "route_name": route_name,
                "zone_id": zone_id,
                "zone_name": zone_name,
                "order_id": collection.order_id,
                "collected_by_order_booker": collection.collected_by_order_booker,
                "order_booker_name": order_booker_name,
                "collected_by_delivery_man": collection.collected_by_delivery_man,
                "delivery_man_name": delivery_man_name,
                "verified_by_distributor": collection.verified_by_distributor,
                "amount": float(collection.amount) if collection.amount else 0.0,
                "status": collection.status.value if hasattr(collection.status, 'value') else str(collection.status),
                "visit_id": collection.visit_id,
                "collection_date": collection.collection_date.isoformat() if collection.collection_date else None,
                "photo_proof": collection.photo_proof,
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
    def create_collection_for_delivery_man(db: Session, shop_id: int, delivery_man_id: int,
                                          amount: float, collected_at: datetime = None,
                                          remarks: str = None, order_id: int = None) -> Dict:
        """
        Create a daily collection entry by delivery man.
        
        FLOW:
        1. Validates shop exists
        2. Validates delivery man exists
        3. Creates collection with status="pending"
        4. **INSTANTLY reduces shop's outstanding_balance** (for immediate credit limit increase)
        5. Returns collection data
        
        Note: Outstanding balance is reduced immediately so shop can order right away.
        Payment record is created later when distributor approves.
        
        Args:
            db: Database session
            shop_id: Shop ID where collection was made
            delivery_man_id: Delivery man ID who collected
            amount: Collection amount
            collected_at: Timestamp when collection was made (will be stored as collection_date)
            remarks: Optional remarks (not stored in database, kept for API compatibility)
            order_id: Optional order ID this collection is linked to
        
        Returns:
            Dict: Collection data with updated outstanding balance
        """
        # Validate shop exists
        shop = ShopRepository.get_by_id(db, shop_id)
        if not shop:
            raise ValueError("Shop not found")
        
        # Validate delivery man exists
        delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id)
        if not delivery_man:
            raise ValueError("Delivery Man not found")
        
        try:
            # Create collection (database uses collection_date, not collected_at)
            collection = DailyCollectionRepository.create(
                db=db,
                shop_id=shop_id,
                collected_by_delivery_man=delivery_man_id,
                amount=Decimal(str(amount)),
                collection_date=collected_at,  # Use collection_date to match database
                order_id=order_id
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
            
            # Update shop's outstanding balance
            updated_shop = ShopRepository.update(
                db=db,
                shop_id=shop_id,
                outstanding_balance=new_outstanding
            )
            
            if not updated_shop:
                raise ValueError("Shop not found after update")
            
            # Use the updated shop
            shop = updated_shop
            delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id)
            
            # **CREDIT WALLET IMMEDIATELY** when collection is created
            # The collector (delivery man) has collected the money, so they should see it in their wallet right away
            from services.wallet_service import WalletService
            from repositories.route_repository import RouteRepository
            from repositories.zone_repository import ZoneRepository
            
            # Get shop's route and zone information for complete trail
            route_id = shop.route_id if shop else None
            route_name = None
            zone_id = shop.zone_id if shop else None
            zone_name = None
            
            if route_id:
                route = RouteRepository.get_by_id(db, route_id)
                route_name = route.name if route else None
            
            if zone_id:
                zone = ZoneRepository.get_by_id(db, zone_id)
                zone_name = zone.name if zone else None
            
            # Flush to get collection.id before committing (for wallet reference)
            db.flush()
            
            # Credit delivery man's wallet
            try:
                WalletService.credit_wallet(
                    db=db,
                    user_type="delivery_man",
                    user_id=delivery_man_id,
                    amount=payment_amount,
                    description=f"Collection from shop {shop.name if shop else shop_id}",
                    reference_type="daily_collection",
                    reference_id=collection.id,  # Now available after flush
                    initiated_by_type="delivery_man",
                    initiated_by_id=delivery_man_id,
                    transaction_metadata={
                        "shop_id": shop_id,
                        "shop_name": shop.name if shop else None,
                        "shop_owner": shop.owner_name if shop else None,
                        "route_id": route_id,
                        "route_name": route_name,
                        "zone_id": zone_id,
                        "zone_name": zone_name,
                        "collection_id": collection.id,  # Now available after flush
                        "collection_date": collection.collection_date.isoformat() if collection.collection_date else None,
                        "status": "pending"  # Collection is pending distributor approval
                    }
                )
            except Exception as e:
                # Log error but don't fail collection creation
                # Wallet credit failure shouldn't prevent collection from being created
                print(f"Warning: Failed to credit wallet for collection: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # Commit all changes together (collection, shop update, wallet credit)
            db.commit()
            
            # Refresh collection and shop to get latest data
            db.refresh(collection)
            db.refresh(shop)
            
            # Update wallet transaction with collection_id if wallet credit succeeded
            # (This is optional - the metadata already has shop info)
            
            return {
                "id": collection.id,
                "shop_id": collection.shop_id,
                "shop_name": shop.name if shop else None,
                "shop_owner": shop.owner_name if shop else None,
                "order_id": collection.order_id,
                "collected_by_order_booker": collection.collected_by_order_booker,
                "order_booker_name": None,
                "collected_by_delivery_man": collection.collected_by_delivery_man,
                "delivery_man_name": delivery_man.name if delivery_man else None,
                "verified_by_distributor": collection.verified_by_distributor,
                "amount": float(collection.amount) if collection.amount else 0.0,
                "status": collection.status.value if hasattr(collection.status, 'value') else str(collection.status),
                "visit_id": collection.visit_id,
                "collection_date": collection.collection_date.isoformat() if collection.collection_date else None,
                "photo_proof": collection.photo_proof,
                # Include updated credit information in response
                "shop_outstanding_balance": float(shop.outstanding_balance) if shop.outstanding_balance else 0.0,
                "shop_credit_limit": float(shop.credit_limit) if shop.credit_limit else 0.0,
                "shop_available_credit": max(0.0, float(shop.credit_limit - shop.outstanding_balance)) if shop.credit_limit and shop.outstanding_balance is not None else (float(shop.credit_limit) if shop.credit_limit else 0.0)
            }
        except Exception as e:
            # Rollback on any error
            db.rollback()
            raise
    
    @staticmethod
    def get_collections_by_delivery_man(db: Session, delivery_man_id: int) -> List[Dict]:
        """
        Get all collections by a delivery man.
        OPTIMIZED: Uses batch loading to avoid N+1 queries.
        
        Args:
            db: Database session
            delivery_man_id: Delivery man ID
        
        Returns:
            List[Dict]: List of collections with shop info
        """
        collections = DailyCollectionRepository.get_by_delivery_man(db, delivery_man_id)
        
        if not collections:
            return []
        
        # Batch load all related entities to avoid N+1 queries
        from models.shop import Shop
        from models.delivery_man import DeliveryMan
        from models.order_booker import OrderBooker
        
        # Collect all unique IDs
        shop_ids = list(set([c.shop_id for c in collections if c.shop_id]))
        delivery_man_ids = list(set([c.collected_by_delivery_man for c in collections if c.collected_by_delivery_man]))
        order_booker_ids = list(set([c.collected_by_order_booker for c in collections if c.collected_by_order_booker]))
        
        # Batch load shops (1 query for all shops)
        shops_map = {}
        if shop_ids:
            shops_query = db.query(Shop).filter(Shop.id.in_(shop_ids)).all()
            shops_map = {shop.id: shop for shop in shops_query}
        
        # Batch load delivery men (1 query for all delivery men)
        delivery_men_map = {}
        if delivery_man_ids:
            dm_query = db.query(DeliveryMan).filter(DeliveryMan.id.in_(delivery_man_ids)).all()
            delivery_men_map = {dm.id: dm for dm in dm_query}
        
        # Batch load order bookers (1 query for all order bookers)
        order_bookers_map = {}
        if order_booker_ids:
            ob_query = db.query(OrderBooker).filter(OrderBooker.id.in_(order_booker_ids)).all()
            order_bookers_map = {ob.id: ob for ob in ob_query}
        
        # Build result using lookup maps (no additional queries)
        result = []
        for collection in collections:
            shop = shops_map.get(collection.shop_id)
            delivery_man = delivery_men_map.get(collection.collected_by_delivery_man) if collection.collected_by_delivery_man else None
            order_booker = order_bookers_map.get(collection.collected_by_order_booker) if collection.collected_by_order_booker else None
            
            result.append({
                "id": collection.id,
                "shop_id": collection.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "shop_owner": shop.owner_name if shop else None,
                "order_id": collection.order_id,
                "collected_by_order_booker": collection.collected_by_order_booker,
                "order_booker_name": order_booker.name if order_booker else None,
                "collected_by_delivery_man": collection.collected_by_delivery_man,
                "delivery_man_name": delivery_man.name if delivery_man else None,
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
        # Note: Wallet was already credited when collection was created, so we don't credit again here
        payment = PaymentRepository.create(
            db=db,
            shop_id=approved.shop_id,
            amount=approved.amount,
            order_id=approved.order_id,  # Link to order if collection was for an order
            received_by_distributor=distributor_id,
            payment_date=approved.collection_date or datetime.utcnow()
        )
        
        # NOTE: Wallet is NOT credited here because it was already credited when the collection was created.
        # The wallet credit happens immediately when the order booker/delivery man creates the collection,
        # so they see the money in their wallet right away. Approval is just verification by the distributor.
        
        # **DO NOT REDUCE OUTSTANDING BALANCE AGAIN** - it was already reduced when collection was created
        # This allows shop to order immediately after payment, while payment record is created later for audit
        
        # Get shop name for response (refresh to get latest data)
        shop = ShopRepository.get_by_id(db, approved.shop_id)
        if shop:
            db.refresh(shop)
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

