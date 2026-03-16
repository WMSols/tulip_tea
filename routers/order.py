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
from typing import List, Dict, Optional
from config.database import get_db
from models.schemas import OrderCreate, OrderResponse, OrderDeliveryUpdate, OrderPaymentCollection
from services.order_service import OrderService
from services.activity_log_service import ActivityLogService
from utils.auth_helpers import get_current_user_from_request
from utils.dependencies import get_current_user, get_current_distributor, get_current_order_booker, get_current_delivery_man
from typing import Dict

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/order-booker/{order_booker_id}", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, tags=["Orders", "Order Booker APIs"])
async def create_order(
    order_booker_id: int,
    order: OrderCreate,
    request: Request,
    order_booker: Dict = Depends(get_current_order_booker),
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
    # Verify order booker can only create orders for themselves
    if order_booker['user_id'] != order_booker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create orders for your own account"
        )
    
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
        
        # Convert final_total_amount to Decimal if provided
        from decimal import Decimal
        final_total_decimal = None
        if order.final_total_amount is not None:
            final_total_decimal = Decimal(str(order.final_total_amount))
        
        order_data = OrderService.create_order(
            db=db,
            shop_id=order.shop_id,
            order_booker_id=order_booker_id,
            order_items=[item.dict() for item in order.order_items],
            distributor_id=distributor_id,
            visit_id=order.visit_id,
            scheduled_date=scheduled_date_obj,
            final_total_amount=final_total_decimal,
            order_resolution_type=order.order_resolution_type,
            subsidy_id=order.subsidy_id
        )
        
        # Log order creation
        subsidy_status = order_data.get('subsidy_status', 'none')
        changes_summary = f"Order created: {order_data.get('shop_name')} - Rs. {order_data.get('total_amount', 0)}"
        if subsidy_status == 'pending_approval':
            discount_amount = (order_data.get('calculated_total_amount', 0) or 0) - (order_data.get('final_total_amount', 0) or 0)
            changes_summary += f" (Subsidy requested: Rs. {discount_amount:.2f} discount, awaiting distributor approval)"
        
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
                'calculated_total_amount': str(order_data.get('calculated_total_amount', 0)) if order_data.get('calculated_total_amount') else None,
                'final_total_amount': str(order_data.get('final_total_amount', 0)) if order_data.get('final_total_amount') else None,
                'subsidy_status': subsidy_status,
                'status': order_data.get('status')
            },
            metadata={
                'order_items_count': len(order_data.get('order_items', [])),
                'visit_id': order_data.get('visit_id'),
                'scheduled_date': str(order_data.get('scheduled_date', '')) if order_data.get('scheduled_date') else None
            },
            changes_summary=changes_summary,
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
    order_booker: Dict = Depends(get_current_order_booker),
    db: Session = Depends(get_db)
):
    """List all orders placed by an order booker."""
    # Verify order booker can only view their own orders
    if order_booker['user_id'] != order_booker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view orders for your own account"
        )
    
    try:
        orders = OrderService.get_orders_by_order_booker(db, order_booker_id)
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching orders: {str(e)}"
        )


@router.get("/delivery-man/{delivery_man_id}", response_model=List[OrderResponse], tags=["Orders", "Delivery Man APIs"])
async def list_orders_by_delivery_man(
    delivery_man_id: int,
    include_delivery: bool = False,
    pending: Optional[str] = Query(None, description="Return only pending/active orders for Orders tab (e.g. ?pending or ?pending=true)"),
    deliveries: Optional[str] = Query(None, description="Return only completed deliveries for Deliveries tab (e.g. ?deliveries or ?deliveries=true)"),
    delivery_man: Dict = Depends(get_current_delivery_man),
    db: Session = Depends(get_db)
):
    """List orders for a delivery man. Use ?pending for Orders tab (active only, with delivery). Use ?deliveries for Deliveries tab (completed only, with full delivery). Otherwise use include_delivery=true to embed delivery summary."""
    # Verify delivery man can only view their own orders
    if delivery_man['user_id'] != delivery_man_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view orders for your own account"
        )
    pending_only = pending is not None
    deliveries_only = deliveries is not None
    if pending_only and deliveries_only:
        pending_only = True
        deliveries_only = False
    try:
        orders = OrderService.get_orders_by_delivery_man(
            db, delivery_man_id,
            include_delivery=include_delivery or pending_only or deliveries_only,
            pending_only=pending_only,
            deliveries_only=deliveries_only
        )
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching orders: {str(e)}"
        )


