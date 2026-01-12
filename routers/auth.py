"""
Authentication Router
=====================
Handles login endpoints for all user roles (Distributor, Order Booker, Delivery Man).

API ENDPOINTS:
- POST /auth/login/distributor
- POST /auth/login/order-booker
- POST /auth/login/delivery-man

FLOW FOR EACH LOGIN:
1. Client sends POST request with phone + password
2. Router validates request body (Pydantic schema)
3. Router calls appropriate Service.login_*() method
4. Service:
   - Gets user from Repository by phone
   - Verifies password using AuthService.verify_password()
   - Creates JWT token using AuthService.create_access_token()
   - Returns token + user info
5. Router returns response to client

RESPONSE:
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "user": {
        "id": 1,
        "name": "John Doe",
        "phone": "03001234567",
        "role": "distributor",
        ...
    }
}
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from config.database import get_db
from models.schemas import DistributorLogin, OrderBookerLogin, DeliveryManLogin, TokenResponse
from services.distributor_service import DistributorService
from services.order_booker_service import OrderBookerService
from services.delivery_man_service import DeliveryManService
from services.activity_log_service import ActivityLogService

# Create router with prefix /auth (all routes will be /auth/*)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login/distributor", response_model=TokenResponse)
async def login_distributor(credentials: DistributorLogin, request: Request, db: Session = Depends(get_db)):
    """
    Login endpoint for Distributor role.
    
    API: POST /auth/login/distributor
    
    FLOW:
    1. Receives credentials (phone, password) from request body
    2. Calls DistributorService.login_distributor()
       - Service gets distributor by phone from repository
       - Service verifies password using bcrypt
       - Service creates JWT token if valid
    3. Returns token + user info, or 401 if invalid
    
    Request Body:
        {
            "phone": "03001234567",
            "password": "password123"
        }
    
    Response (200):
        {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "token_type": "bearer",
            "user": {
                "id": 1,
                "name": "John",
                "phone": "03001234567",
                "email": "john@example.com",
                "zone_id": 1,
                "role": "distributor"
            }
        }
    
    Response (401):
        {
            "detail": "Invalid phone number or password"
        }
    
    Args:
        credentials: DistributorLogin schema (phone, password)
        request: FastAPI Request object (for logging IP/user agent)
        db: Database session (injected by FastAPI Depends)
    
    Returns:
        TokenResponse: JWT token and user information
    """
    # Call service layer to handle login logic
    result = DistributorService.login_distributor(
        db=db,
        phone=credentials.phone,
        password=credentials.password
    )
    
    # If service returns None, credentials are invalid
    if not result:
        # Log failed login attempt
        ActivityLogService.log_failure(
            db=db,
            user_id=None,
            user_role='system',
            action_type='LOGIN',
            entity_type='user',
            error_message='Invalid phone number or password',
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password"
        )
    
    # Log successful login
    ActivityLogService.log_login(
        db=db,
        user_id=result['user']['id'],
        user_role='distributor',
        user_name=result['user'].get('name'),
        request=request
    )
    
    # Return token and user info
    return result


@router.post("/login/order-booker", response_model=TokenResponse)
async def login_order_booker(credentials: OrderBookerLogin, request: Request, db: Session = Depends(get_db)):
    """
    Login endpoint for Order Booker role.
    
    API: POST /auth/login/order-booker
    
    FLOW: Same as distributor login, but uses OrderBookerService
    
    Request Body:
        {
            "phone": "03001234567",
            "password": "password123"
        }
    
    Response: Same format as distributor login, with role="order_booker"
    """
    # Call service layer to handle login logic
    result = OrderBookerService.login_order_booker(
        db=db,
        phone=credentials.phone,
        password=credentials.password
    )
    
    # If service returns None, credentials are invalid
    if not result:
        # Log failed login attempt
        ActivityLogService.log_failure(
            db=db,
            user_id=None,
            user_role='system',
            action_type='LOGIN',
            entity_type='user',
            error_message='Invalid phone number or password',
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password"
        )
    
    # Log successful login
    ActivityLogService.log_login(
        db=db,
        user_id=result['user']['id'],
        user_role='order_booker',
        user_name=result['user'].get('name'),
        request=request
    )
    
    # Return token and user info
    return result


@router.post("/login/delivery-man", response_model=TokenResponse)
async def login_delivery_man(credentials: DeliveryManLogin, request: Request, db: Session = Depends(get_db)):
    """
    Login endpoint for Delivery Man role.
    
    API: POST /auth/login/delivery-man
    
    FLOW: Same as distributor login, but uses DeliveryManService
    
    Request Body:
        {
            "phone": "03001234567",
            "password": "password123"
        }
    
    Response: Same format as distributor login, with role="delivery_man"
    """
    # Call service layer to handle login logic
    result = DeliveryManService.login_delivery_man(
        db=db,
        phone=credentials.phone,
        password=credentials.password
    )
    
    # If service returns None, credentials are invalid
    if not result:
        # Log failed login attempt
        ActivityLogService.log_failure(
            db=db,
            user_id=None,
            user_role='system',
            action_type='LOGIN',
            entity_type='user',
            error_message='Invalid phone number or password',
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password"
        )
    
    # Log successful login
    ActivityLogService.log_login(
        db=db,
        user_id=result['user']['id'],
        user_role='delivery_man',
        user_name=result['user'].get('name'),
        request=request
    )
    
    # Return token and user info
    return result



