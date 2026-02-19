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
            unpaid_orders = [o for o in orders if o.status not in [OrderStatus.DELIVERED, OrderStatus.PARTIAL_DELIVERED, OrderStatus.DISAPPROVED]]
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
                    final_total_amount: Decimal = None,
                    order_resolution_type: str = None, subsidy_id: int = None,
                    auto_commit: bool = True) -> Dict:
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
            raise ValueError(f"Shop is not approved. Current status: {shop.registration_status}")
        
        # Validate credit limit approval
        # If shop has a credit_limit > 0, it means there was an approved request
        # Only check active_requests if credit_limit == 0 (new shop with no approved limit)
        credit_limit = Decimal(str(shop.credit_limit or 0))
        
        if credit_limit == 0:
            # Shop has no approved credit limit - check if there's an approved request
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
                        raise ValueError("Credit limit request is pending approval. Wait for distributor approval")
                    else:
                        # No approved request found - could be rejected or never created
                        raise ValueError("Credit limit request not approved. Contact distributor")
            else:
                # No credit limit requests at all - shop cannot place orders
                raise ValueError("Shop has no credit limit. Please request credit limit approval first.")
        # If credit_limit > 0, shop has an approved limit - allow orders (validation will happen later based on amount)
        
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
            
            # If product_id is provided, fetch product and use its price and name
            if product_id:
                product = ProductRepository.get_by_id(db, product_id)
                if not product:
                    raise ValueError(f"Product not found")
                if not product.is_active:
                    raise ValueError(f"Product is not active")
                
                # Use product price if available, otherwise use provided unit_price
                # Handle Decimal type from database
                product_price = float(product.price) if product.price is not None else None
                if product_price and product_price > 0:
                    unit_price = product_price
                elif not unit_price or unit_price <= 0:
                    raise ValueError(f"Product '{product.name}' has no price set")
                
                # Always use product name from database when product_id is provided
                # This ensures consistency and prevents incorrect names (e.g., product code) from being stored
                product_name = product.name
            elif not unit_price or unit_price <= 0:
                # No product_id and no valid unit_price
                raise ValueError("Provide product_id or unit_price")
            
            processed_items.append({
                'product_id': product_id,
                'product_name': product_name,
                'quantity': quantity,
                'unit_price': float(unit_price)
            })
        
        # Calculate total amount from processed items (this is the calculated_total_amount)
        calculated_total_amount = Decimal('0')
        for item in processed_items:
            quantity = item['quantity']
            unit_price = Decimal(str(item['unit_price']))
            item_total = quantity * unit_price
            calculated_total_amount += item_total
        
        if calculated_total_amount <= 0:
            raise ValueError("Order amount must be greater than 0")
        
        # Determine final_total_amount
        # If provided, use it; otherwise use calculated_total_amount
        if final_total_amount is not None:
            final_total_amount_decimal = Decimal(str(final_total_amount))
            # Validate final_total_amount
            if final_total_amount_decimal <= 0:
                raise ValueError("Final amount must be greater than 0")
            if final_total_amount_decimal > calculated_total_amount:
                raise ValueError(f"Final amount (Rs. {final_total_amount_decimal}) cannot exceed order amount (Rs. {calculated_total_amount})")
        else:
            final_total_amount_decimal = calculated_total_amount
        
        # Determine subsidy_status
        # If final_total_amount < calculated_total_amount, requires approval
        if final_total_amount_decimal < calculated_total_amount:
            subsidy_status = 'pending_approval'
        else:
            subsidy_status = 'none'
        
        # Explicitly refresh shop to get the latest outstanding_balance
        # This ensures we get the most recent value after any updates (e.g., from daily collections)
        db.refresh(shop)
        
        # Initialize variables for backward compatibility (legacy subsidy system)
        final_amount = final_total_amount_decimal  # Amount to use for credit limit check
        original_amount = calculated_total_amount  # Store calculated total (repurposed original_amount)
        resolution_type = order_resolution_type or 'normal'
        
        # Legacy subsidy system handling (for backward compatibility)
        # If order_resolution_type is provided, use legacy system
        if order_resolution_type:
            print(f"[DEBUG OrderService.create_order] Using legacy subsidy system: order_resolution_type={order_resolution_type}, subsidy_id={subsidy_id}")
        
        # Validate credit limit using shop's outstanding_balance field
        # credit_limit is already defined above (line ~130) - reuse it
        if credit_limit > 0:  # Only check if shop has a credit limit
            # Use shop's outstanding_balance field (maintained automatically)
            current_outstanding = Decimal(str(shop.outstanding_balance or 0))
            # Available credit cannot be negative - if outstanding > credit_limit, available = 0
            available_credit = max(Decimal('0'), credit_limit - current_outstanding)
            
            # Step 1: Apply subsidy if provided (can be combined with payment_before_delivery)
            subsidized_amount = final_total_amount_decimal
            subsidy_applied = False
            subsidy_percentage = None
            if subsidy_id:
                from repositories.subsidy_repository import SubsidyRepository
                subsidy = SubsidyRepository.get_by_id(db, subsidy_id, include_deleted=False)
                if not subsidy:
                    raise ValueError(f"Subsidy not found")
                
                if not subsidy.is_active:
                    raise ValueError(f"Subsidy is not active")
                
                # Calculate discounted amount
                subsidy_percentage = Decimal(str(subsidy.percentage))
                subsidized_amount = calculated_total_amount * (1 - subsidy_percentage / 100)  # Discounted amount
                subsidy_applied = True
                print(f"[DEBUG OrderService] Subsidy applied: Original={calculated_total_amount}, Discounted={subsidized_amount}, Percentage={subsidy_percentage}%")
            
            # Step 2: Determine final order amount (after subsidy if applied)
            # Final amount is the subsidized amount if subsidy was applied, otherwise use final_total_amount_decimal
            final_order_amount = subsidized_amount if subsidy_applied else final_total_amount_decimal
            
            # Step 3: CRITICAL VALIDATION - Order amount must NEVER exceed credit limit
            # This applies to ALL order types: normal, subsidized, payment_before_delivery
            # Formula: current_outstanding + final_order_amount <= credit_limit
            # Allow equality: if order amount equals available credit, it's allowed
            new_outstanding_after_order = current_outstanding + final_order_amount
            
            if new_outstanding_after_order > credit_limit:
                # Order exceeds credit limit - REJECT with clear error message
                if subsidy_applied:
                    subsidy_pct_str = f"{subsidy_percentage}%" if subsidy_percentage else "applied"
                    raise ValueError(
                        f"Order amount exceeds credit limit. "
                        f"Original: Rs. {calculated_total_amount}, After {subsidy_pct_str} subsidy: Rs. {subsidized_amount}. "
                        f"Credit limit: Rs. {credit_limit}, Current outstanding: Rs. {current_outstanding}, "
                        f"Available credit: Rs. {available_credit}. "
                        f"Maximum order amount allowed: Rs. {available_credit}. "
                        f"Please reduce order quantity or items to stay within credit limit."
                    )
                else:
                    raise ValueError(
                        f"Order amount (Rs. {final_order_amount}) exceeds credit limit (Rs. {credit_limit}). "
                        f"Current outstanding: Rs. {current_outstanding}, Available credit: Rs. {available_credit}. "
                        f"Maximum order amount allowed: Rs. {available_credit}. "
                        f"Please reduce order quantity or items, apply subsidy, or request credit limit increase."
                    )
            
            # Step 4: Credit is sufficient - validate and set resolution type
            credit_sufficient = (new_outstanding_after_order <= credit_limit)
            
            if not credit_sufficient:
                # This should not happen due to check above, but keep for safety
                raise ValueError(
                    f"Order amount (Rs. {final_order_amount}) exceeds available credit (Rs. {available_credit}). "
                    f"Credit limit: Rs. {credit_limit}, Outstanding: Rs. {current_outstanding}. "
                    f"Maximum order amount: Rs. {available_credit}"
                )
            
            # Credit is sufficient - set final amount and resolution type
            final_total_amount_decimal = final_order_amount
            
            # Determine resolution type based on order_resolution_type and subsidy
            if order_resolution_type == 'payment_before_delivery':
                # Payment before delivery is allowed if credit is sufficient
                # (Shop wants to pay before delivery even though credit is available)
                resolution_type = 'payment_before_delivery'
                if subsidy_applied:
                    print(f"[DEBUG OrderService] Payment before delivery with subsidy: Amount={final_total_amount_decimal}")
            elif subsidy_applied or order_resolution_type == 'subsidy':
                # Validate subsidy_id is provided if subsidy is selected
                if order_resolution_type == 'subsidy' and not subsidy_id:
                    raise ValueError("Subsidy ID is required when using subsidy option")
                resolution_type = 'subsidy'
                print(f"[DEBUG OrderService] Subsidy applied: Original={calculated_total_amount}, Discounted={subsidized_amount}, Resolution={resolution_type}")
            else:
                resolution_type = 'normal'
                print(f"[DEBUG OrderService] Normal order: Amount={final_total_amount_decimal}, Resolution={resolution_type}")
        
        # Create order with new subsidy approval system
        print(f"[DEBUG OrderService] Creating order: calculated_total={calculated_total_amount}, final_total={final_total_amount_decimal}, subsidy_status={subsidy_status}")
        order = OrderRepository.create(
            db=db,
            shop_id=shop_id,
            order_booker_id=order_booker_id,
            distributor_id=distributor_id,
            delivery_man_id=None,  # Assigned later by distributor
            visit_id=visit_id,
            total_amount=final_total_amount_decimal,  # Final amount (after order booker edits)
            status=OrderStatus.PENDING,
            scheduled_date=scheduled_date,
            original_amount=calculated_total_amount,  # Calculated total (sum of items)
            final_total_amount=final_total_amount_decimal,  # Final amount (explicit column)
            subsidy_status=subsidy_status,  # 'none' or 'pending_approval'
            # Legacy fields (for backward compatibility)
            order_resolution_type=resolution_type if order_resolution_type else None,
            subsidy_id=subsidy_id if subsidy_id else None,  # Store subsidy_id if provided, regardless of resolution_type
            auto_commit=auto_commit
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
        # Only update if order doesn't require approval (subsidy_status = 'none')
        # If pending_approval, outstanding balance will be updated after approval
        if subsidy_status == 'none':
            amount_to_add = final_total_amount_decimal
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
        else:
            print(f"[DEBUG OrderService] Order {order.id} requires approval (subsidy_status={subsidy_status}). Outstanding balance will be updated after approval.")
        
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
            "created_at": order.created_at.isoformat() if order.created_at else None,
            # New subsidy approval fields
            "calculated_total_amount": float(calculated_total_amount) if calculated_total_amount else None,
            "final_total_amount": float(final_total_amount_decimal) if final_total_amount_decimal else None,
            "subsidy_status": subsidy_status,
            "subsidy_approved_by": None,
            "subsidy_approved_at": None,
            "subsidy_rejection_reason": None,
            # Legacy fields (for backward compatibility)
            "original_amount": float(calculated_total_amount) if calculated_total_amount else None,
            "order_resolution_type": resolution_type if order_resolution_type else None,
            "subsidy_id": subsidy_id if resolution_type == 'subsidy' else None
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
        5. Includes orders with status: pending, delivered, partial_delivered, disapproved
        6. Excludes orders with subsidy_status: pending_approval, rejected (cannot be assigned)
        """
        from models.order import Order
        from sqlalchemy import select, or_
        from repositories.delivery_man_repository import DeliveryManRepository
        
        # Get delivery man to retrieve their zone_id and distributor_id
        delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id, include_deleted=False)
        if not delivery_man:
            print(f"[get_orders_by_delivery_man] Delivery man {delivery_man_id} not found")
            return []
        
        zone_id = delivery_man.zone_id
        distributor_id = delivery_man.distributor_id
        print(f"[get_orders_by_delivery_man] Delivery man {delivery_man_id} is assigned to zone {zone_id}, distributor {distributor_id}")
        
        # Status filter - used in all queries
        from models.order import OrderStatus
        status_filter = Order.status.in_([OrderStatus.PENDING, OrderStatus.DELIVERED, OrderStatus.PARTIAL_DELIVERED, OrderStatus.DISAPPROVED])
        
        # Distributor filter - CRITICAL: Only show orders from this delivery man's distributor
        distributor_filter = Order.distributor_id == distributor_id
        
        # Build separate queries for UNION (each can use its specific index)
        # Using UNION ALL for better performance, then getting distinct order IDs
        order_ids_set = set()
        
        # Query 1: Explicitly assigned orders (uses idx_orders_delivery_man_status_created)
        # Must belong to the same distributor
        q1_ids = db.query(Order.id).filter(
            Order.delivery_man_id == delivery_man_id,
            distributor_filter,  # Filter by distributor
            status_filter
        ).all()
        order_ids_set.update([row[0] for row in q1_ids])
        print(f"[get_orders_by_delivery_man] Query 1 (explicitly assigned): {len(q1_ids)} orders")
        
        # Query 2 & 3: Orders from shops and order bookers
        # Handle both cases: with zone_id and without zone_id (null)
        from models.shop import Shop
        from models.order_booker import OrderBooker as OB
        from models.order_booker import OrderBooker
        
        if zone_id:
            # Query 2: Orders from shops in zone (uses idx_orders_shop_status_created)
            # Use subquery to get shop IDs efficiently (uses idx_shops_zone_active)
            # IMPORTANT: Filter shops by their order booker's distributor_id to ensure data isolation
            # Shops don't have direct distributor_id, but are linked through order_bookers
            # Join shops with order_bookers to filter by distributor
            # Check both assigned_to_order_booker and created_by_order_booker
            shop_ids_subq = select(Shop.id).join(
                OB, 
                or_(
                    Shop.assigned_to_order_booker == OB.id,
                    Shop.created_by_order_booker == OB.id
                )
            ).filter(
                Shop.zone_id == zone_id,
                OB.distributor_id == distributor_id,  # Filter by distributor through order booker
                Shop.deleted_at.is_(None),
                Shop.is_active == True,
                OB.deleted_at.is_(None),
                OB.is_active == True
            ).distinct()
            q2_ids = db.query(Order.id).filter(
                Order.shop_id.in_(shop_ids_subq),
                distributor_filter,  # Double-check order belongs to distributor
                status_filter
            ).all()
            order_ids_set.update([row[0] for row in q2_ids])
            print(f"[get_orders_by_delivery_man] Query 2 (shops in zone {zone_id}, distributor {distributor_id}): {len(q2_ids)} orders")
            
            # Query 3: Orders from order bookers in zone (uses idx_orders_order_booker_status_created)
            # Use subquery to get order booker IDs efficiently (uses idx_order_bookers_zone_active)
            # IMPORTANT: Filter order bookers by distributor_id to ensure data isolation
            order_booker_ids_subq = select(OrderBooker.id).filter(
                OrderBooker.zone_id == zone_id,
                OrderBooker.distributor_id == distributor_id,  # Filter by distributor
                OrderBooker.deleted_at.is_(None),
                OrderBooker.is_active == True
            )
            q3_ids = db.query(Order.id).filter(
                Order.order_booker_id.in_(order_booker_ids_subq),
                distributor_filter,  # Double-check order belongs to distributor
                status_filter
            ).all()
            order_ids_set.update([row[0] for row in q3_ids])
            print(f"[get_orders_by_delivery_man] Query 3 (order bookers in zone {zone_id}, distributor {distributor_id}): {len(q3_ids)} orders")
            
            # Query 2a & 3a: Fallback queries to catch orders from same distributor across zones
            # This ensures delivery men see all orders from their distributor, even if shop/order booker is in different zone
            # This is important for operational flexibility within a distributor's domain
            print(f"[get_orders_by_delivery_man] Running fallback queries for cross-zone orders (distributor {distributor_id})")
            
            # Query 2a: Direct orders by distributor_id (catches all orders from distributor, regardless of zone)
            q2a_ids = db.query(Order.id).filter(
                distributor_filter,  # Filter by distributor
                status_filter
            ).all()
            order_ids_set.update([row[0] for row in q2a_ids])
            print(f"[get_orders_by_delivery_man] Query 2a (fallback: direct orders, distributor {distributor_id}): {len(q2a_ids)} orders")
            
            # Query 3a: Orders from order bookers of same distributor (no zone filter)
            # This catches orders from order bookers in other zones of the same distributor
            order_booker_ids_subq_fallback = select(OrderBooker.id).filter(
                OrderBooker.distributor_id == distributor_id,  # Filter by distributor only (no zone)
                OrderBooker.deleted_at.is_(None),
                OrderBooker.is_active == True
            )
            q3a_ids = db.query(Order.id).filter(
                Order.order_booker_id.in_(order_booker_ids_subq_fallback),
                distributor_filter,  # Double-check order belongs to distributor
                status_filter
            ).all()
            order_ids_set.update([row[0] for row in q3a_ids])
            print(f"[get_orders_by_delivery_man] Query 3a (fallback: order bookers, distributor {distributor_id}): {len(q3a_ids)} orders")
        else:
            # Fallback: When delivery man has no zone assigned, show orders from order bookers of same distributor
            # This ensures delivery men can still see orders even if not assigned to a zone yet
            print(f"[get_orders_by_delivery_man] Delivery man has no zone assigned - using distributor-only filtering")
            
            # Query 2a (no zone): Direct orders by distributor_id (simplest and most efficient)
            # Since orders have distributor_id, we can directly query them
            q2a_ids = db.query(Order.id).filter(
                distributor_filter,  # Filter by distributor
                status_filter
            ).all()
            order_ids_set.update([row[0] for row in q2a_ids])
            print(f"[get_orders_by_delivery_man] Query 2a (direct orders, no zone, distributor {distributor_id}): {len(q2a_ids)} orders")
            
            # Query 2b (no zone): Orders from shops linked to order bookers of same distributor
            # Join shops with order_bookers to filter by distributor (no zone filter)
            # This is a secondary check to ensure we catch all orders
            shop_ids_subq = select(Shop.id).join(
                OB, 
                or_(
                    Shop.assigned_to_order_booker == OB.id,
                    Shop.created_by_order_booker == OB.id
                )
            ).filter(
                OB.distributor_id == distributor_id,  # Filter by distributor through order booker
                Shop.deleted_at.is_(None),
                Shop.is_active == True,
                OB.deleted_at.is_(None),
                OB.is_active == True
            ).distinct()
            q2b_ids = db.query(Order.id).filter(
                Order.shop_id.in_(shop_ids_subq),
                distributor_filter,  # Double-check order belongs to distributor
                status_filter
            ).all()
            order_ids_set.update([row[0] for row in q2b_ids])
            print(f"[get_orders_by_delivery_man] Query 2b (shops, no zone, distributor {distributor_id}): {len(q2b_ids)} orders")
            
            # Query 3 (no zone): Orders from order bookers of same distributor (no zone filter)
            order_booker_ids_subq = select(OrderBooker.id).filter(
                OrderBooker.distributor_id == distributor_id,  # Filter by distributor only
                OrderBooker.deleted_at.is_(None),
                OrderBooker.is_active == True
            )
            q3_ids = db.query(Order.id).filter(
                Order.order_booker_id.in_(order_booker_ids_subq),
                distributor_filter,  # Double-check order belongs to distributor
                status_filter
            ).all()
            order_ids_set.update([row[0] for row in q3_ids])
            print(f"[get_orders_by_delivery_man] Query 3 (order bookers, no zone, distributor {distributor_id}): {len(q3_ids)} orders")
        
        # Query 4: Orders with deliveries (uses idx_deliveries_delivery_man_order)
        # Use subquery to get order IDs efficiently
        # Must belong to the same distributor
        from models.delivery import Delivery
        delivery_order_ids_subq = select(Delivery.order_id).filter(
            Delivery.delivery_man_id == delivery_man_id,
            Delivery.deleted_at.is_(None)
        ).distinct()
        q4_ids = db.query(Order.id).filter(
            Order.id.in_(delivery_order_ids_subq),
            distributor_filter,  # Filter by distributor
            status_filter
        ).all()
        order_ids_set.update([row[0] for row in q4_ids])
        print(f"[get_orders_by_delivery_man] Query 4 (orders with deliveries): {len(q4_ids)} orders")
        
        # Convert set to list for IN clause
        order_ids = list(order_ids_set)
        
        print(f"[get_orders_by_delivery_man] Found {len(order_ids)} unique orders from all query conditions (distributor {distributor_id})")
        
        if order_ids:
            # Fetch full order objects using the IDs (uses primary key index)
            # Filter out orders with pending_approval or rejected subsidy_status
            # Order by created_at DESC (uses idx_orders_created_at_desc or idx_orders_status_created)
            # Final distributor check to ensure data isolation
            orders = db.query(Order).filter(
                Order.id.in_(order_ids),
                distributor_filter,  # Final distributor check
                # Exclude orders that cannot be assigned (pending approval or rejected)
                or_(
                    Order.subsidy_status.is_(None),
                    Order.subsidy_status == 'none',
                    Order.subsidy_status == 'approved'
                )
            ).order_by(Order.created_at.desc()).all()
        else:
            orders = []
            print(f"[get_orders_by_delivery_man] No orders found")
        
        if orders:
            # Debug: Show order details
            try:
                order_details = []
                for o in orders:
                    try:
                        status_str = o.status.value if hasattr(o.status, 'value') else str(o.status) if o.status else 'PENDING'
                        order_details.append((o.id, o.shop_id, status_str, o.delivery_man_id, getattr(o, 'order_resolution_type', None)))
                    except Exception as e:
                        print(f"[get_orders_by_delivery_man] Error processing order {o.id}: {e}")
                        order_details.append((o.id, o.shop_id, 'PENDING', o.delivery_man_id, getattr(o, 'order_resolution_type', None)))
                print(f"[get_orders_by_delivery_man] Order details: {order_details}")
            except Exception as e:
                print(f"[get_orders_by_delivery_man] Error in debug logging: {e}")
        
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
        
        # Helper function to safely format datetime to ISO string
        def safe_isoformat(dt):
            """Safely convert datetime to ISO format string, returning None if dt is None."""
            if dt is None:
                return None
            try:
                return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
            except:
                return None
        
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
                "status": (order.status.value if hasattr(order.status, 'value') else str(order.status)) if order.status else 'PENDING',
                "scheduled_date": order.scheduled_date.isoformat() if order.scheduled_date else None,
                "order_items": order_items,
                # GPS removed from orders - stored in shop_visits instead
                # "delivery_gps_lat": float(order.delivery_gps_lat) if order.delivery_gps_lat else None,
                # "delivery_gps_lng": float(order.delivery_gps_lng) if order.delivery_gps_lng else None,
                "delivery_remarks": order.delivery_remarks,
                "delivery_images": delivery_images_list,
                "created_at": safe_isoformat(order.created_at),
                "updated_at": safe_isoformat(order.updated_at),
                # New subsidy approval system
                "calculated_total_amount": float(order.original_amount) if hasattr(order, 'original_amount') and order.original_amount else None,
                "final_total_amount": float(order.final_total_amount) if hasattr(order, 'final_total_amount') and order.final_total_amount else (float(order.total_amount) if order.total_amount else None),
                "subsidy_status": getattr(order, 'subsidy_status', None) or 'none',
                "subsidy_approved_by": getattr(order, 'subsidy_approved_by', None),
                "subsidy_approved_at": safe_isoformat(getattr(order, 'subsidy_approved_at', None)),
                "subsidy_rejection_reason": getattr(order, 'subsidy_rejection_reason', None),
                # DEPRECATED: Legacy fields (kept for backward compatibility)
                "order_resolution_type": order_resolution_type,
                "subsidy_id": subsidy_id,
                "subsidy_info": subsidy_info,
                "original_amount": float(order.original_amount) if hasattr(order, 'original_amount') and order.original_amount else None,
                "payment_collected_before_delivery": getattr(order, 'payment_collected_before_delivery', False),
                "payment_collected_amount": float(order.payment_collected_amount) if hasattr(order, 'payment_collected_amount') and order.payment_collected_amount else None,
                "payment_collected_at": safe_isoformat(getattr(order, 'payment_collected_at', None))
            })
            
            # Debug: Log what we're returning
            print(f"[DEBUG _format_orders] Order {order.id}: Returning order_resolution_type = {result[-1]['order_resolution_type']}")
        
        return result
    
    @staticmethod
    def assign_delivery_man(db: Session, order_id: int, delivery_man_id: int, auto_commit: bool = True) -> Dict:
        """
        Assign order to a delivery man.
        
        Args:
            db: Database session
            order_id: Order ID
            delivery_man_id: Delivery man ID
            auto_commit: If True, commits immediately. If False, caller must commit.
        
        Returns:
            Dict with order assignment details
        """
        from repositories.delivery_man_repository import DeliveryManRepository
        
        # Validate order exists
        order = OrderRepository.get_by_id(db, order_id)
        if not order:
            raise ValueError("Order not found")
        
        # Validate order can be assigned (subsidy_status must be 'none' or 'approved')
        subsidy_status = getattr(order, 'subsidy_status', None) or 'none'
        if subsidy_status == 'pending_approval':
            raise ValueError("Order requires distributor approval for subsidy")
        if subsidy_status == 'rejected':
            raise ValueError("Order subsidy was rejected by distributor")
        
        # Validate delivery man exists
        delivery_man = DeliveryManRepository.get_by_id(db, delivery_man_id)
        if not delivery_man:
            raise ValueError("Delivery man not found")
        
        order = OrderRepository.assign_delivery_man(db, order_id, delivery_man_id, auto_commit=auto_commit)
        if not order:
            raise ValueError("Order not found")
        
        return {
            "id": order.id,
            "delivery_man_id": order.delivery_man_id,
            "delivery_man_name": delivery_man.name,
            "status": order.status.value if hasattr(order.status, 'value') else str(order.status)
        }
    
    @staticmethod
    def get_pending_subsidy_approvals(db: Session, distributor_id: int) -> List[Dict]:
        """
        Get all orders pending subsidy approval for a distributor.
        
        Args:
            db: Database session
            distributor_id: Distributor ID to get pending approvals for
        
        Returns:
            List of orders with subsidy_status = 'pending_approval'
        """
        from models.order import Order
        orders = db.query(Order).filter(
            Order.subsidy_status == 'pending_approval',
            Order.distributor_id == distributor_id
        ).order_by(Order.created_at.desc()).all()
        
        return OrderService._format_orders(db, orders)
    
    @staticmethod
    def approve_subsidy(db: Session, order_id: int, distributor_id: int) -> Dict:
        """
        Approve a subsidized order.
        
        Args:
            db: Database session
            order_id: Order ID to approve
            distributor_id: Distributor ID approving the order
        
        Returns:
            Updated order data
        
        Raises:
            ValueError: If order not found, not pending approval, or distributor mismatch
        """
        from datetime import datetime
        
        order = OrderRepository.get_by_id(db, order_id)
        if not order:
            raise ValueError("Order not found")
        
        # Validate order is pending approval
        subsidy_status = getattr(order, 'subsidy_status', None) or 'none'
        if subsidy_status != 'pending_approval':
            raise ValueError(f"Order is not pending approval. Status: {subsidy_status}")
        
        # Validate distributor has permission (order belongs to their order booker)
        if order.distributor_id and order.distributor_id != distributor_id:
            raise ValueError("No permission to approve this order")
        
        # Update order
        order.subsidy_status = 'approved'
        order.subsidy_approved_by = distributor_id
        order.subsidy_approved_at = datetime.utcnow()
        
        # Update shop's outstanding balance (was not updated during creation)
        # Use final_total_amount (the reduced amount) for outstanding balance calculation
        if order.shop_id:
            from repositories.shop_repository import ShopRepository
            shop = ShopRepository.get_by_id(db, order.shop_id)
            if shop:
                # Use final_total_amount (the reduced amount after order booker's discount)
                # This is the actual amount the shop will owe
                final_amount = Decimal(str(order.final_total_amount)) if order.final_total_amount else Decimal(str(order.total_amount))
                
                # Refresh shop to get latest outstanding_balance
                db.refresh(shop)
                current_outstanding = Decimal(str(shop.outstanding_balance or 0))
                new_outstanding = current_outstanding + final_amount
                
                ShopRepository.update(
                    db=db,
                    shop_id=order.shop_id,
                    outstanding_balance=new_outstanding
                )
                print(f"[approve_subsidy] Updated shop {order.shop_id} outstanding balance: {current_outstanding} -> {new_outstanding} (using final_total_amount: {final_amount})")
        
        db.commit()
        db.refresh(order)
        
        return OrderService._format_orders(db, [order])[0]
    
    @staticmethod
    def reject_subsidy(db: Session, order_id: int, distributor_id: int, rejection_reason: str = None) -> Dict:
        """
        Reject a subsidized order.
        
        Args:
            db: Database session
            order_id: Order ID to reject
            distributor_id: Distributor ID rejecting the order
            rejection_reason: Optional reason for rejection
        
        Returns:
            Updated order data
        
        Raises:
            ValueError: If order not found, not pending approval, or distributor mismatch
        """
        order = OrderRepository.get_by_id(db, order_id)
        if not order:
            raise ValueError("Order not found")
        
        # Validate order is pending approval
        subsidy_status = getattr(order, 'subsidy_status', None) or 'none'
        if subsidy_status != 'pending_approval':
            raise ValueError(f"Order is not pending approval. Status: {subsidy_status}")
        
        # Validate distributor has permission
        if order.distributor_id and order.distributor_id != distributor_id:
            raise ValueError("No permission to reject this order")
        
        # Update order
        order.subsidy_status = 'rejected'
        order.subsidy_rejection_reason = rejection_reason
        
        # Do NOT update outstanding balance (order was not approved)
        
        db.commit()
        db.refresh(order)
        
        return OrderService._format_orders(db, [order])[0]

