"""
Weekly Route Schedule Database Model
=====================================
SQLAlchemy ORM model for the 'weekly_route_schedules' table.

PURPOSE:
Represents a recurring weekly schedule template that assigns routes to order bookers
or delivery men on specific days of the week. This is the template from which
visit tasks are generated.

WORKFLOW:
1. Distributor creates a weekly schedule (e.g., "Order Booker 1 visits Route 5 every Monday")
2. System generates visit_tasks from active schedules
3. Order Booker/Delivery Man sees their scheduled tasks
4. When visit is completed, task is linked to actual shop_visit

RELATIONSHIPS:
- Belongs to a Route (via route_id foreign key)
- Assigned to Order Booker or Delivery Man (via assignee_type + assignee_id)
- Created by Distributor (via created_by_distributor foreign key)
- Has many Visit Tasks (via visit_tasks.weekly_schedule_id)

DATABASE TABLE: weekly_route_schedules
"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.sql import func
from config.database import Base


class WeeklyRouteSchedule(Base):
    """
    Weekly Route Schedule table model.
    
    Maps to the 'weekly_route_schedules' table in PostgreSQL.
    Each schedule represents a recurring weekly assignment.
    """
    __tablename__ = "weekly_route_schedules"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the schedule.
    Auto-incremented by database.
    Used as foreign key in: visit_tasks
    """

    # Generic Assignment (supports both order_booker and delivery_man)
    assignee_type = Column(String(20), nullable=False)
    """
    Type of assignee: 'order_booker' or 'delivery_man'.
    - Required field
    - Used with assignee_id to reference the correct table
    - Allows generic scheduling for both types
    """
    
    assignee_id = Column(BigInteger, nullable=False)
    """
    ID of the assignee (order_booker_id or delivery_man_id).
    - Required field
    - References order_bookers.id or delivery_men.id based on assignee_type
    - Used with assignee_type to identify who is scheduled
    """

    # Route Assignment
    route_id = Column(BigInteger, ForeignKey("routes.id"), nullable=False)
    """
    Foreign key to routes table.
    - Links schedule to the route that should be visited
    - Required field
    - When schedule is active, all shops in this route are scheduled for visit
    """

    # Day of Week
    day_of_week = Column(Integer, nullable=False)
    """
    Day of week when this schedule applies.
    - 0 = Monday
    - 1 = Tuesday
    - 2 = Wednesday
    - 3 = Thursday
    - 4 = Friday
    - 5 = Saturday
    - 6 = Sunday
    - Required field
    """

    # Activation Status
    is_active = Column(Boolean, nullable=False, default=True)
    """
    Activation status.
    - TRUE = active (schedule is used to generate tasks)
    - FALSE = inactive (schedule is suspended, no tasks generated)
    - Default: TRUE
    """

    # Relationships
    created_by_distributor = Column(BigInteger, ForeignKey("distributors.id"), nullable=False)
    """
    Foreign key to distributors table.
    - Links schedule to the distributor who created it
    - Required field
    - Used for filtering schedules by distributor
    - Tracks who created the schedule for auditing
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when schedule record was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and sorting
    """

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """
    Timestamp when schedule record was last updated.
    - Automatically updated by database on UPDATE
    - Timezone-aware (stores UTC)
    - Used for tracking modifications
    - Null on initial creation
    """

    # Soft Delete
    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """
    Soft delete timestamp.
    - When set, schedule is considered deleted but data is preserved
    - NULL = active record
    - Used for soft delete functionality
    """

    # Check Constraints
    __table_args__ = (
        CheckConstraint("assignee_type IN ('order_booker', 'delivery_man')", name="chk_assignee_type"),
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="chk_day_of_week"),
    )

