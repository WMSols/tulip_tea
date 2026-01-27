"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any


# Distributor Schemas
class DistributorCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: str
    password: str
    # Note: Distributors are NOT assigned to zones - they create zones but are not assigned to them


class DistributorLogin(BaseModel):
    phone: str
    password: str


# Super Admin Schemas
class SuperAdminLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

    class Config:
        from_attributes = True


class DistributorResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    phone: str
    # Note: Distributors are NOT assigned to zones - they create zones but are not assigned to them
    created_at: Optional[str]

    class Config:
        from_attributes = True


# Order Booker Schemas
class OrderBookerCreate(BaseModel):
    name: str
    phone: str
    password: str
    email: Optional[EmailStr] = None
    zone_id: Optional[int] = None


class OrderBookerLogin(BaseModel):
    phone: str
    password: str


class OrderBookerResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    phone: str
    zone_id: Optional[int] = None
    distributor_id: int
    created_at: Optional[str]

    class Config:
        from_attributes = True


class OrderBookerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    zone_id: Optional[int] = None
    password: Optional[str] = None


# Delivery Man Schemas
class DeliveryManCreate(BaseModel):
    name: str
    phone: str
    password: str
    zone_id: Optional[int] = None
    # Note: Delivery men work by zone, not routes - route_ids removed


class DeliveryManLogin(BaseModel):
    phone: str
    password: str


class DeliveryManResponse(BaseModel):
    id: int
    name: str
    phone: str
    distributor_id: int
    zone_id: Optional[int] = None
    route_ids: Optional[List[int]] = None  # List of assigned route IDs
    created_at: Optional[str]

    class Config:
        from_attributes = True


class DeliveryManUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    zone_id: Optional[int] = None
    password: Optional[str] = None


# Zone Schemas
class ZoneCreate(BaseModel):
    name: str


class ZoneUpdate(BaseModel):
    name: str


class ZoneResponse(BaseModel):
    id: int
    name: str
    created_at: Optional[str]

    class Config:
        from_attributes = True


# Route Schemas
class RouteCreate(BaseModel):
    name: str
    zone_id: int


class RouteUpdate(BaseModel):
    name: str


class RouteResponse(BaseModel):
    id: int
    name: str
    zone_id: Optional[int] = None
    order_booker_id: Optional[int] = None
    created_by_distributor: Optional[int] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class RouteAssign(BaseModel):
    order_booker_id: int


class RouteInfo(BaseModel):
    route_id: int
    route_name: str
    route_zone_id: Optional[int] = None
    route_zone_name: Optional[str] = None
    order_booker_id: Optional[int] = None
    order_booker_name: Optional[str] = None
    sequence: Optional[int] = None  # Visit order on this route


# Shop Schemas
class ShopRegister(BaseModel):
    name: str
    owner_name: str
    owner_phone: str
    gps_lat: float
    gps_lng: float
    zone_id: Optional[int] = None
    route_id: Optional[int] = None
    credit_limit: Optional[float] = 0
    owner_cnic_front_photo: Optional[str] = None  # Base64 encoded image
    owner_cnic_back_photo: Optional[str] = None  # Base64 encoded image


class ShopResponse(BaseModel):
    id: int
    name: str
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    credit_limit: float
    outstanding_balance: Optional[float] = 0
    is_registered: bool
    registration_status: str
    verified_by_distributor: Optional[int] = None
    verified_at: Optional[str] = None
    zone_id: Optional[int] = None
    created_by_order_booker: Optional[int] = None
    created_by_order_booker_name: Optional[str] = None
    assigned_to_order_booker: Optional[int] = None
    assigned_to_order_booker_name: Optional[str] = None
    routes: Optional[List[RouteInfo]] = []
    owner_cnic_front_photo: Optional[str] = None
    owner_cnic_back_photo: Optional[str] = None
    shop_exterior_photo: Optional[str] = None
    owner_photo: Optional[str] = None
    credit_limit_request_id: Optional[int] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ShopUpdate(BaseModel):
    name: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    credit_limit: Optional[float] = None
    zone_id: Optional[int] = None
    route_id: Optional[int] = None
    owner_cnic_front_photo: Optional[str] = None  # Base64 encoded image
    owner_cnic_back_photo: Optional[str] = None  # Base64 encoded image


