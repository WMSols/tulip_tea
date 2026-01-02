"""
Shop router.
Handles shop registration and management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from config.database import get_db
from models.schemas import ShopRegister, ShopResponse
from services.shop_service import ShopService

router = APIRouter(prefix="/shops", tags=["Shops"])


@router.post("/order-booker/{order_booker_id}", response_model=ShopResponse, status_code=status.HTTP_201_CREATED)
async def register_shop(
    order_booker_id: int,
    shop: ShopRegister,
    db: Session = Depends(get_db)
):
    """Register a new shop (by Order Booker)."""
    try:
        result = ShopService.register_shop(
            db=db,
            name=shop.name,
            owner_name=shop.owner_name,
            owner_phone=shop.owner_phone,
            gps_lat=Decimal(str(shop.gps_lat)),
            gps_lng=Decimal(str(shop.gps_lng)),
            order_booker_id=order_booker_id,
            zone_id=shop.zone_id,
            credit_limit=Decimal(str(shop.credit_limit)) if shop.credit_limit else None,
            legacy_balance=Decimal(str(shop.legacy_balance)) if shop.legacy_balance else None
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/order-booker/{order_booker_id}", response_model=List[ShopResponse])
async def list_shops_by_order_booker(order_booker_id: int, db: Session = Depends(get_db)):
    """List all shops registered by an order booker."""
    shops = ShopService.get_shops_by_order_booker(db=db, order_booker_id=order_booker_id)
    return shops

