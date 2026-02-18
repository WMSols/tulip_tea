"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any


# Distributor Schemas
class DistributorCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: str
    password: str
    # Note: Distributors are NOT assigned to zones - they create zones but are not assigned to them


class DistributorUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    # Note: All fields are optional - only provided fields will be updated


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
    name: str = Field(..., min_length=1, description="Order booker name cannot be empty")
    phone: str
    password: str
    email: Optional[EmailStr] = None
    zone_id: Optional[int] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Order booker name cannot be empty')
        return v.strip()


class OrderBookerLogin(BaseModel):
    phone: str
    password: str


class OrderBookerResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    phone: str
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None  # Denormalized zone name
    distributor_id: int
    distributor_name: Optional[str] = None  # Denormalized distributor name
    created_at: Optional[str]

    class Config:
        from_attributes = True


class OrderBookerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Order booker name cannot be empty if provided")
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    zone_id: Optional[int] = None
    password: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError('Order booker name cannot be empty')
            return v.strip()
        return v


# Delivery Man Schemas
class DeliveryManCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Delivery man name cannot be empty")
    phone: str
    password: str
    zone_id: Optional[int] = None
    # Note: Delivery men work by zone, not routes - route_ids removed
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Delivery man name cannot be empty')
        return v.strip()


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
    name: Optional[str] = Field(None, min_length=1, description="Delivery man name cannot be empty if provided")
    phone: Optional[str] = None
    zone_id: Optional[int] = None
    password: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError('Delivery man name cannot be empty')
            return v.strip()
        return v


# Zone Schemas
class ZoneCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Zone name cannot be empty")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Zone name cannot be empty')
        return v.strip()


class ZoneUpdate(BaseModel):
    name: str = Field(..., min_length=1, description="Zone name cannot be empty")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Zone name cannot be empty')
        return v.strip()


class ZoneResponse(BaseModel):
    id: int
    name: str
    route_count: Optional[int] = None  # Number of routes in this zone
    shop_count: Optional[int] = None  # Number of shops in this zone
    created_at: Optional[str]

    class Config:
        from_attributes = True


# Route Schemas
class RouteCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Route name cannot be empty")
    zone_id: int
    order_booker_id: Optional[int] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Route name cannot be empty')
        return v.strip()


class RouteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Route name cannot be empty if provided")
    zone_id: Optional[int] = None
    order_booker_id: Optional[int] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError('Route name cannot be empty')
            return v.strip()
        return v


class RouteResponse(BaseModel):
    id: int
    name: str
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None  # Denormalized zone name
    order_booker_id: Optional[int] = None
    order_booker_name: Optional[str] = None  # Denormalized order booker name
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
    legacy_balance: Optional[float] = 0
    owner_cnic_front_photo: Optional[str] = None  # Base64 encoded image
    owner_cnic_back_photo: Optional[str] = None  # Base64 encoded image
    owner_photo: Optional[str] = None  # Base64 encoded image
    shop_exterior_photo: Optional[str] = None  # Base64 encoded image
    user_gps_lat: Optional[float] = None  # Order booker's current GPS location for validation
    user_gps_lng: Optional[float] = None  # Order booker's current GPS location for validation


class ShopResponse(BaseModel):
    id: int
    name: str
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    credit_limit: float
    # legacy_balance removed from response - it's now part of outstanding_balance
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
    legacy_balance: Optional[float] = None
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
    collected_at: str  # ISO format datetime string - Required from frontend
    remarks: Optional[str] = None
    visit_id: Optional[int] = None  # Link to visit if created during visit
    order_id: Optional[int] = None  # Link to order if collection is for a specific order


class DailyCollectionResponse(BaseModel):
    id: int
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    shop_owner: Optional[str] = None
    order_id: Optional[int] = None
    collected_by_order_booker: Optional[int] = None
    order_booker_name: Optional[str] = None
    collected_by_delivery_man: Optional[int] = None
    delivery_man_name: Optional[str] = None
    verified_by_distributor: Optional[int] = None
    amount: float
    status: Optional[str] = None
    visit_id: Optional[int] = None
    collection_date: Optional[str] = None
    photo_proof: Optional[str] = None
    shop_outstanding_balance: Optional[float] = None
    shop_credit_limit: Optional[float] = None
    shop_available_credit: Optional[float] = None

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
    # Note: user_gps_lat and user_gps_lng are optional fields for location validation.
    # If provided, the backend will validate that the user is near the shop location.
    # If not provided, validation will use gps_lat/gps_lng (visit location) instead.
    shop_id: Optional[int] = None
    visit_types: Optional[List[str]] = []  # List of visit types: ["order_booking", "daily_collections", etc.]
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    visit_time: str  # ISO format string (e.g., "2026-01-07T10:30:00") - Required from frontend
    photo: Optional[str] = None  # Base64 string or URL
    reason: Optional[str] = None
    # Order data (if visit_types includes "order_booking")
    order_items: Optional[List[OrderItemCreate]] = None  # List of order items
    scheduled_date: Optional[str] = None  # ISO date string (e.g., "2026-01-10")
    # New subsidy approval system (replaces order_resolution_type and subsidy_id)
    final_total_amount: Optional[float] = None  # Final amount after order booker edits (optional, defaults to calculated total)
    # DEPRECATED: Legacy fields (kept for backward compatibility, will be ignored)
    order_resolution_type: Optional[str] = None  # DEPRECATED: Use final_total_amount instead
    subsidy_id: Optional[int] = None  # DEPRECATED: Not used in new system
    # Daily collection data (if visit_types includes "daily_collections")
    collection_amount: Optional[float] = None
    collection_remarks: Optional[str] = None


