"""
Database Models Module
======================
This module imports all SQLAlchemy ORM models to ensure they are registered
with the Base metadata. This is required for SQLAlchemy to create the
database tables automatically.

IMPORTANT:
- All models must be imported here
- This ensures Base.metadata.create_all() creates all tables
- Models are imported in main.py via: from models import *

MODELS INCLUDED:
1. Distributor - Regional managers
2. OrderBooker - Field staff who register shops and create orders
3. DeliveryMan - Field staff who deliver orders
4. Zone - Geographic zones for organizing operations
5. Route - Delivery routes containing multiple shops
6. Shop - Retail locations where products are sold (now uses route_id directly)
7. CreditLimitRequest - Requests for credit limit changes
8. Wallet - Cash wallets for distributors, order bookers, and delivery men
9. WalletTransaction - Transaction history for wallets
NOTE: RouteShop and DeliveryManRoute models removed - shops use route_id directly, delivery men work by zone

USAGE:
    from models import distributor, order_booker, delivery_man
    # Or import all:
    from models import *
"""
# Import all models to ensure they're registered with Base
# This is critical for SQLAlchemy to discover all table definitions
from . import distributor, order_booker, delivery_man, zone, route, shop, credit_limit_request, daily_collection, payment, shop_visit, visit_type, order, order_item, activity_log, super_admin, warehouse, inventory, delivery_man_warehouse, product, delivery, delivery_item, subsidy, wallet, wallet_transaction

# Export all models for easy importing
__all__ = ["distributor", "order_booker", "delivery_man", "zone", "route", "shop", "credit_limit_request", "daily_collection", "payment", "shop_visit", "visit_type", "order", "order_item", "activity_log", "super_admin", "warehouse", "inventory", "delivery_man_warehouse", "product", "delivery", "delivery_item", "subsidy", "wallet", "wallet_transaction"]
