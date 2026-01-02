"""
Distributor router.
Handles distributor CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from models.schemas import DistributorCreate, DistributorResponse, TokenResponse
from services.distributor_service import DistributorService
from repositories.distributor_repository import DistributorRepository

router = APIRouter(prefix="/distributors", tags=["Distributors"])


@router.post("/", response_model=DistributorResponse, status_code=status.HTTP_201_CREATED)
async def create_distributor(distributor: DistributorCreate, db: Session = Depends(get_db)):
    """
    Create a new distributor.
    Note: In production, this should be restricted to Super Admin only.
    """
    try:
        result = DistributorService.create_distributor(
            db=db,
            name=distributor.name,
            email=distributor.email,
            phone=distributor.phone,
            assigned_zone=distributor.assigned_zone,
            password=distributor.password
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[DistributorResponse])
async def list_distributors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all distributors."""
    distributors = DistributorRepository.get_all(db=db, skip=skip, limit=limit)
    return [
        {
            "id": d.id,
            "name": d.name,
            "email": d.email,
            "phone": d.phone,
            "assigned_zone": d.assigned_zone,
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in distributors
    ]


@router.get("/{distributor_id}", response_model=DistributorResponse)
async def get_distributor(distributor_id: int, db: Session = Depends(get_db)):
    """Get distributor by ID."""
    distributor = DistributorRepository.get_by_id(db=db, distributor_id=distributor_id)
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distributor not found"
        )
    return {
        "id": distributor.id,
        "name": distributor.name,
        "email": distributor.email,
        "phone": distributor.phone,
        "assigned_zone": distributor.assigned_zone,
        "created_at": distributor.created_at.isoformat() if distributor.created_at else None
    }

