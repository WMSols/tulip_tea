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
from models.shop import Shop
from models.order_booker import OrderBooker
from models.delivery_man import DeliveryMan
from models.distributor import Distributor
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
        # Validate requested_credit_limit is positive
        if requested_credit_limit is None or requested_credit_limit <= 0:
            raise ValueError("Requested credit limit must be greater than 0")
        
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
        
        # Get requester name based on role
        requested_by_name = None
        if request.requested_by_role == "order_booker":
            requester = OrderBookerRepository.get_by_id(db, request.requested_by_id)
            requested_by_name = requester.name if requester else None
        elif request.requested_by_role == "delivery_man":
            requester = DeliveryManRepository.get_by_id(db, request.requested_by_id)
            requested_by_name = requester.name if requester else None
        
        # Get shop name
        shop = ShopRepository.get_by_id(db, request.shop_id)
        shop_name = shop.name if shop else None
        
        return {
            "id": request.id,
            "shop_id": request.shop_id,
            "shop_name": shop_name,
            "requested_by_role": request.requested_by_role,
            "requested_by_id": request.requested_by_id,
            "requested_by_name": requested_by_name,
            "old_credit_limit": float(request.old_credit_limit) if request.old_credit_limit else 0,
            "requested_credit_limit": float(request.requested_credit_limit),
            "status": request.status.value if hasattr(request.status, 'value') else str(request.status),
            "remarks": request.remarks,
            "created_at": request.created_at.isoformat() if request.created_at else None,
            "deleted_at": request.deleted_at.isoformat() if request.deleted_at else None,
            "is_active": request.is_active if hasattr(request, 'is_active') else True
        }
    
    @staticmethod
    def get_pending_requests(db: Session, distributor_id: int = None, include_disapproved: bool = True) -> List[Dict]:
        """
        Get all pending credit limit requests (and optionally disapproved), optionally filtered by distributor.
        
        FLOW:
        1. Gets all pending requests from repository (filtered by distributor if provided)
        2. If include_disapproved is True, also gets disapproved requests
        3. Batch loads all related entities (shops, order bookers, delivery men, distributors) to avoid N+1 queries
        4. Includes shop information
        5. Returns formatted list
        
        Args:
            db: Database session
            distributor_id: Optional distributor ID - filters requests to shops belonging to this distributor's order bookers
            include_disapproved: If True, also includes disapproved requests (default: True)
        
        Returns:
            List[Dict]: List of pending (and optionally disapproved) requests with shop info
        
        Note: When distributor_id is provided, only returns requests for shops that:
            - Were created by an order booker belonging to this distributor, OR
            - Are assigned to an order booker belonging to this distributor, OR
            - Were verified by this distributor
        """
        requests = CreditLimitRequestRepository.get_pending(db, distributor_id)
        
        # Also get disapproved requests if requested
        if include_disapproved:
            disapproved = CreditLimitRequestRepository.get_disapproved(db, distributor_id)
            requests = list(requests) + list(disapproved)
        
        if not requests:
            return []
        
        # Batch load all related entities to avoid N+1 queries
        # Collect all unique IDs
        shop_ids = set()
        order_booker_ids = set()
        delivery_man_ids = set()
        distributor_ids = set()
        
        for req in requests:
            shop_ids.add(req.shop_id)
            if req.requested_by_role == "order_booker":
                order_booker_ids.add(req.requested_by_id)
            elif req.requested_by_role == "delivery_man":
                delivery_man_ids.add(req.requested_by_id)
            if req.approved_by_distributor:
                distributor_ids.add(req.approved_by_distributor)
        
        # Batch load shops (1 query for all shops)
        shops_map = {}
        if shop_ids:
            shops = db.query(Shop).filter(
                Shop.id.in_(shop_ids),
                Shop.deleted_at.is_(None)
            ).all()
            shops_map = {shop.id: shop for shop in shops}
        
        # Batch load order bookers (1 query for all order bookers)
        order_bookers_map = {}
        if order_booker_ids:
            order_bookers = db.query(OrderBooker).filter(
                OrderBooker.id.in_(order_booker_ids),
                OrderBooker.deleted_at.is_(None)
            ).all()
            order_bookers_map = {ob.id: ob for ob in order_bookers}
        
        # Batch load delivery men (1 query for all delivery men)
        delivery_men_map = {}
        if delivery_man_ids:
            delivery_men = db.query(DeliveryMan).filter(
                DeliveryMan.id.in_(delivery_man_ids),
                DeliveryMan.deleted_at.is_(None)
            ).all()
            delivery_men_map = {dm.id: dm for dm in delivery_men}
        
        # Batch load distributors (1 query for all distributors)
        distributors_map = {}
        if distributor_ids:
            distributors = db.query(Distributor).filter(
                Distributor.id.in_(distributor_ids),
                Distributor.deleted_at.is_(None)
            ).all()
            distributors_map = {d.id: d for d in distributors}
        
        # Build result using lookup maps (no additional queries)
        result = []
        for req in requests:
            shop = shops_map.get(req.shop_id)
            
            # Get requester name from lookup map
            requested_by_name = None
            if req.requested_by_role == "order_booker":
                requester = order_bookers_map.get(req.requested_by_id)
                requested_by_name = requester.name if requester else None
            elif req.requested_by_role == "delivery_man":
                requester = delivery_men_map.get(req.requested_by_id)
                requested_by_name = requester.name if requester else None
            
            # Get distributor name from lookup map
            approved_by_distributor_name = None
            if req.approved_by_distributor:
                distributor = distributors_map.get(req.approved_by_distributor)
                approved_by_distributor_name = distributor.name if distributor else None
            
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
                "approved_by_distributor": req.approved_by_distributor,
                "approved_by_distributor_name": approved_by_distributor_name,
                "approved_at": req.approved_at.isoformat() if req.approved_at else None,
                "remarks": req.remarks,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "deleted_at": req.deleted_at.isoformat() if req.deleted_at else None,
                "is_active": req.is_active if hasattr(req, 'is_active') else True
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
        
        # Get shop name
        shop = ShopRepository.get_by_id(db, updated.shop_id)
        shop_name = shop.name if shop else None
        
        # Get requester name based on role
        requested_by_name = None
        if updated.requested_by_role == "order_booker":
            requester = OrderBookerRepository.get_by_id(db, updated.requested_by_id)
            requested_by_name = requester.name if requester else None
        elif updated.requested_by_role == "delivery_man":
            requester = DeliveryManRepository.get_by_id(db, updated.requested_by_id)
            requested_by_name = requester.name if requester else None
        
        return {
            "id": updated.id,
            "shop_id": updated.shop_id,
            "shop_name": shop_name,
            "requested_by_role": updated.requested_by_role,
            "requested_by_id": updated.requested_by_id,
            "requested_by_name": requested_by_name,
            "old_credit_limit": float(updated.old_credit_limit) if updated.old_credit_limit else 0,
            "requested_credit_limit": float(updated.requested_credit_limit),
            "status": updated.status.value if hasattr(updated.status, 'value') else str(updated.status),
            "remarks": updated.remarks,
            "created_at": updated.created_at.isoformat() if updated.created_at else None,
            "deleted_at": updated.deleted_at.isoformat() if updated.deleted_at else None
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
        
        # Get approved_by_distributor_name
        approved_by_distributor_name = None
        if approved.approved_by_distributor:
            distributor = DistributorRepository.get_by_id(db, approved.approved_by_distributor)
            approved_by_distributor_name = distributor.name if distributor else None
        
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
            "approved_by_distributor_name": approved_by_distributor_name,
            "approved_at": approved.approved_at.isoformat() if approved.approved_at else None,
            "remarks": approved.remarks,
            "created_at": approved.created_at.isoformat() if approved.created_at else None,
            "deleted_at": approved.deleted_at.isoformat() if approved.deleted_at else None
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
        
        # Get approved_by_distributor_name
        approved_by_distributor_name = None
        if rejected.approved_by_distributor:
            distributor = DistributorRepository.get_by_id(db, rejected.approved_by_distributor)
            approved_by_distributor_name = distributor.name if distributor else None
        
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
            "approved_by_distributor_name": approved_by_distributor_name,
            "approved_at": rejected.approved_at.isoformat() if rejected.approved_at else None,
            "remarks": rejected.remarks,
            "created_at": rejected.created_at.isoformat() if rejected.created_at else None,
            "deleted_at": rejected.deleted_at.isoformat() if rejected.deleted_at else None
        }
    
    @staticmethod
    def soft_delete_request(db: Session, request_id: int) -> Dict:
        """
        Soft delete a DISAPPROVED credit limit request.
        
        FLOW:
        1. Validates request exists
        2. Validates request is DISAPPROVED (only DISAPPROVED can be soft deleted)
        3. Soft deletes request (sets deleted_at)
        4. Returns soft-deleted request data
        
        Args:
            db: Database session
            request_id: Request ID to soft delete
        
        Returns:
            Dict: Soft-deleted request data
        
        Raises:
            ValueError: If request not found or not DISAPPROVED
        """
        # Validate request exists
        request = CreditLimitRequestRepository.get_by_id(db, request_id)
        if not request:
            raise ValueError("Credit limit request not found")
        
        # Only DISAPPROVED requests can be soft deleted
        from models.credit_limit_request import CreditLimitRequestStatus
        if request.status != CreditLimitRequestStatus.DISAPPROVED:
            raise ValueError("Only DISAPPROVED credit limit requests can be soft deleted")
        
        # Check if already soft deleted
        if request.deleted_at is not None:
            raise ValueError("Credit limit request is already soft deleted")
        
        # Soft delete the request
        deleted = CreditLimitRequestRepository.soft_delete(db, request_id)
        if not deleted:
            raise ValueError("Failed to soft delete request")
        
        # Get shop name for response
        shop = ShopRepository.get_by_id(db, deleted.shop_id)
        shop_name = shop.name if shop else None
        
        # Get requester name based on role
        requested_by_name = None
        if deleted.requested_by_role == "order_booker":
            requester = OrderBookerRepository.get_by_id(db, deleted.requested_by_id)
            requested_by_name = requester.name if requester else None
        elif deleted.requested_by_role == "delivery_man":
            requester = DeliveryManRepository.get_by_id(db, deleted.requested_by_id)
            requested_by_name = requester.name if requester else None
        
        # Get approved_by_distributor_name
        approved_by_distributor_name = None
        if deleted.approved_by_distributor:
            distributor = DistributorRepository.get_by_id(db, deleted.approved_by_distributor)
            approved_by_distributor_name = distributor.name if distributor else None
        
        return {
            "id": deleted.id,
            "shop_id": deleted.shop_id,
            "shop_name": shop_name,
            "requested_by_role": deleted.requested_by_role,
            "requested_by_id": deleted.requested_by_id,
            "requested_by_name": requested_by_name,
            "old_credit_limit": float(deleted.old_credit_limit) if deleted.old_credit_limit else 0,
            "requested_credit_limit": float(deleted.requested_credit_limit),
            "status": deleted.status.value if hasattr(deleted.status, 'value') else str(deleted.status),
            "approved_by_distributor": deleted.approved_by_distributor,
            "approved_by_distributor_name": approved_by_distributor_name,
            "approved_at": deleted.approved_at.isoformat() if deleted.approved_at else None,
            "remarks": deleted.remarks,
            "created_at": deleted.created_at.isoformat() if deleted.created_at else None,
            "deleted_at": deleted.deleted_at.isoformat() if deleted.deleted_at else None
        }
    
    @staticmethod
    def get_all_requests_by_distributor(db: Session, distributor_id: int, skip: int = 0, limit: int = 50) -> List[Dict]:
        """
        Get all credit limit requests (pending, approved, disapproved) for a distributor.
        
        FLOW:
        1. Gets all requests from repository (filtered by distributor, paginated)
        2. Batch loads all related entities (shops, order bookers, delivery men, distributors) to avoid N+1 queries
        3. Includes shop information
        4. Returns formatted list
        
        Args:
            db: Database session
            distributor_id: Distributor ID
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (default: 50)
        
        Returns:
            List[Dict]: List of all requests (pending, approved, disapproved) with shop info
        """
        requests = CreditLimitRequestRepository.get_all_by_distributor(db, distributor_id, skip, limit)
        
        if not requests:
            return []
        
        # Batch load all related entities to avoid N+1 queries
        # Collect all unique IDs
        shop_ids = set()
        order_booker_ids = set()
        delivery_man_ids = set()
        distributor_ids = set()
        
        for req in requests:
            shop_ids.add(req.shop_id)
            if req.requested_by_role == "order_booker":
                order_booker_ids.add(req.requested_by_id)
            elif req.requested_by_role == "delivery_man":
                delivery_man_ids.add(req.requested_by_id)
            if req.approved_by_distributor:
                distributor_ids.add(req.approved_by_distributor)
        
        # Batch load shops (1 query for all shops)
        shops_map = {}
        if shop_ids:
            shops = db.query(Shop).filter(
                Shop.id.in_(shop_ids),
                Shop.deleted_at.is_(None)
            ).all()
            shops_map = {shop.id: shop for shop in shops}
        
        # Batch load order bookers (1 query for all order bookers)
        order_bookers_map = {}
        if order_booker_ids:
            order_bookers = db.query(OrderBooker).filter(
                OrderBooker.id.in_(order_booker_ids),
                OrderBooker.deleted_at.is_(None)
            ).all()
            order_bookers_map = {ob.id: ob for ob in order_bookers}
        
        # Batch load delivery men (1 query for all delivery men)
        delivery_men_map = {}
        if delivery_man_ids:
            delivery_men = db.query(DeliveryMan).filter(
                DeliveryMan.id.in_(delivery_man_ids),
                DeliveryMan.deleted_at.is_(None)
            ).all()
            delivery_men_map = {dm.id: dm for dm in delivery_men}
        
        # Batch load distributors (1 query for all distributors)
        distributors_map = {}
        if distributor_ids:
            distributors = db.query(Distributor).filter(
                Distributor.id.in_(distributor_ids),
                Distributor.deleted_at.is_(None)
            ).all()
            distributors_map = {d.id: d for d in distributors}
        
        # Build result using lookup maps (no additional queries)
        result = []
        for req in requests:
            shop = shops_map.get(req.shop_id)
            
            # Get requester name from lookup map
            requested_by_name = None
            if req.requested_by_role == "order_booker":
                requester = order_bookers_map.get(req.requested_by_id)
                requested_by_name = requester.name if requester else None
            elif req.requested_by_role == "delivery_man":
                requester = delivery_men_map.get(req.requested_by_id)
                requested_by_name = requester.name if requester else None
            
            # Get distributor name from lookup map
            approved_by_distributor_name = None
            if req.approved_by_distributor:
                distributor = distributors_map.get(req.approved_by_distributor)
                approved_by_distributor_name = distributor.name if distributor else None
            
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
                "approved_by_distributor": req.approved_by_distributor,
                "approved_by_distributor_name": approved_by_distributor_name,
                "approved_at": req.approved_at.isoformat() if req.approved_at else None,
                "remarks": req.remarks,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "deleted_at": req.deleted_at.isoformat() if req.deleted_at else None,
                "is_active": req.is_active if hasattr(req, 'is_active') else True
            })
        
        return result
    
    @staticmethod
    def get_requests_by_order_booker(db: Session, order_booker_id: int, include_soft_deleted: bool = True) -> List[Dict]:
        """
        Get all credit limit requests created by an order booker.
        
        FLOW:
        1. Gets all requests from repository (including soft-deleted if requested, excluding APPROVED)
        2. Batch loads all related entities (shops, distributors) to avoid N+1 queries
        3. Includes shop information
        4. Returns formatted list
        
        Args:
            db: Database session
            order_booker_id: Order booker ID
            include_soft_deleted: If True, includes soft-deleted requests (default: True)
        
        Returns:
            List[Dict]: List of requests with shop info (excluding APPROVED requests)
        """
        requests = CreditLimitRequestRepository.get_by_order_booker(
            db=db,
            order_booker_id=order_booker_id,
            include_soft_deleted=include_soft_deleted,
            exclude_approved=True  # Always exclude APPROVED requests
        )
        
        if not requests:
            return []
        
        # Batch load all related entities to avoid N+1 queries
        shop_ids = set()
        distributor_ids = set()
        
        for req in requests:
            shop_ids.add(req.shop_id)
            if req.approved_by_distributor:
                distributor_ids.add(req.approved_by_distributor)
        
        # Batch load shops (1 query for all shops)
        shops_map = {}
        if shop_ids:
            shops = db.query(Shop).filter(Shop.id.in_(shop_ids)).all()
            shops_map = {shop.id: shop for shop in shops}
        
        # Batch load distributors (1 query for all distributors)
        distributors_map = {}
        if distributor_ids:
            distributors = db.query(Distributor).filter(Distributor.id.in_(distributor_ids)).all()
            distributors_map = {d.id: d for d in distributors}
        
        # Build result using lookup maps (no additional queries)
        result = []
        for req in requests:
            shop = shops_map.get(req.shop_id)
            
            # Get distributor name from lookup map
            approved_by_distributor_name = None
            if req.approved_by_distributor:
                distributor = distributors_map.get(req.approved_by_distributor)
                approved_by_distributor_name = distributor.name if distributor else None
            
            result.append({
                "id": req.id,
                "shop_id": req.shop_id,
                "shop_name": shop.name if shop else "Unknown",
                "shop_owner": shop.owner_name if shop else None,
                "requested_by_role": req.requested_by_role,
                "requested_by_id": req.requested_by_id,
                "old_credit_limit": float(req.old_credit_limit) if req.old_credit_limit else 0,
                "requested_credit_limit": float(req.requested_credit_limit),
                "status": req.status.value if hasattr(req.status, 'value') else str(req.status),
                "approved_by_distributor": req.approved_by_distributor,
                "approved_by_distributor_name": approved_by_distributor_name,
                "approved_at": req.approved_at.isoformat() if req.approved_at else None,
                "remarks": req.remarks,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "deleted_at": req.deleted_at.isoformat() if req.deleted_at else None,
                "is_active": req.is_active if hasattr(req, 'is_active') else True
            })
        
        return result

