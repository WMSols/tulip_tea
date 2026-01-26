"""
Subsidy Repository
==================
Data access layer for Subsidy operations.
"""
from sqlalchemy.orm import Session
from models.subsidy import Subsidy
from typing import Optional, List
from decimal import Decimal


class SubsidyRepository:
    """Repository for Subsidy database operations."""
    
    @staticmethod
    def create(db: Session, distributor_id: int, name: str, percentage: Decimal,
               description: str = None) -> Subsidy:
        """
        Create a new subsidy.
        
        Args:
            db: Database session
            distributor_id: Distributor ID who is creating the subsidy
            name: Subsidy name (e.g., "5% Discount")
            percentage: Discount percentage (0-100)
            description: Optional description
        
        Returns:
            Created subsidy instance
        """
        subsidy = Subsidy(
            distributor_id=distributor_id,
            name=name,
            description=description,
            percentage=percentage,
            is_active=True
        )
        db.add(subsidy)
        db.commit()
        db.refresh(subsidy)
        return subsidy
    
    @staticmethod
    def get_by_id(db: Session, subsidy_id: int, include_deleted: bool = False) -> Optional[Subsidy]:
        """Get subsidy by ID."""
        query = db.query(Subsidy).filter(Subsidy.id == subsidy_id)
        if not include_deleted:
            query = query.filter(Subsidy.deleted_at.is_(None))
        return query.first()
    
    @staticmethod
    def get_by_distributor(db: Session, distributor_id: int,
                          include_inactive: bool = False,
                          include_deleted: bool = False) -> List[Subsidy]:
        """
        Get all subsidies for a distributor.
        
        Args:
            db: Database session
            distributor_id: Distributor ID
            include_inactive: If True, includes inactive subsidies
            include_deleted: If True, includes soft-deleted subsidies
        
        Returns:
            List of subsidies
        """
        query = db.query(Subsidy).filter(Subsidy.distributor_id == distributor_id)
        
        if not include_inactive:
            query = query.filter(Subsidy.is_active == True)
        
        if not include_deleted:
            query = query.filter(Subsidy.deleted_at.is_(None))
        
        return query.order_by(Subsidy.created_at.desc()).all()
    
    @staticmethod
    def get_active_by_distributor(db: Session, distributor_id: int) -> List[Subsidy]:
        """
        Get all active subsidies for a distributor.
        
        Args:
            db: Database session
            distributor_id: Distributor ID
        
        Returns:
            List of active subsidies
        """
        return db.query(Subsidy).filter(
            Subsidy.distributor_id == distributor_id,
            Subsidy.is_active == True,
            Subsidy.deleted_at.is_(None)
        ).order_by(Subsidy.created_at.desc()).all()
    
    @staticmethod
    def update(db: Session, subsidy_id: int, name: str = None,
              description: str = None, percentage: Decimal = None,
              is_active: bool = None) -> Optional[Subsidy]:
        """
        Update subsidy.
        
        Args:
            db: Database session
            subsidy_id: Subsidy ID to update
            name: New name (optional)
            description: New description (optional)
            percentage: New percentage (optional)
            is_active: New active status (optional)
        
        Returns:
            Updated subsidy instance or None if not found
        """
        subsidy = db.query(Subsidy).filter(Subsidy.id == subsidy_id).first()
        if not subsidy:
            return None
        
        if name is not None:
            subsidy.name = name
        if description is not None:
            subsidy.description = description
        if percentage is not None:
            subsidy.percentage = percentage
        if is_active is not None:
            subsidy.is_active = is_active
        
        db.commit()
        db.refresh(subsidy)
        return subsidy
    
    @staticmethod
    def soft_delete(db: Session, subsidy_id: int) -> Optional[Subsidy]:
        """
        Soft delete subsidy.
        
        Args:
            db: Database session
            subsidy_id: Subsidy ID to delete
        
        Returns:
            Deleted subsidy instance or None if not found
        """
        from datetime import datetime
        subsidy = db.query(Subsidy).filter(Subsidy.id == subsidy_id).first()
        if not subsidy:
            return None
        
        subsidy.deleted_at = datetime.utcnow()
        db.commit()
        db.refresh(subsidy)
        return subsidy

