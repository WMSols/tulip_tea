"""
Delivery Man router.
Handles delivery man CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict
from config.database import get_db
from models.schemas import DeliveryManCreate, DeliveryManResponse, DeliveryManUpdate
from services.delivery_man_service import DeliveryManService
from utils.dependencies import get_current_user, get_current_distributor
from services.activity_log_service import ActivityLogService
from utils.auth_helpers import get_current_user_from_request

router = APIRouter(prefix="/delivery-men", tags=["Delivery Men"])


# List routes first (more specific paths)
@router.get("/distributor/{distributor_id}", response_model=List[DeliveryManResponse], tags=["Delivery Men", "Distributor APIs"])
async def list_delivery_men_by_distributor(
    distributor_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """List all delivery men for a specific distributor. Distributors can only view their own delivery men."""
    # Verify distributor can only view their own delivery men
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view delivery men for your own distributor account"
        )
    try:
        delivery_men = DeliveryManService.get_delivery_men_by_distributor(
            db=db,
            distributor_id=distributor_id
        )
        return delivery_men
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching delivery men: {str(e)}"
        )


# Update and Delete routes (before create to avoid conflicts)
@router.put("/{delivery_man_id}", response_model=DeliveryManResponse)
async def update_delivery_man(
    delivery_man_id: int,
    update_data: DeliveryManUpdate,
    request: Request,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a delivery man. Requires authentication."""
    try:
        # Get old values before update
        from repositories.delivery_man_repository import DeliveryManRepository
        old_delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id, include_deleted=False)
        old_values = {}
        if old_delivery_man:
            old_values = {
                'name': old_delivery_man.name,
                'phone': old_delivery_man.phone,
                'zone_id': old_delivery_man.zone_id,
                'is_active': old_delivery_man.is_active
            }
        
        result = DeliveryManService.update_delivery_man(
            db=db,
            delivery_man_id=delivery_man_id,
            name=update_data.name,
            phone=update_data.phone,
            zone_id=update_data.zone_id,
            password=update_data.password
        )
        
        # Log update
        ActivityLogService.log_update(
            db=db,
            user_id=current_user.get('user_id'),
            user_role=current_user.get('user_role', 'distributor'),
            entity_type='delivery_man',
            entity_id=delivery_man_id,
            old_values=old_values,
            new_values={
                'name': result.get('name'),
                'phone': result.get('phone'),
                'zone_id': result.get('zone_id'),
                'is_active': result.get('is_active', True)
            },
            user_name=current_user.get('user_name'),
            changes_summary=f"Delivery man updated: {result.get('name')}",
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=current_user.get('user_id'),
            user_role=current_user.get('user_role', 'distributor'),
            action_type='UPDATE',
            entity_type='delivery_man',
            entity_id=delivery_man_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{delivery_man_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery_man(
    delivery_man_id: int,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Delete a delivery man. Only distributors can delete delivery men."""
    try:
        # Get old values before delete
        from repositories.delivery_man_repository import DeliveryManRepository
        old_delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id, include_deleted=False)
        old_values = {}
        if old_delivery_man:
            old_values = {
                'name': old_delivery_man.name,
                'phone': old_delivery_man.phone,
                'zone_id': old_delivery_man.zone_id,
                'is_active': old_delivery_man.is_active
            }
        
        DeliveryManService.delete_delivery_man(db=db, delivery_man_id=delivery_man_id)
        
        # Log delete
        ActivityLogService.log_delete(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='delivery_man',
            entity_id=delivery_man_id,
            old_values=old_values,
            user_name=distributor.get('user_name'),
            changes_summary=f"Delivery man deleted: {old_delivery_man.name if old_delivery_man else 'N/A'}",
            request=request
        )
        
        return None
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            action_type='DELETE',
            entity_type='delivery_man',
            entity_id=delivery_man_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# Create route last (less specific path)
@router.get("/{delivery_man_id}/routes", response_model=List[dict])
async def get_delivery_man_routes(
    delivery_man_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all routes in the delivery man's zone (zone-based assignment, not route-specific). Requires authentication."""
    try:
        from repositories.delivery_man_repository import DeliveryManRepository
        from repositories.route_repository import RouteRepository
        from repositories.zone_repository import ZoneRepository
        
        # Get delivery man to find their zone
        delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id, include_deleted=False)
        if not delivery_man or not delivery_man.zone_id:
            return []
        
        # Get all routes in the delivery man's zone
        routes = RouteRepository.get_by_zone(db, delivery_man.zone_id)
        result = []
        
        for route in routes:
            zone = ZoneRepository.get_by_id(db, route.zone_id) if route.zone_id else None
            result.append({
                "id": route.id,
                "name": route.name,
                "zone_id": route.zone_id,
                "zone_name": zone.name if zone else None,
                "order_booker_id": route.order_booker_id,
                "created_at": route.created_at.isoformat() if route.created_at else None
            })
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching routes: {str(e)}"
        )


@router.get("/{delivery_man_id}/warehouses", response_model=List[dict], tags=["Delivery Men", "Delivery Man APIs"])
async def get_delivery_man_warehouses(
    delivery_man_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all warehouses assigned to a delivery man with inventory details. Requires authentication."""
    try:
        from repositories.delivery_man_warehouse_repository import DeliveryManWarehouseRepository
        from repositories.warehouse_repository import WarehouseRepository
        from repositories.zone_repository import ZoneRepository
        from repositories.inventory_repository import InventoryRepository
        from repositories.product_repository import ProductRepository
        
        assignments = DeliveryManWarehouseRepository.get_by_delivery_man(db, delivery_man_id)
        result = []
        
        for assignment in assignments:
            warehouse = WarehouseRepository.get_by_id(db, assignment.warehouse_id)
            if warehouse:
                zone = ZoneRepository.get_by_id(db, warehouse.zone_id) if warehouse.zone_id else None
                
                # Get inventory for this warehouse
                inventory_items = InventoryRepository.get_by_warehouse(db, warehouse.id)
                inventory_list = []
                
                for inv in inventory_items:
                    product = None
                    if inv.product_id:
                        product = ProductRepository.get_by_id(db, inv.product_id)
                    
                    inventory_list.append({
                        "id": inv.id,
                        "product_id": inv.product_id,
                        "product_name": product.name if product else inv.item_name,
                        "product_code": product.code if product else inv.item_code,
                        "item_name": inv.item_name,
                        "item_code": inv.item_code,
                        "unit": inv.unit,
                        "quantity": inv.quantity,
                        "available": inv.quantity > 0
                    })
                
                result.append({
                    "id": warehouse.id,
                    "name": warehouse.name,
                    "zone_id": warehouse.zone_id,
                    "zone_name": zone.name if zone else None,
                    "address": warehouse.address,
                    "is_active": warehouse.is_active,
                    "created_at": warehouse.created_at.isoformat() if warehouse.created_at else None,
                    "inventory": inventory_list,
                    "inventory_count": len(inventory_list),
                    "total_items": sum(inv.quantity for inv in inventory_items)
                })
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching warehouses: {str(e)}"
        )


@router.post("/{distributor_id}", response_model=DeliveryManResponse, status_code=status.HTTP_201_CREATED, tags=["Delivery Men", "Distributor APIs"])
async def create_delivery_man(
    distributor_id: int,
    delivery_man: DeliveryManCreate,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Create a new delivery man.
    Only distributors can create delivery men.
    """
    # Verify distributor can only create delivery men for their own account
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create delivery men for your own distributor account"
        )
    try:
        result = DeliveryManService.create_delivery_man(
            db=db,
            distributor_id=distributor_id,
            name=delivery_man.name,
            phone=delivery_man.phone,
            password=delivery_man.password,
            zone_id=delivery_man.zone_id,
            route_ids=None  # Delivery men work by zone, not routes
        )
        
        # Log creation
        ActivityLogService.log_create(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='delivery_man',
            entity_id=result['id'],
            new_values={
                'name': result.get('name'),
                'phone': result.get('phone'),
                'zone_id': result.get('zone_id')
            },
            user_name=distributor.get('user_name'),
            changes_summary=f"Delivery man created: {result.get('name')}",
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            action_type='CREATE',
            entity_type='delivery_man',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

