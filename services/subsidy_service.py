"""
Subsidy Service
===============
Business logic for Subsidy operations.
"""
from sqlalchemy.orm import Session
from repositories.subsidy_repository import SubsidyRepository
from typing import Dict, List, Optional
from decimal import Decimal


class SubsidyService:
    """Service for Subsidy business logic."""
    
    @staticmethod
    def create_subsidy(db: Session, distributor_id: int, name: str,
                      percentage: Decimal, description: str = None) -> Dict:
        """
        Create a new subsidy.
        
        Args:
            db: Database session
            distributor_id: Distributor ID who is creating the subsidy
            name: Subsidy name (e.g., "5% Discount")
            percentage: Discount percentage (0-100)
            description: Optional description
        
        Returns:
            Dictionary with subsidy data
        """
        # Validate percentage
        if percentage < 0 or percentage > 100:
            raise ValueError("Percentage must be between 0 and 100")
        
        subsidy = SubsidyRepository.create(
            db=db,
            distributor_id=distributor_id,
            name=name,
            percentage=percentage,
            description=description
        )
        
        return SubsidyService._format_subsidy(subsidy)
    
    @staticmethod
    def get_subsidies_by_distributor(db: Session, distributor_id: int,
                                     include_inactive: bool = False) -> List[Dict]:
        """
        Get all subsidies for a distributor.
        
        Args:
            db: Database session
            distributor_id: Distributor ID
            include_inactive: If True, includes inactive subsidies
        
        Returns:
            List of subsidy dictionaries
        """
        subsidies = SubsidyRepository.get_by_distributor(
            db=db,
            distributor_id=distributor_id,
            include_inactive=include_inactive,
            include_deleted=False
        )
        
        return [SubsidyService._format_subsidy(subsidy) for subsidy in subsidies]
    
    @staticmethod
    def get_active_subsidies_by_distributor(db: Session, distributor_id: int) -> List[Dict]:
        """
        Get all active subsidies for a distributor.
        
        Args:
            db: Database session
            distributor_id: Distributor ID
        
        Returns:
            List of active subsidy dictionaries
        """
        subsidies = SubsidyRepository.get_active_by_distributor(db, distributor_id)
        return [SubsidyService._format_subsidy(subsidy) for subsidy in subsidies]
    
    @staticmethod
    def get_subsidy_by_id(db: Session, subsidy_id: int) -> Optional[Dict]:
        """
        Get subsidy by ID.
        
        Args:
            db: Database session
            subsidy_id: Subsidy ID
        
        Returns:
            Subsidy dictionary or None if not found
        """
        subsidy = SubsidyRepository.get_by_id(db, subsidy_id, include_deleted=False)
        if not subsidy:
            return None
        
        return SubsidyService._format_subsidy(subsidy)
    
    @staticmethod
    def update_subsidy(db: Session, subsidy_id: int, name: str = None,
                      description: str = None, percentage: Decimal = None,
                      is_active: bool = None) -> Optional[Dict]:
        """
        Update subsidy.
        
        Args:
            db: Database session
            subsidy_id: Subsidy ID to update
            name: New name (optional)
            description: New description (optional)
            percentage: New percentage (optional, must be 0-100)
            is_active: New active status (optional)
        
        Returns:
            Updated subsidy dictionary or None if not found
        """
        # Validate percentage if provided
        if percentage is not None and (percentage < 0 or percentage > 100):
            raise ValueError("Percentage must be between 0 and 100")
        
        subsidy = SubsidyRepository.update(
            db=db,
            subsidy_id=subsidy_id,
            name=name,
            description=description,
            percentage=percentage,
            is_active=is_active
        )
        
        if not subsidy:
            return None
        
        return SubsidyService._format_subsidy(subsidy)
    
    @staticmethod
    def delete_subsidy(db: Session, subsidy_id: int) -> bool:
        """
        Soft delete subsidy.
        
        Args:
            db: Database session
            subsidy_id: Subsidy ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        subsidy = SubsidyRepository.soft_delete(db, subsidy_id)
        return subsidy is not None
    
    @staticmethod
    def _format_subsidy(subsidy) -> Dict:
        """Format subsidy object to dictionary."""
        return {
            "id": subsidy.id,
            "distributor_id": subsidy.distributor_id,
            "name": subsidy.name,
            "description": subsidy.description,
            "percentage": float(subsidy.percentage) if subsidy.percentage else 0.0,
            "is_active": subsidy.is_active,
            "created_at": subsidy.created_at.isoformat() if subsidy.created_at else None,
            "updated_at": subsidy.updated_at.isoformat() if subsidy.updated_at else None,
            "deleted_at": subsidy.deleted_at.isoformat() if subsidy.deleted_at else None
        }

