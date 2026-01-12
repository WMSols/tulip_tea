"""
Authentication Helper Utilities
================================
Helper functions to extract user information from requests.
"""
from fastapi import Request, HTTPException, status
from typing import Optional, Dict
from services.auth_service import decode_access_token
from jose import JWTError


def get_current_user_from_request(request: Request) -> Optional[Dict]:
    """
    Extract user information from Authorization header in request.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Dict with user_id, user_role, user_name, or None if no token/valid token
    """
    try:
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        
        # Extract token (format: "Bearer <token>")
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        
        token = parts[1]
        
        # Decode token
        payload = decode_access_token(token)
        
        # Extract user info
        user_id = int(payload.get('sub'))
        user_role = payload.get('role')
        
        # Map role names (token uses 'order_booker', but we need 'order_booker' for logs)
        role_mapping = {
            'distributor': 'distributor',
            'order_booker': 'order_booker',
            'delivery_man': 'delivery_man'
        }
        user_role = role_mapping.get(user_role, user_role)
        
        return {
            'user_id': user_id,
            'user_role': user_role,
            'user_name': None  # Will be filled from database if needed
        }
    except (JWTError, ValueError, KeyError):
        # Invalid token or missing fields
        return None






