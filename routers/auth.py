"""
Authentication router.
Handles login for all user roles.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from config.database import get_db
from models.schemas import DistributorLogin, OrderBookerLogin, DeliveryManLogin, TokenResponse
from services.distributor_service import DistributorService
from services.order_booker_service import OrderBookerService
from services.delivery_man_service import DeliveryManService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login/distributor", response_model=TokenResponse)
async def login_distributor(credentials: DistributorLogin, db: Session = Depends(get_db)):
    """Login endpoint for Distributor."""
    result = DistributorService.login_distributor(
        db=db,
        phone=credentials.phone,
        password=credentials.password
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password"
        )
    
    return result


@router.post("/login/order-booker", response_model=TokenResponse)
async def login_order_booker(credentials: OrderBookerLogin, db: Session = Depends(get_db)):
    """Login endpoint for Order Booker."""
    result = OrderBookerService.login_order_booker(
        db=db,
        phone=credentials.phone,
        password=credentials.password
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password"
        )
    
    return result


@router.post("/login/delivery-man", response_model=TokenResponse)
async def login_delivery_man(credentials: DeliveryManLogin, db: Session = Depends(get_db)):
    """Login endpoint for Delivery Man."""
    result = DeliveryManService.login_delivery_man(
        db=db,
        phone=credentials.phone,
        password=credentials.password
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password"
        )
    
    return result

