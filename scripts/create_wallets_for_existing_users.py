"""
Create Wallets for Existing Users
=================================
This script creates wallets for all existing distributors, order bookers, and delivery men
who don't already have a wallet.

USAGE:
    python scripts/create_wallets_for_existing_users.py

NOTE:
    - Only creates wallets for users who don't already have one
    - Skips users who already have wallets
    - Safe to run multiple times (idempotent)
"""
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from config.database import get_db
from repositories.wallet_repository import WalletRepository


def create_wallets_for_existing_users():
    """Create wallets for all existing users who don't have one."""
    db: Session = next(get_db())
    
    try:
        print("=" * 60)
        print("Creating Wallets for Existing Users")
        print("=" * 60)
        
        from models.distributor import Distributor
        from models.order_booker import OrderBooker
        from models.delivery_man import DeliveryMan
        
        # Create wallets for distributors
        print("\n📦 Processing Distributors...")
        distributors = db.query(Distributor).filter(
            Distributor.deleted_at.is_(None),
            Distributor.is_active == True
        ).all()
        
        distributor_count = 0
        for distributor in distributors:
            existing_wallet = WalletRepository.get_by_user(db, "distributor", distributor.id)
            if not existing_wallet:
                WalletRepository.create(db, "distributor", distributor.id)
                distributor_count += 1
                print(f"  ✓ Created wallet for distributor {distributor.id} ({distributor.name})")
            else:
                print(f"  ⊘ Distributor {distributor.id} already has wallet")
        
        print(f"\n  Total: {len(distributors)} distributors, {distributor_count} new wallets created")
        
        # Create wallets for order bookers
        print("\n👤 Processing Order Bookers...")
        order_bookers = db.query(OrderBooker).filter(
            OrderBooker.deleted_at.is_(None),
            OrderBooker.is_active == True
        ).all()
        
        order_booker_count = 0
        for order_booker in order_bookers:
            existing_wallet = WalletRepository.get_by_user(db, "order_booker", order_booker.id)
            if not existing_wallet:
                WalletRepository.create(db, "order_booker", order_booker.id)
                order_booker_count += 1
                print(f"  ✓ Created wallet for order booker {order_booker.id} ({order_booker.name})")
            else:
                print(f"  ⊘ Order booker {order_booker.id} already has wallet")
        
        print(f"\n  Total: {len(order_bookers)} order bookers, {order_booker_count} new wallets created")
        
        # Create wallets for delivery men
        print("\n🚚 Processing Delivery Men...")
        delivery_men = db.query(DeliveryMan).filter(
            DeliveryMan.deleted_at.is_(None),
            DeliveryMan.is_active == True
        ).all()
        
        delivery_man_count = 0
        for delivery_man in delivery_men:
            existing_wallet = WalletRepository.get_by_user(db, "delivery_man", delivery_man.id)
            if not existing_wallet:
                WalletRepository.create(db, "delivery_man", delivery_man.id)
                delivery_man_count += 1
                print(f"  ✓ Created wallet for delivery man {delivery_man.id} ({delivery_man.name})")
            else:
                print(f"  ⊘ Delivery man {delivery_man.id} already has wallet")
        
        print(f"\n  Total: {len(delivery_men)} delivery men, {delivery_man_count} new wallets created")
        
        # Summary
        total_new = distributor_count + order_booker_count + delivery_man_count
        total_users = len(distributors) + len(order_bookers) + len(delivery_men)
        
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Total users processed: {total_users}")
        print(f"New wallets created: {total_new}")
        print(f"Users with existing wallets: {total_users - total_new}")
        print("=" * 60)
        print("\n✅ Wallet creation completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_wallets_for_existing_users()

