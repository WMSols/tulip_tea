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
        
        # Create warehouse for distributor (one warehouse per distributor)
        try:
            from repositories.warehouse_repository import WarehouseRepository
            # Check if warehouse already exists for this distributor
            existing_warehouse = WarehouseRepository.get_by_distributor(db, distributor.id)
            if existing_warehouse:
                print(f"Warehouse {existing_warehouse.id} already exists for distributor {distributor.id}")
            else:
                warehouse = WarehouseRepository.create(
                    db=db,
                    name=f"{distributor.name}'s Warehouse",
                    distributor_id=distributor.id,
                    zone_id=None,  # Optional, can be set later
                    address=None  # Can be set later
                )
                print(f"Created warehouse {warehouse.id} for distributor {distributor.id}")
        except Exception as e:
            # If warehouse creation fails, rollback and re-raise with helpful message
            db.rollback()
            error_msg = str(e)
            if "distributor_id" in error_msg and "does not exist" in error_msg:
                raise ValueError(
                    "Database schema error: 'distributor_id' column missing from warehouses table. "
                    "Please run the migration script: python scripts/migrate_warehouse_distributor_id.py"
                )
            else:
                raise ValueError(f"Failed to create warehouse: {error_msg}")
        
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
    
    @staticmethod
    def update_distributor(db: Session, distributor_id: int, name: str = None, 
                          email: str = None, phone: str = None, password: str = None) -> Dict:
        """
        Update distributor information.
        
        FLOW:
        1. Validates distributor exists
        2. Validates phone/email uniqueness if being changed
        3. Hashes password if being changed
        4. Updates distributor fields
        5. Returns updated distributor data
        
        Args:
            db: Database session
            distributor_id: Distributor ID to update
            name: New name (optional)
            email: New email (optional)
            phone: New phone (optional)
            password: New password (optional, will be hashed)
        
        Returns:
            Dictionary with updated distributor data
        
        Raises:
            ValueError: If distributor not found or validation fails
        """
        # Verify distributor exists
        distributor = DistributorRepository.get_by_id(db, distributor_id, include_deleted=True)
        if not distributor:
            raise ValueError("Distributor not found")
        
        # Validate phone uniqueness if phone is being changed
        if phone and phone != distributor.phone:
            existing = DistributorRepository.get_by_phone(db, phone)
            if existing and existing.id != distributor_id:
                raise ValueError("Phone number already registered")
        
        # Validate email uniqueness if email is being changed
        if email is not None and email != distributor.email:
            if email:  # Only check if email is not None and not empty
                existing_email = DistributorRepository.get_by_email(db, email)
                if existing_email and existing_email.id != distributor_id:
                    raise ValueError("Email already registered")
        
        # Hash password if provided
        password_hash = None
        if password:
            password_hash = get_password_hash(password)
        
        # Update distributor
        updated_distributor = DistributorRepository.update(
            db=db,
            distributor_id=distributor_id,
            name=name,
            email=email,
            phone=phone,
            password_hash=password_hash
        )
        
        if not updated_distributor:
            raise ValueError("Failed to update distributor")
        
        return {
            "id": updated_distributor.id,
            "name": updated_distributor.name,
            "email": updated_distributor.email,
            "phone": updated_distributor.phone,
            "created_at": updated_distributor.created_at.isoformat() if updated_distributor.created_at else None
        }

