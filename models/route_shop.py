"""
Route-Shop relationship model.
"""
from sqlalchemy import Column, BigInteger, Integer, ForeignKey
from config.database import Base


class RouteShop(Base):
    """Route-Shop junction table model."""
    __tablename__ = "route_shops"

    id = Column(BigInteger, primary_key=True, index=True)
    route_id = Column(BigInteger, ForeignKey("routes.id"), nullable=True)
    shop_id = Column(BigInteger, ForeignKey("shops.id"), nullable=True)
    sequence = Column(Integer, nullable=True)

