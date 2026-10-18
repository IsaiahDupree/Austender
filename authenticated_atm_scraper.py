#!/usr/bin/env python3
"""
Authenticated ATM Scraper for Austender
---------------------------------------
Enhanced scraper that focuses on authenticated access to Austender,
implementing multiple strategies for bypassing access restrictions.
"""

import os
import json
import time
import random
import asyncio
import logging
import httpx
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from openai import AsyncOpenAI
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"logs/authenticated_scraper_{datetime.now().strftime('%Y%m%d_%H%M')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("authenticated_scraper")

# Create directories
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)

class AuthenticatedATMScraper:
    """ATM scraper with authentication and multiple strategies."""
    
    def __init__(self, headless=False, debug=True):
        """Initialize the authenticated scraper."""
        self.headless = headless
        self.debug = debug
        
        # Credentials for authentication
        self.username = os.getenv("AUSTENDER_USERNAME", "")
        self.password = os.getenv("AUSTENDER_PASSWORD", "")
        
        # OpenAI API for screenshot analysis
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Search parameters
        self.keyword = "construction"
        self.state = "NSW"  # Can be None for all states
        
        # URLs
        self.main_url = "https://www.tenders.gov.au"
        self.login_url = "https://www.tenders.gov.au/Home/Login"
        self.atm_search_url = "https://www.tenders.gov.au/ATM/Search"
        
        # Browser and context variables
        self.browser = None
        self.context = None
        self.page = None
        
        logger.info("Initialized Authenticated ATM Scraper")
    
    async def setup_browser(self, browser_type="chromium"):
        """Set up a browser with stealth plugin."""
        logger.info(f"Setting up {browser_type} browser")
        
        try:
            # Start a new playwright instance
            playwright = await async_playwright().start()
            
            # Select the browser type
            if browser_type == "firefox":
                self.browser = await playwright.firefox.launch(headless=self.headless)
            elif browser_type == "webkit":
                self.browser = await playwright.webkit.launch(headless=self.headless)
            else:
                self.browser = await playwright.chromium.launch(headless=self.headless)
            
            # Create a new browser context with realistic viewport
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
            )
            
            # Add human-like interaction behaviors
            await self.context.add_init_script("""
                // Override the navigator properties to make detection harder
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
                
                // Add a delay function for human-like timing
                window.humanDelay = function(min, max) {
                    const delay = Math.floor(Math.random() * (max - min + 1)) + min;
                    return new Promise(resolve => setTimeout(resolve, delay));
                };
            """)
            
            # Create a new page
            self.page = await self.context.new_page()
            
            # Add event listeners for additional stealth
            await self.page.add_init_script("""
                // Override permissions prompt
                window.Notification = {
                    permission: 'granted',
                    requestPermission: () => Promise.resolve('granted')
                };
                
                // Override some WebGL functions to prevent fingerprinting
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Google Inc. (Intel)';
                    }
                    if (parameter === 37446) {
                        return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
                    }
                    return getParameter.apply(this, arguments);
                };
            """)
            
            # Set extra HTTP headers to appear more legitimate
            await self.page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache"
            })
            
            logger.info(f"Browser setup complete with {browser_type}")
            return True
        
        except Exception as e:
            logger.error(f"Error setting up browser: {str(e)}")
            return False
    
    async def simulate_human_behavior(self):
        """Simulate human-like behavior for anti-bot evasion."""
        logger.info("Simulating human behavior")
        
        try:
            # Simulate mouse movements
            await self.page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await self.page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            
            # Simulate scrolling
            await self.page.evaluate("""
                window.scrollTo({
                    top: Math.random() * 100,
                    behavior: 'smooth'
                });
            """)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Simulate more natural scrolling
            await self.page.evaluate("""
                window.scrollTo({
                    top: Math.random() * 300,
                    behavior: 'smooth'
                });
            """)
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            return True
        
        except Exception as e:
            logger.error(f"Error simulating human behavior: {str(e)}")
            return False
    
    async def login(self):
        """Log in to Austender using credentials."""
        logger.info("Attempting to log in to Austender")
        
        try:
            # Navigate to the login page
            await self.page.goto(self.login_url, wait_until="networkidle")
            logger.info("Navigated to login page")
            
            # Take a screenshot for debugging if enabled
            if self.debug:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"screenshots/login_page_{timestamp}.png"
                await self.page.screenshot(path=screenshot_path)
                logger.info(f"Saved login page screenshot to {screenshot_path}")
            
            # Simulate human behavior before login
            await self.simulate_human_behavior()
            
            # Fill in the login form
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await self.page.fill("input[name='UserName']", self.username)
            await asyncio.sleep(random.uniform(0.8, 1.2))
            await self.page.fill("input[name='Password']", self.password)
            
            # Add a small delay before clicking login
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Click the login button
            login_button = await self.page.query_selector("button[type='submit'], input[type='submit']")
            if login_button:
                await login_button.click()
                logger.info("Clicked login button")
            else:
                logger.warning("Login button not found")
                return False
            
            # Wait for navigation to complete
            await self.page.wait_for_load_state("networkidle")
            
            # Check if login was successful
            current_url = self.page.url
            if "login" not in current_url.lower():
                logger.info("Login successful")
                
                # Take a screenshot after login if debugging
                if self.debug:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = f"screenshots/after_login_{timestamp}.png"
                    await self.page.screenshot(path=screenshot_path)
                    logger.info(f"Saved post-login screenshot to {screenshot_path}")
                
                return True
            else:
                logger.warning("Login failed")
                return False
        
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False
    
    async def navigate_to_atm_search(self):
        """Navigate to the ATM search page."""
        logger.info("Navigating to ATM search page")
        
        try:
            # Try to find and click the ATM link from the main navigation first
            try:
                await self.page.goto(self.main_url, wait_until="networkidle")
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # Look for the ATM link in the navigation
                atm_link = await self.page.query_selector("a[href*='ATM'], a:text('ATM')")
                if atm_link:
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    await atm_link.click()
                    logger.info("Clicked ATM link in navigation")
                    await self.page.wait_for_load_state("networkidle")
                    
                    # Then look for a search link
                    search_link = await self.page.query_selector("a[href*='Search'], a:text('Search')")
                    if search_link:
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        await search_link.click()
                        logger.info("Clicked Search link in ATM section")
                        await self.page.wait_for_load_state("networkidle")
                    else:
                        logger.info("Search link not found, trying direct navigation")
                else:
                    logger.info("ATM link not found in navigation, trying direct navigation")
            
            except Exception as e:
                logger.warning(f"Error during navigation via links: {str(e)}")
            
            # If navigation via links fails, try direct URL access
            if not self.page.url.endswith("ATM/Search"):
                logger.info("Direct navigation to ATM search page")
                await self.page.goto(self.atm_search_url, wait_until="networkidle")
            
            # Simulate human behavior on the search page
            await self.simulate_human_behavior()
            
            # Take a screenshot of the search page if debugging
            if self.debug:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"screenshots/atm_search_{timestamp}.png"
                await self.page.screenshot(path=screenshot_path)
                logger.info(f"Saved ATM search page screenshot to {screenshot_path}")
                
                # Analyze the screenshot to check if we're on the right page
                screenshot_analysis = await self.analyze_screenshot(screenshot_path)
                logger.info(f"Screenshot analysis: {screenshot_analysis}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error navigating to ATM search page: {str(e)}")
            return False
    
    async def perform_search(self):
        """Perform a search for ATM listings."""
        logger.info(f"Performing search with keyword: {self.keyword}, state: {self.state}")
        
        try:
            # Wait for search form to be loaded
            await self.page.wait_for_selector("form", timeout=10000)
            
            # Fill in search criteria with random delays to appear human-like
            if self.keyword:
                keyword_field = await self.page.query_selector("input[name*='keyword'], input[placeholder*='keyword']")
                if keyword_field:
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    await keyword_field.fill(self.keyword)
                    logger.info(f"Filled keyword field with: {self.keyword}")
                else:
                    logger.warning("Keyword field not found")
            
            # Select state if provided
            if self.state:
                state_selector = await self.page.query_selector("select[name*='state'], select[id*='state']")
                if state_selector:
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    await state_selector.select_option(value=self.state)
                    logger.info(f"Selected state: {self.state}")
                else:
                    logger.warning("State selector not found")
            
            # Click search button with delay
            await asyncio.sleep(random.uniform(0.8, 1.5))
            search_button = await self.page.query_selector("button[type='submit'], input[type='submit']")
            if search_button:
                await search_button.click()
                logger.info("Clicked search button")
            else:
                logger.warning("Search button not found")
                return False
            
            # Wait for results to load
            await self.page.wait_for_load_state("networkidle")
            
            # Take a screenshot of the results page if debugging
            if self.debug:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"screenshots/search_results_{timestamp}.png"
                await self.page.screenshot(path=screenshot_path)
                logger.info(f"Saved search results screenshot to {screenshot_path}")
                
                # Analyze the screenshot to see if we got search results
                screenshot_analysis = await self.analyze_screenshot(screenshot_path)
                logger.info(f"Results page analysis: {screenshot_analysis}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error performing search: {str(e)}")
            return False
    
    async def extract_listings(self):
        """Extract ATM listings from the search results."""
        logger.info("Extracting ATM listings from search results")
        
        listings = []
        
        try:
            # Try multiple selector strategies to find listings
            selectors = [
                "table.searchResults tr[class^='row']",
                ".results-table tbody tr",
                "table#ATMSearchResults tr",
                ".search-results .atm-item",
                "div[id*='ATM'] table tr",
                "div.table-responsive table tr"
            ]
            
            for selector in selectors:
                rows = await self.page.query_selector_all(selector)
                if rows and len(rows) > 1:  # Skip if only header row
                    logger.info(f"Found {len(rows)} rows using selector: {selector}")
                    
                    # Process each row
                    for row in rows:
                        try:
                            # Extract data based on common patterns
                            title_element = await row.query_selector("td a, th a, .title a")
                            if title_element:
                                title = await title_element.inner_text()
                                href = await title_element.get_attribute("href")
                                
                                # Get other data from cells
                                cells = await row.query_selector_all("td, th")
                                
                                # Try to extract other fields
                                reference_id = None
                                published_date = None
                                closing_date = None
                                category = None
                                
                                # Based on common patterns in ATM tables
                                if len(cells) >= 2:
                                    reference_id_text = await cells[0].inner_text() if len(cells) > 0 else None
                                    if reference_id_text:
                                        reference_id = reference_id_text.strip()
                                
                                if len(cells) >= 3:
                                    published_date_text = await cells[2].inner_text() if len(cells) > 2 else None
                                    if published_date_text:
                                        published_date = published_date_text.strip()
                                
                                if len(cells) >= 4:
                                    closing_date_text = await cells[3].inner_text() if len(cells) > 3 else None
                                    if closing_date_text:
                                        closing_date = closing_date_text.strip()
                                
                                if len(cells) >= 5:
                                    category_text = await cells[4].inner_text() if len(cells) > 4 else None
                                    if category_text:
                                        category = category_text.strip()
                                
                                # Create listing object
                                listing = {
                                    "title": title.strip() if title else "Unknown",
                                    "url": href if href and href.startswith("http") else f"{self.main_url}{href}",
                                    "reference_id": reference_id,
                                    "published_date": published_date,
                                    "closing_date": closing_date,
                                    "category": category,
                                    "extracted_at": datetime.now().isoformat()
                                }
                                
                                listings.append(listing)
                        
                        except Exception as e:
                            logger.warning(f"Error extracting data from row: {str(e)}")
                    
                    # If we found listings with this selector, no need to try others
                    if listings:
                        break
            
            if not listings:
                # If no listings found, try extracting using HTML parsing
                html_content = await self.page.content()
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Try various ways to find tables with listings
                tables = soup.select("table.searchResults, .results-table, table#ATMSearchResults")
                if tables:
                    for table in tables:
                        rows = table.select("tr")
                        for row in rows[1:]:  # Skip header row
                            try:
                                cells = row.select("td")
                                if cells and len(cells) >= 3:
                                    title_element = row.select_one("td a")
                                    if title_element:
                                        title = title_element.text
                                        href = title_element.get("href", "")
                                        
                                        # Create listing object
                                        listing = {
                                            "title": title.strip(),
                                            "url": href if href.startswith("http") else f"{self.main_url}{href}",
                                            "reference_id": cells[0].text.strip() if len(cells) > 0 else None,
                                            "published_date": cells[2].text.strip() if len(cells) > 2 else None,
                                            "closing_date": cells[3].text.strip() if len(cells) > 3 else None,
                                            "category": cells[4].text.strip() if len(cells) > 4 else None,
                                            "extracted_at": datetime.now().isoformat()
                                        }
                                        
                                        listings.append(listing)
                            except Exception as e:
                                logger.warning(f"Error parsing row with BeautifulSoup: {str(e)}")
            
            logger.info(f"Extracted {len(listings)} ATM listings")
            
            # Save the listings to a file
            if listings:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"data/atm_listings_{timestamp}.json"
                with open(filename, "w") as f:
                    json.dump(listings, f, indent=2)
                logger.info(f"Saved {len(listings)} listings to {filename}")
            
            return listings
        
        except Exception as e:
            logger.error(f"Error extracting listings: {str(e)}")
            return []
    
    async def analyze_screenshot(self, screenshot_path):
        """Analyze screenshot using OpenAI API to help debug issues."""
        logger.info(f"Analyzing screenshot: {screenshot_path}")
        
        try:
            import base64
            
            # Read the screenshot and convert to base64
            with open(screenshot_path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Call OpenAI API to analyze the screenshot
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert web scraper analyzing screenshots to help debug issues. Be concise but thorough."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Analyze this screenshot from the Austender website. What page is shown? Are there any search results or listings visible? Is there an error message? Is this a login page? Provide a brief analysis of what's visible and any issues you notice."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]}
                ],
                max_tokens=300
            )
            
            analysis = response.choices[0].message.content
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing screenshot: {str(e)}")
            return "Error analyzing screenshot"
    
    async def execute_with_retries(self, max_retries=3):
        """Execute the scraping process with retries using different browser types."""
        logger.info(f"Executing with up to {max_retries} retries")
        
        browser_types = ["chromium", "firefox", "webkit"]
        listings = []
        
        for attempt, browser_type in enumerate(browser_types, 1):
            if attempt > max_retries:
                break
            
            logger.info(f"Attempt {attempt}/{max_retries} using {browser_type}")
            
            try:
                # Set up browser
                setup_success = await self.setup_browser(browser_type)
                if not setup_success:
                    logger.warning(f"Failed to set up {browser_type} browser, trying next type")
                    continue
                
                # Login to Austender
                login_success = await self.login()
                if not login_success:
                    logger.warning("Login failed, trying without authentication")
                
                # Navigate to ATM search page
                nav_success = await self.navigate_to_atm_search()
                if not nav_success:
                    logger.warning("Navigation to ATM search failed, trying next browser type")
                    await self.close_browser()
                    continue
                
                # Perform search
                search_success = await self.perform_search()
                if not search_success:
                    logger.warning("Search failed, trying next browser type")
                    await self.close_browser()
                    continue
                
                # Extract listings
                current_listings = await self.extract_listings()
                if current_listings:
                    listings = current_listings
                    logger.info(f"Successfully extracted {len(listings)} listings using {browser_type}")
                    break
                else:
                    logger.warning(f"No listings extracted with {browser_type}, trying next type")
                
                # Close browser before next attempt
                await self.close_browser()
            
            except Exception as e:
                logger.error(f"Error during execution with {browser_type}: {str(e)}")
                await self.close_browser()
        
        # Return results
        return {
            "success": bool(listings),
            "data": listings,
            "method": "authenticated_browser",
            "timestamp": datetime.now().isoformat()
        }
    
    async def close_browser(self):
        """Close the browser and clean up resources."""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
        
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")

