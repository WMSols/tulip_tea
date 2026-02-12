"""
Order Booker business logic service.
"""
from sqlalchemy.orm import Session
from repositories.order_booker_repository import OrderBookerRepository
from repositories.distributor_repository import DistributorRepository
from repositories.zone_repository import ZoneRepository
from services.auth_service import get_password_hash, verify_password, create_access_token
from typing import Optional, Dict, List


class OrderBookerService:
    """Service for Order Booker business logic."""
    
    @staticmethod
    def create_order_booker(db: Session, distributor_id: int, name: str, phone: str,
                           password: str, email: str = None, zone_id: int = None) -> Dict:
        """
        Create a new order booker (only by distributor).
        
        Returns:
            Dictionary with order booker data
        """
        # Verify distributor exists
        distributor = DistributorRepository.get_by_id(db, distributor_id)
        if not distributor:
            raise ValueError("Distributor not found")
        
        # Check if phone already exists
        existing = OrderBookerRepository.get_by_phone(db, phone)
        if existing:
            raise ValueError("Phone number already registered")
        
        # Hash password
        password_hash = get_password_hash(password)
        
        # Create order booker
        order_booker = OrderBookerRepository.create(
            db=db,
            distributor_id=distributor_id,
            name=name,
            phone=phone,
            password_hash=password_hash,
            email=email,
            zone_id=zone_id
        )
        
        # Get denormalized names
        zone_name = None
        if zone_id:
            zone = ZoneRepository.get_by_id(db, zone_id)
            zone_name = zone.name if zone else None
        
        distributor_name = distributor.name if distributor else None
        
        # Create wallet for order booker
        try:
            from services.wallet_service import WalletService
            WalletService.get_or_create_wallet(db, "order_booker", order_booker.id)
        except Exception as e:
            # Log error but don't fail user creation
            print(f"Warning: Failed to create wallet for order booker {order_booker.id}: {str(e)}")
        
        return {
            "id": order_booker.id,
            "name": order_booker.name,
            "email": order_booker.email,
            "phone": order_booker.phone,
            "zone_id": order_booker.zone_id,
            "zone_name": zone_name,
            "distributor_id": order_booker.distributor_id,
            "distributor_name": distributor_name,
            "created_at": order_booker.created_at.isoformat() if order_booker.created_at else None
        }
    
    @staticmethod
    def login_order_booker(db: Session, phone: str, password: str) -> Optional[Dict]:
        """
        Authenticate order booker and return JWT token.
        
        Returns:
            Dictionary with access_token and user info, or None if invalid
        """
        # Get order booker by phone (include_deleted=False to exclude soft-deleted and inactive)
        order_booker = OrderBookerRepository.get_by_phone(db, phone, include_deleted=False)
        if not order_booker:
            return None
        
        # Check if order booker is active
        if not order_booker.is_active:
            return None
        
        # Verify password
        if not verify_password(password, order_booker.password_hash):
            return None
        
        # Create JWT token
        token_data = {
            "sub": str(order_booker.id),
            "role": "order_booker",
            "phone": order_booker.phone
        }
        access_token = create_access_token(data=token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": order_booker.id,
                "name": order_booker.name,
                "email": order_booker.email,
                "phone": order_booker.phone,
                "zone_id": order_booker.zone_id,
                "distributor_id": order_booker.distributor_id,
                "role": "order_booker"
            }
        }
    
    @staticmethod
    def get_order_bookers_by_distributor(db: Session, distributor_id: int) -> List[Dict]:
        """
        Get all order bookers for a distributor.
        OPTIMIZED: Uses batch loading to avoid N+1 queries.
        """
        try:
            order_bookers = OrderBookerRepository.get_by_distributor(db, distributor_id)
            
            if not order_bookers:
                return []
            
            # Batch load all zones (1 query instead of N queries)
            from models.zone import Zone
            zone_ids = list(set([ob.zone_id for ob in order_bookers if ob.zone_id]))
            zones_map = {}
            if zone_ids:
                zones = db.query(Zone).filter(Zone.id.in_(zone_ids)).all()
                zones_map = {zone.id: zone for zone in zones}
            
            # Get distributor name once
            distributor = DistributorRepository.get_by_id(db, distributor_id)
            distributor_name = distributor.name if distributor else None
            
            # Build result using lookup map (no additional queries)
            result = []
            for ob in order_bookers:
                zone_name = None
                if ob.zone_id and ob.zone_id in zones_map:
                    zone_name = zones_map[ob.zone_id].name
                
                result.append({
                    "id": ob.id,
                    "name": ob.name,
                    "email": ob.email if ob.email else None,
                    "phone": ob.phone,
                    "zone_id": ob.zone_id,
                    "zone_name": zone_name,
                    "distributor_id": ob.distributor_id,
                    "distributor_name": distributor_name,
                    "created_at": ob.created_at.isoformat() if ob.created_at else None
                })
            return result
        except Exception as e:
            raise ValueError(f"Error fetching order bookers: {str(e)}")
    
    @staticmethod
    def get_order_bookers_by_zone(db: Session, zone_id: int, distributor_id: int = None) -> List[Dict]:
        """
        Get all order bookers assigned to a specific zone.
        
        Args:
            db: Database session
            zone_id: Zone ID to filter by
            distributor_id: Optional distributor ID to further filter
        
        Returns:
            List of order bookers in the specified zone
        """
        try:
            order_bookers = OrderBookerRepository.get_by_zone(db, zone_id, distributor_id)
            # Get zone name once
            zone = ZoneRepository.get_by_id(db, zone_id)
            zone_name = zone.name if zone else None
            
            result = []
            for ob in order_bookers:
                # Get distributor name
                distributor_name = None
                if ob.distributor_id:
                    distributor = DistributorRepository.get_by_id(db, ob.distributor_id)
                    distributor_name = distributor.name if distributor else None
                
                result.append({
                    "id": ob.id,
                    "name": ob.name,
                    "email": ob.email if ob.email else None,
                    "phone": ob.phone,
                    "zone_id": ob.zone_id,
                    "zone_name": zone_name,
                    "distributor_id": ob.distributor_id,
                    "distributor_name": distributor_name,
                    "created_at": ob.created_at.isoformat() if ob.created_at else None
                })
            return result
        except Exception as e:
            raise ValueError(f"Error fetching order bookers: {str(e)}")
    
    @staticmethod
    def update_order_booker(db: Session, order_booker_id: int, name: str = None,
                           phone: str = None, email: str = None, zone_id: int = None,
                           password: str = None) -> Dict:
        """Update an order booker."""
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        password_hash = None
        if password:
            password_hash = get_password_hash(password)
        
        updated = OrderBookerRepository.update(
            db=db,
            order_booker_id=order_booker_id,
            name=name,
            phone=phone,
            email=email,
            zone_id=zone_id,
            password_hash=password_hash
        )
        
        if not updated:
            raise ValueError("Failed to update order booker")
        
        # Get denormalized names
        zone_name = None
        if updated.zone_id:
            zone = ZoneRepository.get_by_id(db, updated.zone_id)
            zone_name = zone.name if zone else None
        
        distributor_name = None
        if updated.distributor_id:
            distributor = DistributorRepository.get_by_id(db, updated.distributor_id)
            distributor_name = distributor.name if distributor else None
        
        return {
            "id": updated.id,
            "name": updated.name,
            "email": updated.email,
            "phone": updated.phone,
            "zone_id": updated.zone_id,
            "zone_name": zone_name,
            "distributor_id": updated.distributor_id,
            "distributor_name": distributor_name,
            "created_at": updated.created_at.isoformat() if updated.created_at else None
        }
    
    @staticmethod
    def delete_order_booker(db: Session, order_booker_id: int, 
                           reassign_shops_to: int = None, 
                           reassign_routes_to: int = None,
                           deleter_id: int = None,
                           request = None) -> bool:
        """
        Soft delete an order booker with optional reassignment of shops and routes.
        
        This method handles the soft deletion of an order booker while preserving data integrity.
        It supports reassigning shops and routes to another order booker, or unassigning them if no reassignment is provided.
        
        FLOW:
        1. Verify order booker exists
        2. Check for shops assigned to this order booker (assigned_to_order_booker)
           - If reassign_shops_to is provided: Reassign all shops to new order booker
           - If not provided: Unassign shops (set assigned_to_order_booker to NULL)
           - created_by_order_booker remains unchanged for audit trail
        3. Check for routes assigned to this order booker
           - If reassign_routes_to is provided: Reassign all routes to new order booker
           - If not provided: Unassign routes (set order_booker_id to NULL)
        4. Soft delete the order booker (set deleted_at and is_active=False)
        
        IMPORTANT NOTES:
        - This is a SOFT DELETE - data is preserved, just hidden from normal operations
        - When shops are reassigned, only assigned_to_order_booker is updated
        - created_by_order_booker remains unchanged for audit trail
        - Routes can be reassigned or unassigned (set to NULL)
        - Order booker cannot login after soft deletion (is_active=False)
        
        Args:
            db: Database session
            order_booker_id: ID of order booker to soft delete
            reassign_shops_to: Optional - New order booker ID to reassign shops to. If None, shops are unassigned.
            reassign_routes_to: Optional - New order booker ID to reassign routes to. If None, routes are unassigned.
            deleter_id: Optional - ID of user performing the deletion (for logging)
            request: Optional - FastAPI request object (for logging context)
        
        Returns:
            bool: True if successful
        
        Raises:
            ValueError: If order booker not found, or if reassignment order booker doesn't exist
        """
        from models.shop import Shop
        from models.route import Route
        from repositories.shop_repository import ShopRepository
        
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        # Check for shops assigned to this order booker (assigned_to_order_booker, not created_by)
        # Note: created_by_order_booker is kept for audit trail, we only need to handle assigned_to
        shops = db.query(Shop).filter(Shop.assigned_to_order_booker == order_booker_id).all()
        shops_count = len(shops)
        
        if shops_count > 0:
            if reassign_shops_to:
                # Verify new order booker exists
                new_order_booker = OrderBookerRepository.get_by_id(db, reassign_shops_to)
                if not new_order_booker:
                    raise ValueError(f"Reassignment order booker (ID: {reassign_shops_to}) not found")
                
                # Reassign shops: Update assigned_to_order_booker, keep created_by_order_booker for audit
                reassigned_count = ShopRepository.reassign_shops_to_order_booker(
                    db=db,
                    from_order_booker_id=order_booker_id,
                    to_order_booker_id=reassign_shops_to
                )
                
                # Verify all shops were reassigned
                if reassigned_count != shops_count:
                    raise ValueError(
                        f"Reassignment incomplete: Expected {shops_count} shops, "
                        f"but only {reassigned_count} were reassigned."
                    )
            else:
                # For soft delete, we can just unassign shops (set assigned_to_order_booker to NULL)
                # This allows soft deletion without requiring reassignment
                # created_by_order_booker remains unchanged for audit trail
                for shop in shops:
                    shop.assigned_to_order_booker = None
                db.commit()
        
        # Check for routes assigned to this order booker
        routes = db.query(Route).filter(Route.order_booker_id == order_booker_id).all()
        routes_count = len(routes)
        
        if routes_count > 0:
            if reassign_routes_to:
                # Verify new order booker exists
                new_order_booker = OrderBookerRepository.get_by_id(db, reassign_routes_to)
                if not new_order_booker:
                    raise ValueError(f"Reassignment order booker (ID: {reassign_routes_to}) not found")
                
                # Reassign routes: Update order_booker_id for all routes
                for route in routes:
                    route.order_booker_id = reassign_routes_to
                db.commit()
            else:
                # For soft delete, we can just unassign routes (set to NULL) instead of blocking deletion
                # This allows soft deletion without requiring reassignment
                for route in routes:
                    route.order_booker_id = None
                db.commit()
        
        # Now safe to soft delete the order booker
        success = OrderBookerRepository.delete(db, order_booker_id)
        if success:
            # Log the soft delete operation
            from services.activity_log_service import ActivityLogService
            ActivityLogService.log_delete(
                db=db,
                user_id=deleter_id,
                user_role='distributor',
                entity_type='order_booker',
                entity_id=order_booker_id,
                changes_summary=f"Soft deleted Order Booker {order_booker.name} (ID: {order_booker_id})",
                metadata={
                    'reassigned_shops_to': reassign_shops_to,
                    'reassigned_routes_to': reassign_routes_to,
                    'shops_count': shops_count,
                    'routes_count': routes_count,
                    'shops_unassigned': shops_count > 0 and not reassign_shops_to,
                    'routes_unassigned': routes_count > 0 and not reassign_routes_to
                },
                request=request
            )
        return success

