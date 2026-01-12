"""
Visit Type Repository
=====================
Data access layer for Visit Type operations.
"""
from sqlalchemy.orm import Session
from models.visit_type import VisitType
from typing import List, Optional


class VisitTypeRepository:
    """Repository for Visit Type database operations."""
    
    @staticmethod
    def create(db: Session, visit_id: int, visit_type: str) -> VisitType:
        """
        Create a new visit type association.
        
        Args:
            db: Database session
            visit_id: Visit ID
            visit_type: Type of visit (e.g., "order_booking", "daily_collections")
        
        Returns:
            Created visit type instance
        """
        visit_type_obj = VisitType(
            visit_id=visit_id,
            visit_type=visit_type
        )
        db.add(visit_type_obj)
        db.commit()
        db.refresh(visit_type_obj)
        return visit_type_obj
    
    @staticmethod
    def get_by_visit(db: Session, visit_id: int) -> List[VisitType]:
        """Get all visit types for a visit."""
        return db.query(VisitType).filter(VisitType.visit_id == visit_id).all()
    
    @staticmethod
    def delete_by_visit(db: Session, visit_id: int) -> int:
        """Delete all visit types for a visit."""
        count = db.query(VisitType).filter(VisitType.visit_id == visit_id).delete()
        db.commit()
        return count
    
    @staticmethod
    def has_type(db: Session, visit_id: int, visit_type: str) -> bool:
        """Check if visit has a specific type."""
        return db.query(VisitType).filter(
            VisitType.visit_id == visit_id,
            VisitType.visit_type == visit_type
        ).first() is not None








