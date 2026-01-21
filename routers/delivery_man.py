"""
Delivery Man router.
Handles delivery man CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import DeliveryManCreate, DeliveryManResponse, DeliveryManUpdate
from services.delivery_man_service import DeliveryManService

router = APIRouter(prefix="/delivery-men", tags=["Delivery Men"])


# List routes first (more specific paths)
@router.get("/distributor/{distributor_id}", response_model=List[DeliveryManResponse])
async def list_delivery_men_by_distributor(
    distributor_id: int,
    db: Session = Depends(get_db)
):
    """List all delivery men for a specific distributor."""
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
    db: Session = Depends(get_db)
):
    """Update a delivery man."""
    try:
        result = DeliveryManService.update_delivery_man(
            db=db,
            delivery_man_id=delivery_man_id,
            name=update_data.name,
            phone=update_data.phone,
            zone_id=update_data.zone_id,
            password=update_data.password
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{delivery_man_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery_man(
    delivery_man_id: int,
    db: Session = Depends(get_db)
):
    """Delete a delivery man."""
    try:
        DeliveryManService.delete_delivery_man(db=db, delivery_man_id=delivery_man_id)
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# Create route last (less specific path)
@router.get("/{delivery_man_id}/routes", response_model=List[dict])
async def get_delivery_man_routes(
    delivery_man_id: int,
    db: Session = Depends(get_db)
):
    """Get all routes in the delivery man's zone (zone-based assignment, not route-specific)."""
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


@router.get("/{delivery_man_id}/warehouses", response_model=List[dict])
async def get_delivery_man_warehouses(
    delivery_man_id: int,
    db: Session = Depends(get_db)
):
    """Get all warehouses assigned to a delivery man with inventory details."""
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


@router.post("/{distributor_id}", response_model=DeliveryManResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_man(
    distributor_id: int,
    delivery_man: DeliveryManCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new delivery man.
    Only distributors can create delivery men.
    """
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
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

