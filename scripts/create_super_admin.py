"""
Create Super Admin Script
=========================
Script to create a super admin user in the database.

USAGE:
    python scripts/create_super_admin.py

This script will prompt for:
    - Name
    - Email (used for login)
    - Password (will be hashed)
    - Phone (optional)

After running this script, you can login to the super admin dashboard using the email and password.
"""
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from config.database import SessionLocal
from repositories.super_admin_repository import SuperAdminRepository
from services.auth_service import get_password_hash


def create_super_admin():
    """Create a new super admin user."""
    db: Session = SessionLocal()
    
    try:
        print("=" * 50)
        print("Create Super Admin User")
        print("=" * 50)
        print()
        
        # Get user input
        name = input("Enter super admin name: ").strip()
        if not name:
            print("❌ Name is required")
            return
        
        email = input("Enter email (used for login): ").strip()
        if not email:
            print("❌ Email is required")
            return
        
        # Check if email already exists
        existing = SuperAdminRepository.get_by_email(db, email)
        if existing:
            print(f"❌ Email {email} already exists")
            return
        
        password = input("Enter password: ").strip()
        if not password:
            print("❌ Password is required")
            return
        
        if len(password) < 6:
            print("⚠️  Warning: Password is less than 6 characters")
            confirm = input("Continue anyway? (y/n): ").strip().lower()
            if confirm != 'y':
                return
        
        phone = input("Enter phone (optional, press Enter to skip): ").strip()
        if not phone:
            phone = None
        else:
            # Check if phone already exists
            existing_phone = SuperAdminRepository.get_by_phone(db, phone)
            if existing_phone:
                print(f"❌ Phone {phone} already exists")
                return
        
        # Hash password
        password_hash = get_password_hash(password)
        
        # Create super admin
        super_admin = SuperAdminRepository.create(
            db=db,
            name=name,
            email=email,
            password_hash=password_hash,
            phone=phone
        )
        
        print()
        print("=" * 50)
        print("✅ Super Admin created successfully!")
        print("=" * 50)
        print(f"ID: {super_admin.id}")
        print(f"Name: {super_admin.name}")
        print(f"Email: {super_admin.email}")
        print(f"Phone: {super_admin.phone or 'N/A'}")
        print(f"Active: {super_admin.is_active}")
        print()
        print("You can now login to the super admin dashboard using:")
        print(f"  Email: {super_admin.email}")
        print(f"  Password: [the password you entered]")
        print()
        print("Dashboard URL: tests/super_admin_dashboard.html")
        
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    create_super_admin()