@router.get("/pending-subsidy-approval", response_model=List[OrderResponse], tags=["Orders", "Distributor APIs"])
async def get_pending_subsidy_approvals(
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Get all orders pending subsidy approval for the authenticated distributor.
    
    API: GET /orders/pending-subsidy-approval
    
    Returns orders where:
    - subsidy_status = 'pending_approval'
    - distributor_id matches the authenticated distributor
    
    Response (200):
        List of orders pending approval
    """
    try:
        distributor_id = distributor['user_id']
        orders = OrderService.get_pending_subsidy_approvals(db, distributor_id)
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pending approvals: {str(e)}"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: int,
    current_user: Dict = Depends(get_current_user),
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
    current_user: Dict = Depends(get_current_user),
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


@router.post("/{order_id}/collect-payment", response_model=OrderResponse)
async def collect_payment_before_delivery(
    order_id: int,
    payment_data: "OrderPaymentCollection",
    request: Request = None,
    delivery_man: Dict = Depends(get_current_delivery_man),
    db: Session = Depends(get_db)
):
    """
    Collect payment before delivery (by Delivery Man).
    
    API: POST /orders/{order_id}/collect-payment
    
    FLOW:
    1. Delivery Man arrives at shop
    2. If order requires payment before delivery, collects payment first
    3. Records payment amount and timestamp
    4. Reduces shop's outstanding balance
    5. Order can now be delivered
    
    Request Body:
        {
            "payment_amount": 5000.00,
            "remarks": "Payment collected in cash" (optional)
        }
    
    Response (200):
        Updated order (OrderResponse) including for payment_before_delivery orders:
        - payment_collected_before_delivery: true
        - payment_collected_amount: amount recorded
        - payment_collected_at: ISO timestamp
        So frontend can see payment is collected and allow deliver.
    """
    try:
        from repositories.order_repository import OrderRepository
        from repositories.shop_repository import ShopRepository
        from decimal import Decimal
        from datetime import datetime
        
        order = OrderRepository.get_by_id(db, order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Check if order requires payment before delivery
        if order.order_resolution_type != 'payment_before_delivery':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This order does not require payment before delivery"
            )
        
        # Check if payment already collected
        if order.payment_collected_before_delivery:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already collected for this order"
            )
        
        payment_amount = Decimal(str(payment_data.payment_amount))
        if payment_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount must be greater than 0"
            )
        
        # Single transaction: order + shop + wallet; commit only at the end so no DB write on error
        # 1. Update order (in memory, no commit)
        order.payment_collected_before_delivery = True
        order.payment_collected_amount = payment_amount
        order.payment_collected_at = datetime.utcnow()
        db.flush()
        
        # 2. Reduce shop's outstanding balance (no commit)
        shop = ShopRepository.get_by_id(db, order.shop_id)
        if shop:
            current_outstanding = Decimal(str(shop.outstanding_balance or 0))
            new_outstanding = max(Decimal('0'), current_outstanding - payment_amount)
            ShopRepository.update(
                db=db,
                shop_id=order.shop_id,
                outstanding_balance=new_outstanding,
                auto_commit=False
            )
        
        # 3. Credit delivery man's wallet and record transaction (no commit)
        from services.wallet_service import WalletService
        WalletService.credit_wallet(
            db=db,
            user_type="delivery_man",
            user_id=delivery_man['user_id'],
            amount=payment_amount,
            description=f"Collection from shop {shop.name if shop else order.shop_id} (payment before delivery - Order #{order_id})",
            reference_type="order_collect_payment",
            reference_id=order_id,
            initiated_by_type="delivery_man",
            initiated_by_id=delivery_man['user_id'],
            transaction_metadata={
                "shop_id": order.shop_id,
                "shop_name": shop.name if shop else None,
                "order_id": order_id,
                "amount": float(payment_amount),
                "payment_collected_at": order.payment_collected_at.isoformat() if getattr(order, 'payment_collected_at', None) else None,
            },
            auto_commit=False
        )
        
        # 4. Commit once; on any exception above, session rolls back and DB is not written
        db.commit()
        db.refresh(order)
        
        # 5. Format response (includes payment_collected_before_delivery, payment_collected_amount, payment_collected_at)
        from services.order_service import OrderService
        order_data = OrderService._format_orders(db, [order])[0]
        
        return order_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error collecting payment: {str(e)}"
        )


@router.put("/{order_id}/deliver", response_model=OrderResponse, tags=["Orders", "Delivery Man APIs"])
async def deliver_order(
    order_id: int,
    delivery_data: "OrderDeliveryUpdate",
    request: Request = None,
    delivery_man: Dict = Depends(get_current_delivery_man),
    db: Session = Depends(get_db)
):
    """
    Mark order as delivered or disapproved (by Delivery Man) with delivery proof.
    
    API: PUT /orders/{order_id}/deliver
    
    Request Body:
        {
            "status": "delivered" or "disapproved",
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
        
        # Check if payment is required before delivery
        if order.order_resolution_type == 'payment_before_delivery':
            if not order.payment_collected_before_delivery:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payment must be collected before delivery. Please collect payment first using /orders/{order_id}/collect-payment"
                )
        
        old_status = order.status.value if hasattr(order.status, 'value') else str(order.status)
        
        # Convert delivery_images list to JSON string if provided
        delivery_images_json = None
        if delivery_data.delivery_images:
            delivery_images_json = json.dumps(delivery_data.delivery_images)
        
        # Create shop visit for delivery
        from repositories.shop_visit_repository import ShopVisitRepository
        from repositories.visit_type_repository import VisitTypeRepository
        from datetime import datetime
        
        visit_type = "delivery" if delivery_data.status == "delivered" else "cancelled"  # Visit type can be "cancelled" even if order status is "disapproved"
        
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
            visit_date=datetime.utcnow(),  # Model uses visit_date
            photos=visit_photos_json,  # Multiple images as JSON
            reason=delivery_data.delivery_remarks  # Delivery remarks stored in reason field
        )
        
        # Create visit type in junction table
        # Note: shop_visit is already committed, so visit_type should also commit immediately
        # If visit_type creation fails, it's logged but doesn't fail the delivery update
        try:
            VisitTypeRepository.create(db, shop_visit.id, visit_type, auto_commit=True)
        except Exception as e:
            # Log error but don't fail the delivery - visit is already created
            print(f"Warning: Failed to create visit type '{visit_type}': {e}")
            # This is acceptable since visit_type is supplementary data
        
        # Update order with delivery proof (without GPS - GPS is in shop_visits now)
        from models.order import OrderStatus
        order_status = OrderStatus.DELIVERED if delivery_data.status == "delivered" else OrderStatus.DISAPPROVED
        updated_order = OrderRepository.update_delivery_proof(
            db=db,
            order_id=order_id,
            status=order_status,
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
                changes_summary = f"Order marked as {delivery_data.status} by delivery man"
                if delivery_data.delivery_remarks:
                    changes_summary += f" - Remarks: {delivery_data.delivery_remarks[:50]}"
                if delivery_data.delivery_images:
                    changes_summary += f" - {len(delivery_data.delivery_images)} image(s) uploaded"
                
                ActivityLogService.log_update(
                    db=db,
                    user_id=delivery_man['user_id'],
                    user_role='delivery_man',
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


@router.put("/{order_id}/approve-subsidy", response_model=OrderResponse, tags=["Orders", "Distributor APIs"])
async def approve_subsidy(
    order_id: int,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Approve a subsidized order (by Distributor).
    
    API: PUT /orders/{order_id}/approve-subsidy
    
    FLOW:
    1. Distributor reviews pending subsidy approval
    2. Approves the order
    3. Order becomes assignable to delivery man
    4. Shop's outstanding balance is updated
    
    Response (200):
        Updated order data with subsidy_status = 'approved'
    """
    try:
        distributor_id = distributor['user_id']
        
        result = OrderService.approve_subsidy(db, order_id, distributor_id)
        
        # Log approval
        ActivityLogService.log_activity(
            db=db,
            user_id=distributor_id,
            user_role='distributor',
            action_type='APPROVE',
            entity_type='order',
            entity_id=order_id,
            new_values={
                'subsidy_status': 'approved',
                'subsidy_approved_by': distributor_id
            },
            changes_summary=f"Subsidy approved: Order {order_id}",
            request=request
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
            detail=f"Error approving subsidy: {str(e)}"
        )


@router.put("/{order_id}/reject-subsidy", response_model=OrderResponse, tags=["Orders", "Distributor APIs"])
async def reject_subsidy(
    order_id: int,
    rejection_reason: str = Query(None, description="Optional reason for rejection"),
    request: Request = None,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Reject a subsidized order (by Distributor).
    
    API: PUT /orders/{order_id}/reject-subsidy?rejection_reason={reason}
    
    FLOW:
    1. Distributor reviews pending subsidy approval
    2. Rejects the order with optional reason
    3. Order cannot be assigned to delivery man
    4. Shop's outstanding balance is NOT updated
    
    Query Parameters:
        rejection_reason: Optional reason for rejection
    
    Response (200):
        Updated order data with subsidy_status = 'rejected'
    """
    try:
        distributor_id = distributor['user_id']
        
        result = OrderService.reject_subsidy(db, order_id, distributor_id, rejection_reason)
        
        # Log rejection
        ActivityLogService.log_activity(
            db=db,
            user_id=distributor_id,
            user_role='distributor',
            action_type='REJECT',
            entity_type='order',
            entity_id=order_id,
            new_values={
                'subsidy_status': 'rejected',
                'subsidy_rejection_reason': rejection_reason
            },
            changes_summary=f"Subsidy rejected: Order {order_id}" + (f" - {rejection_reason}" if rejection_reason else ""),
            request=request
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
            detail=f"Error rejecting subsidy: {str(e)}"
        )


@router.post("/{order_id}/assign", response_model=OrderResponse, tags=["Orders", "Distributor APIs"])
async def assign_order_to_delivery_man(
    order_id: int,
    delivery_man_id: int,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Assign order to a delivery man (by Distributor).
    
    API: POST /orders/{order_id}/assign?delivery_man_id={id}
    
    FLOW:
    1. Distributor views pending orders
    2. Selects delivery man for order
    3. Service assigns order
    4. Order status remains "pending" until delivery man marks it as "delivered" or "disapproved"
    """
    # Wrap all database operations in a single transaction to prevent partial execution
    try:
        # Get order before assignment for logging
        from repositories.order_repository import OrderRepository
        order_before = OrderRepository.get_by_id(db, order_id)
        if not order_before:
            raise ValueError("Order not found")
        
        old_delivery_man_id = order_before.delivery_man_id
        old_status = order_before.status.value if hasattr(order_before.status, 'value') else str(order_before.status)
        
        # Assign delivery man with auto_commit=False to control transaction
        result = OrderService.assign_delivery_man(db, order_id, delivery_man_id, auto_commit=False)
        
        # Get full order data
        order = OrderRepository.get_by_id(db, order_id)
        if not order:
            raise ValueError("Order not found")
        orders = OrderService._format_orders(db, [order])
        order_data = orders[0] if orders else result
        
        # Log order assignment (with error handling to prevent transaction rollback)
        try:
            ActivityLogService.log_activity(
                db=db,
                user_id=distributor['user_id'],
                user_role='distributor',
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
        except Exception as log_error:
            # Logging failures should not break the operation
            print(f"⚠️ Failed to log order assignment (non-critical): {log_error}")
            import traceback
            traceback.print_exc()
        
        # Commit transaction after all operations succeed
        db.commit()
        
        return order_data
    except Exception as e:
        # Rollback on any error
        db.rollback()
        raise
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

