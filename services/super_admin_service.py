"""
Super Admin Service
===================
Business logic service for Super Admin operations.
"""
from sqlalchemy.orm import Session
from repositories.super_admin_repository import SuperAdminRepository
from services.auth_service import verify_password, create_access_token
from typing import Optional, Dict


class SuperAdminService:
    """Service for Super Admin business logic."""

    @staticmethod
    def login_super_admin(db: Session, email: str, password: str) -> Optional[Dict]:
        """
        Authenticate super admin and return JWT token.
        
        Returns:
            Dictionary with access_token and user info, or None if invalid
        """
        # Get super admin by email
        super_admin = SuperAdminRepository.get_by_email(db, email)
        if not super_admin:
            return None
        
        # Check if super admin is active
        if not super_admin.is_active:
            return None
        
        # Verify password
        if not verify_password(password, super_admin.password_hash):
            return None
        
        # Create JWT token
        token_data = {
            "sub": str(super_admin.id),
            "role": "super_admin",
            "email": super_admin.email,
            "name": super_admin.name
        }
        access_token = create_access_token(data=token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": super_admin.id,
                "name": super_admin.name,
                "email": super_admin.email,
                "phone": super_admin.phone,
                "role": "super_admin"
            }
        }

