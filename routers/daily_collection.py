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
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import (
    DailyCollectionCreate, DailyCollectionResponse,
    DailyCollectionApprove, DailyCollectionReject
)
from services.daily_collection_service import DailyCollectionService

router = APIRouter(prefix="/daily-collections", tags=["Daily Collections"])


@router.post("/order-booker/{order_booker_id}", response_model=DailyCollectionResponse, status_code=status.HTTP_201_CREATED)
async def submit_daily_collection(
    order_booker_id: int,
    collection: DailyCollectionCreate,
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
    3. Returns list for review
    
    Note: Distributors are not assigned to zones, so distributor_id is accepted
    but doesn't filter results. All pending collections are returned.
    
    Response (200):
        List of pending collections awaiting approval
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


@router.post("/{collection_id}/approve", response_model=dict)
async def approve_daily_collection(
    collection_id: int,
    approval_data: DailyCollectionApprove,
    distributor_id: int,
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
        result = DailyCollectionService.approve_collection(
            db=db,
            collection_id=collection_id,
            distributor_id=distributor_id,
            remarks=approval_data.remarks
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
            detail=f"Error approving collection: {str(e)}"
        )


@router.post("/{collection_id}/reject", response_model=DailyCollectionResponse)
async def reject_daily_collection(
    collection_id: int,
    rejection_data: DailyCollectionReject,
    distributor_id: int,
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
        result = DailyCollectionService.reject_collection(
            db=db,
            collection_id=collection_id,
            distributor_id=distributor_id,
            remarks=rejection_data.remarks
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

