#!/usr/bin/env python
"""
Direct Austender Scraper

This script directly scrapes construction opportunities from Austender
using Playwright for advanced browser automation to bypass anti-bot measures.
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

from playwright.sync_api import sync_playwright, Page, Browser

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

# Try to import database modules
try:
    from opportunity_finder import OpportunityDatabase
except ImportError as e:
    logger.error(f"Failed to import database modules: {str(e)}")
    print(f"Import Error: {str(e)}")
    print("Make sure opportunity_finder.py is in the current directory")
    
# Default category to search for
DEFAULT_CATEGORY = "construction"
    
class AustenderScraper:
    """Scraper for tenders.gov.au using Playwright for advanced browser control."""
    
    def __init__(self, headless: bool = True, slow_mo: int = 100):
        """
        Initialize the Austender scraper.
        
        Args:
            headless: Whether to run in headless mode
            slow_mo: Milliseconds to slow down browser actions (helps avoid detection)
        """
        self.base_url = "https://www.tenders.gov.au"
        self.search_url = f"{self.base_url}/Search/KeywordSearch"
        self.headless = headless
        self.slow_mo = slow_mo
        self.opportunity_db = OpportunityDatabase()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    def __enter__(self):
        """Initialize Playwright and browser when used as context manager."""
        self.start_browser()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close browser when exiting context."""
        self.close_browser()
        
    def start_browser(self):
        """Start the Playwright browser."""
        logger.info("Starting Playwright browser")
        self.playwright = sync_playwright().start()
        
        # Use Chromium with specific arguments to avoid detection
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-web-security',
                '--disable-features=BlockInsecurePrivateNetworkRequests',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        # Use multiple user agents that rotate
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36 Edg/94.0.992.31"
        ]
        selected_user_agent = random.choice(user_agents)
        logger.info(f"Using user agent: {selected_user_agent}")
        
        # Create a new browser context with specific options to avoid fingerprinting
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=selected_user_agent,
            locale="en-AU",
            timezone_id="Australia/Sydney",
            geolocation={"latitude": -33.865143, "longitude": 151.209900},  # Sydney
            permissions=["geolocation"]
        )
        
        # Add hooks to avoid common fingerprinting techniques
        self.context.add_init_script("""
            // Override the navigator's plugins and mimeTypes
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return {
                        length: 5,
                        item: () => { return null; },
                        namedItem: () => { return null; },
                        refresh: () => {}
                    };
                }
            });
            
            // Override WebGL fingerprinting
            const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(contextType, ...args) {
                const context = getContext.call(this, contextType, ...args);
                if (contextType === "webgl" || contextType === "experimental-webgl") {
                    const getParameter = context.getParameter;
                    context.getParameter = function(parameter) {
                        // Spoof WebGL parameters to randomized values
                        return getParameter.call(this, parameter);
                    };
                }
                return context;
            };
        """)
        
        # Create a new page
        self.page = self.context.new_page()
        
        # Add random timing and movements to seem more human-like
        self.page.set_default_timeout(30000)
        
        return self.page
        
    def close_browser(self):
        """Close the browser and Playwright."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
    def search_opportunities(self, category: str = DEFAULT_CATEGORY, max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Search for opportunities on Austender.
        
        Args:
            category: Category to search for (e.g., construction)
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of opportunities found
        """
        if not self.page:
            self.start_browser()
            
        opportunities = []
        
        try:
            # Navigate directly to the search results page with the query parameters
            # This avoids having to interact with the form
            search_url_with_params = f"{self.search_url}?keyword={category}&type=ATM&dateType=ClosingDate"
            logger.info(f"Navigating directly to search URL: {search_url_with_params}")
            
            # Navigate with increased timeout
            self.page.goto(search_url_with_params, timeout=60000)
            
            # Wait for page to load completely with a longer timeout
            self.page.wait_for_load_state("networkidle", timeout=60000)
            
            # Take a screenshot for debugging
            os.makedirs("screenshots", exist_ok=True)
            self.page.screenshot(path=f"screenshots/search_page_{int(time.time())}.png")
            logger.info("Took screenshot of search page")
            
            # Check if we've been blocked or redirected to a captcha
            page_title = self.page.title()
            page_url = self.page.url
            logger.info(f"Current page title: {page_title}")
            logger.info(f"Current URL: {page_url}")
            
            # Add a longer wait before checking for results
            logger.info("Waiting for page to fully load...")
            time.sleep(random.uniform(5.0, 8.0))
            
            # Always save the page HTML for analysis
            html_content = self.page.content()
            html_file_path = f"logs/page_content_{int(time.time())}.html"
            with open(html_file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Saved page HTML to {html_file_path} for analysis")
            
            # First check if there's a "no results" message
            try:
                no_results_locators = [
                    "text=No opportunities found",
                    "text=No results match your search criteria",
                    "text=No matching records found",
                    ".no-results",
                    "div:has-text('No opportunities')"
                ]
                
                for locator in no_results_locators:
                    try:
                        if self.page.query_selector(locator):
                            logger.info(f"Found 'no results' message: {locator}")
                            logger.info("Legitimately no opportunities match the search criteria")
                            return opportunities  # Return empty list since no opportunities found
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Error checking for no results: {str(e)}")
            
            # Try multiple selectors for the search results container
            selectors_to_try = [
                ".search-results",
                "#searchResults",
                "div[class*='search-results']",
                "div[class*='searchResults']",
                "main",  # Sometimes the results might be in the main content area
                "#main-content"
            ]
            
            results_container = None
            for selector in selectors_to_try:
                try:
                    logger.info(f"Trying to locate results container with selector: {selector}")
                    container = self.page.query_selector(selector)
                    if container:
                        logger.info(f"Found results container with selector: {selector}")
                        results_container = container
                        break
                except Exception as e:
                    logger.warning(f"Selector {selector} not found or error: {str(e)}")
            
            if not results_container:
                logger.error("Could not find any search results container with known selectors")
                return opportunities  # Return empty list since we can't find any results
                
            # Now that we have the container, look for opportunity items inside it
            item_selectors = [
                ".opportunity-item",
                ".result-item",
                "tr:has(a)",  # Often results are in table rows with links
                "div[class*='opportunity']",
                "div[class*='result']",
                "article",  # Sometimes results are in article elements
                ".card"   # Some sites use card-based layouts
            ]
            
            opportunity_elements = []
            for selector in item_selectors:
                try:
                    elements = results_container.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        logger.info(f"Found {len(elements)} opportunity elements with selector: {selector}")
                        opportunity_elements = elements
                        break
                except Exception as e:
                    logger.warning(f"Error finding opportunity elements with selector {selector}: {str(e)}")
            
            # If we still don't have opportunity elements, try a different approach - look for links
            if not opportunity_elements:
                logger.warning("Could not find opportunity elements with standard selectors, trying links approach")
                try:
                    # Look for links that might be opportunity links
                    links = results_container.query_selector_all("a")
                    if links and len(links) > 0:
                        logger.info(f"Found {len(links)} links in results container")
                        
                        # Filter links that might be opportunities (containing /ATM/ or /Search/ or similar patterns)
                        filtered_links = []
                        for link in links:
                            href = link.get_attribute("href")
                            if href and ("/ATM/" in href or "/Search/" in href or "Details" in href):
                                filtered_links.append(link)
                        
                        if filtered_links:
                            logger.info(f"Found {len(filtered_links)} potential opportunity links")
                            # Create custom opportunity elements from links
                            for link in filtered_links:
                                # Get the parent element that contains the whole opportunity
                                parent = link
                                for _ in range(3):  # Go up to 3 levels up to find a container
                                    if parent.get_attribute("class") and ("item" in parent.get_attribute("class") or "result" in parent.get_attribute("class")):
                                        break
                                    parent_handle = parent.evaluate("el => el.parentElement")
                                    if parent_handle:
                                        parent = parent_handle
                                
                                opportunity_elements.append(parent)
                            
                            logger.info(f"Created {len(opportunity_elements)} opportunity elements from links")
                except Exception as e:
                    logger.error(f"Error finding opportunity links: {str(e)}")
            
            if not opportunity_elements:
                logger.error("Could not find any opportunity elements on the page")
                return opportunities
            
            # Process up to max_pages of results
            page_num = 1
            while page_num <= max_pages:
                logger.info(f"Processing page {page_num} of search results")
                
                # Wait for page to fully load
                self.page.wait_for_load_state("networkidle")
                
                # We're already processing opportunity elements from our earlier search, continue with extraction
                
                # Extract data from each opportunity element
                for element in opportunity_elements:
                    try:
                        # Basic opportunity information
                        title_element = element.query_selector("h3 a")
                        if title_element:
                            title = title_element.inner_text().strip()
                            url = title_element.get_attribute("href")
                            if url and not url.startswith("http"):
                                url = f"{self.base_url}{url}"
                                
                            atm_id = element.query_selector(".opportunity-id")
                            atm_id_text = atm_id.inner_text().strip() if atm_id else "Unknown"
                            
                            # Create opportunity object
                            opportunity = {
                                "title": title,
                                "url": url,
                                "reference_id": atm_id_text,
                                "source": "austender",
                                "scrape_date": datetime.date.today().isoformat()
                            }
                            
                            # Extract other fields if available using a more robust approach
                            # For each field, try multiple potential selectors
                            
                            # Location
                            for selector in [".location", "*[class*='location']", "*:has-text('Location:')"]:
                                try:
                                    location_elem = element.query_selector(selector)
                                    if location_elem:
                                        location_text = location_elem.inner_text().strip()
                                        if "Location:" in location_text:
                                            location_text = location_text.split("Location:")[1].strip()
                                        opportunity["location"] = location_text
                                        break
                                except Exception:
                                    continue
                            
                            # Dates
                            for selector in [".dates", "*[class*='date']", "*:has-text('Closes:')", "*:has-text('Close')"]:
                                try:
                                    dates_elem = element.query_selector(selector)
                                    if dates_elem:
                                        dates_text = dates_elem.inner_text().strip()
                                        # Try to parse closing date
                                        if "Closes:" in dates_text:
                                            closing_date_text = dates_text.split("Closes:")[1].strip()
                                            opportunity["closing_date"] = self._parse_date(closing_date_text)
                                        elif "Close" in dates_text:
                                            closing_date_text = dates_text.split("Close")[1].strip()
                                            opportunity["closing_date"] = self._parse_date(closing_date_text)
                                        break
                                except Exception:
                                    continue
                            
                            # Value
                            for selector in [".value", "*[class*='value']", "*:has-text('Value:')", "*:has-text('$')"]:
                                try:
                                    value_elem = element.query_selector(selector)
                                    if value_elem:
                                        value_text = value_elem.inner_text().strip()
                                        if "Value:" in value_text:
                                            value_text = value_text.split("Value:")[1].strip()
                                        value_amount = self._parse_value(value_text)
                                        if value_amount is not None:
                                            opportunity["capital_value"] = value_amount
                                            break
                                except Exception:
                                    continue
                            
                            # Add to opportunities list
                            opportunities.append(opportunity)
                            logger.debug(f"Added opportunity: {title}")
                            
                    except Exception as e:
                        logger.error(f"Error extracting opportunity details: {str(e)}")
                        continue
                
                # Check if there is a next page button
                next_page = self.page.query_selector(".pagination .next:not(.disabled)")
                
                if next_page and page_num < max_pages:
                    logger.info("Moving to next page of results")
                    next_page.click()
                    self.page.wait_for_load_state("networkidle")
                    time.sleep(random.uniform(2.0, 3.0))  # Wait between page loads
                    page_num += 1
                else:
                    logger.info("No more pages or reached max pages limit")
                    break
            
            logger.info(f"Finished scraping. Found {len(opportunities)} opportunities")
            return opportunities
            
        except Exception as e:
            logger.error(f"Error scraping opportunities: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return opportunities
    
    def get_opportunity_details(self, url: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific opportunity.
        
        Args:
            url: URL of the opportunity
            
        Returns:
            Dictionary with detailed opportunity information
        """
        if not self.page:
            self.start_browser()
            
        opportunity = {
            "url": url,
            "source": "austender",
            "scrape_date": datetime.date.today().isoformat()
        }
        
        try:
            logger.info(f"Getting details for opportunity at {url}")
            
            # Navigate to the opportunity page with increased timeout
            self.page.goto(url, timeout=60000)
            self.page.wait_for_load_state("networkidle", timeout=60000)
            
            # Take a screenshot for debugging
            self.page.screenshot(path=f"screenshots/opportunity_detail_{int(time.time())}.png")
            logger.info("Took screenshot of opportunity detail page")
            
            # Save the HTML for analysis
            html_content = self.page.content()
            html_file_path = f"logs/opportunity_detail_{int(time.time())}.html"
            with open(html_file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Saved opportunity detail HTML to {html_file_path}")
            
            # Extract opportunity details
            
            # Title
            title_elem = self.page.query_selector("h1")
            if title_elem:
                opportunity["title"] = title_elem.inner_text().strip()
            
            # ATM ID
            atm_id_elem = self.page.query_selector(".atm-id")
            if atm_id_elem:
                opportunity["reference_id"] = atm_id_elem.inner_text().strip()
            
            # Published date
            publish_date_elem = self.page.query_selector(".field-published-date .field-value")
            if publish_date_elem:
                date_text = publish_date_elem.inner_text().strip()
                opportunity["publish_date"] = self._parse_date(date_text)
            
            # Closing date
            close_date_elem = self.page.query_selector(".field-closing-date .field-value")
            if close_date_elem:
                date_text = close_date_elem.inner_text().strip()
                opportunity["closing_date"] = self._parse_date(date_text)
            
            # Location
            location_elem = self.page.query_selector(".field-location .field-value")
            if location_elem:
                opportunity["location"] = location_elem.inner_text().strip()
            
            # Description
            description_elem = self.page.query_selector(".description")
            if description_elem:
                opportunity["description"] = description_elem.inner_text().strip()
            
            # Category
            category_elem = self.page.query_selector(".field-category .field-value")
            if category_elem:
                opportunity["category"] = category_elem.inner_text().strip()
            
            # ATM Type
            atm_type_elem = self.page.query_selector(".field-atm-type .field-value")
            if atm_type_elem:
                opportunity["opportunity_type"] = atm_type_elem.inner_text().strip()
            
            # Value
            value_elem = self.page.query_selector(".field-value-range .field-value")
            if value_elem:
                value_text = value_elem.inner_text().strip()
                value_amount = self._parse_value(value_text)
                if value_amount is not None:
                    opportunity["capital_value"] = value_amount
            
            # Agency
            agency_elem = self.page.query_selector(".field-agency .field-value")
            if agency_elem:
                opportunity["agency"] = agency_elem.inner_text().strip()
            
            # Contact information
            contact_name_elem = self.page.query_selector(".field-contact-name .field-value")
            if contact_name_elem:
                opportunity["contact_name"] = contact_name_elem.inner_text().strip()
                
            contact_email_elem = self.page.query_selector(".field-contact-email .field-value")
            if contact_email_elem:
                opportunity["contact_email"] = contact_email_elem.inner_text().strip()
                
            contact_phone_elem = self.page.query_selector(".field-contact-phone .field-value")
            if contact_phone_elem:
                opportunity["contact_phone"] = contact_phone_elem.inner_text().strip()
            
            # Attachments
            attachment_elems = self.page.query_selector_all(".documents-list .document-item")
            if attachment_elems:
                attachments = []
                for elem in attachment_elems:
                    link_elem = elem.query_selector("a")
                    if link_elem:
                        attachment_url = link_elem.get_attribute("href")
                        attachment_name = link_elem.inner_text().strip()
                        
                        # Make URL absolute if it's relative
                        if attachment_url and not attachment_url.startswith("http"):
                            attachment_url = f"{self.base_url}{attachment_url}"
                        
                        attachments.append({
                            "name": attachment_name,
                            "url": attachment_url,
                            "upload_date": datetime.date.today().isoformat()
                        })
                
                if attachments:
                    opportunity["attachments"] = attachments
            
            logger.info(f"Successfully extracted details for opportunity: {opportunity.get('title', url)}")
            return opportunity
            
        except Exception as e:
            logger.error(f"Error getting opportunity details: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return opportunity
    
    def save_opportunities(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        Save opportunities to the database.
        
        Args:
            opportunities: List of opportunities to save
        """
        if not opportunities:
            logger.info("No opportunities to save")
            return
        
        logger.info(f"Saving {len(opportunities)} opportunities to the database")
        
        for opportunity in opportunities:
            opportunity_id = self.opportunity_db.add_opportunity(opportunity)
            if opportunity_id > 0:
                logger.debug(f"Saved opportunity with ID {opportunity_id}: {opportunity.get('title', 'Unknown')}")
            else:
                logger.warning(f"Failed to save opportunity: {opportunity.get('title', 'Unknown')}")
        
        logger.info("Finished saving opportunities to database")
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse a date string into an ISO format date string.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            ISO format date string or None if parsing fails
        """
        if not date_str:
            return None
        
        # Clean up the string
        date_str = date_str.strip()
        
        # Handle cases where the field name might be in the string
        if ":" in date_str:
            date_str = date_str.split(":", 1)[1].strip()
        
        # Remove timezone information
        date_str = date_str.split(" AEST")[0].split(" AEDT")[0].strip()
        
        # Try different date formats
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
        return None
    
    def _parse_value(self, value_str: str) -> Optional[float]:
        """
        Parse a monetary value string into a float.
        
        Args:
            value_str: Value string to parse
            
        Returns:
            Parsed value or None if parsing fails
        """
        if not value_str:
            return None
        
        # Clean up the string
        value_str = value_str.strip().lower()
        
        # Handle cases where the field name might be in the string
        if ":" in value_str:
            value_str = value_str.split(":", 1)[1].strip()
        
        # Handle 'not disclosed' or similar
        if "not disclosed" in value_str or "not available" in value_str or "n/a" in value_str:
            return None
        
        # Remove currency symbols and commas
        value_str = value_str.replace("$", "").replace(",", "").strip()
        
        # Handle ranges
        if "-" in value_str:
            parts = value_str.split("-")
            if len(parts) == 2:
                try:
                    # Extract numbers
                    import re
                    first_match = re.search(r"[\d.]+", parts[0].strip())
                    second_match = re.search(r"[\d.]+", parts[1].strip())
                    
                    if first_match and second_match:
                        first = float(first_match.group(0))
                        second = float(second_match.group(0))
                        return (first + second) / 2  # Return the average
                except (ValueError, AttributeError):
                    pass
        
        # Handle currency codes
        value_parts = value_str.split()
        if value_parts:
            try:
                # Take the first part that looks like a number
                for part in value_parts:
                    if part and part[0].isdigit():
                        return float(part)
            except ValueError:
                pass
        
        logger.warning(f"Could not parse value: {value_str}")
        return None


def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(description="Austender Scraper using Playwright")
    parser.add_argument("--headless", action="store_true", default=False, 
                        help="Run in headless mode (default: False)")
    parser.add_argument("--category", default=DEFAULT_CATEGORY, 
                        help=f"Category to search for (default: {DEFAULT_CATEGORY})")
    parser.add_argument("--pages", type=int, default=3, 
                        help="Maximum number of pages to scrape (default: 3)")
    parser.add_argument("--details", action="store_true", default=True, 
                        help="Get detailed information for each opportunity (default: True)")
    parser.add_argument("--save", action="store_true", default=True, 
                        help="Save opportunities to the database (default: True)")
    parser.add_argument("--scheduler", action="store_true", 
                        help="Run in scheduler mode")
    parser.add_argument("--interval", type=int, default=12, 
                        help="Hours between scheduled runs (default: 12)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode (more verbose logging)")
    
    args = parser.parse_args()
    
    # Create directories for logs and screenshots if they don't exist
    Path("logs").mkdir(exist_ok=True)
    Path("screenshots").mkdir(exist_ok=True)
    
    # Set logging level based on debug flag
    if args.debug:
        logging.getLogger('austender_scraper').setLevel(logging.DEBUG)
    
    # If running in scheduler mode, set up recurring scraper runs
    if args.scheduler:
        import schedule
        
        logger.info(f"Starting scheduler to run every {args.interval} hours")
        
        # Define the job to run
        def scheduled_job():
            logger.info(f"Running scheduled scrape job for category: {args.category}")
            
            try:
                run_scraper(
                    headless=args.headless,
                    category=args.category,
                    max_pages=args.pages,
                    get_details=args.details,
                    save=args.save
                )
            except Exception as e:
                logger.error(f"Error in scheduled job: {str(e)}")
        
        # Schedule the job
        schedule.every(args.interval).hours.do(scheduled_job)
        
        # Run the job immediately once
        scheduled_job()
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        # Run once
        run_scraper(
            headless=args.headless,
            category=args.category,
            max_pages=args.pages,
            get_details=args.details,
            save=args.save
        )


def run_scraper(headless: bool, category: str, max_pages: int, get_details: bool, save: bool):
    """Run the scraper with the specified parameters."""
    try:
        logger.info(f"Starting Austender scraper for category: {category}")
        
        # Use context manager to ensure browser is closed properly
        with AustenderScraper(headless=headless) as scraper:
            # Search for opportunities
            opportunities = scraper.search_opportunities(
                category=category,
                max_pages=max_pages
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
            
            # Get detailed information if requested
            if get_details and opportunities:
                detailed_opportunities = []
                
                for i, opp in enumerate(opportunities, 1):
                    if "url" in opp and opp["url"]:
                        logger.info(f"Getting details for opportunity {i}/{len(opportunities)}")
                        details = scraper.get_opportunity_details(opp["url"])
                        detailed_opportunities.append(details)
                        
                        # Print a brief summary
                        print(f"\nDetails for opportunity {i}:")
                        print(f"Title:        {details.get('title', 'Unknown')}")
                        print(f"Reference ID: {details.get('reference_id', 'Unknown')}")
                        print(f"Location:     {details.get('location', 'Unknown')}")
                        print(f"Value:        {details.get('capital_value', 'Unknown')}")
                        
                        # Be nice to the server
                        time.sleep(random.uniform(3, 5))
                
                opportunities = detailed_opportunities
            
            # Save to database if requested
            if save and opportunities:
                scraper.save_opportunities(opportunities)
                logger.info(f"Saved {len(opportunities)} opportunities to the database")
        
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
