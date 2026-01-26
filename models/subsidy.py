"""
Subsidy Database Model
=====================
SQLAlchemy ORM model for the 'subsidies' table.

PURPOSE:
Represents subsidy rates created by Distributors. Order Bookers can apply these
subsidies when shop credit is insufficient to place an order. The subsidy reduces
the order amount so it fits within the shop's available credit limit.

WORKFLOW:
1. Distributor creates subsidy rates (e.g., 5%, 10%, 15%)
2. Order Booker places order for shop
3. If shop credit is insufficient, Order Booker can apply a subsidy
4. System calculates: total_amount = original_amount * (1 - percentage/100)
5. Order is created with discounted amount (fits in credit limit)

RELATIONSHIPS:
- Created by Distributor (via distributor_id foreign key)
- Applied to Orders (via orders.subsidy_id)

EXAMPLES:
- "5% Discount" - 5% off order amount
- "10% Early Payment Discount" - 10% off for early payment
- "15% Loyalty Discount" - 15% off for loyal customers

DATABASE TABLE: subsidies
"""
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from config.database import Base


class Subsidy(Base):
    """
    Subsidy table model.
    
    Maps to the 'subsidies' table in PostgreSQL.
    Each record represents a discount rate that can be applied to orders.
    """
    __tablename__ = "subsidies"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the subsidy.
    Auto-incremented by database.
    Used as foreign key in: orders
    """

    # Relationships
    distributor_id = Column(BigInteger, ForeignKey("distributors.id"), nullable=False)
    """
    Foreign key to distributors table.
    - Required: Every subsidy must belong to a distributor
    - Links subsidy to the distributor who created it
    - Used for filtering subsidies by distributor
    """

    # Basic Information
    name = Column(String, nullable=False)
    """
    Subsidy name.
    - Required field
    - Used for display and identification
    - Examples: "5% Discount", "10% Early Payment Discount", "15% Loyalty Discount"
    - Not unique: Multiple distributors can have subsidies with the same name
    """

    description = Column(String, nullable=True)
    """
    Optional description of the subsidy.
    - Can explain when/why this subsidy should be used
    - Example: "Apply when shop has good payment history"
    - Nullable: Optional field
    """

    # Subsidy Details
    percentage = Column(Numeric(5, 2), nullable=False)
    """
    Discount percentage.
    - Required field
    - Format: Decimal (5 digits total, 2 decimal places)
    - Range: 0.00 to 100.00
    - Example: 10.00 means 10% discount
    - Formula: total_amount = original_amount * (1 - percentage/100)
    - The order's total_amount will contain the discounted amount
    - The order's original_amount will contain the original amount before discount
    - Used to calculate the reduced order amount
    """

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    """
    Activation status.
    - TRUE = active (can be applied to orders)
    - FALSE = inactive (cannot be applied, but historical orders remain valid)
    - Default: TRUE
    - Used for temporarily disabling subsidies without deleting them
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when subsidy was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and sorting
    """

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """
    Timestamp when subsidy was last updated.
    - Automatically updated by database on UPDATE
    - Timezone-aware (stores UTC)
    - Used for tracking modifications
    - Null on initial creation
    """

    # Soft Delete
    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """
    Soft delete timestamp.
    - When set, subsidy is considered deleted but data is preserved for audit
    - NULL = active record
    - Used for soft delete functionality
    - Historical orders with this subsidy remain valid even if deleted
    """

