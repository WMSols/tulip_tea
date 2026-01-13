"""
Authentication Helper Utilities
================================
Helper functions to extract user information from requests.
"""
from fastapi import Request, HTTPException, status
from typing import Optional, Dict
from services.auth_service import decode_access_token
from jose import JWTError


def get_current_user_from_request(request: Request) -> Dict:
    """
    Extract user information from Authorization header in request.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Dict with user_id, user_role, user_name
    
    Raises:
        HTTPException: If no valid token is found
    """
    try:
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing"
            )
        
        # Extract token (format: "Bearer <token>")
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        token = parts[1]
        
        # Decode token
        payload = decode_access_token(token)
        
        # Extract user info
        user_id = int(payload.get('sub'))
        user_role = payload.get('role')
        user_name = payload.get('name')  # May not be in token for all roles
        
        # Map role names (token uses role names, map to standard format)
        role_mapping = {
            'distributor': 'distributor',
            'order_booker': 'order_booker',
            'delivery_man': 'delivery_man',
            'super_admin': 'super_admin'
        }
        user_role = role_mapping.get(user_role, user_role)
        
        return {
            'user_id': user_id,
            'user_role': user_role,
            'user_name': user_name
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )








