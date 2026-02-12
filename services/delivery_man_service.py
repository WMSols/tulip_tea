"""
Delivery Man business logic service.
"""
from sqlalchemy.orm import Session
from repositories.delivery_man_repository import DeliveryManRepository
from repositories.distributor_repository import DistributorRepository
from services.auth_service import get_password_hash, verify_password, create_access_token
from typing import Optional, Dict, List


class DeliveryManService:
    """Service for Delivery Man business logic."""
    
    @staticmethod
    def create_delivery_man(db: Session, distributor_id: int, name: str, phone: str,
                           password: str, zone_id: int = None, route_ids: List[int] = None) -> Dict:
        """
        Create a new delivery man with zone and route assignments.
        
        FLOW:
        1. Validates distributor exists
        2. Validates zone exists (if provided)
        3. Validates routes exist and belong to the same zone (if provided)
        4. Creates delivery man with zone_id
        5. Assigns routes to delivery man
        6. Returns delivery man data with route assignments
        
        Args:
            db: Database session
            distributor_id: Distributor ID creating the delivery man
            name: Delivery man name
            phone: Delivery man phone
            password: Plain text password (will be hashed)
            zone_id: Optional zone ID to assign
            route_ids: Optional list of route IDs to assign
        
        Returns:
            Dictionary with delivery man data including route_ids
        """
        from repositories.zone_repository import ZoneRepository
        from repositories.route_repository import RouteRepository
        # DeliveryManRouteRepository removed - delivery men now work by zone, not routes
        
        # Verify distributor exists
        distributor = DistributorRepository.get_by_id(db, distributor_id)
        if not distributor:
            raise ValueError("Distributor not found")
        
        # Verify zone exists (if provided)
        if zone_id:
            zone = ZoneRepository.get_by_id(db, zone_id)
            if not zone:
                raise ValueError(f"Zone with ID {zone_id} not found")
        
        # Note: route_ids parameter is ignored - delivery men work by zone only
        # Routes are no longer assigned to delivery men
        
        # Check if phone already exists
        existing = DeliveryManRepository.get_by_phone(db, phone)
        if existing:
            raise ValueError("Phone number already registered")
        
        # Hash password
        password_hash = get_password_hash(password)
        
        # Create delivery man
        delivery_man = DeliveryManRepository.create(
            db=db,
            distributor_id=distributor_id,
            name=name,
            phone=phone,
            password_hash=password_hash,
            zone_id=zone_id
        )
        
        # Route assignment removed - delivery men now work by zone, not routes
        # Routes are no longer assigned to delivery men
        assigned_route_ids = []
        
        # Create wallet for delivery man
        try:
            from services.wallet_service import WalletService
            WalletService.get_or_create_wallet(db, "delivery_man", delivery_man.id)
        except Exception as e:
            # Log error but don't fail user creation
            print(f"Warning: Failed to create wallet for delivery man {delivery_man.id}: {str(e)}")
        
        return {
            "id": delivery_man.id,
            "name": delivery_man.name,
            "phone": delivery_man.phone,
            "distributor_id": delivery_man.distributor_id,
            "zone_id": delivery_man.zone_id,
            "route_ids": assigned_route_ids,
            "created_at": delivery_man.created_at.isoformat() if delivery_man.created_at else None
        }
    
    @staticmethod
    def login_delivery_man(db: Session, phone: str, password: str) -> Optional[Dict]:
        """
        Authenticate delivery man and return JWT token.
        
        Returns:
            Dictionary with access_token and user info, or None if invalid
        """
        # Get delivery man by phone (include_deleted=False to exclude soft-deleted and inactive)
        delivery_man = DeliveryManRepository.get_by_phone(db, phone, include_deleted=False)
        if not delivery_man:
            return None
        
        # Check if delivery man is active
        if not delivery_man.is_active:
            return None
        
        # Verify password
        if not verify_password(password, delivery_man.password_hash):
            return None
        
        # Create JWT token
        token_data = {
            "sub": str(delivery_man.id),
            "role": "delivery_man",
            "phone": delivery_man.phone
        }
        access_token = create_access_token(data=token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": delivery_man.id,
                "name": delivery_man.name,
                "phone": delivery_man.phone,
                "distributor_id": delivery_man.distributor_id,
                "role": "delivery_man"
            }
        }
    
    @staticmethod
    def get_delivery_men_by_distributor(db: Session, distributor_id: int) -> List[Dict]:
        """
        Get all delivery men for a distributor (zone-based, not route-based).
        OPTIMIZED: Uses batch loading to avoid N+1 queries.
        """
        try:
            delivery_men = DeliveryManRepository.get_by_distributor(db, distributor_id)
            
            if not delivery_men:
                return []
            
            # Batch load all routes by zone (1 query per unique zone instead of N queries)
            from models.route import Route
            zone_ids = list(set([dm.zone_id for dm in delivery_men if dm.zone_id]))
            routes_by_zone = {}
            if zone_ids:
                routes = db.query(Route).filter(
                    Route.zone_id.in_(zone_ids),
                    Route.deleted_at.is_(None)
                ).all()
                # Group routes by zone_id
                for route in routes:
                    if route.zone_id not in routes_by_zone:
                        routes_by_zone[route.zone_id] = []
                    routes_by_zone[route.zone_id].append(route.id)
            
            # Build result using lookup map (no additional queries)
            result = []
            for dm in delivery_men:
                route_ids = routes_by_zone.get(dm.zone_id, []) if dm.zone_id else []
                
                result.append({
                    "id": dm.id,
                    "name": dm.name,
                    "phone": dm.phone,
                    "zone_id": dm.zone_id,
                    "distributor_id": dm.distributor_id,
                    "route_ids": route_ids,  # Routes in zone (for display)
                    "created_at": dm.created_at.isoformat() if dm.created_at else None
                })
            return result
        except Exception as e:
            raise ValueError(f"Error retrieving delivery men: {str(e)}")
    
    @staticmethod
    def update_delivery_man(db: Session, delivery_man_id: int, name: str = None,
                           phone: str = None, zone_id: int = None,
                           password: str = None) -> Dict:
        """Update a delivery man."""
        delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id)
        if not delivery_man:
            raise ValueError("Delivery Man not found")
        
        password_hash = None
        if password:
            password_hash = get_password_hash(password)
        
        updated = DeliveryManRepository.update(
            db=db,
            delivery_man_id=delivery_man_id,
            name=name,
            phone=phone,
            zone_id=zone_id,
            password_hash=password_hash
        )
        
        if not updated:
            raise ValueError("Failed to update delivery man")
        
        return {
            "id": updated.id,
            "name": updated.name,
            "phone": updated.phone,
            "zone_id": updated.zone_id,
            "distributor_id": updated.distributor_id,
            "created_at": updated.created_at.isoformat() if updated.created_at else None
        }
    
    @staticmethod
    def delete_delivery_man(db: Session, delivery_man_id: int) -> bool:
        """Soft delete a delivery man."""
        delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id)
        if not delivery_man:
            raise ValueError("Delivery Man not found")
        
        success = DeliveryManRepository.delete(db, delivery_man_id)
        if success:
            # Log the soft delete operation
            from services.activity_log_service import ActivityLogService
            ActivityLogService.log_activity(
                db=db,
                user_id=None,  # Could be passed as parameter if needed
                user_role='distributor',
                action_type='DELETE',
                entity_type='delivery_man',
                entity_id=delivery_man_id,
                changes_summary=f"Delivery Man {delivery_man_id} soft deleted",
                status='success'
            )
        return success

