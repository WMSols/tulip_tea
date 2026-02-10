"""
Subsidy Router
=============
Handles subsidy CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import SubsidyCreate, SubsidyResponse, SubsidyUpdate
from services.subsidy_service import SubsidyService
from utils.dependencies import get_current_user, get_current_distributor
from typing import Dict

router = APIRouter(prefix="/subsidies", tags=["Subsidies"])


@router.post("/distributor/{distributor_id}", response_model=SubsidyResponse, status_code=status.HTTP_201_CREATED, tags=["Subsidies", "Distributor APIs"])
async def create_subsidy(
    distributor_id: int,
    subsidy: SubsidyCreate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Create a new subsidy (by Distributor).
    
    API: POST /subsidies/distributor/{distributor_id}
    
    FLOW:
    1. Distributor creates a subsidy rate (e.g., 5%, 10%, 15%)
    2. Subsidy becomes available for Order Bookers to apply
    3. Order Bookers can use this subsidy when shop credit is insufficient
    
    Request Body:
        {
            "name": "5% Discount",
            "percentage": 5.0,
            "description": "Apply when shop has good payment history"
        }
    
    Response (201):
        Created subsidy data
    """
    # Verify distributor can only create subsidies for their own account
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create subsidies for your own distributor account"
        )
    try:
        from decimal import Decimal
        result = SubsidyService.create_subsidy(
            db=db,
            distributor_id=distributor_id,
            name=subsidy.name,
            percentage=Decimal(str(subsidy.percentage)),
            description=subsidy.description
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
            detail=f"Error creating subsidy: {str(e)}"
        )


@router.get("/distributor/{distributor_id}", response_model=List[SubsidyResponse], tags=["Subsidies", "Distributor APIs"])
async def list_subsidies_by_distributor(
    distributor_id: int,
    include_inactive: bool = False,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    List all subsidies for a distributor.
    
    API: GET /subsidies/distributor/{distributor_id}?include_inactive=false
    
    Response (200):
        List of subsidies
    """
    # Verify distributor can only view their own subsidies
    if distributor['user_id'] != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view subsidies for your own distributor account"
        )
    try:
        subsidies = SubsidyService.get_subsidies_by_distributor(
            db=db,
            distributor_id=distributor_id,
            include_inactive=include_inactive
        )
        return subsidies
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching subsidies: {str(e)}"
        )


@router.get("/distributor/{distributor_id}/active", response_model=List[SubsidyResponse], tags=["Subsidies", "Order Booker APIs"])
async def list_active_subsidies_by_distributor(
    distributor_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all active subsidies for a distributor.
    
    API: GET /subsidies/distributor/{distributor_id}/active
    
    Response (200):
        List of active subsidies (for Order Bookers to use)
    """
    try:
        subsidies = SubsidyService.get_active_subsidies_by_distributor(
            db=db,
            distributor_id=distributor_id
        )
        return subsidies
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching active subsidies: {str(e)}"
        )


@router.get("/{subsidy_id}", response_model=SubsidyResponse, tags=["Subsidies", "Distributor APIs"])
async def get_subsidy(
    subsidy_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Get subsidy by ID.
    
    API: GET /subsidies/{subsidy_id}
    
    Response (200):
        Subsidy data
    """
    try:
        subsidy = SubsidyService.get_subsidy_by_id(db, subsidy_id)
        if not subsidy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subsidy not found"
            )
        # Verify subsidy belongs to the authenticated distributor
        if subsidy.get('distributor_id') != distributor['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access subsidies for your own distributor account"
            )
        return subsidy
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching subsidy: {str(e)}"
        )


@router.put("/{subsidy_id}", response_model=SubsidyResponse, tags=["Subsidies", "Distributor APIs"])
async def update_subsidy(
    subsidy_id: int,
    subsidy_update: SubsidyUpdate,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Update subsidy (by Distributor).
    
    API: PUT /subsidies/{subsidy_id}
    
    Request Body:
        {
            "name": "Updated Name" (optional),
            "percentage": 10.0 (optional),
            "description": "Updated description" (optional),
            "is_active": true (optional)
        }
    
    Response (200):
        Updated subsidy data
    """
    # First verify subsidy exists and belongs to distributor
    try:
        existing_subsidy = SubsidyService.get_subsidy_by_id(db, subsidy_id)
        if not existing_subsidy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subsidy not found"
            )
        if existing_subsidy.get('distributor_id') != distributor['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update subsidies for your own distributor account"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying subsidy ownership: {str(e)}"
        )
    
    try:
        from decimal import Decimal
        update_data = {}
        if subsidy_update.name is not None:
            update_data['name'] = subsidy_update.name
        if subsidy_update.percentage is not None:
            update_data['percentage'] = Decimal(str(subsidy_update.percentage))
        if subsidy_update.description is not None:
            update_data['description'] = subsidy_update.description
        if subsidy_update.is_active is not None:
            update_data['is_active'] = subsidy_update.is_active
        
        result = SubsidyService.update_subsidy(
            db=db,
            subsidy_id=subsidy_id,
            **update_data
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subsidy not found"
            )
        
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating subsidy: {str(e)}"
        )


@router.delete("/{subsidy_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Subsidies", "Distributor APIs"])
async def delete_subsidy(
    subsidy_id: int,
    distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Soft delete subsidy (by Distributor).
    
    API: DELETE /subsidies/{subsidy_id}
    
    Response (204):
        No content
    """
    # First verify subsidy exists and belongs to distributor
    try:
        existing_subsidy = SubsidyService.get_subsidy_by_id(db, subsidy_id)
        if not existing_subsidy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subsidy not found"
            )
        if existing_subsidy.get('distributor_id') != distributor['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete subsidies for your own distributor account"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying subsidy ownership: {str(e)}"
        )
    
    try:
        deleted = SubsidyService.delete_subsidy(db, subsidy_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subsidy not found"
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting subsidy: {str(e)}"
        )

