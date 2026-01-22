"""
Delivery Router
==============
Handles API endpoints for delivery tracking operations.

API ENDPOINTS:
- POST /deliveries/order/{order_id} - Create delivery for order
- POST /deliveries/{delivery_id}/pickup - Record warehouse pickup
- POST /deliveries/{delivery_id}/deliver - Record shop delivery
- POST /deliveries/{delivery_id}/return - Record warehouse return
- GET /deliveries/order/{order_id} - Get delivery by order
- GET /deliveries/delivery-man/{delivery_man_id} - Get deliveries by delivery man
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from decimal import Decimal
from config.database import get_db
from services.delivery_service import DeliveryService
from utils.auth_helpers import get_current_user_from_request
from pydantic import BaseModel

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])


# Request Schemas
class DeliveryPickupRequest(BaseModel):
    pickup_quantities: Dict[int, int]  # order_item_id -> quantity
    pickup_gps_lat: Optional[float] = None
    pickup_gps_lng: Optional[float] = None


class DeliveryDeliverRequest(BaseModel):
    delivery_quantities: Dict[int, int]  # order_item_id -> quantity
    delivery_gps_lat: Optional[float] = None
    delivery_gps_lng: Optional[float] = None
    delivery_remarks: Optional[str] = None
    delivery_images: Optional[List[str]] = None


class DeliveryReturnRequest(BaseModel):
    return_quantities: Dict[int, int]  # order_item_id -> quantity
    return_gps_lat: Optional[float] = None
    return_gps_lng: Optional[float] = None
    return_reason: Optional[str] = None


class DeliveryCreateRequest(BaseModel):
    warehouse_id: int


@router.post("/order/{order_id}", status_code=status.HTTP_201_CREATED)
async def create_delivery_for_order(
    order_id: int,
    request_data: DeliveryCreateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create a delivery record for an order.
    
    This is called when an order is assigned to a delivery man.
    Creates delivery and delivery_items records.
    """
    try:
        user_info = get_current_user_from_request(request)
        delivery_man_id = user_info.get('user_id')
        
        if not delivery_man_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        result = DeliveryService.create_delivery_for_order(
            db=db,
            order_id=order_id,
            delivery_man_id=delivery_man_id,
            warehouse_id=request_data.warehouse_id
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error creating delivery: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating delivery: {str(e)}"
        )


@router.post("/{delivery_id}/pickup")
async def pickup_from_warehouse(
    delivery_id: int,
    pickup_data: DeliveryPickupRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Record warehouse pickup and deduct inventory.
    
    This is called when delivery man picks up stock from warehouse.
    Automatically deducts inventory quantities.
    """
    try:
        user_info = get_current_user_from_request(request)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        result = DeliveryService.pickup_from_warehouse(
            db=db,
            delivery_id=delivery_id,
            pickup_quantities=pickup_data.pickup_quantities,
            pickup_gps_lat=Decimal(str(pickup_data.pickup_gps_lat)) if pickup_data.pickup_gps_lat else None,
            pickup_gps_lng=Decimal(str(pickup_data.pickup_gps_lng)) if pickup_data.pickup_gps_lng else None
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording pickup: {str(e)}"
        )


@router.post("/{delivery_id}/deliver")
async def deliver_to_shop(
    delivery_id: int,
    deliver_data: DeliveryDeliverRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Record shop delivery.
    
    This is called when delivery man delivers order to shop.
    Updates quantities and status.
    """
    try:
        user_info = get_current_user_from_request(request)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        result = DeliveryService.deliver_to_shop(
            db=db,
            delivery_id=delivery_id,
            delivery_quantities=deliver_data.delivery_quantities,
            delivery_gps_lat=Decimal(str(deliver_data.delivery_gps_lat)) if deliver_data.delivery_gps_lat else None,
            delivery_gps_lng=Decimal(str(deliver_data.delivery_gps_lng)) if deliver_data.delivery_gps_lng else None,
            delivery_remarks=deliver_data.delivery_remarks,
            delivery_images=deliver_data.delivery_images
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording delivery: {str(e)}"
        )


@router.post("/{delivery_id}/return")
async def return_to_warehouse(
    delivery_id: int,
    return_data: DeliveryReturnRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Record return to warehouse and add inventory back.
    
    This is called when delivery man returns unsold stock to warehouse.
    Automatically adds inventory quantities back.
    """
    try:
        user_info = get_current_user_from_request(request)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        result = DeliveryService.return_to_warehouse(
            db=db,
            delivery_id=delivery_id,
            return_quantities=return_data.return_quantities,
            return_gps_lat=Decimal(str(return_data.return_gps_lat)) if return_data.return_gps_lat else None,
            return_gps_lng=Decimal(str(return_data.return_gps_lng)) if return_data.return_gps_lng else None,
            return_reason=return_data.return_reason
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording return: {str(e)}"
        )


@router.get("/order/{order_id}")
async def get_delivery_by_order(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get delivery data for an order.
    
    Returns null if no delivery exists yet (this is normal for new orders).
    """
    try:
        result = DeliveryService.get_delivery_by_order(db=db, order_id=order_id)
        # Return null instead of 404 - it's expected for orders without deliveries yet
        return result if result else None
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error fetching delivery for order {order_id}: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching delivery: {str(e)}"
        )


@router.get("/delivery-man/{delivery_man_id}")
async def get_deliveries_by_delivery_man(
    delivery_man_id: int,
    skip: int = 0,
    limit: int = 100,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get all deliveries for a delivery man."""
    try:
        result = DeliveryService.get_deliveries_by_delivery_man(
            db=db,
            delivery_man_id=delivery_man_id,
            skip=skip,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching deliveries: {str(e)}"
        )


@router.get("/distributor/{distributor_id}")
async def get_deliveries_by_distributor(
    distributor_id: int,
    skip: int = 0,
    limit: int = 1000,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get all deliveries for a distributor (through their delivery men)."""
    try:
        result = DeliveryService.get_deliveries_by_distributor(
            db=db,
            distributor_id=distributor_id,
            skip=skip,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching deliveries: {str(e)}"
        )

