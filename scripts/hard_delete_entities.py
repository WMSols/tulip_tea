"""
Hard Delete Entities Script
===========================
Interactive script to permanently delete entities and all related data from the database.

This script handles cascading deletes for:
- Shops (and related: credit_limit_requests, orders, payments, daily_collections, shop_visits, route_shops)
- Order Bookers (and related: routes, orders, shop_visits, shop assignments)
- Delivery Men (and related: orders, daily_collections, shop_visits, delivery_man_routes)
- Routes (and related: route_shops, delivery_man_routes)

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
from models.route_shop import RouteShop
from models.delivery_man_route import DeliveryManRoute


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
        print("0. Exit")
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
    
    def get_shop_related_data(self, shop_id: int) -> Dict:
        """Get all data related to a shop."""
        return {
            'credit_limit_requests': self.db.query(CreditLimitRequest).filter(CreditLimitRequest.shop_id == shop_id).all(),
            'orders': self.db.query(Order).filter(Order.shop_id == shop_id).all(),
            'payments': self.db.query(Payment).filter(Payment.shop_id == shop_id).all(),
            'daily_collections': self.db.query(DailyCollection).filter(DailyCollection.shop_id == shop_id).all(),
            'shop_visits': self.db.query(ShopVisit).filter(ShopVisit.shop_id == shop_id).all(),
            'route_shops': self.db.query(RouteShop).filter(RouteShop.shop_id == shop_id).all(),
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
        return {
            'route_shops': self.db.query(RouteShop).filter(RouteShop.route_id == route_id).all(),
            'delivery_man_routes': self.db.query(DeliveryManRoute).filter(DeliveryManRoute.route_id == route_id).all(),
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
        print(f"   - Route-Shop Links: {len(related['route_shops'])}")
        
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
            
            for route_shop in related['route_shops']:
                self.db.delete(route_shop)
                self.deleted_summary['route_shops'] = self.deleted_summary.get('route_shops', 0) + 1
            if related['route_shops']:  # Only flush if there are route_shops to delete
                self.db.flush()  # Ensure route_shops are deleted before shop
            
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
        print(f"\n📊 Related data that will be deleted:")
        print(f"   - Route-Shop Links: {len(related['route_shops'])}")
        print(f"   - Delivery Man-Route Links: {len(related['delivery_man_routes'])}")
        
        confirm = input(f"\n⚠️  Are you SURE you want to delete route '{route.name}'? (type 'del' to confirm): ")
        if confirm != 'del':
            print("❌ Deletion cancelled.")
            return False
        
        try:
            # Delete related data
            for route_shop in related['route_shops']:
                self.db.delete(route_shop)
                self.deleted_summary['route_shops'] = self.deleted_summary.get('route_shops', 0) + 1
            
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


def main():
    """Main interactive loop."""
    db: Session = SessionLocal()
    deleter = EntityDeleter(db)
    
    try:
        while True:
            deleter.show_menu()
            choice = input("\nEnter your choice (0-4): ").strip()
            
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
                
                try:
                    shop_id = int(input("\nEnter Shop ID to delete: "))
                    deleter.delete_shop(shop_id)
                except ValueError:
                    print("❌ Invalid Shop ID!")
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
                
                try:
                    ob_id = int(input("\nEnter Order Booker ID to delete: "))
                    deleter.delete_order_booker(ob_id)
                except ValueError:
                    print("❌ Invalid Order Booker ID!")
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
                
                try:
                    dm_id = int(input("\nEnter Delivery Man ID to delete: "))
                    deleter.delete_delivery_man(dm_id)
                except ValueError:
                    print("❌ Invalid Delivery Man ID!")
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
                
                try:
                    route_id = int(input("\nEnter Route ID to delete: "))
                    deleter.delete_route(route_id)
                except ValueError:
                    print("❌ Invalid Route ID!")
                except KeyboardInterrupt:
                    print("\n\n❌ Operation cancelled by user.")
            
            else:
                print("❌ Invalid choice! Please enter 0-4.")
            
            # Show summary
            deleter.show_summary()
            
            # Ask if user wants to continue
            if choice in ['1', '2', '3', '4']:
                continue_choice = input("\nContinue deleting? (y/n): ").strip().lower()
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

