# Stores click logs

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base

class ClickLog(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(String, ForeignKey("links.link_id"), nullable=False)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=False)
    is_bot = Column(Boolean, default=False)
    click_at = Column(DateTime, default=func.now())
    fraud_reason = Column(String)

    link = relationship("TrackingLink", back_populates="clicks")
