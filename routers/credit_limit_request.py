"""
Credit Limit Request Router
===========================
Handles API endpoints for credit limit requests.

API ENDPOINTS:
- POST /credit-limit-requests/order-booker/{order_booker_id} - Create request (Order Booker)
- GET /credit-limit-requests/pending - List pending requests (Distributor)
- PUT /credit-limit-requests/{request_id} - Update request (Distributor)
- POST /credit-limit-requests/{request_id}/approve - Approve request (Distributor)
- POST /credit-limit-requests/{request_id}/reject - Reject request (Distributor)

FLOW:
1. Order Booker creates request → Status: "pending"
2. Distributor views pending requests
3. Distributor can edit credit limit value
4. Distributor approves/rejects → Status: "approved"/"rejected"
5. On approval, shop's credit_limit is updated
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import (
    CreditLimitRequestCreate, CreditLimitRequestResponse,
    CreditLimitRequestUpdate, CreditLimitRequestApprove, CreditLimitRequestReject
)
from services.credit_limit_request_service import CreditLimitRequestService

router = APIRouter(prefix="/credit-limit-requests", tags=["Credit Limit Requests"])


@router.post("/order-booker/{order_booker_id}", response_model=CreditLimitRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_credit_limit_request(
    order_booker_id: int,
    request_data: CreditLimitRequestCreate,
    db: Session = Depends(get_db)
):
    """
    Create a credit limit request for an existing shop.
    
    API: POST /credit-limit-requests/order-booker/{order_booker_id}
    
    FLOW:
    1. Order Booker selects existing shop
    2. Requests credit limit increase/decrease
    3. Service creates request with status="pending"
    4. Returns request data
    
    Request Body:
        {
            "shop_id": 1,
            "requested_credit_limit": 75000.00,
            "remarks": "Shop has good payment history"
        }
    
    Response (201):
        {
            "id": 1,
            "shop_id": 1,
            "requested_by_role": "order_booker",
            "requested_by_id": 1,
            "old_credit_limit": 50000.00,
            "requested_credit_limit": 75000.00,
            "status": "pending",
            ...
        }
    """
    try:
        result = CreditLimitRequestService.create_request(
            db=db,
            shop_id=request_data.shop_id,
            requested_by_role="order_booker",
            requested_by_id=order_booker_id,
            requested_credit_limit=request_data.requested_credit_limit,
            remarks=request_data.remarks
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/pending", response_model=List[CreditLimitRequestResponse])
async def get_pending_requests(
    distributor_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Get all pending credit limit requests.
    
    API: GET /credit-limit-requests/pending?distributor_id={id}
    
    FLOW:
    1. Distributor views dashboard
    2. Service gets all pending requests
    3. Optionally filters by distributor's zone
    4. Returns list with shop information
    
    Response (200):
        [
            {
                "id": 1,
                "shop_id": 1,
                "shop_name": "Ali General Store",
                "shop_owner": "Ahmed Ali",
                "old_credit_limit": 50000.00,
                "requested_credit_limit": 75000.00,
                "status": "pending",
                ...
            },
            ...
        ]
    """
    try:
        requests = CreditLimitRequestService.get_pending_requests(db=db, distributor_id=distributor_id)
        return requests
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pending requests: {str(e)}"
        )


@router.put("/{request_id}", response_model=CreditLimitRequestResponse)
async def update_credit_limit_request(
    request_id: int,
    update_data: CreditLimitRequestUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a pending credit limit request (edit credit limit value).
    
    API: PUT /credit-limit-requests/{request_id}
    
    FLOW:
    1. Distributor views pending request
    2. Edits requested_credit_limit if needed
    3. Service updates request
    4. Returns updated request
    
    Request Body:
        {
            "requested_credit_limit": 80000.00,  // Optional: Edit the requested amount
            "remarks": "Updated based on shop performance"  // Optional
        }
    
    Response (200):
        Updated request data
    """
    try:
        result = CreditLimitRequestService.update_request(
            db=db,
            request_id=request_id,
            requested_credit_limit=update_data.requested_credit_limit,
            remarks=update_data.remarks
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{request_id}/approve", response_model=CreditLimitRequestResponse)
async def approve_credit_limit_request(
    request_id: int,
    approval_data: CreditLimitRequestApprove,
    distributor_id: int,
    db: Session = Depends(get_db)
):
    """
    Approve a credit limit request.
    
    API: POST /credit-limit-requests/{request_id}/approve?distributor_id={id}
    
    FLOW:
    1. Distributor reviews request
    2. Can set final_credit_limit (can differ from requested)
    3. Service approves request and updates shop's credit_limit
    4. Returns approved request
    
    Request Body:
        {
            "final_credit_limit": 80000.00,  // Optional: Can differ from requested
            "remarks": "Approved based on shop performance"
        }
    
    Response (200):
        Approved request data with reviewed_by_distributor and reviewed_at
    """
    try:
        result = CreditLimitRequestService.approve_request(
            db=db,
            request_id=request_id,
            distributor_id=distributor_id,
            final_credit_limit=approval_data.final_credit_limit,
            remarks=approval_data.remarks
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{request_id}/reject", response_model=CreditLimitRequestResponse)
async def reject_credit_limit_request(
    request_id: int,
    rejection_data: CreditLimitRequestReject,
    distributor_id: int,
    db: Session = Depends(get_db)
):
    """
    Reject a credit limit request.
    
    API: POST /credit-limit-requests/{request_id}/reject?distributor_id={id}
    
    FLOW:
    1. Distributor reviews request
    2. Decides to reject
    3. Provides reason in remarks
    4. Service rejects request (shop credit_limit unchanged)
    5. Returns rejected request
    
    Request Body:
        {
            "remarks": "Shop has outstanding dues, cannot increase credit limit"
        }
    
    Response (200):
        Rejected request data with reviewed_by_distributor and reviewed_at
    """
    try:
        result = CreditLimitRequestService.reject_request(
            db=db,
            request_id=request_id,
            distributor_id=distributor_id,
            remarks=rejection_data.remarks
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

