"""
Credit Limit Request Repository
================================
Data access layer for Credit Limit Request operations.

This repository handles all direct database interactions for the CreditLimitRequest model.
It uses SQLAlchemy ORM to perform CRUD operations on the 'credit_limit_requests' table.

ARCHITECTURE:
Router → Service → Repository → Database

This layer:
- Receives database session from Service layer
- Performs SQL queries via SQLAlchemy ORM
- Returns model instances or None
- No business logic (validation, etc.) - that's in Service layer
"""
from sqlalchemy.orm import Session
from sqlalchemy import String, or_, cast
from models.credit_limit_request import CreditLimitRequest, CreditLimitRequestStatus
from models.shop import Shop
from models.order_booker import OrderBooker
from typing import Optional, List


class CreditLimitRequestRepository:
    """
    Repository for Credit Limit Request database operations.
    
    This class contains static methods for all database operations on credit_limit_requests table.
    Each method:
    1. Takes a database session and parameters
    2. Performs SQL query via SQLAlchemy
    3. Returns CreditLimitRequest model instance(s) or None
    """
    
    @staticmethod
    def create(db: Session, shop_id: int, requested_by_role: str, requested_by_id: int,
              requested_credit_limit: float, old_credit_limit: float = None,
              remarks: str = None) -> CreditLimitRequest:
        """
        Create a new credit limit request record in the database.
        
        FLOW:
        1. Creates CreditLimitRequest model instance with provided data
        2. Sets status to "pending" by default
        3. Adds to database session (staged for commit)
        4. Commits transaction (saves to database)
        5. Refreshes instance to get auto-generated ID and timestamps
        6. Returns the created request
        
        Args:
            db: SQLAlchemy database session
            shop_id: Shop ID (foreign key to shops table)
            requested_by_role: Role of requester ("order_booker" or "delivery_man")
            requested_by_id: ID of the requester
            requested_credit_limit: New credit limit being requested
            old_credit_limit: Current credit limit (None for new shops)
            remarks: Optional remarks/notes
        
        Returns:
            CreditLimitRequest: Created request model instance with ID and timestamps
        """
        # Create model instance (maps to credit_limit_requests table)
        request = CreditLimitRequest(
            shop_id=shop_id,
            requested_by_role=requested_by_role,
            requested_by_id=requested_by_id,
            requested_credit_limit=requested_credit_limit,
            old_credit_limit=old_credit_limit,
            remarks=remarks,
            status=CreditLimitRequestStatus.PENDING,  # Default status
            is_active=True  # New requests are active by default
        )
        # Add to session (staged, not yet saved)
        db.add(request)
        # Commit transaction (saves to database)
        db.commit()
        # Refresh to get auto-generated fields (id, created_at)
        db.refresh(request)
        return request
    
    @staticmethod
    def get_by_id(db: Session, request_id: int) -> Optional[CreditLimitRequest]:
        """
        Get a credit limit request by its ID.
        
        FLOW:
        1. Queries credit_limit_requests table
        2. Filters by id = request_id
        3. Returns first match or None
        
        Args:
            db: SQLAlchemy database session
            request_id: Request ID (primary key)
        
        Returns:
            Optional[CreditLimitRequest]: Request instance if found, None otherwise
        """
        # SQL: SELECT * FROM credit_limit_requests WHERE id = request_id LIMIT 1
        return db.query(CreditLimitRequest).filter(CreditLimitRequest.id == request_id).first()
    
    @staticmethod
    def get_by_shop(db: Session, shop_id: int) -> List[CreditLimitRequest]:
        """
        Get all credit limit requests for a specific shop.
        
        FLOW:
        1. Queries credit_limit_requests table
        2. Filters by shop_id = shop_id
        3. Returns list of requests (ordered by created_at desc)
        
        Args:
            db: SQLAlchemy database session
            shop_id: Shop ID (foreign key)
        
        Returns:
            List[CreditLimitRequest]: List of request instances
        """
        # SQL: SELECT * FROM credit_limit_requests WHERE shop_id = shop_id AND deleted_at IS NULL ORDER BY created_at DESC
        # Query with explicit column selection to avoid enum conversion issues
        from sqlalchemy import select, text
        try:
            # Try normal query first
            requests = db.query(CreditLimitRequest).filter(
                CreditLimitRequest.shop_id == shop_id,
                CreditLimitRequest.deleted_at.is_(None)  # Exclude soft-deleted requests
            ).order_by(CreditLimitRequest.created_at.desc()).all()
            
            # Manually handle status conversion to avoid enum issues
            for req in requests:
                try:
                    # Access status to trigger any conversion, catch if it fails
                    _ = req.status
                except Exception:
                    # If enum conversion fails, manually set status as string
                    # Query status directly as string
                    status_result = db.execute(
                        text("SELECT status FROM credit_limit_requests WHERE id = :id"),
                        {"id": req.id}
                    ).scalar()
                    # Set status as enum value based on string
                    if status_result:
                        status_lower = str(status_result).lower()
                        if status_lower == 'approved':
                            req.status = CreditLimitRequestStatus.APPROVED
                        elif status_lower == 'pending':
                            req.status = CreditLimitRequestStatus.PENDING
                        elif status_lower == 'disapproved':
                            req.status = CreditLimitRequestStatus.DISAPPROVED
            return requests
        except Exception as e:
            # If query fails due to enum issues, use raw SQL
            print(f"Warning: Enum conversion issue in get_by_shop, using workaround: {e}")
            # Fallback: query with raw SQL and manually construct objects
            result = db.execute(
                text("""
                    SELECT id, shop_id, requested_by_role, requested_by_id, 
                           requested_credit_limit, old_credit_limit, status, 
                           remarks, approved_by_distributor, approved_at, 
                           created_at, updated_at, deleted_at
                    FROM credit_limit_requests 
                    WHERE shop_id = :shop_id AND deleted_at IS NULL 
                    ORDER BY created_at DESC
                """),
                {"shop_id": shop_id}
            )
            requests = []
            for row in result:
                req = CreditLimitRequest()
                req.id = row[0]
                req.shop_id = row[1]
                req.requested_by_role = row[2]
                req.requested_by_id = row[3]
                req.requested_credit_limit = row[4]
                req.old_credit_limit = row[5]
                # Convert status string to enum
                status_str = str(row[6]).lower()
                if status_str == 'approved':
                    req.status = CreditLimitRequestStatus.APPROVED
                elif status_str == 'pending':
                    req.status = CreditLimitRequestStatus.PENDING
                elif status_str == 'disapproved':
                    req.status = CreditLimitRequestStatus.DISAPPROVED
                req.remarks = row[7]
                req.approved_by_distributor = row[8]
                req.approved_at = row[9]
                req.created_at = row[10]
                req.updated_at = row[11]
                req.deleted_at = row[12]
                requests.append(req)
            return requests
    
    @staticmethod
    def get_pending(db: Session, distributor_id: int = None) -> List[CreditLimitRequest]:
        """
        Get all pending credit limit requests, optionally filtered by distributor.
        OPTIMIZED: Uses JOINs instead of multiple queries for better performance.
        
        FLOW:
        1. Queries credit_limit_requests table with JOINs
        2. Filters by status = "pending"
        3. If distributor_id is provided, filters to only shops belonging to that distributor's order bookers
        4. Returns list of pending requests
        
        Args:
            db: SQLAlchemy database session
            distributor_id: Optional distributor ID - filters requests to shops belonging to this distributor's order bookers
        
        Returns:
            List[CreditLimitRequest]: List of pending request instances
        
        Note: When distributor_id is provided, only returns requests for shops that:
            - Were created by an order booker belonging to this distributor, OR
            - Are assigned to an order booker belonging to this distributor, OR
            - Were verified by this distributor
        """
        # Base query with JOIN to shops for efficient filtering
        query = db.query(CreditLimitRequest).join(
            Shop, CreditLimitRequest.shop_id == Shop.id
        )
        
        # Filter by pending status, active requests, and active shops
        # For distributors: only show active requests (is_active = true)
        query = query.filter(
            cast(CreditLimitRequest.status, String) == "pending",
            CreditLimitRequest.deleted_at.is_(None),  # Exclude soft-deleted requests
            CreditLimitRequest.is_active == True,  # Only active requests for distributors
            Shop.deleted_at.is_(None),
            Shop.is_active == True
        )
        
        # If distributor_id is provided, add JOINs to filter by distributor
        if distributor_id:
            # LEFT JOIN with order_bookers for created_by and assigned_to filtering
            # Use distinct() to avoid duplicate results from multiple JOINs
            query = query.outerjoin(
                OrderBooker,
                or_(
                    (Shop.created_by_order_booker == OrderBooker.id),
                    (Shop.assigned_to_order_booker == OrderBooker.id)
                )
            ).filter(
                or_(
                    # Shop created by or assigned to order booker belonging to this distributor
                    (
                        (OrderBooker.distributor_id == distributor_id) &
                        (OrderBooker.deleted_at.is_(None)) &
                        (OrderBooker.is_active == True)
                    ),
                    # Shop verified by this distributor
                    (Shop.verified_by_distributor == distributor_id)
                )
            ).distinct()
        
        return query.order_by(CreditLimitRequest.created_at.asc()).all()
    
    @staticmethod
    def get_disapproved(db: Session, distributor_id: int = None) -> List[CreditLimitRequest]:
        """
        Get all disapproved credit limit requests, optionally filtered by distributor.
        OPTIMIZED: Uses JOINs instead of multiple queries for better performance.
        
        FLOW:
        1. Queries credit_limit_requests table with JOINs
        2. Filters by status = "disapproved"
        3. If distributor_id is provided, filters to only shops belonging to that distributor's order bookers
        4. Returns list of disapproved requests (including soft-deleted ones)
        
        Args:
            db: SQLAlchemy database session
            distributor_id: Optional distributor ID - filters requests to shops belonging to this distributor's order bookers
        
        Returns:
            List[CreditLimitRequest]: List of disapproved request instances
        
        Note: When distributor_id is provided, only returns requests for shops that:
            - Were created by an order booker belonging to this distributor, OR
            - Are assigned to an order booker belonging to this distributor, OR
            - Were verified by this distributor
        """
        # Base query with JOIN to shops for efficient filtering
        query = db.query(CreditLimitRequest).join(
            Shop, CreditLimitRequest.shop_id == Shop.id
        )
        
        # Filter by disapproved status, active requests, and active shops
        # For distributors: only show active requests (is_active = true)
        # Note: We include soft-deleted requests so they can be shown in the UI
        query = query.filter(
            cast(CreditLimitRequest.status, String) == "disapproved",
            CreditLimitRequest.is_active == True,  # Only active requests for distributors
            Shop.deleted_at.is_(None),
            Shop.is_active == True
        )
        
        # If distributor_id is provided, add JOINs to filter by distributor
        if distributor_id:
            # LEFT JOIN with order_bookers for created_by and assigned_to filtering
            # Use distinct() to avoid duplicate results from multiple JOINs
            query = query.outerjoin(
                OrderBooker,
                or_(
                    (Shop.created_by_order_booker == OrderBooker.id),
                    (Shop.assigned_to_order_booker == OrderBooker.id)
                )
            ).filter(
                or_(
                    # Shop created by or assigned to order booker belonging to this distributor
                    (
                        (OrderBooker.distributor_id == distributor_id) &
                        (OrderBooker.deleted_at.is_(None)) &
                        (OrderBooker.is_active == True)
                    ),
                    # Shop verified by this distributor
                    (Shop.verified_by_distributor == distributor_id)
                )
            ).distinct()
        
        return query.order_by(CreditLimitRequest.created_at.desc()).all()
    
    @staticmethod
    def get_all_by_distributor(db: Session, distributor_id: int, skip: int = 0, limit: int = 50) -> List[CreditLimitRequest]:
        """
        Get all credit limit requests (pending, approved, disapproved) for shops belonging to a distributor.
        OPTIMIZED: Uses JOINs instead of multiple queries for better performance.
        
        FLOW:
        1. Queries credit_limit_requests table with JOINs
        2. Filters to shops belonging to this distributor's order bookers
        3. Returns all statuses (pending, approved, disapproved)
        4. Only returns active requests (is_active = True)
        5. Applies pagination (skip, limit)
        
        Args:
            db: SQLAlchemy database session
            distributor_id: Distributor ID - filters requests to shops belonging to this distributor's order bookers
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (default: 50)
        
        Returns:
            List[CreditLimitRequest]: List of all request instances (pending, approved, disapproved)
        
        Note: Only returns requests for shops that:
            - Were created by an order booker belonging to this distributor, OR
            - Are assigned to an order booker belonging to this distributor, OR
            - Were verified by this distributor
        """
        # Base query with JOIN to shops for efficient filtering
        query = db.query(CreditLimitRequest).join(
            Shop, CreditLimitRequest.shop_id == Shop.id
        )
        
        # Filter by active requests and active shops
        # For distributors: only show active requests (is_active = true)
        query = query.filter(
            CreditLimitRequest.deleted_at.is_(None),  # Exclude soft-deleted requests
            CreditLimitRequest.is_active == True,  # Only active requests for distributors
            Shop.deleted_at.is_(None),
            Shop.is_active == True
        )
        
        # Filter by distributor using JOINs
        query = query.outerjoin(
            OrderBooker,
            or_(
                (Shop.created_by_order_booker == OrderBooker.id),
                (Shop.assigned_to_order_booker == OrderBooker.id)
            )
        ).filter(
            or_(
                # Shop created by or assigned to order booker belonging to this distributor
                (
                    (OrderBooker.distributor_id == distributor_id) &
                    (OrderBooker.deleted_at.is_(None)) &
                    (OrderBooker.is_active == True)
                ),
                # Shop verified by this distributor
                (Shop.verified_by_distributor == distributor_id)
            )
        ).distinct()
        
        # Apply pagination and ordering
        return query.order_by(CreditLimitRequest.created_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, request_id: int, **kwargs) -> Optional[CreditLimitRequest]:
        """
        Update credit limit request fields.
        
        FLOW:
        1. Gets request by ID
        2. Updates specified fields
        3. Commits transaction
        4. Refreshes and returns updated instance
        
        Args:
            db: SQLAlchemy database session
            request_id: Request ID to update
            **kwargs: Fields to update (requested_credit_limit, status, remarks, etc.)
        
        Returns:
            Optional[CreditLimitRequest]: Updated request instance, None if not found
        """
        request = db.query(CreditLimitRequest).filter(CreditLimitRequest.id == request_id).first()
        if not request:
            return None
        
        # Update only provided fields
        # Allow None values to be set explicitly (needed for clearing fields like approved_by_distributor)
        for key, value in kwargs.items():
            if hasattr(request, key):
                setattr(request, key, value)
        
        db.commit()
        db.refresh(request)
        return request
    
    @staticmethod
    def approve(db: Session, request_id: int, distributor_id: int, 
                final_credit_limit: float = None, remarks: str = None) -> Optional[CreditLimitRequest]:
        """
        Approve a credit limit request.
        
        FLOW:
        1. Gets request by ID
        2. Updates status to "approved"
        3. Sets approved_by_distributor and approved_at
        4. Updates requested_credit_limit if final_credit_limit provided
        5. Commits transaction
        
        Args:
            db: SQLAlchemy database session
            request_id: Request ID to approve
            distributor_id: Distributor ID who is approving
            final_credit_limit: Final credit limit (can differ from requested)
            remarks: Optional remarks
        
        Returns:
            Optional[CreditLimitRequest]: Approved request instance, None if not found
        """
        from datetime import datetime
        
        request = db.query(CreditLimitRequest).filter(CreditLimitRequest.id == request_id).first()
        if not request:
            return None
        
        request.status = CreditLimitRequestStatus.APPROVED
        request.approved_by_distributor = distributor_id
        request.approved_at = datetime.utcnow()
        
        if final_credit_limit is not None:
            request.requested_credit_limit = final_credit_limit
        
        if remarks:
            request.remarks = remarks
        
        db.commit()
        db.refresh(request)
        return request
    
    @staticmethod
    def reject(db: Session, request_id: int, distributor_id: int, remarks: str = None) -> Optional[CreditLimitRequest]:
        """
        Reject a credit limit request.
        
        FLOW:
        1. Gets request by ID
        2. Updates status to "disapproved"
        3. Sets approved_by_distributor and approved_at
        4. Sets remarks (reason for disapproval)
        5. Commits transaction
        
        Args:
            db: SQLAlchemy database session
            request_id: Request ID to disapprove
            distributor_id: Distributor ID who is disapproving
            remarks: Reason for disapproval
        
        Returns:
            Optional[CreditLimitRequest]: Disapproved request instance, None if not found
        """
        from datetime import datetime
        
        request = db.query(CreditLimitRequest).filter(CreditLimitRequest.id == request_id).first()
        if not request:
            return None
        
        request.status = CreditLimitRequestStatus.DISAPPROVED
        request.approved_by_distributor = distributor_id
        request.approved_at = datetime.utcnow()
        
        if remarks:
            request.remarks = remarks
        
        db.commit()
        db.refresh(request)
        return request
    
    @staticmethod
    def soft_delete(db: Session, request_id: int) -> Optional[CreditLimitRequest]:
        """
        Soft delete a credit limit request by setting deleted_at timestamp.
        
        FLOW:
        1. Gets request by ID
        2. Sets deleted_at to current timestamp
        3. Commits transaction
        4. Returns soft-deleted request
        
        Args:
            db: SQLAlchemy database session
            request_id: Request ID to soft delete
        
        Returns:
            Optional[CreditLimitRequest]: Soft-deleted request instance, None if not found
        """
        from datetime import datetime
        
        request = db.query(CreditLimitRequest).filter(CreditLimitRequest.id == request_id).first()
        if not request:
            return None
        
        # Soft delete: set deleted_at and mark as inactive
        request.deleted_at = datetime.utcnow()
        request.is_active = False  # Hide from distributors when soft deleted
        
        db.commit()
        db.refresh(request)
        return request
    
    @staticmethod
    def get_by_order_booker(db: Session, order_booker_id: int, include_soft_deleted: bool = True, exclude_approved: bool = True) -> List[CreditLimitRequest]:
        """
        Get all credit limit requests created by a specific order booker.
        
        FLOW:
        1. Queries credit_limit_requests table
        2. Filters by requested_by_role = "order_booker" and requested_by_id = order_booker_id
        3. Optionally includes soft-deleted requests
        4. Optionally excludes APPROVED requests
        5. Returns list of requests (ordered by created_at desc)
        
        Args:
            db: SQLAlchemy database session
            order_booker_id: Order booker ID
            include_soft_deleted: If True, includes soft-deleted requests (default: True)
            exclude_approved: If True, excludes APPROVED requests (default: True)
        
        Returns:
            List[CreditLimitRequest]: List of request instances
        """
        query = db.query(CreditLimitRequest).filter(
            CreditLimitRequest.requested_by_role == "order_booker",
            CreditLimitRequest.requested_by_id == order_booker_id
        )
        
        # Exclude APPROVED requests if requested
        if exclude_approved:
            query = query.filter(
                cast(CreditLimitRequest.status, String) != "approved"
            )
        
        # Include or exclude soft-deleted requests
        if not include_soft_deleted:
            query = query.filter(CreditLimitRequest.deleted_at.is_(None))
        
        return query.order_by(CreditLimitRequest.created_at.desc()).all()

