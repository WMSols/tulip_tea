"""
Location Router
===============
Dedicated endpoint(s) for validating user location against a shop.

API ENDPOINTS:
- GET /location/validate-shop/{shop_id} - Validate current user location against shop (Order Booker / Delivery Man)

Uses existing GeolocationService; does not modify orders, visits, or other flows.
"""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from config.database import get_db
from models.schemas import LocationValidateResponse
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.delivery_man_repository import DeliveryManRepository
from services.geolocation_service import GeolocationService
from utils.dependencies import get_current_user

router = APIRouter(prefix="/location", tags=["Location Validation"])


def _get_user_distributor_id(db: Session, user_id: int, user_role: str):
    """Resolve distributor_id for order_booker or delivery_man."""
    if user_role == "order_booker":
        ob = OrderBookerRepository.get_by_id(db, user_id, include_deleted=False)
        return ob.distributor_id if ob else None
    if user_role == "delivery_man":
        dm = DeliveryManRepository.get_by_id(db, user_id, include_deleted=False)
        return dm.distributor_id if dm else None
    return None


def _get_shop_distributor_id(db: Session, shop) -> int | None:
    """Resolve distributor_id for a shop (via order booker or verified_by_distributor)."""
    ob_id = shop.assigned_to_order_booker or shop.created_by_order_booker
    if ob_id:
        ob = OrderBookerRepository.get_by_id(db, ob_id, include_deleted=False)
        if ob:
            return ob.distributor_id
    if getattr(shop, "verified_by_distributor", None):
        return shop.verified_by_distributor
    return None


@router.get(
    "/validate-shop/{shop_id}",
    response_model=LocationValidateResponse,
    tags=[
        "Location Validation",
        "Order Booker APIs",
        "Delivery Man APIs",
    ],
    summary="Validate user location against shop",
    description="""
    Check whether the **current user's location** (sent by the frontend) is within the allowed distance of the **shop's registered location**.

    - **Authentication:** JWT required. Send `Authorization: Bearer <token>` (Order Booker or Delivery Man login token).
    - **Access:** User can only validate shops that belong to their distributor team.
    - **Threshold:** Within 100m of the shop (GeolocationService.MAX_VISIT_DISTANCE_KM).
    - **Use case:** Before starting a visit or delivery, the app calls this endpoint to confirm the user is at the shop.

    Returns `valid`, `distance_km`, `distance_meters`, and `message`. Does not create or update any orders, visits, or deliveries.
    """,
)
async def validate_location_against_shop(
    shop_id: int,
    lat: float = Query(..., description="User's current latitude (from device GPS)"),
    lng: float = Query(..., description="User's current longitude (from device GPS)"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Restrict to order booker and delivery man only
    if current_user.get("user_role") not in ("order_booker", "delivery_man"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only order bookers and delivery men can validate location against a shop.",
        )

    shop = ShopRepository.get_by_id(db, shop_id, include_deleted=False)
    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    if not shop.gps_lat or not shop.gps_lng:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shop does not have GPS coordinates registered.",
        )

    user_distributor_id = _get_user_distributor_id(
        db, current_user["user_id"], current_user["user_role"]
    )
    shop_distributor_id = _get_shop_distributor_id(db, shop)
    if user_distributor_id is None or shop_distributor_id != user_distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only validate location for shops in your distributor team.",
        )

    # Validate coordinates format
    is_valid_coords, coord_msg = GeolocationService.validate_coordinates(lat, lng)
    if not is_valid_coords:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=coord_msg)

    is_valid, distance_km, message = GeolocationService.validate_visit_location(
        target_lat=Decimal(str(shop.gps_lat)),
        target_lng=Decimal(str(shop.gps_lng)),
        visit_lat=Decimal(str(lat)),
        visit_lng=Decimal(str(lng)),
        entity_type="shop",
    )
    distance_meters = round(distance_km * 1000, 2)

    return LocationValidateResponse(
        valid=is_valid,
        distance_km=round(distance_km, 4),
        distance_meters=distance_meters,
        message=message,
        shop_id=shop_id,
    )
