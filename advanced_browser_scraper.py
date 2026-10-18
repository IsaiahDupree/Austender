#!/usr/bin/env python
"""
Advanced Browser-Based Scraper for Government Tender Sites

This script uses Selenium WebDriver to simulate real browser navigation
and extract opportunities from government tender websites that implement
anti-bot measures.

Features:
- Human-like browsing behavior simulation
- Advanced form handling and navigation
- Session management and cookie handling
- Proxy rotation (optional)
- Captcha detection and handling
"""

import os
import sys
import time
import random
import json
import logging
import datetime
import argparse
from typing import List, Dict, Any, Optional
from pathlib import Path

# Try to import Selenium - provide helpful error if not installed
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, 
        NoSuchElementException, 
        ElementNotInteractableException,
        WebDriverException
    )
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Selenium is required for this script. Install it with:")
    print("pip install selenium webdriver-manager")
    sys.exit(1)

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import project modules
try:
    from database.models import Opportunity, Attachment
    from config.config import DATABASE_URL
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except ImportError as e:
    print(f"Failed to import project modules: {str(e)}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/advanced_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("advanced_scraper")

# Set up database connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class AdvancedBrowserScraper:
    """Advanced browser-based scraper for government tender websites."""
    
    def __init__(self, headless: bool = False, proxy: Optional[str] = None):
        """
        Initialize the browser-based scraper.
        
        Args:
            headless: Whether to run the browser in headless mode
            proxy: Optional proxy server to use
        """
        self.headless = headless
        self.proxy = proxy
        self.driver = None
        self.wait = None
        self.sites = {
            "austender": {
                "url": "https://www.tenders.gov.au",
                "search_url": "https://www.tenders.gov.au/search/search-advanced.aspx",
                "selectors": {
                    "search_input": "#searchKeyword",
                    "category_dropdown": "#Category",
                    "location_dropdown": "#Location",
                    "search_button": "input[type='submit'][value='Search']",
                    "opportunity_links": ".search-results .opportunity-item a",
                    "next_page": ".pagination a.next",
                }
            },
            "nsw_etender": {
                "url": "https://www.tenders.nsw.gov.au",
                "search_url": "https://www.tenders.nsw.gov.au/nsw/?event=public.advancedsearch.list",
                "selectors": {
                    "search_input": "#keywords",
                    "category_dropdown": "#category", 
                    "location_dropdown": "#location",
                    "search_button": "input[type='submit'][value='Search']",
                    "opportunity_links": ".opportunityTable tr td a",
                    "next_page": ".pagination a:contains('Next')",
                }
            },
            # Add more sites as needed
        }
        
        self._setup_browser()
    
    def _setup_browser(self):
        """Set up the browser with appropriate options."""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless")
        
        # Make browser automation less detectable
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Set realistic window size
        options.add_argument("--window-size=1920,1080")
        
        # Use a realistic user agent
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36")
        
        # Use proxy if provided
        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")
        
        # Install and set up Chrome driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # Override JavaScript properties used for bot detection
        self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
        """)
        
        # Set up wait mechanism with a timeout of 20 seconds
        self.wait = WebDriverWait(self.driver, 20)
    
    def _simulate_human_browsing(self):
        """Add random pauses and mouse movements to simulate human browsing."""
        # Random pause between 2-5 seconds
        time.sleep(random.uniform(2, 5))
        
        # Simulate some scrolling
        scroll_amount = random.randint(200, 800)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.5, 2))
    
    def _safe_click(self, element):
        """
        Safely click an element with human-like behavior.
        
        Args:
            element: The WebElement to click
        """
        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(random.uniform(0.5, 1.5))
            
            # Click the element
            element.click()
            
            # Add small pause after click
            time.sleep(random.uniform(1, 3))
            return True
        except (ElementNotInteractableException, WebDriverException) as e:
            logger.warning(f"Failed to click element: {str(e)}")
            try:
                # Attempt JavaScript click as fallback
                self.driver.execute_script("arguments[0].click();", element)
                time.sleep(random.uniform(1, 3))
                return True
            except Exception as js_e:
                logger.error(f"JavaScript click also failed: {str(js_e)}")
                return False
    
    def scrape_austender(self, category: str = "construction", max_pages: int = 5):
        """
        Scrape opportunities from the Austender website.
        
        Args:
            category: Category to search for
            max_pages: Maximum number of pages to scrape
        
        Returns:
            List of opportunities
        """
        site_config = self.sites["austender"]
        opportunities = []
        
        try:
            # Navigate to the search page
            logger.info(f"Navigating to Austender search page: {site_config['search_url']}")
            self.driver.get(site_config['search_url'])
            self._simulate_human_browsing()
            
            # Complete the search form
            logger.info(f"Searching for category: {category}")
            
            # Find and fill the category dropdown
            try:
                category_dropdown = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, site_config['selectors']['category_dropdown']))
                )
                category_dropdown_select = webdriver.support.ui.Select(category_dropdown)
                category_dropdown_select.select_by_visible_text(category.capitalize())
                self._simulate_human_browsing()
            except (TimeoutException, NoSuchElementException) as e:
                logger.warning(f"Could not find category dropdown: {str(e)}")
            
            # Submit the search form
            try:
                search_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, site_config['selectors']['search_button']))
                )
                self._safe_click(search_button)
            except (TimeoutException, NoSuchElementException) as e:
                logger.warning(f"Could not find search button: {str(e)}")
                # Try pressing Enter on the form as an alternative
                search_input = self.driver.find_element(By.CSS_SELECTOR, site_config['selectors']['search_input'])
                search_input.send_keys(Keys.RETURN)
            
            # Process the specified number of pages
            current_page = 1
            while current_page <= max_pages:
                logger.info(f"Processing page {current_page}")
                self._simulate_human_browsing()
                
                # Extract opportunities from the current page
                try:
                    # Wait for the results to load
                    self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".search-results"))
                    )
                    
                    # Extract all opportunity elements
                    opportunity_elements = self.driver.find_elements(By.CSS_SELECTOR, site_config['selectors']['opportunity_links'])
                    
                    if not opportunity_elements:
                        logger.info("No opportunities found on this page")
                        break
                    
                    logger.info(f"Found {len(opportunity_elements)} opportunities on page {current_page}")
                    
                    # Process each opportunity
                    for element in opportunity_elements:
                        try:
                            title = element.text.strip()
                            url = element.get_attribute("href")
                            
                            if title and url:
                                # Store basic information for now
                                opportunities.append({
                                    "title": title,
                                    "url": url,
                                    "source": "Austender",
                                    "scrape_date": datetime.date.today()
                                })
                                logger.debug(f"Found opportunity: {title} at {url}")
                        except Exception as e:
                            logger.warning(f"Error extracting opportunity details: {str(e)}")
                    
                    # Check if there's a next page
                    try:
                        next_page = self.driver.find_element(By.CSS_SELECTOR, site_config['selectors']['next_page'])
                        if next_page.is_displayed() and next_page.is_enabled():
                            self._safe_click(next_page)
                            current_page += 1
                            # Add longer pause between page navigations
                            time.sleep(random.uniform(3, 6))
                        else:
                            logger.info("No more pages available")
                            break
                    except NoSuchElementException:
                        logger.info("No next page link found - reached the end of results")
                        break
                    
                except Exception as e:
                    logger.error(f"Error processing page {current_page}: {str(e)}")
                    break
            
            logger.info(f"Completed scraping, found {len(opportunities)} opportunities")
            return opportunities
            
        except Exception as e:
            logger.error(f"Error scraping Austender: {str(e)}")
            import traceback
            traceback.print_exc()
            return opportunities
        finally:
            # Always ensure we have the latest cookies saved
            self._save_cookies("austender")
    
    def get_opportunity_details(self, url: str) -> Dict[str, Any]:
        """
        Get detailed information about an opportunity.
        
        Args:
            url: URL of the opportunity detail page
        
        Returns:
            Dictionary with opportunity details
        """
        details = {
            "url": url,
            "scrape_date": datetime.date.today()
        }
        
        try:
            logger.info(f"Fetching opportunity details from: {url}")
            self.driver.get(url)
            self._simulate_human_browsing()
            
            # Determine which site we're on based on the URL
            site_key = next((key for key, config in self.sites.items() if config["url"] in url), None)
            
            if not site_key:
                logger.warning(f"Unknown site for URL: {url}")
                return details
            
            # Extract details based on the site structure
            if site_key == "austender":
                # Wait for the page to load
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".opportunity-details, .tender-detail"))
                )
                
                # Extract basic information
                try:
                    details["title"] = self.driver.find_element(By.CSS_SELECTOR, "h1.opportunity-title").text.strip()
                except NoSuchElementException:
                    try:
                        details["title"] = self.driver.find_element(By.CSS_SELECTOR, ".tender-title h1").text.strip()
                    except NoSuchElementException:
                        logger.warning("Could not find opportunity title")
                
                # Extract reference ID
                try:
                    details["reference_id"] = self.driver.find_element(By.CSS_SELECTOR, ".atm-id").text.strip()
                except NoSuchElementException:
                    try:
                        id_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'ATM ID:') or contains(text(), 'Reference:')]/following-sibling::*")
                        details["reference_id"] = id_element.text.strip()
                    except NoSuchElementException:
                        logger.warning("Could not find reference ID")
                
                # Extract dates
                try:
                    publish_date = self.driver.find_element(By.CSS_SELECTOR, ".publish-date").text.strip()
                    details["publish_date"] = self._parse_date(publish_date)
                except NoSuchElementException:
                    try:
                        publish_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Published:')]/following-sibling::*")
                        details["publish_date"] = self._parse_date(publish_element.text.strip())
                    except NoSuchElementException:
                        logger.warning("Could not find publish date")
                
                try:
                    closing_date = self.driver.find_element(By.CSS_SELECTOR, ".closing-date").text.strip()
                    details["closing_date"] = self._parse_date(closing_date)
                except NoSuchElementException:
                    try:
                        closing_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Closing:')]/following-sibling::*")
                        details["closing_date"] = self._parse_date(closing_element.text.strip())
                    except NoSuchElementException:
                        logger.warning("Could not find closing date")
                
                # Extract location
                try:
                    details["location"] = self.driver.find_element(By.CSS_SELECTOR, ".location").text.strip()
                except NoSuchElementException:
                    try:
                        location_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Location:')]/following-sibling::*")
                        details["location"] = location_element.text.strip()
                    except NoSuchElementException:
                        logger.warning("Could not find location")
                
                # Extract description
                try:
                    description_element = self.driver.find_element(By.CSS_SELECTOR, ".opportunity-description")
                    details["description"] = description_element.text.strip()
                except NoSuchElementException:
                    try:
                        description_element = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'Description')]/following-sibling::div")
                        details["description"] = description_element.text.strip()
                    except NoSuchElementException:
                        logger.warning("Could not find description")
                
                # Extract value
                try:
                    value_str = self.driver.find_element(By.CSS_SELECTOR, ".estimated-value").text.strip()
                    details["capital_value"] = self._parse_value(value_str)
                except NoSuchElementException:
                    try:
                        value_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Value:') or contains(text(), 'Estimated Value:')]/following-sibling::*")
                        details["capital_value"] = self._parse_value(value_element.text.strip())
                    except NoSuchElementException:
                        logger.warning("Could not find value")
                
                # Extract attachments
                attachments = []
                try:
                    attachment_elements = self.driver.find_elements(By.CSS_SELECTOR, ".attachment")
                    
                    for element in attachment_elements:
                        try:
                            name_element = element.find_element(By.CSS_SELECTOR, ".name")
                            link_element = element.find_element(By.CSS_SELECTOR, "a")
                            
                            attachments.append({
                                "name": name_element.text.strip(),
                                "url": link_element.get_attribute("href"),
                                "upload_date": datetime.date.today()
                            })
                        except NoSuchElementException:
                            continue
                except NoSuchElementException:
                    logger.warning("Could not find attachments")
                
                details["attachments"] = attachments
            
            # Add similar extraction logic for other sites as needed
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting opportunity details: {str(e)}")
            import traceback
            traceback.print_exc()
            return details
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """
        Parse a date string into a datetime.date object.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Parsed date or None if parsing fails
        """
        if not date_str:
            return None
        
        # Clean up the date string - remove extra content after time
        date_str = date_str.split(" AEST")[0].split(" AEDT")[0]
        
        formats = [
            "%d/%m/%Y",
            "%d/%m/%Y %H:%M %p",
            "%d/%m/%Y %H:%M:%S",
            "%d %b %Y",
            "%d %B %Y",
            "%B %d, %Y",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.datetime.strptime(date_str, fmt).date()
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
        if not value_str or "not disclosed" in value_str.lower():
            return None
        
        # Remove currency symbols and commas
        value_str = value_str.replace("$", "").replace(",", "").strip()
        
        # Handle ranges (e.g., "5,000,000 - 8,000,000")
        if "-" in value_str:
            parts = value_str.split("-")
            if len(parts) == 2:
                try:
                    # Extract numbers from strings
                    import re
                    first = float(re.search(r"[\d.]+", parts[0].strip()).group(0))
                    second = float(re.search(r"[\d.]+", parts[1].strip()).group(0))
                    return (first + second) / 2  # Return the average
                except (ValueError, AttributeError):
                    pass
        
        # Handle "AUD" or other currency codes
        value_str = value_str.split(" ")[0].strip()
        
        try:
            return float(value_str)
        except ValueError:
            logger.warning(f"Could not parse value: {value_str}")
            return None
    
    def save_opportunities(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        Save opportunities to the database.
        
        Args:
            opportunities: List of opportunity dictionaries to save
        """
        if not opportunities:
            logger.info("No opportunities to save")
            return
        
        logger.info(f"Saving {len(opportunities)} opportunities to the database")
        
        with SessionLocal() as db:
            for opp_data in opportunities:
                try:
                    # Check if opportunity already exists
                    existing = None
                    if "reference_id" in opp_data and opp_data["reference_id"]:
                        existing = db.query(Opportunity).filter(
                            Opportunity.reference_id == opp_data["reference_id"]
                        ).first()
                    elif "url" in opp_data and opp_data["url"]:
                        existing = db.query(Opportunity).filter(
                            Opportunity.url == opp_data["url"]
                        ).first()
                    
                    if existing:
                        # Update existing opportunity
                        logger.debug(f"Updating existing opportunity: {opp_data.get('title', opp_data.get('reference_id', 'Unknown'))}")
                        
                        # Don't overwrite non-None values with None
                        for key, value in opp_data.items():
                            if key != "attachments" and value is not None:
                                setattr(existing, key, value)
                        
                        # Handle attachments if present
                        if "attachments" in opp_data and opp_data["attachments"]:
                            self._update_attachments(db, existing, opp_data["attachments"])
                        
                        opportunity = existing
                    else:
                        # Create new opportunity
                        logger.debug(f"Creating new opportunity: {opp_data.get('title', 'Unknown')}")
                        
                        # Extract attachment data if present
                        attachments_data = opp_data.pop("attachments", [])
                        
                        # Create opportunity
                        opportunity = Opportunity(**{k: v for k, v in opp_data.items() if k != "attachments"})
                        db.add(opportunity)
                        db.flush()  # Ensure the opportunity has an ID before adding attachments
                        
                        # Add attachments if present
                        if attachments_data:
                            self._add_attachments(db, opportunity, attachments_data)
                    
                    db.commit()
                    
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error saving opportunity: {str(e)}")
                    continue
        
        logger.info("Finished saving opportunities")
    
    def _add_attachments(self, db, opportunity, attachments_data):
        """Add attachments to an opportunity."""
        for attachment_data in attachments_data:
            try:
                new_attachment = Attachment(
                    opportunity_id=opportunity.id,
                    name=attachment_data.get("name"),
                    url=attachment_data.get("url"),
                    description=attachment_data.get("description"),
                    upload_date=attachment_data.get("upload_date", datetime.date.today())
                )
                db.add(new_attachment)
            except Exception as e:
                logger.warning(f"Error adding attachment: {str(e)}")
                continue
    
    def _update_attachments(self, db, opportunity, attachments_data):
        """Update attachments for an opportunity."""
        # Get existing attachment URLs
        existing_urls = {attachment.url: attachment for attachment in opportunity.attachments}
        
        # Add new attachments
        for attachment_data in attachments_data:
            try:
                url = attachment_data.get("url")
                
                if url and url not in existing_urls:
                    new_attachment = Attachment(
                        opportunity_id=opportunity.id,
                        name=attachment_data.get("name"),
                        url=url,
                        description=attachment_data.get("description"),
                        upload_date=attachment_data.get("upload_date", datetime.date.today())
                    )
                    db.add(new_attachment)
            except Exception as e:
                logger.warning(f"Error updating attachment: {str(e)}")
                continue
    
    def _save_cookies(self, site_key: str):
        """Save cookies for a site to disk for later use."""
        cookies_dir = Path("cookies")
        cookies_dir.mkdir(exist_ok=True)
        
        cookie_file = cookies_dir / f"{site_key}_cookies.json"
        
        try:
            with open(cookie_file, "w") as f:
                json.dump(self.driver.get_cookies(), f)
            logger.debug(f"Saved cookies for {site_key}")
        except Exception as e:
            logger.warning(f"Failed to save cookies: {str(e)}")
    
    def _load_cookies(self, site_key: str):
        """Load cookies for a site from disk."""
        cookies_dir = Path("cookies")
        cookie_file = cookies_dir / f"{site_key}_cookies.json"
        
        if not cookie_file.exists():
            logger.debug(f"No cookie file found for {site_key}")
            return False
        
        try:
            with open(cookie_file, "r") as f:
                cookies = json.load(f)
            
            # Navigate to the domain first
            site_url = self.sites[site_key]["url"]
            self.driver.get(site_url)
            time.sleep(2)
            
            # Add the cookies
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            
            logger.debug(f"Loaded cookies for {site_key}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load cookies: {str(e)}")
            return False
    
    def close(self):
        """Close the browser and release resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Browser closed")


def main():
    """Main function to parse arguments and run the scraper."""
    parser = argparse.ArgumentParser(description="Advanced browser-based scraper for government tender sites")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode (no visible browser)")
    parser.add_argument("--proxy", help="Proxy server to use (e.g., 'http://127.0.0.1:8080')")
    parser.add_argument("--site", choices=["austender", "nsw_etender", "all"], default="austender", help="Site to scrape")
    parser.add_argument("--category", default="construction", help="Category to search for")
    parser.add_argument("--pages", type=int, default=3, help="Maximum number of pages to scrape")
    parser.add_argument("--details", action="store_true", default=True, help="Get detailed information for each opportunity")
    parser.add_argument("--save", action="store_true", default=True, help="Save opportunities to the database")
    parser.add_argument("--scheduler", action="store_true", help="Run in scheduler mode")
    parser.add_argument("--interval", type=int, default=12, help="Hours between scheduled runs")
    parser.add_argument("--sources", help="Comma-separated list of sources to scrape in scheduler mode")
    
    args = parser.parse_args()
    
    # If running in scheduler mode, set up recurring scraper runs
    if args.scheduler:
        import schedule
        import time
        
        logger.info(f"Starting scheduler to run every {args.interval} hours")
        
        # Parse sources list
        sources = ["austender"]
        if args.sources:
            sources = args.sources.split(",")
        
        # Define the job to run
        def scheduled_job():
            logger.info(f"Running scheduled scrape job for sources: {sources}")
            for site in sources:
                try:
                    run_scraper(site=site, category=args.category, max_pages=args.pages, 
                               headless=args.headless, proxy=args.proxy,
                               get_details=args.details, save=args.save)
                except Exception as e:
                    logger.error(f"Error in scheduled job for site {site}: {str(e)}")
                    continue
        
        # Schedule the job
        schedule.every(args.interval).hours.do(scheduled_job)
        
        # Run the job immediately once
        scheduled_job()
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        # Run once for the specified site or all sites
        if args.site == "all":
            sites = ["austender", "nsw_etender"]
            for site in sites:
                try:
                    run_scraper(site=site, category=args.category, max_pages=args.pages,
                               headless=args.headless, proxy=args.proxy,
                               get_details=args.details, save=args.save)
                except Exception as e:
                    logger.error(f"Error scraping site {site}: {str(e)}")
                    continue
        else:
            run_scraper(site=args.site, category=args.category, max_pages=args.pages,
                       headless=args.headless, proxy=args.proxy,
                       get_details=args.details, save=args.save)


def run_scraper(site, category, max_pages, headless=True, proxy=None, get_details=True, save=True):
    """Run the scraper with the specified parameters."""
    try:
        logger.info(f"Initializing advanced browser scraper for {site}")
        scraper = AdvancedBrowserScraper(headless=headless, proxy=proxy)
        
        try:
            # Scrape opportunities
            if site == "austender":
                opportunities = scraper.scrape_austender(category=category, max_pages=max_pages)
            elif site == "nsw_etender":
                # Implement NSW eTender scraping
                logger.info("NSW eTender scraping not yet implemented")
                opportunities = []
            else:
                logger.error(f"Unknown site: {site}")
                opportunities = []
            
            logger.info(f"Found {len(opportunities)} opportunities from {site}")
            
            # Log opportunity summary
            for i, opp in enumerate(opportunities, 1):
                logger.info(f"Opportunity {i}: {opp.get('title', 'Unknown')} | {opp.get('url', 'Unknown')}")
            
            # Get detailed information if requested
            if get_details and opportunities:
                detailed_opportunities = []
                
                for i, opp in enumerate(opportunities, 1):
                    if "url" in opp and opp["url"]:
                        logger.info(f"Fetching details for opportunity {i}/{len(opportunities)}")
                        details = scraper.get_opportunity_details(opp["url"])
                        detailed_opportunities.append({**opp, **details})
                        
                        # Log some information
                        logger.info(f"Retrieved details: {details.get('title', 'Unknown')} | {details.get('reference_id', 'Unknown')}")
                        
                        # Be nice to the server
                        time.sleep(random.uniform(3, 5))
                
                opportunities = detailed_opportunities
            
            # Save to database if requested
            if save and opportunities:
                scraper.save_opportunities(opportunities)
                logger.info(f"Saved {len(opportunities)} opportunities to the database")
                
            return opportunities
            
        finally:
            # Always close the browser
            scraper.close()
        
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


if __name__ == "__main__":
    main()
