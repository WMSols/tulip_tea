"""
Credit Limit Request Router
===========================
Handles API endpoints for credit limit requests.

API ENDPOINTS:
- POST /credit-limit-requests/order-booker/{order_booker_id} - Create request (Order Booker)
- GET /credit-limit-requests/all?distributor_id={id} - Get all requests (pending, approved, disapproved) (Distributor)
- PUT /credit-limit-requests/{request_id} - Update request (Distributor)
- POST /credit-limit-requests/{request_id}/approve - Approve request (Distributor)
- POST /credit-limit-requests/{request_id}/reject - Reject request (Distributor)
- DELETE /credit-limit-requests/{request_id} - Soft delete DISAPPROVED request (Distributor)
- GET /credit-limit-requests/order-booker/{order_booker_id}/my-requests - Get all requests by order booker

COMMENTED OUT (Distributor endpoints - disabled):
- GET /credit-limit-requests/pending - List pending requests (Distributor) - Use /all instead

FLOW:
1. Order Booker creates request → Status: "pending"
2. Distributor views pending requests
3. Distributor can edit credit limit value
4. Distributor approves/rejects → Status: "approved"/"disapproved"
5. On approval, shop's credit_limit is updated
6. Distributor can soft delete DISAPPROVED requests
7. Order booker can view all their requests (including soft-deleted, excluding APPROVED)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import (
    CreditLimitRequestCreate, CreditLimitRequestResponse,
    CreditLimitRequestUpdate, CreditLimitRequestApprove, CreditLimitRequestReject
)
from services.credit_limit_request_service import CreditLimitRequestService
from services.activity_log_service import ActivityLogService
from utils.dependencies import get_current_order_booker, get_current_distributor, get_current_user
from typing import Dict

router = APIRouter(prefix="/credit-limit-requests", tags=["Credit Limit Requests"])


@router.post("/order-booker/{order_booker_id}", response_model=CreditLimitRequestResponse, status_code=status.HTTP_201_CREATED, tags=["Credit Limit Requests", "Order Booker APIs"])
async def create_credit_limit_request(
    order_booker_id: int,
    request_data: CreditLimitRequestCreate,
    request: Request,
    order_booker: Dict = Depends(get_current_order_booker),
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
    # Verify order booker can only create requests for themselves
    if order_booker['user_id'] != order_booker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create credit limit requests for your own account"
        )
    
    try:
        result = CreditLimitRequestService.create_request(
            db=db,
            shop_id=request_data.shop_id,
            requested_by_role="order_booker",
            requested_by_id=order_booker_id,
            requested_credit_limit=request_data.requested_credit_limit,
            remarks=request_data.remarks
        )
        
        # Log credit limit request creation (with error handling to prevent transaction rollback)
        try:
            ActivityLogService.log_activity(
                db=db,
                user_id=order_booker_id,
                user_role='order_booker',
                action_type='CREATE',
                entity_type='credit_limit_request',
                entity_id=result['id'],
                new_values={
                    'shop_id': result.get('shop_id'),
                    'shop_name': result.get('shop_name'),
                    'old_credit_limit': str(result.get('old_credit_limit', 0)),
                    'requested_credit_limit': str(result.get('requested_credit_limit', 0)),
                    'status': result.get('status')
                },
                changes_summary=f"Credit limit request: {result.get('shop_name')} - {result.get('old_credit_limit', 0)} → {result.get('requested_credit_limit', 0)}",
                reason=request_data.remarks,
                request=request
            )
        except Exception as log_error:
            # Logging failures should not break the operation
            print(f"⚠️ Failed to log credit limit request creation (non-critical): {log_error}")
            import traceback
            traceback.print_exc()
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/all", response_model=List[CreditLimitRequestResponse], tags=["Credit Limit Requests", "Distributor APIs"])
async def get_all_credit_limit_requests(
    distributor_id: int = Query(..., description="Distributor ID to filter requests"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return (default: 50)"),
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Get all credit limit requests (pending, approved, disapproved) for shops belonging to the specified distributor.
    
    API: GET /credit-limit-requests/all?distributor_id={id}&skip=0&limit=50
    
    FLOW:
    1. Distributor views all credit limit requests
    2. Service gets all requests (pending, approved, disapproved) filtered to shops belonging to this distributor's order bookers
    3. Returns paginated list with shop information
    
    Query Parameters:
        distributor_id: Required - Distributor ID - Only returns requests for shops that:
            - Were created by an order booker belonging to this distributor, OR
            - Are assigned to an order booker belonging to this distributor, OR
            - Were verified by this distributor
        skip: Number of records to skip (for pagination, default: 0)
        limit: Maximum number of records to return (default: 50, max: 500)
    
    Response (200):
        [
            {
                "id": 1,
                "shop_id": 1,
                "shop_name": "Ali General Store",
                "shop_owner": "Ahmed Ali",
                "old_credit_limit": 50000.00,
                "requested_credit_limit": 75000.00,
                "status": "pending",  // or "approved" or "disapproved"
                ...
            },
            ...
        ]
    """
    # Verify distributor can only view requests for their own account
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view credit limit requests for your own distributor account"
        )
    
    try:
        requests = CreditLimitRequestService.get_all_requests_by_distributor(
            db=db,
            distributor_id=distributor_id,
            skip=skip,
            limit=limit
        )
        return requests
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching credit limit requests: {str(e)}"
        )


