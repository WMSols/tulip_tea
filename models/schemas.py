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
    assigned_zone: str
    password: str


class DistributorLogin(BaseModel):
    phone: str
    password: str


class DistributorResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    phone: str
    assigned_zone: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


# Order Booker Schemas
class OrderBookerCreate(BaseModel):
    name: str
    phone: str
    assigned_zone: str
    password: str
    email: Optional[EmailStr] = None


class OrderBookerLogin(BaseModel):
    phone: str
    password: str


class OrderBookerResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    phone: str
    assigned_zone: Optional[str]
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
    distributor_id: int
    created_at: Optional[str]

    class Config:
        from_attributes = True


# Auth Response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