class ShopVisitResponse(BaseModel):
    id: int
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    shop_zone_id: Optional[int] = None  # Zone ID of the shop
    shop_routes: Optional[List[Dict]] = None  # List of routes this shop belongs to
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
    final_total_amount: Optional[float] = None  # Final amount after order booker edits (optional, defaults to calculated total)
    order_resolution_type: Optional[str] = None  # 'normal', 'payment_before_delivery', or None (defaults to 'normal')
    subsidy_id: Optional[int] = None  # Subsidy ID to apply (can be used with any order_resolution_type)


class SubsidyInfo(BaseModel):
    """Subsidy information for orders."""
    id: int
    name: str
    percentage: float

    class Config:
        from_attributes = True


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
    # New subsidy approval system
    calculated_total_amount: Optional[float] = None  # Original calculated total from items (original_amount)
    final_total_amount: Optional[float] = None  # Final amount after order booker edits
    subsidy_status: Optional[str] = None  # 'none', 'pending_approval', 'approved', 'rejected'
    subsidy_approved_by: Optional[int] = None  # Distributor ID who approved
    subsidy_approved_at: Optional[str] = None  # Timestamp when approved
    subsidy_rejection_reason: Optional[str] = None  # Reason if rejected
    # DEPRECATED: Legacy fields (kept for backward compatibility)
    order_resolution_type: Optional[str] = None  # DEPRECATED: Use subsidy_status instead
    subsidy_id: Optional[int] = None  # DEPRECATED: Not used
    subsidy_info: Optional[SubsidyInfo] = None  # DEPRECATED: Not used
    original_amount: Optional[float] = None  # DEPRECATED: Use calculated_total_amount instead
    payment_collected_before_delivery: Optional[bool] = False
    payment_collected_amount: Optional[float] = None
    payment_collected_at: Optional[str] = None

    class Config:
        from_attributes = True


class OrderDeliveryUpdate(BaseModel):
    """Schema for updating order with delivery proof information."""
    status: str  # "delivered" or "cancelled"
    delivery_gps_lat: Optional[float] = None
    delivery_gps_lng: Optional[float] = None
    delivery_remarks: Optional[str] = None
    delivery_images: Optional[List[str]] = None  # Array of Supabase storage URLs


class OrderPaymentCollection(BaseModel):
    """Schema for collecting payment before delivery."""
    payment_amount: float
    remarks: Optional[str] = None


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
    requested_by_name: Optional[str] = None  # Denormalized name of requester
    old_credit_limit: Optional[float] = None
    requested_credit_limit: float
    status: Optional[str] = None
    approved_by_distributor: Optional[int] = None
    approved_by_distributor_name: Optional[str] = None  # Denormalized name of approver
    approved_at: Optional[str] = None
    remarks: Optional[str] = None
    created_at: Optional[str] = None
    deleted_at: Optional[str] = None  # Soft delete timestamp
    is_active: Optional[bool] = True  # Active status - distributors see only active requests

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
    distributor_id: int
    zone_id: Optional[int] = None
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
    price: Optional[float] = None


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


# Subsidy Schemas
class SubsidyCreate(BaseModel):
    name: str
    percentage: float
    description: Optional[str] = None


class SubsidyUpdate(BaseModel):
    name: Optional[str] = None
    percentage: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SubsidyResponse(BaseModel):
    id: int
    distributor_id: int
    name: str
    description: Optional[str]
    percentage: float
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    deleted_at: Optional[str]

    class Config:
        from_attributes = True


# Wallet Schemas
class WalletTransferRequest(BaseModel):
    from_user_type: str  # 'distributor', 'order_booker', 'delivery_man'
    from_user_id: int
    to_user_type: str  # 'distributor', 'order_booker', 'delivery_man'
    to_user_id: int
    amount: float
    description: Optional[str] = None
    initiated_by_type: Optional[str] = None  # 'distributor', 'order_booker', 'delivery_man', 'system'
    initiated_by_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class WalletCollectionRequest(BaseModel):
    """Request for distributor to collect money from order booker or delivery man."""
    from_user_type: str  # 'order_booker' or 'delivery_man'
    from_user_id: int
    amount: float
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Weekly Route Schedule Schemas
class WeeklyRouteScheduleCreate(BaseModel):
    assignee_type: str  # 'order_booker' or 'delivery_man'
    assignee_id: int
    route_id: int
    day_of_week: int  # 0=Monday, 6=Sunday


class WeeklyRouteScheduleUpdate(BaseModel):
    route_id: Optional[int] = None
    day_of_week: Optional[int] = None
    is_active: Optional[bool] = None


class WeeklyRouteScheduleResponse(BaseModel):
    id: int
    assignee_type: str
    assignee_id: int
    assignee_name: Optional[str] = None
    route_id: int
    route_name: Optional[str] = None
    day_of_week: int
    is_active: bool
    created_by_distributor: int
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# Visit Task Schemas
class VisitTaskResponse(BaseModel):
    id: int
    shop_id: int
    shop_name: Optional[str] = None
    shop_owner: Optional[str] = None
    shop_phone: Optional[str] = None
    shop_gps_lat: Optional[float] = None
    shop_gps_lng: Optional[float] = None
    route_id: int
    route_name: Optional[str] = None
    scheduled_date: str
    day_of_week: int
    status: str
    shop_visit_id: Optional[int] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class VisitTaskStatusUpdate(BaseModel):
    status: str  # 'pending', 'in_progress', 'completed', 'skipped', 'cancelled'
    shop_visit_id: Optional[int] = None
    notes: Optional[str] = None


class TaskGenerationRequest(BaseModel):
    weeks_ahead: Optional[int] = 4
    assignee_type: Optional[str] = None  # 'order_booker' or 'delivery_man'
