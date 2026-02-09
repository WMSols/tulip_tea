"""
Daily Collection Router
=======================
Handles daily collection operations.

API ENDPOINTS:
- POST /daily-collections/order-booker/{id} - Submit daily collection (Order Booker)
- GET /daily-collections/order-booker/{id} - List collections by order booker
- GET /daily-collections/pending - List pending collections (Distributor)
- POST /daily-collections/{id}/approve - Approve collection (Distributor)
- POST /daily-collections/{id}/reject - Reject collection (Distributor)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import (
    DailyCollectionCreate, DailyCollectionResponse,
    DailyCollectionApprove, DailyCollectionReject
)
from services.daily_collection_service import DailyCollectionService
from services.activity_log_service import ActivityLogService
from utils.auth_helpers import get_current_user_from_request

router = APIRouter(prefix="/daily-collections", tags=["Daily Collections"])


@router.post("/delivery-man/{delivery_man_id}", response_model=DailyCollectionResponse, status_code=status.HTTP_201_CREATED, tags=["Daily Collections", "Delivery Man APIs"])
async def submit_daily_collection_by_delivery_man(
    delivery_man_id: int,
    collection: DailyCollectionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Submit a daily collection entry (by Delivery Man).
    
    API: POST /daily-collections/delivery-man/{delivery_man_id}
    
    FLOW:
    1. Delivery Man visits shop and collects payment
    2. Delivery Man submits collection entry with amount
    3. Collection is created with status="pending"
    4. **INSTANTLY reduces shop's outstanding_balance** (for immediate credit limit increase)
    5. Returns collection data with updated credit info
    
    Request Body:
        {
            "shop_id": 1,
            "amount": 5000.00,
            "collected_at": "2026-01-05T10:30:00",  // Optional
            "remarks": "Cash collection from shop owner",
            "order_id": 123  // Optional, if collection is for a specific order
        }
    
    Response (201):
        Created collection data with status="pending" and updated shop credit info
    """
    try:
        from datetime import datetime
        collected_at = None
        if collection.collected_at:
            collected_at = datetime.fromisoformat(collection.collected_at.replace('Z', '+00:00'))
        
        result = DailyCollectionService.create_collection_for_delivery_man(
            db=db,
            shop_id=collection.shop_id,
            delivery_man_id=delivery_man_id,
            amount=collection.amount,
            collected_at=collected_at,
            remarks=collection.remarks,
            order_id=getattr(collection, 'order_id', None)
        )
        
        # Log collection creation
        ActivityLogService.log_create(
            db=db,
            user_id=delivery_man_id,
            user_role='delivery_man',
            entity_type='daily_collection',
            entity_id=result['id'],
            new_values={
                'shop_id': result.get('shop_id'),
                'shop_name': result.get('shop_name'),
                'amount': str(result.get('amount', 0)),
                'status': result.get('status')
            },
            metadata={
                'visit_id': result.get('visit_id'),
                'order_id': result.get('order_id'),
                'remarks': collection.remarks,
                'summary': f"Collection recorded: {result.get('shop_name')} - Rs. {result.get('amount', 0)}"
            },
            request=request
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating collection: {str(e)}"
        )


