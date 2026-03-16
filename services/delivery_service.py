"""
Delivery Service
===============
Business logic for delivery tracking and inventory management.
"""
from sqlalchemy.orm import Session
from repositories.delivery_repository import DeliveryRepository
from repositories.delivery_item_repository import DeliveryItemRepository
from repositories.order_repository import OrderRepository
from repositories.order_item_repository import OrderItemRepository
from repositories.inventory_repository import InventoryRepository
from repositories.warehouse_repository import WarehouseRepository
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
import json


class DeliveryService:
    """Service for Delivery business logic."""
    
    @staticmethod
    def create_delivery_for_order(db: Session, order_id: int, delivery_man_id: int,
                                  warehouse_id: int) -> Dict:
        """
        Create a delivery record for an order.
        
        This is called when an order is assigned to a delivery man.
        Creates delivery and delivery_items records.
        """
        # Verify order exists
        order = OrderRepository.get_by_id(db, order_id)
        if not order:
            raise ValueError("Order not found")
        
        # Check if delivery already exists
        existing_delivery = DeliveryRepository.get_by_order(db, order_id)
        if existing_delivery:
            raise ValueError("Delivery already exists for this order")
        
        # Create delivery
        delivery = DeliveryRepository.create(
            db=db,
            order_id=order_id,
            delivery_man_id=delivery_man_id,
            warehouse_id=warehouse_id,
            status='pending_pickup'
        )
        
        # Get order items and create delivery items
        from models.order_item import OrderItem
        order_items = db.query(OrderItem).filter(
            OrderItem.order_id == order_id
        ).all()
        
        if not order_items:
            raise ValueError("Order has no items. Cannot create delivery.")
        
        delivery_items = []
        for order_item in order_items:
            try:
                # Find matching inventory item by product_id or product_name
                inventory_item_id = None
                inventory_items = InventoryRepository.get_by_warehouse(db, warehouse_id)
                
                # Try to match by product_id first
                if order_item.product_id:
                    inventory_item = next(
                        (inv for inv in inventory_items if inv.product_id == order_item.product_id),
                        None
                    )
                    if inventory_item:
                        inventory_item_id = inventory_item.id
                
                # If not found by product_id, try to match by product_name/item_name
                if not inventory_item_id and order_item.product_name:
                    product_name_lower = order_item.product_name.lower().strip()
                    inventory_item = next(
                        (inv for inv in inventory_items 
                         if inv.item_name and inv.item_name.lower().strip() == product_name_lower),
                        None
                    )
                    if inventory_item:
                        inventory_item_id = inventory_item.id
                        print(f"[create_delivery_for_order] Matched inventory by name: {order_item.product_name} -> inventory_id {inventory_item_id}")
                
                delivery_item = DeliveryItemRepository.create(
                    db=db,
                    delivery_id=delivery.id,
                    order_item_id=order_item.id,
                    product_id=order_item.product_id,
                    inventory_item_id=inventory_item_id,
                    quantity_picked_up=0  # Will be set during pickup
                )
                delivery_items.append(delivery_item)
            except Exception as e:
                # Rollback delivery creation if delivery items fail
                db.rollback()
                raise ValueError(f"Error creating delivery item for order item {order_item.id}: {str(e)}")
        
        return {
            "id": delivery.id,
            "order_id": delivery.order_id,
            "delivery_man_id": delivery.delivery_man_id,
            "warehouse_id": delivery.warehouse_id,
            "status": delivery.status,
            "created_at": delivery.created_at.isoformat() if delivery.created_at else None
        }
    
    @staticmethod
    def pickup_from_warehouse(db: Session, delivery_id: int, pickup_quantities: Dict[int, int],
                              pickup_gps_lat: Decimal = None, pickup_gps_lng: Decimal = None) -> Dict:
        """
        Record warehouse pickup and deduct inventory.
        
        Args:
            delivery_id: Delivery ID
            pickup_quantities: Dict mapping order_item_id to quantity picked up
            pickup_gps_lat: GPS latitude at pickup location
            pickup_gps_lng: GPS longitude at pickup location
        
        Returns:
            Updated delivery data
        """
        # Validate GPS coordinates
        DeliveryService._validate_gps_coordinate(pickup_gps_lat, pickup_gps_lng, "pickup")
        
        delivery = DeliveryRepository.get_by_id(db, delivery_id)
        if not delivery:
            raise ValueError("Delivery not found")
        
        if delivery.status != 'pending_pickup':
            raise ValueError(f"Cannot pickup. Current status: {delivery.status}")
        
        # Get delivery items
        delivery_items = DeliveryItemRepository.get_by_delivery(db, delivery_id)
        
        # Update quantities and deduct inventory
        for delivery_item in delivery_items:
            order_item_id = delivery_item.order_item_id
            quantity = pickup_quantities.get(order_item_id, 0)
            
            if quantity > 0:
                # Update delivery item
                DeliveryItemRepository.update_pickup_quantity(
                    db=db,
                    delivery_item_id=delivery_item.id,
                    quantity_picked_up=quantity
                )
                
                # Deduct from inventory
                inventory = None
                order_item = None
                inventory_items = []
                if delivery_item.inventory_item_id:
                    # Use stored inventory_item_id
                    inventory = InventoryRepository.get_by_id(db, delivery_item.inventory_item_id)
                else:
                    # Try to find inventory by product_id, product_name, or product_code
                    from models.order_item import OrderItem
                    from repositories.product_repository import ProductRepository
                    order_item = db.query(OrderItem).filter(OrderItem.id == order_item_id).first()
                    if order_item:
                        inventory_items = InventoryRepository.get_by_warehouse(db, delivery.warehouse_id)
                        
                        # Method 1: Try by product_id first (most reliable)
                        if order_item.product_id:
                            inventory = next(
                                (inv for inv in inventory_items if inv.product_id == order_item.product_id),
                                None
                            )
                            if inventory:
                                print(f"[pickup_from_warehouse] Matched inventory by product_id: {order_item.product_id} -> inventory_id {inventory.id}")
                        
                        # Method 2: Try by product_name matching item_name
                        if not inventory and order_item.product_name:
                            product_name_lower = order_item.product_name.lower().strip()
                            inventory = next(
                                (inv for inv in inventory_items 
                                 if inv.item_name and inv.item_name.lower().strip() == product_name_lower),
                                None
                            )
                            if inventory:
                                print(f"[pickup_from_warehouse] Matched inventory by name: '{order_item.product_name}' -> inventory_id {inventory.id}")
                        
                        # Method 3: Try by product_code matching item_code (if order item has product_id)
                        if not inventory and order_item.product_id:
                            product = ProductRepository.get_by_id(db, order_item.product_id)
                            if product and product.code:
                                product_code_lower = product.code.lower().strip()
                                inventory = next(
                                    (inv for inv in inventory_items 
                                     if inv.item_code and inv.item_code.lower().strip() == product_code_lower),
                                    None
                                )
                                if inventory:
                                    print(f"[pickup_from_warehouse] Matched inventory by code: '{product.code}' -> inventory_id {inventory.id}")
                        
                        # Method 4: Fuzzy matching - check if product name is a prefix of item_code or vice versa
                        if not inventory and order_item.product_name:
                            product_name_lower = order_item.product_name.lower().strip()
                            for inv in inventory_items:
                                if inv.item_code:
                                    item_code_lower = inv.item_code.lower().strip()
                                    # Check if product name is a prefix of item code (e.g., "t1" matches "t1d2")
                                    if item_code_lower.startswith(product_name_lower) or product_name_lower.startswith(item_code_lower):
                                        inventory = inv
                                        print(f"[pickup_from_warehouse] Matched inventory by fuzzy code/name: '{order_item.product_name}' matches '{inv.item_code}' -> inventory_id {inventory.id}")
                                        break
                        
                        # If found, update delivery_item with inventory_item_id for future operations
                        if inventory and not delivery_item.inventory_item_id:
                            delivery_item.inventory_item_id = inventory.id
                            db.commit()
                            print(f"[pickup_from_warehouse] Linked inventory_item_id {inventory.id} to delivery_item {delivery_item.id}")
                
                if inventory:
                    # Ensure quantity is an integer
                    available_qty = int(inventory.quantity) if inventory.quantity is not None else 0
                    requested_qty = int(quantity) if quantity is not None else 0
                    
                    if available_qty < requested_qty:
                        raise ValueError(
                            f"Insufficient inventory for {inventory.item_name or 'product'}. "
                            f"Available: {available_qty}, Requested: {requested_qty}"
                        )
                    
                    old_quantity = available_qty
                    new_quantity = available_qty - requested_qty
                    
                    InventoryRepository.update(
                        db=db,
                        inventory_id=inventory.id,
                        quantity=new_quantity
                    )
                    print(f"[pickup_from_warehouse] Deducted inventory: {inventory.item_name or 'product'} (inventory_id={inventory.id}) - {old_quantity} -> {new_quantity}")
                else:
                    # Log detailed information for debugging
                    order_item_info = f"order_item_id={order_item_id}"
                    if order_item:
                        order_item_info += f", product_id={order_item.product_id}, product_name='{order_item.product_name}'"
                    print(f"[pickup_from_warehouse] WARNING: Could not find inventory item for {order_item_info} in warehouse {delivery.warehouse_id}. Inventory not deducted.")
                    if inventory_items:
                        # Build inventory items list for logging (avoid backslash in f-string)
                        inv_list = []
                        for inv in inventory_items:
                            inv_list.append(f"id={inv.id}, product_id={inv.product_id}, item_name='{inv.item_name}', item_code='{inv.item_code}'")
                        print(f"[pickup_from_warehouse] Available inventory items in warehouse: {inv_list}")
                    else:
                        print(f"[pickup_from_warehouse] No inventory items found in warehouse {delivery.warehouse_id}")
        
        # Update delivery status and pickup info
        updated_delivery = DeliveryRepository.update_pickup(
            db=db,
            delivery_id=delivery_id,
            picked_up_at=datetime.utcnow(),
            pickup_gps_lat=pickup_gps_lat,
            pickup_gps_lng=pickup_gps_lng,
            status='in_transit'
        )
        
        return DeliveryService._format_delivery_data(db, updated_delivery)
    
    @staticmethod
    def _validate_gps_coordinate(lat: Decimal = None, lng: Decimal = None, coord_type: str = "GPS"):
        """Validate GPS coordinates are within valid ranges."""
        if lat is not None:
            lat_float = float(lat)
            if lat_float < -90 or lat_float > 90:
                raise ValueError(f"Invalid {coord_type} latitude: {lat_float}. Must be between -90 and 90.")
        
        if lng is not None:
            lng_float = float(lng)
            if lng_float < -180 or lng_float > 180:
                raise ValueError(f"Invalid {coord_type} longitude: {lng_float}. Must be between -180 and 180.")
    
    @staticmethod
    def deliver_to_shop(db: Session, delivery_id: int, delivery_quantities: Dict[int, int],
                       delivery_gps_lat: Decimal = None, delivery_gps_lng: Decimal = None,
                       delivery_remarks: str = None, delivery_images: List[str] = None) -> Dict:
        """
        Record shop delivery.
        
        Args:
            delivery_id: Delivery ID
            delivery_quantities: Dict mapping order_item_id to quantity delivered
            delivery_gps_lat: GPS latitude at delivery location
            delivery_gps_lng: GPS longitude at delivery location
            delivery_remarks: Delivery remarks
            delivery_images: List of delivery proof image URLs
        
        Returns:
            Updated delivery data
        """
        # Validate GPS coordinates
        DeliveryService._validate_gps_coordinate(delivery_gps_lat, delivery_gps_lng, "delivery")
        
        delivery = DeliveryRepository.get_by_id(db, delivery_id)
        if not delivery:
            raise ValueError("Delivery not found")
        
        if delivery.status not in ['in_transit', 'picked_up', 'partially_delivered']:
            raise ValueError(f"Cannot deliver. Current status: {delivery.status}")
        
        # Get delivery items
        delivery_items = DeliveryItemRepository.get_by_delivery(db, delivery_id)
        if not delivery_items:
            raise ValueError("No delivery items found. Please complete pickup first.")
        
        # Validate that delivery_quantities contains at least one non-zero value
        if not delivery_quantities or all(qty == 0 for qty in delivery_quantities.values()):
            raise ValueError("At least one quantity must be greater than 0")
        
        # Validate that all order_item_ids in delivery_quantities exist in delivery_items
        delivery_item_order_ids = {item.order_item_id for item in delivery_items}
        invalid_ids = set(delivery_quantities.keys()) - delivery_item_order_ids
        if invalid_ids:
            raise ValueError(f"Invalid order_item_ids in delivery_quantities: {invalid_ids}")
        
        # Update quantities
        total_delivered = 0
        total_picked = 0
        total_returned = 0
        for delivery_item in delivery_items:
            order_item_id = delivery_item.order_item_id
            quantity_delivered = delivery_quantities.get(order_item_id, 0)
            quantity_picked = delivery_item.quantity_picked_up
            
            # Get current delivered quantity (for partial deliveries)
            current_quantity_delivered = delivery_item.quantity_delivered or 0
            current_quantity_returned = delivery_item.quantity_returned or 0
            
            # Validate total delivered doesn't exceed picked
            total_delivered_after = current_quantity_delivered + quantity_delivered
            if total_delivered_after > quantity_picked:
                raise ValueError(
                    f"Cannot deliver more than picked up. "
                    f"Picked: {quantity_picked}, Already delivered: {current_quantity_delivered}, "
                    f"New delivery: {quantity_delivered}, Total would be: {total_delivered_after}"
                )
            
            # Update delivered quantity (additive for partial deliveries)
            new_total_delivered = current_quantity_delivered + quantity_delivered
            
            # Don't set quantity_returned here - it should only be set when explicitly returning
            # quantity_returned will be calculated as: quantity_picked - new_total_delivered
            # when the user explicitly returns
            
            DeliveryItemRepository.update_quantities(
                db=db,
                delivery_item_id=delivery_item.id,
                quantity_delivered=new_total_delivered,
                quantity_returned=None  # Don't set returned quantity during delivery
            )
            
            total_delivered += new_total_delivered  # Use total delivered, not just new delivery
            total_picked += quantity_picked
            total_returned += current_quantity_returned  # Track already returned items
        
        # Calculate remaining items (picked - delivered - returned)
        total_remaining = total_picked - total_delivered - total_returned
        
        # Determine status
        if total_delivered == total_picked:
            status = 'delivered'
        elif total_delivered > 0:
            status = 'partially_delivered'
        else:
            status = 'returned'
        
        # Prepare delivery images JSON
        delivery_images_json = None
        if delivery_images:
            delivery_images_json = json.dumps(delivery_images)
        
        # Update delivery
        updated_delivery = DeliveryRepository.update_delivery(
            db=db,
            delivery_id=delivery_id,
            delivered_at=datetime.utcnow(),
            delivery_gps_lat=delivery_gps_lat,
            delivery_gps_lng=delivery_gps_lng,
            delivery_remarks=delivery_remarks,
            delivery_images=delivery_images_json,
            status=status
        )
        
        # Update order status ONLY if all items are accounted for (delivered + returned = picked)
        # If there are remaining items, order status stays PENDING until return is completed
        if delivery.order_id:
            from models.order import OrderStatus
            if total_remaining == 0:
                # All items are accounted for (delivered + returned = picked)
                if status == 'delivered':
                    # Fully delivered - update order status to DELIVERED
                    OrderRepository.update_status(db, delivery.order_id, OrderStatus.DELIVERED.value)
                elif status == 'partially_delivered':
                    # Partially delivered - update order status to PARTIAL_DELIVERED
                    OrderRepository.update_status(db, delivery.order_id, OrderStatus.PARTIAL_DELIVERED.value)
                # If status is 'returned', order status remains PENDING (nothing delivered yet)
            else:
                # There are remaining items that need to be returned
                # Order status remains PENDING until return is completed
                print(f"[deliver_to_shop] Remaining items ({total_remaining}) need to be returned. Order status remains PENDING.")
        
        return DeliveryService._format_delivery_data(db, updated_delivery)
    
    @staticmethod
    def return_to_warehouse(db: Session, delivery_id: int, return_quantities: Dict[int, int],
                           return_gps_lat: Decimal = None, return_gps_lng: Decimal = None,
                           return_reason: str = None) -> Dict:
        """
        Record return to warehouse and add inventory back.
        
        Args:
            delivery_id: Delivery ID
            return_quantities: Dict mapping order_item_id to quantity returned
            return_gps_lat: GPS latitude at return location
            return_gps_lng: GPS longitude at return location
            return_reason: Reason for return
        
        Returns:
            Updated delivery data
        """
        # Validate GPS coordinates
        DeliveryService._validate_gps_coordinate(return_gps_lat, return_gps_lng, "return")
        
        delivery = DeliveryRepository.get_by_id(db, delivery_id)
        if not delivery:
            raise ValueError("Delivery not found")
        
        # Allow returns when:
        # 1. Items have been delivered (partially_delivered or delivered) - return remaining items
        # 2. Items are in transit or picked up but not yet delivered - return all items
        if delivery.status not in ['in_transit', 'picked_up', 'partially_delivered', 'delivered']:
            raise ValueError(f"Cannot return. Current status: {delivery.status}")
        
        # Get delivery items and run all updates in one transaction (single commit at end; rollback on error)
        delivery_items = DeliveryItemRepository.get_by_delivery(db, delivery_id)
        try:
            # Update quantities and add inventory back
            for delivery_item in delivery_items:
                order_item_id = delivery_item.order_item_id
                new_quantity_returned = return_quantities.get(order_item_id, 0)
                
                if new_quantity_returned > 0:
                    # Get the current quantity_returned (should be 0 or None since we don't set it during delivery)
                    current_quantity_returned = delivery_item.quantity_returned or 0
                    
                    # Validate return quantity
                    max_returnable = delivery_item.quantity_picked_up - (delivery_item.quantity_delivered or 0)
                    if new_quantity_returned > max_returnable:
                        raise ValueError(
                            f"Cannot return more than available. "
                            f"Available to return: {max_returnable}, Requested: {new_quantity_returned}"
                        )
                    
                    # Calculate the NET amount to add back (incremental return)
                    # This handles cases where user returns in multiple steps
                    net_return_amount = new_quantity_returned - current_quantity_returned
                    
                    print(f"[return_to_warehouse] order_item_id={order_item_id}, current_returned={current_quantity_returned}, new_returned={new_quantity_returned}, net_return={net_return_amount}")
                    
                    # Update delivery item with new total returned quantity (no commit; single commit at end of flow)
                    DeliveryItemRepository.update_quantities(
                        db=db,
                        delivery_item_id=delivery_item.id,
                        quantity_returned=new_quantity_returned,
                        auto_commit=False
                    )
                    
                    # Add back to inventory the net return amount (incremental)
                    if net_return_amount > 0:
                        # Add back to inventory
                        inventory = None
                        if delivery_item.inventory_item_id:
                            # Use stored inventory_item_id
                            inventory = InventoryRepository.get_by_id(db, delivery_item.inventory_item_id)
                        else:
                            # Try to find inventory by product_id or product_name
                            from models.order_item import OrderItem
                            order_item = db.query(OrderItem).filter(OrderItem.id == order_item_id).first()
                            if order_item:
                                inventory_items = InventoryRepository.get_by_warehouse(db, delivery.warehouse_id)
                                
                                # Try by product_id first
                                if order_item.product_id:
                                    inventory = next(
                                        (inv for inv in inventory_items if inv.product_id == order_item.product_id),
                                        None
                                    )
                                
                                # If not found, try by product_name
                                if not inventory and order_item.product_name:
                                    product_name_lower = order_item.product_name.lower().strip()
                                    inventory = next(
                                        (inv for inv in inventory_items 
                                         if inv.item_name and inv.item_name.lower().strip() == product_name_lower),
                                        None
                                    )
                                
                                # If found, update delivery_item with inventory_item_id for future operations (no commit here; single commit at end)
                                if inventory and not delivery_item.inventory_item_id:
                                    delivery_item.inventory_item_id = inventory.id
                                    print(f"[return_to_warehouse] Found and linked inventory by name: {order_item.product_name} -> inventory_id {inventory.id}")
                        
                        if inventory:
                            old_quantity = inventory.quantity
                            new_quantity = inventory.quantity + net_return_amount
                            InventoryRepository.update(
                                db=db,
                                inventory_id=inventory.id,
                                quantity=new_quantity,
                                auto_commit=False
                            )
                            print(f"[return_to_warehouse] Added back to inventory: {inventory.item_name or 'product'} - {old_quantity} -> {new_quantity} (net_return={net_return_amount})")
                        else:
                            print(f"[return_to_warehouse] WARNING: Could not find inventory item for order_item_id {order_item_id}. Inventory not updated.")
                    elif net_return_amount < 0:
                        print(f"[return_to_warehouse] WARNING: net_return_amount is negative ({net_return_amount}). This shouldn't happen. Skipping inventory update.")
                    else:
                        print(f"[return_to_warehouse] No net return amount (already returned). Skipping inventory update.")
            
            # Recalculate totals after return to check if all items are accounted for
            # Refresh delivery items to get updated quantities
            delivery_items = DeliveryItemRepository.get_by_delivery(db, delivery_id)
            total_delivered = 0
            total_picked = 0
            total_returned = 0
            for delivery_item in delivery_items:
                total_delivered += delivery_item.quantity_delivered or 0
                total_picked += delivery_item.quantity_picked_up
                total_returned += delivery_item.quantity_returned or 0
            
            # Calculate remaining items
            total_remaining = total_picked - total_delivered - total_returned
            
            # Determine delivery status based on final state
            if total_delivered == total_picked:
                # All items delivered, none returned
                delivery_status = 'delivered'
            elif total_delivered > 0 and total_remaining == 0:
                # Some items delivered, all remaining items returned
                delivery_status = 'partially_delivered'
            elif total_delivered == 0 and total_returned == total_picked:
                # All items returned, nothing delivered
                delivery_status = 'returned'
            elif total_delivered > 0 and total_remaining > 0:
                # Some items delivered, but still has remaining items (partial return)
                delivery_status = 'partially_delivered'
            else:
                # Still has remaining items (shouldn't happen after return, but handle it)
                delivery_status = 'partially_delivered'
            
            # Update delivery status (no commit yet; single commit at end of flow)
            updated_delivery = DeliveryRepository.update_return(
                db=db,
                delivery_id=delivery_id,
                returned_at=datetime.utcnow(),
                return_gps_lat=return_gps_lat,
                return_gps_lng=return_gps_lng,
                return_reason=return_reason,
                status=delivery_status,
                auto_commit=False
            )
            
            # Update order status if all items are now accounted for (delivered + returned = picked)
            if delivery.order_id and total_remaining == 0:
                from models.order import OrderStatus
                if total_delivered == total_picked:
                    # Fully delivered - update order status to DELIVERED
                    OrderRepository.update_status(db, delivery.order_id, OrderStatus.DELIVERED.value, auto_commit=False)
                    print(f"[return_to_warehouse] All items delivered. Order status updated to DELIVERED.")
                elif total_delivered > 0:
                    # Partially delivered - update order status to PARTIAL_DELIVERED
                    OrderRepository.update_status(db, delivery.order_id, OrderStatus.PARTIAL_DELIVERED.value, auto_commit=False)
                    print(f"[return_to_warehouse] Some items delivered ({total_delivered}/{total_picked}). Order status updated to PARTIAL_DELIVERED.")
                # If total_delivered == 0, order status remains PENDING (nothing delivered)
            elif delivery.order_id and total_remaining > 0:
                print(f"[return_to_warehouse] WARNING: Still have remaining items ({total_remaining}). Order status remains PENDING.")
            
            # Single commit: only persist when all steps succeeded (no partial commit on error)
            db.commit()
            return DeliveryService._format_delivery_data(db, updated_delivery)
        except Exception:
            db.rollback()
            raise
    
    @staticmethod
    def _format_delivery_data(db: Session, delivery) -> Dict:
        """Format delivery data for API response."""
        try:
            # Get delivery items
            delivery_items = DeliveryItemRepository.get_by_delivery(db, delivery.id)
            
            # Get order and shop information
            order = OrderRepository.get_by_id(db, delivery.order_id)
            shop_id = None
            shop_name = None
            shop_zone_id = None
            delivery_man_name = None
            
            if order:
                shop_id = order.shop_id
                if shop_id:
                    from repositories.shop_repository import ShopRepository
                    shop = ShopRepository.get_by_id(db, shop_id)
                    if shop:
                        shop_name = shop.name
                        shop_zone_id = shop.zone_id
            
            # Get delivery man name
            if delivery.delivery_man_id:
                from repositories.delivery_man_repository import DeliveryManRepository
                delivery_man = DeliveryManRepository.get_by_id(db, delivery.delivery_man_id)
                if delivery_man:
                    delivery_man_name = delivery_man.name
            
            # Parse delivery images
            delivery_images = []
            if delivery.delivery_images:
                try:
                    delivery_images = json.loads(delivery.delivery_images)
                except:
                    pass
            
            # Helper function to safely convert datetime
            def safe_isoformat(dt):
                if dt is None:
                    return None
                try:
                    return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
                except:
                    return None
            
            # Helper function to safely convert numeric
            def safe_float(value):
                if value is None:
                    return None
                try:
                    return float(value)
                except:
                    return None
            
            return {
                "id": delivery.id,
                "order_id": delivery.order_id,
                "delivery_man_id": delivery.delivery_man_id,
                "delivery_man_name": delivery_man_name,
                "warehouse_id": delivery.warehouse_id,
                "shop_id": shop_id,
                "shop_name": shop_name,
                "shop_zone_id": shop_zone_id,
                "status": delivery.status,
                "picked_up_at": safe_isoformat(delivery.picked_up_at),
                "pickup_gps_lat": safe_float(delivery.pickup_gps_lat),
                "pickup_gps_lng": safe_float(delivery.pickup_gps_lng),
                "delivered_at": safe_isoformat(delivery.delivered_at),
                "delivery_gps_lat": safe_float(delivery.delivery_gps_lat),
                "delivery_gps_lng": safe_float(delivery.delivery_gps_lng),
                "delivery_remarks": delivery.delivery_remarks,
                "delivery_images": delivery_images,
                "returned_at": safe_isoformat(delivery.returned_at),
                "return_gps_lat": safe_float(delivery.return_gps_lat),
                "return_gps_lng": safe_float(delivery.return_gps_lng),
                "return_reason": delivery.return_reason,
                "created_at": safe_isoformat(delivery.created_at),
                "updated_at": safe_isoformat(delivery.updated_at),
                "delivery_items": [
                    {
                        "id": item.id,
                        "order_item_id": item.order_item_id,
                        "product_id": item.product_id,
                        "inventory_item_id": item.inventory_item_id,
                        "quantity_picked_up": item.quantity_picked_up,
                        "quantity_delivered": item.quantity_delivered,
                        "quantity_returned": item.quantity_returned
                    }
                    for item in delivery_items
                ]
            }
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error formatting delivery data for delivery {delivery.id}: {str(e)}")
            print(f"Traceback: {error_trace}")
            raise ValueError(f"Error formatting delivery data: {str(e)}")

    @staticmethod
    def _format_deliveries_batch(db: Session, deliveries: List) -> List[Dict]:
        """Format a list of deliveries using batch-loaded related data (no N+1)."""
        if not deliveries:
            return []
        delivery_ids = [d.id for d in deliveries]
        order_ids = list(set([d.order_id for d in deliveries if d.order_id]))
        delivery_man_ids = list(set([d.delivery_man_id for d in deliveries if d.delivery_man_id]))

        from models.delivery_item import DeliveryItem
        delivery_items_map = {}
        if delivery_ids:
            all_items = db.query(DeliveryItem).filter(DeliveryItem.delivery_id.in_(delivery_ids)).all()
            for item in all_items:
                if item.delivery_id not in delivery_items_map:
                    delivery_items_map[item.delivery_id] = []
                delivery_items_map[item.delivery_id].append(item)

        from models.order import Order
        orders_map = {}
        if order_ids:
            orders = db.query(Order).filter(Order.id.in_(order_ids)).all()
            orders_map = {o.id: o for o in orders}

        shop_ids = list(set([o.shop_id for o in orders_map.values() if o.shop_id]))
        shops_map = {}
        if shop_ids:
            from models.shop import Shop
            shops = db.query(Shop).filter(Shop.id.in_(shop_ids)).all()
            shops_map = {s.id: s for s in shops}

        delivery_men_map = {}
        if delivery_man_ids:
            from models.delivery_man import DeliveryMan
            dms = db.query(DeliveryMan).filter(DeliveryMan.id.in_(delivery_man_ids)).all()
            delivery_men_map = {dm.id: dm for dm in dms}

        def safe_isoformat(dt):
            if dt is None:
                return None
            try:
                return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
            except Exception:
                return None

        def safe_float(value):
            if value is None:
                return None
            try:
                return float(value)
            except Exception:
                return None

        result = []
        for delivery in deliveries:
            delivery_items = delivery_items_map.get(delivery.id, [])
            order = orders_map.get(delivery.order_id)
            shop_id = shop_name = shop_zone_id = None
            if order and order.shop_id:
                shop = shops_map.get(order.shop_id)
                if shop:
                    shop_id, shop_name, shop_zone_id = shop.id, shop.name, shop.zone_id
            delivery_man = delivery_men_map.get(delivery.delivery_man_id)
            delivery_man_name = delivery_man.name if delivery_man else None
            delivery_images = []
            if getattr(delivery, 'delivery_images', None):
                try:
                    delivery_images = json.loads(delivery.delivery_images)
                except Exception:
                    pass
            result.append({
                "id": delivery.id,
                "order_id": delivery.order_id,
                "delivery_man_id": delivery.delivery_man_id,
                "delivery_man_name": delivery_man_name,
                "warehouse_id": delivery.warehouse_id,
                "shop_id": shop_id,
                "shop_name": shop_name,
                "shop_zone_id": shop_zone_id,
                "status": delivery.status,
                "picked_up_at": safe_isoformat(getattr(delivery, 'picked_up_at', None)),
                "pickup_gps_lat": safe_float(getattr(delivery, 'pickup_gps_lat', None)),
                "pickup_gps_lng": safe_float(getattr(delivery, 'pickup_gps_lng', None)),
                "delivered_at": safe_isoformat(getattr(delivery, 'delivered_at', None)),
                "delivery_gps_lat": safe_float(getattr(delivery, 'delivery_gps_lat', None)),
                "delivery_gps_lng": safe_float(getattr(delivery, 'delivery_gps_lng', None)),
                "delivery_remarks": getattr(delivery, 'delivery_remarks', None),
                "delivery_images": delivery_images,
                "returned_at": safe_isoformat(getattr(delivery, 'returned_at', None)),
                "return_gps_lat": safe_float(getattr(delivery, 'return_gps_lat', None)),
                "return_gps_lng": safe_float(getattr(delivery, 'return_gps_lng', None)),
                "return_reason": getattr(delivery, 'return_reason', None),
                "created_at": safe_isoformat(getattr(delivery, 'created_at', None)),
                "updated_at": safe_isoformat(getattr(delivery, 'updated_at', None)),
                "delivery_items": [
                    {
                        "id": item.id,
                        "order_item_id": item.order_item_id,
                        "product_id": item.product_id,
                        "inventory_item_id": item.inventory_item_id,
                        "quantity_picked_up": item.quantity_picked_up,
                        "quantity_delivered": item.quantity_delivered,
                        "quantity_returned": item.quantity_returned
                    }
                    for item in delivery_items
                ]
            })
        return result

    @staticmethod
    def format_delivery_summary(delivery) -> Dict:
        """Format a delivery ORM object to a minimal summary dict (no DB queries). For embedding in order list."""
        def safe_isoformat(dt):
            if dt is None:
                return None
            try:
                return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
            except Exception:
                return None

        def safe_float(value):
            if value is None:
                return None
            try:
                return float(value)
            except Exception:
                return None

        delivery_images = []
        if getattr(delivery, 'delivery_images', None):
            try:
                delivery_images = json.loads(delivery.delivery_images)
            except Exception:
                pass

        return {
            "id": delivery.id,
            "order_id": getattr(delivery, 'order_id', None),
            "warehouse_id": getattr(delivery, 'warehouse_id', None),
            "status": delivery.status,
            "picked_up_at": safe_isoformat(getattr(delivery, 'picked_up_at', None)),
            "pickup_gps_lat": safe_float(getattr(delivery, 'pickup_gps_lat', None)),
            "pickup_gps_lng": safe_float(getattr(delivery, 'pickup_gps_lng', None)),
            "delivered_at": safe_isoformat(getattr(delivery, 'delivered_at', None)),
            "delivery_gps_lat": safe_float(getattr(delivery, 'delivery_gps_lat', None)),
            "delivery_gps_lng": safe_float(getattr(delivery, 'delivery_gps_lng', None)),
            "delivery_remarks": getattr(delivery, 'delivery_remarks', None),
            "delivery_images": delivery_images,
            "returned_at": safe_isoformat(getattr(delivery, 'returned_at', None)),
            "return_gps_lat": safe_float(getattr(delivery, 'return_gps_lat', None)),
            "return_gps_lng": safe_float(getattr(delivery, 'return_gps_lng', None)),
            "return_reason": getattr(delivery, 'return_reason', None),
            "created_at": safe_isoformat(getattr(delivery, 'created_at', None)),
            "updated_at": safe_isoformat(getattr(delivery, 'updated_at', None)),
        }

    @staticmethod
    def get_delivery_by_order(db: Session, order_id: int) -> Optional[Dict]:
        """Get delivery data for an order."""
        delivery = DeliveryRepository.get_by_order(db, order_id)
        if not delivery:
            return None
        return DeliveryService._format_delivery_data(db, delivery)
    
    @staticmethod
    def get_deliveries_by_delivery_man(db: Session, delivery_man_id: int,
                                      skip: int = 0, limit: int = 100) -> List[Dict]:
        """Get all deliveries for a delivery man. Uses batch loading to avoid N+1 queries."""
        deliveries = DeliveryRepository.get_by_delivery_man(
            db=db,
            delivery_man_id=delivery_man_id,
            skip=skip,
            limit=limit
        )
        if not deliveries:
            return []
        return DeliveryService._format_deliveries_batch(db, deliveries)
    
    @staticmethod
    def get_deliveries_by_distributor(db: Session, distributor_id: int,
                                     skip: int = 0, limit: int = 1000) -> List[Dict]:
        """
        Get all deliveries for a distributor (through their delivery men).
        OPTIMIZED: Uses batch loading to avoid N+1 queries.
        
        FLOW:
        1. Gets all deliveries from repository (1 query)
        2. Batch loads all related data (delivery items, orders, shops, delivery men)
        3. Formats deliveries using pre-loaded data (no additional queries)
        
        Args:
            db: Database session
            distributor_id: Distributor ID
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        
        Returns:
            List[Dict]: List of deliveries with all related data
        """
        deliveries = DeliveryRepository.get_by_distributor(
            db=db,
            distributor_id=distributor_id,
            skip=skip,
            limit=limit
        )
        return DeliveryService._format_deliveries_batch(db, deliveries)

