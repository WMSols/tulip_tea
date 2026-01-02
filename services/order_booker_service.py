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
                           assigned_zone: str, password: str, email: str = None) -> Dict:
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
            assigned_zone=assigned_zone,
            password_hash=password_hash,
            email=email
        )
        
        return {
            "id": order_booker.id,
            "name": order_booker.name,
            "email": order_booker.email,
            "phone": order_booker.phone,
            "assigned_zone": order_booker.assigned_zone,
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
                "assigned_zone": order_booker.assigned_zone,
                "distributor_id": order_booker.distributor_id,
                "role": "order_booker"
            }
        }
    
    @staticmethod
    def get_order_bookers_by_distributor(db: Session, distributor_id: int) -> List[Dict]:
        """Get all order bookers for a distributor."""
        order_bookers = OrderBookerRepository.get_by_distributor(db, distributor_id)
        return [
            {
                "id": ob.id,
                "name": ob.name,
                "email": ob.email,
                "phone": ob.phone,
                "assigned_zone": ob.assigned_zone,
                "created_at": ob.created_at.isoformat() if ob.created_at else None
            }
            for ob in order_bookers
        ]

