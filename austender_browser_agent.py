#!/usr/bin/env python3
"""
Austender Browsing Agent
-----------------------
This script demonstrates how to use Browser-Use to autonomously navigate the Austender
website, search for construction opportunities, and extract relevant information.
"""

import os
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict

# Browser-Use imports
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig, BrowserContextConfig
from browser_use.controller.service import Controller

# Language model
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"austender_browser_use_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("austender_browser_agent")

# Create directories for outputs
os.makedirs("screenshots", exist_ok=True)
os.makedirs("output", exist_ok=True)

# Initialize controller for custom functions
controller = Controller()

# Custom models for storing extracted data
class Opportunity(BaseModel):
    id: str = Field(description="Unique identifier for the opportunity")
    title: str = Field(description="Title of the opportunity")
    category: str = Field(description="Category or type of opportunity")
    agency: str = Field(description="Government agency or department")
    closing_date: str = Field(description="Closing date for submissions")
    value: str = Field(description="Value or budget of the opportunity if available")
    description: str = Field(description="Brief description of the opportunity")
    url: str = Field(description="URL to view the opportunity details")

class Opportunities(BaseModel):
    opportunities: List[Opportunity] = Field(description="List of opportunities found")
    total_found: int = Field(description="Total number of opportunities found")
    search_terms: List[str] = Field(description="Search terms used to find these opportunities")
    source: str = Field(description="Source website (e.g., 'Austender')")

# Register a custom function to save opportunities to a file
@controller.action("Save opportunities", param_model=Opportunities)
def save_opportunities(params: Opportunities):
    """Save the scraped opportunities to a JSON file."""
    filename = f"output/austender_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(params.dict(), f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {params.total_found} opportunities to {filename}")
    return f"Saved {params.total_found} opportunities to {filename}"

async def browse_austender(search_terms: List[str] = ["construction"], max_results: int = 20):
    """
    Browse the Austender website to find and extract opportunities.
    
    Args:
        search_terms: List of keywords to search for
        max_results: Maximum number of results to retrieve
    """
    # Browser configuration with anti-detection measures
    browser_config = BrowserConfig(
        headless=False,  # Set to True for production
        disable_security=True,
        new_context_config=BrowserContextConfig(
            disable_security=True,
            minimum_wait_page_load_time=1,
            maximum_wait_page_load_time=15,
            browser_window_size={
                "width": 1920,
                "height": 1080,
            },
        )
    )
    
    # Initialize the browser
    browser = Browser(config=browser_config)
    
    # Initialize the language model
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
    )
    
    # Construct a detailed task for the agent
    search_terms_str = ", ".join(search_terms)
    task = f"""
    Navigate to the Austender website (https://www.tenders.gov.au) and search for {search_terms_str} opportunities.
    
    Follow these steps carefully:
    1. Go to the Austender homepage at https://www.tenders.gov.au
    2. Navigate to the ATM (Approach to Market) search page
    3. Enter the search terms: {search_terms_str}
    4. Apply filters for "Current & Forecast" to see active opportunities
    5. Browse through the search results and extract details for up to {max_results} opportunities
    6. For each opportunity, collect:
       - The ATM ID (unique identifier)
       - Title
       - Category
       - Agency
       - Closing date
       - Budget/value (if available)
       - A brief description
       - The URL to view more details
    7. When finished, use the 'Save opportunities' function to save all the data
    
    Important notes:
    - Act like a human user by scrolling naturally and pausing between actions
    - If you encounter CAPTCHA or security checks, try to solve them or notify me
    - If pagination exists, go through multiple pages to find enough opportunities
    - Focus only on construction and infrastructure-related opportunities
    - Avoid being detected as a bot by not clicking too quickly or in patterns
    """
    
    # Initialize the agent
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        controller=controller,
        validate_output=True,
    )
    
    # Run the agent
    logger.info(f"Starting Austender browsing agent with search terms: {search_terms}")
    history = await agent.run(max_steps=50)
    
    # Save browsing history for debugging
    history.save_to_file(f"output/austender_browsing_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    return history

async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Browser-Use agent for Austender")
    parser.add_argument("--terms", type=str, nargs="+", default=["construction"], 
                      help="Search terms to use")
    parser.add_argument("--max-results", type=int, default=20, 
                      help="Maximum number of results to retrieve")
    parser.add_argument("--headless", action="store_true", 
                      help="Run in headless mode")
    
    args = parser.parse_args()
    
    try:
        await browse_austender(search_terms=args.terms, max_results=args.max_results)
        logger.info("Browsing completed successfully")
        
    except Exception as e:
        logger.error(f"Error during browsing: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
