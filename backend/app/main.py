from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import engine, Base, get_db
from app import models
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from browser_use_austender_agent import BrowserUseAustenderAgent, AUSTENDER_URL

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tender Scraper API")

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to Tender Scraper API"}

@app.get("/tenders", tags=["Tenders"])
def get_tenders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve a paginated list of tenders."""
    return db.query(models.Tender).offset(skip).limit(limit).all()

@app.get("/tenders/{tender_id}", tags=["Tenders"])
def get_tender(tender_id: int, db: Session = Depends(get_db)):
    """Retrieve a single tender by ID."""
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender

# Request model for scraping
class ScrapeRequest(BaseModel):
    task: Optional[str] = None
    keyword: Optional[str] = "construction"
    category: Optional[str] = None
    pages: Optional[int] = 2
    details: Optional[bool] = False

@app.post("/tenders/scrape/austender", tags=["Scrape"])
async def scrape_austender(
    request: ScrapeRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Agentically browse Austender: either execute a custom task or perform a search."""
    req = request
    agent = BrowserUseAustenderAgent(headless=True)
    await agent.start_browser()
    await agent.navigate_to(AUSTENDER_URL)

    if req.task:
        # Execute the provided custom task
        task_result = await agent.execute_task(req.task, max_steps=10)
        await agent.close()
        return {"task": req.task, "result": task_result}

    # Standard search workflow
    opportunities = await agent.search_opportunities(
        keyword=req.keyword,
        category=req.category,
        max_pages=req.pages
    )
    results = []
    if req.details and opportunities:
        for opp in opportunities[: min(len(opportunities), 5)]:
            details = await agent.get_opportunity_details(
                opportunity_id=opp.get("id"), opportunity_url=opp.get("url")
            )
            if details:
                results.append(details)
                tender = models.Tender(
                    source="austender",
                    title=details.get("title"),
                    published_date=details.get("published_date"),
                    close_date=details.get("close_date"),
                    capital_value=details.get("capital_value"),
                    scope_description=details.get("scope_description"),
                    market_timing=details.get("market_timing"),
                    procurement_panel=details.get("procurement_panel"),
                    source_url=details.get("source_url"),
                    raw_html=details.get("raw_html")
                )
                db.add(tender)
        db.commit()
    await agent.close()
    return {"count": len(results), "results": results}
