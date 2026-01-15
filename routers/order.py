"""
Order Router
============
Handles API endpoints for order operations.

API ENDPOINTS:
- POST /orders/order-booker/{order_booker_id} - Create order (Order Booker)
- GET /orders/order-booker/{order_booker_id} - List orders by order booker
- GET /orders/delivery-man/{delivery_man_id} - List orders assigned to delivery man
- GET /orders/visit/{visit_id} - Get orders linked to a visit
- POST /orders/{order_id}/assign - Assign order to delivery man (Distributor)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import OrderCreate, OrderResponse, OrderDeliveryUpdate
from services.order_service import OrderService
from services.activity_log_service import ActivityLogService
from utils.auth_helpers import get_current_user_from_request

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/order-booker/{order_booker_id}", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_booker_id: int,
    order: OrderCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create a new order (by Order Booker).
    
    API: POST /orders/order-booker/{order_booker_id}
    
    FLOW:
    1. Order Booker places order during visit
    2. Service validates credit limit
    3. Creates order with items
    4. Returns order data
    
    Request Body:
        {
            "shop_id": 1,
            "order_items": [
                {"product_name": "Tulip Tea Premium", "quantity": 10, "unit_price": 500.00},
                {"product_name": "Tulip Tea Regular", "quantity": 5, "unit_price": 300.00}
            ],
            "scheduled_date": "2026-01-10",  // Optional
            "visit_id": 1  // Optional - link to visit
        }
    
    Response (201):
        Order data with items
    """
    try:
        from datetime import date
        
        scheduled_date_obj = None
        if order.scheduled_date:
            try:
                scheduled_date_obj = date.fromisoformat(order.scheduled_date)
            except (ValueError, AttributeError):
                raise ValueError("Invalid scheduled_date format. Use ISO date format (e.g., 2026-01-10)")
        
        # Get distributor_id from order_booker
        from repositories.order_booker_repository import OrderBookerRepository
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        distributor_id = order_booker.distributor_id
        
        order_data = OrderService.create_order(
            db=db,
            shop_id=order.shop_id,
            order_booker_id=order_booker_id,
            order_items=[item.dict() for item in order.order_items],
            distributor_id=distributor_id,
            visit_id=order.visit_id,
            scheduled_date=scheduled_date_obj
        )
        
        # Log order creation
        ActivityLogService.log_create(
            db=db,
            user_id=order_booker_id,
            user_role='order_booker',
            entity_type='order',
            entity_id=order_data['id'],
            new_values={
                'shop_id': order_data.get('shop_id'),
                'shop_name': order_data.get('shop_name'),
                'total_amount': str(order_data.get('total_amount', 0)),
                'status': order_data.get('status')
            },
            metadata={
                'order_items_count': len(order_data.get('order_items', [])),
                'visit_id': order_data.get('visit_id'),
                'scheduled_date': str(order_data.get('scheduled_date', '')) if order_data.get('scheduled_date') else None
            },
            changes_summary=f"Order created: {order_data.get('shop_name')} - Rs. {order_data.get('total_amount', 0)}",
            request=request
        )
        
        return order_data
    except ValueError as e:
        # Log failure
        user_info = get_current_user_from_request(request)
        ActivityLogService.log_failure(
            db=db,
            user_id=user_info['user_id'] if user_info else order_booker_id,
            user_role=user_info['user_role'] if user_info else 'order_booker',
            action_type='CREATE',
            entity_type='order',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log failure
        user_info = get_current_user_from_request(request)
        ActivityLogService.log_failure(
            db=db,
            user_id=user_info['user_id'] if user_info else order_booker_id,
            user_role=user_info['user_role'] if user_info else 'order_booker',
            action_type='CREATE',
            entity_type='order',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating order: {str(e)}"
        )


@router.get("/order-booker/{order_booker_id}", response_model=List[OrderResponse])
async def list_orders_by_order_booker(
    order_booker_id: int,
    db: Session = Depends(get_db)
):
    """List all orders placed by an order booker."""
    try:
        orders = OrderService.get_orders_by_order_booker(db, order_booker_id)
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching orders: {str(e)}"
        )


