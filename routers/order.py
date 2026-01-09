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
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import OrderCreate, OrderResponse
from services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/order-booker/{order_booker_id}", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_booker_id: int,
    order: OrderCreate,
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
        return order_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
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


@router.post("/{order_id}/assign", response_model=OrderResponse)
async def assign_order_to_delivery_man(
    order_id: int,
    delivery_man_id: int,
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
        result = OrderService.assign_delivery_man(db, order_id, delivery_man_id)
        # Get full order data
        from repositories.order_repository import OrderRepository
        order = OrderRepository.get_by_id(db, order_id)
        if not order:
            raise ValueError("Order not found")
        orders = OrderService._format_orders(db, [order])
        return orders[0] if orders else result
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

