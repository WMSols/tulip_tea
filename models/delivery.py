"""
Delivery Database Model
=======================
SQLAlchemy ORM model for the 'deliveries' table.

PURPOSE:
Tracks the complete delivery lifecycle from warehouse pickup to shop delivery and returns.
Each delivery is linked to an order and tracks inventory movements.

WORKFLOW:
1. Order assigned to delivery man → Delivery created with status='pending_pickup'
2. Delivery man picks up stock from warehouse → status='picked_up' (inventory deducted)
3. Delivery man reaches shop → status='in_transit' or 'processing'
4. Delivery man delivers to shop → status='delivered' or 'partially_delivered'
5. Delivery man returns unsold stock → status='returned' (inventory added back)

RELATIONSHIPS:
- Belongs to an Order (via order_id foreign key)
- Belongs to a Delivery Man (via delivery_man_id foreign key)
- Belongs to a Warehouse (via warehouse_id foreign key)
- Has Delivery Items (via delivery_items.delivery_id)

DATABASE TABLE: deliveries
"""
from sqlalchemy import Column, BigInteger, Numeric, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func
from config.database import Base


class Delivery(Base):
    """
    Delivery table model.
    
    Maps to the 'deliveries' table in PostgreSQL.
    Each record represents a delivery tracking entry for an order.
    """
    __tablename__ = "deliveries"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    """Primary key: Unique identifier for the delivery."""

    # Foreign Keys
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    """Foreign key to orders table. Links delivery to the order being delivered."""

    delivery_man_id = Column(BigInteger, ForeignKey("delivery_men.id", ondelete="RESTRICT"), nullable=False)
    """Foreign key to delivery_men table. Delivery man handling this delivery."""

    warehouse_id = Column(BigInteger, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    """Foreign key to warehouses table. Warehouse where stock is picked from."""

    # Status Tracking
    status = Column(String, nullable=False, default='pending_pickup')
    """
    Delivery status.
    - 'pending_pickup': Order assigned, waiting for warehouse pickup
    - 'picked_up': Stock picked up from warehouse (inventory deducted)
    - 'in_transit': On the way to shop
    - 'delivered': Successfully delivered to shop
    - 'partially_delivered': Some items delivered, some returned
    - 'returned': All items returned to warehouse (inventory added back)
    - 'failed': Delivery failed
    """

    # Warehouse Pickup Tracking
    picked_up_at = Column(DateTime(timezone=False), nullable=True)
    """Timestamp when stock was picked up from warehouse."""
    
    pickup_gps_lat = Column(Numeric(11, 8), nullable=True)
    """GPS latitude where stock was picked up. Range: -90 to 90."""
    
    pickup_gps_lng = Column(Numeric(12, 8), nullable=True)
    """GPS longitude where stock was picked up. Range: -180 to 180."""

    # Delivery Tracking
    delivered_at = Column(DateTime(timezone=False), nullable=True)
    """Timestamp when order was delivered to shop."""
    
    delivery_gps_lat = Column(Numeric(11, 8), nullable=True)
    """GPS latitude where order was delivered. Range: -90 to 90."""
    
    delivery_gps_lng = Column(Numeric(12, 8), nullable=True)
    """GPS longitude where order was delivered. Range: -180 to 180."""
    
    delivery_remarks = Column(Text, nullable=True)
    """Remarks/notes from delivery man when delivering to shop."""
    
    delivery_images = Column(Text, nullable=True)
    """JSON array of delivery proof image URLs (Supabase storage)."""

    # Return Tracking
    returned_at = Column(DateTime(timezone=False), nullable=True)
    """Timestamp when unsold stock was returned to warehouse."""
    
    return_gps_lat = Column(Numeric(11, 8), nullable=True)
    """GPS latitude where stock was returned. Range: -90 to 90."""
    
    return_gps_lng = Column(Numeric(12, 8), nullable=True)
    """GPS longitude where stock was returned. Range: -180 to 180."""
    
    return_reason = Column(Text, nullable=True)
    """Reason for returning stock (e.g., 'Shop closed', 'Partial delivery')."""

    # Failure Tracking
    failure_reason = Column(Text, nullable=True)
    """Reason if delivery failed."""
    
    failure_gps_lat = Column(Numeric(11, 8), nullable=True)
    """GPS latitude where delivery failed. Range: -90 to 90."""
    
    failure_gps_lng = Column(Numeric(12, 8), nullable=True)
    """GPS longitude where delivery failed. Range: -180 to 180."""

    # Legacy field (for backward compatibility)
    proof_photo = Column(Text, nullable=True)
    """Legacy single photo field. Use delivery_images instead."""

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    """Timestamp when delivery record was created."""
    
    updated_at = Column(DateTime(timezone=False), onupdate=func.now())
    """Timestamp when delivery record was last updated."""
    
    deleted_at = Column(DateTime(timezone=False), nullable=True)
    """Soft delete timestamp. NULL = active delivery."""

