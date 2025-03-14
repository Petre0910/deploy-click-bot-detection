# Database models for tracking links

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from models.base import Base

class TrackingLink(Base):
    __tablename__ = "links"
    
    link_id = Column(String, primary_key=True, nullable=False)
    destination = Column(String, nullable=False)
    utm = Column(String, nullable=False)
    email_id = Column(String, nullable=False)

    clicks = relationship("ClickLog", back_populates="link", cascade="all, delete-orphan")
