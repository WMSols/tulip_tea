"""
Shop database model.
"""
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from config.database import Base


class Shop(Base):
    """Shop table model."""
    __tablename__ = "shops"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_name = Column(String)
    owner_phone = Column(String)
    gps_lat = Column(Numeric(10, 8))
    gps_lng = Column(Numeric(11, 8))
    credit_limit = Column(Numeric(10, 2), default=0)
    legacy_balance = Column(Numeric(10, 2), default=0)
    is_registered = Column(Boolean, default=False)
    created_by_order_booker = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=True)
    zone_id = Column(BigInteger, ForeignKey("zones.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