# Shop Verification Schema
class ShopVerify(BaseModel):
    registration_status: str  # "approved" or "rejected"
    remarks: Optional[str] = None


# Daily Collection Schemas
class DailyCollectionCreate(BaseModel):
    shop_id: int
    amount: float
    collected_at: Optional[str] = None  # ISO format datetime string
    remarks: Optional[str] = None
    visit_id: Optional[int] = None  # Link to visit if created during visit


class DailyCollectionResponse(BaseModel):
    id: int
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    shop_owner: Optional[str] = None
    order_id: Optional[int] = None
    collected_by_order_booker: Optional[int] = None
    order_booker_name: Optional[str] = None
    collected_by_delivery_man: Optional[int] = None
    verified_by_distributor: Optional[int] = None
    amount: float
    status: Optional[str] = None
    visit_id: Optional[int] = None
    collection_date: Optional[str] = None
    photo_proof: Optional[str] = None

    class Config:
        from_attributes = True


class DailyCollectionApprove(BaseModel):
    remarks: Optional[str] = None


class DailyCollectionReject(BaseModel):
    remarks: Optional[str] = None


# Payment Schemas
class PaymentResponse(BaseModel):
    id: int
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    order_id: Optional[int] = None
    # Note: Payment table has: id, shop_id, order_id, amount, received_by_distributor, payment_date
    # collected_by_order_booker info comes from daily_collection record
    collected_by_order_booker: Optional[int] = None
    order_booker_name: Optional[str] = None
    received_by_distributor: Optional[int] = None
    amount: Optional[float] = None
    payment_date: Optional[str] = None


# Shop Visit Schemas
class OrderItemCreate(BaseModel):
    product_id: Optional[int] = None  # Product ID (preferred - price will be fetched from products table)
    product_name: Optional[str] = None  # Product name (optional, can be fetched from product_id, used for logging/denormalization)
    quantity: int
    unit_price: Optional[float] = None  # Optional - will be fetched from products table if product_id is provided (backward compatibility)
    # Allow extra fields (like total_price from frontend) to be ignored
    class Config:
        extra = "ignore"  # Ignore extra fields like total_price


class ShopVisitCreate(BaseModel):
    shop_id: Optional[int] = None
    visit_types: Optional[List[str]] = []  # List of visit types: ["order_booking", "daily_collections", etc.]
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    visit_time: Optional[str] = None  # ISO format string (e.g., "2026-01-07T10:30:00")
    photo: Optional[str] = None  # Base64 string or URL
    reason: Optional[str] = None
    # Order data (if visit_types includes "order_booking")
    order_items: Optional[List[OrderItemCreate]] = None  # List of order items
    scheduled_date: Optional[str] = None  # ISO date string (e.g., "2026-01-10")
    # Daily collection data (if visit_types includes "daily_collections")
    collection_amount: Optional[float] = None
    collection_remarks: Optional[str] = None


class ShopVisitResponse(BaseModel):
    id: int
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    shop_zone_id: Optional[int] = None  # Zone ID of the shop
    order_booker_id: Optional[int] = None
    order_booker_name: Optional[str] = None
    delivery_man_id: Optional[int] = None
    delivery_man_name: Optional[str] = None  # Delivery man name
    visit_types: Optional[List[str]] = []  # List of visit types
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    visit_time: Optional[str] = None
    photo: Optional[str] = None  # Legacy single photo
    photos: Optional[List[str]] = None  # Multiple photos (JSON array)
    reason: Optional[str] = None
    # Linked data
    order_id: Optional[int] = None  # Order created during this visit (if order_booking type)
    collection_id: Optional[int] = None  # Collection created during this visit (if daily_collections type)
    # Note: created_at is not in the database schema, visit_time serves as the timestamp

    class Config:
        from_attributes = True