@router.post("/order-booker/{order_booker_id}", response_model=DailyCollectionResponse, status_code=status.HTTP_201_CREATED)
async def submit_daily_collection(
    order_booker_id: int,
    collection: DailyCollectionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Submit a daily collection entry (by Order Booker).
    
    API: POST /daily-collections/order-booker/{order_booker_id}
    
    FLOW:
    1. Order Booker visits shop and collects payment
    2. Order Booker submits collection entry with amount
    3. Collection is created with status="pending"
    4. Returns collection data
    
    Request Body:
        {
            "shop_id": 1,
            "amount": 5000.00,
            "collected_at": "2026-01-05T10:30:00",  // Optional
            "remarks": "Cash collection from shop owner"
        }
    
    Response (201):
        Created collection data with status="pending"
    """
    try:
        from datetime import datetime
        collected_at = None
        if collection.collected_at:
            collected_at = datetime.fromisoformat(collection.collected_at.replace('Z', '+00:00'))
        
        result = DailyCollectionService.create_collection(
            db=db,
            shop_id=collection.shop_id,
            order_booker_id=order_booker_id,
            amount=collection.amount,
            collected_at=collected_at,
            remarks=collection.remarks
        )
        
        # Log collection creation
        ActivityLogService.log_create(
            db=db,
            user_id=order_booker_id,
            user_role='order_booker',
            entity_type='daily_collection',
            entity_id=result['id'],
            new_values={
                'shop_id': result.get('shop_id'),
                'shop_name': result.get('shop_name'),
                'amount': str(result.get('amount', 0)),
                'status': result.get('status')
            },
            metadata={
                'visit_id': result.get('visit_id'),
                'order_id': result.get('order_id'),
                'remarks': collection.remarks,
                'summary': f"Collection recorded: {result.get('shop_name')} - Rs. {result.get('amount', 0)}"
            },
            request=request
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating collection: {str(e)}"
        )


@router.get("/{collection_id}", response_model=DailyCollectionResponse)
async def get_collection_by_id(
    collection_id: int,
    db: Session = Depends(get_db)
):
    """Get a daily collection by ID."""
    try:
        from repositories.daily_collection_repository import DailyCollectionRepository
        from repositories.shop_repository import ShopRepository
        from repositories.order_booker_repository import OrderBookerRepository
        
        collection = DailyCollectionRepository.get_by_id(db, collection_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found"
            )
        
        shop = ShopRepository.get_by_id(db, collection.shop_id) if collection.shop_id else None
        order_booker = OrderBookerRepository.get_by_id(db, collection.collected_by_order_booker) if collection.collected_by_order_booker else None
        
        return {
            "id": collection.id,
            "shop_id": collection.shop_id,
            "shop_name": shop.name if shop else None,
            "shop_owner": shop.owner_name if shop else None,
            "order_id": collection.order_id,
            "collected_by_order_booker": collection.collected_by_order_booker,
            "order_booker_name": order_booker.name if order_booker else None,
            "collected_by_delivery_man": collection.collected_by_delivery_man,
            "verified_by_distributor": collection.verified_by_distributor,
            "amount": float(collection.amount) if collection.amount else 0,
            "status": collection.status,
            "visit_id": collection.visit_id,
            "collection_date": collection.collection_date.isoformat() if collection.collection_date else None,
            "photo_proof": collection.photo_proof
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching collection: {str(e)}"
        )


@router.get("/delivery-man/{delivery_man_id}", response_model=List[DailyCollectionResponse])
async def list_collections_by_delivery_man(
    delivery_man_id: int,
    db: Session = Depends(get_db)
):
    """
    List all daily collections submitted by a delivery man.
    
    API: GET /daily-collections/delivery-man/{delivery_man_id}
    
    Response (200):
        List of collections with shop information
    """
    try:
        collections = DailyCollectionService.get_collections_by_delivery_man(
            db=db,
            delivery_man_id=delivery_man_id
        )
        return collections
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching collections: {str(e)}"
        )


@router.get("/order-booker/{order_booker_id}", response_model=List[DailyCollectionResponse])
async def list_collections_by_order_booker(
    order_booker_id: int,
    db: Session = Depends(get_db)
):
    """
    List all daily collections submitted by an order booker.
    
    API: GET /daily-collections/order-booker/{order_booker_id}
    
    Response (200):
        List of collections with shop information
    """
    try:
        collections = DailyCollectionService.get_collections_by_order_booker(
            db=db,
            order_booker_id=order_booker_id
        )
        return collections
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching collections: {str(e)}"
        )


@router.get("/pending", response_model=List[DailyCollectionResponse])
async def list_pending_collections(
    distributor_id: int = None,
    db: Session = Depends(get_db)
):
    """
    List all pending daily collections (for Distributor).
    
    API: GET /daily-collections/pending?distributor_id={id}
    
    FLOW:
    1. Distributor views pending collections
    2. Service gets all collections with status="pending"
    3. Returns list for review with complete trail (shop, route, zone, collector)
    
    Note: Distributors are not assigned to zones, so distributor_id is accepted
    but doesn't filter results. All pending collections are returned.
    
    Response (200):
        List of pending collections awaiting approval with complete trail information
    """
    try:
        collections = DailyCollectionService.get_pending_collections(
            db=db,
            distributor_id=distributor_id
        )
        return collections
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pending collections: {str(e)}"
        )


@router.get("/all", response_model=List[DailyCollectionResponse])
async def list_all_collections(
    distributor_id: int = None,
    status: str = None,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """
    List all daily collections with complete trail information (for Distributor).
    
    API: GET /daily-collections/all?distributor_id={id}&status={status}&skip={skip}&limit={limit}
    
    FLOW:
    1. Distributor views all collections (or filtered by status)
    2. Service gets all collections with complete trail information
    3. Returns list with shop, route, zone, collector details
    
    Query Parameters:
        distributor_id: Optional (not used for filtering, kept for API consistency)
        status: Optional status filter ("pending", "verified", "rejected")
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 1000)
    
    Response (200):
        List of all collections with complete trail information:
        - Shop details (name, owner)
        - Route information (route_id, route_name)
        - Zone information (zone_id, zone_name)
        - Collector information (order_booker_name or delivery_man_name)
        - Collection details (amount, date, status)
    """
    try:
        collections = DailyCollectionService.get_all_collections(
            db=db,
            distributor_id=distributor_id,
            status=status,
            skip=skip,
            limit=limit
        )
        return collections
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching collections: {str(e)}"
        )


@router.post("/{collection_id}/approve", response_model=dict, tags=["Daily Collections", "Distributor APIs"])
async def approve_daily_collection(
    collection_id: int,
    approval_data: DailyCollectionApprove,
    distributor_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Approve a daily collection and create payment record.
    
    API: POST /daily-collections/{collection_id}/approve?distributor_id={id}
    
    FLOW:
    1. Distributor reviews pending collection
    2. Approves collection (sets status, reviewed_by, reviewed_at)
    3. Creates payment record from collection
    4. Links collection to payment
    5. Returns approved collection and payment data
    
    Request Body:
        {
            "remarks": "Approved, payment verified"
        }
    
    Response (200):
        Approved collection and created payment data
    """
    try:
        # Get collection before approval for logging
        from repositories.daily_collection_repository import DailyCollectionRepository
        collection_before = DailyCollectionRepository.get_by_id(db, collection_id)
        if not collection_before:
            raise ValueError("Collection not found")
        
        old_status = collection_before.status
        old_amount = float(collection_before.amount) if collection_before.amount else 0
        
        result = DailyCollectionService.approve_collection(
            db=db,
            collection_id=collection_id,
            distributor_id=distributor_id,
            remarks=approval_data.remarks
        )
        
        # Log collection approval
        ActivityLogService.log_approve(
            db=db,
            user_id=distributor_id,
            user_role='distributor',
            entity_type='daily_collection',
            entity_id=collection_id,
            old_values={'status': old_status, 'amount': str(old_amount)},
            new_values={
                'status': result.get('collection', {}).get('status'),
                'amount': str(result.get('collection', {}).get('amount', 0)),
                'payment_id': result.get('payment', {}).get('id')
            },
            changes_summary=f"Collection approved: Rs. {old_amount} - Payment ID: {result.get('payment', {}).get('id')}",
            reason=approval_data.remarks,
            metadata={'payment_id': result.get('payment', {}).get('id')},
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
            entity_type='daily_collection',
            entity_id=collection_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log failure
        ActivityLogService.log_failure(
            db=db,
            user_id=distributor_id,
            user_role='distributor',
            action_type='APPROVE',
            entity_type='daily_collection',
            entity_id=collection_id,
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving collection: {str(e)}"
        )


@router.post("/{collection_id}/reject", response_model=DailyCollectionResponse, tags=["Daily Collections", "Distributor APIs"])
async def reject_daily_collection(
    collection_id: int,
    rejection_data: DailyCollectionReject,
    distributor_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Reject a daily collection.
    
    API: POST /daily-collections/{collection_id}/reject?distributor_id={id}
    
    FLOW:
    1. Distributor reviews pending collection
    2. Rejects collection (sets status, reviewed_by, reviewed_at)
    3. Returns rejected collection data
    
    Request Body:
        {
            "remarks": "Amount mismatch, please verify"
        }
    
    Response (200):
        Rejected collection data
    """
    try:
        # Get collection before rejection for logging
        from repositories.daily_collection_repository import DailyCollectionRepository
        collection_before = DailyCollectionRepository.get_by_id(db, collection_id)
        if not collection_before:
            raise ValueError("Collection not found")
        
        old_status = collection_before.status
        old_amount = float(collection_before.amount) if collection_before.amount else 0
        
        result = DailyCollectionService.reject_collection(
            db=db,
            collection_id=collection_id,
            distributor_id=distributor_id,
            remarks=rejection_data.remarks
        )
        
        # Log collection rejection
        ActivityLogService.log_reject(
            db=db,
            user_id=distributor_id,
            user_role='distributor',
            entity_type='daily_collection',
            entity_id=collection_id,
            old_values={'status': old_status, 'amount': str(old_amount)},
            new_values={'status': result.get('status')},
            changes_summary=f"Collection rejected: Rs. {old_amount}",
            reason=rejection_data.remarks,
            request=request
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting collection: {str(e)}"
        )