# COMMENTED OUT: Temporarily disabled distributor endpoints
# @router.get("/pending", response_model=List[CreditLimitRequestResponse], tags=["Credit Limit Requests", "Distributor APIs", "Order Booker APIs"])
# async def get_pending_requests(
#     distributor_id: int = Query(..., description="Distributor ID to filter pending requests"),
#     current_user: Dict = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get all pending credit limit requests for shops belonging to the specified distributor.
#     
#     API: GET /credit-limit-requests/pending?distributor_id={id}
#     
#     FLOW:
#     1. Distributor views dashboard
#     2. Service gets pending requests filtered to shops belonging to this distributor's order bookers
#     3. Returns list with shop information
#     
#     Query Parameters:
#         distributor_id: Required - Only returns requests for shops that:
#             - Were created by an order booker belonging to this distributor, OR
#             - Are assigned to an order booker belonging to this distributor, OR
#             - Were verified by this distributor
#     
#     Response (200):
#         [
#             {
#                 "id": 1,
#                 "shop_id": 1,
#                 "shop_name": "Ali General Store",
#                 "shop_owner": "Ahmed Ali",
#                 "old_credit_limit": 50000.00,
#                 "requested_credit_limit": 75000.00,
#                 "status": "pending",
#                 ...
#             },
#             ...
#         ]
#     """
#     # Verify user can only view requests for their own distributor if they're a distributor
#     if current_user['user_role'] == 'distributor' and current_user['user_id'] != distributor_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only view pending requests for your own distributor account"
#         )
#     
#     try:
#         requests = CreditLimitRequestService.get_pending_requests(db=db, distributor_id=distributor_id)
#         return requests
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error fetching pending requests: {str(e)}"
#         )


