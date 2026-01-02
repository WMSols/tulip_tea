"""
Distributor business logic service.
"""
from sqlalchemy.orm import Session
from repositories.distributor_repository import DistributorRepository
from services.auth_service import get_password_hash, verify_password, create_access_token
from typing import Optional, Dict


class DistributorService:
    """Service for Distributor business logic."""
    
    @staticmethod
    def create_distributor(db: Session, name: str, email: str, phone: str,
                          password: str, zone_id: int = None) -> Dict:
        """
        Create a new distributor.
        
        Returns:
            Dictionary with distributor data and success status
        """
        # Check if phone already exists
        existing = DistributorRepository.get_by_phone(db, phone)
        if existing:
            raise ValueError("Phone number already registered")
        
        # Check if email already exists (if provided)
        if email:
            existing_email = DistributorRepository.get_by_email(db, email)
            if existing_email:
                raise ValueError("Email already registered")
        
        # Hash password
        password_hash = get_password_hash(password)
        
        # Create distributor
        distributor = DistributorRepository.create(
            db=db,
            name=name,
            email=email,
            phone=phone,
            password_hash=password_hash,
            zone_id=zone_id
        )
        
        return {
            "id": distributor.id,
            "name": distributor.name,
            "email": distributor.email,
            "phone": distributor.phone,
            "zone_id": distributor.zone_id,
            "created_at": distributor.created_at.isoformat() if distributor.created_at else None
        }
    
    @staticmethod
    def login_distributor(db: Session, phone: str, password: str) -> Optional[Dict]:
        """
        Authenticate distributor and return JWT token.
        
        Returns:
            Dictionary with access_token and user info, or None if invalid
        """
        # Get distributor by phone
        distributor = DistributorRepository.get_by_phone(db, phone)
        if not distributor:
            return None
        
        # Verify password
        if not verify_password(password, distributor.password_hash):
            return None
        
        # Create JWT token
        token_data = {
            "sub": str(distributor.id),
            "role": "distributor",
            "phone": distributor.phone
        }
        access_token = create_access_token(data=token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": distributor.id,
                "name": distributor.name,
                "email": distributor.email,
                "phone": distributor.phone,
                "zone_id": distributor.zone_id,
                "role": "distributor"
            }
        }

