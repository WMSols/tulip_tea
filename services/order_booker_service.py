"""
Order Booker business logic service.
"""
from sqlalchemy.orm import Session
from repositories.order_booker_repository import OrderBookerRepository
from repositories.distributor_repository import DistributorRepository
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
        
        return {
            "id": order_booker.id,
            "name": order_booker.name,
            "email": order_booker.email,
            "phone": order_booker.phone,
            "zone_id": order_booker.zone_id,
            "distributor_id": order_booker.distributor_id,
            "created_at": order_booker.created_at.isoformat() if order_booker.created_at else None
        }
    
    @staticmethod
    def login_order_booker(db: Session, phone: str, password: str) -> Optional[Dict]:
        """
        Authenticate order booker and return JWT token.
        
        Returns:
            Dictionary with access_token and user info, or None if invalid
        """
        # Get order booker by phone
        order_booker = OrderBookerRepository.get_by_phone(db, phone)
        if not order_booker:
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
        """Get all order bookers for a distributor."""
        try:
            order_bookers = OrderBookerRepository.get_by_distributor(db, distributor_id)
            result = []
            for ob in order_bookers:
                result.append({
                    "id": ob.id,
                    "name": ob.name,
                    "email": ob.email if ob.email else None,
                    "phone": ob.phone,
                    "zone_id": ob.zone_id,
                    "distributor_id": ob.distributor_id,
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
            result = []
            for ob in order_bookers:
                result.append({
                    "id": ob.id,
                    "name": ob.name,
                    "email": ob.email if ob.email else None,
                    "phone": ob.phone,
                    "zone_id": ob.zone_id,
                    "distributor_id": ob.distributor_id,
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
        
        return {
            "id": updated.id,
            "name": updated.name,
            "email": updated.email,
            "phone": updated.phone,
            "zone_id": updated.zone_id,
            "distributor_id": updated.distributor_id,
            "created_at": updated.created_at.isoformat() if updated.created_at else None
        }
    
    @staticmethod
    def delete_order_booker(db: Session, order_booker_id: int, 
                           reassign_shops_to: int = None, 
                           reassign_routes_to: int = None) -> bool:
        """
        Delete an order booker with optional reassignment of shops and routes.
        
        This method handles the deletion of an order booker while preserving data integrity.
        It supports reassigning shops and routes to another order booker before deletion.
        
        FLOW:
        1. Verify order booker exists
        2. Check for shops created by this order booker
           - If reassign_shops_to is provided: Reassign all shops to new order booker
           - If not provided: Raise error with count of shops
        3. Check for routes assigned to this order booker
           - If reassign_routes_to is provided: Reassign all routes to new order booker
           - If not provided: Raise error with count of routes
        4. Delete the order booker
        
        IMPORTANT NOTES:
        - When shops are reassigned, only assigned_to_order_booker is updated
        - created_by_order_booker remains unchanged for audit trail
        - Routes are fully reassigned (order_booker_id is updated)
        
        Args:
            db: Database session
            order_booker_id: ID of order booker to delete
            reassign_shops_to: Optional - New order booker ID to reassign shops to
            reassign_routes_to: Optional - New order booker ID to reassign routes to
        
        Returns:
            bool: True if successful
        
        Raises:
            ValueError: If order booker not found, or if shops/routes exist without reassignment
        """
        from models.shop import Shop
        from models.route import Route
        from repositories.shop_repository import ShopRepository
        
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        # Check for shops created by this order booker
        shops = db.query(Shop).filter(Shop.created_by_order_booker == order_booker_id).all()
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
                raise ValueError(
                    f"Cannot delete order booker: {shops_count} shop(s) were created by this order booker. "
                    "Please provide 'reassign_shops_to' parameter to reassign shops, or delete shops first."
                )
        
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
                raise ValueError(
                    f"Cannot delete order booker: {routes_count} route(s) are assigned to this order booker. "
                    "Please provide 'reassign_routes_to' parameter to reassign routes, or reassign routes first."
                )
        
        # Now safe to delete the order booker
        return OrderBookerRepository.delete(db, order_booker_id)

