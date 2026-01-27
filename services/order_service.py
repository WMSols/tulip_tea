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
            from models.order import Order, OrderStatus
            orders = db.query(Order).filter(Order.shop_id == shop_id).all()
            # Note: Status is now an enum, so we need to compare with enum values
            unpaid_orders = [o for o in orders if o.status not in [OrderStatus.DELIVERED, OrderStatus.DISAPPROVED]]
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
        # Note: Legacy balance is no longer a separate column - it's already included
        # in outstanding_balance when the shop was created/updated
        outstanding = total_orders - total_payments
        return outstanding
    
    @staticmethod
    def create_order(db: Session, shop_id: int, order_booker_id: int,
                    order_items: List[Dict], distributor_id: int = None,
                    visit_id: int = None, scheduled_date: date = None,
                    order_resolution_type: str = None, subsidy_id: int = None) -> Dict:
        """
        Create a new order with credit limit validation and conditional order support.
        
        FLOW:
        1. Validates shop exists and is approved
        2. Validates order booker exists
        3. Calculates total order amount from items
        4. Handles conditional orders:
           - If credit insufficient and order_resolution_type='subsidy': applies subsidy
           - If credit insufficient and order_resolution_type='payment_before_delivery': allows order with payment requirement
           - If credit sufficient: normal order
        5. Validates credit limit (outstanding + new_order <= credit_limit)
        6. Creates order with status="pending"
        7. Creates order items
        8. Returns order data with items
        
        Args:
            db: Database session
            shop_id: Shop ID where order is placed
            order_booker_id: Order booker ID who placed the order
            order_items: List of order items [{"product_name": "...", "quantity": 10, "unit_price": 500.00}]
            distributor_id: Distributor ID (optional)
            visit_id: Visit ID where order was placed (optional)
            scheduled_date: Scheduled delivery date (optional)
            order_resolution_type: How to resolve if credit insufficient ('normal', 'subsidy', 'payment_before_delivery')
            subsidy_id: Subsidy ID to apply (required if order_resolution_type='subsidy')
        
        Returns:
            Dict: Order data with items
        
        Raises:
            ValueError: If validation fails or credit limit exceeded
        """
        from models.order import Order, OrderStatus
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
        from sqlalchemy import String, cast
        # Query credit requests and handle enum conversion safely
        credit_requests = CreditLimitRequestRepository.get_by_shop(db, shop_id)
        
        # Filter out soft-deleted requests and safely convert status
        active_requests = []
        for req in credit_requests:
            if req.deleted_at is None:
                # Safely get status value to avoid enum conversion issues
                try:
                    if hasattr(req.status, 'value'):
                        status_value = req.status.value
                    else:
                        status_value = str(req.status).lower()
                    # Create a simple object with status as string to avoid enum issues
                    class SimpleRequest:
                        def __init__(self, req, status_str):
                            self.id = req.id
                            self.shop_id = req.shop_id
                            self.status = status_str
                            self.deleted_at = req.deleted_at
                    active_requests.append(SimpleRequest(req, status_value))
                except Exception as e:
                    # If enum conversion fails, use string representation
                    status_value = str(req.status).lower()
                    class SimpleRequest:
                        def __init__(self, req, status_str):
                            self.id = req.id
                            self.shop_id = req.shop_id
                            self.status = status_str
                            self.deleted_at = req.deleted_at
                    active_requests.append(SimpleRequest(req, status_value))
        
        # If there are any active credit limit requests, check approval status
        if active_requests:
            # Check if there's at least one approved request
            # Status is now a string (from SimpleRequest wrapper)
            has_approved_request = any(
                str(req.status).lower() == 'approved'
                for req in active_requests
            )
            
            if not has_approved_request:
                # Check if there are any pending requests
                # Status is now a string (from SimpleRequest wrapper)
                has_pending_request = any(
                    str(req.status).lower() == 'pending'
                    for req in active_requests
                )
                
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
        
        # Initialize conditional order variables
        final_amount = total_amount  # Amount to use for credit limit check (will be discounted for subsidy)
        original_amount = None  # Only set for subsidy orders
        resolution_type = order_resolution_type or 'normal'
        print(f"[DEBUG OrderService.create_order] Initial: order_resolution_type={order_resolution_type}, subsidy_id={subsidy_id}, resolution_type={resolution_type}")
        
        # Validate credit limit using shop's outstanding_balance field
        credit_limit = Decimal(str(shop.credit_limit or 0))
        if credit_limit > 0:  # Only check if shop has a credit limit
            # Use shop's outstanding_balance field (maintained automatically)
            current_outstanding = Decimal(str(shop.outstanding_balance or 0))
            available_credit = credit_limit - current_outstanding
            
            # Check if credit is sufficient
            if current_outstanding + total_amount > credit_limit:
                # Credit insufficient - need conditional order resolution
                if not order_resolution_type:
                    raise ValueError(
                        f"Order amount (Rs. {total_amount}) exceeds available credit. "
                        f"Credit limit: Rs. {credit_limit}, Outstanding: Rs. {current_outstanding}, "
                        f"Available: Rs. {available_credit}. "
                        f"Please use one of: spot_payment (via daily collection), subsidy, or payment_before_delivery"
                    )
                
                if order_resolution_type == 'subsidy':
                    # Apply subsidy to reduce order amount
                    if not subsidy_id:
                        raise ValueError("subsidy_id is required when using subsidy resolution")
                    
                    from repositories.subsidy_repository import SubsidyRepository
                    subsidy = SubsidyRepository.get_by_id(db, subsidy_id, include_deleted=False)
                    if not subsidy:
                        raise ValueError(f"Subsidy with ID {subsidy_id} not found")
                    
                    if not subsidy.is_active:
                        raise ValueError(f"Subsidy with ID {subsidy_id} is not active")
                    
                    # Calculate discounted amount
                    original_amount = total_amount  # Store original before discount
                    discount_percentage = Decimal(str(subsidy.percentage))
                    final_amount = total_amount * (1 - discount_percentage / 100)  # Discounted amount
                    
                    # Check if discounted amount fits in credit
                    if current_outstanding + final_amount > credit_limit:
                        raise ValueError(
                            f"Even with {subsidy.percentage}% subsidy, order doesn't fit in credit. "
                            f"Original: Rs. {total_amount}, Discounted: Rs. {final_amount}, "
                            f"Available credit: Rs. {available_credit}"
                        )
                    
                    resolution_type = 'subsidy'
                
                elif order_resolution_type == 'payment_before_delivery':
                    # Allow order but require payment before delivery
                    # Credit limit check will use full amount (payment will be collected before delivery)
                    final_amount = total_amount
                    resolution_type = 'payment_before_delivery'
                
                elif order_resolution_type == 'normal':
                    # Normal order but credit insufficient - should not happen
                    raise ValueError(
                        f"Order amount (Rs. {total_amount}) exceeds available credit. "
                        f"Available: Rs. {available_credit}. "
                        f"Please use subsidy or payment_before_delivery resolution"
                    )
                else:
                    raise ValueError(f"Invalid order_resolution_type: {order_resolution_type}. Must be 'normal', 'subsidy', or 'payment_before_delivery'")
            else:
                # Credit is sufficient - but check if user selected subsidy or payment_before_delivery
                print(f"[DEBUG OrderService] Credit sufficient. order_resolution_type: {order_resolution_type}, subsidy_id: {subsidy_id}")
                if order_resolution_type == 'subsidy':
                    # User selected subsidy even though credit is sufficient - apply it anyway
                    print(f"[DEBUG OrderService] Applying subsidy even though credit is sufficient")
                    if not subsidy_id:
                        raise ValueError("subsidy_id is required when using subsidy resolution")
                    
                    from repositories.subsidy_repository import SubsidyRepository
                    subsidy = SubsidyRepository.get_by_id(db, subsidy_id, include_deleted=False)
                    if not subsidy:
                        raise ValueError(f"Subsidy with ID {subsidy_id} not found")
                    
                    if not subsidy.is_active:
                        raise ValueError(f"Subsidy with ID {subsidy_id} is not active")
                    
                    # Calculate discounted amount
                    original_amount = total_amount  # Store original before discount
                    discount_percentage = Decimal(str(subsidy.percentage))
                    final_amount = total_amount * (1 - discount_percentage / 100)  # Discounted amount
                    resolution_type = 'subsidy'
                    print(f"[DEBUG OrderService] Subsidy applied. Original: {total_amount}, Discounted: {final_amount}, resolution_type: {resolution_type}")
                elif order_resolution_type == 'payment_before_delivery':
                    # User selected payment before delivery even though credit is sufficient
                    final_amount = total_amount
                    resolution_type = 'payment_before_delivery'
                    print(f"[DEBUG OrderService] Payment before delivery selected. resolution_type: {resolution_type}")
                else:
                    # Credit is sufficient and no special resolution type - normal order
                    resolution_type = 'normal'
                    print(f"[DEBUG OrderService] Normal order (credit sufficient). resolution_type: {resolution_type}")
        
        # Create order with conditional order information
        # For subsidy orders: total_amount = discounted amount, original_amount = original amount
        # For other orders: total_amount = order amount, original_amount = NULL
        print(f"[DEBUG OrderService] Before creating order: resolution_type={resolution_type}, subsidy_id={subsidy_id}, original_amount={original_amount}, final_amount={final_amount}")
        order = OrderRepository.create(
            db=db,
            shop_id=shop_id,
            order_booker_id=order_booker_id,
            distributor_id=distributor_id,
            delivery_man_id=None,  # Assigned later by distributor
            visit_id=visit_id,
            total_amount=final_amount,  # Use final_amount (discounted for subsidy, original for others)
            status=OrderStatus.PENDING,
            scheduled_date=scheduled_date,
            order_resolution_type=resolution_type,
            subsidy_id=subsidy_id if resolution_type == 'subsidy' else None,
            original_amount=original_amount  # Only set for subsidy orders
        )
        print(f"[DEBUG OrderService] After creating order: order.id={order.id}, order.order_resolution_type={order.order_resolution_type}, order.subsidy_id={order.subsidy_id}, order.original_amount={order.original_amount}")
        
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
        # total_amount already contains the final amount (discounted for subsidy, original for others)
        amount_to_add = final_amount
        # Refresh shop to get latest data
        shop = ShopRepository.get_by_id(db, shop_id)
        if shop:
            current_outstanding = Decimal(str(shop.outstanding_balance or 0))
            new_outstanding = current_outstanding + amount_to_add
            
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
            "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
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
        
        OPTIMIZED: Uses UNION approach to allow efficient index usage.
        Each subquery can use its specific index, avoiding sequential scans.
        
        NEW LOGIC: Delivery men see ALL orders in their assigned zone, regardless of routes or shops.
        
        Includes:
        1. Orders explicitly assigned to the delivery man (delivery_man_id = delivery_man_id)
        2. Orders from all active shops in the delivery man's assigned zone
        3. Orders from order bookers in the same zone
        4. Orders that have deliveries for this delivery man (to allow completion of existing work)
        5. Includes orders with status: pending, delivered, disapproved
        """
        from models.order import Order
        from sqlalchemy import select
        from repositories.delivery_man_repository import DeliveryManRepository
        
        # Get delivery man to retrieve their zone_id
        delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id, include_deleted=False)
        if not delivery_man:
            print(f"[get_orders_by_delivery_man] Delivery man {delivery_man_id} not found")
            return []
        
        zone_id = delivery_man.zone_id
        print(f"[get_orders_by_delivery_man] Delivery man {delivery_man_id} is assigned to zone {zone_id}")
        
        # Status filter - used in all queries
        from models.order import OrderStatus
        status_filter = Order.status.in_([OrderStatus.PENDING, OrderStatus.DELIVERED, OrderStatus.DISAPPROVED])
        
        # Build separate queries for UNION (each can use its specific index)
        # Using UNION ALL for better performance, then getting distinct order IDs
        order_ids_set = set()
        
        # Query 1: Explicitly assigned orders (uses idx_orders_delivery_man_status_created)
        q1_ids = db.query(Order.id).filter(
            Order.delivery_man_id == delivery_man_id,
            status_filter
        ).all()
        order_ids_set.update([row[0] for row in q1_ids])
        print(f"[get_orders_by_delivery_man] Query 1 (explicitly assigned): {len(q1_ids)} orders")
        
        if zone_id:
            # Query 2: Orders from shops in zone (uses idx_orders_shop_status_created)
            # Use subquery to get shop IDs efficiently (uses idx_shops_zone_active)
            from models.shop import Shop
            shop_ids_subq = select(Shop.id).filter(
                Shop.zone_id == zone_id,
                Shop.deleted_at.is_(None),
                Shop.is_active == True
            )
            q2_ids = db.query(Order.id).filter(
                Order.shop_id.in_(shop_ids_subq),
                status_filter
            ).all()
            order_ids_set.update([row[0] for row in q2_ids])
            print(f"[get_orders_by_delivery_man] Query 2 (shops in zone): {len(q2_ids)} orders")
            
            # Query 3: Orders from order bookers in zone (uses idx_orders_order_booker_status_created)
            # Use subquery to get order booker IDs efficiently (uses idx_order_bookers_zone_active)
            from models.order_booker import OrderBooker
            order_booker_ids_subq = select(OrderBooker.id).filter(
                OrderBooker.zone_id == zone_id,
                OrderBooker.deleted_at.is_(None),
                OrderBooker.is_active == True
            )
            q3_ids = db.query(Order.id).filter(
                Order.order_booker_id.in_(order_booker_ids_subq),
                status_filter
            ).all()
            order_ids_set.update([row[0] for row in q3_ids])
            print(f"[get_orders_by_delivery_man] Query 3 (order bookers in zone): {len(q3_ids)} orders")
        
        # Query 4: Orders with deliveries (uses idx_deliveries_delivery_man_order)
        # Use subquery to get order IDs efficiently
        from models.delivery import Delivery
        delivery_order_ids_subq = select(Delivery.order_id).filter(
            Delivery.delivery_man_id == delivery_man_id,
            Delivery.deleted_at.is_(None)
        ).distinct()
        q4_ids = db.query(Order.id).filter(
            Order.id.in_(delivery_order_ids_subq),
            status_filter
        ).all()
        order_ids_set.update([row[0] for row in q4_ids])
        print(f"[get_orders_by_delivery_man] Query 4 (orders with deliveries): {len(q4_ids)} orders")
        
        # Convert set to list for IN clause
        order_ids = list(order_ids_set)
        
        print(f"[get_orders_by_delivery_man] Found {len(order_ids)} unique orders from all query conditions")
        
        if order_ids:
            # Fetch full order objects using the IDs (uses primary key index)
            # Order by created_at DESC (uses idx_orders_created_at_desc or idx_orders_status_created)
            orders = db.query(Order).filter(
                Order.id.in_(order_ids)
            ).order_by(Order.created_at.desc()).all()
        else:
            orders = []
            print(f"[get_orders_by_delivery_man] No orders found")
        
        if orders:
            # Debug: Show order details
            order_details = [(o.id, o.shop_id, o.status.value if hasattr(o.status, 'value') else str(o.status), o.delivery_man_id, getattr(o, 'order_resolution_type', None)) for o in orders]
            print(f"[get_orders_by_delivery_man] Order details: {order_details}")
        
        return OrderService._format_orders(db, orders)
    
    @staticmethod
    def get_orders_by_visit(db: Session, visit_id: int) -> List[Dict]:
        """Get all orders linked to a visit."""
        orders = OrderRepository.get_by_visit(db, visit_id)
        return OrderService._format_orders(db, orders)
    
    @staticmethod
    def _format_orders(db: Session, orders: List) -> List[Dict]:
        """Format orders with related data. Optimized with batch loading to avoid N+1 queries."""
        if not orders:
            return []
        
        from models.shop import Shop
        from models.order_booker import OrderBooker
        from models.delivery_man import DeliveryMan
        from models.order_item import OrderItem
        from models.subsidy import Subsidy
        
        # Batch load all related data in single queries
        order_ids = [order.id for order in orders]
        shop_ids = list(set([order.shop_id for order in orders if order.shop_id]))
        order_booker_ids = list(set([order.order_booker_id for order in orders if order.order_booker_id]))
        delivery_man_ids = list(set([order.delivery_man_id for order in orders if order.delivery_man_id]))
        subsidy_ids = list(set([order.subsidy_id for order in orders if hasattr(order, 'subsidy_id') and order.subsidy_id]))
        
        # Batch load shops
        shops = {}
        if shop_ids:
            shops_query = db.query(Shop).filter(Shop.id.in_(shop_ids)).all()
            shops = {shop.id: shop for shop in shops_query}
        
        # Batch load order bookers
        order_bookers = {}
        if order_booker_ids:
            ob_query = db.query(OrderBooker).filter(OrderBooker.id.in_(order_booker_ids)).all()
            order_bookers = {ob.id: ob for ob in ob_query}
        
        # Batch load delivery men
        delivery_men = {}
        if delivery_man_ids:
            dm_query = db.query(DeliveryMan).filter(DeliveryMan.id.in_(delivery_man_ids)).all()
            delivery_men = {dm.id: dm for dm in dm_query}
        
        # Batch load order items
        items_by_order = {}
        if order_ids:
            items_query = db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).all()
            for item in items_query:
                if item.order_id not in items_by_order:
                    items_by_order[item.order_id] = []
                items_by_order[item.order_id].append(item)
        
        # Batch load subsidies
        subsidies = {}
        if subsidy_ids:
            subsidy_query = db.query(Subsidy).filter(Subsidy.id.in_(subsidy_ids), Subsidy.deleted_at.is_(None)).all()
            subsidies = {sub.id: sub for sub in subsidy_query}
        
        result = []
        for order in orders:
            # Get related data from batch-loaded dictionaries
            shop = shops.get(order.shop_id) if order.shop_id else None
            order_booker = order_bookers.get(order.order_booker_id) if order.order_booker_id else None
            delivery_man = delivery_men.get(order.delivery_man_id) if order.delivery_man_id else None
            
            # Get order items from batch-loaded data
            items = items_by_order.get(order.id, [])
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
            
            # Get subsidy information from batch-loaded data
            subsidy_info = None
            order_resolution_type = getattr(order, 'order_resolution_type', None)
            subsidy_id = getattr(order, 'subsidy_id', None)
            
            # Debug logging
            print(f"[DEBUG _format_orders] Order {order.id}: order_resolution_type = {order_resolution_type}, type = {type(order_resolution_type)}")
            print(f"[DEBUG _format_orders] Order {order.id}: subsidy_id = {subsidy_id}")
            
            if order_resolution_type == 'subsidy' and subsidy_id:
                subsidy = subsidies.get(subsidy_id)
                if subsidy:
                    subsidy_info = {
                        "id": subsidy.id,
                        "name": subsidy.name,
                        "percentage": float(subsidy.percentage) if subsidy.percentage else 0
                    }
                    print(f"[DEBUG _format_orders] Order {order.id}: Loaded subsidy info: {subsidy_info}")
            
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
                "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
                "scheduled_date": order.scheduled_date.isoformat() if order.scheduled_date else None,
                "order_items": order_items,
                # GPS removed from orders - stored in shop_visits instead
                # "delivery_gps_lat": float(order.delivery_gps_lat) if order.delivery_gps_lat else None,
                # "delivery_gps_lng": float(order.delivery_gps_lng) if order.delivery_gps_lng else None,
                "delivery_remarks": order.delivery_remarks,
                "delivery_images": delivery_images_list,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                # Conditional order information
                "order_resolution_type": order_resolution_type,
                "subsidy_id": subsidy_id,
                "subsidy_info": subsidy_info,
                "original_amount": float(order.original_amount) if hasattr(order, 'original_amount') and order.original_amount else None,
                "payment_collected_before_delivery": getattr(order, 'payment_collected_before_delivery', False),
                "payment_collected_amount": float(order.payment_collected_amount) if hasattr(order, 'payment_collected_amount') and order.payment_collected_amount else None,
                "payment_collected_at": order.payment_collected_at.isoformat() if hasattr(order, 'payment_collected_at') and order.payment_collected_at else None
            })
            
            # Debug: Log what we're returning
            print(f"[DEBUG _format_orders] Order {order.id}: Returning order_resolution_type = {result[-1]['order_resolution_type']}")
        
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
            "status": order.status.value if hasattr(order.status, 'value') else str(order.status)
        }

