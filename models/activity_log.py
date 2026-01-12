"""
Activity Log Database Model
===========================
SQLAlchemy ORM model for the 'activity_logs' table.

PURPOSE:
Tracks all user actions and system operations for audit, compliance, and debugging.

USAGE:
- Automatically logs CREATE, UPDATE, DELETE operations
- Tracks approvals, rejections, and status changes
- Records login/logout events
- Stores before/after values for updates
- Links to any entity type (shop, order, payment, etc.)
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.sql import func
from config.database import Base


class ActivityLog(Base):
    """
    Activity Log table model.
    
    Maps to the 'activity_logs' table in PostgreSQL.
    Universal logging table for all system activities.
    """
    __tablename__ = "activity_logs"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """Primary key: Unique identifier for the log entry."""

    # WHO: User Information
    user_id = Column(BigInteger, nullable=True, index=True)
    """
    ID of the user who performed the action.
    - Can be distributor_id, order_booker_id, or delivery_man_id
    - Nullable for system-generated actions
    """

    user_role = Column(String, nullable=False, index=True)
    """
    Role of the user who performed the action.
    - Values: 'distributor', 'order_booker', 'delivery_man', 'system'
    - Required field
    """

    user_name = Column(String, nullable=True)
    """
    Name of the user (denormalized for quick access).
    - Optional field
    - Stored for performance (avoids joins)
    """

    # WHAT: Action Details
    action_type = Column(String, nullable=False, index=True)
    """
    Type of action performed.
    - Values: 'CREATE', 'UPDATE', 'DELETE', 'APPROVE', 'REJECT', 
              'LOGIN', 'LOGOUT', 'VIEW', 'ASSIGN', 'UNASSIGN', etc.
    - Required field
    """

    entity_type = Column(String, nullable=False, index=True)
    """
    Type of entity affected.
    - Values: 'shop', 'order', 'payment', 'daily_collection', 
              'credit_limit_request', 'route', 'zone', etc.
    - Required field
    """

    entity_id = Column(BigInteger, nullable=True, index=True)
    """
    ID of the affected entity.
    - Nullable for actions that don't target a specific entity
    - Example: LOGIN doesn't have an entity_id
    """

    # WHEN & WHERE
    timestamp = Column(DateTime(timezone=False), server_default=func.now(), nullable=False, index=True)
    """Timestamp when the action occurred. Defaults to current time."""

    ip_address = Column(INET, nullable=True)
    """
    IP address of the client.
    - Optional field
    - Useful for security tracking
    - Format: IPv4 or IPv6
    """

    user_agent = Column(Text, nullable=True)
    """
    User agent string (browser/device info).
    - Optional field
    - Useful for debugging and analytics
    """

    # WHAT CHANGED: For UPDATE operations
    old_values = Column(JSONB, nullable=True)
    """
    Previous state of the entity (for UPDATE operations).
    - JSONB format for flexible storage
    - Example: {"credit_limit": "1000.00", "status": "pending"}
    - Nullable (only for UPDATE operations)
    """

    new_values = Column(JSONB, nullable=True)
    """
    New state of the entity (for CREATE/UPDATE operations).
    - JSONB format for flexible storage
    - Example: {"credit_limit": "2000.00", "status": "approved"}
    - Nullable (only for CREATE/UPDATE operations)
    """

    changes_summary = Column(Text, nullable=True)
    """
    Human-readable summary of changes.
    - Optional field
    - Example: "Credit limit changed from Rs. 1,000 to Rs. 2,000"
    - Useful for quick understanding without parsing JSONB
    """

    # WHY: Context
    reason = Column(Text, nullable=True)
    """
    Reason for the action.
    - Optional field
    - Example: "Customer requested increase", "Payment received"
    """

    notes = Column(Text, nullable=True)
    """
    Additional notes about the action.
    - Optional field
    - Free-form text for any additional context
    """

    # STATUS
    status = Column(String, nullable=False, default='success')
    """
    Status of the action.
    - Values: 'success', 'failure', 'pending'
    - Default: 'success'
    """

    error_message = Column(Text, nullable=True)
    """
    Error message if status is 'failure'.
    - Nullable
    - Only set when status = 'failure'
    """

    # ADDITIONAL CONTEXT
    # Note: Using 'additional_metadata' as Python attribute name because 'metadata' is reserved by SQLAlchemy
    # The database column is still named 'metadata'
    additional_metadata = Column('metadata', JSONB, nullable=True)
    """
    Additional context data in JSONB format.
    - Flexible storage for entity-specific data
    - Example: {"order_items": [...], "collection_amount": "500.00"}
    - Indexed with GIN for efficient queries
    - Database column name: 'metadata'
    """

    __table_args__ = (
        CheckConstraint(
            "user_role IN ('distributor', 'order_booker', 'delivery_man', 'system')",
            name='check_user_role'
        ),
        CheckConstraint(
            "status IN ('success', 'failure', 'pending')",
            name='check_status'
        ),
        Index('idx_activity_logs_user', 'user_id', 'user_role'),
        Index('idx_activity_logs_entity', 'entity_type', 'entity_id'),
        Index('idx_activity_logs_metadata', 'metadata', postgresql_using='gin'),
    )

