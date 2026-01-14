"""
Super Admin Repository
======================
Data access layer for Super Admin database operations.
"""
from sqlalchemy.orm import Session
from models.super_admin import SuperAdmin
from typing import Optional, List


class SuperAdminRepository:
    """Repository for Super Admin database operations."""

    @staticmethod
    def get_by_id(db: Session, super_admin_id: int) -> Optional[SuperAdmin]:
        """Get super admin by ID."""
        return db.query(SuperAdmin).filter(SuperAdmin.id == super_admin_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[SuperAdmin]:
        """Get super admin by email."""
        return db.query(SuperAdmin).filter(SuperAdmin.email == email).first()

    @staticmethod
    def get_by_phone(db: Session, phone: str) -> Optional[SuperAdmin]:
        """Get super admin by phone."""
        return db.query(SuperAdmin).filter(SuperAdmin.phone == phone).first()

    @staticmethod
    def get_all(db: Session) -> List[SuperAdmin]:
        """Get all super admins."""
        return db.query(SuperAdmin).all()

    @staticmethod
    def create(db: Session, name: str, email: str, password_hash: str, phone: str = None) -> SuperAdmin:
        """Create a new super admin."""
        super_admin = SuperAdmin(
            name=name,
            email=email,
            phone=phone,
            password_hash=password_hash
        )
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)
        return super_admin

    @staticmethod
    def update_is_active(db: Session, super_admin_id: int, is_active: bool) -> bool:
        """Update super admin's active status."""
        super_admin = db.query(SuperAdmin).filter(SuperAdmin.id == super_admin_id).first()
        if not super_admin:
            return False
        super_admin.is_active = is_active
        db.commit()
        db.refresh(super_admin)
        return True






