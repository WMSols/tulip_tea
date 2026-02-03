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
                          password: str) -> Dict:
        """
        Create a new distributor.
        
        Note: Distributors are NOT assigned to zones. They can create zones,
        but zones are assigned to Order Bookers and Delivery Men.
        
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
        
        # Create distributor (no zone_id - distributors create zones but are not assigned to them)
        distributor = DistributorRepository.create(
            db=db,
            name=name,
            email=email,
            phone=phone,
            password_hash=password_hash
        )
        
        # Create wallet for distributor
        try:
            from services.wallet_service import WalletService
            WalletService.get_or_create_wallet(db, "distributor", distributor.id)
        except Exception as e:
            # Log error but don't fail user creation
            print(f"Warning: Failed to create wallet for distributor {distributor.id}: {str(e)}")
        
        return {
            "id": distributor.id,
            "name": distributor.name,
            "email": distributor.email,
            "phone": distributor.phone,
            "created_at": distributor.created_at.isoformat() if distributor.created_at else None
        }
    
    @staticmethod
    def login_distributor(db: Session, phone: str, password: str) -> Optional[Dict]:
        """
        Authenticate distributor and return JWT token.
        
        Returns:
            Dictionary with access_token and user info, or None if invalid
        """
        # Get distributor by phone (include_deleted=False to exclude soft-deleted and inactive)
        distributor = DistributorRepository.get_by_phone(db, phone, include_deleted=False)
        if not distributor:
            return None
        
        # Check if distributor is active
        if not distributor.is_active:
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
                "role": "distributor"
            }
        }

