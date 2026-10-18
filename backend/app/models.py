from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base

class Tender(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    title = Column(String, index=True)
    published_date = Column(DateTime)
    close_date = Column(DateTime)
    capital_value = Column(String)
    scope_description = Column(Text)
    market_timing = Column(String)
    procurement_panel = Column(String)
    source_url = Column(String)
    raw_html = Column(Text)
