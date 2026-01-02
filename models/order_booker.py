"""
Order Booker database model.
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from config.database import Base


class OrderBooker(Base):
    """Order Booker table model."""
    __tablename__ = "order_bookers"

    id = Column(BigInteger, primary_key=True, index=True)
    distributor_id = Column(BigInteger, ForeignKey("distributors.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    zone_id = Column(BigInteger, ForeignKey("zones.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

