"""
Route router.
Handles route CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict
from config.database import get_db
from models.schemas import RouteCreate, RouteUpdate, RouteResponse, RouteAssign
from services.route_service import RouteService
from utils.dependencies import get_current_user, get_current_distributor
from services.activity_log_service import ActivityLogService

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.post("/{distributor_id}", response_model=RouteResponse, status_code=status.HTTP_201_CREATED, tags=["Routes", "Distributor APIs"])
async def create_route(
    distributor_id: int,
    route: RouteCreate,
    request: Request,
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
            zone_id=route.zone_id,
            order_booker_id=route.order_booker_id
        )
        
        # Log creation
        ActivityLogService.log_create(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='route',
            entity_id=result['id'],
            new_values={
                'name': result.get('name'),
                'zone_id': result.get('zone_id'),
                'order_booker_id': result.get('order_booker_id')
            },
            user_name=distributor.get('user_name'),
            changes_summary=f"Route created: {result.get('name')}",
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            action_type='CREATE',
            entity_type='route',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/distributor/{distributor_id}", response_model=List[RouteResponse], tags=["Routes", "Distributor APIs"])
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


@router.get("/order-booker/{order_booker_id}", response_model=List[RouteResponse], tags=["Routes", "Order Booker APIs"])
async def list_routes_by_order_booker(
    order_booker_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all routes assigned to an order booker. Requires authentication."""
    routes = RouteService.get_routes_by_order_booker(db=db, order_booker_id=order_booker_id)
    return routes


@router.post("/{route_id}/assign", response_model=RouteResponse, tags=["Routes", "Distributor APIs"])
async def assign_route_to_order_booker(
    route_id: int,
    assignment: RouteAssign,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Assign a route to an order booker. Only distributors can assign routes."""
    try:
        # Get old values
        from repositories.route_repository import RouteRepository
        old_route = RouteRepository.get_by_id(db, route_id)
        old_values = {'order_booker_id': old_route.order_booker_id} if old_route else {}
        
        result = RouteService.assign_route_to_order_booker(
            db=db,
            route_id=route_id,
            order_booker_id=assignment.order_booker_id
        )
        
        # Log assignment
        ActivityLogService.log_activity(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            action_type='ASSIGN',
            entity_type='route',
            entity_id=route_id,
            old_values=old_values,
            new_values={'order_booker_id': assignment.order_booker_id},
            user_name=distributor.get('user_name'),
            changes_summary=f"Route {route_id} assigned to order booker {assignment.order_booker_id}",
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            action_type='ASSIGN',
            entity_type='route',
            entity_id=route_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{route_id}", response_model=RouteResponse)
async def update_route(
    route_id: int,
    route: RouteUpdate,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Update route name, zone, and/or order booker assignment.
    Only distributors can update routes.
    
    You can update:
    - Route name only (provide name, omit other fields)
    - Zone only (provide zone_id, omit other fields)
    - Order booker assignment only (provide order_booker_id, omit other fields)
    - Any combination of the above
    - Unassign order booker (explicitly set order_booker_id to null in JSON)
    
    Note: If a field is provided (even if null), it will be updated.
    To unassign order booker, explicitly set order_booker_id to null in the request body.
    """
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
        
        # Check which fields were explicitly provided in the request
        # Pydantic v1 uses __fields_set__, v2 uses model_fields_set
        update_order_booker = False
        update_zone = False
        
        if hasattr(route, '__fields_set__'):
            # Pydantic v1
            update_order_booker = 'order_booker_id' in route.__fields_set__
            update_zone = 'zone_id' in route.__fields_set__
        elif hasattr(route, 'model_fields_set'):
            # Pydantic v2
            update_order_booker = 'order_booker_id' in route.model_fields_set
            update_zone = 'zone_id' in route.model_fields_set
        else:
            # Fallback: Check if fields were provided
            update_order_booker = route.order_booker_id is not None or (route.name is None and route.zone_id is None and route.order_booker_id is not None)
            update_zone = route.zone_id is not None or (route.name is None and route.order_booker_id is None and route.zone_id is not None)
        
        # Get old values
        old_values = {
            'name': existing_route.name,
            'zone_id': existing_route.zone_id,
            'order_booker_id': existing_route.order_booker_id
        }
        
        result = RouteService.update_route(
            db=db, 
            route_id=route_id, 
            name=route.name,
            zone_id=route.zone_id,
            order_booker_id=route.order_booker_id,
            update_order_booker=update_order_booker,
            update_zone=update_zone
        )
        
        # Log update
        ActivityLogService.log_update(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='route',
            entity_id=route_id,
            old_values=old_values,
            new_values={
                'name': result.get('name'),
                'zone_id': result.get('zone_id'),
                'order_booker_id': result.get('order_booker_id')
            },
            user_name=distributor.get('user_name'),
            changes_summary=f"Route updated: {result.get('name')}",
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            action_type='UPDATE',
            entity_type='route',
            entity_id=route_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route(
    route_id: int,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """Delete a route. Only distributors can delete routes."""
    try:
        # Get old values
        from repositories.route_repository import RouteRepository
        old_route = RouteRepository.get_by_id(db, route_id)
        old_values = {
            'name': old_route.name,
            'zone_id': old_route.zone_id,
            'order_booker_id': old_route.order_booker_id
        } if old_route else {}
        
        RouteService.delete_route(db=db, route_id=route_id)
        
        # Log delete
        ActivityLogService.log_delete(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            entity_type='route',
            entity_id=route_id,
            old_values=old_values,
            user_name=distributor.get('user_name'),
            changes_summary=f"Route deleted: {old_values.get('name', 'N/A')}",
            request=request
        )
        
        return None
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor['user_id'],
            user_role='distributor',
            action_type='DELETE',
            entity_type='route',
            entity_id=route_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

