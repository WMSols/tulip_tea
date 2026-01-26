"""
Credit Limit Request Business Logic Service
===========================================
Handles business logic for credit limit requests.

This service layer:
- Validates business rules
- Coordinates between repositories
- Handles credit limit updates on approval
- Returns formatted data to routers
"""
from sqlalchemy.orm import Session
from repositories.credit_limit_request_repository import CreditLimitRequestRepository
from repositories.shop_repository import ShopRepository
from repositories.order_booker_repository import OrderBookerRepository
from repositories.delivery_man_repository import DeliveryManRepository
from repositories.distributor_repository import DistributorRepository
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime


class CreditLimitRequestService:
    """Service for Credit Limit Request business logic."""
    
    @staticmethod
    def create_request(db: Session, shop_id: int, requested_by_role: str, 
                      requested_by_id: int, requested_credit_limit: float,
                      remarks: str = None) -> Dict:
        """
        Create a credit limit request for an existing shop.
        
        FLOW:
        1. Validates shop exists
        2. Validates requester exists (order_booker or delivery_man)
        3. Gets current credit limit from shop
        4. Creates credit limit request with status="pending"
        5. Returns request data
        
        Args:
            db: Database session
            shop_id: Shop ID
            requested_by_role: "order_booker" or "delivery_man"
            requested_by_id: ID of requester
            requested_credit_limit: New credit limit requested
            remarks: Optional remarks
        
        Returns:
            Dict: Request data
        """
        # Validate shop exists
        shop = ShopRepository.get_by_id(db, shop_id)
        if not shop:
            raise ValueError("Shop not found")
        
        # Validate requester exists
        if requested_by_role == "order_booker":
            requester = OrderBookerRepository.get_by_id(db, requested_by_id)
            if not requester:
                raise ValueError("Order Booker not found")
        elif requested_by_role == "delivery_man":
            requester = DeliveryManRepository.get_by_id(db, requested_by_id)
            if not requester:
                raise ValueError("Delivery Man not found")
        else:
            raise ValueError("Invalid role. Must be 'order_booker' or 'delivery_man'")
        
        # Get current credit limit
        old_credit_limit = float(shop.credit_limit) if shop.credit_limit else 0
        
        # Create request
        request = CreditLimitRequestRepository.create(
            db=db,
            shop_id=shop_id,
            requested_by_role=requested_by_role,
            requested_by_id=requested_by_id,
            requested_credit_limit=requested_credit_limit,
            old_credit_limit=old_credit_limit,
            remarks=remarks
        )
        
        return {
            "id": request.id,
            "shop_id": request.shop_id,
            "requested_by_role": request.requested_by_role,
            "requested_by_id": request.requested_by_id,
            "old_credit_limit": float(request.old_credit_limit) if request.old_credit_limit else 0,
            "requested_credit_limit": float(request.requested_credit_limit),
            "status": request.status.value if hasattr(request.status, 'value') else str(request.status),
            "remarks": request.remarks,
            "created_at": request.created_at.isoformat() if request.created_at else None
        }
    
    @staticmethod
    def get_pending_requests(db: Session, distributor_id: int = None) -> List[Dict]:
        """
        Get all pending credit limit requests.
        
        FLOW:
        1. Gets all pending requests from repository
        2. Includes shop information
        3. Returns formatted list
        
        Args:
            db: Database session
            distributor_id: Optional distributor ID (currently not used for filtering)
        
        Returns:
            List[Dict]: List of pending requests with shop info
        
        Note: Distributors are not assigned to zones, so distributor_id is not used for filtering.
        All pending requests are returned regardless of distributor.
        """
        requests = CreditLimitRequestRepository.get_pending(db, distributor_id)
        
        result = []
        for req in requests:
            shop = ShopRepository.get_by_id(db, req.shop_id)
            
            # Get requester name based on role
            requested_by_name = None
            if req.requested_by_role == "order_booker":
                requester = OrderBookerRepository.get_by_id(db, req.requested_by_id)
                requested_by_name = requester.name if requester else None
            elif req.requested_by_role == "delivery_man":
                requester = DeliveryManRepository.get_by_id(db, req.requested_by_id)
                requested_by_name = requester.name if requester else None
            
            result.append({
                "id": req.id,
                "shop_id": req.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "shop_owner": shop.owner_name if shop else None,
                "requested_by_role": req.requested_by_role,
                "requested_by_id": req.requested_by_id,
                "requested_by_name": requested_by_name,
                "old_credit_limit": float(req.old_credit_limit) if req.old_credit_limit else 0,
                "requested_credit_limit": float(req.requested_credit_limit),
                "status": req.status.value if hasattr(req.status, 'value') else str(req.status),
                "remarks": req.remarks,
                "created_at": req.created_at.isoformat() if req.created_at else None
            })
        
        return result
    
    @staticmethod
    def update_request(db: Session, request_id: int, requested_credit_limit: float = None,
                      remarks: str = None) -> Dict:
        """
        Update a pending credit limit request (by distributor).
        
        FLOW:
        1. Validates request exists and is pending
        2. Updates requested_credit_limit if provided
        3. Updates remarks if provided
        4. Returns updated request
        
        Args:
            db: Database session
            request_id: Request ID to update
            requested_credit_limit: New credit limit value
            remarks: Updated remarks
        
        Returns:
            Dict: Updated request data
        """
        request = CreditLimitRequestRepository.get_by_id(db, request_id)
        if not request:
            raise ValueError("Credit limit request not found")
        
        from models.credit_limit_request import CreditLimitRequestStatus
        if request.status != CreditLimitRequestStatus.PENDING:
            raise ValueError("Can only update pending requests")
        
        update_data = {}
        if requested_credit_limit is not None:
            update_data["requested_credit_limit"] = Decimal(str(requested_credit_limit))
        if remarks is not None:
            update_data["remarks"] = remarks
        
        updated = CreditLimitRequestRepository.update(db, request_id, **update_data)
        if not updated:
            raise ValueError("Failed to update request")
        
        return {
            "id": updated.id,
            "shop_id": updated.shop_id,
            "requested_credit_limit": float(updated.requested_credit_limit),
            "status": updated.status.value if hasattr(updated.status, 'value') else str(updated.status),
            "remarks": updated.remarks
        }
    
    @staticmethod
    def approve_request(db: Session, request_id: int, distributor_id: int,
                       final_credit_limit: float = None, remarks: str = None) -> Dict:
        """
        Approve a credit limit request.
        
        FLOW:
        1. Validates request exists and is pending
        2. Validates distributor exists
        3. Approves request (sets status, approved_by, approved_at)
        4. Updates shop's credit_limit to final_credit_limit (or requested_credit_limit)
        5. Returns approved request data
        
        Args:
            db: Database session
            request_id: Request ID to approve
            distributor_id: Distributor ID who is approving
            final_credit_limit: Final credit limit (can differ from requested)
            remarks: Optional remarks
        
        Returns:
            Dict: Approved request data
        """
        # Validate request
        request = CreditLimitRequestRepository.get_by_id(db, request_id)
        if not request:
            raise ValueError("Credit limit request not found")
        
        from models.credit_limit_request import CreditLimitRequestStatus
        if request.status != CreditLimitRequestStatus.PENDING:
            raise ValueError("Request is not pending")
        
        # Validate distributor
        distributor = DistributorRepository.get_by_id(db, distributor_id)
        if not distributor:
            raise ValueError("Distributor not found")
        
        # Determine final credit limit
        credit_limit_to_set = final_credit_limit if final_credit_limit is not None else float(request.requested_credit_limit)
        
        # Approve request
        approved = CreditLimitRequestRepository.approve(
            db=db,
            request_id=request_id,
            distributor_id=distributor_id,
            final_credit_limit=credit_limit_to_set,
            remarks=remarks
        )
        
        # Update shop's credit limit
        ShopRepository.update(
            db=db,
            shop_id=request.shop_id,
            credit_limit=Decimal(str(credit_limit_to_set))
        )
        
        # Get shop name for response
        shop = ShopRepository.get_by_id(db, approved.shop_id)
        shop_name = shop.name if shop else None
        
        # Get requester name based on role
        requested_by_name = None
        if approved.requested_by_role == "order_booker":
            requester = OrderBookerRepository.get_by_id(db, approved.requested_by_id)
            requested_by_name = requester.name if requester else None
        elif approved.requested_by_role == "delivery_man":
            requester = DeliveryManRepository.get_by_id(db, approved.requested_by_id)
            requested_by_name = requester.name if requester else None
        
        return {
            "id": approved.id,
            "shop_id": approved.shop_id,
            "shop_name": shop_name,
            "requested_by_role": approved.requested_by_role,
            "requested_by_id": approved.requested_by_id,
            "requested_by_name": requested_by_name,
            "old_credit_limit": float(approved.old_credit_limit) if approved.old_credit_limit else 0,
            "requested_credit_limit": float(approved.requested_credit_limit),
            "status": approved.status.value if hasattr(approved.status, 'value') else str(approved.status),
            "approved_by_distributor": approved.approved_by_distributor,
            "approved_at": approved.approved_at.isoformat() if approved.approved_at else None,
            "remarks": approved.remarks,
            "created_at": approved.created_at.isoformat() if approved.created_at else None
        }
    
    @staticmethod
    def reject_request(db: Session, request_id: int, distributor_id: int,
                     remarks: str = None) -> Dict:
        """
        Reject a credit limit request.
        
        FLOW:
        1. Validates request exists and is pending
        2. Validates distributor exists
        3. Rejects request (sets status, approved_by, approved_at)
        4. Returns rejected request data
        
        Args:
            db: Database session
            request_id: Request ID to reject
            distributor_id: Distributor ID who is rejecting
            remarks: Reason for rejection
        
        Returns:
            Dict: Rejected request data
        """
        # Validate request
        request = CreditLimitRequestRepository.get_by_id(db, request_id)
        if not request:
            raise ValueError("Credit limit request not found")
        
        from models.credit_limit_request import CreditLimitRequestStatus
        if request.status != CreditLimitRequestStatus.PENDING:
            raise ValueError("Request is not pending")
        
        # Validate distributor
        distributor = DistributorRepository.get_by_id(db, distributor_id)
        if not distributor:
            raise ValueError("Distributor not found")
        
        # Reject request
        rejected = CreditLimitRequestRepository.reject(
            db=db,
            request_id=request_id,
            distributor_id=distributor_id,
            remarks=remarks
        )
        
        # Get shop name for response
        shop = ShopRepository.get_by_id(db, rejected.shop_id)
        shop_name = shop.name if shop else None
        
        # Get requester name based on role
        requested_by_name = None
        if rejected.requested_by_role == "order_booker":
            requester = OrderBookerRepository.get_by_id(db, rejected.requested_by_id)
            requested_by_name = requester.name if requester else None
        elif rejected.requested_by_role == "delivery_man":
            requester = DeliveryManRepository.get_by_id(db, rejected.requested_by_id)
            requested_by_name = requester.name if requester else None
        
        return {
            "id": rejected.id,
            "shop_id": rejected.shop_id,
            "shop_name": shop_name,
            "requested_by_role": rejected.requested_by_role,
            "requested_by_id": rejected.requested_by_id,
            "requested_by_name": requested_by_name,
            "old_credit_limit": float(rejected.old_credit_limit) if rejected.old_credit_limit else 0,
            "requested_credit_limit": float(rejected.requested_credit_limit),
            "status": rejected.status.value if hasattr(rejected.status, 'value') else str(rejected.status),
            "approved_by_distributor": rejected.approved_by_distributor,
            "approved_at": rejected.approved_at.isoformat() if rejected.approved_at else None,
            "remarks": rejected.remarks,
            "created_at": rejected.created_at.isoformat() if rejected.created_at else None
        }

