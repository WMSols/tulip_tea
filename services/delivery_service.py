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
from services.activity_log_service import ActivityLogService
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
                # Find matching inventory item by product_id
                inventory_item_id = None
                if order_item.product_id:
                    inventory_items = InventoryRepository.get_by_warehouse(db, warehouse_id)
                    inventory_item = next(
                        (inv for inv in inventory_items if inv.product_id == order_item.product_id),
                        None
                    )
                    if inventory_item:
                        inventory_item_id = inventory_item.id
                
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
                              pickup_gps_lat: Decimal = None, pickup_gps_lng: Decimal = None,
                              user_id: int = None, user_role: str = None, user_name: str = None) -> Dict:
        """
        Record warehouse pickup and deduct inventory.
        
        Args:
            delivery_id: Delivery ID
            pickup_quantities: Dict mapping order_item_id to quantity picked up
            pickup_gps_lat: GPS latitude at pickup location
            pickup_gps_lng: GPS longitude at pickup location
            user_id: ID of user performing the action (for activity log)
            user_role: Role of user (for activity log)
            user_name: Name of user (for activity log)
        
        Returns:
            Updated delivery data
        """
        print(f"🔵 [PICKUP] Starting pickup for delivery_id={delivery_id}, quantities={pickup_quantities}")
        
        # Validate GPS coordinates
        DeliveryService._validate_gps_coordinate(pickup_gps_lat, pickup_gps_lng, "pickup")
        
        delivery = DeliveryRepository.get_by_id(db, delivery_id)
        if not delivery:
            raise ValueError("Delivery not found")
        
        if delivery.status != 'pending_pickup':
            raise ValueError(f"Cannot pickup. Current status: {delivery.status}")
        
        # Get delivery items
        delivery_items = DeliveryItemRepository.get_by_delivery(db, delivery_id)
        print(f"🔵 [PICKUP] Found {len(delivery_items)} delivery items")
        
        # Track inventory changes for activity log
        inventory_changes = []
        
        # Update quantities and deduct inventory
        for delivery_item in delivery_items:
            order_item_id = delivery_item.order_item_id
            quantity = pickup_quantities.get(order_item_id, 0)
            
            if quantity > 0:
                print(f"🔵 [PICKUP] Processing order_item_id={order_item_id}, quantity={quantity}")
                
                # Update delivery item
                DeliveryItemRepository.update_pickup_quantity(
                    db=db,
                    delivery_item_id=delivery_item.id,
                    quantity_picked_up=quantity
                )
                
                # Deduct from inventory if inventory_item_id is set
                if delivery_item.inventory_item_id:
                    inventory = InventoryRepository.get_by_id(db, delivery_item.inventory_item_id)
                    if inventory:
                        old_quantity = inventory.quantity
                        if inventory.quantity < quantity:
                            raise ValueError(
                                f"Insufficient inventory for {inventory.item_name}. "
                                f"Available: {inventory.quantity}, Requested: {quantity}"
                            )
                        new_quantity = inventory.quantity - quantity
                        print(f"🔵 [PICKUP] Updating inventory_id={inventory.id}, item={inventory.item_name}, "
                              f"old_qty={old_quantity} -> new_qty={new_quantity}")
                        
                        updated_inventory = InventoryRepository.update(
                            db=db,
                            inventory_id=inventory.id,
                            quantity=new_quantity
                        )
                        
                        # Verify update by re-fetching from database
                        db.commit()  # Ensure commit
                        verified_inventory = InventoryRepository.get_by_id(db, inventory.id)
                        if verified_inventory:
                            print(f"🔵 [PICKUP] Verified inventory update: inventory_id={verified_inventory.id}, "
                                  f"quantity={verified_inventory.quantity} (expected: {new_quantity})")
                            if verified_inventory.quantity != new_quantity:
                                print(f"❌ [PICKUP] ERROR: Inventory quantity mismatch! Expected {new_quantity}, got {verified_inventory.quantity}")
                        else:
                            print(f"❌ [PICKUP] ERROR: Could not verify inventory update - inventory not found!")
                        
                        inventory_changes.append({
                            "inventory_id": inventory.id,
                            "item_name": inventory.item_name,
                            "old_quantity": old_quantity,
                            "new_quantity": new_quantity,
                            "quantity_deducted": quantity
                        })
                else:
                    print(f"⚠️ [PICKUP] Warning: delivery_item_id={delivery_item.id} has no inventory_item_id")
        
        # Update delivery status and pickup info
        updated_delivery = DeliveryRepository.update_pickup(
            db=db,
            delivery_id=delivery_id,
            picked_up_at=datetime.utcnow(),
            pickup_gps_lat=pickup_gps_lat,
            pickup_gps_lng=pickup_gps_lng,
            status='in_transit'
        )
        
        # Log activity
        try:
            ActivityLogService.log_activity(
                db=db,
                user_id=user_id,
                user_role=user_role or 'delivery_man',
                action_type='UPDATE',
                entity_type='delivery',
                entity_id=delivery_id,
                user_name=user_name,
                changes_summary=f"Stock picked up from warehouse. {len(inventory_changes)} inventory items updated.",
                new_values={
                    "status": "in_transit",
                    "picked_up_at": updated_delivery.picked_up_at.isoformat() if updated_delivery.picked_up_at else None,
                    "inventory_changes": inventory_changes
                },
                metadata={
                    "pickup_quantities": pickup_quantities,
                    "warehouse_id": delivery.warehouse_id,
                    "order_id": delivery.order_id
                }
            )
            print(f"✅ [PICKUP] Activity log created for delivery_id={delivery_id}")
        except Exception as e:
            print(f"⚠️ [PICKUP] Failed to log activity: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"✅ [PICKUP] Pickup completed successfully for delivery_id={delivery_id}")
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
                       delivery_remarks: str = None, delivery_images: List[str] = None,
                       user_id: int = None, user_role: str = None, user_name: str = None) -> Dict:
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
        
        print(f"🟢 [DELIVER] Starting delivery for delivery_id={delivery_id}, quantities={delivery_quantities}")
        
        # Update quantities
        total_delivered = 0
        total_picked = 0
        inventory_changes = []
        
        for delivery_item in delivery_items:
            order_item_id = delivery_item.order_item_id
            quantity_delivered = delivery_quantities.get(order_item_id, 0)
            quantity_picked = delivery_item.quantity_picked_up
            
            if quantity_delivered > quantity_picked:
                raise ValueError(
                    f"Cannot deliver more than picked up. "
                    f"Picked: {quantity_picked}, Delivered: {quantity_delivered}"
                )
            
            # Calculate returned quantity
            quantity_returned = quantity_picked - quantity_delivered
            
            print(f"🟢 [DELIVER] Processing order_item_id={order_item_id}, "
                  f"picked={quantity_picked}, delivered={quantity_delivered}, returned={quantity_returned}")
            
            DeliveryItemRepository.update_quantities(
                db=db,
                delivery_item_id=delivery_item.id,
                quantity_delivered=quantity_delivered,
                quantity_returned=quantity_returned
            )
            
            # If there's a difference (partially delivered), automatically return the remaining to inventory
            if quantity_returned > 0 and delivery_item.inventory_item_id:
                inventory = InventoryRepository.get_by_id(db, delivery_item.inventory_item_id)
                if inventory:
                    old_quantity = inventory.quantity
                    new_quantity = inventory.quantity + quantity_returned
                    print(f"🟢 [DELIVER] Returning to inventory: inventory_id={inventory.id}, "
                          f"item={inventory.item_name}, old_qty={old_quantity} -> new_qty={new_quantity}, "
                          f"returned_qty={quantity_returned}")
                    
                    updated_inventory = InventoryRepository.update(
                        db=db,
                        inventory_id=inventory.id,
                        quantity=new_quantity
                    )
                    
                    # Verify update by re-fetching from database
                    db.commit()  # Ensure commit
                    verified_inventory = InventoryRepository.get_by_id(db, inventory.id)
                    if verified_inventory:
                        print(f"🟢 [DELIVER] Verified inventory update: inventory_id={verified_inventory.id}, "
                              f"quantity={verified_inventory.quantity} (expected: {new_quantity})")
                        if verified_inventory.quantity != new_quantity:
                            print(f"❌ [DELIVER] ERROR: Inventory quantity mismatch! Expected {new_quantity}, got {verified_inventory.quantity}")
                    else:
                        print(f"❌ [DELIVER] ERROR: Could not verify inventory update - inventory not found!")
                    
                    inventory_changes.append({
                        "inventory_id": inventory.id,
                        "item_name": inventory.item_name,
                        "old_quantity": old_quantity,
                        "new_quantity": new_quantity,
                        "quantity_returned": quantity_returned
                    })
            elif quantity_returned > 0:
                print(f"⚠️ [DELIVER] Warning: quantity_returned={quantity_returned} but no inventory_item_id")
            
            total_delivered += quantity_delivered
            total_picked += quantity_picked
        
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
        
        print(f"🟢 [DELIVER] Delivery status updated to: {status}, total_delivered={total_delivered}, total_picked={total_picked}")
        
        # Log activity
        try:
            ActivityLogService.log_activity(
                db=db,
                user_id=user_id,
                user_role=user_role or 'delivery_man',
                action_type='UPDATE',
                entity_type='delivery',
                entity_id=delivery_id,
                user_name=user_name,
                changes_summary=f"Stock delivered to shop. Status: {status}. {len(inventory_changes)} inventory items returned.",
                new_values={
                    "status": status,
                    "delivered_at": updated_delivery.delivered_at.isoformat() if updated_delivery.delivered_at else None,
                    "total_delivered": total_delivered,
                    "total_picked": total_picked,
                    "inventory_changes": inventory_changes
                },
                metadata={
                    "delivery_quantities": delivery_quantities,
                    "warehouse_id": delivery.warehouse_id,
                    "order_id": delivery.order_id,
                    "delivery_remarks": delivery_remarks
                }
            )
            print(f"✅ [DELIVER] Activity log created for delivery_id={delivery_id}")
        except Exception as e:
            print(f"⚠️ [DELIVER] Failed to log activity: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"✅ [DELIVER] Delivery completed successfully for delivery_id={delivery_id}")
        return DeliveryService._format_delivery_data(db, updated_delivery)
    
    @staticmethod
    def return_to_warehouse(db: Session, delivery_id: int, return_quantities: Dict[int, int],
                           return_gps_lat: Decimal = None, return_gps_lng: Decimal = None,
                           return_reason: str = None,
                           user_id: int = None, user_role: str = None, user_name: str = None) -> Dict:
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
        
        if delivery.status not in ['partially_delivered', 'delivered']:
            raise ValueError(f"Cannot return. Current status: {delivery.status}")
        
        print(f"🔴 [RETURN] Starting return for delivery_id={delivery_id}, quantities={return_quantities}")
        
        # Get delivery items
        delivery_items = DeliveryItemRepository.get_by_delivery(db, delivery_id)
        print(f"🔴 [RETURN] Found {len(delivery_items)} delivery items")
        
        inventory_changes = []
        
        # Update quantities and add inventory back
        for delivery_item in delivery_items:
            order_item_id = delivery_item.order_item_id
            quantity_returned = return_quantities.get(order_item_id, 0)
            
            if quantity_returned > 0:
                # Validate return quantity
                max_returnable = delivery_item.quantity_picked_up - delivery_item.quantity_delivered
                if quantity_returned > max_returnable:
                    raise ValueError(
                        f"Cannot return more than available. "
                        f"Available to return: {max_returnable}, Requested: {quantity_returned}"
                    )
                
                # Get current returned quantity to avoid double-counting
                current_returned = delivery_item.quantity_returned or 0
                
                print(f"🔴 [RETURN] Processing order_item_id={order_item_id}, "
                      f"quantity_returned={quantity_returned}, current_returned={current_returned}")
                
                # Update delivery item
                DeliveryItemRepository.update_quantities(
                    db=db,
                    delivery_item_id=delivery_item.id,
                    quantity_returned=quantity_returned
                )
                
                # Add back to inventory if inventory_item_id is set
                # Only add the difference to avoid double-counting if already returned during delivery
                if delivery_item.inventory_item_id:
                    inventory = InventoryRepository.get_by_id(db, delivery_item.inventory_item_id)
                    if inventory:
                        # Calculate the difference: new_returned - current_returned
                        quantity_to_add = quantity_returned - current_returned
                        if quantity_to_add > 0:
                            old_quantity = inventory.quantity
                            new_quantity = inventory.quantity + quantity_to_add
                            print(f"🔴 [RETURN] Adding to inventory: inventory_id={inventory.id}, "
                                  f"item={inventory.item_name}, old_qty={old_quantity} -> new_qty={new_quantity}, "
                                  f"quantity_to_add={quantity_to_add}")
                            
                            updated_inventory = InventoryRepository.update(
                                db=db,
                                inventory_id=inventory.id,
                                quantity=new_quantity
                            )
                            
                            # Verify update by re-fetching from database
                            db.commit()  # Ensure commit
                            verified_inventory = InventoryRepository.get_by_id(db, inventory.id)
                            if verified_inventory:
                                print(f"🔴 [RETURN] Verified inventory update: inventory_id={verified_inventory.id}, "
                                      f"quantity={verified_inventory.quantity} (expected: {new_quantity})")
                                if verified_inventory.quantity != new_quantity:
                                    print(f"❌ [RETURN] ERROR: Inventory quantity mismatch! Expected {new_quantity}, got {verified_inventory.quantity}")
                            else:
                                print(f"❌ [RETURN] ERROR: Could not verify inventory update - inventory not found!")
                            
                            inventory_changes.append({
                                "inventory_id": inventory.id,
                                "item_name": inventory.item_name,
                                "old_quantity": old_quantity,
                                "new_quantity": new_quantity,
                                "quantity_added": quantity_to_add
                            })
                        else:
                            print(f"⚠️ [RETURN] No quantity to add (quantity_to_add={quantity_to_add})")
                else:
                    print(f"⚠️ [RETURN] Warning: delivery_item_id={delivery_item.id} has no inventory_item_id")
        
        # Update delivery status
        updated_delivery = DeliveryRepository.update_return(
            db=db,
            delivery_id=delivery_id,
            returned_at=datetime.utcnow(),
            return_gps_lat=return_gps_lat,
            return_gps_lng=return_gps_lng,
            return_reason=return_reason,
            status='returned'
        )
        
        print(f"🔴 [RETURN] Return status updated, {len(inventory_changes)} inventory items updated")
        
        # Log activity
        try:
            ActivityLogService.log_activity(
                db=db,
                user_id=user_id,
                user_role=user_role or 'delivery_man',
                action_type='UPDATE',
                entity_type='delivery',
                entity_id=delivery_id,
                user_name=user_name,
                changes_summary=f"Stock returned to warehouse. {len(inventory_changes)} inventory items updated.",
                new_values={
                    "status": "returned",
                    "returned_at": updated_delivery.returned_at.isoformat() if updated_delivery.returned_at else None,
                    "return_reason": return_reason,
                    "inventory_changes": inventory_changes
                },
                metadata={
                    "return_quantities": return_quantities,
                    "warehouse_id": delivery.warehouse_id,
                    "order_id": delivery.order_id
                }
            )
            print(f"✅ [RETURN] Activity log created for delivery_id={delivery_id}")
        except Exception as e:
            print(f"⚠️ [RETURN] Failed to log activity: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"✅ [RETURN] Return completed successfully for delivery_id={delivery_id}")
        return DeliveryService._format_delivery_data(db, updated_delivery)
    
    @staticmethod
    def _format_delivery_data(db: Session, delivery) -> Dict:
        """Format delivery data for API response."""
        try:
            # Get delivery items
            delivery_items = DeliveryItemRepository.get_by_delivery(db, delivery.id)
            
            # Get order items to fetch product names
            from models.order_item import OrderItem
            order_item_ids = [item.order_item_id for item in delivery_items]
            order_items = {}
            if order_item_ids:
                order_items_query = db.query(OrderItem).filter(OrderItem.id.in_(order_item_ids)).all()
                order_items = {item.id: item for item in order_items_query}
            
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
                "warehouse_id": delivery.warehouse_id,
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
                        "product_name": (lambda oi: oi.product_name if oi else None)(order_items.get(item.order_item_id)),
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
    def get_delivery_by_order(db: Session, order_id: int) -> Optional[Dict]:
        """Get delivery data for an order."""
        delivery = DeliveryRepository.get_by_order(db, order_id)
        if not delivery:
            return None
        return DeliveryService._format_delivery_data(db, delivery)
    
    @staticmethod
    def get_deliveries_by_delivery_man(db: Session, delivery_man_id: int,
                                      skip: int = 0, limit: int = 100) -> List[Dict]:
        """Get all deliveries for a delivery man."""
        deliveries = DeliveryRepository.get_by_delivery_man(
            db=db,
            delivery_man_id=delivery_man_id,
            skip=skip,
            limit=limit
        )
        return [DeliveryService._format_delivery_data(db, d) for d in deliveries]

