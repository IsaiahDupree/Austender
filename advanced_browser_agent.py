#!/usr/bin/env python3
"""
Advanced Austender Browsing Agent
-------------------------------
This script demonstrates sophisticated agentic browsing of the Austender website
using Browser-Use with enhanced anti-detection measures, human-like behavior,
and advanced data extraction capabilities.
"""

import os
import json
import time
import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

# Browser-Use imports
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig, BrowserContextConfig
from browser_use.controller.service import Controller
from browser_use.agent.config import AgentConfig

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
        logging.FileHandler(f"logs/advanced_browser_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("advanced_browser_agent")

# Create directories
os.makedirs("logs", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("data", exist_ok=True)

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42"
]

# Initialize controller for custom functions
controller = Controller()

# Custom models for storing extracted data
class OpportunityDocument(BaseModel):
    """Model for documents associated with opportunities."""
    title: str = Field(description="Document title")
    url: str = Field(description="URL to access the document")
    file_type: str = Field(description="File type (e.g., PDF, DOCX)")
    description: Optional[str] = Field(description="Document description if available")

class OpportunityDetail(BaseModel):
    """Model for detailed opportunity information."""
    id: str = Field(description="Unique identifier for the opportunity")
    title: str = Field(description="Title of the opportunity")
    category: str = Field(description="Category or type of opportunity")
    agency: str = Field(description="Government agency or department")
    location: Optional[str] = Field(description="Location of the project")
    closing_date: str = Field(description="Closing date for submissions")
    publishing_date: Optional[str] = Field(description="Date when the opportunity was published")
    value_amount: Optional[float] = Field(description="Numeric value of the opportunity if available")
    value_currency: Optional[str] = Field(description="Currency of the value (e.g., AUD)")
    description: str = Field(description="Detailed description of the opportunity")
    scope: Optional[str] = Field(description="Project scope information")
    market_timing: Optional[str] = Field(description="Market timing information")
    capital_value: Optional[str] = Field(description="Capital value information")
    status: str = Field(description="Current status of the opportunity")
    contact_name: Optional[str] = Field(description="Contact person name")
    contact_email: Optional[str] = Field(description="Contact email address")
    contact_phone: Optional[str] = Field(description="Contact phone number")
    url: str = Field(description="URL to view the opportunity details")
    documents: Optional[List[OpportunityDocument]] = Field(description="Associated documents")
    panel_data: Optional[Dict] = Field(description="Information about procurement panels")
    tags: Optional[List[str]] = Field(description="Tags or keywords associated with the opportunity")

class OpportunitiesCollection(BaseModel):
    """Collection of opportunity details."""
    opportunities: List[OpportunityDetail] = Field(description="List of detailed opportunities")
    total_found: int = Field(description="Total number of opportunities found")
    search_terms: List[str] = Field(description="Search terms used to find these opportunities")
    source: str = Field(description="Source website (e.g., 'Austender')")
    search_date: str = Field(description="Date when the search was performed")
    filters_applied: Dict = Field(description="Search filters that were applied")

# Register custom functions
@controller.action("Save detailed opportunities", param_model=OpportunitiesCollection)
def save_detailed_opportunities(params: OpportunitiesCollection):
    """Save detailed opportunities to a JSON file and a simple CSV summary."""
    # Save as JSON
    json_filename = f"output/austender_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(params.dict(), f, indent=2, ensure_ascii=False)
    
    # Create a simple CSV for quick viewing
    csv_filename = f"output/austender_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_filename, "w", encoding="utf-8") as f:
        # Write header
        f.write("ID,Title,Agency,Closing Date,Value,Category,Status,URL\n")
        
        # Write data rows
        for opp in params.opportunities:
            value = f"{opp.value_amount} {opp.value_currency}" if opp.value_amount else "Not specified"
            f.write(f"\"{opp.id}\",\"{opp.title.replace('\"', '\"\"')}\",\"{opp.agency.replace('\"', '\"\"')}\",\"{opp.closing_date}\",\"{value}\",\"{opp.category}\",\"{opp.status}\",\"{opp.url}\"\n")
    
    logger.info(f"Saved {params.total_found} detailed opportunities to {json_filename} and {csv_filename}")
    return f"Saved {params.total_found} opportunities to {json_filename} and {csv_filename}"

@controller.action("Take screenshot", param_model=str)
async def take_screenshot(page_description: str):
    """Take a screenshot of the current page."""
    filename = f"screenshots/austender_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    # Note: The actual screenshot is taken by Browser-Use's built-in functionality
    # This function is mainly for logging purposes
    logger.info(f"Taking screenshot of: {page_description}")
    return f"Screenshot saved as {filename}"

@controller.action("Solve CAPTCHA", param_model=Dict)
async def solve_captcha(captcha_info: Dict):
    """Handle CAPTCHA challenges by providing guidance."""
    logger.warning(f"CAPTCHA detected: {captcha_info.get('type', 'unknown')}")
    # In a real implementation, you might integrate with a CAPTCHA solving service
    # For now, we'll just log the challenge
    return "Please solve the CAPTCHA manually. The agent will wait."

async def create_browser_with_anti_detection():
    """Create a browser instance with advanced anti-detection measures."""
    # Select a random user agent
    user_agent = random.choice(USER_AGENTS)
    
    # Create browser config with anti-detection settings
    browser_config = BrowserConfig(
        headless=False,  # Set to True for production
        disable_security=True,
        new_context_config=BrowserContextConfig(
            disable_security=True,
            minimum_wait_page_load_time=1,
            maximum_wait_page_load_time=15,
            browser_window_size={"width": 1920, "height": 1080},
            user_agent=user_agent,
            timezone_id="Australia/Sydney",  # Use Australian timezone to appear local
            locale="en-AU",  # Australian English locale
            geolocation={"latitude": -33.865143, "longitude": 151.209900},  # Sydney
            has_touch=False,
            is_mobile=False,
            color_scheme="light",
        )
    )
    
    # Create the browser instance
    browser = Browser(config=browser_config)
    
    # Add evasions through init scripts
    await browser.new_context.add_init_script("""
        // Override webdriver detection
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        
        // Override other detection properties
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-AU', 'en', 'en-US']
        });
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Add random mouse movements
        function randomMouseMovement() {
            if (Math.random() > 0.7) {
                const event = new MouseEvent('mousemove', {
                    'view': window,
                    'bubbles': true,
                    'cancelable': true,
                    'clientX': Math.random() * window.innerWidth,
                    'clientY': Math.random() * window.innerHeight
                });
                document.dispatchEvent(event);
                
                if (Math.random() > 0.9) {
                    // Occasionally scroll a bit
                    window.scrollBy({
                        top: (Math.random() - 0.5) * 100,
                        behavior: 'smooth'
                    });
                }
            }
            
            setTimeout(randomMouseMovement, Math.random() * 3000 + 1000);
        }
        
        randomMouseMovement();
    """)
    
    return browser

async def browse_austender_with_advanced_features(
    search_terms: List[str] = ["construction"],
    max_results: int = 20,
    detailed_view: bool = True,
    date_range: Optional[Dict] = None
):
    """
    Browse Austender with advanced features and anti-detection measures.
    
    Args:
        search_terms: List of keywords to search for
        max_results: Maximum number of results to retrieve
        detailed_view: Whether to get detailed information for each opportunity
        date_range: Optional date range filter (e.g., {"from": "2025-01-01", "to": "2025-12-31"})
    """
    # Create browser with anti-detection measures
    browser = await create_browser_with_anti_detection()
    
    # Initialize the language model
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
    )
    
    # Create agent configuration
    agent_config = AgentConfig(
        temperature=0.2,
        max_steps=50,
        max_time=3600,  # 1 hour timeout
        instructions="""
        You are an expert web navigation agent specializing in government procurement sites.
        When browsing:
        - Simulate human-like behavior with natural pauses, scrolling, and navigation
        - Avoid clicking too quickly or in patterns
        - Occasionally move the mouse randomly across the page
        - Vary your scrolling speed and patterns
        - When filling forms, add natural typing delays (100-300ms between characters)
        - If you encounter a CAPTCHA, use the 'Solve CAPTCHA' function and wait
        - Take occasional screenshots to document important pages
        
        Focus on extracting complete and accurate information. For construction opportunities,
        pay special attention to scope, market timing, capital value, and procurement panel information.
        
        Be thorough but efficient, and document any challenges encountered.
        """
    )
    
    # Construct the task details
    search_terms_str = ", ".join(search_terms)
    
    # Add date range filter if provided
    date_filter_instructions = ""
    if date_range:
        date_filter_instructions = f"""
        Apply date filters:
        - From: {date_range.get('from', 'earliest')}
        - To: {date_range.get('to', 'latest')}
        """
    
    task = f"""
    Navigate to the Austender website (https://www.tenders.gov.au) and perform a comprehensive search for {search_terms_str} opportunities.
    
    Follow these steps:
    
    1. Go to the Austender homepage at https://www.tenders.gov.au
    
    2. Navigate to the ATM (Approach to Market) search page
    
    3. Configure the search with these parameters:
       - Keywords: {search_terms_str}
       - Show only "Current & Forecast" opportunities
       - Category: Focus on "Construction and Maintenance Services"
       {date_filter_instructions}
    
    4. Browse through the search results and collect detailed information
    
    5. For each opportunity, extract:
       - ATM ID (unique identifier)
       - Title
       - Category
       - Agency
       - Closing date
       - Publishing date
       - Value/Budget information (amount and currency)
       - Location
       - Status
       - Contact details
       - Full description
       
    6. For construction opportunities, also look for:
       - Project scope information
       - Market timing details
       - Capital value data
       - Procurement panel details
       - Associated documents
       
    7. Continue until you've collected data for at least {max_results} opportunities
       or have gone through all available results
    
    8. Use the 'Save detailed opportunities' function to save the collected data
    
    9. Take screenshots of important pages using the 'Take screenshot' function
    
    Approach the website with natural human-like behavior to avoid detection:
    - Add random pauses between actions (1-5 seconds)
    - Scroll naturally through pages
    - Occasionally move the mouse without clicking
    - Avoid rapid or patterned clicking
    """
    
    # Initialize the agent
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        controller=controller,
        config=agent_config,
        validate_output=True,
    )
    
    # Run the agent
    logger.info(f"Starting advanced Austender browsing agent with search terms: {search_terms}")
    history = await agent.run()
    
    # Save browsing history for analysis
    history.save_to_file(f"output/austender_advanced_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    return history

async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Advanced Browser-Use agent for Austender")
    parser.add_argument("--terms", type=str, nargs="+", default=["construction"], 
                      help="Search terms to use")
    parser.add_argument("--max-results", type=int, default=20, 
                      help="Maximum number of results to retrieve")
    parser.add_argument("--headless", action="store_true", 
                      help="Run in headless mode")
    parser.add_argument("--from-date", type=str,
                      help="Start date for filtering (YYYY-MM-DD)")
    parser.add_argument("--to-date", type=str,
                      help="End date for filtering (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Set up date filter if provided
    date_range = None
    if args.from_date or args.to_date:
        date_range = {
            "from": args.from_date if args.from_date else "earliest",
            "to": args.to_date if args.to_date else "latest"
        }
    
    try:
        # Run the advanced browsing agent
        await browse_austender_with_advanced_features(
            search_terms=args.terms,
            max_results=args.max_results,
            date_range=date_range
        )
        logger.info("Advanced browsing completed successfully")
        
    except Exception as e:
        logger.error(f"Error during advanced browsing: {str(e)}")
        raise
    
if __name__ == "__main__":
    asyncio.run(main())
