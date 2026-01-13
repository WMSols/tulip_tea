# Hard Delete Entities Script

## Overview

The `hard_delete_entities.py` script provides an interactive interface to permanently delete entities from the database along with all their related data. This script handles foreign key relationships properly to avoid database constraint violations.

## ⚠️ WARNING

**This script performs HARD DELETES - deleted data CANNOT be recovered!**

Always backup your database before running this script.

## Usage

```bash
python scripts/hard_delete_entities.py
```

## Supported Entity Types

1. **Shop** - Deletes shop and all related data
2. **Order Booker** - Deletes order booker and updates related foreign keys
3. **Delivery Man** - Deletes delivery man and updates related foreign keys
4. **Route** - Deletes route and all related junction table entries

## What Gets Deleted

### When Deleting a Shop:

The following related data is **DELETED**:
- ✅ Credit Limit Requests (credit_limit_requests where shop_id = X)
- ✅ Orders (orders where shop_id = X)
  - Also deletes Order Items for those orders
- ✅ Payments (payments where shop_id = X)
- ✅ Daily Collections (daily_collections where shop_id = X)
- ✅ Shop Visits (shop_visits where shop_id = X)
- ✅ Route-Shop Links (route_shops where shop_id = X)
- ✅ The Shop itself

**Total Impact**: Shop + 6 related entity types

### When Deleting an Order Booker:

The following foreign keys are **SET TO NULL** (data preserved):
- 🔄 Shops Created (shops.created_by_order_booker set to NULL)
- 🔄 Shops Assigned (shops.assigned_to_order_booker set to NULL)
- 🔄 Routes (routes.order_booker_id set to NULL)
- 🔄 Orders (orders.order_booker_id set to NULL)
- 🔄 Shop Visits (shop_visits.order_booker_id set to NULL)

The following is **DELETED**:
- ✅ The Order Booker itself

**Total Impact**: Order Booker deleted, 5 related entity types updated (FKs set to NULL)

### When Deleting a Delivery Man:

The following foreign keys are **SET TO NULL** (data preserved):
- 🔄 Orders (orders.delivery_man_id set to NULL)
- 🔄 Daily Collections (daily_collections.collected_by_delivery_man set to NULL)
- 🔄 Shop Visits (shop_visits.delivery_man_id set to NULL)

The following is **DELETED**:
- ✅ Delivery Man-Route Links (delivery_man_routes where delivery_man_id = X)
- ✅ The Delivery Man itself

**Total Impact**: Delivery Man + delivery_man_routes deleted, 3 related entity types updated (FKs set to NULL)

### When Deleting a Route:

The following is **DELETED**:
- ✅ Route-Shop Links (route_shops where route_id = X)
- ✅ Delivery Man-Route Links (delivery_man_routes where route_id = X)
- ✅ The Route itself

**Total Impact**: Route + 2 junction table types deleted

## Interactive Flow

1. **Select Entity Type**: Choose from menu (1-4)
2. **View Available Entities**: Script lists all entities of selected type
3. **Enter Entity ID**: Type the ID of the entity to delete
4. **Review Related Data**: Script shows what will be affected
5. **Confirm Deletion**: Type 'DELETE' (all caps) to confirm
6. **View Summary**: See what was deleted
7. **Continue or Exit**: Choose to delete more or exit

## Safety Features

- ✅ Requires explicit 'DELETE' confirmation (case-sensitive)
- ✅ Shows all related data before deletion
- ✅ Uses database transactions (rollback on error)
- ✅ Provides detailed deletion summary
- ✅ Handles foreign key constraints properly

## Example Session

```
🗑️  HARD DELETE ENTITIES SCRIPT
============================================================

⚠️  WARNING: This will PERMANENTLY DELETE data from the database!
⚠️  This action CANNOT be undone!

Select entity type to delete:
1. Shop
2. Order Booker
3. Delivery Man
4. Route
0. Exit
------------------------------------------------------------

Enter your choice (0-4): 1

📋 Available Shops (5 total):
   1. Shop A (Phone: 03001234567)
   2. Shop B (Phone: 03001234568)
   ...

Enter Shop ID to delete: 1

📋 Shop to delete: Shop A (ID: 1)

📊 Related data that will be deleted:
   - Credit Limit Requests: 2
   - Orders: 5
   - Payments: 3
   - Daily Collections: 2
   - Shop Visits: 10
   - Route-Shop Links: 1

⚠️  Are you SURE you want to delete shop 'Shop A' and ALL related data? (type 'DELETE' to confirm): DELETE

✅ Shop 'Shop A' (ID: 1) and all related data deleted successfully!

============================================================
📊 DELETION SUMMARY
============================================================
   credit_limit_requests: 2
   daily_collections: 2
   order_items: 15
   orders: 5
   payments: 3
   route_shops: 1
   shop_visits: 10
   shops: 1
============================================================

Continue deleting? (y/n): n

👋 Exiting...
✅ Database connection closed.
```

## Notes

- The script does NOT delete Distributors or Super Admins (as requested)
- All deletions are permanent (hard deletes, not soft deletes)
- The script handles all foreign key relationships automatically
- Related data is either deleted or foreign keys are set to NULL (depending on business logic)




