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
                           password: str) -> Dict:
        """
        Create a new delivery man (only by distributor).
        
        Returns:
            Dictionary with delivery man data
        """
        # Verify distributor exists
        distributor = DistributorRepository.get_by_id(db, distributor_id)
        if not distributor:
            raise ValueError("Distributor not found")
        
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
            password_hash=password_hash
        )
        
        return {
            "id": delivery_man.id,
            "name": delivery_man.name,
            "phone": delivery_man.phone,
            "distributor_id": delivery_man.distributor_id,
            "created_at": delivery_man.created_at.isoformat() if delivery_man.created_at else None
        }
    
    @staticmethod
    def login_delivery_man(db: Session, phone: str, password: str) -> Optional[Dict]:
        """
        Authenticate delivery man and return JWT token.
        
        Returns:
            Dictionary with access_token and user info, or None if invalid
        """
        # Get delivery man by phone
        delivery_man = DeliveryManRepository.get_by_phone(db, phone)
        if not delivery_man:
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
        """Get all delivery men for a distributor."""
        delivery_men = DeliveryManRepository.get_by_distributor(db, distributor_id)
        return [
            {
                "id": dm.id,
                "name": dm.name,
                "phone": dm.phone,
                "created_at": dm.created_at.isoformat() if dm.created_at else None
            }
            for dm in delivery_men
        ]

