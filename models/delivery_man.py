"""
Delivery Man database model.
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from config.database import Base


class DeliveryMan(Base):
    """Delivery Man table model."""
    __tablename__ = "delivery_men"

    id = Column(BigInteger, primary_key=True, index=True)
    distributor_id = Column(BigInteger, ForeignKey("distributors.id"), nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

