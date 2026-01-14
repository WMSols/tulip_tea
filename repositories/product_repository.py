"""
Product repository.
Data access layer for Product operations.
"""
from sqlalchemy.orm import Session
from models.product import Product
from typing import Optional, List


class ProductRepository:
    """Repository for Product database operations."""
    
    @staticmethod
    def create(db: Session, code: str, name: str, unit: str = None) -> Product:
        """Create a new product."""
        product = Product(
            code=code,
            name=name,
            unit=unit,
            is_active=True
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    
    @staticmethod
    def get_by_id(db: Session, product_id: int, include_deleted: bool = True) -> Optional[Product]:
        """Get product by ID.
        
        Args:
            db: Database session
            product_id: Product ID to fetch
            include_deleted: If True, includes soft-deleted products (default: True for updates)
        
        Returns:
            Product instance or None if not found
        """
        query = db.query(Product).filter(Product.id == product_id)
        if not include_deleted:
            query = query.filter(Product.deleted_at.is_(None))
        return query.first()
    
    @staticmethod
    def get_by_code(db: Session, code: str, include_deleted: bool = False) -> Optional[Product]:
        """Get product by code."""
        query = db.query(Product).filter(Product.code == code)
        if not include_deleted:
            query = query.filter(Product.deleted_at.is_(None))
        return query.first()
    
    @staticmethod
    def get_all(db: Session, include_inactive: bool = False, include_deleted: bool = False) -> List[Product]:
        """Get all products."""
        query = db.query(Product)
        if not include_deleted:
            query = query.filter(Product.deleted_at.is_(None))
        if not include_inactive:
            query = query.filter(Product.is_active == True)
        return query.order_by(Product.name).all()
    
    @staticmethod
    def get_active(db: Session) -> List[Product]:
        """Get all active products (not deleted, is_active=True)."""
        return db.query(Product).filter(
            Product.deleted_at.is_(None),
            Product.is_active == True
        ).order_by(Product.name).all()
    
    @staticmethod
    def update(db: Session, product_id: int, code: str = None, name: str = None, 
               unit: str = None, is_active: bool = None) -> Optional[Product]:
        """Update product."""
        # Include deleted products so we can update/reactivate them
        product = ProductRepository.get_by_id(db, product_id, include_deleted=True)
        if not product:
            return None
        
        if code is not None:
            product.code = code
        if name is not None:
            product.name = name
        if unit is not None:
            product.unit = unit
        if is_active is not None:
            product.is_active = is_active
        
        db.commit()
        db.refresh(product)
        return product
    
    @staticmethod
    def delete(db: Session, product_id: int) -> bool:
        """Soft delete product."""
        product = ProductRepository.get_by_id(db, product_id)
        if not product:
            return False
        
        from datetime import datetime
        product.deleted_at = datetime.now()
        db.commit()
        return True


