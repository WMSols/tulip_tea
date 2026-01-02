"""
Distributor database model.
"""
from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.sql import func
from config.database import Base


class Distributor(Base):
    """Distributor table model."""
    __tablename__ = "distributors"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=False, unique=True, index=True)
    assigned_zone = Column(String)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

