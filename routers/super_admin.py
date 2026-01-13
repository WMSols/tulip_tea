"""
Super Admin Router
==================
Handles super admin endpoints for viewing and managing all entities.

API ENDPOINTS:
- POST /super-admin/login - Super admin login
- GET /super-admin/entities - Get all entities (distributors, order_bookers, delivery_men, shops, zones, routes)
- PUT /super-admin/entities/{entity_type}/{entity_id}/toggle-active - Toggle is_active status
- PUT /super-admin/entities/{entity_type}/{entity_id}/reactivate - Reactivate soft-deleted entity
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, List, Any
from config.database import get_db
from models.schemas import SuperAdminLogin, TokenResponse
from services.super_admin_service import SuperAdminService
from services.activity_log_service import ActivityLogService
from utils.auth_helpers import get_current_user_from_request
from repositories.distributor_repository import DistributorRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.delivery_man_repository import DeliveryManRepository
from repositories.shop_repository import ShopRepository
from repositories.zone_repository import ZoneRepository
from repositories.route_repository import RouteRepository

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])


@router.post("/login", response_model=TokenResponse)
async def login_super_admin(credentials: SuperAdminLogin, request: Request, db: Session = Depends(get_db)):
    """
    Super admin login endpoint.
    
    API: POST /super-admin/login
    
    Request Body:
        {
            "email": "admin@tuliptea.com",
            "password": "admin123"
        }
    
    Response (200):
        {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "token_type": "bearer",
            "user": {
                "id": 1,
                "name": "Super Admin",
                "email": "admin@tuliptea.com",
                "role": "super_admin"
            }
        }
    """
    try:
        result = SuperAdminService.login_super_admin(
            db=db,
            email=credentials.email,
            password=credentials.password
        )
        
        if not result:
            try:
                ActivityLogService.log_failure(
                    db=db,
                    user_id=None,
                    user_role='super_admin',
                    action_type='LOGIN',
                    entity_type='super_admin',
                    error_message='Invalid email or password',
                    metadata={'email': credentials.email},
                    request=request
                )
            except Exception as log_error:
                # Don't fail login if logging fails
                print(f"Warning: Failed to log login failure: {log_error}")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        try:
            ActivityLogService.log_login(
                db=db,
                user_id=result['user']['id'],
                user_role='super_admin',
                user_name=result['user']['name'],
                request=request
            )
        except Exception as log_error:
            # Don't fail login if logging fails
            print(f"Warning: Failed to log login: {log_error}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@router.get("/entities")
async def get_all_entities(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get all entities in the system (for super admin dashboard).
    
    API: GET /super-admin/entities
    
    FLOW:
    1. Super admin requests all entities
    2. Service fetches all distributors, order_bookers, delivery_men, shops, zones, routes
    3. Returns formatted list with is_active status
    
    Response (200):
        {
            "distributors": [...],
            "order_bookers": [...],
            "delivery_men": [...],
            "shops": [...],
            "zones": [...],
            "routes": [...]
        }
    """
    # Verify super admin
    user_info = get_current_user_from_request(request)
    if user_info['user_role'] != 'super_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can access this endpoint"
        )
    
    try:
        # Import models for direct queries
        from models.distributor import Distributor
        from models.order_booker import OrderBooker
        from models.delivery_man import DeliveryMan
        from models.shop import Shop
        from models.zone import Zone
        from models.route import Route
        
        # Get all distributors (include deleted/inactive for super admin view)
        try:
            distributors = db.query(Distributor).all()
        except Exception as e:
            print(f"Error querying distributors: {e}")
            distributors = []
        distributors_list = []
        for d in distributors:
            distributors_list.append({
                "id": d.id,
                "name": d.name,
                "email": d.email,
                "phone": d.phone,
                "is_active": d.is_active,
                "deleted_at": d.deleted_at.isoformat() if d.deleted_at else None,
                "created_at": d.created_at.isoformat() if d.created_at else None
            })
        
        # Get all order bookers (include deleted/inactive)
        try:
            order_bookers = db.query(OrderBooker).all()
        except Exception as e:
            print(f"Error querying order_bookers: {e}")
            order_bookers = []
        order_bookers_list = []
        for ob in order_bookers:
            order_bookers_list.append({
                "id": ob.id,
                "name": ob.name,
                "email": ob.email,
                "phone": ob.phone,
                "zone_id": ob.zone_id,
                "distributor_id": ob.distributor_id,
                "is_active": ob.is_active,
                "deleted_at": ob.deleted_at.isoformat() if ob.deleted_at else None,
                "created_at": ob.created_at.isoformat() if ob.created_at else None
            })
        
        # Get all delivery men (include deleted/inactive)
        try:
            delivery_men = db.query(DeliveryMan).all()
        except Exception as e:
            print(f"Error querying delivery_men: {e}")
            delivery_men = []
        delivery_men_list = []
        for dm in delivery_men:
            delivery_men_list.append({
                "id": dm.id,
                "name": dm.name,
                "phone": dm.phone,
                "distributor_id": dm.distributor_id,
                "is_active": dm.is_active,
                "deleted_at": dm.deleted_at.isoformat() if dm.deleted_at else None,
                "created_at": dm.created_at.isoformat() if dm.created_at else None
            })
        
        # Get all shops (include deleted/inactive)
        try:
            # Rollback any previous failed transaction
            db.rollback()
            
            # Query shops - handle missing outstanding_balance column gracefully
            try:
                shops = db.query(Shop).all()
                print(f"DEBUG: Found {len(shops)} shops in database")
            except Exception as shop_error:
                # If outstanding_balance column doesn't exist, use raw SQL
                if "outstanding_balance" in str(shop_error):
                    print("WARNING: outstanding_balance column not found, using raw SQL query")
                    db.rollback()
                    from sqlalchemy import text
                    result = db.execute(text("""
                        SELECT id, name, owner_name, owner_phone, credit_limit, 
                               is_active, registration_status, zone_id, deleted_at, created_at 
                        FROM shops
                    """))
                    shops = []
                    for row in result:
                        # Create a simple object-like structure
                        class ShopRow:
                            def __init__(self, row):
                                self.id = row[0]
                                self.name = row[1]
                                self.owner_name = row[2]
                                self.owner_phone = row[3]
                                self.credit_limit = row[4]
                                self.is_active = row[5]
                                self.registration_status = row[6]
                                self.zone_id = row[7]
                                self.deleted_at = row[8]
                                self.created_at = row[9]
                        shops.append(ShopRow(row))
                    print(f"DEBUG: Found {len(shops)} shops using raw SQL query")
                else:
                    raise shop_error
        except Exception as e:
            import traceback
            print(f"ERROR querying shops: {e}")
            traceback.print_exc()
            db.rollback()
            shops = []
        shops_list = []
        for s in shops:
            try:
                shops_list.append({
                    "id": s.id,
                    "name": s.name,
                    "owner_name": s.owner_name,
                    "owner_phone": s.owner_phone,
                    "credit_limit": float(s.credit_limit) if s.credit_limit else 0,
                    "is_active": s.is_active,
                    "registration_status": s.registration_status,
                    "zone_id": s.zone_id,
                    "deleted_at": s.deleted_at.isoformat() if s.deleted_at else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                })
            except Exception as e:
                print(f"ERROR processing shop {s.id if hasattr(s, 'id') else 'unknown'}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Get all zones (include deleted/inactive)
        try:
            # Rollback any previous failed transaction
            db.rollback()
            
            zones = db.query(Zone).all()
            print(f"DEBUG: Found {len(zones)} zones in database")
        except Exception as e:
            import traceback
            print(f"ERROR querying zones: {e}")
            traceback.print_exc()
            db.rollback()
            zones = []
        zones_list = []
        for z in zones:
            try:
                zones_list.append({
                    "id": z.id,
                    "name": z.name,
                    "is_active": z.is_active,
                    "deleted_at": z.deleted_at.isoformat() if z.deleted_at else None,
                    "created_at": z.created_at.isoformat() if z.created_at else None
                })
            except Exception as e:
                print(f"ERROR processing zone {z.id if hasattr(z, 'id') else 'unknown'}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Get all routes (include deleted/inactive)
        try:
            # Rollback any previous failed transaction
            db.rollback()
            
            routes = db.query(Route).all()
            print(f"DEBUG: Found {len(routes)} routes in database")
        except Exception as e:
            import traceback
            print(f"ERROR querying routes: {e}")
            traceback.print_exc()
            db.rollback()
            routes = []
        routes_list = []
        for r in routes:
            routes_list.append({
                "id": r.id,
                "name": r.name,
                "zone_id": r.zone_id,
                "order_booker_id": r.order_booker_id,
                "is_active": r.is_active,
                "deleted_at": r.deleted_at.isoformat() if r.deleted_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None
            })
        
        result = {
            "distributors": distributors_list,
            "order_bookers": order_bookers_list,
            "delivery_men": delivery_men_list,
            "shops": shops_list,
            "zones": zones_list,
            "routes": routes_list
        }
        
        # Debug logging
        print(f"Super Admin Entities Response:")
        print(f"  Distributors: {len(distributors_list)}")
        print(f"  Order Bookers: {len(order_bookers_list)}")
        print(f"  Delivery Men: {len(delivery_men_list)}")
        print(f"  Shops: {len(shops_list)}")
        print(f"  Zones: {len(zones_list)}")
        print(f"  Routes: {len(routes_list)}")
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching entities: {str(e)}"
        )


@router.put("/entities/{entity_type}/{entity_id}/toggle-active")
async def toggle_entity_active(
    entity_type: str,
    entity_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Toggle is_active status for any entity.
    
    API: PUT /super-admin/entities/{entity_type}/{entity_id}/toggle-active
    
    Path Parameters:
        entity_type: One of: "distributor", "order_booker", "delivery_man", "shop", "zone", "route"
        entity_id: ID of the entity to toggle
    
    FLOW:
    1. Super admin requests to toggle entity active status
    2. Service finds entity by type and ID
    3. Toggles is_active (True → False, False → True)
    4. Logs the action
    5. Returns updated entity
    
    Response (200):
        {
            "id": 1,
            "entity_type": "distributor",
            "is_active": false,
            "message": "Entity status updated successfully"
        }
    """
    # Verify super admin
    user_info = get_current_user_from_request(request)
    if user_info['user_role'] != 'super_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can access this endpoint"
        )
    
    print(f"=== TOGGLE ACTIVE ENDPOINT HIT ===")
    print(f"Entity Type: {entity_type}")
    print(f"Entity ID: {entity_id}")
    
    try:
        entity = None
        old_is_active = None
        
        # Get entity based on type
        if entity_type == "distributor":
            entity = DistributorRepository.get_by_id(db, entity_id, include_deleted=True)
            if not entity:
                raise ValueError(f"Distributor with ID {entity_id} not found")
            old_is_active = entity.is_active
            entity.is_active = not entity.is_active
            db.commit()
            db.refresh(entity)
        
        elif entity_type == "order_booker":
            entity = OrderBookerRepository.get_by_id(db, entity_id, include_deleted=True)
            if not entity:
                raise ValueError(f"Order Booker with ID {entity_id} not found")
            old_is_active = entity.is_active
            entity.is_active = not entity.is_active
            db.commit()
            db.refresh(entity)
        
        elif entity_type == "delivery_man":
            entity = DeliveryManRepository.get_by_id(db, entity_id, include_deleted=True)
            if not entity:
                raise ValueError(f"Delivery Man with ID {entity_id} not found")
            old_is_active = entity.is_active
            entity.is_active = not entity.is_active
            db.commit()
            db.refresh(entity)
        
        elif entity_type == "shop":
            print("Getting shop...")
            # Query shop including deleted ones for toggle
            entity = ShopRepository.get_by_id(db, entity_id, include_deleted=True)
            print(f"Shop query result: {entity}")
            if not entity:
                print(f"ERROR: Shop with ID {entity_id} not found")
                raise ValueError(f"Shop with ID {entity_id} not found")
            print(f"Found shop: ID={entity.id}, Name={entity.name}, deleted_at={entity.deleted_at}, is_active={entity.is_active}")
            old_is_active = entity.is_active
            entity.is_active = not entity.is_active
            print(f"Toggling is_active from {old_is_active} to {entity.is_active}")
            db.commit()
            db.refresh(entity)
            print(f"Shop updated: is_active={entity.is_active}")
        
        elif entity_type == "zone":
            entity = ZoneRepository.get_by_id(db, entity_id, include_deleted=True)
            if not entity:
                raise ValueError(f"Zone with ID {entity_id} not found")
            old_is_active = entity.is_active
            entity.is_active = not entity.is_active
            db.commit()
            db.refresh(entity)
        
        elif entity_type == "route":
            entity = RouteRepository.get_by_id(db, entity_id, include_deleted=True)
            if not entity:
                raise ValueError(f"Route with ID {entity_id} not found")
            old_is_active = entity.is_active
            entity.is_active = not entity.is_active
            db.commit()
            db.refresh(entity)
        
        else:
            raise ValueError(f"Invalid entity_type: {entity_type}. Must be one of: distributor, order_booker, delivery_man, shop, zone, route")
        
        # Store the result before logging (in case logging fails and rolls back)
        result = {
            "id": entity_id,
            "entity_type": entity_type,
            "is_active": entity.is_active,
            "message": f"{entity_type.title()} status updated successfully"
        }
        
        # Log the action (with error handling to prevent transaction rollback)
        try:
            ActivityLogService.log_update(
                db=db,
                user_id=user_info['user_id'],
                user_role='super_admin',
                entity_type=entity_type,
                entity_id=entity_id,
                old_values={"is_active": old_is_active},
                new_values={"is_active": entity.is_active},
                changes_summary=f"Super Admin {user_info['user_name']} toggled {entity_type} {entity_id} active status from {old_is_active} to {entity.is_active}",
                request=request
            )
        except Exception as log_error:
            # Logging failures should not break the operation
            print(f"⚠️ Failed to log activity (non-critical): {log_error}")
            # If logging fails, rollback and re-commit the entity change
            db.rollback()
            # Re-apply the entity change
            entity.is_active = not old_is_active
            db.commit()
            db.refresh(entity)
            import traceback
            traceback.print_exc()
        
        return result
    
    except ValueError as e:
        print(f"=== TOGGLE ACTIVE VALUE ERROR ===")
        print(f"Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        print(f"=== TOGGLE ACTIVE EXCEPTION ===")
        print(f"Entity Type: {entity_type}")
        print(f"Entity ID: {entity_id}")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling entity active status: {str(e)}"
        )


@router.put("/entities/{entity_type}/{entity_id}/reactivate")
async def reactivate_entity(
    entity_type: str,
    entity_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Reactivate a soft-deleted entity (sets deleted_at to NULL and is_active to True).
    
    API: PUT /super-admin/entities/{entity_type}/{entity_id}/reactivate
    
    Path Parameters:
        entity_type: One of: "distributor", "order_booker", "delivery_man", "shop", "zone", "route"
        entity_id: ID of the entity to reactivate
    
    FLOW:
    1. Super admin requests to reactivate entity
    2. Service finds entity by type and ID (including deleted)
    3. Sets deleted_at to NULL and is_active to True
    4. Logs the action
    5. Returns updated entity
    
    Response (200):
        {
            "id": 1,
            "entity_type": "distributor",
            "is_active": true,
            "deleted_at": null,
            "message": "Entity reactivated successfully"
        }
    """
    print(f"=== REACTIVATE ENDPOINT HIT ===")
    print(f"Entity Type: {entity_type}")
    print(f"Entity ID: {entity_id}")
    print(f"Request Path: {request.url.path}")
    print(f"Request Method: {request.method}")
    
    try:
        # Verify super admin
        print("Verifying super admin...")
        user_info = get_current_user_from_request(request)
        print(f"User Info: {user_info}")
        
        if user_info['user_role'] != 'super_admin':
            print(f"ERROR: User role is {user_info['user_role']}, expected super_admin")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can access this endpoint"
            )
        print("Super admin verified successfully")
    
        from datetime import datetime
        entity = None
        old_deleted_at = None
        old_is_active = None
        
        print(f"Processing reactivate for {entity_type} with ID {entity_id}")
        
        # Get entity based on type (must include deleted)
        if entity_type == "distributor":
            print("Getting distributor...")
            entity = DistributorRepository.get_by_id(db, entity_id, include_deleted=True)
            if not entity:
                raise ValueError(f"Distributor with ID {entity_id} not found")
            old_deleted_at = entity.deleted_at
            old_is_active = entity.is_active
            entity.deleted_at = None
            entity.is_active = True
            db.commit()
            db.refresh(entity)
        
        elif entity_type == "order_booker":
            entity = OrderBookerRepository.get_by_id(db, entity_id, include_deleted=True)
            if not entity:
                raise ValueError(f"Order Booker with ID {entity_id} not found")
            old_deleted_at = entity.deleted_at
            old_is_active = entity.is_active
            entity.deleted_at = None
            entity.is_active = True
            db.commit()
            db.refresh(entity)
        
        elif entity_type == "delivery_man":
            entity = DeliveryManRepository.get_by_id(db, entity_id, include_deleted=True)
            if not entity:
                raise ValueError(f"Delivery Man with ID {entity_id} not found")
            old_deleted_at = entity.deleted_at
            old_is_active = entity.is_active
            entity.deleted_at = None
            entity.is_active = True
            db.commit()
            db.refresh(entity)
        
        elif entity_type == "shop":
            print("Getting shop...")
            # Query shop including deleted ones
            entity = ShopRepository.get_by_id(db, entity_id, include_deleted=True)
            print(f"Shop query result: {entity}")
            if not entity:
                print(f"ERROR: Shop with ID {entity_id} not found")
                raise ValueError(f"Shop with ID {entity_id} not found")
            print(f"Found shop: ID={entity.id}, Name={entity.name}, deleted_at={entity.deleted_at}, is_active={entity.is_active}")
            old_deleted_at = entity.deleted_at
            old_is_active = entity.is_active
            entity.deleted_at = None
            entity.is_active = True
            print("Updating shop...")
            db.commit()
            db.refresh(entity)
            print(f"Shop updated: deleted_at={entity.deleted_at}, is_active={entity.is_active}")
        
        elif entity_type == "zone":
            entity = ZoneRepository.get_by_id(db, entity_id, include_deleted=True)
            if not entity:
                raise ValueError(f"Zone with ID {entity_id} not found")
            old_deleted_at = entity.deleted_at
            old_is_active = entity.is_active
            entity.deleted_at = None
            entity.is_active = True
            db.commit()
            db.refresh(entity)
        
        elif entity_type == "route":
            entity = RouteRepository.get_by_id(db, entity_id, include_deleted=True)
            if not entity:
                raise ValueError(f"Route with ID {entity_id} not found")
            old_deleted_at = entity.deleted_at
            old_is_active = entity.is_active
            entity.deleted_at = None
            entity.is_active = True
            db.commit()
            db.refresh(entity)
        
        else:
            raise ValueError(f"Invalid entity_type: {entity_type}. Must be one of: distributor, order_booker, delivery_man, shop, zone, route")
        
        # Store the result before logging (in case logging fails and rolls back)
        result = {
            "id": entity_id,
            "entity_type": entity_type,
            "is_active": True,
            "deleted_at": None,
            "message": f"{entity_type.title()} reactivated successfully"
        }
        
        # Log the action (with error handling to prevent transaction rollback)
        print("Logging activity...")
        try:
            ActivityLogService.log_update(
                db=db,
                user_id=user_info['user_id'],
                user_role='super_admin',
                entity_type=entity_type,
                entity_id=entity_id,
                old_values={"deleted_at": old_deleted_at.isoformat() if old_deleted_at else None, "is_active": old_is_active},
                new_values={"deleted_at": None, "is_active": True},
                changes_summary=f"Super Admin {user_info['user_name']} reactivated {entity_type} {entity_id} (restored from soft delete)",
                request=request
            )
            print("Activity logged successfully")
        except Exception as log_error:
            print(f"WARNING: Failed to log activity: {log_error}")
            # If logging fails, rollback and re-commit the entity change
            db.rollback()
            # Re-apply the entity change
            entity.deleted_at = None
            entity.is_active = True
            db.commit()
            db.refresh(entity)
            import traceback
            traceback.print_exc()
        
        result = {
            "id": entity_id,
            "entity_type": entity_type,
            "is_active": True,
            "deleted_at": None,
            "message": f"{entity_type.title()} reactivated successfully"
        }
        print(f"Returning result: {result}")
        print("=== REACTIVATE SUCCESS ===")
        return result
    
    except HTTPException as e:
        print(f"=== REACTIVATE HTTP EXCEPTION ===")
        print(f"Status: {e.status_code}")
        print(f"Detail: {e.detail}")
        raise e
    except ValueError as e:
        print(f"=== REACTIVATE VALUE ERROR ===")
        print(f"Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        print(f"=== REACTIVATE EXCEPTION ===")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reactivating entity: {str(e)}"
        )

