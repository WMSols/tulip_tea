"""
Hard Delete Entities Script
===========================
Interactive script to permanently delete entities and all related data from the database.

This script handles cascading deletes for:
- Shops (and related: credit_limit_requests, orders, payments, daily_collections, shop_visits)
- Order Bookers (and related: routes, orders, shop_visits, shop assignments)
- Delivery Men (and related: orders, daily_collections, shop_visits, delivery_man_routes)
- Routes (and related: shops.route_id set to NULL, delivery_man_routes)
- Products (and related: order_items.product_id set to NULL, inventory.product_id set to NULL)
- Inventory (individual inventory items)
- Delivery Man-Warehouse Assignments (junction table records)
- Warehouses (and related: inventory items, delivery_man_warehouse assignments)
- Shop Visits (Order Booker visits from shop_visits table)
- Deliveries (Delivery Man visits from deliveries table - shown in distributor's visits tab)
- Orders (and related: order_items deleted, deliveries.order_id set to NULL, payments.order_id set to NULL, daily_collections.order_id set to NULL)

Additional Features:
- Image Bucket Cleanup: Delete all images from Supabase storage buckets
- Sequence Reset: Reset PostgreSQL auto-increment sequences for primary keys

WARNING: This performs HARD DELETES - data cannot be recovered!
"""

import sys
import os
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from config.database import SessionLocal
from config.storage import storage
from models.shop import Shop
from models.order_booker import OrderBooker
from models.delivery_man import DeliveryMan
from models.route import Route
from models.credit_limit_request import CreditLimitRequest
from models.order import Order
from models.order_item import OrderItem
from models.payment import Payment
from models.daily_collection import DailyCollection
from models.shop_visit import ShopVisit
# RouteShop model not imported - route_shops table doesn't exist (shops have route_id directly)
from models.delivery_man_route import DeliveryManRoute
from models.product import Product
from models.inventory import Inventory
from models.delivery_man_warehouse import DeliveryManWarehouse
from models.warehouse import Warehouse
from models.zone import Zone
from models.distributor import Distributor
from models.delivery import Delivery
from models.delivery_item import DeliveryItem
from models.subsidy import Subsidy
from models.activity_log import ActivityLog
from models.super_admin import SuperAdmin
from models.visit_type import VisitType


