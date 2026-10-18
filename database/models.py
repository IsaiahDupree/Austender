from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
from sqlalchemy.sql import func

from config.config import DATABASE_URL

Base = declarative_base()


class Opportunity(Base):
    """Main model for storing opportunity data from all sources."""
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    reference_id = Column(String(100), index=True)  # ID from the original source
    source = Column(String(50), index=True)  # Austender, ANI, ICN, SAM
    url = Column(String(500))
    
    # Financial information
    capital_value = Column(Float)
    capital_value_currency = Column(String(10), default="AUD")
    
    # Timing information
    publish_date = Column(Date, index=True)
    closing_date = Column(Date, index=True)
    start_date = Column(Date)
    estimated_duration = Column(String(100))  # e.g., "6 months", "2 years"
    
    # Categorization
    category = Column(String(100), index=True)
    subcategory = Column(String(100), index=True)
    tags = Column(String(255))  # Comma-separated tags
    
    # Procurement details
    procurement_method = Column(String(100))
    panel_arrangement = Column(Boolean, default=False)
    panel_name = Column(String(200))
    
    # Location information
    location = Column(String(200), index=True)
    region = Column(String(100), index=True)
    
    # Contact information
    contact_name = Column(String(200))
    contact_email = Column(String(200))
    contact_phone = Column(String(50))
    
    # System fields
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    last_scraped = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    attachments = relationship("Attachment", back_populates="opportunity", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Opportunity(id={self.id}, title='{self.title}', source='{self.source}')>"


class Attachment(Base):
    """Model for storing attachments related to opportunities."""
    __tablename__ = "attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    name = Column(String(255))
    file_type = Column(String(50))
    url = Column(String(500))
    size = Column(Integer)  # Size in bytes
    description = Column(Text)
    upload_date = Column(Date)
    
    # Relationships
    opportunity = relationship("Opportunity", back_populates="attachments")
    
    def __repr__(self):
        return f"<Attachment(id={self.id}, name='{self.name}')>"


# Database setup function
def setup_database():
    """Initialize the database and create tables if they don't exist."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    return engine
