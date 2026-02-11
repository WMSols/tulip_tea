"""
FastAPI Dependencies for Authentication
========================================
Reusable dependencies for protecting endpoints with JWT authentication.
"""
from fastapi import Depends, HTTPException, status, Request
from typing import Dict
from utils.auth_helpers import get_current_user_from_request


def get_current_user(request: Request) -> Dict:
    """
    Dependency to get current authenticated user from JWT token.
    
    This dependency:
    - Extracts JWT token from Authorization header
    - Validates token signature and expiration
    - Returns user info (user_id, user_role, user_name)
    - Raises 401 if token is missing, invalid, or expired
    
    Usage:
        @router.get("/protected")
        async def protected_endpoint(
            current_user: Dict = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            user_id = current_user['user_id']
            user_role = current_user['user_role']
            ...
    
    Returns:
        Dict with keys:
            - user_id: int - User's ID
            - user_role: str - User's role (distributor/order_booker/delivery_man)
            - user_name: str - User's name (may be None)
    
    Raises:
        HTTPException 401: If token is missing, invalid, or expired
    """
    try:
        user_info = get_current_user_from_request(request)
        return user_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )


def get_current_distributor(request: Request) -> Dict:
    """
    Dependency to ensure current user is a distributor.
    
    This dependency:
    - Requires valid JWT token
    - Verifies user role is 'distributor'
    - Raises 403 if user is not a distributor
    
    Usage:
        @router.post("/distributor-only")
        async def distributor_endpoint(
            distributor: Dict = Depends(get_current_distributor),
            db: Session = Depends(get_db)
        ):
            distributor_id = distributor['user_id']
            ...
    
    Returns:
        Dict with user info (same as get_current_user)
    
    Raises:
        HTTPException 401: If token is missing, invalid, or expired
        HTTPException 403: If user is not a distributor
    """
    user_info = get_current_user_from_request(request)
    if user_info['user_role'] != 'distributor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only distributors can access this endpoint"
        )
    return user_info


def get_current_order_booker(request: Request) -> Dict:
    """
    Dependency to ensure current user is an order booker.
    
    Usage:
        @router.get("/order-booker-only")
        async def order_booker_endpoint(
            order_booker: Dict = Depends(get_current_order_booker),
            db: Session = Depends(get_db)
        ):
            order_booker_id = order_booker['user_id']
            ...
    
    Returns:
        Dict with user info
    
    Raises:
        HTTPException 401: If token is missing, invalid, or expired
        HTTPException 403: If user is not an order booker
    """
    user_info = get_current_user_from_request(request)
    if user_info['user_role'] != 'order_booker':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only order bookers can access this endpoint"
        )
    return user_info


def get_current_delivery_man(request: Request) -> Dict:
    """
    Dependency to ensure current user is a delivery man.
    
    Usage:
        @router.get("/delivery-man-only")
        async def delivery_man_endpoint(
            delivery_man: Dict = Depends(get_current_delivery_man),
            db: Session = Depends(get_db)
        ):
            delivery_man_id = delivery_man['user_id']
            ...
    
    Returns:
        Dict with user info
    
    Raises:
        HTTPException 401: If token is missing, invalid, or expired
        HTTPException 403: If user is not a delivery man
    """
    user_info = get_current_user_from_request(request)
    if user_info['user_role'] != 'delivery_man':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only delivery men can access this endpoint"
        )
    return user_info


def get_current_super_admin(request: Request) -> Dict:
    """
    Dependency to ensure current user is a super admin.
    
    Usage:
        @router.get("/super-admin-only")
        async def super_admin_endpoint(
            super_admin: Dict = Depends(get_current_super_admin),
            db: Session = Depends(get_db)
        ):
            admin_id = super_admin['user_id']
            ...
    
    Returns:
        Dict with user info
    
    Raises:
        HTTPException 401: If token is missing, invalid, or expired
        HTTPException 403: If user is not a super admin
    """
    user_info = get_current_user_from_request(request)
    if user_info['user_role'] != 'super_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can access this endpoint"
        )
    return user_info


