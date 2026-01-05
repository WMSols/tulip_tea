"""
Password Management Utility Script
==================================
Since bcrypt is a one-way hash, we cannot reverse passwords.
This script helps you:
1. List all users (from all roles)
2. Reset passwords (hash new password and update database)
3. Verify passwords (check if password matches stored hash)
4. Delete users (remove from database)

USAGE:
    Interactive mode: python scripts/password_manager.py
    List users: python scripts/password_manager.py --list
    Reset password: python scripts/password_manager.py --reset ROLE USER_ID NEW_PASSWORD
    Verify password: python scripts/password_manager.py --verify ROLE USER_ID PASSWORD
    Delete user: python scripts/password_manager.py --delete ROLE USER_ID

FLOW:
1. Opens database session
2. Queries user tables (distributors, order_bookers, delivery_men)
3. Formats and displays user information
4. For password operations: uses AuthService functions
5. Closes database session
"""
import sys
import os

# Add parent directory to path so we can import from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from config.database import SessionLocal
from repositories.distributor_repository import DistributorRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.delivery_man_repository import DeliveryManRepository
from services.auth_service import get_password_hash, verify_password
from models.order_booker import OrderBooker
from models.delivery_man import DeliveryMan


def list_all_users():
    """
    List all users from all tables with formatted output.
    
    FLOW:
    1. Opens database session
    2. Queries distributors table via DistributorRepository.get_all()
    3. Queries order_bookers table directly (using SQLAlchemy)
    4. Queries delivery_men table directly
    5. Formats data in a table and prints to console
    6. Shows summary with total counts
    7. Closes database session
    
    Returns:
        None (prints to console)
    
    Output Format:
        - Distributors: ID, Name, Phone, Email, Zone
        - Order Bookers: ID, Name, Phone, Email, Zone, Distributor ID
        - Delivery Men: ID, Name, Phone, Distributor ID, Created At
        - Summary: Total counts
    """
    db: Session = SessionLocal()
    
    try:
        print("\n" + "="*100)
        print(" " * 35 + "ALL USERS IN SYSTEM")
        print("="*100)
        
        # Distributors
        distributors = DistributorRepository.get_all(db)
        print(f"\n{'='*100}")
        print(f"📊 DISTRIBUTORS ({len(distributors)})")
        print(f"{'='*100}")
        if distributors:
            print(f"{'ID':<6} | {'Name':<25} | {'Phone':<18} | {'Email':<30} | {'Zone':<15}")
            print("-" * 100)
            for d in distributors:
                email = (d.email[:27] + '...') if d.email and len(d.email) > 30 else (d.email or 'N/A')
                zone = f"Zone ID: {d.zone_id}" if d.zone_id else 'N/A'
                print(f"{d.id:<6} | {d.name:<25} | {d.phone:<18} | {email:<30} | {zone:<15}")
        else:
            print("  No distributors found.")
        
        # Order Bookers
        all_order_bookers = db.query(OrderBooker).all()
        print(f"\n{'='*100}")
        print(f"📋 ORDER BOOKERS ({len(all_order_bookers)})")
        print(f"{'='*100}")
        if all_order_bookers:
            print(f"{'ID':<6} | {'Name':<25} | {'Phone':<18} | {'Email':<30} | {'Zone':<15} | {'Dist. ID':<10}")
            print("-" * 100)
            for ob in all_order_bookers:
                email = (ob.email[:27] + '...') if ob.email and len(ob.email) > 30 else (ob.email or 'N/A')
                zone = f"Zone ID: {ob.zone_id}" if ob.zone_id else 'N/A'
                print(f"{ob.id:<6} | {ob.name:<25} | {ob.phone:<18} | {email:<30} | {zone:<15} | {ob.distributor_id:<10}")
        else:
            print("  No order bookers found.")
        
        # Delivery Men
        all_delivery_men = db.query(DeliveryMan).all()
        print(f"\n{'='*100}")
        print(f"🚚 DELIVERY MEN ({len(all_delivery_men)})")
        print(f"{'='*100}")
        if all_delivery_men:
            print(f"{'ID':<6} | {'Name':<25} | {'Phone':<18} | {'Dist. ID':<10} | {'Created At':<20}")
            print("-" * 100)
            for dm in all_delivery_men:
                created = dm.created_at.strftime('%Y-%m-%d %H:%M') if dm.created_at else 'N/A'
                print(f"{dm.id:<6} | {dm.name:<25} | {dm.phone:<18} | {dm.distributor_id:<10} | {created:<20}")
        else:
            print("  No delivery men found.")
        
        # Summary
        total = len(distributors) + len(all_order_bookers) + len(all_delivery_men)
        print(f"\n{'='*100}")
        print(f"📈 SUMMARY: Total Users = {total} (Distributors: {len(distributors)}, Order Bookers: {len(all_order_bookers)}, Delivery Men: {len(all_delivery_men)})")
        print("="*100 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def reset_password(role: str, user_id: int, new_password: str):
    """
    Reset password for a user.
    
    FLOW:
    1. Opens database session
    2. Hashes new password using AuthService.get_password_hash()
    3. Gets user by ID from appropriate repository based on role
    4. Updates password_hash field in database
    5. Commits transaction
    6. Prints success message
    7. Closes database session
    
    Args:
        role: User role ("distributor", "order_booker", "delivery_man")
        user_id: User ID (primary key)
        new_password: New plain text password (will be hashed)
    
    Returns:
        None (prints result to console)
    
    Note:
        - Password is hashed using bcrypt before storing
        - Old password cannot be recovered (bcrypt is one-way)
    """
    db: Session = SessionLocal()
    
    try:
        # Hash the new password using AuthService (bcrypt with 12 rounds)
        password_hash = get_password_hash(new_password)
        
        # Get user from appropriate repository based on role
        if role.lower() == "distributor":
            user = DistributorRepository.get_by_id(db, user_id)
            if not user:
                print(f"❌ Distributor with ID {user_id} not found")
                return
            user.password_hash = password_hash
            db.commit()
            print(f"✅ Password reset for Distributor: {user.name} (ID: {user.id})")
            print(f"   New Password: {new_password}")
            
        elif role.lower() in ["order_booker", "orderbooker", "ob"]:
            user = OrderBookerRepository.get_by_id(db, user_id)
            if not user:
                print(f"❌ Order Booker with ID {user_id} not found")
                return
            user.password_hash = password_hash
            db.commit()
            print(f"✅ Password reset for Order Booker: {user.name} (ID: {user.id})")
            print(f"   New Password: {new_password}")
            
        elif role.lower() in ["delivery_man", "deliveryman", "dm"]:
            user = DeliveryManRepository.get_by_id(db, user_id)
            if not user:
                print(f"❌ Delivery Man with ID {user_id} not found")
                return
            user.password_hash = password_hash
            db.commit()
            print(f"✅ Password reset for Delivery Man: {user.name} (ID: {user.id})")
            print(f"   New Password: {new_password}")
        else:
            print(f"❌ Invalid role: {role}")
            print("   Valid roles: distributor, order_booker, delivery_man")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def verify_user_password(role: str, user_id: int, password: str):
    """
    Verify if a password matches for a user.
    
    FLOW:
    1. Opens database session
    2. Gets user by ID from appropriate repository based on role
    3. Uses AuthService.verify_password() to compare:
       - Plain password (user input)
       - Hashed password (from database)
    4. Prints result (correct/incorrect)
    5. Closes database session
    
    Args:
        role: User role ("distributor", "order_booker", "delivery_man")
        user_id: User ID (primary key)
        password: Plain text password to verify
    
    Returns:
        None (prints result to console)
    
    Note:
        - Uses bcrypt.checkpw() to securely compare passwords
        - Never stores or logs the plain password
    """
    db: Session = SessionLocal()
    
    try:
        if role.lower() == "distributor":
            user = DistributorRepository.get_by_id(db, user_id)
            if not user:
                print(f"❌ Distributor with ID {user_id} not found")
                return
            role_name = "Distributor"
            
        elif role.lower() in ["order_booker", "orderbooker", "ob"]:
            user = OrderBookerRepository.get_by_id(db, user_id)
            if not user:
                print(f"❌ Order Booker with ID {user_id} not found")
                return
            role_name = "Order Booker"
            
        elif role.lower() in ["delivery_man", "deliveryman", "dm"]:
            user = DeliveryManRepository.get_by_id(db, user_id)
            if not user:
                print(f"❌ Delivery Man with ID {user_id} not found")
                return
            role_name = "Delivery Man"
        else:
            print(f"❌ Invalid role: {role}")
            return
        
        if verify_password(password, user.password_hash):
            print(f"✅ Password is CORRECT for {role_name}: {user.name} (ID: {user.id})")
        else:
            print(f"❌ Password is INCORRECT for {role_name}: {user.name} (ID: {user.id})")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


def delete_user(role: str, user_id: int):
    """
    Delete a user from the system.
    
    FLOW:
    1. Opens database session
    2. Gets user by ID from appropriate repository
    3. Deletes user record from database
    4. Commits transaction
    5. Prints success message
    6. Closes database session
    
    Args:
        role: User role ("distributor", "order_booker", "delivery_man")
        user_id: User ID (primary key)
    
    Returns:
        bool: True if deleted successfully, False otherwise
    
    Warning:
        - This action is permanent and cannot be undone
        - Foreign key constraints may prevent deletion if user has related records
    """
    db: Session = SessionLocal()
    
    try:
        if role.lower() == "distributor":
            user = DistributorRepository.get_by_id(db, user_id)
            if not user:
                print(f"❌ Distributor with ID {user_id} not found")
                return False
            user_name = user.name
            db.delete(user)
            db.commit()
            print(f"✅ Deleted Distributor: {user_name} (ID: {user_id})")
            return True
            
        elif role.lower() in ["order_booker", "orderbooker", "ob"]:
            user = OrderBookerRepository.get_by_id(db, user_id)
            if not user:
                print(f"❌ Order Booker with ID {user_id} not found")
                return False
            user_name = user.name
            db.delete(user)
            db.commit()
            print(f"✅ Deleted Order Booker: {user_name} (ID: {user_id})")
            return True
            
        elif role.lower() in ["delivery_man", "deliveryman", "dm"]:
            user = DeliveryManRepository.get_by_id(db, user_id)
            if not user:
                print(f"❌ Delivery Man with ID {user_id} not found")
                return False
            user_name = user.name
            db.delete(user)
            db.commit()
            print(f"✅ Deleted Delivery Man: {user_name} (ID: {user_id})")
            return True
        else:
            print(f"❌ Invalid role: {role}")
            print("   Valid roles: distributor, order_booker, delivery_man")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def interactive_menu():
    """Interactive menu for password management."""
    while True:
        print("\n" + "="*80)
        print(" " * 20 + "PASSWORD MANAGEMENT UTILITY")
        print("="*80)
        print("1. List all users")
        print("2. Reset password")
        print("3. Verify password")
        print("4. Delete user")
        print("5. Exit")
        print("="*80)
        
        choice = input("\nSelect an option (1-5): ").strip()
        
        if choice == "1":
            list_all_users()
            
        elif choice == "2":
            print("\n" + "-"*80)
            print("RESET PASSWORD")
            print("-"*80)
            role = input("  Role (distributor/order_booker/delivery_man): ").strip()
            try:
                user_id = int(input("  User ID: ").strip())
                new_password = input("  New Password: ").strip()
                if new_password:
                    reset_password(role, user_id, new_password)
                else:
                    print("❌ Password cannot be empty")
            except ValueError:
                print("❌ Invalid user ID")
                
        elif choice == "3":
            print("\n" + "-"*80)
            print("VERIFY PASSWORD")
            print("-"*80)
            role = input("  Role (distributor/order_booker/delivery_man): ").strip()
            try:
                user_id = int(input("  User ID: ").strip())
                password = input("  Password to verify: ").strip()
                if password:
                    verify_user_password(role, user_id, password)
                else:
                    print("❌ Password cannot be empty")
            except ValueError:
                print("❌ Invalid user ID")
        
        elif choice == "4":
            print("\n" + "-"*80)
            print("DELETE USER")
            print("-"*80)
            print("⚠️  WARNING: This action cannot be undone!")
            role = input("  Role (distributor/order_booker/delivery_man): ").strip()
            try:
                user_id = int(input("  User ID: ").strip())
                confirm = input(f"  Are you sure you want to delete this user? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y']:
                    delete_user(role, user_id)
                else:
                    print("❌ Deletion cancelled.")
            except ValueError:
                print("❌ Invalid user ID")
                
        elif choice == "5":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid option. Please select 1-5.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Password Management Utility")
    parser.add_argument("--list", action="store_true", help="List all users")
    parser.add_argument("--reset", nargs=3, metavar=("ROLE", "USER_ID", "PASSWORD"),
                       help="Reset password: --reset ROLE USER_ID NEW_PASSWORD")
    parser.add_argument("--verify", nargs=3, metavar=("ROLE", "USER_ID", "PASSWORD"),
                       help="Verify password: --verify ROLE USER_ID PASSWORD")
    parser.add_argument("--delete", nargs=2, metavar=("ROLE", "USER_ID"),
                       help="Delete user: --delete ROLE USER_ID")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Run in interactive mode")
    
    args = parser.parse_args()
    
    if args.list:
        list_all_users()
    elif args.reset:
        role, user_id, password = args.reset
        reset_password(role, int(user_id), password)
    elif args.verify:
        role, user_id, password = args.verify
        verify_user_password(role, int(user_id), password)
    elif args.delete:
        role, user_id = args.delete
        print("⚠️  WARNING: This action cannot be undone!")
        confirm = input(f"Are you sure you want to delete {role} with ID {user_id}? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            delete_user(role, int(user_id))
        else:
            print("❌ Deletion cancelled.")
    elif args.interactive:
        interactive_menu()
    else:
        # Default to interactive mode
        interactive_menu()

