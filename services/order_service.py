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
from repositories.product_repository import ProductRepository
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
        
        # Outstanding = Orders - Payments
        # Note: outstanding_balance column already includes any initial legacy balance
        outstanding = total_orders - total_payments
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
        
        # Refresh shop to ensure we have the latest outstanding_balance
        # This is critical after daily collections which update outstanding_balance instantly
        db.refresh(shop)
        
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
        
        # Process order items: fetch prices from product table if product_id is provided
        processed_items = []
        for item in order_items:
            product_id = item.get('product_id')
            quantity = int(item.get('quantity', 0))
            unit_price = item.get('unit_price')
            product_name = item.get('product_name', '')
            
            # If product_id is provided, fetch product and use its price
            if product_id:
                product = ProductRepository.get_by_id(db, product_id)
                if not product:
                    raise ValueError(f"Product with ID {product_id} not found")
                if not product.is_active:
                    raise ValueError(f"Product with ID {product_id} is not active")
                
                # Use product price if available, otherwise use provided unit_price
                # Handle Decimal type from database
                product_price = float(product.price) if product.price is not None else None
                if product_price and product_price > 0:
                    unit_price = product_price
                elif not unit_price or unit_price <= 0:
                    raise ValueError(f"Product '{product.name}' (ID: {product_id}) does not have a price set. Please set the price in the product table.")
                
                # Use product name if not provided
                if not product_name:
                    product_name = product.name
            elif not unit_price or unit_price <= 0:
                # No product_id and no valid unit_price
                raise ValueError("Either product_id must be provided (to fetch price from product table) or unit_price must be provided")
            
            processed_items.append({
                'product_id': product_id,
                'product_name': product_name,
                'quantity': quantity,
                'unit_price': float(unit_price)
            })
        
        # Calculate total amount from processed items
        total_amount = Decimal('0')
        for item in processed_items:
            quantity = item['quantity']
            unit_price = Decimal(str(item['unit_price']))
            item_total = quantity * unit_price
            total_amount += item_total
        
        if total_amount <= 0:
            raise ValueError("Order total amount must be greater than 0")
        
        # Explicitly refresh shop to get the latest outstanding_balance
        # This ensures we get the most recent value after any updates (e.g., from daily collections)
        db.refresh(shop)
        
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
        
        # Create order items using processed items
        created_items = []
        for item in processed_items:
            quantity = item['quantity']
            unit_price = Decimal(str(item['unit_price']))
            total_price = quantity * unit_price
            
            order_item = OrderItemRepository.create(
                db=db,
                order_id=order.id,
                product_name=item['product_name'],
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
        """
        Get all orders for a delivery man.
        
        NEW LOGIC: Delivery men see ALL orders in their assigned zone, regardless of routes or shops.
        
        Includes:
        1. Orders explicitly assigned to the delivery man (delivery_man_id = delivery_man_id)
        2. Orders from all active shops in the delivery man's assigned zone
        3. Orders that have deliveries for this delivery man (to allow completion of existing work)
        4. Includes orders with status: pending, confirmed, delivered, cancelled
        """
        from models.order import Order
        from sqlalchemy import or_, and_
        from repositories.delivery_man_repository import DeliveryManRepository
        
        # Get delivery man to retrieve their zone_id
        delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id, include_deleted=False)
        if not delivery_man:
            print(f"[get_orders_by_delivery_man] Delivery man {delivery_man_id} not found")
            return []
        
        zone_id = delivery_man.zone_id
        print(f"[get_orders_by_delivery_man] Delivery man {delivery_man_id} is assigned to zone {zone_id}")
        
        # Get all active shops in the delivery man's zone
        shop_ids = set()
        if zone_id:
            from models.shop import Shop
            # Query all active shops in the delivery man's zone
            shops_in_zone = db.query(Shop).filter(
                Shop.zone_id == zone_id,
                Shop.deleted_at.is_(None),  # Exclude soft-deleted shops
                Shop.is_active == True  # Only include active shops
            ).all()
            shop_ids = {shop.id for shop in shops_in_zone}
            print(f"[get_orders_by_delivery_man] Found {len(shop_ids)} active shops in zone {zone_id}: {list(shop_ids)}")
            if shop_ids:
                # Debug: Show which shops were found
                shop_details = [(s.id, s.name, s.is_active) for s in shops_in_zone]
                print(f"[get_orders_by_delivery_man] Shop details: {shop_details}")
        else:
            print(f"[get_orders_by_delivery_man] Delivery man {delivery_man_id} has no zone assigned")
        
        # Build query: orders explicitly assigned OR orders from shops in zone OR orders with deliveries
        # Include all order statuses (pending, confirmed, delivered, cancelled)
        conditions = []
        
        # Condition 1: Orders explicitly assigned to this delivery man
        conditions.append(Order.delivery_man_id == delivery_man_id)
        
        # Condition 2: Orders from all active shops in the delivery man's zone
        if shop_ids:
            conditions.append(Order.shop_id.in_(shop_ids))
            print(f"[get_orders_by_delivery_man] Including orders from {len(shop_ids)} shops in zone {zone_id}")
        
        # Condition 3: Orders that have deliveries for this delivery man
        # This ensures delivery men can see orders they've already worked on, even if not explicitly assigned
        from models.delivery import Delivery
        delivery_order_ids = db.query(Delivery.order_id).filter(
            Delivery.delivery_man_id == delivery_man_id,
            Delivery.deleted_at.is_(None)
        ).distinct().all()
        delivery_order_ids_list = [row[0] for row in delivery_order_ids]
        if delivery_order_ids_list:
            conditions.append(Order.id.in_(delivery_order_ids_list))
            print(f"[get_orders_by_delivery_man] Found {len(delivery_order_ids_list)} orders with deliveries for this delivery man")
        
        # Include all order statuses - frontend will filter them appropriately
        # Orders tab shows: pending, confirmed
        # Deliveries tab shows: confirmed, delivered, cancelled
        status_filter = Order.status.in_(['pending', 'confirmed', 'delivered', 'cancelled'])
        
        # Query orders matching any condition and status filter
        if len(conditions) > 0:
            # Use or_() to match any condition, and and_() to combine with status filter
            if len(conditions) == 1:
                # Only one condition - combine with status filter directly
                print(f"[get_orders_by_delivery_man] Querying with 1 condition: explicitly assigned orders")
                orders = db.query(Order).filter(
                    and_(
                        conditions[0],
                        status_filter
                    )
                ).order_by(Order.created_at.desc()).all()
            else:
                # Multiple conditions - use or_() to match any
                print(f"[get_orders_by_delivery_man] Querying with {len(conditions)} conditions: explicitly assigned OR shops in zone OR orders with deliveries")
                orders = db.query(Order).filter(
                    and_(
                        or_(*conditions),
                        status_filter
                    )
                ).order_by(Order.created_at.desc()).all()
            print(f"[get_orders_by_delivery_man] Found {len(orders)} orders")
            if orders:
                # Debug: Show order details
                order_details = [(o.id, o.shop_id, o.status, o.delivery_man_id) for o in orders]
                print(f"[get_orders_by_delivery_man] Order details: {order_details}")
        else:
            # No conditions (shouldn't happen, but handle gracefully)
            orders = []
            print(f"[get_orders_by_delivery_man] No conditions to query, returning empty list")
        
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
            
            # Parse delivery_images JSON string to list
            import json
            delivery_images_list = []
            if order.delivery_images:
                try:
                    # delivery_images is stored as JSON string in TEXT column
                    if isinstance(order.delivery_images, str):
                        delivery_images_list = json.loads(order.delivery_images)
                    elif isinstance(order.delivery_images, list):
                        # If already a list (shouldn't happen, but handle it)
                        delivery_images_list = order.delivery_images
                except Exception as e:
                    print(f"Error parsing delivery_images: {e}")
                    delivery_images_list = []
            
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
                # GPS removed from orders - stored in shop_visits instead
                # "delivery_gps_lat": float(order.delivery_gps_lat) if order.delivery_gps_lat else None,
                # "delivery_gps_lng": float(order.delivery_gps_lng) if order.delivery_gps_lng else None,
                "delivery_remarks": order.delivery_remarks,
                "delivery_images": delivery_images_list,
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