@router.get("/delivery-man/{delivery_man_id}", response_model=List[OrderResponse])
async def list_orders_by_delivery_man(
    delivery_man_id: int,
    db: Session = Depends(get_db)
):
    """List all orders assigned to a delivery man."""
    try:
        orders = OrderService.get_orders_by_delivery_man(db, delivery_man_id)
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching orders: {str(e)}"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: int,
    db: Session = Depends(get_db)
):
    """Get an order by ID."""
    try:
        from repositories.order_repository import OrderRepository
        order = OrderRepository.get_by_id(db, order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        orders = OrderService._format_orders(db, [order])
        return orders[0] if orders else None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching order: {str(e)}"
        )


@router.get("/visit/{visit_id}", response_model=List[OrderResponse])
async def list_orders_by_visit(
    visit_id: int,
    db: Session = Depends(get_db)
):
    """List all orders linked to a visit."""
    try:
        orders = OrderService.get_orders_by_visit(db, visit_id)
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching orders: {str(e)}"
        )


@router.put("/{order_id}/deliver", response_model=OrderResponse)
async def deliver_order(
    order_id: int,
    delivery_data: "OrderDeliveryUpdate",
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Mark order as delivered or cancelled (by Delivery Man) with delivery proof.
    
    API: PUT /orders/{order_id}/deliver
    
    Request Body:
        {
            "status": "delivered" or "cancelled",
            "delivery_gps_lat": 33.684422 (optional),
            "delivery_gps_lng": 73.047905 (optional),
            "delivery_remarks": "Delivered to shop owner" (optional),
            "delivery_images": ["https://.../image1.jpg", "https://.../image2.jpg"] (optional)
        }
    
    Note: Images should be uploaded to Supabase storage bucket "deliveries" first,
    then URLs should be provided in delivery_images array.
    """
    try:
        from repositories.order_repository import OrderRepository
        from decimal import Decimal
        import json
        
        order = OrderRepository.get_by_id(db, order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        old_status = order.status
        
        # Convert delivery_images list to JSON string if provided
        delivery_images_json = None
        if delivery_data.delivery_images:
            delivery_images_json = json.dumps(delivery_data.delivery_images)
        
        # Create shop visit for delivery
        from repositories.shop_visit_repository import ShopVisitRepository
        from repositories.visit_type_repository import VisitTypeRepository
        from datetime import datetime
        
        visit_type = "delivery" if delivery_data.status == "delivered" else "cancelled"
        
        # Create shop visit with GPS and images
        visit_photos_json = None
        if delivery_data.delivery_images:
            visit_photos_json = json.dumps(delivery_data.delivery_images)
        
        shop_visit = ShopVisitRepository.create(
            db=db,
            shop_id=order.shop_id,
            delivery_man_id=order.delivery_man_id,
            visit_type=visit_type,
            gps_lat=Decimal(str(delivery_data.delivery_gps_lat)) if delivery_data.delivery_gps_lat is not None else None,
            gps_lng=Decimal(str(delivery_data.delivery_gps_lng)) if delivery_data.delivery_gps_lng is not None else None,
            visit_time=datetime.utcnow(),
            photos=visit_photos_json,  # Multiple images as JSON
            reason=delivery_data.delivery_remarks  # Delivery remarks stored in reason field
        )
        
        # Create visit type in junction table
        try:
            VisitTypeRepository.create(db, shop_visit.id, visit_type)
        except Exception as e:
            print(f"Warning: Failed to create visit type '{visit_type}': {e}")
        
        # Update order with delivery proof (without GPS - GPS is in shop_visits now)
        updated_order = OrderRepository.update_delivery_proof(
            db=db,
            order_id=order_id,
            status=delivery_data.status,
            delivery_gps_lat=None,  # GPS removed from orders - stored in shop_visits
            delivery_gps_lng=None,  # GPS removed from orders - stored in shop_visits
            delivery_remarks=delivery_data.delivery_remarks,
            delivery_images=delivery_images_json
        )
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Link order to the shop visit
        updated_order.visit_id = shop_visit.id
        db.commit()
        db.refresh(updated_order)
        
        # Get full order data
        orders = OrderService._format_orders(db, [updated_order])
        order_data = orders[0] if orders else None
        
        # Parse delivery_images JSON string back to list for response
        if updated_order.delivery_images:
            try:
                # delivery_images is stored as JSON string in TEXT column
                if isinstance(updated_order.delivery_images, str):
                    order_data['delivery_images'] = json.loads(updated_order.delivery_images)
                elif isinstance(updated_order.delivery_images, list):
                    # If already a list (shouldn't happen, but handle it)
                    order_data['delivery_images'] = updated_order.delivery_images
                else:
                    order_data['delivery_images'] = []
            except Exception as e:
                print(f"Error parsing delivery_images in response: {e}")
                order_data['delivery_images'] = []
        
        # Log order delivery
        if request:
            try:
                current_user = get_current_user_from_request(request, db)
                changes_summary = f"Order marked as {delivery_data.status} by delivery man"
                if delivery_data.delivery_remarks:
                    changes_summary += f" - Remarks: {delivery_data.delivery_remarks[:50]}"
                if delivery_data.delivery_images:
                    changes_summary += f" - {len(delivery_data.delivery_images)} image(s) uploaded"
                
                ActivityLogService.log_update(
                    db=db,
                    user_id=current_user.get('id') or updated_order.delivery_man_id,
                    user_role=current_user.get('role', 'delivery_man'),
                    entity_type='order',
                    entity_id=order_id,
                    old_values={'status': old_status},
                    new_values={
                        'status': delivery_data.status,
                        'delivery_gps_lat': delivery_data.delivery_gps_lat,
                        'delivery_gps_lng': delivery_data.delivery_gps_lng,
                        'delivery_remarks': delivery_data.delivery_remarks,
                        'delivery_images_count': len(delivery_data.delivery_images) if delivery_data.delivery_images else 0
                    },
                    changes_summary=changes_summary
                )
            except Exception as log_error:
                print(f"Warning: Failed to log order delivery: {log_error}")
        
        return order_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error delivering order: {str(e)}"
        )


@router.post("/{order_id}/assign", response_model=OrderResponse)
async def assign_order_to_delivery_man(
    order_id: int,
    delivery_man_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Assign order to a delivery man (by Distributor).
    
    API: POST /orders/{order_id}/assign?delivery_man_id={id}
    
    FLOW:
    1. Distributor views pending orders
    2. Selects delivery man for order
    3. Service assigns order
    4. Order status changes to "confirmed"
    """
    try:
        # Get order before assignment for logging
        from repositories.order_repository import OrderRepository
        order_before = OrderRepository.get_by_id(db, order_id)
        if not order_before:
            raise ValueError("Order not found")
        
        old_delivery_man_id = order_before.delivery_man_id
        old_status = order_before.status
        
        result = OrderService.assign_delivery_man(db, order_id, delivery_man_id)
        # Get full order data
        order = OrderRepository.get_by_id(db, order_id)
        if not order:
            raise ValueError("Order not found")
        orders = OrderService._format_orders(db, [order])
        order_data = orders[0] if orders else result
        
        # Log order assignment
        user_info = get_current_user_from_request(request)
        ActivityLogService.log_activity(
            db=db,
            user_id=user_info['user_id'] if user_info else None,
            user_role=user_info['user_role'] if user_info else 'distributor',
            action_type='ASSIGN',
            entity_type='order',
            entity_id=order_id,
            old_values={
                'delivery_man_id': old_delivery_man_id,
                'status': old_status
            },
            new_values={
                'delivery_man_id': delivery_man_id,
                'status': order_data.get('status')
            },
            changes_summary=f"Order assigned to delivery man: {order_data.get('delivery_man_name', 'N/A')}",
            metadata={'shop_id': order_data.get('shop_id'), 'shop_name': order_data.get('shop_name')},
            request=request
        )
        
        return order_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning order: {str(e)}"
        )

