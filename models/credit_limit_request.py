"""
Credit Limit Request Database Model
===================================
SQLAlchemy ORM model for the 'credit_limit_requests' table.

PURPOSE:
Tracks requests for credit limit changes (increase/decrease) for shops.
Order Bookers can request credit limit changes, and Distributors review and approve/reject them.

WORKFLOW:
1. Order Booker registers new shop with credit limit → Creates request
2. Order Booker requests credit limit change for existing shop → Creates request
3. Request status: "pending" → "approved" or "disapproved"
4. Distributor reviews, can edit credit limit value, and approves/disapproves
5. On approval, shop's credit_limit is updated

RELATIONSHIPS:
- Belongs to a Shop (via shop_id foreign key)
- Requested by Order Booker or Delivery Man (via requested_by_role + requested_by_id)
- Reviewed by Distributor (via approved_by_distributor foreign key)

STATUS VALUES:
- "pending" - Awaiting distributor review
- "approved" - Distributor approved, credit limit updated
- "disapproved" - Distributor disapproved/rejected the request

DATABASE TABLE: credit_limit_requests
"""
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, ForeignKey, Enum, TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.sql import func
import enum
from config.database import Base


class CreditLimitRequestStatus(str, enum.Enum):
    """Credit limit request status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    DISAPPROVED = "disapproved"
    
    def __str__(self):
        """Return the enum value when converted to string."""
        return self.value


class CreditLimitRequestStatusEnum(TypeDecorator):
    """TypeDecorator to ensure enum values (lowercase) are used, not enum names (uppercase)."""
    # Use String as base since database stores lowercase but enum type expects uppercase
    impl = String(50)
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        """Load the dialect-specific implementation."""
        if dialect.name == 'postgresql':
            # Use String type instead of ENUM to avoid mismatch between enum definition (uppercase)
            # and actual database values (lowercase). We handle conversion in process_bind_param/process_result_value.
            from sqlalchemy import String
            return dialect.type_descriptor(String(50))
        return super().load_dialect_impl(dialect)
    
    def bind_processor(self, dialect):
        """Return a processor that converts enum to lowercase string value (matching database)."""
        def process(value):
            if value is None:
                return None
            if isinstance(value, CreditLimitRequestStatus):
                # Use enum value (lowercase to match database)
                return value.value
            # Convert to lowercase to match database enum
            return str(value).lower()
        return process
    
    def process_bind_param(self, value, dialect):
        """Convert enum to lowercase string value when binding to database."""
        if value is None:
            return None
        if isinstance(value, CreditLimitRequestStatus):
            # Use the enum value (lowercase string), not the enum name
            return value.value
        if isinstance(value, str):
            # Already a string, ensure it's lowercase
            return value.lower()
        return str(value).lower()
    
    def process_result_value(self, value, dialect):
        """Convert database value back to enum."""
        if value is None:
            return None
        if isinstance(value, str):
            # Convert lowercase string from DB to enum
            try:
                return CreditLimitRequestStatus(value.lower())
            except ValueError:
                # If value doesn't match enum, return as-is (shouldn't happen)
                return value
        return value


class CreditLimitRequest(Base):
    """
    Credit Limit Request table model.
    
    Maps to the 'credit_limit_requests' table in PostgreSQL.
    Each record represents a request to change a shop's credit limit.
    """
    __tablename__ = "credit_limit_requests"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the credit limit request.
    Auto-incremented by database.
    """

    # Relationships
    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=False)
    """
    Foreign key to shops table.
    - Required: Every request must be for a specific shop
    - Links request to the shop whose credit limit is being changed
    - Used for filtering requests by shop
    """

    approved_by_distributor = Column(BigInteger, ForeignKey("distributors.id"), nullable=True)
    """
    Foreign key to distributors table.
    - Links request to the distributor who approved/rejected it
    - Nullable: Set when distributor reviews the request
    - Used for tracking who approved/rejected the request
    """

    # Request Information
    requested_by_role = Column(String, nullable=False)
    """
    Role of the user who made the request.
    - Required field
    - Values: "order_booker" or "delivery_man"
    - Used with requested_by_id to identify the requester
    - Example: "order_booker"
    """

    requested_by_id = Column(BigInteger, nullable=False)
    """
    ID of the user who made the request.
    - Required field
    - References the ID in the table specified by requested_by_role
    - Example: If requested_by_role="order_booker", this is order_bookers.id
    - Used to track who requested the credit limit change
    """

    # Credit Limit Information
    old_credit_limit = Column(Numeric(10, 2), nullable=True)
    """
    Shop's current credit limit before the request.
    - Nullable: For new shops, there's no old limit
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 50000.00 (Rs. 50,000)
    - Used to show what the limit was before the change
    """

    requested_credit_limit = Column(Numeric(10, 2), nullable=False)
    """
    The new credit limit being requested.
    - Required field
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 75000.00 (Rs. 75,000)
    - This is what the requester wants the credit limit to be
    - Distributor can edit this value before approving
    """

    # Status and Review
    status = Column(
        CreditLimitRequestStatusEnum(),
        nullable=False,
        default=CreditLimitRequestStatus.PENDING,
        server_default='pending'
    )
    """
    Request status.
    - Values: "pending", "approved", "disapproved"
    - Default: "pending" when created
    - "pending": Awaiting distributor review
    - "approved": Distributor approved, shop credit_limit updated
    - "disapproved": Distributor disapproved/rejected the request
    """

    remarks = Column(String, nullable=True)
    """
    Additional notes or comments about the request.
    - Optional field
    - Can be added by requester or distributor
    - Used for explaining the reason for request or rejection
    - Example: "Shop has good payment history, requesting increase"
    """

    # Timestamps
    approved_at = Column(DateTime(timezone=True), nullable=True)
    """
    Timestamp when distributor approved/rejected the request.
    - Nullable: Set when distributor approves/rejects
    - Timezone-aware (stores UTC)
    - Used for tracking when decision was made
    """

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when request was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for sorting and filtering requests
    """

    # Soft Delete
    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """
    Soft delete timestamp.
    - When set, request is considered deleted but data is preserved for audit
    - NULL = active record
    - Used for soft delete functionality
    - Typically set when associated shop is soft deleted
    """