class EntityDeleter:
    """Handles hard deletion of entities with proper foreign key handling."""
    
    def __init__(self, db: Session):
        self.db = db
        self.deleted_summary: Dict[str, int] = {}
    
    def show_menu(self):
        """Display main menu."""
        print("\n" + "="*60)
        print("🗑️  HARD DELETE ENTITIES SCRIPT")
        print("="*60)
        print("\n⚠️  WARNING: This will PERMANENTLY DELETE data from the database!")
        print("⚠️  This action CANNOT be undone!\n")
        print("Select entity type to delete:")
        print("1. Shop")
        print("2. Order Booker")
        print("3. Delivery Man")
        print("4. Route")
        print("5. Product")
        print("6. Inventory")
        print("7. Delivery Man-Warehouse Assignment")
        print("8. Warehouse")
        print("9. Shop Visit (Order Booker Visits from shop_visits table)")
        print("10. Delivery (Delivery Man Visits from deliveries table)")
        print("11. Order")
        print("\n--- Image Bucket Cleanup ---")
        print("12. Clean Shop Registrations Bucket")
        print("13. Clean Daily Collections Bucket")
        print("14. Clean Deliveries Bucket")
        print("15. Clean Shop Visits Bucket")
        print("\n--- Sequence Reset ---")
        print("16. Reset Primary Key Sequences")
        print("\n--- DANGER ZONE ---")
        print("17. ⚠️  DELETE ALL DATA FROM ALL TABLES ⚠️")
        print("\n0. Exit")
        print("-"*60)
    
    def list_shops(self) -> List[Shop]:
        """List all shops."""
        shops = self.db.query(Shop).order_by(Shop.id).all()
        return shops
    
    def list_order_bookers(self) -> List[OrderBooker]:
        """List all order bookers."""
        return self.db.query(OrderBooker).order_by(OrderBooker.id).all()
    
    def list_delivery_men(self) -> List[DeliveryMan]:
        """List all delivery men."""
        return self.db.query(DeliveryMan).order_by(DeliveryMan.id).all()
    
    def list_routes(self) -> List[Route]:
        """List all routes."""
        return self.db.query(Route).order_by(Route.id).all()
    
    def list_products(self) -> List[Product]:
        """List all products."""
        return self.db.query(Product).order_by(Product.id).all()
    
    def list_inventory(self) -> List[Inventory]:
        """List all inventory items."""
        return self.db.query(Inventory).order_by(Inventory.id).all()
    
    def list_delivery_man_warehouses(self) -> List[DeliveryManWarehouse]:
        """List all delivery man-warehouse assignments."""
        return self.db.query(DeliveryManWarehouse).order_by(DeliveryManWarehouse.id).all()
    
    def list_warehouses(self) -> List[Warehouse]:
        """List all warehouses."""
        return self.db.query(Warehouse).order_by(Warehouse.id).all()
    
    def list_shop_visits(self) -> List[ShopVisit]:
        """List all shop visits (Order Booker visits from shop_visits table)."""
        return self.db.query(ShopVisit).order_by(ShopVisit.id).all()
    
    def list_deliveries(self) -> List[Delivery]:
        """List all deliveries (Delivery Man visits from deliveries table)."""
        return self.db.query(Delivery).order_by(Delivery.id).all()
    
    def list_orders(self) -> List[Order]:
        """List all orders."""
        return self.db.query(Order).order_by(Order.id).all()
    
    def get_order_related_data(self, order_id: int) -> Dict:
        """Get all data related to an order."""
        # Query payments using raw SQL to avoid column mismatch issues
        # Only select id and order_id columns that we actually need
        payments_result = self.db.execute(
            text("SELECT id, order_id FROM payments WHERE order_id = :order_id"),
            {"order_id": order_id}
        ).fetchall()
        
        # Convert to Payment objects (minimal - just for compatibility)
        payments = []
        for row in payments_result:
            # Create a minimal Payment object with just id and order_id
            payment = Payment()
            payment.id = row[0]
            payment.order_id = row[1]
            payments.append(payment)
        
        return {
            'order_items': self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all(),
            'deliveries': self.db.query(Delivery).filter(Delivery.order_id == order_id).all(),
            'payments': payments,
            'daily_collections': self.db.query(DailyCollection).filter(DailyCollection.order_id == order_id).all(),
        }
    
    def get_shop_related_data(self, shop_id: int) -> Dict:
        """Get all data related to a shop."""
        # Query payments using raw SQL to avoid column mismatch issues
        # Only select columns that actually exist in the database
        payments_result = self.db.execute(
            text("SELECT id, shop_id, order_id, amount, payment_date FROM payments WHERE shop_id = :shop_id"),
            {"shop_id": shop_id}
        )
        payments_data = payments_result.fetchall()
        # Create minimal Payment objects for compatibility
        payments = []
        for row in payments_data:
            payment = Payment()
            payment.id = row[0]
            payment.shop_id = row[1]
            payment.order_id = row[2]
            payment.amount = row[3]
            payment.payment_date = row[4]
            payments.append(payment)
        
        return {
            'credit_limit_requests': self.db.query(CreditLimitRequest).filter(CreditLimitRequest.shop_id == shop_id).all(),
            'orders': self.db.query(Order).filter(Order.shop_id == shop_id).all(),
            'payments': payments,  # Use raw SQL query result
            'daily_collections': self.db.query(DailyCollection).filter(DailyCollection.shop_id == shop_id).all(),
            'shop_visits': self.db.query(ShopVisit).filter(ShopVisit.shop_id == shop_id).all(),
            # route_shops table doesn't exist - shops have route_id directly on shops table
        }
    
    def get_order_booker_related_data(self, order_booker_id: int) -> Dict:
        """Get all data related to an order booker."""
        return {
            'shops_created': self.db.query(Shop).filter(Shop.created_by_order_booker == order_booker_id).all(),
            'shops_assigned': self.db.query(Shop).filter(Shop.assigned_to_order_booker == order_booker_id).all(),
            'routes': self.db.query(Route).filter(Route.order_booker_id == order_booker_id).all(),
            'orders': self.db.query(Order).filter(Order.order_booker_id == order_booker_id).all(),
            'shop_visits': self.db.query(ShopVisit).filter(ShopVisit.order_booker_id == order_booker_id).all(),
        }
    
    def get_delivery_man_related_data(self, delivery_man_id: int) -> Dict:
        """Get all data related to a delivery man."""
        return {
            'orders': self.db.query(Order).filter(Order.delivery_man_id == delivery_man_id).all(),
            'daily_collections': self.db.query(DailyCollection).filter(DailyCollection.collected_by_delivery_man == delivery_man_id).all(),
            'shop_visits': self.db.query(ShopVisit).filter(ShopVisit.delivery_man_id == delivery_man_id).all(),
            'delivery_man_routes': self.db.query(DeliveryManRoute).filter(DeliveryManRoute.delivery_man_id == delivery_man_id).all(),
        }
    
    def get_route_related_data(self, route_id: int) -> Dict:
        """Get all data related to a route."""
        # Get shops that have this route_id (route_shops table doesn't exist - shops have route_id directly)
        shops_with_route = self.db.query(Shop).filter(Shop.route_id == route_id).all()
        return {
            'shops_with_route': shops_with_route,  # Shops that have this route_id
            'delivery_man_routes': self.db.query(DeliveryManRoute).filter(DeliveryManRoute.route_id == route_id).all(),
        }
    
    def get_product_related_data(self, product_id: int) -> Dict:
        """Get all data related to a product."""
        return {
            'order_items': self.db.query(OrderItem).filter(OrderItem.product_id == product_id).all(),
            'inventory_items': self.db.query(Inventory).filter(Inventory.product_id == product_id).all(),
        }
    
    def get_warehouse_related_data(self, warehouse_id: int) -> Dict:
        """Get all data related to a warehouse."""
        return {
            'inventory_items': self.db.query(Inventory).filter(Inventory.warehouse_id == warehouse_id).all(),
            'delivery_man_warehouses': self.db.query(DeliveryManWarehouse).filter(DeliveryManWarehouse.warehouse_id == warehouse_id).all(),
        }
    
    def delete_shop(self, shop_id: int) -> bool:
        """Delete a shop and all related data."""
        shop = self.db.query(Shop).filter(Shop.id == shop_id).first()
        if not shop:
            print(f"❌ Shop with ID {shop_id} not found!")
            return False
        
        related = self.get_shop_related_data(shop_id)
        
        # Show what will be deleted
        print(f"\n📋 Shop to delete: {shop.name} (ID: {shop_id})")
        print(f"\n📊 Related data that will be deleted:")
        print(f"   - Credit Limit Requests: {len(related['credit_limit_requests'])}")
        print(f"   - Orders: {len(related['orders'])}")
        print(f"   - Payments: {len(related['payments'])}")
        print(f"   - Daily Collections: {len(related['daily_collections'])}")
        print(f"   - Shop Visits: {len(related['shop_visits'])}")
        # Route info is stored directly on shop (route_id, route_sequence) - no junction table
        
        # Confirm deletion
        confirm = input(f"\n⚠️  Are you SURE you want to delete shop '{shop.name}' and ALL related data? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Delete related data
            for credit_request in related['credit_limit_requests']:
                self.db.delete(credit_request)
                self.deleted_summary['credit_limit_requests'] = self.deleted_summary.get('credit_limit_requests', 0) + 1
            
            for order in related['orders']:
                # Delete order items first (must be done before deleting order)
                order_items = self.db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                for item in order_items:
                    self.db.delete(item)
                    self.deleted_summary['order_items'] = self.deleted_summary.get('order_items', 0) + 1
                # Flush to ensure order_items are deleted before deleting order
                self.db.flush()
                # Now delete the order
                self.db.delete(order)
                self.deleted_summary['orders'] = self.deleted_summary.get('orders', 0) + 1
            
            for payment in related['payments']:
                self.db.delete(payment)
                self.deleted_summary['payments'] = self.deleted_summary.get('payments', 0) + 1
            
            for collection in related['daily_collections']:
                self.db.delete(collection)
                self.deleted_summary['daily_collections'] = self.deleted_summary.get('daily_collections', 0) + 1
            
            # Delete shop visits (must be flushed before deleting shop)
            for visit in related['shop_visits']:
                self.db.delete(visit)
                self.deleted_summary['shop_visits'] = self.deleted_summary.get('shop_visits', 0) + 1
            if related['shop_visits']:  # Only flush if there are visits to delete
                self.db.flush()  # Ensure shop_visits are deleted before shop
            
            # route_shops table doesn't exist - shops have route_id directly (no junction table to delete)
            
            # Delete the shop (after all related data is deleted and flushed)
            self.db.delete(shop)
            self.deleted_summary['shops'] = self.deleted_summary.get('shops', 0) + 1
            
            self.db.commit()
            print(f"✅ Shop '{shop.name}' (ID: {shop_id}) and all related data deleted successfully!")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting shop: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_order_booker(self, order_booker_id: int) -> bool:
        """Delete an order booker and handle related data."""
        order_booker = self.db.query(OrderBooker).filter(OrderBooker.id == order_booker_id).first()
        if not order_booker:
            print(f"❌ Order Booker with ID {order_booker_id} not found!")
            return False
        
        related = self.get_order_booker_related_data(order_booker_id)
        
        # Show what will be affected
        print(f"\n📋 Order Booker to delete: {order_booker.name} (ID: {order_booker_id})")
        print(f"\n📊 Related data that will be affected:")
        print(f"   - Shops Created: {len(related['shops_created'])} (created_by_order_booker will be set to NULL)")
        print(f"   - Shops Assigned: {len(related['shops_assigned'])} (assigned_to_order_booker will be set to NULL)")
        print(f"   - Routes: {len(related['routes'])} (order_booker_id will be set to NULL)")
        print(f"   - Orders: {len(related['orders'])} (order_booker_id will be set to NULL)")
        print(f"   - Shop Visits: {len(related['shop_visits'])} (order_booker_id will be set to NULL)")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete Order Booker '{order_booker.name}'? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Update related data (set foreign keys to NULL)
            for shop in related['shops_created']:
                shop.created_by_order_booker = None
            for shop in related['shops_assigned']:
                shop.assigned_to_order_booker = None
            for route in related['routes']:
                route.order_booker_id = None
            for order in related['orders']:
                order.order_booker_id = None
            for visit in related['shop_visits']:
                visit.order_booker_id = None
            
            # Delete the order booker
            self.db.delete(order_booker)
            self.deleted_summary['order_bookers'] = self.deleted_summary.get('order_bookers', 0) + 1
            
            self.db.commit()
            print(f"✅ Order Booker '{order_booker.name}' (ID: {order_booker_id}) deleted successfully!")
            print(f"   Related data foreign keys have been set to NULL.")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting order booker: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_delivery_man(self, delivery_man_id: int) -> bool:
        """Delete a delivery man and handle related data."""
        delivery_man = self.db.query(DeliveryMan).filter(DeliveryMan.id == delivery_man_id).first()
        if not delivery_man:
            print(f"❌ Delivery Man with ID {delivery_man_id} not found!")
            return False
        
        related = self.get_delivery_man_related_data(delivery_man_id)
        
        # Show what will be affected
        print(f"\n📋 Delivery Man to delete: {delivery_man.name} (ID: {delivery_man_id})")
        print(f"\n📊 Related data that will be affected:")
        print(f"   - Orders: {len(related['orders'])} (delivery_man_id will be set to NULL)")
        print(f"   - Daily Collections: {len(related['daily_collections'])} (collected_by_delivery_man will be set to NULL)")
        print(f"   - Shop Visits: {len(related['shop_visits'])} (delivery_man_id will be set to NULL)")
        print(f"   - Delivery Man-Route Links: {len(related['delivery_man_routes'])} (will be deleted)")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete Delivery Man '{delivery_man.name}'? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Update related data (set foreign keys to NULL)
            for order in related['orders']:
                order.delivery_man_id = None
            for collection in related['daily_collections']:
                collection.collected_by_delivery_man = None
            for visit in related['shop_visits']:
                visit.delivery_man_id = None
            
            # Delete delivery_man_routes
            for dm_route in related['delivery_man_routes']:
                self.db.delete(dm_route)
                self.deleted_summary['delivery_man_routes'] = self.deleted_summary.get('delivery_man_routes', 0) + 1
            
            # Delete the delivery man
            self.db.delete(delivery_man)
            self.deleted_summary['delivery_men'] = self.deleted_summary.get('delivery_men', 0) + 1
            
            self.db.commit()
            print(f"✅ Delivery Man '{delivery_man.name}' (ID: {delivery_man_id}) deleted successfully!")
            print(f"   Related data foreign keys have been set to NULL.")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting delivery man: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_route(self, route_id: int) -> bool:
        """Delete a route and all related data."""
        route = self.db.query(Route).filter(Route.id == route_id).first()
        if not route:
            print(f"❌ Route with ID {route_id} not found!")
            return False
        
        related = self.get_route_related_data(route_id)
        
        # Show what will be deleted
        print(f"\n📋 Route to delete: {route.name} (ID: {route_id})")
        print(f"\n📊 Related data that will be affected:")
        print(f"   - Shops with this route: {len(related['shops_with_route'])} (route_id will be set to NULL)")
        print(f"   - Delivery Man-Route Links: {len(related['delivery_man_routes'])}")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete route '{route.name}'? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Set route_id to NULL on shops (route_shops table doesn't exist - shops have route_id directly)
            for shop in related['shops_with_route']:
                shop.route_id = None
                shop.route_sequence = None
            if related['shops_with_route']:
                self.db.flush()  # Ensure route_id is cleared before route deletion
            
            for dm_route in related['delivery_man_routes']:
                self.db.delete(dm_route)
                self.deleted_summary['delivery_man_routes'] = self.deleted_summary.get('delivery_man_routes', 0) + 1
            
            # Delete the route
            self.db.delete(route)
            self.deleted_summary['routes'] = self.deleted_summary.get('routes', 0) + 1
            
            self.db.commit()
            print(f"✅ Route '{route.name}' (ID: {route_id}) and all related data deleted successfully!")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting route: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_product(self, product_id: int) -> bool:
        """Delete a product and handle related data."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            print(f"❌ Product with ID {product_id} not found!")
            return False
        
        related = self.get_product_related_data(product_id)
        
        # Show what will be affected
        print(f"\n📋 Product to delete: {product.name} (Code: {product.code}, ID: {product_id})")
        print(f"\n📊 Related data that will be affected:")
        print(f"   - Order Items: {len(related['order_items'])} (product_id will be set to NULL)")
        print(f"   - Inventory Items: {len(related['inventory_items'])} (product_id will be set to NULL)")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete Product '{product.name}' (Code: {product.code})? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Update related data (set foreign keys to NULL)
            # Note: Database will handle ON DELETE SET NULL, but we do it explicitly for clarity
            for order_item in related['order_items']:
                order_item.product_id = None
            for inventory_item in related['inventory_items']:
                inventory_item.product_id = None
            
            # Delete the product
            self.db.delete(product)
            self.deleted_summary['products'] = self.deleted_summary.get('products', 0) + 1
            
            self.db.commit()
            print(f"✅ Product '{product.name}' (Code: {product.code}, ID: {product_id}) deleted successfully!")
            print(f"   Related data foreign keys have been set to NULL.")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting product: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_inventory(self, inventory_id: int) -> bool:
        """Delete an inventory item."""
        inventory = self.db.query(Inventory).filter(Inventory.id == inventory_id).first()
        if not inventory:
            print(f"❌ Inventory item with ID {inventory_id} not found!")
            return False
        
        # Show what will be deleted
        print(f"\n📋 Inventory item to delete:")
        print(f"   - ID: {inventory_id}")
        print(f"   - Item Name: {inventory.item_name}")
        print(f"   - Item Code: {inventory.item_code or 'N/A'}")
        print(f"   - Quantity: {inventory.quantity}")
        print(f"   - Warehouse ID: {inventory.warehouse_id}")
        print(f"   - Product ID: {inventory.product_id or 'N/A'}")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete inventory item '{inventory.item_name}' (ID: {inventory_id})? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Delete the inventory item
            self.db.delete(inventory)
            self.deleted_summary['inventory'] = self.deleted_summary.get('inventory', 0) + 1
            
            self.db.commit()
            print(f"✅ Inventory item '{inventory.item_name}' (ID: {inventory_id}) deleted successfully!")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting inventory item: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_delivery_man_warehouse(self, assignment_id: int) -> bool:
        """Delete a delivery man-warehouse assignment."""
        assignment = self.db.query(DeliveryManWarehouse).filter(DeliveryManWarehouse.id == assignment_id).first()
        if not assignment:
            print(f"❌ Delivery Man-Warehouse assignment with ID {assignment_id} not found!")
            return False
        
        # Get related info for display
        delivery_man = self.db.query(DeliveryMan).filter(DeliveryMan.id == assignment.delivery_man_id).first()
        warehouse = self.db.query(Warehouse).filter(Warehouse.id == assignment.warehouse_id).first()
        
        # Show what will be deleted
        print(f"\n📋 Delivery Man-Warehouse assignment to delete:")
        print(f"   - Assignment ID: {assignment_id}")
        print(f"   - Delivery Man: {delivery_man.name if delivery_man else 'N/A'} (ID: {assignment.delivery_man_id})")
        print(f"   - Warehouse: {warehouse.name if warehouse else 'N/A'} (ID: {assignment.warehouse_id})")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete this assignment? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Delete the assignment
            self.db.delete(assignment)
            self.deleted_summary['delivery_man_warehouses'] = self.deleted_summary.get('delivery_man_warehouses', 0) + 1
            
            self.db.commit()
            print(f"✅ Delivery Man-Warehouse assignment (ID: {assignment_id}) deleted successfully!")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting assignment: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_warehouse(self, warehouse_id: int) -> bool:
        """Delete a warehouse and all related data."""
        warehouse = self.db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        if not warehouse:
            print(f"❌ Warehouse with ID {warehouse_id} not found!")
            return False
        
        related = self.get_warehouse_related_data(warehouse_id)
        
        # Show what will be deleted
        print(f"\n📋 Warehouse to delete: {warehouse.name} (ID: {warehouse_id})")
        print(f"\n📊 Related data that will be deleted:")
        print(f"   - Inventory Items: {len(related['inventory_items'])}")
        print(f"   - Delivery Man-Warehouse Assignments: {len(related['delivery_man_warehouses'])}")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete warehouse '{warehouse.name}' and ALL related data? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Delete related data
            for inventory_item in related['inventory_items']:
                self.db.delete(inventory_item)
                self.deleted_summary['inventory'] = self.deleted_summary.get('inventory', 0) + 1
            
            for assignment in related['delivery_man_warehouses']:
                self.db.delete(assignment)
                self.deleted_summary['delivery_man_warehouses'] = self.deleted_summary.get('delivery_man_warehouses', 0) + 1
            
            # Flush to ensure related data is deleted before warehouse
            if related['inventory_items'] or related['delivery_man_warehouses']:
                self.db.flush()
            
            # Delete the warehouse
            self.db.delete(warehouse)
            self.deleted_summary['warehouses'] = self.deleted_summary.get('warehouses', 0) + 1
            
            self.db.commit()
            print(f"✅ Warehouse '{warehouse.name}' (ID: {warehouse_id}) and all related data deleted successfully!")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting warehouse: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_shop_visit(self, visit_id: int) -> bool:
        """
        Delete a shop visit from shop_visits table (Order Booker visits only).
        
        Note: This deletes from shop_visits table only.
        For Delivery Man visits (deliveries), use delete_delivery() instead.
        """
        visit = self.db.query(ShopVisit).filter(ShopVisit.id == visit_id).first()
        if not visit:
            print(f"❌ Shop Visit with ID {visit_id} not found!")
            return False
        
        # Get related data that references this visit
        related_orders = self.db.query(Order).filter(Order.visit_id == visit_id).all()
        related_collections = self.db.query(DailyCollection).filter(DailyCollection.visit_id == visit_id).all()
        related_visit_types = self.db.query(VisitType).filter(VisitType.visit_id == visit_id).all()
        
        # Determine visit type for display
        visit_type_label = "Unknown"
        if visit.order_booker_id and visit.delivery_man_id:
            visit_type_label = "Order Booker & Delivery Man Visit"
        elif visit.order_booker_id:
            visit_type_label = "Order Booker Visit"
        elif visit.delivery_man_id:
            visit_type_label = "Delivery Man Visit"
        
        # Show what will be affected
        print(f"\n📋 Shop Visit to delete ({visit_type_label}):")
        print(f"   - Visit ID: {visit_id}")
        print(f"   - Shop ID: {visit.shop_id or 'N/A'}")
        if visit.order_booker_id:
            order_booker = self.db.query(OrderBooker).filter(OrderBooker.id == visit.order_booker_id).first()
            ob_name = order_booker.name if order_booker else f"ID {visit.order_booker_id}"
            print(f"   - Order Booker: {ob_name} (ID: {visit.order_booker_id})")
        if visit.delivery_man_id:
            delivery_man = self.db.query(DeliveryMan).filter(DeliveryMan.id == visit.delivery_man_id).first()
            dm_name = delivery_man.name if delivery_man else f"ID {visit.delivery_man_id}"
            print(f"   - Delivery Man: {dm_name} (ID: {visit.delivery_man_id})")
        print(f"   - Visit Date: {visit.visit_date or 'N/A'}")
        
        print(f"\n📊 Related data that will be affected:")
        print(f"   - Orders: {len(related_orders)} (visit_id will be set to NULL)")
        print(f"   - Daily Collections: {len(related_collections)} (visit_id will be set to NULL)")
        print(f"   - Visit Types: {len(related_visit_types)} (will be deleted)")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete Shop Visit (ID: {visit_id})? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Delete visit types first (they reference visit_id with CASCADE, but we'll delete explicitly)
            for vt in related_visit_types:
                self.db.delete(vt)
            self.deleted_summary['visit_types'] = self.deleted_summary.get('visit_types', 0) + len(related_visit_types)
            
            # Set foreign keys to NULL in orders (don't delete orders, just unlink them)
            for order in related_orders:
                order.visit_id = None
            self.deleted_summary['orders_updated'] = self.deleted_summary.get('orders_updated', 0) + len(related_orders)
            
            # Set foreign keys to NULL in daily collections (don't delete collections, just unlink them)
            for collection in related_collections:
                collection.visit_id = None
            self.deleted_summary['collections_updated'] = self.deleted_summary.get('collections_updated', 0) + len(related_collections)
            
            # Flush to ensure foreign keys are updated before deleting visit
            if related_orders or related_collections or related_visit_types:
                self.db.flush()
            
            # Delete the shop visit
            self.db.delete(visit)
            self.deleted_summary['shop_visits'] = self.deleted_summary.get('shop_visits', 0) + 1
            
            self.db.commit()
            print(f"✅ Shop Visit (ID: {visit_id}) deleted successfully!")
            if related_orders:
                print(f"   - {len(related_orders)} order(s) unlinked (visit_id set to NULL)")
            if related_collections:
                print(f"   - {len(related_collections)} collection(s) unlinked (visit_id set to NULL)")
            if related_visit_types:
                print(f"   - {len(related_visit_types)} visit type(s) deleted")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting shop visit: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_delivery(self, delivery_id: int) -> bool:
        """
        Delete a delivery (Delivery Man visit) from deliveries table and handle related data (foreign keys).
        
        Note: Deliveries are Delivery Man visits shown in distributor's visits tab.
        This is separate from shop_visits table (which has Order Booker visits).
        """
        delivery = self.db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if not delivery:
            print(f"❌ Delivery with ID {delivery_id} not found!")
            return False
        
        # Get related data that references this delivery
        related_delivery_items = self.db.query(DeliveryItem).filter(DeliveryItem.delivery_id == delivery_id).all()
        
        # Get delivery man and order info for display
        delivery_man = None
        if delivery.delivery_man_id:
            delivery_man = self.db.query(DeliveryMan).filter(DeliveryMan.id == delivery.delivery_man_id).first()
        
        order = None
        if delivery.order_id:
            order = self.db.query(Order).filter(Order.id == delivery.order_id).first()
        
        shop = None
        if order and order.shop_id:
            shop = self.db.query(Shop).filter(Shop.id == order.shop_id).first()
        
        # Show what will be affected
        print(f"\n📋 Delivery to delete (Delivery Man Visit):")
        print(f"   - Delivery ID: {delivery_id}")
        if delivery_man:
            print(f"   - Delivery Man: {delivery_man.name} (ID: {delivery.delivery_man_id})")
        if shop:
            print(f"   - Shop: {shop.name} (ID: {order.shop_id})")
        if order:
            print(f"   - Order ID: {delivery.order_id}")
        print(f"   - Status: {delivery.status}")
        if delivery.picked_up_at:
            print(f"   - Picked Up At: {delivery.picked_up_at}")
        if delivery.delivered_at:
            print(f"   - Delivered At: {delivery.delivered_at}")
        
        print(f"\n📊 Related data that will be deleted:")
        print(f"   - Delivery Items: {len(related_delivery_items)} (will be deleted)")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete Delivery (ID: {delivery_id})? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Delete delivery items first (they reference delivery_id)
            for item in related_delivery_items:
                self.db.delete(item)
            self.deleted_summary['delivery_items'] = self.deleted_summary.get('delivery_items', 0) + len(related_delivery_items)
            
            # Flush to ensure delivery items are deleted before deleting delivery
            if related_delivery_items:
                self.db.flush()
            
            # Delete the delivery
            # Note: order_id has ondelete="SET NULL", so order will remain but order_id will be set to NULL
            self.db.delete(delivery)
            self.deleted_summary['deliveries'] = self.deleted_summary.get('deliveries', 0) + 1
            
            self.db.commit()
            print(f"✅ Delivery (ID: {delivery_id}) deleted successfully!")
            if related_delivery_items:
                print(f"   - {len(related_delivery_items)} delivery item(s) deleted")
            if delivery.order_id:
                print(f"   - Order (ID: {delivery.order_id}) unlinked (order_id set to NULL)")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting delivery: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_order(self, order_id: int) -> bool:
        """
        Delete an order and handle related data (foreign keys).
        
        Handles:
        - Order Items (deleted - CASCADE)
        - Deliveries (order_id set to NULL - SET NULL)
        - Payments (order_id set to NULL manually)
        - Daily Collections (order_id set to NULL manually)
        """
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            print(f"❌ Order with ID {order_id} not found!")
            return False
        
        related = self.get_order_related_data(order_id)
        
        # Get shop and order booker info for display
        shop = None
        if order.shop_id:
            shop = self.db.query(Shop).filter(Shop.id == order.shop_id).first()
        
        order_booker = None
        if order.order_booker_id:
            order_booker = self.db.query(OrderBooker).filter(OrderBooker.id == order.order_booker_id).first()
        
        delivery_man = None
        if order.delivery_man_id:
            delivery_man = self.db.query(DeliveryMan).filter(DeliveryMan.id == order.delivery_man_id).first()
        
        # Show what will be affected
        print(f"\n📋 Order to delete:")
        print(f"   - Order ID: {order_id}")
        if shop:
            print(f"   - Shop: {shop.name} (ID: {order.shop_id})")
        if order_booker:
            print(f"   - Order Booker: {order_booker.name} (ID: {order.order_booker_id})")
        if delivery_man:
            print(f"   - Delivery Man: {delivery_man.name} (ID: {order.delivery_man_id})")
        print(f"   - Status: {order.status}")
        print(f"   - Total Amount: {order.total_amount}")
        if order.scheduled_date:
            print(f"   - Scheduled Date: {order.scheduled_date}")
        
        print(f"\n📊 Related data that will be affected:")
        print(f"   - Order Items: {len(related['order_items'])} (will be deleted - CASCADE)")
        print(f"   - Deliveries: {len(related['deliveries'])} (order_id will be set to NULL - SET NULL)")
        print(f"   - Payments: {len(related['payments'])} (order_id will be set to NULL)")
        print(f"   - Daily Collections: {len(related['daily_collections'])} (order_id will be set to NULL)")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete Order (ID: {order_id})? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Delete order items first (they have CASCADE, but we'll delete explicitly for clarity)
            for item in related['order_items']:
                self.db.delete(item)
            self.deleted_summary['order_items'] = self.deleted_summary.get('order_items', 0) + len(related['order_items'])
            
            # Set foreign keys to NULL in payments (no CASCADE, must do manually)
            # Use raw SQL to avoid column mismatch issues
            if related['payments']:
                self.db.execute(
                    text("UPDATE payments SET order_id = NULL WHERE order_id = :order_id"),
                    {"order_id": order_id}
                )
                self.deleted_summary['payments_updated'] = self.deleted_summary.get('payments_updated', 0) + len(related['payments'])
            
            # Set foreign keys to NULL in daily collections (no CASCADE, must do manually)
            for collection in related['daily_collections']:
                collection.order_id = None
            self.deleted_summary['collections_updated'] = self.deleted_summary.get('collections_updated', 0) + len(related['daily_collections'])
            
            # Note: Deliveries have ondelete="SET NULL", so order_id will be set to NULL automatically
            # But we'll update them explicitly for clarity and to show what's happening
            for delivery in related['deliveries']:
                delivery.order_id = None
            self.deleted_summary['deliveries_updated'] = self.deleted_summary.get('deliveries_updated', 0) + len(related['deliveries'])
            
            # Flush to ensure foreign keys are updated before deleting order
            if related['order_items'] or related['payments'] or related['daily_collections'] or related['deliveries']:
                self.db.flush()
            
            # Delete the order
            self.db.delete(order)
            self.deleted_summary['orders'] = self.deleted_summary.get('orders', 0) + 1
            
            self.db.commit()
            print(f"✅ Order (ID: {order_id}) deleted successfully!")
            if related['order_items']:
                print(f"   - {len(related['order_items'])} order item(s) deleted")
            if related['deliveries']:
                print(f"   - {len(related['deliveries'])} delivery/deliveries unlinked (order_id set to NULL)")
            if related['payments']:
                print(f"   - {len(related['payments'])} payment(s) unlinked (order_id set to NULL)")
            if related['daily_collections']:
                print(f"   - {len(related['daily_collections'])} collection(s) unlinked (order_id set to NULL)")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting order: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def parse_ids(self, ids_input: str) -> List[int]:
        """Parse comma or space separated IDs from user input."""
        if not ids_input:
            return []
        
        # Replace commas with spaces and split
        ids_str = ids_input.replace(',', ' ').split()
        ids = []
        for id_str in ids_str:
            try:
                ids.append(int(id_str.strip()))
            except ValueError:
                continue
        return ids
    
    def show_summary(self):
        """Show summary of deleted entities."""
        if not self.deleted_summary:
            return
        
        print("\n" + "="*60)
        print("📊 DELETION SUMMARY")
        print("="*60)
        for entity_type, count in sorted(self.deleted_summary.items()):
            print(f"   {entity_type}: {count}")
        print("="*60)
    
    def list_bucket_files(self, bucket_name: str) -> List[str]:
        """List all files in a Supabase storage bucket."""
        if not storage.client:
            print(f"❌ Supabase storage client not initialized!")
            return []
        
        try:
            # Recursively get all files from all folders
            files = []
            
            def get_all_files(path: str = "") -> List[str]:
                """Recursively list all files in a bucket path."""
                files_list = []
                try:
                    items = storage.client.storage.from_(bucket_name).list(path)
                    
                    if items:
                        for item in items:
                            # Handle both dict and object responses
                            if isinstance(item, dict):
                                item_name = item.get('name', '')
                                item_id = item.get('id')
                            else:
                                item_name = getattr(item, 'name', '')
                                item_id = getattr(item, 'id', None)
                            
                            item_path = f"{path}/{item_name}" if path else item_name
                            
                            # If it has an 'id', it's a file; otherwise it's a folder
                            if item_id:
                                # It's a file
                                files_list.append(item_path)
                            else:
                                # It's a folder, recurse
                                sub_files = get_all_files(item_path)
                                files_list.extend(sub_files)
                    
                    return files_list
                except Exception as e:
                    # If listing fails, try to continue
                    print(f"   ⚠️  Warning listing path '{path}': {e}")
                    return files_list
            
            files = get_all_files()
            return files
            
        except Exception as e:
            print(f"❌ Error listing files in bucket '{bucket_name}': {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def clean_bucket(self, bucket_name: str) -> bool:
        """Delete all files from a Supabase storage bucket."""
        if not storage.client:
            print(f"❌ Supabase storage client not initialized!")
            return False
        
        print(f"\n📋 Cleaning bucket: {bucket_name}")
        
        # List all files
        files = self.list_bucket_files(bucket_name)
        
        if not files:
            print(f"✅ Bucket '{bucket_name}' is already empty!")
            return True
        
        print(f"\n📊 Found {len(files)} file(s) in bucket '{bucket_name}'")
        print(f"   Sample files (first 5):")
        for i, file_path in enumerate(files[:5]):
            print(f"      - {file_path}")
        if len(files) > 5:
            print(f"      ... and {len(files) - 5} more")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete ALL {len(files)} file(s) from bucket '{bucket_name}'? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Bucket cleanup cancelled.")
            return False
        
        try:
            deleted_count = 0
            failed_count = 0
            
            # Delete files in batches (Supabase allows batch deletion)
            batch_size = 100
            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]
                try:
                    storage.client.storage.from_(bucket_name).remove(batch)
                    deleted_count += len(batch)
                    print(f"   ✅ Deleted batch {i//batch_size + 1} ({len(batch)} files)")
                except Exception as batch_error:
                    print(f"   ⚠️  Error deleting batch {i//batch_size + 1}: {batch_error}")
                    # Try deleting individually
                    for file_path in batch:
                        try:
                            storage.client.storage.from_(bucket_name).remove([file_path])
                            deleted_count += 1
                        except Exception:
                            failed_count += 1
                            print(f"      ❌ Failed to delete: {file_path}")
            
            print(f"\n✅ Bucket cleanup completed!")
            print(f"   - Deleted: {deleted_count} file(s)")
            if failed_count > 0:
                print(f"   - Failed: {failed_count} file(s)")
            
            self.deleted_summary[f'bucket_{bucket_name}'] = deleted_count
            return True
            
        except Exception as e:
            print(f"❌ Error cleaning bucket: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def reset_sequence(self, table_name: str, sequence_name: str = None) -> bool:
        """Reset a PostgreSQL sequence to start from 1 or continue from max ID."""
        if not sequence_name:
            # Default sequence name: {table_name}_id_seq
            sequence_name = f"{table_name}_id_seq"
        
        try:
            # Check if table exists
            table_check = self.db.execute(text(
                f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}')"
            ))
            table_exists = table_check.scalar()
            
            if not table_exists:
                print(f"   ⚠️  Table '{table_name}' does not exist, skipping")
                return False
            
            # Get current max ID from table
            result = self.db.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}"))
            max_id = result.scalar() or 0
            
            # Reset sequence to max_id + 1 (so next insert starts from max_id + 1)
            # Or set to 1 if table is empty
            next_val = max_id + 1 if max_id > 0 else 1
            
            # Check if sequence exists
            seq_check = self.db.execute(text(
                f"SELECT EXISTS(SELECT 1 FROM pg_class WHERE relname = '{sequence_name}')"
            ))
            seq_exists = seq_check.scalar()
            
            if not seq_exists:
                print(f"   ⚠️  Sequence '{sequence_name}' does not exist for table '{table_name}'")
                return False
            
            # Reset sequence (setval with false means next nextval() will return the set value)
            self.db.execute(text(f"SELECT setval('{sequence_name}', {next_val}, false)"))
            self.db.commit()
            
            print(f"   ✅ Reset '{sequence_name}' to {next_val} (max ID: {max_id})")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"   ❌ Error resetting sequence for '{table_name}': {e}")
            return False
    
    def reset_all_sequences(self) -> bool:
        """Reset all primary key sequences for all tables."""
        print("\n📋 Resetting Primary Key Sequences")
        print("\nThis will reset all auto-increment sequences so new entries start from 1")
        print("(or continue from the highest existing ID if data exists).\n")
        
        # List of all tables with primary key sequences
        tables = [
            'shops', 'order_bookers', 'delivery_men', 'routes', 'products',
            'inventory', 'delivery_man_warehouses', 'warehouses', 'zones',
            'distributors', 'orders', 'order_items', 'payments', 'daily_collections',
            'shop_visits', 'credit_limit_requests', 'delivery_man_routes',
            'activity_logs', 'super_admins', 'visit_types'
        ]
        
        print(f"📊 Tables to reset: {len(tables)}")
        for table in tables:
            print(f"   - {table}")
        
        confirm = input(f"\n⚠️  Are you SURE you want to reset sequences for ALL {len(tables)} tables? (type 'reset' to confirm): ")
        if confirm != 'reset':
            print("❌ Sequence reset cancelled.")
            return False
        
        try:
            success_count = 0
            failed_count = 0
            
            for table in tables:
                if self.reset_sequence(table):
                    success_count += 1
                else:
                    failed_count += 1
            
            print(f"\n✅ Sequence reset completed!")
            print(f"   - Success: {success_count} table(s)")
            if failed_count > 0:
                print(f"   - Failed: {failed_count} table(s)")
            
            self.deleted_summary['sequences_reset'] = success_count
            return True
            
        except Exception as e:
            print(f"❌ Error resetting sequences: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_all_data(self) -> bool:
        """
        Delete ALL data from ALL tables in the correct order to respect foreign key constraints.
        
        Deletion order (child tables first, then parents):
        1. Junction/child tables: order_items, delivery_items, visit_types, delivery_man_routes, delivery_man_warehouses
        1a. Clear route_id on shops (route_shops table doesn't exist - shops have route_id directly)
        2. Dependent tables: orders, deliveries, shop_visits, daily_collections, payments, credit_limit_requests, activity_logs
        3. Main entities: shops, products, inventory, warehouses
        4. User entities: order_bookers, delivery_men
        5. Organizational: routes, zones, distributors
        6. System: subsidies, super_admins
        """
        print("\n" + "="*60)
        print("⚠️  ⚠️  ⚠️  DANGER ZONE ⚠️  ⚠️  ⚠️")
        print("="*60)
        print("\n⚠️  WARNING: This will DELETE ALL DATA from ALL TABLES!")
        print("⚠️  This includes:")
        print("   - All shops, orders, payments, collections")
        print("   - All order bookers, delivery men, distributors")
        print("   - All routes, zones, warehouses, products")
        print("   - All activity logs, visits, deliveries")
        print("   - EVERYTHING in the database!")
        print("\n⚠️  This action CANNOT be undone!")
        print("⚠️  Make sure you have a backup if needed!")
        
        confirm1 = input("\nType 'DELETE ALL' (exactly) to proceed: ").strip()
        if confirm1 != 'DELETE ALL':
            print("❌ Deletion cancelled.")
            return False
        
        confirm2 = input("\n⚠️  Are you ABSOLUTELY SURE? Type 'YES DELETE EVERYTHING' (exactly): ").strip()
        if confirm2 != 'YES DELETE EVERYTHING':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            print("\n🗑️  Starting deletion of all data...")
            
            # Step 1: Delete junction/child tables first
            print("\n📋 Step 1: Deleting junction/child tables...")
            
            # Order Items
            order_items = self.db.query(OrderItem).all()
            for item in order_items:
                self.db.delete(item)
            self.deleted_summary['order_items'] = len(order_items)
            print(f"   ✅ Deleted {len(order_items)} order items")
            
            # Delivery Items
            delivery_items = self.db.query(DeliveryItem).all()
            for item in delivery_items:
                self.db.delete(item)
            self.deleted_summary['delivery_items'] = len(delivery_items)
            print(f"   ✅ Deleted {len(delivery_items)} delivery items")
            
            # Visit Types
            visit_types = self.db.query(VisitType).all()
            for vt in visit_types:
                self.db.delete(vt)
            self.deleted_summary['visit_types'] = len(visit_types)
            print(f"   ✅ Deleted {len(visit_types)} visit types")
            
            # Route Shops
            # route_shops table doesn't exist - shops have route_id directly
            # Set route_id to NULL on all shops instead
            shops_with_routes = self.db.query(Shop).filter(Shop.route_id.isnot(None)).all()
            for shop in shops_with_routes:
                shop.route_id = None
                shop.route_sequence = None
            self.deleted_summary['shops_route_cleared'] = len(shops_with_routes)
            print(f"   ✅ Cleared route_id from {len(shops_with_routes)} shops (route_shops table doesn't exist)")
            
            # Delivery Man Routes
            delivery_man_routes = self.db.query(DeliveryManRoute).all()
            for dmr in delivery_man_routes:
                self.db.delete(dmr)
            self.deleted_summary['delivery_man_routes'] = len(delivery_man_routes)
            print(f"   ✅ Deleted {len(delivery_man_routes)} delivery man-route links")
            
            # Delivery Man Warehouses
            delivery_man_warehouses = self.db.query(DeliveryManWarehouse).all()
            for dmw in delivery_man_warehouses:
                self.db.delete(dmw)
            self.deleted_summary['delivery_man_warehouses'] = len(delivery_man_warehouses)
            print(f"   ✅ Deleted {len(delivery_man_warehouses)} delivery man-warehouse links")
            
            self.db.flush()
            
            # Step 2: Delete dependent tables
            print("\n📋 Step 2: Deleting dependent tables...")
            
            # First, unlink shop visits from orders and daily collections (set visit_id to NULL)
            # This prevents foreign key errors when deleting shop visits
            orders_with_visits = self.db.query(Order).filter(Order.visit_id.isnot(None)).all()
            for order in orders_with_visits:
                order.visit_id = None
            if orders_with_visits:
                print(f"   ✅ Unlinked {len(orders_with_visits)} orders from shop visits")
            
            collections_with_visits = self.db.query(DailyCollection).filter(DailyCollection.visit_id.isnot(None)).all()
            for collection in collections_with_visits:
                collection.visit_id = None
            if collections_with_visits:
                print(f"   ✅ Unlinked {len(collections_with_visits)} collections from shop visits")
            
            self.db.flush()  # Ensure foreign keys are updated before deleting shop visits
            
            # Now delete orders (visit_id already set to NULL)
            orders = self.db.query(Order).all()
            for order in orders:
                self.db.delete(order)
            self.deleted_summary['orders'] = len(orders)
            print(f"   ✅ Deleted {len(orders)} orders")
            
            # Deliveries
            deliveries = self.db.query(Delivery).all()
            for delivery in deliveries:
                self.db.delete(delivery)
            self.deleted_summary['deliveries'] = len(deliveries)
            print(f"   ✅ Deleted {len(deliveries)} deliveries")
            
            # Daily Collections (visit_id already set to NULL)
            daily_collections = self.db.query(DailyCollection).all()
            for collection in daily_collections:
                self.db.delete(collection)
            self.deleted_summary['daily_collections'] = len(daily_collections)
            print(f"   ✅ Deleted {len(daily_collections)} daily collections")
            
            # Shop Visits (now safe to delete - no foreign key references)
            shop_visits = self.db.query(ShopVisit).all()
            for visit in shop_visits:
                self.db.delete(visit)
            self.deleted_summary['shop_visits'] = len(shop_visits)
            print(f"   ✅ Deleted {len(shop_visits)} shop visits")
            
            # Payments (use raw SQL to avoid column mismatch)
            payments_result = self.db.execute(text("SELECT COUNT(*) FROM payments"))
            payment_count = payments_result.scalar() or 0
            if payment_count > 0:
                self.db.execute(text("DELETE FROM payments"))
            self.deleted_summary['payments'] = payment_count
            print(f"   ✅ Deleted {payment_count} payments")
            
            # Credit Limit Requests
            credit_requests = self.db.query(CreditLimitRequest).all()
            for req in credit_requests:
                self.db.delete(req)
            self.deleted_summary['credit_limit_requests'] = len(credit_requests)
            print(f"   ✅ Deleted {len(credit_requests)} credit limit requests")
            
            # Activity Logs
            activity_logs = self.db.query(ActivityLog).all()
            for log in activity_logs:
                self.db.delete(log)
            self.deleted_summary['activity_logs'] = len(activity_logs)
            print(f"   ✅ Deleted {len(activity_logs)} activity logs")
            
            self.db.flush()
            
            # Step 3: Delete main entities
            print("\n📋 Step 3: Deleting main entities...")
            
            # Shops
            shops = self.db.query(Shop).all()
            for shop in shops:
                self.db.delete(shop)
            self.deleted_summary['shops'] = len(shops)
            print(f"   ✅ Deleted {len(shops)} shops")
            
            # Inventory
            inventory_items = self.db.query(Inventory).all()
            for inv in inventory_items:
                self.db.delete(inv)
            self.deleted_summary['inventory'] = len(inventory_items)
            print(f"   ✅ Deleted {len(inventory_items)} inventory items")
            
            # Products
            products = self.db.query(Product).all()
            for product in products:
                self.db.delete(product)
            self.deleted_summary['products'] = len(products)
            print(f"   ✅ Deleted {len(products)} products")
            
            # Warehouses
            warehouses = self.db.query(Warehouse).all()
            for warehouse in warehouses:
                self.db.delete(warehouse)
            self.deleted_summary['warehouses'] = len(warehouses)
            print(f"   ✅ Deleted {len(warehouses)} warehouses")
            
            self.db.flush()
            
            # Step 4: Delete user entities
            print("\n📋 Step 4: Deleting user entities...")
            
            # Order Bookers
            order_bookers = self.db.query(OrderBooker).all()
            for ob in order_bookers:
                self.db.delete(ob)
            self.deleted_summary['order_bookers'] = len(order_bookers)
            print(f"   ✅ Deleted {len(order_bookers)} order bookers")
            
            # Delivery Men
            delivery_men = self.db.query(DeliveryMan).all()
            for dm in delivery_men:
                self.db.delete(dm)
            self.deleted_summary['delivery_men'] = len(delivery_men)
            print(f"   ✅ Deleted {len(delivery_men)} delivery men")
            
            self.db.flush()
            
            # Step 5: Delete organizational entities
            print("\n📋 Step 5: Deleting organizational entities...")
            
            # Routes
            routes = self.db.query(Route).all()
            for route in routes:
                self.db.delete(route)
            self.deleted_summary['routes'] = len(routes)
            print(f"   ✅ Deleted {len(routes)} routes")
            
            # Zones
            zones = self.db.query(Zone).all()
            for zone in zones:
                self.db.delete(zone)
            self.deleted_summary['zones'] = len(zones)
            print(f"   ✅ Deleted {len(zones)} zones")
            
            # Distributors
            distributors = self.db.query(Distributor).all()
            for distributor in distributors:
                self.db.delete(distributor)
            self.deleted_summary['distributors'] = len(distributors)
            print(f"   ✅ Deleted {len(distributors)} distributors")
            
            self.db.flush()
            
            # Step 6: Delete system entities
            print("\n📋 Step 6: Deleting system entities...")
            
            # Subsidies
            subsidies = self.db.query(Subsidy).all()
            for subsidy in subsidies:
                self.db.delete(subsidy)
            self.deleted_summary['subsidies'] = len(subsidies)
            print(f"   ✅ Deleted {len(subsidies)} subsidies")
            
            # Super Admins
            super_admins = self.db.query(SuperAdmin).all()
            for admin in super_admins:
                self.db.delete(admin)
            self.deleted_summary['super_admins'] = len(super_admins)
            print(f"   ✅ Deleted {len(super_admins)} super admins")
            
            # Commit all deletions
            self.db.commit()
            
            print("\n" + "="*60)
            print("✅ ALL DATA DELETED SUCCESSFULLY!")
            print("="*60)
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"\n❌ Error deleting all data: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main interactive loop."""
    db: Session = SessionLocal()
    deleter = EntityDeleter(db)
    
    try:
        while True:
            deleter.show_menu()
            choice = input("\nEnter your choice (0-17): ").strip()
            
            if choice == '0':
                print("\n👋 Exiting...")
                break
            
            elif choice == '1':  # Shop
                shops = deleter.list_shops()
                if not shops:
                    print("\n❌ No shops found in database.")
                    continue
                
                print(f"\n📋 Available Shops ({len(shops)} total):")
                for shop in shops:
                    print(f"   {shop.id}. {shop.name} (Phone: {shop.owner_phone or 'N/A'})")
                print(f"\n📌 Available Shop IDs: {', '.join(str(s.id) for s in shops)}")
                
                try:
                    ids_input = input("\nEnter Shop ID(s) to delete (comma or space separated for multiple): ").strip()
                    shop_ids = deleter.parse_ids(ids_input)
                    if not shop_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(shop_ids) == 1:
                        deleter.delete_shop(shop_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(shop_ids)} shops!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for shop_id in shop_ids:
                                if deleter.delete_shop(shop_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(shop_ids)} shops.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Shop ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '2':  # Order Booker
                order_bookers = deleter.list_order_bookers()
                if not order_bookers:
                    print("\n❌ No order bookers found in database.")
                    continue
                
                print(f"\n📋 Available Order Bookers ({len(order_bookers)} total):")
                for ob in order_bookers:
                    print(f"   {ob.id}. {ob.name} (Phone: {ob.phone})")
                print(f"\n📌 Available Order Booker IDs: {', '.join(str(ob.id) for ob in order_bookers)}")
                
                try:
                    ids_input = input("\nEnter Order Booker ID(s) to delete (comma or space separated for multiple): ").strip()
                    ob_ids = deleter.parse_ids(ids_input)
                    if not ob_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(ob_ids) == 1:
                        deleter.delete_order_booker(ob_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(ob_ids)} order bookers!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for ob_id in ob_ids:
                                if deleter.delete_order_booker(ob_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(ob_ids)} order bookers.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Order Booker ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '3':  # Delivery Man
                delivery_men = deleter.list_delivery_men()
                if not delivery_men:
                    print("\n❌ No delivery men found in database.")
                    continue
                
                print(f"\n📋 Available Delivery Men ({len(delivery_men)} total):")
                for dm in delivery_men:
                    print(f"   {dm.id}. {dm.name} (Phone: {dm.phone})")
                print(f"\n📌 Available Delivery Man IDs: {', '.join(str(dm.id) for dm in delivery_men)}")
                
                try:
                    ids_input = input("\nEnter Delivery Man ID(s) to delete (comma or space separated for multiple): ").strip()
                    dm_ids = deleter.parse_ids(ids_input)
                    if not dm_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(dm_ids) == 1:
                        deleter.delete_delivery_man(dm_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(dm_ids)} delivery men!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for dm_id in dm_ids:
                                if deleter.delete_delivery_man(dm_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(dm_ids)} delivery men.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Delivery Man ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '4':  # Route
                routes = deleter.list_routes()
                if not routes:
                    print("\n❌ No routes found in database.")
                    continue
                
                print(f"\n📋 Available Routes ({len(routes)} total):")
                for route in routes:
                    print(f"   {route.id}. {route.name} (Zone ID: {route.zone_id or 'N/A'})")
                print(f"\n📌 Available Route IDs: {', '.join(str(r.id) for r in routes)}")
                
                try:
                    ids_input = input("\nEnter Route ID(s) to delete (comma or space separated for multiple): ").strip()
                    route_ids = deleter.parse_ids(ids_input)
                    if not route_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(route_ids) == 1:
                        deleter.delete_route(route_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(route_ids)} routes!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for route_id in route_ids:
                                if deleter.delete_route(route_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(route_ids)} routes.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Route ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '5':  # Product
                products = deleter.list_products()
                if not products:
                    print("\n❌ No products found in database.")
                    continue
                
                print(f"\n📋 Available Products ({len(products)} total):")
                for product in products:
                    status = "Active" if product.is_active and not product.deleted_at else "Inactive/Deleted"
                    print(f"   {product.id}. {product.name} (Code: {product.code}, Status: {status})")
                print(f"\n📌 Available Product IDs: {', '.join(str(p.id) for p in products)}")
                
                try:
                    ids_input = input("\nEnter Product ID(s) to delete (comma or space separated for multiple): ").strip()
                    product_ids = deleter.parse_ids(ids_input)
                    if not product_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(product_ids) == 1:
                        deleter.delete_product(product_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(product_ids)} products!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for product_id in product_ids:
                                if deleter.delete_product(product_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(product_ids)} products.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Product ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '6':  # Inventory
                inventory_items = deleter.list_inventory()
                if not inventory_items:
                    print("\n❌ No inventory items found in database.")
                    continue
                
                print(f"\n📋 Available Inventory Items ({len(inventory_items)} total):")
                for inv in inventory_items:
                    print(f"   {inv.id}. {inv.item_name} (Code: {inv.item_code or 'N/A'}, Qty: {inv.quantity}, Warehouse ID: {inv.warehouse_id})")
                print(f"\n📌 Available Inventory IDs: {', '.join(str(inv.id) for inv in inventory_items)}")
                
                try:
                    ids_input = input("\nEnter Inventory ID(s) to delete (comma or space separated for multiple): ").strip()
                    inventory_ids = deleter.parse_ids(ids_input)
                    if not inventory_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(inventory_ids) == 1:
                        deleter.delete_inventory(inventory_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(inventory_ids)} inventory items!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for inventory_id in inventory_ids:
                                if deleter.delete_inventory(inventory_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(inventory_ids)} inventory items.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Inventory ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '7':  # Delivery Man-Warehouse Assignment
                assignments = deleter.list_delivery_man_warehouses()
                if not assignments:
                    print("\n❌ No delivery man-warehouse assignments found in database.")
                    continue
                
                print(f"\n📋 Available Delivery Man-Warehouse Assignments ({len(assignments)} total):")
                for assignment in assignments:
                    delivery_man = deleter.db.query(DeliveryMan).filter(DeliveryMan.id == assignment.delivery_man_id).first()
                    warehouse = deleter.db.query(Warehouse).filter(Warehouse.id == assignment.warehouse_id).first()
                    dm_name = delivery_man.name if delivery_man else f"ID {assignment.delivery_man_id}"
                    wh_name = warehouse.name if warehouse else f"ID {assignment.warehouse_id}"
                    print(f"   {assignment.id}. Delivery Man: {dm_name} → Warehouse: {wh_name}")
                print(f"\n📌 Available Assignment IDs: {', '.join(str(a.id) for a in assignments)}")
                
                try:
                    ids_input = input("\nEnter Assignment ID(s) to delete (comma or space separated for multiple): ").strip()
                    assignment_ids = deleter.parse_ids(ids_input)
                    if not assignment_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(assignment_ids) == 1:
                        deleter.delete_delivery_man_warehouse(assignment_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(assignment_ids)} assignments!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for assignment_id in assignment_ids:
                                if deleter.delete_delivery_man_warehouse(assignment_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(assignment_ids)} assignments.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Assignment ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '8':  # Warehouse
                warehouses = deleter.list_warehouses()
                if not warehouses:
                    print("\n❌ No warehouses found in database.")
                    continue
                
                print(f"\n📋 Available Warehouses ({len(warehouses)} total):")
                for warehouse in warehouses:
                    status = "Active" if warehouse.is_active and not warehouse.deleted_at else "Inactive/Deleted"
                    print(f"   {warehouse.id}. {warehouse.name} (Zone ID: {warehouse.zone_id}, Status: {status})")
                    if warehouse.address:
                        print(f"      Address: {warehouse.address}")
                print(f"\n📌 Available Warehouse IDs: {', '.join(str(w.id) for w in warehouses)}")
                
                try:
                    ids_input = input("\nEnter Warehouse ID(s) to delete (comma or space separated for multiple): ").strip()
                    warehouse_ids = deleter.parse_ids(ids_input)
                    if not warehouse_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(warehouse_ids) == 1:
                        deleter.delete_warehouse(warehouse_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(warehouse_ids)} warehouses!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for warehouse_id in warehouse_ids:
                                if deleter.delete_warehouse(warehouse_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(warehouse_ids)} warehouses.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Warehouse ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '9':  # Shop Visit (Order Booker Visits)
                shop_visits = deleter.list_shop_visits()
                if not shop_visits:
                    print("\n❌ No shop visits found in database.")
                    continue
                
                print(f"\n📋 Available Shop Visits ({len(shop_visits)} total):")
                print("   (Order Booker visits from shop_visits table)")
                print("   Note: For Delivery Man visits, use option 10 (Delivery)")
                for visit in shop_visits:
                    # Determine visit type
                    visit_type = []
                    if visit.order_booker_id:
                        order_booker = deleter.db.query(OrderBooker).filter(OrderBooker.id == visit.order_booker_id).first()
                        ob_name = order_booker.name if order_booker else f"OB#{visit.order_booker_id}"
                        visit_type.append(f"OB: {ob_name}")
                    if visit.delivery_man_id:
                        delivery_man = deleter.db.query(DeliveryMan).filter(DeliveryMan.id == visit.delivery_man_id).first()
                        dm_name = delivery_man.name if delivery_man else f"DM#{visit.delivery_man_id}"
                        visit_type.append(f"DM: {dm_name}")
                    
                    visit_type_str = " | ".join(visit_type) if visit_type else "Unknown"
                    
                    visit_info = f"   {visit.id}. {visit_type_str}"
                    if visit.shop_id:
                        shop = deleter.db.query(Shop).filter(Shop.id == visit.shop_id).first()
                        shop_name = shop.name if shop else f"Shop#{visit.shop_id}"
                        visit_info += f" → {shop_name}"
                    if visit.visit_date:
                        visit_info += f" ({visit.visit_date.strftime('%Y-%m-%d %H:%M') if visit.visit_date else 'N/A'})"
                    print(visit_info)
                print(f"\n📌 Available Shop Visit IDs: {', '.join(str(v.id) for v in shop_visits)}")
                
                try:
                    ids_input = input("\nEnter Shop Visit ID(s) to delete (comma or space separated for multiple): ").strip()
                    visit_ids = deleter.parse_ids(ids_input)
                    if not visit_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(visit_ids) == 1:
                        deleter.delete_shop_visit(visit_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(visit_ids)} shop visits!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for visit_id in visit_ids:
                                if deleter.delete_shop_visit(visit_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(visit_ids)} shop visits.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Shop Visit ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '10':  # Delivery (Delivery Man Visits)
                deliveries = deleter.list_deliveries()
                if not deliveries:
                    print("\n❌ No deliveries found in database.")
                    continue
                
                print(f"\n📋 Available Deliveries ({len(deliveries)} total):")
                print("   (Delivery Man Visits from deliveries table)")
                for delivery in deliveries:
                    # Get delivery man name
                    delivery_man_name = "N/A"
                    if delivery.delivery_man_id:
                        delivery_man = deleter.db.query(DeliveryMan).filter(DeliveryMan.id == delivery.delivery_man_id).first()
                        delivery_man_name = delivery_man.name if delivery_man else f"DM#{delivery.delivery_man_id}"
                    
                    # Get shop name via order
                    shop_name = "N/A"
                    if delivery.order_id:
                        order = deleter.db.query(Order).filter(Order.id == delivery.order_id).first()
                        if order and order.shop_id:
                            shop = deleter.db.query(Shop).filter(Shop.id == order.shop_id).first()
                            shop_name = shop.name if shop else f"Shop#{order.shop_id}"
                    
                    delivery_info = f"   {delivery.id}. DM: {delivery_man_name}"
                    if shop_name != "N/A":
                        delivery_info += f" → {shop_name}"
                    delivery_info += f" | Status: {delivery.status}"
                    if delivery.order_id:
                        delivery_info += f" | Order ID: {delivery.order_id}"
                    if delivery.picked_up_at:
                        delivery_info += f" | Picked: {delivery.picked_up_at.strftime('%Y-%m-%d %H:%M') if delivery.picked_up_at else 'N/A'}"
                    print(delivery_info)
                print(f"\n📌 Available Delivery IDs: {', '.join(str(d.id) for d in deliveries)}")
                
                try:
                    ids_input = input("\nEnter Delivery ID(s) to delete (comma or space separated for multiple): ").strip()
                    delivery_ids = deleter.parse_ids(ids_input)
                    if not delivery_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(delivery_ids) == 1:
                        deleter.delete_delivery(delivery_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(delivery_ids)} deliveries!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for delivery_id in delivery_ids:
                                if deleter.delete_delivery(delivery_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(delivery_ids)} deliveries.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Delivery ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '11':  # Order
                orders = deleter.list_orders()
                if not orders:
                    print("\n❌ No orders found in database.")
                    continue
                
                print(f"\n📋 Available Orders ({len(orders)} total):")
                for order in orders:
                    # Get shop name
                    shop_name = "N/A"
                    if order.shop_id:
                        shop = deleter.db.query(Shop).filter(Shop.id == order.shop_id).first()
                        shop_name = shop.name if shop else f"Shop#{order.shop_id}"
                    
                    # Get order booker name
                    order_booker_name = "N/A"
                    if order.order_booker_id:
                        order_booker = deleter.db.query(OrderBooker).filter(OrderBooker.id == order.order_booker_id).first()
                        order_booker_name = order_booker.name if order_booker else f"OB#{order.order_booker_id}"
                    
                    # Get delivery man name
                    delivery_man_name = "N/A"
                    if order.delivery_man_id:
                        delivery_man = deleter.db.query(DeliveryMan).filter(DeliveryMan.id == order.delivery_man_id).first()
                        delivery_man_name = delivery_man.name if delivery_man else f"DM#{order.delivery_man_id}"
                    
                    order_info = f"   {order.id}. Shop: {shop_name} | OB: {order_booker_name}"
                    if delivery_man_name != "N/A":
                        order_info += f" | DM: {delivery_man_name}"
                    order_info += f" | Status: {order.status} | Amount: {order.total_amount}"
                    if order.scheduled_date:
                        order_info += f" | Scheduled: {order.scheduled_date}"
                    print(order_info)
                print(f"\n📌 Available Order IDs: {', '.join(str(o.id) for o in orders)}")
                
                try:
                    ids_input = input("\nEnter Order ID(s) to delete (comma or space separated for multiple): ").strip()
                    order_ids = deleter.parse_ids(ids_input)
                    if not order_ids:
                        print("❌ No valid IDs provided!")
                        continue
                    
                    if len(order_ids) == 1:
                        deleter.delete_order(order_ids[0])
                    else:
                        print(f"\n⚠️  You are about to delete {len(order_ids)} orders!")
                        confirm = input("Type 'del' to confirm bulk deletion: ")
                        if confirm == 'del':
                            success_count = 0
                            for order_id in order_ids:
                                if deleter.delete_order(order_id):
                                    success_count += 1
                            print(f"\n✅ Successfully deleted {success_count} out of {len(order_ids)} orders.")
                        else:
                            print("❌ Bulk deletion cancelled.")
                except ValueError:
                    print("❌ Invalid Order ID(s)!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            elif choice == '12':  # Clean Shop Registrations Bucket
                deleter.clean_bucket('shop-registrations')
            
            elif choice == '13':  # Clean Daily Collections Bucket
                deleter.clean_bucket('daily-collections')
            
            elif choice == '14':  # Clean Deliveries Bucket
                deleter.clean_bucket('deliveries')
            
            elif choice == '15':  # Clean Shop Visits Bucket
                deleter.clean_bucket('shop-visits')
            
            elif choice == '16':  # Reset Sequences
                deleter.reset_all_sequences()
            
            elif choice == '17':  # Delete All Data
                deleter.delete_all_data()
            
            else:
                print("❌ Invalid choice! Please enter 0-17.")
            
            # Show summary
            deleter.show_summary()
            
            # Ask if user wants to continue
            if choice in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17']:
                continue_choice = input("\nContinue? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    break
    
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print("\n✅ Database connection closed.")


if __name__ == "__main__":
    main()

