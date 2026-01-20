"""
Product Router
=============
Handles product management operations.

API ENDPOINTS:
- POST /products/ - Create new product
- GET /products/ - List all products (active only by default)
- GET /products/{id} - Get product by ID
- PUT /products/{id} - Update product
- DELETE /products/{id} - Soft delete product
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import ProductCreate, ProductResponse, ProductUpdate
from services.product_service import ProductService
from services.activity_log_service import ActivityLogService
from utils.auth_helpers import get_current_user_from_request

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new product."""
    try:
        result = ProductService.create_product(
            db=db,
            code=product.code,
            name=product.name,
            unit=product.unit
        )
        
        # Log activity (with error handling - don't fail if logging fails)
        try:
            current_user = get_current_user_from_request(request)
            ActivityLogService.log_activity(
                db=db,
                user_id=current_user['id'],
                user_role=current_user['role'],
                action_type='CREATE',
                entity_type='product',
                entity_id=result['id'],
                new_values={'code': result['code'], 'name': result['name']},
                changes_summary=f"Product '{result['name']}' (Code: {result['code']}) created",
                request=request
            )
        except Exception as log_error:
            # Log error but don't fail the request
            print(f"Warning: Failed to log product creation: {log_error}")
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        error_detail = str(e)
        if hasattr(e, '__traceback__'):
            error_detail += f"\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating product: {error_detail}"
        )


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    include_inactive: bool = Query(False, description="Include inactive products"),
    db: Session = Depends(get_db)
):
    """List all products."""
    try:
        products = ProductService.get_all_products(db, include_inactive=include_inactive)
        return products
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching products: {str(e)}"
        )


@router.get("/active", response_model=List[ProductResponse])
async def list_active_products(db: Session = Depends(get_db)):
    """List all active products (for order bookers)."""
    try:
        products = ProductService.get_active_products(db)
        return products
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching active products: {str(e)}"
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product by ID."""
    try:
        product = ProductService.get_product_by_id(db, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        return product
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching product: {str(e)}"
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update product."""
    try:
        # Get product before update for logging
        old_product = ProductService.get_product_by_id(db, product_id, include_deleted=True)
        if not old_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        old_values = {
            'code': old_product['code'],
            'name': old_product['name'],
            'unit': old_product['unit'],
            'price': old_product.get('price'),
            'is_active': old_product['is_active']
        }
        
        result = ProductService.update_product(
            db=db,
            product_id=product_id,
            code=product.code,
            name=product.name,
            unit=product.unit,
            price=product.price,
            is_active=product.is_active
        )
        
        # Log activity (with error handling - don't fail if logging fails)
        try:
            current_user = get_current_user_from_request(request)
            # Get updated fields from product (handle both Pydantic v1 and v2)
            try:
                if hasattr(product, 'model_dump'):
                    # Pydantic v2
                    product_dict = product.model_dump(exclude_unset=True)
                else:
                    # Pydantic v1
                    product_dict = product.dict(exclude_unset=True)
            except Exception:
                product_dict = {}
            
            new_values = {k: v for k, v in {
                'code': result['code'],
                'name': result['name'],
                'unit': result['unit'],
                'is_active': result['is_active']
            }.items() if product_dict.get(k.replace('_', '')) is not None}
            
            changes = []
            if product.code and product.code != old_values['code']:
                changes.append(f"code: '{old_values['code']}' → '{result['code']}'")
            if product.name and product.name != old_values['name']:
                changes.append(f"name: '{old_values['name']}' → '{result['name']}'")
            if product.unit is not None and product.unit != old_values['unit']:
                changes.append(f"unit: '{old_values['unit']}' → '{result['unit']}'")
            if product.is_active is not None and product.is_active != old_values['is_active']:
                changes.append(f"is_active: {old_values['is_active']} → {result['is_active']}")
            
            ActivityLogService.log_update(
                db=db,
                user_id=current_user['id'],
                user_role=current_user['role'],
                entity_type='product',
                entity_id=product_id,
                old_values=old_values,
                new_values=new_values,
                changes_summary=f"Product '{result['name']}' updated: {', '.join(changes) if changes else 'No changes'}"
            )
        except Exception as log_error:
            # Log error but don't fail the request
            print(f"Warning: Failed to log product update: {log_error}")
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        if hasattr(e, '__traceback__'):
            error_detail += f"\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating product: {error_detail}"
        )


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Soft delete product."""
    try:
        # Get product before delete for logging (include deleted to get soft-deleted products)
        product = ProductService.get_product_by_id(db, product_id, include_deleted=True)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        result = ProductService.delete_product(db, product_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Log activity (with error handling - don't fail if logging fails)
        try:
            current_user = get_current_user_from_request(request)
            ActivityLogService.log_delete(
                db=db,
                user_id=current_user['id'],
                user_role=current_user['role'],
                entity_type='product',
                entity_id=product_id,
                old_values={'code': product['code'], 'name': product['name']},
                changes_summary=f"Product '{product['name']}' (Code: {product['code']}) deleted"
            )
        except Exception as log_error:
            # Log error but don't fail the request
            print(f"Warning: Failed to log product deletion: {log_error}")
        
        return {"message": "Product deleted successfully", "product_id": product_id}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        if hasattr(e, '__traceback__'):
            error_detail += f"\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting product: {error_detail}"
        )


