"""
Order Database Model
====================
SQLAlchemy ORM model for the 'orders' table.

PURPOSE:
Represents an order placed by an Order Booker for a shop during a visit.
Orders contain order items and are assigned to Delivery Men for delivery.

WORKFLOW:
1. Order Booker visits shop and places order
2. Order is created with status="pending"
3. Distributor assigns order to Delivery Man
4. Delivery Man delivers order (status="delivered") or marks as disapproved
5. Payment is collected (linked via payments table)

RELATIONSHIPS:
- Belongs to a Shop (via shop_id foreign key)
- Created by an Order Booker (via order_booker_id foreign key)
- Assigned to a Distributor (via distributor_id foreign key)
- Assigned to a Delivery Man (via delivery_man_id foreign key) - Optional
- Linked to a Visit (via visit_id foreign key) - Optional
- Has Order Items (via order_items.order_id)
- Has Payments (via payments.order_id)

DATABASE TABLE: orders
"""
from sqlalchemy import Column, BigInteger, Numeric, DateTime, ForeignKey, String, Date, Text, Enum, Boolean, TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.sql import func
import enum
from config.database import Base


class OrderStatus(str, enum.Enum):
    """Order status enumeration.
    
    NOTE: Database enum uses UPPERCASE values ('PENDING', 'DELIVERED', 'DISAPPROVED').
    Python enum values match the database exactly.
    """
    PENDING = "PENDING"  # Match database enum (uppercase)
    DELIVERED = "DELIVERED"  # Match database enum (uppercase)
    DISAPPROVED = "DISAPPROVED"  # Match database enum (uppercase)
    
    def __str__(self):
        """Return the enum value when converted to string."""
        return self.value


class OrderStatusEnum(TypeDecorator):
    """TypeDecorator to ensure enum values (lowercase) are used, not enum names (uppercase)."""
    impl = ENUM
    cache_ok = True
    
    def __init__(self):
        # Initialize with explicit lowercase string values to match database
        super().__init__(
            OrderStatus, 
            name='order_status_enum', 
            create_type=False
        )
    
    def load_dialect_impl(self, dialect):
        """Load the dialect-specific implementation."""
        if dialect.name == 'postgresql':
            # For PostgreSQL, use the ENUM type but ensure values are lowercase
            # Cast to the existing enum type in the database
            from sqlalchemy import String, cast
            # Return ENUM but we'll handle conversion in process_bind_param
            return dialect.type_descriptor(
                ENUM(OrderStatus, name='order_status_enum', create_type=False)
            )
        return super().load_dialect_impl(dialect)
    
    def bind_processor(self, dialect):
        """Return a processor that converts enum to uppercase string value (matching database)."""
        def process(value):
            print(f"[DEBUG OrderStatusEnum.bind_processor] Processing value: {value}, type: {type(value)}")
            if value is None:
                return None
            if isinstance(value, OrderStatus):
                result = value.value  # Use enum value (UPPERCASE to match database)
                print(f"[DEBUG OrderStatusEnum.bind_processor] Converting enum {value} to value: '{result}'")
                return result
            result = str(value).upper()  # Convert to uppercase to match database enum
            print(f"[DEBUG OrderStatusEnum.bind_processor] Converting string '{value}' to uppercase: '{result}'")
            return result
        return process
    
    def process_bind_param(self, value, dialect):
        """Convert enum to its value (uppercase string) when binding to database."""
        print(f"[DEBUG OrderStatusEnum.process_bind_param] Received value: {value}, type: {type(value)}")
        if value is None:
            return None
        if isinstance(value, OrderStatus):
            result = value.value  # Use enum value (UPPERCASE to match database)
            print(f"[DEBUG OrderStatusEnum.process_bind_param] Converting enum {value} to value: '{result}'")
            return result
        result = str(value).upper()  # Convert to uppercase to match database enum
        print(f"[DEBUG OrderStatusEnum.process_bind_param] Converting string '{value}' to uppercase: '{result}'")
        return result
    
    def process_result_value(self, value, dialect):
        """Convert database value to enum when loading from database."""
        if value is None:
            return None
        if isinstance(value, OrderStatus):
            return value
        # Convert string to enum - database returns uppercase
        value_upper = str(value).upper()
        if value_upper == 'PENDING':
            return OrderStatus.PENDING
        elif value_upper == 'DELIVERED':
            return OrderStatus.DELIVERED
        elif value_upper == 'DISAPPROVED':
            return OrderStatus.DISAPPROVED
        return OrderStatus.PENDING


