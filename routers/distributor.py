"""
Distributor router.
Handles distributor CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import DistributorCreate, DistributorResponse, TokenResponse
from services.distributor_service import DistributorService
from repositories.distributor_repository import DistributorRepository
from services.activity_log_service import ActivityLogService
from utils.auth_helpers import get_current_user_from_request

router = APIRouter(prefix="/distributors", tags=["Distributors"])


@router.post("/", response_model=DistributorResponse, status_code=status.HTTP_201_CREATED)
async def create_distributor(distributor: DistributorCreate, request: Request, db: Session = Depends(get_db)):
    """
    Create a new distributor.
    
    Note: 
    - In production, this should be restricted to Super Admin only.
    - Distributors are NOT assigned to zones - they create zones but are not assigned to them.
    - Zones are assigned to Order Bookers and Delivery Men.
    """
    try:
        result = DistributorService.create_distributor(
            db=db,
            name=distributor.name,
            email=distributor.email,
            phone=distributor.phone,
            password=distributor.password
        )
        
        # Log distributor creation
        user_info = get_current_user_from_request(request)
        ActivityLogService.log_create(
            db=db,
            user_id=user_info.get('user_id') if user_info else None,
            user_role=user_info.get('user_role', 'system') if user_info else 'system',
            entity_type='distributor',
            entity_id=result['id'],
            new_values={
                'name': result.get('name'),
                'email': result.get('email'),
                'phone': result.get('phone')
            },
            user_name=user_info.get('user_name') if user_info else None,
            changes_summary=f"Distributor created: {result.get('name')}",
            request=request
        )
        
        return result
    except ValueError as e:
        # Log failure
        user_info = get_current_user_from_request(request)
        ActivityLogService.log_failure(
            db=db,
            user_id=user_info.get('user_id') if user_info else None,
            user_role=user_info.get('user_role', 'system') if user_info else 'system',
            action_type='CREATE',
            entity_type='distributor',
            error_message=str(e),
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[DistributorResponse])
async def list_distributors(skip: int = 0, limit: int = 100, request: Request = None, db: Session = Depends(get_db)):
    """List all distributors."""
    distributors = DistributorRepository.get_all(db=db, skip=skip, limit=limit)
    
    # Log view operation
    if request:
        user_info = get_current_user_from_request(request)
        ActivityLogService.log_activity(
            db=db,
            user_id=user_info.get('user_id') if user_info else None,
            user_role=user_info.get('user_role', 'system') if user_info else 'system',
            action_type='VIEW',
            entity_type='distributor',
            user_name=user_info.get('user_name') if user_info else None,
            changes_summary=f"Listed {len(distributors)} distributors",
            request=request
        )
    
    return [
        {
            "id": d.id,
            "name": d.name,
            "email": d.email,
            "phone": d.phone,
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in distributors
    ]


@router.get("/{distributor_id}", response_model=DistributorResponse)
async def get_distributor(distributor_id: int, request: Request = None, db: Session = Depends(get_db)):
    """Get distributor by ID."""
    distributor = DistributorRepository.get_by_id(db=db, distributor_id=distributor_id)
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distributor not found"
        )
    
    # Log view operation
    if request:
        user_info = get_current_user_from_request(request)
        ActivityLogService.log_activity(
            db=db,
            user_id=user_info.get('user_id') if user_info else None,
            user_role=user_info.get('user_role', 'system') if user_info else 'system',
            action_type='VIEW',
            entity_type='distributor',
            entity_id=distributor_id,
            user_name=user_info.get('user_name') if user_info else None,
            changes_summary=f"Viewed distributor: {distributor.name}",
            request=request
        )
    
    return {
        "id": distributor.id,
        "name": distributor.name,
        "email": distributor.email,
        "phone": distributor.phone,
        "created_at": distributor.created_at.isoformat() if distributor.created_at else None
    }

