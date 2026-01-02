"""
Zone database model.
"""
from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.sql import func
from config.database import Base


class Zone(Base):
    """Zone table model."""
    __tablename__ = "zones"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

