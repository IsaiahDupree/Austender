"""
API Main Module

This module provides the FastAPI application for serving opportunity data.
"""

import os
import logging
from typing import List, Optional
from datetime import date, datetime
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sys
import atexit

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Opportunity, Attachment
from scrapers.austender_scraper import AustenderScraper
from utils.document_analyzer import DocumentAnalyzer
from sqlalchemy import create_engine, desc, or_
from sqlalchemy.orm import sessionmaker
from config.config import DATABASE_URL, HOST, PORT, ALLOWED_ORIGINS

# Import notification, subscription, and scraper modules
from utils.notification_coordinator import start_notification_system, stop_notification_system
from utils.scraper_scheduler import start_scraper_scheduler, stop_scraper_scheduler
from api.endpoints import subscriptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api")

# Create FastAPI app
app = FastAPI(
    title="Government Construction Opportunities API",
    description="API for accessing construction opportunities from Austender and other sources",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models for API
class AttachmentModel(BaseModel):
    id: int
    name: Optional[str] = None
    file_type: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    upload_date: Optional[date] = None
    
    class Config:
        from_attributes = True


class OpportunityModel(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    reference_id: Optional[str] = None
    source: str
    url: Optional[str] = None
    
    capital_value: Optional[float] = None
    capital_value_currency: Optional[str] = None
    
    publish_date: Optional[date] = None
    closing_date: Optional[date] = None
    start_date: Optional[date] = None
    estimated_duration: Optional[str] = None
    
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: Optional[str] = None
    
    procurement_method: Optional[str] = None
    panel_arrangement: Optional[bool] = None
    panel_name: Optional[str] = None
    
    location: Optional[str] = None
    region: Optional[str] = None
    
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    
    attachments: List[AttachmentModel] = []
    
    class Config:
        from_attributes = True


class RunScrapeRequest(BaseModel):
    sources: List[str] = ["Austender"]
    categories: List[str] = ["construction"]
    locations: List[str] = []
    max_pages: int = 10


# API endpoints
@app.get("/")
async def read_root():
    return {"message": "Government Construction Opportunities API"}


@app.get("/opportunities", response_model=List[OpportunityModel])
async def get_opportunities(
    db: Session = Depends(get_db),
    source: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    published_after: Optional[date] = None,
    closing_after: Optional[date] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Get a list of opportunities with optional filtering.
    """
    query = db.query(Opportunity)
    
    # Apply filters if provided
    if source:
        query = query.filter(Opportunity.source == source)
    
    if category:
        query = query.filter(Opportunity.category == category)
    
    if location:
        query = query.filter(Opportunity.location.contains(location))
    
    if min_value is not None:
        query = query.filter(Opportunity.capital_value >= min_value)
    
    if max_value is not None:
        query = query.filter(Opportunity.capital_value <= max_value)
    
    if published_after:
        query = query.filter(Opportunity.publish_date >= published_after)
    
    if closing_after:
        query = query.filter(Opportunity.closing_date >= closing_after)
    
    if search:
        query = query.filter(
            or_(
                Opportunity.title.contains(search),
                Opportunity.description.contains(search),
                Opportunity.reference_id.contains(search),
                Opportunity.location.contains(search)
            )
        )
    
    # Order by newest first
    query = query.order_by(desc(Opportunity.created_at))
    
    # Apply pagination
    total = query.count()
    opportunities = query.offset(skip).limit(limit).all()
    
    # Return with pagination metadata
    return opportunities


@app.get("/opportunities/{opportunity_id}", response_model=OpportunityModel)
async def get_opportunity(opportunity_id: int, db: Session = Depends(get_db)):
    """
    Get a specific opportunity by ID.
    """
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    return opportunity


@app.get("/opportunities/reference/{reference_id}", response_model=OpportunityModel)
async def get_opportunity_by_reference(reference_id: str, db: Session = Depends(get_db)):
    """
    Get a specific opportunity by its reference ID.
    """
    opportunity = db.query(Opportunity).filter(Opportunity.reference_id == reference_id).first()
    
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    return opportunity


@app.get("/sources")
async def get_sources(db: Session = Depends(get_db)):
    """
    Get a list of all available opportunity sources.
    """
    sources = db.query(Opportunity.source).distinct().all()
    return {"sources": [source[0] for source in sources]}


@app.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    """
    Get a list of all available categories.
    """
    categories = db.query(Opportunity.category).distinct().all()
    return {"categories": [category[0] for category in categories if category[0]]}


@app.get("/locations")
async def get_locations(db: Session = Depends(get_db)):
    """
    Get a list of all available locations.
    """
    locations = db.query(Opportunity.location).distinct().all()
    return {"locations": [location[0] for location in locations if location[0]]}


@app.post("/scrape")
async def run_scrape(
    request: RunScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger a scraping job in the background.
    """
    def run_austender_scrape():
        scraper = AustenderScraper()
        scraper.run_full_scrape(
            categories=request.categories,
            locations=request.locations or [None],
            max_pages=request.max_pages
        )
    
    # Add the scraping task to background tasks
    if "Austender" in request.sources:
        background_tasks.add_task(run_austender_scrape)
    
    return {"message": "Scraping job started", "sources": request.sources}


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """
    Get statistics about the opportunities in the database.
    """
    total_opportunities = db.query(Opportunity).count()
    sources = db.query(Opportunity.source, db.func.count(Opportunity.id)).group_by(Opportunity.source).all()
    
    # Get average capital value by source
    avg_values = db.query(
        Opportunity.source, 
        db.func.avg(Opportunity.capital_value)
    ).group_by(Opportunity.source).all()
    
    # Get counts by category
    categories = db.query(
        Opportunity.category, 
        db.func.count(Opportunity.id)
    ).filter(Opportunity.category != None).group_by(Opportunity.category).all()
    
    # Get counts by location
    locations = db.query(
        Opportunity.location, 
        db.func.count(Opportunity.id)
    ).filter(Opportunity.location != None).group_by(Opportunity.location).all()
    
    return {
        "total_opportunities": total_opportunities,
        "by_source": {source: count for source, count in sources},
        "avg_values": {source: float(avg) if avg else None for source, avg in avg_values},
        "by_category": {cat: count for cat, count in categories if cat},
        "by_location": {loc: count for loc, count in locations if loc}
    }


# Include the subscription router
app.include_router(subscriptions.router)

# Serve static files (if needed)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Event handlers
@app.on_event("startup")
async def startup_event():
    """
    Initialize services when the application starts.
    """
    logger.info("Initializing application services")
    try:
        # Start notification coordinator - this will schedule notification tasks
        logger.info("Starting notification system")
        start_notification_system()
        logger.info("Notification system started successfully")
        
        # Start scraper scheduler - this will schedule scraper jobs
        logger.info("Starting scraper scheduler")
        start_scraper_scheduler()
        logger.info("Scraper scheduler started successfully")
    except Exception as e:
        logger.error(f"Error starting application services: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up resources when the application shuts down.
    """
    logger.info("Shutting down application services")
    try:
        # Stop notification coordinator
        logger.info("Stopping notification system")
        stop_notification_system()
        logger.info("Notification system stopped successfully")
        
        # Stop scraper scheduler
        logger.info("Stopping scraper scheduler")
        stop_scraper_scheduler()
        logger.info("Scraper scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping application services: {str(e)}")

# Register shutdown handler for clean exit
def cleanup():
    logger.info("Application exiting, performing cleanup")
    # Any additional cleanup can go here

atexit.register(cleanup)

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
