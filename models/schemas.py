"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional


# Distributor Schemas
class DistributorCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: str
    password: str
    zone_id: Optional[int] = None


class DistributorLogin(BaseModel):
    phone: str
    password: str


class DistributorResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    phone: str
    zone_id: Optional[int] = None
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


# Delivery Man Schemas
class DeliveryManCreate(BaseModel):
    name: str
    phone: str
    password: str


class DeliveryManLogin(BaseModel):
    phone: str
    password: str


class DeliveryManResponse(BaseModel):
    id: int
    name: str
    phone: str
    zone_id: Optional[int] = None
    distributor_id: int
    created_at: Optional[str]

    class Config:
        from_attributes = True


# Update Schemas
class OrderBookerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    zone_id: Optional[int] = None
    password: Optional[str] = None


class DeliveryManUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    zone_id: Optional[int] = None
    password: Optional[str] = None


# Auth Response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


# Zone Schemas
class ZoneCreate(BaseModel):
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


class RouteResponse(BaseModel):
    id: int
    name: str
    zone_id: Optional[int]
    order_booker_id: Optional[int]
    created_by_distributor: Optional[int]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class RouteAssign(BaseModel):
    order_booker_id: int


# Shop Schemas
class ShopRegister(BaseModel):
    name: str
    owner_name: str
    owner_phone: str
    gps_lat: float
    gps_lng: float
    zone_id: Optional[int] = None
    credit_limit: Optional[float] = 0
    legacy_balance: Optional[float] = 0


class ShopResponse(BaseModel):
    id: int
    name: str
    owner_name: Optional[str]
    owner_phone: Optional[str]
    gps_lat: Optional[float]
    gps_lng: Optional[float]
    credit_limit: Optional[float]
    legacy_balance: Optional[float]
    is_registered: Optional[bool]
    zone_id: Optional[int]
    created_by_order_booker: Optional[int]
    created_at: Optional[str]

    class Config:
        from_attributes = True