class Order(Base):
    """
    Order table model.
    
    Maps to the 'orders' table in PostgreSQL.
    Each record represents an order placed for a shop.
    """
    __tablename__ = "orders"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """
    Primary key: Unique identifier for the order.
    Auto-incremented by database.
    """

    # Foreign Keys
    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=True)
    """
    Foreign key to shops table.
    - Links order to the shop where order was placed
    - Nullable: For flexibility (though typically required)
    - Example: Shop ID 1 = "Ali General Store"
    """

    order_booker_id = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=True)
    """
    Foreign key to order_bookers table.
    - Links order to the order booker who placed it
    - Nullable: For flexibility (though typically required)
    - Example: Order Booker ID 1 = "Ahmed Khan"
    """

    distributor_id = Column(BigInteger, ForeignKey("distributors.id"), nullable=True)
    """
    Foreign key to distributors table.
    - Links order to the distributor (for assignment/approval)
    - Nullable: May be set later during assignment
    - Example: Distributor ID 1 = "Regional Manager"
    """

    delivery_man_id = Column(BigInteger, ForeignKey("delivery_men.id"), nullable=True)
    """
    Foreign key to delivery_men table.
    - Links order to the delivery man assigned to deliver it
    - Nullable: Initially NULL, set when distributor assigns
    - Example: Delivery Man ID 1 = "Hassan Ali"
    """

    visit_id = Column(BigInteger, ForeignKey("shop_visits.id"), nullable=True)
    """
    Foreign key to shop_visits table.
    - Links order to the visit where it was placed
    - Nullable: For orders created outside of visits (rare)
    - Example: Visit ID 1 = "Visit to Ali General Store on 2026-01-07"
    """

    # Financial Information
    total_amount = Column(Numeric(10, 2), nullable=True)
    """
    Final order amount (affects outstanding balance).
    - Calculated from sum of order_items.total_price
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 5000.00 (Rs. 5,000)
    - For normal orders: total_amount = original order amount
    - For subsidy orders: total_amount = discounted amount (after subsidy applied)
    - For payment_before_delivery: total_amount = full order amount
    - Used for credit limit validation and outstanding balance calculation
    """

    # Conditional Order Information
    order_resolution_type = Column(String, nullable=True)
    """
    How order was resolved when credit was insufficient.
    - Values: "normal", "subsidy", "payment_before_delivery"
    - "normal": Order placed normally (credit was sufficient)
    - "subsidy": Subsidy was applied to reduce order amount
    - "payment_before_delivery": Order placed with payment collection required before delivery
    - Nullable: For backward compatibility with existing orders
    """

    subsidy_id = Column(BigInteger, ForeignKey("subsidies.id"), nullable=True)
    """
    Foreign key to subsidies table.
    - Links order to the subsidy applied (if order_resolution_type = "subsidy")
    - Nullable: Only set when subsidy is applied
    - Used to track which subsidy rate was used
    """

    original_amount = Column(Numeric(10, 2), nullable=True)
    """
    Original order amount before subsidy was applied.
    - Only set when order_resolution_type = "subsidy"
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 5000.00 (Rs. 5,000)
    - Used to show original amount vs final amount (total_amount)
    - For subsidy orders: original_amount = before discount, total_amount = after discount
    - For normal orders: original_amount = NULL, total_amount = order amount
    """

    payment_collected_before_delivery = Column(Boolean, default=False, nullable=False)
    """
    Whether payment was collected by delivery man before delivery.
    - Only relevant when order_resolution_type = "payment_before_delivery"
    - Default: FALSE
    - Set to TRUE when delivery man collects payment
    - Used to prevent delivery until payment is collected
    """

    payment_collected_amount = Column(Numeric(10, 2), nullable=True)
    """
    Amount collected by delivery man before delivery.
    - Only set when order_resolution_type = "payment_before_delivery" and payment_collected_before_delivery = TRUE
    - Format: Decimal (10 digits total, 2 decimal places)
    - Example: 5000.00 (Rs. 5,000)
    - Used to track how much was collected before delivery
    """

    payment_collected_at = Column(DateTime(timezone=True), nullable=True)
    """
    Timestamp when payment was collected by delivery man before delivery.
    - Only set when payment_collected_before_delivery = TRUE
    - Timezone-aware (stores UTC)
    - Used for auditing and tracking payment collection
    """

    # Status and Scheduling
    # Use TypeDecorator to ensure lowercase enum values are used
    status = Column(
        OrderStatusEnum(),
        nullable=False,
        default=OrderStatus.PENDING,
        server_default='PENDING'  # Match database enum (uppercase)
    )
    """
    Order status.
    - Values: "pending", "delivered", "disapproved"
    - Default: "pending" when first created
    - "pending": Order placed, awaiting delivery
    - "delivered": Order delivered to shop
    - "disapproved": Order disapproved/rejected
    """

    scheduled_date = Column(Date, nullable=True)
    """
    Scheduled delivery date.
    - Date when order should be delivered
    - Format: DATE (YYYY-MM-DD)
    - Example: 2026-01-10
    - Used for delivery planning
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """
    Timestamp when order was created.
    - Automatically set by database on INSERT
    - Timezone-aware (stores UTC)
    - Used for auditing and sorting
    """

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """
    Timestamp when order was last updated.
    - Automatically updated by database on UPDATE
    - Timezone-aware (stores UTC)
    - Used for tracking modifications
    - Null on initial creation
    """

    # Delivery Proof Information
    # NOTE: GPS coordinates removed from orders table - now stored in shop_visits table
    # delivery_gps_lat = Column(Numeric(10, 8), nullable=True)  # REMOVED - use shop_visits.gps_lat
    # delivery_gps_lng = Column(Numeric(11, 8), nullable=True)  # REMOVED - use shop_visits.gps_lng

    delivery_remarks = Column(Text, nullable=True)
    """
    Remarks/notes added by delivery man when delivering or cancelling order.
    - Free text field for delivery notes
    - Example: "Delivered to shop owner. Payment received."
    - Example: "Cancelled - Shop closed"
    - Used for delivery documentation
    """

    delivery_images = Column(Text, nullable=True)  # Will store JSON array as string
    """
    Delivery proof images (Supabase storage URLs).
    - JSON array of image URLs from Supabase storage bucket "deliveries"
    - Format: JSON string array, e.g., '["https://.../image1.jpg", "https://.../image2.jpg"]'
    - Example: ["https://your-project.supabase.co/storage/v1/object/public/deliveries/order_123_delivery_1.jpg"]
    - Used for delivery verification and proof
    - Images are stored in Supabase storage bucket named "deliveries"
    - Stored as TEXT column containing JSON array string (PostgreSQL TEXT[] can be stored as JSON string)
    """















