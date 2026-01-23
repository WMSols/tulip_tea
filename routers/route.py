"""
Route router.
Handles route CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from config.database import get_db
from models.schemas import RouteCreate, RouteUpdate, RouteResponse, RouteAssign
from services.route_service import RouteService
from utils.dependencies import get_current_user, get_current_distributor

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.post("/{distributor_id}", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def create_route(
    distributor_id: int,
    route: RouteCreate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Create a new route. Only distributors can create routes."""
    # Verify distributor can only create routes for their own account
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create routes for your own distributor account"
        )
    try:
        result = RouteService.create_route(
            db=db,
            name=route.name,
            distributor_id=distributor_id,
            zone_id=route.zone_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/distributor/{distributor_id}", response_model=List[RouteResponse])
async def list_routes_by_distributor(
    distributor_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all routes created by a distributor. Requires authentication."""
    routes = RouteService.get_routes_by_distributor(db=db, distributor_id=distributor_id)
    return routes


@router.get("/zone/{zone_id}", response_model=List[RouteResponse])
async def list_routes_by_zone(
    zone_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all routes in a zone. Requires authentication."""
    routes = RouteService.get_routes_by_zone(db=db, zone_id=zone_id)
    return routes


@router.get("/order-booker/{order_booker_id}", response_model=List[RouteResponse])
async def list_routes_by_order_booker(
    order_booker_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all routes assigned to an order booker. Requires authentication."""
    routes = RouteService.get_routes_by_order_booker(db=db, order_booker_id=order_booker_id)
    return routes


@router.post("/{route_id}/assign", response_model=RouteResponse)
async def assign_route_to_order_booker(
    route_id: int,
    assignment: RouteAssign,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Assign a route to an order booker. Only distributors can assign routes."""
    try:
        result = RouteService.assign_route_to_order_booker(
            db=db,
            route_id=route_id,
            order_booker_id=assignment.order_booker_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{route_id}", response_model=RouteResponse)
async def update_route(
    route_id: int,
    route: RouteUpdate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Update route name. Only distributors can update routes."""
    try:
        # Verify route exists and belongs to the distributor
        from repositories.route_repository import RouteRepository
        existing_route = RouteRepository.get_by_id(db, route_id)
        if not existing_route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found"
            )
        
        if existing_route.created_by_distributor != distributor['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update routes that you created"
            )
        
        result = RouteService.update_route(db=db, route_id=route_id, name=route.name)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route(
    route_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Delete a route. Only distributors can delete routes."""
    try:
        RouteService.delete_route(db=db, route_id=route_id)
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

