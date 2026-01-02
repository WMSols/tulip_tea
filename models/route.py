"""
Route database model.
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from config.database import Base


class Route(Base):
    """Route table model."""
    __tablename__ = "routes"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    order_booker_id = Column(BigInteger, ForeignKey("order_bookers.id"), nullable=True)
    created_by_distributor = Column(BigInteger, ForeignKey("distributors.id"), nullable=True)
    zone_id = Column(BigInteger, ForeignKey("zones.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

