"""
Visit Task Database Model
==========================
SQLAlchemy ORM model for the 'visit_tasks' table.

PURPOSE:
Represents a specific visit task generated from a weekly_route_schedule.
Each task is for a specific shop on a specific date, assigned to an order booker
or delivery man. When the visit is completed, it links to the actual shop_visit.

WORKFLOW:
1. System generates visit_tasks from active weekly_route_schedules
2. Order Booker/Delivery Man sees their tasks for today/this week
3. When they visit a shop, a shop_visit is created
4. The visit_task is linked to the shop_visit and marked as completed

RELATIONSHIPS:
- Generated from WeeklyRouteSchedule (via weekly_schedule_id foreign key)
- Assigned to Order Booker or Delivery Man (via assignee_type + assignee_id)
- For a specific Shop (via shop_id foreign key)
- On a specific Route (via route_id foreign key)
- Links to actual ShopVisit when completed (via shop_visit_id foreign key)

DATABASE TABLE: visit_tasks
"""
from sqlalchemy import Column, BigInteger, String, Integer, Date, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.sql import func
from config.database import Base


class VisitTask(Base):
    """
    Visit Task table model.
    
    Maps to the 'visit_tasks' table in PostgreSQL.
    Each task represents a specific shop visit assignment for a specific date.
    """
    __tablename__ = "visit_tasks"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the task.
    Auto-incremented by database.
    """

    # Schedule Reference
    weekly_schedule_id = Column(BigInteger, ForeignKey("weekly_route_schedules.id"), nullable=False)
    """
    Foreign key to weekly_route_schedules table.
    - Links task to the schedule that generated it
    - Required field
    - Used for tracking which schedule created this task
    """

    # Generic Assignment (supports both order_booker and delivery_man)
    assignee_type = Column(String(20), nullable=False)
    """
    Type of assignee: 'order_booker' or 'delivery_man'.
    - Required field
    - Used with assignee_id to reference the correct table
    - Duplicated from schedule for query performance
    """
    
    assignee_id = Column(BigInteger, nullable=False)
    """
    ID of the assignee (order_booker_id or delivery_man_id).
    - Required field
    - References order_bookers.id or delivery_men.id based on assignee_type
    - Duplicated from schedule for query performance
    """

    # Route and Shop
    route_id = Column(BigInteger, ForeignKey("routes.id"), nullable=False)
    """
    Foreign key to routes table.
    - Links task to the route
    - Required field
    - Duplicated from schedule for query performance
    """

    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=False)
    """
    Foreign key to shops table.
    - Links task to the specific shop that should be visited
    - Required field
    - Each task is for one specific shop
    """

    # Scheduled Date
    scheduled_date = Column(Date, nullable=False)
    """
    Specific date when this visit is scheduled.
    - Required field
    - Format: DATE (e.g., 2026-02-10)
    - Used for filtering tasks by date
    """

    # Day of Week
    day_of_week = Column(Integer, nullable=False)
    """
    Day of week for this scheduled date.
    - 0 = Monday
    - 1 = Tuesday
    - 2 = Wednesday
    - 3 = Thursday
    - 4 = Friday
    - 5 = Saturday
    - 6 = Sunday
    - Duplicated from schedule for query performance
    """

    # Status
    status = Column(String(20), nullable=False, default='pending')
    """
    Task status.
    - 'pending' = Not yet started
    - 'in_progress' = Currently being worked on
    - 'completed' = Visit completed and linked to shop_visit
    - 'skipped' = Skipped (with reason in notes)
    - 'cancelled' = Cancelled (with reason in notes)
    - Default: 'pending'
    """

    # Completion Link
    shop_visit_id = Column(BigInteger, ForeignKey("shop_visits.id"), nullable=True)
    """
    Foreign key to shop_visits table.
    - Links task to the actual shop_visit when completed
    - NULL = not yet completed
    - Set when order booker/delivery man completes the visit
    - Used for tracking which visit fulfilled this task
    """

    completed_at = Column(DateTime(timezone=True), nullable=True)
    """
    Timestamp when task was marked as completed.
    - NULL = not yet completed
    - Set when status changes to 'completed'
    - Timezone-aware (stores UTC)
    """

    # Notes
    notes = Column(Text, nullable=True)
    """
    Optional notes about the task.
    - Can include skip/cancel reasons
    - Can include visit remarks
    - Free text field
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when task record was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and sorting
    """

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """
    Timestamp when task record was last updated.
    - Automatically updated by database on UPDATE
    - Timezone-aware (stores UTC)
    - Used for tracking modifications
    - Null on initial creation
    """

    # Soft Delete
    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """
    Soft delete timestamp.
    - When set, task is considered deleted but data is preserved
    - NULL = active record
    - Used for soft delete functionality
    """

    # Check Constraints
    __table_args__ = (
        CheckConstraint("assignee_type IN ('order_booker', 'delivery_man')", name="chk_visit_task_assignee_type"),
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="chk_visit_task_day_of_week"),
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'skipped', 'cancelled')", name="chk_visit_task_status"),
    )




