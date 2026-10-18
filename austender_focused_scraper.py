#!/usr/bin/env python
"""
Austender Focused Scraper

This specialized script is designed to handle the specific structure of
the Austender website, focusing solely on extracting construction-related 
tenders without requiring manual intervention.
"""

import os
import sys
import json
import time
import random
import logging
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, quote

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/austender_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("austender_scraper")

# Setup directories
Path("logs").mkdir(exist_ok=True)
Path("screenshots").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)

# Try to import database modules
try:
    from opportunity_finder import OpportunityDatabase
except ImportError as e:
    logger.error(f"Database module import error: {str(e)}")
    # Create a simple fallback database class if the main one is not available
    class OpportunityDatabase:
        def __init__(self):
            self.db_file = "data/opportunities.json"
            self._ensure_db_file()
            
        def _ensure_db_file(self):
            if not os.path.exists(self.db_file):
                with open(self.db_file, "w") as f:
                    json.dump([], f)
                    
        def add_opportunity(self, opportunity):
            opportunities = self._load_opportunities()
            
            # Check if opportunity already exists
            for existing in opportunities:
                if existing.get("url") == opportunity.get("url"):
                    return -1  # Already exists
            
            # Add new opportunity with ID
            opportunity_id = len(opportunities) + 1
            opportunity["id"] = opportunity_id
            opportunities.append(opportunity)
            
            # Save back to file
            self._save_opportunities(opportunities)
            return opportunity_id
            
        def _load_opportunities(self):
            with open(self.db_file, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
                    
        def _save_opportunities(self, opportunities):
            with open(self.db_file, "w") as f:
                json.dump(opportunities, f, indent=2)

class AustenderFocusedScraper:
    """Specialized scraper for Austender focused on construction opportunities."""
    
    # Base URLs and endpoints
    BASE_URL = "https://www.tenders.gov.au"
    SEARCH_ENDPOINT = "/Search/KeywordSearch"
    
    # Standard search parameters for construction tenders
    DEFAULT_SEARCH_PARAMS = {
        "keyword": "construction",
        "type": "ATM",  # Approach to Market
        "dateType": "ClosingDate"
    }
    
    def __init__(self, headless: bool = False, debug: bool = False):
        """
        Initialize the Austender scraper.
        
        Args:
            headless: Whether to run browser in headless mode
            debug: Whether to enable debug mode
        """
        self.headless = headless
        self.debug = debug
        self.opportunity_db = OpportunityDatabase()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Set up logging level
        if debug:
            logger.setLevel(logging.DEBUG)
            
    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_browser()
        
    def build_search_url(self, params: Dict[str, str] = None) -> str:
        """Build the complete search URL with parameters."""
        if params is None:
            params = self.DEFAULT_SEARCH_PARAMS
            
        # Convert params to URL query string
        query_parts = []
        for key, value in params.items():
            query_parts.append(f"{quote(key)}={quote(value)}")
        
        query_string = "&".join(query_parts)
        
        return f"{self.BASE_URL}{self.SEARCH_ENDPOINT}?{query_string}"
        
    def start_browser(self):
        """Start the Playwright browser with advanced anti-detection measures."""
        logger.info("Starting browser with anti-detection configuration")
        self.playwright = sync_playwright().start()
        
        # Anti-detection browser arguments
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
        ]
        
        # Launch browser with optimal settings for avoiding detection
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )
        
        # Create browser context with realistic fingerprinting
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-AU",
            timezone_id="Australia/Sydney",
            permissions=["geolocation"],
            geolocation={"latitude": -35.2809, "longitude": 149.1300},  # Canberra, Australia
            color_scheme="no-preference",
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            accept_downloads=True
        )
        
        # Add anti-fingerprinting script
        self.context.add_init_script("""
            // Override fingerprinting APIs
            const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                // Spoof renderer info to match a common configuration
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel(R) HD Graphics';
                }
                return originalGetParameter.apply(this, arguments);
            };
            
            // Modify navigator properties to appear as a regular user
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            
            // Hide automation flags
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return [
                        {
                            0: {type: "application/pdf"},
                            name: "PDF Viewer",
                            filename: "internal-pdf-viewer",
                            description: "Portable Document Format"
                        }
                    ];
                }
            });
            
            // Override the Permissions API
            const originalQuery = Permissions.prototype.query;
            Permissions.prototype.query = function(queryObj) {
                return Promise.resolve({
                    state: "granted",
                    onchange: null
                });
            };
        """)
        
        # Create a page with extra timeout
        self.page = self.context.new_page()
        self.page.set_default_timeout(60000)  # 60 seconds timeout
        
        # Add human-like behaviors
        self._add_human_behavior_hooks()
        
        logger.info("Browser started successfully")
        return self.page
        
    def _add_human_behavior_hooks(self):
        """Add hooks for human-like behavior."""
        # Intercept all page navigations to add random delays
        self.page.on("request", lambda request: time.sleep(random.uniform(0.1, 0.5)) 
                    if request.resource_type == "document" else None)
        
        # Add random mouse movements for key actions
        orig_click = self.page.click
        def humanized_click(selector, **kwargs):
            # First move to a random position near the element
            element = self.page.query_selector(selector)
            if element:
                bbox = element.bounding_box()
                if bbox:
                    # Move to a random point near the element first
                    self.page.mouse.move(
                        bbox["x"] + random.uniform(0, bbox["width"]),
                        bbox["y"] + random.uniform(0, bbox["height"])
                    )
                    time.sleep(random.uniform(0.1, 0.3))
            # Then perform the actual click
            return orig_click(selector, **kwargs)
            
        self.page.click = humanized_click
    
    def close_browser(self):
        """Close browser and cleanup resources."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed")
        
    def extract_opportunities_from_search_page(self) -> List[Dict[str, Any]]:
        """
        Extract opportunities from the current search results page.
        
        Returns:
            List of opportunity dictionaries with basic information
        """
        opportunities = []
        
        # Take a screenshot for debugging
        if self.debug:
            screenshot_path = f"screenshots/search_results_{int(time.time())}.png"
            self.page.screenshot(path=screenshot_path)
            logger.debug(f"Saved screenshot to {screenshot_path}")
            
            # Also save the HTML
            html_path = f"logs/search_results_{int(time.time())}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.page.content())
            logger.debug(f"Saved HTML to {html_path}")
            
        # Debug page info
        logger.info(f"Current page title: {self.page.title()}")
        logger.info(f"Current URL: {self.page.url}")
            
        # Check if the results container exists
        search_results = self.page.query_selector(".search-results")
        if not search_results:
            logger.warning("No search results container found")
            return opportunities
            
        # Check for no results message
        no_results_text = search_results.inner_text()
        if "no opportunities found" in no_results_text.lower():
            logger.info("Search explicitly returned no results")
            return opportunities
            
        # Find all opportunity items
        items = search_results.query_selector_all(".opportunity-item")
        logger.info(f"Found {len(items)} opportunity items")
        
        for item in items:
            try:
                # Basic data extraction
                title_elem = item.query_selector("h3 a")
                if not title_elem:
                    continue
                    
                title = title_elem.inner_text().strip()
                url = title_elem.get_attribute("href")
                if url and not url.startswith("http"):
                    url = urljoin(self.BASE_URL, url)
                    
                # Extract ID
                id_elem = item.query_selector(".opportunity-id")
                atm_id = id_elem.inner_text().strip() if id_elem else "Unknown"
                
                # Extract location
                location_elem = item.query_selector(".location")
                location = location_elem.inner_text().strip() if location_elem else None
                
                # Extract dates
                dates_elem = item.query_selector(".dates")
                closing_date = None
                if dates_elem:
                    dates_text = dates_elem.inner_text()
                    if "Closes:" in dates_text:
                        closing_date_part = dates_text.split("Closes:")[1].strip().split(" ")[0]
                        closing_date = self._parse_date(closing_date_part)
                
                # Extract value
                value_elem = item.query_selector(".value")
                value = None
                if value_elem:
                    value_text = value_elem.inner_text().strip()
                    value = self._parse_value(value_text)
                    
                # Create opportunity object
                opportunity = {
                    "title": title,
                    "url": url,
                    "reference_id": atm_id,
                    "location": location,
                    "closing_date": closing_date,
                    "capital_value": value,
                    "source": "austender",
                    "scrape_date": datetime.date.today().isoformat()
                }
                
                opportunities.append(opportunity)
                logger.debug(f"Extracted opportunity: {title}")
                
            except Exception as e:
                logger.error(f"Error extracting opportunity: {str(e)}")
                continue
                
        return opportunities
        
    def has_next_page(self) -> bool:
        """Check if there is a next page of results."""
        next_btn = self.page.query_selector(".pagination .next:not(.disabled)")
        return bool(next_btn)
        
    def go_to_next_page(self) -> bool:
        """
        Navigate to the next page of results.
        
        Returns:
            True if navigation successful, False otherwise
        """
        next_btn = self.page.query_selector(".pagination .next:not(.disabled)")
        if not next_btn:
            logger.info("No next page button found or it's disabled")
            return False
            
        try:
            logger.info("Clicking next page button")
            next_btn.click()
            self.page.wait_for_load_state("networkidle")
            time.sleep(random.uniform(2, 4))  # Wait for page to stabilize
            return True
        except Exception as e:
            logger.error(f"Error navigating to next page: {str(e)}")
            return False
            
    def get_opportunity_details(self, url: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific opportunity.
        
        Args:
            url: URL of the opportunity detail page
            
        Returns:
            Dictionary with detailed opportunity information
        """
        logger.info(f"Getting details for: {url}")
        
        # Basic opportunity with URL
        opportunity = {
            "url": url,
            "source": "austender",
            "scrape_date": datetime.date.today().isoformat()
        }
        
        try:
            # Navigate to opportunity page
            self.page.goto(url, timeout=60000)
            self.page.wait_for_load_state("networkidle")
            time.sleep(random.uniform(1, 3))  # Wait for any dynamic content
            
            # Debug info
            if self.debug:
                screenshot_path = f"screenshots/opportunity_{int(time.time())}.png"
                self.page.screenshot(path=screenshot_path)
                logger.debug(f"Saved opportunity screenshot to {screenshot_path}")
                
                html_path = f"logs/opportunity_{int(time.time())}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(self.page.content())
                logger.debug(f"Saved opportunity HTML to {html_path}")
            
            # Extract details
            # Title
            title_elem = self.page.query_selector("h1")
            if title_elem:
                opportunity["title"] = title_elem.inner_text().strip()
                
            # ATM ID
            id_elem = self.page.query_selector(".atm-id")
            if id_elem:
                opportunity["reference_id"] = id_elem.inner_text().strip()
                
            # Extract fields from the "fields" section
            field_mapping = {
                "field-published-date": "publish_date",
                "field-closing-date": "closing_date",
                "field-location": "location",
                "field-agency": "agency",
                "field-category": "category",
                "field-atm-type": "opportunity_type",
                "field-value-range": "capital_value"
            }
            
            for field_class, field_name in field_mapping.items():
                try:
                    field_elem = self.page.query_selector(f".{field_class} .field-value")
                    if field_elem:
                        field_value = field_elem.inner_text().strip()
                        
                        # Special handling for dates and values
                        if "date" in field_name:
                            field_value = self._parse_date(field_value)
                        elif field_name == "capital_value":
                            field_value = self._parse_value(field_value)
                            
                        opportunity[field_name] = field_value
                except Exception as e:
                    logger.error(f"Error extracting {field_name}: {str(e)}")
                    
            # Description
            description_elem = self.page.query_selector(".description")
            if description_elem:
                opportunity["description"] = description_elem.inner_text().strip()
                
            # Contact info
            contact_fields = {
                "field-contact-name": "contact_name",
                "field-contact-email": "contact_email",
                "field-contact-phone": "contact_phone"
            }
            
            for field_class, field_name in contact_fields.items():
                try:
                    field_elem = self.page.query_selector(f".{field_class} .field-value")
                    if field_elem:
                        opportunity[field_name] = field_elem.inner_text().strip()
                except Exception:
                    pass
                    
            # Attachments
            attachments = []
            attachment_elems = self.page.query_selector_all(".documents-list .document-item")
            
            for elem in attachment_elems:
                try:
                    link_elem = elem.query_selector("a")
                    if link_elem:
                        attachment_url = link_elem.get_attribute("href")
                        attachment_name = link_elem.inner_text().strip()
                        
                        # Make URL absolute if needed
                        if attachment_url and not attachment_url.startswith("http"):
                            attachment_url = urljoin(self.BASE_URL, attachment_url)
                            
                        attachments.append({
                            "name": attachment_name,
                            "url": attachment_url,
                            "upload_date": datetime.date.today().isoformat()
                        })
                except Exception as e:
                    logger.error(f"Error extracting attachment: {str(e)}")
                    
            if attachments:
                opportunity["attachments"] = attachments
                
            logger.info(f"Successfully extracted details for: {opportunity.get('title', 'Unknown')}")
            return opportunity
            
        except Exception as e:
            logger.error(f"Error getting opportunity details: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return opportunity
            
    def search_opportunities(self, category: str = "construction", max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Search for opportunities matching the specified category.
        
        Args:
            category: Search term/category
            max_pages: Maximum pages to scrape
            
        Returns:
            List of opportunity dictionaries
        """
        all_opportunities = []
        
        try:
            # Build search URL
            search_params = self.DEFAULT_SEARCH_PARAMS.copy()
            search_params["keyword"] = category
            search_url = self.build_search_url(search_params)
            
            logger.info(f"Searching with URL: {search_url}")
            
            # Navigate to search page
            self.page.goto(search_url, timeout=60000)
            self.page.wait_for_load_state("networkidle")
            time.sleep(random.uniform(3, 5))  # Wait for dynamic content
            
            # Process results from first page
            page_num = 1
            while page_num <= max_pages:
                logger.info(f"Processing page {page_num}")
                
                # Extract opportunities from current page
                page_opportunities = self.extract_opportunities_from_search_page()
                
                if not page_opportunities:
                    logger.info(f"No opportunities found on page {page_num}")
                    break
                    
                logger.info(f"Found {len(page_opportunities)} opportunities on page {page_num}")
                all_opportunities.extend(page_opportunities)
                
                # Check if there's another page
                if page_num < max_pages and self.has_next_page():
                    if not self.go_to_next_page():
                        logger.warning("Failed to navigate to next page")
                        break
                    page_num += 1
                else:
                    logger.info("No more pages available or reached max pages")
                    break
                    
            logger.info(f"Total opportunities found: {len(all_opportunities)}")
            return all_opportunities
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return all_opportunities
            
    def get_details_for_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get detailed information for a list of opportunities.
        
        Args:
            opportunities: List of basic opportunity dictionaries
            
        Returns:
            List of detailed opportunity dictionaries
        """
        detailed_opportunities = []
        
        for i, opp in enumerate(opportunities, 1):
            if "url" not in opp or not opp["url"]:
                logger.warning(f"Opportunity {i} has no URL, skipping")
                continue
                
            logger.info(f"Getting details for opportunity {i}/{len(opportunities)}: {opp.get('title', 'Unknown')}")
            
            # Get detailed information
            detailed_opp = self.get_opportunity_details(opp["url"])
            detailed_opportunities.append(detailed_opp)
            
            # Be nice to the server
            time.sleep(random.uniform(3, 5))
            
        return detailed_opportunities
        
    def save_opportunities(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        Save opportunities to the database.
        
        Args:
            opportunities: List of opportunities to save
        """
        if not opportunities:
            logger.info("No opportunities to save")
            return
            
        logger.info(f"Saving {len(opportunities)} opportunities to database")
        
        for opportunity in opportunities:
            opportunity_id = self.opportunity_db.add_opportunity(opportunity)
            if opportunity_id > 0:
                logger.info(f"Saved opportunity with ID {opportunity_id}: {opportunity.get('title', 'Unknown')}")
            else:
                logger.info(f"Opportunity already exists: {opportunity.get('title', 'Unknown')}")
                
        logger.info("All opportunities saved to database")
        
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse a date string into ISO format."""
        if not date_str:
            return None
            
        # Clean up string
        date_str = date_str.strip()
        
        # Remove timezone info
        date_str = date_str.split(" AEST")[0].split(" AEDT")[0].strip()
        
        # Try different formats
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d %b %Y",
            "%d %B %Y",
            "%B %d, %Y",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                date_obj = datetime.datetime.strptime(date_str, fmt).date()
                return date_obj.isoformat()
            except ValueError:
                continue
                
        logger.warning(f"Could not parse date: {date_str}")
        return date_str  # Return the original string if we can't parse it
        
    def _parse_value(self, value_str: str) -> Optional[float]:
        """Parse a monetary value into a float."""
        if not value_str:
            return None
            
        # Handle 'not disclosed' cases
        value_str = value_str.lower().strip()
        if "not disclosed" in value_str or "not available" in value_str or "n/a" in value_str:
            return None
            
        # Clean up the string
        value_str = value_str.replace("$", "").replace(",", "").strip()
        
        # Handle ranges (e.g. "$50,000 - $100,000")
        if "-" in value_str:
            parts = value_str.split("-")
            if len(parts) == 2:
                try:
                    # Extract numbers with regex
                    import re
                    first_match = re.search(r"[\d.]+", parts[0].strip())
                    second_match = re.search(r"[\d.]+", parts[1].strip())
                    
                    if first_match and second_match:
                        first = float(first_match.group(0))
                        second = float(second_match.group(0))
                        return (first + second) / 2  # Return the average
                except (ValueError, AttributeError):
                    pass
        
        # Try to extract a single number
        try:
            import re
            match = re.search(r"[\d.]+", value_str)
            if match:
                return float(match.group(0))
        except (ValueError, AttributeError):
            pass
            
        logger.warning(f"Could not parse value: {value_str}")
        return None


def run_scraper(args):
    """Run the scraper with command-line arguments."""
    # Create scraper with user settings
    scraper = AustenderFocusedScraper(
        headless=args.headless,
        debug=args.debug
    )
    
    try:
        with scraper:
            # Search for opportunities
            logger.info(f"Searching for {args.category} opportunities, max {args.pages} pages")
            opportunities = scraper.search_opportunities(
                category=args.category,
                max_pages=args.pages
            )
            
            if not opportunities:
                logger.warning("No opportunities found")
                return
                
            logger.info(f"Found {len(opportunities)} opportunities")
            
            # Print summary
            for i, opp in enumerate(opportunities, 1):
                print(f"\n{'-'*80}")
                print(f"Opportunity {i}/{len(opportunities)}:")
                print(f"{'-'*80}")
                print(f"Title:     {opp.get('title', 'Unknown')}")
                print(f"Reference: {opp.get('reference_id', 'Unknown')}")
                print(f"Location:  {opp.get('location', 'Unknown')}")
                print(f"URL:       {opp.get('url', 'Unknown')}")
                
            # Get details if requested
            if args.details:
                logger.info("Getting detailed information for opportunities")
                detailed_opportunities = scraper.get_details_for_opportunities(opportunities)
                
                # Print detailed summary
                for i, opp in enumerate(detailed_opportunities, 1):
                    print(f"\nDetails for opportunity {i}:")
                    print(f"Title:        {opp.get('title', 'Unknown')}")
                    print(f"Reference ID: {opp.get('reference_id', 'Unknown')}")
                    print(f"Closing Date: {opp.get('closing_date', 'Unknown')}")
                    print(f"Location:     {opp.get('location', 'Unknown')}")
                    print(f"Value:        {opp.get('capital_value', 'Unknown')}")
                    
                opportunities = detailed_opportunities
                
            # Save to database if requested
            if args.save:
                scraper.save_opportunities(opportunities)
                
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def run_scheduled_scraper(args):
    """Run the scraper on a schedule."""
    import schedule
    
    logger.info(f"Starting scheduler to run every {args.interval} hours")
    
    # Define the scheduled job
    def scheduled_job():
        logger.info(f"Running scheduled scrape for category: {args.category}")
        run_scraper(args)
        
    # Schedule job and run immediately once
    schedule.every(args.interval).hours.do(scheduled_job)
    logger.info("Running initial scrape immediately")
    scheduled_job()
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    """Parse arguments and run the scraper."""
    parser = argparse.ArgumentParser(description="Austender Focused Scraper")
    parser.add_argument("--headless", action="store_true", default=False,
                      help="Run in headless mode (default: False)")
    parser.add_argument("--category", default="construction",
                      help="Category to search for (default: construction)")
    parser.add_argument("--pages", type=int, default=3,
                      help="Maximum number of pages to scrape (default: 3)")
    parser.add_argument("--details", action="store_true", default=True,
                      help="Get detailed information for each opportunity (default: True)")
    parser.add_argument("--save", action="store_true", default=True,
                      help="Save opportunities to the database (default: True)")
    parser.add_argument("--scheduler", action="store_true",
                      help="Run the scraper on a schedule")
    parser.add_argument("--interval", type=int, default=12,
                      help="Hours between scheduled runs (default: 12)")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug mode with extra logging and screenshots")
                      
    args = parser.parse_args()
    
    # Run in scheduler mode if requested
    if args.scheduler:
        run_scheduled_scraper(args)
    else:
        run_scraper(args)


if __name__ == "__main__":
    main()
