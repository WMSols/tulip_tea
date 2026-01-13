"""
Order Business Logic Service
============================
Business logic layer for Order operations.

This service handles:
- Order creation with credit limit validation
- Order item management
- Order assignment to delivery men
- Credit limit calculations
"""
from sqlalchemy.orm import Session
from repositories.order_repository import OrderRepository
from repositories.order_item_repository import OrderItemRepository
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.payment_repository import PaymentRepository
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime, date


class OrderService:
    """Service for Order business logic."""
    
    @staticmethod
    def calculate_outstanding_balance(db: Session, shop_id: int) -> Decimal:
        """
        Calculate shop's current outstanding balance.
        
        Outstanding = (Sum of unpaid orders) - (Sum of payments)
        
        Args:
            db: Database session
            shop_id: Shop ID
        
        Returns:
            Decimal: Outstanding balance
        
        Raises:
            Exception: If there's an error querying payments or orders
        """
        try:
            # Get all unpaid orders (status not in 'paid', 'cancelled')
            from models.order import Order
            orders = db.query(Order).filter(Order.shop_id == shop_id).all()
            unpaid_orders = [o for o in orders if o.status not in ['paid', 'cancelled']]
            total_orders = sum(Decimal(str(o.total_amount or 0)) for o in unpaid_orders)
        except Exception as e:
            print(f"ERROR calculating orders total for shop {shop_id}: {e}")
            raise ValueError(f"Error calculating orders total: {str(e)}")
        
        try:
            # Get all payments (exclude soft-deleted)
            payments = PaymentRepository.get_by_shop(db, shop_id, include_deleted=False)
            total_payments = sum(Decimal(str(p.amount or 0)) for p in payments)
        except Exception as e:
            print(f"ERROR querying payments for shop {shop_id}: {e}")
            from models.payment import Payment
            print(f"Payment model columns: {[c.name for c in Payment.__table__.columns]}")
            raise ValueError(f"Error querying payments: {str(e)}")
        
        # Get legacy balance from shop
        shop = ShopRepository.get_by_id(db, shop_id)
        legacy_balance = Decimal(str(shop.legacy_balance or 0)) if shop else Decimal('0')
        
        # Outstanding = Orders - Payments + Legacy Balance
        outstanding = total_orders - total_payments + legacy_balance
        return outstanding
    
    @staticmethod
    def create_order(db: Session, shop_id: int, order_booker_id: int,
                    order_items: List[Dict], distributor_id: int = None,
                    visit_id: int = None, scheduled_date: date = None) -> Dict:
        """
        Create a new order with credit limit validation.
        
        FLOW:
        1. Validates shop exists and is approved
        2. Validates order booker exists
        3. Calculates total order amount from items
        4. Validates credit limit (outstanding + new_order <= credit_limit)
        5. Creates order with status="pending"
        6. Creates order items
        7. Returns order data with items
        
        Args:
            db: Database session
            shop_id: Shop ID where order is placed
            order_booker_id: Order booker ID who placed the order
            order_items: List of order items [{"product_name": "...", "quantity": 10, "unit_price": 500.00}]
            distributor_id: Distributor ID (optional)
            visit_id: Visit ID where order was placed (optional)
            scheduled_date: Scheduled delivery date (optional)
        
        Returns:
            Dict: Order data with items
        
        Raises:
            ValueError: If validation fails or credit limit exceeded
        """
        from models.order import Order
        from models.order_item import OrderItem
        from repositories.payment_repository import PaymentRepository
        
        # Validate shop exists and is approved
        shop = ShopRepository.get_by_id(db, shop_id)
        if not shop:
            raise ValueError("Shop not found")
        if shop.registration_status != "approved":
            raise ValueError(f"Orders can only be placed for approved shops. Shop status: {shop.registration_status}")
        
        # Validate credit limit approval
        # If shop has ANY credit_limit_request (pending or approved), at least one must be approved
        # This covers both cases:
        # 1. Shop with credit_limit = 0 but has pending credit_limit_request
        # 2. Shop with credit_limit > 0 (should have approved request)
        from repositories.credit_limit_request_repository import CreditLimitRequestRepository
        credit_requests = CreditLimitRequestRepository.get_by_shop(db, shop_id)
        
        # Filter out soft-deleted requests
        active_requests = [req for req in credit_requests if req.deleted_at is None]
        
        # If there are any active credit limit requests, check approval status
        if active_requests:
            # Check if there's at least one approved request
            has_approved_request = any(req.status == "approved" for req in active_requests)
            
            if not has_approved_request:
                # Check if there are any pending requests
                has_pending_request = any(req.status == "pending" for req in active_requests)
                
                if has_pending_request:
                    raise ValueError(
                        "Orders cannot be placed for this shop. Credit limit request is pending approval. "
                        "Please wait for distributor to approve the credit limit request."
                    )
                else:
                    # No approved request found - could be rejected or never created
                    raise ValueError(
                        "Orders cannot be placed for this shop. Credit limit request has not been approved. "
                        "Please ensure the credit limit request is approved by the distributor before placing orders."
                    )
        
        # Validate order booker exists
        order_booker = OrderBookerRepository.get_by_id(db, order_booker_id)
        if not order_booker:
            raise ValueError("Order Booker not found")
        
        # Calculate total amount from items
        total_amount = Decimal('0')
        for item in order_items:
            quantity = int(item.get('quantity', 0))
            unit_price = Decimal(str(item.get('unit_price', 0)))
            item_total = quantity * unit_price
            total_amount += item_total
        
        if total_amount <= 0:
            raise ValueError("Order total amount must be greater than 0")
        
        # Validate credit limit using shop's outstanding_balance field
        credit_limit = Decimal(str(shop.credit_limit or 0))
        if credit_limit > 0:  # Only check if shop has a credit limit
            # Use shop's outstanding_balance field (maintained automatically)
            current_outstanding = Decimal(str(shop.outstanding_balance or 0))
            
            if current_outstanding + total_amount > credit_limit:
                available_credit = credit_limit - current_outstanding
                raise ValueError(
                    f"Order amount (Rs. {total_amount}) exceeds available credit. "
                    f"Credit limit: Rs. {credit_limit}, Outstanding: Rs. {current_outstanding}, "
                    f"Available: Rs. {available_credit}"
                )
        
        # Create order
        order = OrderRepository.create(
            db=db,
            shop_id=shop_id,
            order_booker_id=order_booker_id,
            distributor_id=distributor_id,
            delivery_man_id=None,  # Assigned later by distributor
            visit_id=visit_id,
            total_amount=total_amount,
            status="pending",
            scheduled_date=scheduled_date
        )
        
        # Create order items
        created_items = []
        for item in order_items:
            quantity = int(item.get('quantity', 0))
            unit_price = Decimal(str(item.get('unit_price', 0)))
            total_price = quantity * unit_price
            
            order_item = OrderItemRepository.create(
                db=db,
                order_id=order.id,
                product_name=item.get('product_name', ''),
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            created_items.append({
                "id": order_item.id,
                "order_id": order.id,  # Required by OrderItemResponse schema
                "product_name": order_item.product_name,
                "quantity": order_item.quantity,
                "unit_price": float(order_item.unit_price) if order_item.unit_price else None,
                "total_price": float(order_item.total_price) if order_item.total_price else None
            })
        
        # Update shop's outstanding balance: Increase by order amount
        # Refresh shop to get latest data
        shop = ShopRepository.get_by_id(db, shop_id)
        if shop:
            current_outstanding = Decimal(str(shop.outstanding_balance or 0))
            new_outstanding = current_outstanding + total_amount
            
            ShopRepository.update(
                db=db,
                shop_id=shop_id,
                outstanding_balance=new_outstanding
            )
        
        # Get shop name for response (refresh to get updated outstanding_balance)
        shop = ShopRepository.get_by_id(db, shop_id)
        shop_name = shop.name if shop else None
        order_booker_name = order_booker.name if order_booker else None
        
        return {
            "id": order.id,
            "shop_id": order.shop_id,
            "shop_name": shop_name,
            "order_booker_id": order.order_booker_id,
            "order_booker_name": order_booker_name,
            "distributor_id": order.distributor_id,
            "delivery_man_id": order.delivery_man_id,
            "visit_id": order.visit_id,
            "total_amount": float(order.total_amount) if order.total_amount else 0,
            "status": order.status,
            "scheduled_date": order.scheduled_date.isoformat() if order.scheduled_date else None,
            "order_items": created_items,
            "created_at": order.created_at.isoformat() if order.created_at else None
        }
    
    @staticmethod
    def get_orders_by_shop(db: Session, shop_id: int) -> List[Dict]:
        """Get all orders for a shop."""
        orders = OrderRepository.get_by_shop(db, shop_id)
        return OrderService._format_orders(db, orders)
    
    @staticmethod
    def get_orders_by_order_booker(db: Session, order_booker_id: int) -> List[Dict]:
        """Get all orders placed by an order booker."""
        orders = OrderRepository.get_by_order_booker(db, order_booker_id)
        return OrderService._format_orders(db, orders)
    
    @staticmethod
    def get_orders_by_delivery_man(db: Session, delivery_man_id: int) -> List[Dict]:
        """Get all orders assigned to a delivery man."""
        orders = OrderRepository.get_by_delivery_man(db, delivery_man_id)
        return OrderService._format_orders(db, orders)
    
    @staticmethod
    def get_orders_by_visit(db: Session, visit_id: int) -> List[Dict]:
        """Get all orders linked to a visit."""
        orders = OrderRepository.get_by_visit(db, visit_id)
        return OrderService._format_orders(db, orders)
    
    @staticmethod
    def _format_orders(db: Session, orders: List) -> List[Dict]:
        """Format orders with related data."""
        from repositories.shop_repository import ShopRepository
        from repositories.order_booker_repository import OrderBookerRepository
        from repositories.delivery_man_repository import DeliveryManRepository
        from repositories.order_item_repository import OrderItemRepository
        
        result = []
        for order in orders:
            # Get related data
            shop = ShopRepository.get_by_id(db, order.shop_id) if order.shop_id else None
            order_booker = OrderBookerRepository.get_by_id(db, order.order_booker_id) if order.order_booker_id else None
            delivery_man = DeliveryManRepository.get_by_id(db, order.delivery_man_id) if order.delivery_man_id else None
            
            # Get order items
            items = OrderItemRepository.get_by_order(db, order.id)
            order_items = [{
                "id": item.id,
                "order_id": order.id,  # Required by OrderItemResponse schema
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price) if item.unit_price else None,
                "total_price": float(item.total_price) if item.total_price else None
            } for item in items]
            
            result.append({
                "id": order.id,
                "shop_id": order.shop_id,
                "shop_name": shop.name if shop else None,
                "order_booker_id": order.order_booker_id,
                "order_booker_name": order_booker.name if order_booker else None,
                "distributor_id": order.distributor_id,
                "delivery_man_id": order.delivery_man_id,
                "delivery_man_name": delivery_man.name if delivery_man else None,
                "visit_id": order.visit_id,
                "total_amount": float(order.total_amount) if order.total_amount else 0,
                "status": order.status,
                "scheduled_date": order.scheduled_date.isoformat() if order.scheduled_date else None,
                "order_items": order_items,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None
            })
        
        return result
    
    @staticmethod
    def assign_delivery_man(db: Session, order_id: int, delivery_man_id: int) -> Dict:
        """Assign order to a delivery man."""
        from repositories.delivery_man_repository import DeliveryManRepository
        
        # Validate delivery man exists
        delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id)
        if not delivery_man:
            raise ValueError("Delivery Man not found")
        
        order = OrderRepository.assign_delivery_man(db, order_id, delivery_man_id)
        if not order:
            raise ValueError("Order not found")
        
        return {
            "id": order.id,
            "delivery_man_id": order.delivery_man_id,
            "delivery_man_name": delivery_man.name,
            "status": order.status
        }

