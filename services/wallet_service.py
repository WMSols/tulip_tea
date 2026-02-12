"""
Wallet business logic service.
"""
from sqlalchemy.orm import Session
from repositories.wallet_repository import WalletRepository
from models.wallet import Wallet
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime
import json


class WalletService:
    """Service for Wallet business logic."""
    
    @staticmethod
    def get_or_create_wallet(db: Session, user_type: str, user_id: int) -> Dict:
        """
        Get existing wallet or create a new one for a user.
        
        Args:
            db: Database session
            user_type: Type of user ('distributor', 'order_booker', 'delivery_man')
            user_id: ID of the user
        
        Returns:
            Dict: Wallet data
        """
        wallet = WalletRepository.get_by_user(db, user_type, user_id)
        
        if not wallet:
            wallet = WalletRepository.create(db, user_type, user_id)
        
        return {
            "id": wallet.id,
            "user_type": wallet.user_type,
            "user_id": wallet.user_id,
            "current_balance": float(wallet.current_balance) if wallet.current_balance else 0.0,
            "is_active": wallet.is_active,
            "created_at": wallet.created_at.isoformat() if wallet.created_at else None,
            "updated_at": wallet.updated_at.isoformat() if wallet.updated_at else None
        }
    
    @staticmethod
    def get_wallet_balance(db: Session, user_type: str, user_id: int) -> Dict:
        """
        Get wallet balance for a user.
        
        Args:
            db: Database session
            user_type: Type of user ('distributor', 'order_booker', 'delivery_man')
            user_id: ID of the user
        
        Returns:
            Dict: Wallet balance information
        """
        wallet = WalletRepository.get_by_user(db, user_type, user_id)
        
        if not wallet:
            # Create wallet if it doesn't exist
            wallet = WalletRepository.create(db, user_type, user_id)
        
        return {
            "wallet_id": wallet.id,
            "user_type": wallet.user_type,
            "user_id": wallet.user_id,
            "current_balance": float(wallet.current_balance) if wallet.current_balance else 0.0,
            "is_active": wallet.is_active
        }
    
    @staticmethod
    def credit_wallet(
        db: Session,
        user_type: str,
        user_id: int,
        amount: Decimal,
        description: str = None,
        reference_type: str = None,
        reference_id: int = None,
        initiated_by_type: str = None,
        initiated_by_id: int = None,
        transaction_metadata: dict = None
    ) -> Dict:
        """
        Credit money to a wallet (add money).
        
        Args:
            db: Database session
            user_type: Type of user whose wallet to credit
            user_id: ID of the user
            amount: Amount to credit (must be positive)
            description: Description of the transaction
            reference_type: Type of related entity ('daily_collection', 'order', etc.)
            reference_id: ID of related entity
            initiated_by_type: Type of user who initiated this credit
            initiated_by_id: ID of user who initiated
            transaction_metadata: Additional JSON data
        
        Returns:
            Dict: Transaction details and updated balance
        """
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        
        # Get or create wallet
        wallet = WalletRepository.get_by_user(db, user_type, user_id)
        if not wallet:
            wallet = WalletRepository.create(db, user_type, user_id)
        
        # Calculate new balance
        balance_before = wallet.current_balance
        balance_after = balance_before + amount
        
        # Update wallet balance
        updated_wallet = WalletRepository.update_balance(db, wallet.id, balance_after)
        if not updated_wallet:
            raise ValueError("Failed to update wallet balance")
        
        # Create transaction record
        transaction = WalletRepository.create_transaction(
            db=db,
            wallet_id=wallet.id,
            transaction_type="credit",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description or f"Credit of {amount}",
            reference_type=reference_type,
            reference_id=reference_id,
            initiated_by_type=initiated_by_type,
            initiated_by_id=initiated_by_id,
            transaction_metadata=transaction_metadata
        )
        
        return {
            "transaction_id": transaction.id,
            "wallet_id": wallet.id,
            "transaction_type": "credit",
            "amount": float(amount),
            "balance_before": float(balance_before),
            "balance_after": float(balance_after),
            "description": transaction.description,
            "created_at": transaction.created_at.isoformat() if transaction.created_at else None
        }
    
    @staticmethod
    def debit_wallet(
        db: Session,
        user_type: str,
        user_id: int,
        amount: Decimal,
        description: str = None,
        reference_type: str = None,
        reference_id: int = None,
        initiated_by_type: str = None,
        initiated_by_id: int = None,
        transaction_metadata: dict = None
    ) -> Dict:
        """
        Debit money from a wallet (remove money).
        
        Args:
            db: Database session
            user_type: Type of user whose wallet to debit
            user_id: ID of the user
            amount: Amount to debit (must be positive)
            description: Description of the transaction
            reference_type: Type of related entity
            reference_id: ID of related entity
            initiated_by_type: Type of user who initiated this debit
            initiated_by_id: ID of user who initiated
            transaction_metadata: Additional JSON data
        
        Returns:
            Dict: Transaction details and updated balance
        
        Raises:
            ValueError: If wallet doesn't have sufficient balance
        """
        if amount <= 0:
            raise ValueError("Debit amount must be positive")
        
        # Get wallet
        wallet = WalletRepository.get_by_user(db, user_type, user_id)
        if not wallet:
            raise ValueError("Wallet not found")
        
        # Check sufficient balance
        if wallet.current_balance < amount:
            raise ValueError(f"Insufficient balance. Available: {wallet.current_balance}, Required: {amount}")
        
        # Calculate new balance
        balance_before = wallet.current_balance
        balance_after = balance_before - amount
        
        # Update wallet balance
        updated_wallet = WalletRepository.update_balance(db, wallet.id, balance_after)
        if not updated_wallet:
            raise ValueError("Failed to update wallet balance")
        
        # Create transaction record
        transaction = WalletRepository.create_transaction(
            db=db,
            wallet_id=wallet.id,
            transaction_type="debit",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description or f"Debit of {amount}",
            reference_type=reference_type,
            reference_id=reference_id,
            initiated_by_type=initiated_by_type,
            initiated_by_id=initiated_by_id,
            transaction_metadata=transaction_metadata
        )
        
        return {
            "transaction_id": transaction.id,
            "wallet_id": wallet.id,
            "transaction_type": "debit",
            "amount": float(amount),
            "balance_before": float(balance_before),
            "balance_after": float(balance_after),
            "description": transaction.description,
            "created_at": transaction.created_at.isoformat() if transaction.created_at else None
        }
    
    @staticmethod
    def transfer_between_wallets(
        db: Session,
        from_user_type: str,
        from_user_id: int,
        to_user_type: str,
        to_user_id: int,
        amount: Decimal,
        description: str = None,
        initiated_by_type: str = None,
        initiated_by_id: int = None,
        transaction_metadata: dict = None
    ) -> Dict:
        """
        Transfer money from one wallet to another.
        
        Args:
            db: Database session
            from_user_type: Type of user sending money
            from_user_id: ID of user sending money
            to_user_type: Type of user receiving money
            to_user_id: ID of user receiving money
            amount: Amount to transfer (must be positive)
            description: Description of the transfer
            initiated_by_type: Type of user who initiated this transfer
            initiated_by_id: ID of user who initiated
            transaction_metadata: Additional JSON data
        
        Returns:
            Dict: Transfer details including both transactions
        
        Raises:
            ValueError: If sender doesn't have sufficient balance or same wallet
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        
        # Prevent transferring to same wallet
        if from_user_type == to_user_type and from_user_id == to_user_id:
            raise ValueError("Cannot transfer to the same wallet")
        
        # Get sender wallet
        from_wallet = WalletRepository.get_by_user(db, from_user_type, from_user_id)
        if not from_wallet:
            raise ValueError("Sender wallet not found")
        
        # Check sufficient balance
        if from_wallet.current_balance < amount:
            raise ValueError(f"Insufficient balance. Available: {from_wallet.current_balance}, Required: {amount}")
        
        # **OPTIMIZED: Store only collection transaction IDs (lazy loading approach)**
        # This allows distributor to see which shops/routes/zones the money originally came from
        # We store only IDs and fetch details on-demand when displaying (much faster transfers)
        if transaction_metadata is None:
            enhanced_metadata = {}
        elif isinstance(transaction_metadata, dict):
            enhanced_metadata = transaction_metadata.copy()
        else:
            # If it's a string, try to parse it
            try:
                enhanced_metadata = json.loads(transaction_metadata) if isinstance(transaction_metadata, str) else {}
            except (json.JSONDecodeError, TypeError):
                enhanced_metadata = {}
        
        try:
            # OPTIMIZED: Get only recent collection transaction IDs (limit to 10 for performance)
            # Use optimized query: only credit transactions with daily_collection reference
            from models.wallet_transaction import WalletTransaction
            recent_collections = db.query(WalletTransaction).filter(
                WalletTransaction.wallet_id == from_wallet.id,
                WalletTransaction.transaction_type == 'credit',
                WalletTransaction.reference_type == 'daily_collection'
            ).order_by(WalletTransaction.created_at.desc()).limit(10).all()
            
            # Store only transaction IDs (not full data) - we'll fetch details on-demand
            collection_transaction_ids = [t.id for t in recent_collections[:5]]  # Top 5 most recent
            
            if collection_transaction_ids:
                enhanced_metadata['source_collection_transaction_ids'] = collection_transaction_ids
                enhanced_metadata['transfer_amount'] = float(amount)
        except Exception as e:
            # Log error but don't fail transfer - metadata enhancement is optional
            print(f"Warning: Failed to store collection transaction IDs for transfer: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Get or create receiver wallet
        to_wallet = WalletRepository.get_by_user(db, to_user_type, to_user_id)
        if not to_wallet:
            to_wallet = WalletRepository.create(db, to_user_type, to_user_id)
        
        # Calculate balances
        from_balance_before = from_wallet.current_balance
        from_balance_after = from_balance_before - amount
        
        to_balance_before = to_wallet.current_balance
        to_balance_after = to_balance_before + amount
        
        # Update both wallets
        updated_from_wallet = WalletRepository.update_balance(db, from_wallet.id, from_balance_after)
        updated_to_wallet = WalletRepository.update_balance(db, to_wallet.id, to_balance_after)
        
        if not updated_from_wallet or not updated_to_wallet:
            raise ValueError("Failed to update wallet balances")
        
        # Enhance metadata with collection details if this is a distributor collection
        collection_description = description
        if initiated_by_type == 'distributor' and to_user_type == 'distributor':
            # Add collection metadata
            enhanced_metadata['collection_timestamp'] = datetime.utcnow().isoformat()
            enhanced_metadata['collected_by_distributor_id'] = initiated_by_id
            enhanced_metadata['collection_type'] = 'distributor_collection'
            # Get distributor name for better display
            try:
                from repositories.distributor_repository import DistributorRepository
                distributor = DistributorRepository.get_by_id(db, initiated_by_id)
                if distributor:
                    enhanced_metadata['collected_by_distributor_name'] = distributor.name
            except Exception as e:
                print(f"Warning: Could not fetch distributor name: {str(e)}")
            
            # Enhanced description for distributor collections
            collection_timestamp_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            if not collection_description:
                collection_description = f"💰 Money collected by distributor on {collection_timestamp_str} UTC"
            else:
                collection_description = f"💰 {collection_description} (Collected on {collection_timestamp_str} UTC)"
        else:
            collection_description = description or f"Transfer to {to_user_type} {to_user_id}"
        
        transfer_out = WalletRepository.create_transaction(
            db=db,
            wallet_id=from_wallet.id,
            transaction_type="transfer_out",
            amount=amount,
            balance_before=from_balance_before,
            balance_after=from_balance_after,
            description=collection_description,
            reference_type="transfer",
            reference_id=None,  # Will be set to transfer_in transaction ID after creation
            initiated_by_type=initiated_by_type,
            initiated_by_id=initiated_by_id,
            related_wallet_id=to_wallet.id,
            transaction_metadata=enhanced_metadata
        )
        
        # Create transfer_in transaction
        transfer_in = WalletRepository.create_transaction(
            db=db,
            wallet_id=to_wallet.id,
            transaction_type="transfer_in",
            amount=amount,
            balance_before=to_balance_before,
            balance_after=to_balance_after,
            description=description or f"Transfer from {from_user_type} {from_user_id}",
            reference_type="transfer",
            reference_id=transfer_out.id,  # Link to transfer_out transaction
            initiated_by_type=initiated_by_type,
            initiated_by_id=initiated_by_id,
            related_wallet_id=from_wallet.id,
            transaction_metadata=enhanced_metadata
        )
        
        # Update transfer_out reference_id to link to transfer_in
        transfer_out.reference_id = transfer_in.id
        db.commit()
        
        # Log wallet transaction activity
        try:
            from services.activity_log_service import ActivityLogService
            action_type = 'WALLET_COLLECT' if (initiated_by_type == 'distributor' and to_user_type == 'distributor') else 'WALLET_TRANSFER'
            changes_summary = f"Wallet transaction: Rs. {float(amount)} from {from_user_type} {from_user_id} to {to_user_type} {to_user_id}"
            if initiated_by_type == 'distributor' and to_user_type == 'distributor':
                changes_summary = f"Money collected: Rs. {float(amount)} from {from_user_type} {from_user_id} by distributor {initiated_by_id}"
            
            ActivityLogService.log_activity(
                db=db,
                user_id=initiated_by_id,
                user_role=initiated_by_type or 'system',
                action_type=action_type,
                entity_type='wallet_transaction',
                entity_id=transfer_in.id,
                new_values={
                    'from_user_type': from_user_type,
                    'from_user_id': from_user_id,
                    'to_user_type': to_user_type,
                    'to_user_id': to_user_id,
                    'amount': str(amount),
                    'from_balance_before': str(from_balance_before),
                    'from_balance_after': str(from_balance_after),
                    'to_balance_before': str(to_balance_before),
                    'to_balance_after': str(to_balance_after)
                },
                changes_summary=changes_summary,
                metadata={
                    'transfer_out_id': transfer_out.id,
                    'transfer_in_id': transfer_in.id,
                    'description': collection_description,
                    'collection_type': enhanced_metadata.get('collection_type'),
                    'collection_timestamp': enhanced_metadata.get('collection_timestamp')
                },
                status='success'
            )
        except Exception as e:
            # Don't fail transaction if logging fails
            print(f"Warning: Failed to log wallet transaction activity: {str(e)}")
        
        return {
            "transfer_id": transfer_in.id,
            "from_wallet": {
                "wallet_id": from_wallet.id,
                "user_type": from_user_type,
                "user_id": from_user_id,
                "balance_before": float(from_balance_before),
                "balance_after": float(from_balance_after),
                "transaction_id": transfer_out.id
            },
            "to_wallet": {
                "wallet_id": to_wallet.id,
                "user_type": to_user_type,
                "user_id": to_user_id,
                "balance_before": float(to_balance_before),
                "balance_after": float(to_balance_after),
                "transaction_id": transfer_in.id
            },
            "amount": float(amount),
            "description": description,
            "created_at": transfer_in.created_at.isoformat() if transfer_in.created_at else None
        }
    
    @staticmethod
    def get_transaction_history(
        db: Session,
        user_type: str,
        user_id: int,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get transaction history for a wallet.
        
        Args:
            db: Database session
            user_type: Type of user
            user_id: ID of the user
            limit: Maximum number of transactions to return
        
        Returns:
            List of transaction dictionaries
        """
        wallet = WalletRepository.get_by_user(db, user_type, user_id)
        if not wallet:
            return []
        
        transactions = WalletRepository.get_transactions(db, wallet.id, limit)
        
        if not transactions:
            return []
        
        # OPTIMIZED: Batch load all related entities to avoid N+1 queries
        # Collect all IDs that need to be loaded
        collection_ids = [
            t.reference_id for t in transactions 
            if t.reference_type == "daily_collection" and t.reference_id
        ]
        order_booker_ids = []
        delivery_man_ids = []
        shop_ids = []
        
        # Batch load all daily collections (1 query instead of N queries)
        collections_map = {}
        if collection_ids:
            from models.daily_collection import DailyCollection
            collections = db.query(DailyCollection).filter(
                DailyCollection.id.in_(collection_ids)
            ).all()
            collections_map = {c.id: c for c in collections}
            
            # Collect order booker, delivery man, and shop IDs from collections
            for collection in collections:
                if collection.collected_by_order_booker:
                    order_booker_ids.append(collection.collected_by_order_booker)
                if collection.collected_by_delivery_man:
                    delivery_man_ids.append(collection.collected_by_delivery_man)
                if collection.shop_id:
                    shop_ids.append(collection.shop_id)
        
        # Batch load all order bookers (1 query instead of N queries)
        order_bookers_map = {}
        if order_booker_ids:
            from models.order_booker import OrderBooker
            order_bookers = db.query(OrderBooker).filter(
                OrderBooker.id.in_(list(set(order_booker_ids)))
            ).all()
            order_bookers_map = {ob.id: ob for ob in order_bookers}
        
        # Batch load all delivery men (1 query instead of N queries)
        delivery_men_map = {}
        if delivery_man_ids:
            from models.delivery_man import DeliveryMan
            delivery_men = db.query(DeliveryMan).filter(
                DeliveryMan.id.in_(list(set(delivery_man_ids)))
            ).all()
            delivery_men_map = {dm.id: dm for dm in delivery_men}
        
        # OPTIMIZED: Parse metadata ONCE and cache it (avoids parsing twice)
        # This also collects shop IDs and transfer collection IDs for batch loading
        parsed_metadata_map = {}
        transfer_collection_ids_map = {}  # Map transaction_id -> list of collection transaction IDs
        related_wallet_ids = []
        
        for transaction in transactions:
            try:
                metadata_raw = getattr(transaction, 'transaction_metadata', None)
                metadata = {}
                
                if metadata_raw:
                    if isinstance(metadata_raw, dict):
                        metadata = metadata_raw
                    elif isinstance(metadata_raw, str):
                        if metadata_raw.lower() not in ['null', 'none', '']:
                            try:
                                metadata = json.loads(metadata_raw)
                                if not isinstance(metadata, dict):
                                    metadata = {}
                            except (json.JSONDecodeError, TypeError):
                                metadata = {}
                        else:
                            metadata = {}
                    else:
                        metadata = {}
                
                parsed_metadata_map[transaction.id] = metadata
                
                # Collect shop IDs from metadata
                shop_id = metadata.get("shop_id")
                if shop_id:
                    shop_ids.append(shop_id)
                
                # Collect transfer collection transaction IDs for batch loading
                if transaction.reference_type == "transfer" and not metadata.get("shop_name"):
                    collection_ids = metadata.get("source_collection_transaction_ids", [])
                    if collection_ids:
                        transfer_collection_ids_map[transaction.id] = collection_ids
                
                # Collect related wallet IDs
                if transaction.related_wallet_id:
                    related_wallet_ids.append(transaction.related_wallet_id)
            except Exception as e:
                parsed_metadata_map[transaction.id] = {}
                print(f"Warning: Error parsing metadata for transaction {transaction.id}: {str(e)}")
        
        # Batch load shops that need lookup (1 query instead of N queries)
        shops_map = {}
        if shop_ids:
            from models.shop import Shop
            shops = db.query(Shop).filter(Shop.id.in_(list(set(shop_ids)))).all()
            shops_map = {s.id: s for s in shops}
        
        # Collect initiated_by IDs for batch loading
        initiated_by_order_booker_ids = []
        initiated_by_delivery_man_ids = []
        initiated_by_distributor_ids = []
        for transaction in transactions:
            if transaction.initiated_by_type == 'order_booker' and transaction.initiated_by_id:
                initiated_by_order_booker_ids.append(transaction.initiated_by_id)
            elif transaction.initiated_by_type == 'delivery_man' and transaction.initiated_by_id:
                initiated_by_delivery_man_ids.append(transaction.initiated_by_id)
            elif transaction.initiated_by_type == 'distributor' and transaction.initiated_by_id:
                initiated_by_distributor_ids.append(transaction.initiated_by_id)
        
        # Batch load initiated_by entities
        initiated_by_order_bookers_map = {}
        if initiated_by_order_booker_ids:
            from models.order_booker import OrderBooker
            ob_list = db.query(OrderBooker).filter(
                OrderBooker.id.in_(list(set(initiated_by_order_booker_ids)))
            ).all()
            initiated_by_order_bookers_map = {ob.id: ob for ob in ob_list}
        
        initiated_by_delivery_men_map = {}
        if initiated_by_delivery_man_ids:
            from models.delivery_man import DeliveryMan
            dm_list = db.query(DeliveryMan).filter(
                DeliveryMan.id.in_(list(set(initiated_by_delivery_man_ids)))
            ).all()
            initiated_by_delivery_men_map = {dm.id: dm for dm in dm_list}
        
        initiated_by_distributors_map = {}
        if initiated_by_distributor_ids:
            from models.distributor import Distributor
            dist_list = db.query(Distributor).filter(
                Distributor.id.in_(list(set(initiated_by_distributor_ids)))
            ).all()
            initiated_by_distributors_map = {d.id: d for d in dist_list}
        
        # OPTIMIZED: Batch load related wallets and their users (1 query instead of N queries)
        related_wallets_map = {}
        related_user_order_booker_ids = []
        related_user_delivery_man_ids = []
        related_user_distributor_ids = []
        
        if related_wallet_ids:
            related_wallets = db.query(Wallet).filter(
                Wallet.id.in_(list(set(related_wallet_ids)))
            ).all()
            related_wallets_map = {w.id: w for w in related_wallets}
            
            # Collect user IDs for batch loading
            for wallet in related_wallets:
                if wallet.user_type == 'order_booker':
                    related_user_order_booker_ids.append(wallet.user_id)
                elif wallet.user_type == 'delivery_man':
                    related_user_delivery_man_ids.append(wallet.user_id)
                elif wallet.user_type == 'distributor':
                    related_user_distributor_ids.append(wallet.user_id)
        
        # Batch load related user names
        related_user_order_bookers_map = {}
        if related_user_order_booker_ids:
            from models.order_booker import OrderBooker
            ob_list = db.query(OrderBooker).filter(
                OrderBooker.id.in_(list(set(related_user_order_booker_ids)))
            ).all()
            related_user_order_bookers_map = {ob.id: ob for ob in ob_list}
        
        related_user_delivery_men_map = {}
        if related_user_delivery_man_ids:
            from models.delivery_man import DeliveryMan
            dm_list = db.query(DeliveryMan).filter(
                DeliveryMan.id.in_(list(set(related_user_delivery_man_ids)))
            ).all()
            related_user_delivery_men_map = {dm.id: dm for dm in dm_list}
        
        related_user_distributors_map = {}
        if related_user_distributor_ids:
            from models.distributor import Distributor
            dist_list = db.query(Distributor).filter(
                Distributor.id.in_(list(set(related_user_distributor_ids)))
            ).all()
            related_user_distributors_map = {d.id: d for d in dist_list}
        
        # OPTIMIZED: Batch load all transfer trails at once (1 call instead of N calls)
        all_transfer_collection_ids = []
        for collection_ids in transfer_collection_ids_map.values():
            all_transfer_collection_ids.extend(collection_ids)
        
        # Map: collection_transaction_id -> list of trails
        collection_trails_by_transaction_id = {}
        if all_transfer_collection_ids:
            # Get unique collection transaction IDs
            unique_collection_ids = list(set(all_transfer_collection_ids))
            trail_data = WalletService._enrich_transfer_trail(db, unique_collection_ids)
            if trail_data:
                collection_trails = trail_data.get("collection_trails", [])
                # Group trails by collection transaction ID (transaction_id in trail is the wallet transaction ID)
                for trail in collection_trails:
                    trans_id = trail.get('transaction_id')
                    if trans_id:
                        if trans_id not in collection_trails_by_transaction_id:
                            collection_trails_by_transaction_id[trans_id] = []
                        collection_trails_by_transaction_id[trans_id].append(trail)
        
        result = []
        for transaction in transactions:
            try:
                # Build base transaction data
                # Safely access all attributes with None checks
                transaction_data = {
                    "id": transaction.id if hasattr(transaction, 'id') else None,
                    "transaction_type": transaction.transaction_type if hasattr(transaction, 'transaction_type') else None,
                    "amount": float(transaction.amount) if hasattr(transaction, 'amount') and transaction.amount else 0.0,
                    "balance_before": float(transaction.balance_before) if hasattr(transaction, 'balance_before') and transaction.balance_before else 0.0,
                    "balance_after": float(transaction.balance_after) if hasattr(transaction, 'balance_after') and transaction.balance_after else 0.0,
                    "description": transaction.description if hasattr(transaction, 'description') else None,
                    "reference_type": transaction.reference_type if hasattr(transaction, 'reference_type') else None,
                    "reference_id": transaction.reference_id if hasattr(transaction, 'reference_id') else None,
                    "initiated_by_type": transaction.initiated_by_type if hasattr(transaction, 'initiated_by_type') else None,
                    "initiated_by_id": transaction.initiated_by_id if hasattr(transaction, 'initiated_by_id') else None,
                    "related_wallet_id": transaction.related_wallet_id if hasattr(transaction, 'related_wallet_id') else None,
                    "metadata": getattr(transaction, 'transaction_metadata', None),
                    "created_at": transaction.created_at.isoformat() if hasattr(transaction, 'created_at') and transaction.created_at else None
                }
                
                # OPTIMIZED: Use pre-parsed metadata (avoids parsing JSON twice)
                metadata = parsed_metadata_map.get(transaction.id, {})
                
                # Get shop name and trail information from metadata
                try:
                    shop_name = metadata.get("shop_name")
                    shop_id = metadata.get("shop_id")
                    shop_owner = metadata.get("shop_owner")
                    route_id = metadata.get("route_id")
                    route_name = metadata.get("route_name")
                    zone_id = metadata.get("zone_id")
                    zone_name = metadata.get("zone_name")
                    
                    # OPTIMIZED: For transfers, use batch-loaded collection trails
                    if transaction.reference_type == "transfer" and not shop_name:
                        # Check if we have batch-loaded trails for this transaction
                        collection_transaction_ids = transfer_collection_ids_map.get(transaction.id, [])
                        if collection_transaction_ids:
                            # Find trails for any of the collection transaction IDs
                            collection_trails = []
                            for coll_trans_id in collection_transaction_ids:
                                if coll_trans_id in collection_trails_by_transaction_id:
                                    collection_trails.extend(collection_trails_by_transaction_id[coll_trans_id])
                            
                            if collection_trails:
                                # Sort by transaction_id descending to get most recent first
                                collection_trails.sort(key=lambda x: x.get('transaction_id', 0), reverse=True)
                                # Use the first (most recent) collection trail for quick access
                                trail = collection_trails[0]
                                shop_name = trail.get("shop_name") or shop_name
                                shop_id = trail.get("shop_id") or shop_id
                                shop_owner = trail.get("shop_owner") or shop_owner
                                route_id = trail.get("route_id") or route_id
                                route_name = trail.get("route_name") or route_name
                                zone_id = trail.get("zone_id") or zone_id
                                zone_name = trail.get("zone_name") or zone_name
                                
                                # Store all trails for display
                                transaction_data["collection_trails"] = collection_trails
                                transaction_data["trail_count"] = len(collection_trails)
                    
                    # Backward compatibility: Check old format (collection_trails directly in metadata)
                    elif transaction.reference_type == "transfer" and not shop_name:
                        collection_trails = metadata.get("collection_trails", [])
                        if collection_trails and len(collection_trails) > 0:
                            # Use the first (most recent) collection trail
                            trail = collection_trails[0]
                            shop_name = trail.get("shop_name") or shop_name
                            shop_id = trail.get("shop_id") or shop_id
                            shop_owner = trail.get("shop_owner") or shop_owner
                            route_id = trail.get("route_id") or route_id
                            route_name = trail.get("route_name") or route_name
                            zone_id = trail.get("zone_id") or zone_id
                            zone_name = trail.get("zone_name") or zone_name
                            
                            # Store all trails for display
                            transaction_data["collection_trails"] = collection_trails
                            transaction_data["trail_count"] = len(collection_trails)
                    
                    # If metadata doesn't have shop info but has shop_id, look it up from batch-loaded data
                    if not shop_name and shop_id and shop_id in shops_map:
                        shop = shops_map[shop_id]
                        shop_name = shop.name
                        shop_owner = shop.owner_name
                        if not route_id:
                            route_id = shop.route_id
                        if not zone_id:
                            zone_id = shop.zone_id
                    
                    # Add shop information to transaction data
                    if shop_name:
                        transaction_data["shop_name"] = shop_name
                    if shop_id:
                        transaction_data["shop_id"] = shop_id
                    if shop_owner:
                        transaction_data["shop_owner"] = shop_owner
                    if route_id:
                        transaction_data["route_id"] = route_id
                    if route_name:
                        transaction_data["route_name"] = route_name
                    if zone_id:
                        transaction_data["zone_id"] = zone_id
                    if zone_name:
                        transaction_data["zone_name"] = zone_name
                except Exception as e:
                    print(f"Warning: Error getting shop info for transaction {transaction.id if hasattr(transaction, 'id') else 'unknown'}: {str(e)}")
                
                # Get collection details if reference_type is daily_collection (using batch-loaded data)
                try:
                    if transaction.reference_type == "daily_collection" and transaction.reference_id:
                        collection = collections_map.get(transaction.reference_id)
                        if collection:
                            transaction_data["collection_id"] = collection.id
                            transaction_data["collection_amount"] = float(collection.amount) if collection.amount else 0.0
                            transaction_data["collection_date"] = collection.collection_date.isoformat() if collection.collection_date else None
                            # Handle status - might be enum or string
                            try:
                                if hasattr(collection.status, 'value'):
                                    transaction_data["collection_status"] = collection.status.value
                                elif hasattr(collection.status, '__str__'):
                                    transaction_data["collection_status"] = str(collection.status)
                                else:
                                    transaction_data["collection_status"] = collection.status
                            except Exception:
                                transaction_data["collection_status"] = str(collection.status) if collection.status else None
                            
                            # Get collector name (order booker or delivery man) from batch-loaded data
                            try:
                                if collection.collected_by_order_booker:
                                    ob = order_bookers_map.get(collection.collected_by_order_booker)
                                    if ob:
                                        transaction_data["collected_by_name"] = ob.name
                                        transaction_data["collected_by_type"] = "order_booker"
                                        transaction_data["collected_by_id"] = ob.id
                                elif collection.collected_by_delivery_man:
                                    dm = delivery_men_map.get(collection.collected_by_delivery_man)
                                    if dm:
                                        transaction_data["collected_by_name"] = dm.name
                                        transaction_data["collected_by_type"] = "delivery_man"
                                        transaction_data["collected_by_id"] = dm.id
                            except Exception as e:
                                print(f"Warning: Error getting collector info for transaction {transaction.id}: {str(e)}")
                except Exception as e:
                    print(f"Warning: Error getting collection details for transaction {transaction.id}: {str(e)}")
                
                # Get initiated by name (using batch-loaded data)
                try:
                    if transaction.initiated_by_type and transaction.initiated_by_id:
                        if transaction.initiated_by_type == "order_booker":
                            ob = initiated_by_order_bookers_map.get(transaction.initiated_by_id)
                            if ob:
                                transaction_data["initiated_by_name"] = ob.name
                        elif transaction.initiated_by_type == "delivery_man":
                            dm = initiated_by_delivery_men_map.get(transaction.initiated_by_id)
                            if dm:
                                transaction_data["initiated_by_name"] = dm.name
                        elif transaction.initiated_by_type == "distributor":
                            dist = initiated_by_distributors_map.get(transaction.initiated_by_id)
                            if dist:
                                transaction_data["initiated_by_name"] = dist.name
                except Exception as e:
                    print(f"Warning: Error getting initiated_by info for transaction {transaction.id}: {str(e)}")
                
                # OPTIMIZED: For transfers, get related wallet user info from batch-loaded data
                try:
                    if transaction.related_wallet_id:
                        related_wallet = related_wallets_map.get(transaction.related_wallet_id)
                        if related_wallet:
                            transaction_data["related_user_type"] = related_wallet.user_type
                            transaction_data["related_user_id"] = related_wallet.user_id
                            # Get related user name from batch-loaded data
                            if related_wallet.user_type == "order_booker":
                                ob = related_user_order_bookers_map.get(related_wallet.user_id)
                                if ob:
                                    transaction_data["related_user_name"] = ob.name
                            elif related_wallet.user_type == "delivery_man":
                                dm = related_user_delivery_men_map.get(related_wallet.user_id)
                                if dm:
                                    transaction_data["related_user_name"] = dm.name
                            elif related_wallet.user_type == "distributor":
                                dist = related_user_distributors_map.get(related_wallet.user_id)
                                if dist:
                                    transaction_data["related_user_name"] = dist.name
                except Exception as e:
                    print(f"Warning: Error getting related wallet info for transaction {transaction.id}: {str(e)}")
                
                result.append(transaction_data)
            except Exception as e:
                # If there's an error processing a transaction, log it but continue with other transactions
                print(f"Error processing transaction {transaction.id}: {str(e)}")
                import traceback
                traceback.print_exc()
                # Still add basic transaction data even if enrichment fails
                try:
                    result.append({
                        "id": transaction.id,
                        "transaction_type": transaction.transaction_type,
                        "amount": float(transaction.amount) if transaction.amount else 0.0,
                        "balance_before": float(transaction.balance_before) if transaction.balance_before else 0.0,
                        "balance_after": float(transaction.balance_after) if transaction.balance_after else 0.0,
                        "description": transaction.description,
                        "reference_type": transaction.reference_type,
                        "reference_id": transaction.reference_id,
                        "created_at": transaction.created_at.isoformat() if transaction.created_at else None
                    })
                except Exception:
                    # If even basic data fails, skip this transaction
                    continue
        
        return result
    
    @staticmethod
    def _enrich_transfer_trail(db: Session, collection_transaction_ids: List[int]) -> Dict:
        """
        OPTIMIZED: Enrich transfer transaction with collection trail details on-demand.
        This method is called when displaying transfer details, not during transfer creation.
        
        Args:
            db: Database session
            collection_transaction_ids: List of wallet transaction IDs that are collections
        
        Returns:
            Dict with collection_trails array containing enriched trail information
        """
        if not collection_transaction_ids:
            return {}
        
        try:
            from models.wallet_transaction import WalletTransaction
            from models.daily_collection import DailyCollection
            from models.shop import Shop
            from models.route import Route
            from models.zone import Zone
            
            # OPTIMIZED: Single query to get all collection transactions
            collection_transactions = db.query(WalletTransaction).filter(
                WalletTransaction.id.in_(collection_transaction_ids),
                WalletTransaction.reference_type == 'daily_collection',
                WalletTransaction.transaction_type == 'credit'
            ).order_by(WalletTransaction.created_at.desc()).all()
            
            if not collection_transactions:
                return {}
            
            # Extract collection IDs from transactions
            collection_ids = [t.reference_id for t in collection_transactions if t.reference_id]
            
            if not collection_ids:
                return {}
            
            # Get daily collections with shop/route/zone info in one query
            collections = db.query(DailyCollection).filter(
                DailyCollection.id.in_(collection_ids)
            ).all()
            
            # Build lookup maps for efficient access
            collection_map = {c.id: c for c in collections}
            shop_ids = [c.shop_id for c in collections if c.shop_id]
            shops = {}
            routes = {}
            zones = {}
            
            if shop_ids:
                # Get shops
                shop_list = db.query(Shop).filter(
                    Shop.id.in_(shop_ids)
                ).all()
                shops = {s.id: s for s in shop_list}
                
                # Get routes
                route_ids = [s.route_id for s in shop_list if s.route_id]
                if route_ids:
                    route_list = db.query(Route).filter(
                        Route.id.in_(route_ids)
                    ).all()
                    routes = {r.id: r for r in route_list}
                
                # Get zones
                zone_ids = list(set([s.zone_id for s in shop_list if s.zone_id] + 
                                   [r.zone_id for r in routes.values() if r.zone_id]))
                if zone_ids:
                    zone_list = db.query(Zone).filter(
                        Zone.id.in_(zone_ids)
                    ).all()
                    zones = {z.id: z for z in zone_list}
            
            # Build enriched trail information
            trails = []
            for trans in collection_transactions:
                collection = collection_map.get(trans.reference_id) if trans.reference_id else None
                if not collection:
                    continue
                
                shop = shops.get(collection.shop_id) if collection.shop_id else None
                route = routes.get(shop.route_id) if shop and shop.route_id else None
                zone = zones.get(shop.zone_id) if shop and shop.zone_id else None
                if route and route.zone_id and not zone:
                    zone = zones.get(route.zone_id)
                
                # Parse transaction metadata for additional info
                trans_meta = trans.transaction_metadata or {}
                if isinstance(trans_meta, str):
                    try:
                        trans_meta = json.loads(trans_meta) if trans_meta != 'null' else {}
                    except (json.JSONDecodeError, TypeError):
                        trans_meta = {}
                
                trail = {
                    'transaction_id': trans.id,
                    'collection_id': collection.id,
                    'shop_id': shop.id if shop else None,
                    'shop_name': shop.name if shop else trans_meta.get('shop_name'),
                    'shop_owner': shop.owner_name if shop else trans_meta.get('shop_owner'),
                    'route_id': route.id if route else (shop.route_id if shop else trans_meta.get('route_id')),
                    'route_name': route.name if route else trans_meta.get('route_name'),
                    'zone_id': zone.id if zone else (shop.zone_id if shop else trans_meta.get('zone_id')),
                    'zone_name': zone.name if zone else trans_meta.get('zone_name'),
                    'collection_amount': float(trans.amount) if trans.amount else 0.0,
                    'collection_date': collection.collection_date.isoformat() if collection.collection_date else trans_meta.get('collection_date'),
                    'status': collection.status if collection else trans_meta.get('status')
                }
                trails.append(trail)
            
            return {'collection_trails': trails}
            
        except Exception as e:
            print(f"Warning: Error enriching transfer trail: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    @staticmethod
    def get_all_wallets_for_distributor(db: Session, distributor_id: int) -> List[Dict]:
        """
        Get all wallets of order bookers and delivery men under a distributor.
        OPTIMIZED: Uses batch loading to avoid N+1 queries.
        
        Args:
            db: Database session
            distributor_id: ID of the distributor
        
        Returns:
            List of wallet dictionaries with user information
        """
        from repositories.order_booker_repository import OrderBookerRepository
        from repositories.delivery_man_repository import DeliveryManRepository
        from models.wallet import Wallet
        
        result = []
        
        # Get all order bookers for this distributor
        order_bookers = OrderBookerRepository.get_by_distributor(db, distributor_id)
        
        if order_bookers:
            # Batch load all wallets for order bookers (1 query instead of N queries)
            order_booker_ids = [ob.id for ob in order_bookers]
            wallets = db.query(Wallet).filter(
                Wallet.user_type == 'order_booker',
                Wallet.user_id.in_(order_booker_ids)
            ).all()
            wallets_map = {(w.user_type, w.user_id): w for w in wallets}
            
            # Process order bookers using lookup map
            for ob in order_bookers:
                wallet = wallets_map.get(('order_booker', ob.id))
                if wallet:
                    result.append({
                        "wallet_id": wallet.id,
                        "user_type": "order_booker",
                        "user_id": ob.id,
                        "user_name": ob.name,
                        "user_phone": ob.phone,
                        "current_balance": float(wallet.current_balance) if wallet.current_balance else 0.0,
                        "is_active": wallet.is_active,
                        "created_at": wallet.created_at.isoformat() if wallet.created_at else None
                    })
                else:
                    # Create wallet if it doesn't exist
                    wallet = WalletRepository.create(db, 'order_booker', ob.id)
                    result.append({
                        "wallet_id": wallet.id,
                        "user_type": "order_booker",
                        "user_id": ob.id,
                        "user_name": ob.name,
                        "user_phone": ob.phone,
                        "current_balance": 0.0,
                        "is_active": wallet.is_active,
                        "created_at": wallet.created_at.isoformat() if wallet.created_at else None
                    })
        
        # Get all delivery men for this distributor
        delivery_men = DeliveryManRepository.get_by_distributor(db, distributor_id)
        
        if delivery_men:
            # Batch load all wallets for delivery men (1 query instead of N queries)
            delivery_man_ids = [dm.id for dm in delivery_men]
            wallets = db.query(Wallet).filter(
                Wallet.user_type == 'delivery_man',
                Wallet.user_id.in_(delivery_man_ids)
            ).all()
            wallets_map = {(w.user_type, w.user_id): w for w in wallets}
            
            # Process delivery men using lookup map
            for dm in delivery_men:
                wallet = wallets_map.get(('delivery_man', dm.id))
                if wallet:
                    result.append({
                        "wallet_id": wallet.id,
                        "user_type": "delivery_man",
                        "user_id": dm.id,
                        "user_name": dm.name,
                        "user_phone": dm.phone,
                        "current_balance": float(wallet.current_balance) if wallet.current_balance else 0.0,
                        "is_active": wallet.is_active,
                        "created_at": wallet.created_at.isoformat() if wallet.created_at else None
                    })
                else:
                    # Create wallet if it doesn't exist
                    wallet = WalletRepository.create(db, 'delivery_man', dm.id)
                    result.append({
                        "wallet_id": wallet.id,
                        "user_type": "delivery_man",
                        "user_id": dm.id,
                        "user_name": dm.name,
                        "user_phone": dm.phone,
                        "current_balance": 0.0,
                        "is_active": wallet.is_active,
                        "created_at": wallet.created_at.isoformat() if wallet.created_at else None
                    })
        
        return result