# Order Schemas
class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    shop_id: int
    order_items: List[OrderItemCreate]
    scheduled_date: Optional[str] = None  # ISO date string
    visit_id: Optional[int] = None


class OrderResponse(BaseModel):
    id: int
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    order_booker_id: Optional[int] = None
    order_booker_name: Optional[str] = None
    distributor_id: Optional[int] = None
    delivery_man_id: Optional[int] = None
    delivery_man_name: Optional[str] = None
    visit_id: Optional[int] = None
    total_amount: Optional[float] = None
    status: Optional[str] = None
    scheduled_date: Optional[str] = None
    order_items: Optional[List[OrderItemResponse]] = []
    # GPS removed from orders - stored in shop_visits instead
    # delivery_gps_lat: Optional[float] = None
    # delivery_gps_lng: Optional[float] = None
    delivery_remarks: Optional[str] = None
    delivery_images: Optional[List[str]] = None  # Array of image URLs
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class OrderDeliveryUpdate(BaseModel):
    """Schema for updating order with delivery proof information."""
    status: str  # "delivered" or "cancelled"
    delivery_gps_lat: Optional[float] = None
    delivery_gps_lng: Optional[float] = None
    delivery_remarks: Optional[str] = None
    delivery_images: Optional[List[str]] = None  # Array of Supabase storage URLs


# Credit Limit Request Schemas
class CreditLimitRequestCreate(BaseModel):
    shop_id: int
    requested_credit_limit: float
    remarks: Optional[str] = None


class CreditLimitRequestResponse(BaseModel):
    id: int
    shop_id: int
    shop_name: Optional[str] = None
    requested_by_role: str
    requested_by_id: int
    old_credit_limit: Optional[float] = None
    requested_credit_limit: float
    status: Optional[str] = None
    approved_by_distributor: Optional[int] = None
    approved_at: Optional[str] = None
    remarks: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class CreditLimitRequestUpdate(BaseModel):
    requested_credit_limit: Optional[float] = None
    remarks: Optional[str] = None


class CreditLimitRequestApprove(BaseModel):
    final_credit_limit: Optional[float] = None
    remarks: Optional[str] = None


class CreditLimitRequestReject(BaseModel):
    remarks: Optional[str] = None


# Warehouse Schemas
class WarehouseCreate(BaseModel):
    name: str
    zone_id: int
    address: Optional[str] = None


class WarehouseResponse(BaseModel):
    id: int
    name: str
    zone_id: int
    address: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    zone_id: Optional[int] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


# Inventory Schemas
class InventoryCreate(BaseModel):
    product_id: int  # Required: Must select from active products
    quantity: int = 0
    # item_name, item_code, unit will be auto-filled from product


class InventoryResponse(BaseModel):
    id: int
    warehouse_id: int
    product_id: Optional[int] = None
    product_name: Optional[str] = None  # From products table
    product_code: Optional[str] = None  # From products table
    item_name: str  # Kept for backward compatibility
    item_code: Optional[str] = None  # Kept for backward compatibility
    unit: Optional[str] = None
    quantity: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class InventoryUpdate(BaseModel):
    product_id: Optional[int] = None  # Can change product
    quantity: Optional[int] = None
    # item_name, item_code, unit will be auto-updated from product if product_id changes


# Product Schemas
class ProductCreate(BaseModel):
    code: str
    name: str
    unit: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    code: str
    name: str
    unit: Optional[str] = None
    price: Optional[float] = None
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None


# Activity Log Schemas
class ActivityLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user_role: str
    user_name: Optional[str]
    action_type: str
    entity_type: str
    entity_id: Optional[int]
    timestamp: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    changes_summary: Optional[str]
    reason: Optional[str]
    notes: Optional[str]
    status: str
    error_message: Optional[str]
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True
