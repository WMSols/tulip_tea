"""
Product business logic service.
"""
from sqlalchemy.orm import Session
from repositories.product_repository import ProductRepository
from typing import Dict, List, Optional


class ProductService:
    """Service for Product business logic."""
    
    @staticmethod
    def create_product(db: Session, code: str, name: str, unit: str = None, distributor_id: int = None) -> Dict:
        """Create a new product."""
        if distributor_id is None:
            raise ValueError("distributor_id is required to create a product")
        
        # Check if code already exists for this distributor
        existing = ProductRepository.get_by_code(db, code, include_deleted=True)
        if existing:
            # Check if it belongs to the same distributor
            if existing.distributor_id == distributor_id:
                # Same distributor - product code already exists
                if existing.deleted_at is None:
                    raise ValueError(
                        f"A product with code '{code}' already exists. "
                        f"Please use a different product code. "
                        f"Existing product: '{existing.name}' (ID: {existing.id})"
                    )
                else:
                    raise ValueError(
                        f"A product with code '{code}' was previously deleted. "
                        f"Please use a different product code or restore the existing product. "
                        f"Previously deleted product: '{existing.name}' (ID: {existing.id})"
                    )
            else:
                # Different distributor - code conflict
                raise ValueError(
                    f"Product code '{code}' is already in use by another distributor. "
                    f"Please choose a different product code."
                )
        
        product = ProductRepository.create(db, code, name, unit, distributor_id)
        
        # Safely format datetime fields
        created_at_str = None
        if product.created_at:
            try:
                if hasattr(product.created_at, 'isoformat'):
                    created_at_str = product.created_at.isoformat()
                else:
                    created_at_str = str(product.created_at)
            except Exception:
                created_at_str = str(product.created_at) if product.created_at else None
        
        updated_at_str = None
        if product.updated_at:
            try:
                if hasattr(product.updated_at, 'isoformat'):
                    updated_at_str = product.updated_at.isoformat()
                else:
                    updated_at_str = str(product.updated_at)
            except Exception:
                updated_at_str = str(product.updated_at) if product.updated_at else None
        
        return {
            "id": product.id,
            "code": product.code,
            "name": product.name,
            "unit": product.unit,
            "distributor_id": product.distributor_id,
            "is_active": product.is_active,
            "created_at": created_at_str,
            "updated_at": updated_at_str
        }
    
    @staticmethod
    def get_all_products(db: Session, distributor_id: int = None, include_inactive: bool = False) -> List[Dict]:
        """
        Get all products. Filter by distributor_id if provided.
        """
        if distributor_id is None:
            raise ValueError("distributor_id is required to get products")
        
        products = ProductRepository.get_all(db, include_inactive=include_inactive, distributor_id=distributor_id)
        result = []
        for p in products:
            # Safely format datetime fields
            created_at_str = None
            if p.created_at:
                try:
                    if hasattr(p.created_at, 'isoformat'):
                        created_at_str = p.created_at.isoformat()
                    else:
                        created_at_str = str(p.created_at)
                except Exception:
                    created_at_str = str(p.created_at) if p.created_at else None
            
            updated_at_str = None
            if p.updated_at:
                try:
                    if hasattr(p.updated_at, 'isoformat'):
                        updated_at_str = p.updated_at.isoformat()
                    else:
                        updated_at_str = str(p.updated_at)
                except Exception:
                    updated_at_str = str(p.updated_at) if p.updated_at else None
            
            # Format price - convert Decimal to float for JSON serialization
            price_value = None
            if p.price is not None:
                try:
                    price_value = float(p.price)
                except (ValueError, TypeError):
                    price_value = None
            
            result.append({
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "unit": p.unit,
                "price": price_value,
                "is_active": p.is_active,
                "created_at": created_at_str,
                "updated_at": updated_at_str
            })
        return result
    
    @staticmethod
    def get_active_products(db: Session, distributor_id: int = None) -> List[Dict]:
        """Get all active products. Filter by distributor_id if provided."""
        if distributor_id is None:
            raise ValueError("distributor_id is required to get products")
        
        products = ProductRepository.get_active(db, distributor_id=distributor_id)
        result = []
        for p in products:
            # Safely format datetime fields
            created_at_str = None
            if p.created_at:
                try:
                    if hasattr(p.created_at, 'isoformat'):
                        created_at_str = p.created_at.isoformat()
                    else:
                        created_at_str = str(p.created_at)
                except Exception:
                    created_at_str = str(p.created_at) if p.created_at else None
            
            updated_at_str = None
            if p.updated_at:
                try:
                    if hasattr(p.updated_at, 'isoformat'):
                        updated_at_str = p.updated_at.isoformat()
                    else:
                        updated_at_str = str(p.updated_at)
                except Exception:
                    updated_at_str = str(p.updated_at) if p.updated_at else None
            
            # Format price - convert Decimal to float for JSON serialization
            price_value = None
            if p.price is not None:
                try:
                    price_value = float(p.price)
                except (ValueError, TypeError):
                    price_value = None
            
            result.append({
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "unit": p.unit,
                "price": price_value,
                "distributor_id": p.distributor_id,
                "is_active": p.is_active,
                "created_at": created_at_str,
                "updated_at": updated_at_str
            })
        return result
    
    @staticmethod
    def get_product_by_id(db: Session, product_id: int, include_deleted: bool = True) -> Optional[Dict]:
        """Get product by ID.
        
        Args:
            db: Database session
            product_id: Product ID to fetch
            include_deleted: If True, includes soft-deleted products (default: True for admin operations)
        
        Returns:
            Product dictionary or None if not found
        """
        product = ProductRepository.get_by_id(db, product_id, include_deleted=include_deleted)
        if not product:
            return None
        
        # Safely format datetime fields
        created_at_str = None
        if product.created_at:
            try:
                if hasattr(product.created_at, 'isoformat'):
                    created_at_str = product.created_at.isoformat()
                else:
                    created_at_str = str(product.created_at)
            except Exception:
                created_at_str = str(product.created_at) if product.created_at else None
        
        updated_at_str = None
        if product.updated_at:
            try:
                if hasattr(product.updated_at, 'isoformat'):
                    updated_at_str = product.updated_at.isoformat()
                else:
                    updated_at_str = str(product.updated_at)
            except Exception:
                updated_at_str = str(product.updated_at) if product.updated_at else None
        
        # Format price - convert Decimal to float for JSON serialization
        price_value = None
        if product.price is not None:
            try:
                price_value = float(product.price)
            except (ValueError, TypeError):
                price_value = None
        
        return {
            "id": product.id,
            "code": product.code,
            "name": product.name,
            "unit": product.unit,
            "price": price_value,
            "distributor_id": product.distributor_id,
            "is_active": product.is_active,
            "created_at": created_at_str,
            "updated_at": updated_at_str
        }
    
    @staticmethod
    def update_product(db: Session, product_id: int, code: str = None, name: str = None,
                      unit: str = None, price: float = None, is_active: bool = None) -> Dict:
        """Update product."""
        # If code is being updated, check if it already exists
        if code:
            existing = ProductRepository.get_by_code(db, code, include_deleted=True)
            if existing and existing.id != product_id:
                raise ValueError(f"Product with code '{code}' already exists")
        
        product = ProductRepository.update(db, product_id, code, name, unit, price, is_active)
        if not product:
            raise ValueError("Product not found")
        
        # Safely format datetime fields
        created_at_str = None
        if product.created_at:
            try:
                if hasattr(product.created_at, 'isoformat'):
                    created_at_str = product.created_at.isoformat()
                else:
                    created_at_str = str(product.created_at)
            except Exception:
                created_at_str = str(product.created_at) if product.created_at else None
        
        updated_at_str = None
        if product.updated_at:
            try:
                if hasattr(product.updated_at, 'isoformat'):
                    updated_at_str = product.updated_at.isoformat()
                else:
                    updated_at_str = str(product.updated_at)
            except Exception:
                updated_at_str = str(product.updated_at) if product.updated_at else None
        
        # Format price - convert Decimal to float for JSON serialization
        price_value = None
        if product.price is not None:
            try:
                price_value = float(product.price)
            except (ValueError, TypeError):
                price_value = None
        
        return {
            "id": product.id,
            "code": product.code,
            "name": product.name,
            "unit": product.unit,
            "price": price_value,
            "distributor_id": product.distributor_id,
            "is_active": product.is_active,
            "created_at": created_at_str,
            "updated_at": updated_at_str
        }
    
    @staticmethod
    def delete_product(db: Session, product_id: int) -> bool:
        """Soft delete product."""
        return ProductRepository.delete(db, product_id)