@router.put("/{request_id}", response_model=CreditLimitRequestResponse, tags=["Credit Limit Requests", "Distributor APIs"])
async def update_credit_limit_request(
    request_id: int,
    update_data: CreditLimitRequestUpdate,
    distributor: Dict = Depends(get_current_distributor),
    request: Request = None,
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


@router.post("/{request_id}/approve", response_model=CreditLimitRequestResponse, tags=["Credit Limit Requests", "Distributor APIs"])
async def approve_credit_limit_request(
    request_id: int,
    approval_data: CreditLimitRequestApprove,
    distributor_id: int,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
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
        Approved request data with approved_by_distributor and approved_at
    """
    # Verify distributor can only approve requests for their own account
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only approve requests for your own distributor account"
        )
    
    try:
        # Get request before approval for logging
        from repositories.credit_limit_request_repository import CreditLimitRequestRepository
        request_before = CreditLimitRequestRepository.get_by_id(db, request_id)
        if not request_before:
            raise ValueError("Credit limit request not found")
        
        old_status = request_before.status
        old_credit_limit = float(request_before.old_credit_limit) if request_before.old_credit_limit else 0
        requested_limit = float(request_before.requested_credit_limit) if request_before.requested_credit_limit else 0
        
        result = CreditLimitRequestService.approve_request(
            db=db,
            request_id=request_id,
            distributor_id=distributor_id,
            final_credit_limit=approval_data.final_credit_limit,
            remarks=approval_data.remarks
        )
        
        # Get final credit limit (may differ from requested)
        final_limit = float(approval_data.final_credit_limit) if approval_data.final_credit_limit else requested_limit
        
        # Log credit limit approval
        ActivityLogService.log_approve(
            db=db,
            user_id=distributor_id,
            user_role='distributor',
            entity_type='credit_limit_request',
            entity_id=request_id,
            old_values={
                'status': old_status,
                'old_credit_limit': str(old_credit_limit),
                'requested_credit_limit': str(requested_limit)
            },
            new_values={
                'status': result.get('status'),
                'final_credit_limit': str(final_limit)
            },
            changes_summary=f"Credit limit approved: {result.get('shop_name')} - {old_credit_limit} → {final_limit}",
            reason=approval_data.remarks,
            metadata={'shop_id': result.get('shop_id')},
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor_id,
            user_role='distributor',
            action_type='APPROVE',
            entity_type='credit_limit_request',
            entity_id=request_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{request_id}/reject", response_model=CreditLimitRequestResponse, tags=["Credit Limit Requests", "Distributor APIs"])
async def reject_credit_limit_request(
    request_id: int,
    rejection_data: CreditLimitRequestReject,
    distributor_id: int,
    request: Request,
    distributor: Dict = Depends(get_current_distributor),
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
        Rejected request data with approved_by_distributor and approved_at
    """
    # Verify distributor can only reject requests for their own account
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only reject requests for your own distributor account"
        )
    
    try:
        # Get request before rejection for logging
        from repositories.credit_limit_request_repository import CreditLimitRequestRepository
        request_before = CreditLimitRequestRepository.get_by_id(db, request_id)
        if not request_before:
            raise ValueError("Credit limit request not found")
        
        old_status = request_before.status
        old_credit_limit = float(request_before.old_credit_limit) if request_before.old_credit_limit else 0
        requested_limit = float(request_before.requested_credit_limit) if request_before.requested_credit_limit else 0
        
        result = CreditLimitRequestService.reject_request(
            db=db,
            request_id=request_id,
            distributor_id=distributor_id,
            remarks=rejection_data.remarks
        )
        
        # Log credit limit rejection
        ActivityLogService.log_reject(
            db=db,
            user_id=distributor_id,
            user_role='distributor',
            entity_type='credit_limit_request',
            entity_id=request_id,
            old_values={
                'status': old_status,
                'old_credit_limit': str(old_credit_limit),
                'requested_credit_limit': str(requested_limit)
            },
            new_values={'status': result.get('status')},
            changes_summary=f"Credit limit request rejected: {result.get('shop_name')} - Requested: {old_credit_limit} → {requested_limit}",
            reason=rejection_data.remarks,
            metadata={'shop_id': result.get('shop_id')},
            request=request
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{request_id}", status_code=status.HTTP_200_OK, tags=["Credit Limit Requests", "Distributor APIs"])
async def soft_delete_credit_limit_request(
    request_id: int,
    distributor: Dict = Depends(get_current_distributor),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Soft delete a DISAPPROVED credit limit request.
    
    API: DELETE /credit-limit-requests/{request_id}
    
    FLOW:
    1. Validates request exists and is DISAPPROVED
    2. Soft deletes request (sets deleted_at)
    3. Logs the deletion in activity log
    4. Returns soft-deleted request data
    
    Rules:
    - Only DISAPPROVED requests can be soft deleted
    - PENDING and APPROVED requests cannot be deleted
    - Request must not already be soft deleted
    
    Response (200):
        Soft-deleted request data with deleted_at timestamp
    """
    try:
        # Get request before deletion for logging
        from repositories.credit_limit_request_repository import CreditLimitRequestRepository
        request_before = CreditLimitRequestRepository.get_by_id(db, request_id)
        if not request_before:
            raise ValueError("Credit limit request not found")
        
        # Get shop name for logging
        from repositories.shop_repository import ShopRepository
        shop = ShopRepository.get_by_id(db, request_before.shop_id)
        shop_name = shop.name if shop else "Unknown"
        
        # Soft delete the request
        result = CreditLimitRequestService.soft_delete_request(db=db, request_id=request_id)
        
        # Log the soft deletion in activity log (with error handling to prevent transaction rollback)
        try:
            ActivityLogService.log_activity(
                db=db,
                user_id=distributor['user_id'],
                user_role='distributor',
                action_type='DELETE',
                entity_type='credit_limit_request',
                entity_id=request_id,
                user_name=distributor.get('name'),
                old_values={
                    'status': request_before.status.value if hasattr(request_before.status, 'value') else str(request_before.status),
                    'shop_id': request_before.shop_id,
                    'shop_name': shop_name,
                    'requested_credit_limit': str(request_before.requested_credit_limit),
                    'old_credit_limit': str(request_before.old_credit_limit) if request_before.old_credit_limit else None
                },
                changes_summary=f"Credit limit request soft deleted: {shop_name} - Request ID: {request_id}",
                request=request
            )
        except Exception as log_error:
            # Logging failures should not break the operation
            print(f"⚠️ Failed to log credit limit request soft delete (non-critical): {log_error}")
            import traceback
            traceback.print_exc()
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/order-booker/{order_booker_id}/my-requests", response_model=List[CreditLimitRequestResponse], tags=["Credit Limit Requests", "Order Booker APIs"])
async def get_my_credit_limit_requests(
    order_booker_id: int,
    order_booker: Dict = Depends(get_current_order_booker),
    db: Session = Depends(get_db)
):
    """
    Get all credit limit requests created by this order booker.
    
    API: GET /credit-limit-requests/order-booker/{order_booker_id}/my-requests
    
    FLOW:
    1. Order booker views their requests
    2. Service gets all requests (including soft-deleted, excluding APPROVED)
    3. Returns list with shop information
    
    Returns:
    - PENDING requests (including soft-deleted)
    - DISAPPROVED requests (including soft-deleted)
    - Does NOT return APPROVED requests
    
    Response (200):
        [
            {
                "id": 1,
                "shop_id": 1,
                "shop_name": "Ali General Store",
                "status": "pending",
                "deleted_at": null,  // or timestamp if soft-deleted
                ...
            },
            ...
        ]
    """
    # Verify order booker can only view their own requests
    if order_booker['user_id'] != order_booker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own credit limit requests"
        )
    
    try:
        requests = CreditLimitRequestService.get_requests_by_order_booker(
            db=db,
            order_booker_id=order_booker_id,
            include_soft_deleted=True
        )
        return requests
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching requests: {str(e)}"
        )
