"""
Distributor Repository
======================
Data access layer for Distributor database operations.

This repository handles all direct database interactions for the Distributor model.
It uses SQLAlchemy ORM to perform CRUD operations on the 'distributors' table.

ARCHITECTURE:
Router → Service → Repository → Database

This layer:
- Receives database session from Service layer
- Performs SQL queries via SQLAlchemy ORM
- Returns model instances or None
- No business logic (validation, hashing, etc.) - that's in Service layer
"""
from sqlalchemy.orm import Session
from models.distributor import Distributor
from typing import Optional, List


class DistributorRepository:
    """
    Repository for Distributor database operations.
    
    This class contains static methods for all database operations on distributors table.
    Each method:
    1. Takes a database session and parameters
    2. Performs SQL query via SQLAlchemy
    3. Returns Distributor model instance(s) or None
    """
    
    @staticmethod
    def create(db: Session, name: str, email: str, phone: str, 
              password_hash: str) -> Distributor:
        """
        Create a new distributor record in the database.
        
        FLOW:
        1. Creates Distributor model instance with provided data
        2. Adds to database session (staged for commit)
        3. Commits transaction (saves to database)
        4. Refreshes instance to get auto-generated ID and timestamps
        5. Returns the created distributor
        
        Args:
            db: SQLAlchemy database session
            name: Distributor name
            email: Distributor email (unique)
            phone: Distributor phone number (unique)
            password_hash: Hashed password (from AuthService.get_password_hash())
        
        Returns:
            Distributor: Created distributor model instance with ID and timestamps
        
        Note:
            - Password should already be hashed (Service layer responsibility)
            - Email and phone uniqueness should be checked before calling this
            - Distributors are NOT assigned to zones - they create zones but are not assigned to them
            - Zones are assigned to Order Bookers and Delivery Men
        """
        # Create model instance (maps to distributors table)
        # Note: Distributors do not have zone_id - they create zones but are not assigned to them
        distributor = Distributor(
            name=name,
            email=email,
            phone=phone,
            password_hash=password_hash
        )
        # Add to session (staged, not yet saved)
        db.add(distributor)
        # Commit transaction (saves to database)
        db.commit()
        # Refresh to get auto-generated fields (id, created_at, updated_at)
        db.refresh(distributor)
        return distributor
    
    @staticmethod
    def get_by_id(db: Session, distributor_id: int, include_deleted: bool = False) -> Optional[Distributor]:
        """
        Get a distributor by their ID (excludes soft-deleted and inactive by default).
        
        FLOW:
        1. Queries distributors table
        2. Filters by id = distributor_id
        3. Optionally filters by deleted_at IS NULL and is_active = TRUE
        4. Returns first match or None
        
        Args:
            db: SQLAlchemy database session
            distributor_id: Distributor ID (primary key)
            include_deleted: If True, includes soft-deleted and inactive records
        
        Returns:
            Optional[Distributor]: Distributor instance if found, None otherwise
        """
        query = db.query(Distributor).filter(Distributor.id == distributor_id)
        if not include_deleted:
            query = query.filter(Distributor.deleted_at.is_(None), Distributor.is_active == True)
        return query.first()
    
    @staticmethod
    def get_by_phone(db: Session, phone: str, include_deleted: bool = False) -> Optional[Distributor]:
        """
        Get a distributor by their phone number (excludes soft-deleted and inactive by default).
        
        FLOW:
        1. Queries distributors table
        2. Filters by phone = phone
        3. Optionally filters by deleted_at IS NULL and is_active = TRUE
        4. Returns first match or None
        
        Args:
            db: SQLAlchemy database session
            phone: Phone number (unique, indexed)
            include_deleted: If True, includes soft-deleted and inactive records
        
        Returns:
            Optional[Distributor]: Distributor instance if found, None otherwise
        
        Usage:
            Used during login to find user by phone number
        """
        query = db.query(Distributor).filter(Distributor.phone == phone)
        if not include_deleted:
            query = query.filter(Distributor.deleted_at.is_(None), Distributor.is_active == True)
        return query.first()
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[Distributor]:
        """
        Get a distributor by their email address.
        
        FLOW:
        1. Queries distributors table
        2. Filters by email = email
        3. Returns first match or None
        
        Args:
            db: SQLAlchemy database session
            email: Email address (unique, indexed)
        
        Returns:
            Optional[Distributor]: Distributor instance if found, None otherwise
        
        Usage:
            Used to check if email already exists during registration
        """
        # SQL: SELECT * FROM distributors WHERE email = email LIMIT 1
        return db.query(Distributor).filter(Distributor.email == email).first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Distributor]:
        """
        Get all distributors with pagination.
        
        FLOW:
        1. Queries distributors table
        2. Applies offset (skip) and limit for pagination
        3. Returns list of distributor instances
        
        Args:
            db: SQLAlchemy database session
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[Distributor]: List of distributor instances
        
        Usage:
            Used to list all distributors (e.g., admin dashboard)
        """
        # SQL: SELECT * FROM distributors OFFSET skip LIMIT limit
        return db.query(Distributor).offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, distributor_id: int, name: str = None, email: str = None,
               phone: str = None, password_hash: str = None) -> Optional[Distributor]:
        """
        Update distributor information.
        
        FLOW:
        1. Gets distributor by ID
        2. Updates provided fields
        3. Commits changes
        4. Returns updated distributor
        
        Args:
            db: SQLAlchemy database session
            distributor_id: Distributor ID to update
            name: New name (optional)
            email: New email (optional)
            phone: New phone (optional)
            password_hash: New password hash (optional, should be hashed before calling)
        
        Returns:
            Optional[Distributor]: Updated distributor instance or None if not found
        """
        distributor = DistributorRepository.get_by_id(db, distributor_id, include_deleted=True)
        if not distributor:
            return None
        
        if name is not None:
            distributor.name = name
        if email is not None:
            distributor.email = email
        if phone is not None:
            distributor.phone = phone
        if password_hash is not None:
            distributor.password_hash = password_hash
        
        db.commit()
        db.refresh(distributor)
        return distributor