async def run_test(headless=False, debug=True):
    """Run a test of the authenticated scraper."""
    scraper = AuthenticatedATMScraper(headless=headless, debug=debug)
    result = await scraper.execute_with_retries()
    return result

def main():
    """Main function to run the authenticated scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Authenticated ATM Scraper")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with screenshots")
    parser.add_argument("--keyword", type=str, default="construction", help="Keyword to search for")
    parser.add_argument("--state", type=str, help="State filter (e.g. NSW, VIC)")
    
    args = parser.parse_args()
    
    # Run the scraper
    print("Running authenticated ATM scraper...")
    loop = asyncio.get_event_loop()
    scraper = AuthenticatedATMScraper(headless=args.headless, debug=args.debug)
    
    # Set search parameters
    if args.keyword:
        scraper.keyword = args.keyword
    if args.state:
        scraper.state = args.state
    
    # Execute with retries
    result = loop.run_until_complete(scraper.execute_with_retries())
    
    # Print results
    print(f"Execution completed with success: {result['success']}")
    if result["success"]:
        print(f"Extracted {len(result['data'])} ATM listings")
        
        # Print some sample listings
        if result["data"]:
            print("\nSample listings:")
            for i, listing in enumerate(result["data"][:3], 1):
                print(f"\n{'-'*40}")
                print(f"Listing {i}:")
                print(f"Title: {listing.get('title', 'Unknown')}")
                print(f"Reference: {listing.get('reference_id', 'Unknown')}")
                print(f"URL: {listing.get('url', 'Unknown')}")
                print(f"Published: {listing.get('published_date', 'Unknown')}")
                print(f"Closing: {listing.get('closing_date', 'Unknown')}")
    else:
        print("Failed to extract any listings")

if __name__ == "__main__":
    main()
