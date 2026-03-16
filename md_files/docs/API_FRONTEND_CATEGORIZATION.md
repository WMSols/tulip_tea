# API Endpoints Categorization by Frontend Dashboard

This document shows how API endpoints are categorized in Swagger UI based on which frontend dashboard uses them.

## Overview

The FastAPI backend now includes **OpenAPI tag groups** that organize endpoints by frontend dashboard. When you visit `/docs` (Swagger UI), you'll see endpoints grouped into the following categories:

1. **📋 Order Booker Dashboard** - APIs used by `tests/order_booker_dashboard.html`
2. **👔 Distributor Dashboard** - APIs used by `tests/distributor_dashboard.html`
3. **👑 Super Admin Dashboard** - APIs used by `tests/super_admin_dashboard.html`
4. **🚚 Delivery Man Dashboard** - APIs used by `tests/delivery_man_dashboard.html`
5. **📊 Activity Logs Dashboard** - APIs used by `tests/activity_logs_dashboard.html`
6. **🔧 Common APIs** - Shared APIs used by multiple dashboards

## Implementation Details

### Tag System
Each endpoint now has **multiple tags**:
- **Functional Tag**: Describes what the endpoint does (e.g., "Orders", "Shops", "Authentication")
- **Frontend Category Tag**: Indicates which dashboard uses it (e.g., "Order Booker APIs", "Distributor APIs")

### Tag Groups in Swagger UI
The `x-tagGroups` extension in the OpenAPI schema groups related tags together, making it easier to find endpoints by frontend dashboard.

## API Endpoints by Frontend Dashboard

### 📋 Order Booker Dashboard APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/login/order-booker` | POST | Order booker login |
| `/shop-visits/order-booker/{id}` | POST | Register shop visit with order/collection |
| `/shops/order-booker/{id}` | GET | List shops (with approved_only filter) |
| `/shops/order-booker/{id}` | POST | Register new shop |
| `/shops/{shop_id}/credit-info` | GET | Get shop credit limit info |
| `/orders/order-booker/{id}` | POST | Create order (via shop visit) |
| `/credit-limit-requests/order-booker/{id}` | POST | Request credit limit change |
| `/credit-limit-requests/pending` | GET | View pending credit limit requests |
| `/weekly-route-schedules/order-booker/{id}` | GET | Get weekly schedule |
| `/subsidies/distributor/{id}/active` | GET | List active subsidies |
| `/products/active?distributor_id={id}` | GET | List active products |
| `/zones/` | GET | List zones (for shop registration) |
| `/routes/order-booker/{id}` | GET | List assigned routes |
| `/wallets/order_booker/{id}/balance` | GET | Get wallet balance |
| `/wallets/order_booker/{id}/transactions` | GET | Get wallet transactions |

### 👔 Distributor Dashboard APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/login/distributor` | POST | Distributor login |
| `/zones/` | GET, POST | List/Create zones |
| `/zones/{id}` | GET, PUT | Get/Update zone |
| `/routes/distributor/{id}` | GET | List routes |
| `/routes/{distributor_id}` | POST | Create route |
| `/routes/{route_id}/assign` | POST | Assign route to order booker |
| `/routes/{route_id}` | GET, PUT | Get/Update route |
| `/order-bookers/distributor/{id}` | GET | List order bookers |
| `/order-bookers/zone/{zone_id}` | GET | List order bookers by zone |
| `/order-bookers/{distributor_id}` | POST | Create order booker |
| `/order-bookers/{id}` | PUT, DELETE | Update/Delete order booker |
| `/delivery-men/distributor/{id}` | GET | List delivery men |
| `/delivery-men/{distributor_id}` | POST | Create delivery man |
| `/delivery-men/{id}` | PUT, DELETE | Update/Delete delivery man |
| `/shops/all?distributor_id={id}` | GET | List all shops |
| `/shops/pending?distributor_id={id}` | GET | List pending shop approvals |
| `/shops/{shop_id}` | GET, PUT | Get/Update shop |
| `/shops/{shop_id}/verify` | POST | Verify/approve shop |
| `/credit-limit-requests/pending?distributor_id={id}` | GET | List pending credit requests |
| `/credit-limit-requests/{id}/approve` | POST | Approve credit limit request |
| `/credit-limit-requests/{id}/reject` | POST | Reject credit limit request |
| `/products/` | GET, POST | List/Create products |
| `/products/active?distributor_id={id}` | GET | List active products |
| `/products/{id}` | GET, PUT, DELETE | Get/Update/Delete product |
| `/warehouses/?distributor_id={id}` | GET | List warehouses |
| `/warehouses/` | POST | Create warehouse |
| `/warehouses/{id}` | PUT | Update warehouse |
| `/warehouses/{id}/inventory` | GET, POST | Get/Add inventory |
| `/warehouses/{id}/inventory/{item_id}` | PUT, DELETE | Update/Delete inventory item |
| `/warehouses/{id}/delivery-men` | GET | List assigned delivery men |
| `/warehouses/{id}/delivery-men/{dm_id}` | POST, DELETE | Assign/Unassign delivery man |
| `/orders/pending-subsidy-approval` | GET | List orders pending subsidy approval |
| `/orders/{id}/approve-subsidy` | PUT | Approve subsidized order |
| `/orders/{id}/reject-subsidy` | PUT | Reject subsidized order |
| `/orders/{id}/assign` | POST | Assign order to delivery man |
| `/orders/{id}` | GET | Get order details |
| `/deliveries/distributor/{id}` | GET | List all deliveries |
| `/deliveries/order/{order_id}` | GET | Get delivery details |
| `/shop-visits/all?distributor_id={id}` | GET | List all shop visits |
| `/daily-collections/{id}` | GET | Get collection details |
| `/daily-collections/{id}/approve` | POST | Approve daily collection |
| `/daily-collections/{id}/reject` | POST | Reject daily collection |
| `/weekly-route-schedules/distributor/{id}` | GET, POST | List/Create weekly schedules |
| `/weekly-route-schedules/{id}` | PUT | Update schedule |
| `/visit-tasks/generate` | POST | Generate visit tasks |
| `/wallets/distributor/{id}/balance` | GET | Get distributor wallet balance |

