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
            raise ValueError(f"Error retrieving order bookers: {str(e)}")
    
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
    def delete_order_booker(db: Session, order_booker_id: int) -> bool:
        """
        Delete an order booker.
        
        Checks for foreign key references before deletion:
        - Shops created by this order booker
        - Routes assigned to this order booker
        
        Raises ValueError if order booker cannot be deleted due to references.
        """
        from models.shop import Shop
        from models.route import Route
        
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        # Check for shops created by this order booker
        shops_count = db.query(Shop).filter(Shop.created_by_order_booker == order_booker_id).count()
        if shops_count > 0:
            raise ValueError(
                f"Cannot delete order booker: {shops_count} shop(s) were created by this order booker. "
                "Please reassign or delete the shops first."
            )
        
        # Check for routes assigned to this order booker
        routes_count = db.query(Route).filter(Route.order_booker_id == order_booker_id).count()
        if routes_count > 0:
            raise ValueError(
                f"Cannot delete order booker: {routes_count} route(s) are assigned to this order booker. "
                "Please reassign the routes first."
            )
        
        return OrderBookerRepository.delete(db, order_booker_id)