### 👑 Super Admin Dashboard APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/super-admin/login` | POST | Super admin login |
| `/super-admin/entities` | GET | List all entities (distributors, order bookers, delivery men) |
| `/super-admin/distributors` | POST | Create new distributor |
| `/super-admin/distributors/{id}` | PUT | Update distributor info/password |
| `/super-admin/wallets/{user_type}/{user_id}/toggle-active` | PUT | Toggle wallet active status |
| `/wallets/{user_type}/{user_id}/balance` | GET | Get wallet balance (for any user type) |

### 🚚 Delivery Man Dashboard APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/login/delivery-man` | POST | Delivery man login |
| `/orders/delivery-man/{id}` | GET | List orders assigned to delivery man |
| `/orders/{id}` | GET | Get order details |
| `/orders/{id}/deliver` | PUT | Mark order as delivered/cancelled |
| `/deliveries/order/{order_id}` | GET, POST | Get/Create delivery record |
| `/deliveries/{id}/pickup` | POST | Record stock pickup from warehouse |
| `/deliveries/{id}/deliver` | POST | Record delivery to shop |
| `/deliveries/{id}/return` | POST | Return stock to warehouse |
| `/delivery-men/{id}/warehouses` | GET | Get assigned warehouses |
| `/daily-collections/delivery-man/{id}` | POST | Submit daily collection |
| `/shops/{shop_id}/credit-info` | GET | Get shop credit info (for collection) |
| `/wallets/delivery_man/{id}/balance` | GET | Get wallet balance |
| `/wallets/delivery_man/{id}/transactions` | GET | Get wallet transactions |
| `/config/supabase` | GET | Get Supabase config for image uploads |

### 📊 Activity Logs Dashboard APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/activity-logs/` | GET | List activity logs with filters |
| `/activity-logs/{id}` | GET | Get activity log details |

### 🔧 Common APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/config/supabase` | GET | Get Supabase configuration (used by delivery man dashboard) |

## How to View in Swagger UI

1. Start the FastAPI server:
   ```bash
   python main.py
   # or
   uvicorn main:app --reload
   ```

2. Open Swagger UI:
   ```
   http://localhost:8000/docs
   ```

3. **Tag Groups** will appear at the top of the Swagger UI interface, organized by frontend dashboard:
   - 📋 Order Booker Dashboard
   - 👔 Distributor Dashboard
   - 👑 Super Admin Dashboard
   - 🚚 Delivery Man Dashboard
   - 📊 Activity Logs Dashboard
   - 🔧 Common APIs

4. Click on any tag group to expand and see all endpoints in that category.

5. Each endpoint shows **multiple tags** - you can filter by:
   - Functional tag (e.g., "Orders", "Shops")
   - Frontend category tag (e.g., "Order Booker APIs", "Distributor APIs")

## Benefits

1. **Easy Discovery**: Developers can quickly find which APIs are used by each frontend dashboard
2. **Better Organization**: Endpoints are grouped logically by user role
3. **Documentation**: Each tag group links to the corresponding frontend dashboard file
4. **Filtering**: Can filter endpoints by both functional area and frontend dashboard
5. **Visual Clarity**: Tag groups are visually distinct in Swagger UI

## Notes

- Some endpoints appear in multiple categories (e.g., `/orders/{id}` is used by both Distributor and Delivery Man dashboards)
- Endpoints can have multiple tags, allowing flexible filtering
- The tag groups use emojis for visual distinction in Swagger UI
- All tags are defined in `main.py` in the `tags_metadata` list
- Tag groups are configured using the `x-tagGroups` OpenAPI extension

