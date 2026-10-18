#!/usr/bin/env python3
"""
Multi-Tool ATM Scraper for Austender
------------------------------------
A comprehensive approach integrating multiple tools for robust ATM data extraction:
- Browser automation with Playwright and anti-bot measures
- OpenAI for content analysis and problem-solving
- Multiple fallback mechanisms for reliability
"""

import os
import json
import time
import random
import asyncio
import logging
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, urljoin

# OpenAI for content analysis
import openai
from openai import AsyncOpenAI

# Playwright for browser automation
from playwright.async_api import async_playwright, Page, Browser, ElementHandle, Error as PlaywrightError
from playwright_stealth import stealth_async

# For HTTP requests as fallback
import httpx
from bs4 import BeautifulSoup

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"multi_tool_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("multi_tool_scraper")

# Create necessary directories
os.makedirs("screenshots", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("debug", exist_ok=True)

# Austender URLs
BASE_URL = "https://www.tenders.gov.au"
ATM_SEARCH_URL = "https://www.tenders.gov.au/ATM/Search"

class MultiToolATMScraper:
    """Comprehensive scraper using multiple tools and fallback strategies."""
    
    def __init__(self, 
                 headless: bool = False, 
                 debug: bool = False,
                 max_retries: int = 5,
                 model: str = "gpt-4o",
                 browser_type: str = "chromium",
                 use_proxy: bool = False):
        """Initialize the multi-tool scraper with all available options."""
        self.headless = headless
        self.debug = debug
        self.max_retries = max_retries
        self.model = model
        self.browser_type = browser_type
        self.use_proxy = use_proxy
        
        # Browser state
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Tool availability flags
        self.playwright_available = True
        self.httpx_available = True
        
        # Configure debug mode
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Setup OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required in .env file")
        
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("Initialized Multi-Tool ATM Scraper")
    
    async def execute_with_fallbacks(self):
        """Execute ATM extraction with multiple fallback strategies."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {"timestamp": timestamp, "success": False, "data": []}
        
        try:
            # Strategy 1: Playwright with stealth mode
            if self.playwright_available:
                logger.info("Trying Strategy 1: Playwright with stealth mode")
                try:
                    await self.setup_playwright()
                    await self.navigate_to_atm_page()
                    
                    # Take screenshot for verification
                    screenshot_path = f"screenshots/strategy1_{timestamp}.png"
                    await self.page.screenshot(path=screenshot_path)
                    
                    # Analyze with AI
                    analysis = await self.analyze_with_ai(screenshot_path)
                    logger.info(f"AI Analysis: {analysis[:100]}...")
                    
                    # Extract data if possible
                    data = await self.extract_atm_data_playwright()
                    if data:
                        logger.info(f"Strategy 1 succeeded with {len(data)} results")
                        results["success"] = True
                        results["data"] = data
                        results["method"] = "playwright_stealth"
                        return results
                    
                except Exception as e:
                    logger.error(f"Strategy 1 failed: {str(e)}")
            
            # Strategy 2: Direct HTTP requests with headers rotation
            if self.httpx_available:
                logger.info("Trying Strategy 2: Direct HTTP requests")
                try:
                    data = await self.extract_data_with_httpx()
                    if data:
                        logger.info(f"Strategy 2 succeeded with {len(data)} results")
                        results["success"] = True
                        results["data"] = data
                        results["method"] = "httpx_direct"
                        return results
                except Exception as e:
                    logger.error(f"Strategy 2 failed: {str(e)}")
            
            # Strategy 3: Try a different browser type
            if self.playwright_available:
                alt_browsers = ["firefox", "webkit"]
                for browser in alt_browsers:
                    if browser == self.browser_type:
                        continue
                        
                    logger.info(f"Trying Strategy 3: Alternative browser - {browser}")
                    try:
                        # Close existing browser if open
                        await self.close_browser()
                        
                        # Try with alternative browser
                        self.browser_type = browser
                        await self.setup_playwright()
                        await self.navigate_to_atm_page()
                        
                        # Take screenshot for verification
                        screenshot_path = f"screenshots/strategy3_{browser}_{timestamp}.png"
                        await self.page.screenshot(path=screenshot_path)
                        
                        # Extract data if possible
                        data = await self.extract_atm_data_playwright()
                        if data:
                            logger.info(f"Strategy 3 succeeded with {browser} browser - {len(data)} results")
                            results["success"] = True
                            results["data"] = data
                            results["method"] = f"playwright_{browser}"
                            return results
                    except Exception as e:
                        logger.error(f"Strategy 3 with {browser} failed: {str(e)}")
            
            logger.warning("All strategies failed to extract ATM data")
            return results
            
        finally:
            await self.close_browser()
    
    async def setup_playwright(self):
        """Set up Playwright browser with anti-bot measures."""
        if self.browser:
            await self.close_browser()
            
        self.playwright = await async_playwright().start()
        browser_launcher = getattr(self.playwright, self.browser_type)
        
        # Browser launch options
        launch_options = {
            "headless": self.headless,
            "slow_mo": 50,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials"
            ]
        }
        
        self.browser = await browser_launcher.launch(**launch_options)
        
        # Context options with anti-bot measures
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": self.get_random_user_agent(),
            "locale": "en-AU",
            "timezone_id": "Australia/Sydney",
            "geolocation": {"latitude": -33.865143, "longitude": 151.2099},
            "permissions": ["geolocation"],
            "bypass_csp": True,
            "extra_http_headers": {
                "Accept-Language": "en-AU,en-US;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache"
            }
        }
        
        # Add proxy if configured
        if self.use_proxy:
            proxy_url = os.getenv("PROXY_SERVER")
            if proxy_url:
                context_options["proxy"] = {"server": proxy_url}
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        
        # Apply stealth mode
        await stealth_async(self.page)
        
        # Add evasion scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ]
            });
        """)
        
        logger.info(f"Playwright setup complete with {self.browser_type} browser")
    
    async def navigate_to_atm_page(self):
        """Navigate to ATM search page with human-like behavior."""
        logger.info("Navigating to ATM search page")
        
        # First visit the main page
        await self.page.goto(BASE_URL)
        await self.simulate_human_behavior()
        
        # Then try to find and click ATM link
        try:
            selectors = [
                "a[href*='ATM/Search']", 
                "a:text('ATM')", 
                "nav a:has-text('ATM')"
            ]
            
            clicked = False
            for selector in selectors:
                try:
                    # Check if element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        await element.hover()
                        await asyncio.sleep(random.uniform(0.2, 0.5))
                        await element.click()
                        clicked = True
                        break
                except Exception as e:
                    logger.debug(f"Failed to click {selector}: {str(e)}")
            
            # Fallback to direct navigation if clicking failed
            if not clicked:
                logger.info("Direct navigation to ATM search page")
                await self.page.goto(ATM_SEARCH_URL)
            
            # Wait for page to load
            await asyncio.sleep(random.uniform(2.0, 3.0))
            
        except Exception as e:
            logger.error(f"Error navigating to ATM page: {str(e)}")
            # Last resort fallback
            await self.page.goto(ATM_SEARCH_URL)
    
    async def extract_atm_data_playwright(self):
        """Extract ATM data using Playwright."""
        results = []
        
        try:
            # Search for ATMs if keyword provided
            if hasattr(self, 'keyword') and self.keyword:
                await self.search_atms(self.keyword, self.state if hasattr(self, 'state') else None)
            
            # Try to find ATM table rows with multiple selector strategies
            selectors = [
                "table.searchResults tr[class^='row']",
                ".results-table tbody tr",
                "table#ATMSearchResults tr",
                "table tr.atm-result-row",
                "table tbody tr[data-atmid]",
                "table tr:has(td a[href*='ATM/View'])"
            ]
            
            for selector in selectors:
                logger.debug(f"Trying selector: {selector}")
                rows = await self.page.query_selector_all(selector)
                
                if len(rows) > 0:
                    logger.info(f"Found {len(rows)} rows with selector: {selector}")
                    
                    # Extract data from rows
                    for row in rows:
                        try:
                            # Get all cells
                            cells = await row.query_selector_all("td")
                            
                            # Skip rows with insufficient cells
                            if len(cells) < 3:
                                continue
                            
                            # Basic extraction
                            atm_id = await cells[0].text_content() if len(cells) > 0 else ""
                            agency = await cells[1].text_content() if len(cells) > 1 else ""
                            title = await cells[2].text_content() if len(cells) > 2 else ""
                            
                            # Extract URL if available
                            url = ""
                            link = await row.query_selector("a[href*='ATM/View']")
                            if link:
                                href = await link.get_attribute("href")
                                url = urljoin(BASE_URL, href) if href else ""
                            
                            results.append({
                                "ATM ID": atm_id.strip(),
                                "Agency": agency.strip(),
                                "Title": title.strip(),
                                "URL": url
                            })
                        except Exception as e:
                            logger.debug(f"Error extracting row data: {str(e)}")
                    
                    # If we found data, stop trying different selectors
                    if results:
                        break
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting ATM data with Playwright: {str(e)}")
            return []
    
    async def search_atms(self, keyword, state=None):
        """Perform ATM search with provided criteria."""
        try:
            logger.info(f"Searching for ATMs with keyword: {keyword}, state: {state}")
            
            # Try to find and fill keyword field
            keyword_selectors = ["#keyword", "input[name='keyword']", "input[placeholder*='keyword']"]
            for selector in keyword_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    await element.fill(keyword)
                    logger.debug(f"Filled keyword using selector: {selector}")
                    break
            
            # Try to select state if provided
            if state:
                state_selectors = ["select#Location", "select[name='Location']"]
                for selector in state_selectors:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.select_option(state)
                        logger.debug(f"Selected state using selector: {selector}")
                        break
            
            # Submit search form
            submit_selectors = ["input[value='Search']", "button[type='submit']", "button:has-text('Search')"]
            for selector in submit_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    # Some human-like delay
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    await element.click()
                    logger.debug(f"Clicked search using selector: {selector}")
                    
                    # Wait for results to load
                    await asyncio.sleep(random.uniform(2.0, 3.0))
                    break
            
            # Take screenshot of results
            screenshot_path = f"screenshots/search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self.page.screenshot(path=screenshot_path)
            
        except Exception as e:
            logger.error(f"Error performing ATM search: {str(e)}")
    
    async def extract_data_with_httpx(self):
        """Extract data using direct HTTP requests as fallback."""
        results = []
        
        try:
            headers = {
                "User-Agent": self.get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-AU,en-US;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }
            
            # Use proxy if configured
            proxies = None
            if self.use_proxy:
                proxy_url = os.getenv("PROXY_SERVER")
                if proxy_url:
                    proxies = {"http://": proxy_url, "https://": proxy_url}
            
            # First get the main page to establish cookies
            async with httpx.AsyncClient(headers=headers, proxies=proxies, follow_redirects=True) as client:
                logger.info("Making initial request to Austender homepage")
                response = await client.get(BASE_URL, timeout=30.0)
                
                if response.status_code != 200:
                    logger.warning(f"Initial request failed with status {response.status_code}")
                    return []
                
                # Small delay to simulate human browsing
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # Now request the ATM search page
                logger.info("Requesting ATM search page")
                response = await client.get(ATM_SEARCH_URL, timeout=30.0)
                
                if response.status_code != 200:
                    logger.warning(f"ATM page request failed with status {response.status_code}")
                    return []
                
                # Save the HTML for debugging
                if self.debug:
                    with open(f"debug/atm_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", "w", encoding="utf-8") as f:
                        f.write(response.text)
                
                # Parse the response
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Look for tables that might contain ATM data
                tables = soup.select("table.searchResults, .results-table, table#ATMSearchResults")
                
                if not tables:
                    logger.warning("No ATM tables found in the response")
                    return []
                
                # Process the first table we find
                table = tables[0]
                rows = table.select("tr")
                
                for row in rows[1:]:  # Skip header row
                    cells = row.select("td")
                    if len(cells) < 3:
                        continue
                    
                    atm_id = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                    agency = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    title = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    
                    # Extract URL if available
                    url = ""
                    link = row.select_one("a[href*='ATM/View']")
                    if link and link.has_attr("href"):
                        url = urljoin(BASE_URL, link["href"])
                    
                    results.append({
                        "ATM ID": atm_id,
                        "Agency": agency,
                        "Title": title,
                        "URL": url
                    })
                
                logger.info(f"Extracted {len(results)} results with direct HTTP request")
                return results
                
        except Exception as e:
            logger.error(f"Error extracting data with HTTPX: {str(e)}")
            return []
    
    async def analyze_with_ai(self, image_path):
        """Analyze screenshot with OpenAI vision model."""
        try:
            # Read the image file
            with open(image_path, "rb") as img_file:
                import base64
                img_data = base64.b64encode(img_file.read()).decode("utf-8")
            
            # Call OpenAI API with the image
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert web scraper assistant. Analyze this Austender website screenshot and provide insights about the page structure, any errors, and suggestions for extracting data."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Analyze this screenshot from Austender website:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                    ]}
                ],
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error analyzing image with AI: {str(e)}")
            return f"Error analyzing image: {str(e)}"
    
    async def simulate_human_behavior(self):
        """Simulate realistic human browsing behavior."""
        try:
            # Get viewport dimensions
            dimensions = await self.page.evaluate("""
                () => ({
                    width: document.documentElement.clientWidth,
                    height: document.documentElement.clientHeight
                })
            """)
            
            # Random mouse movements
            for _ in range(random.randint(3, 6)):
                x = random.randint(100, dimensions["width"] - 200)
                y = random.randint(100, dimensions["height"] - 200)
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Random scrolling behavior
            scroll_amount = random.randint(300, 800)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.8, 1.5))
            
            # Sometimes scroll back up a bit
            if random.random() > 0.5:
                await self.page.evaluate(f"window.scrollBy(0, {-random.randint(100, 300)})")
                await asyncio.sleep(random.uniform(0.5, 1.0))
            
        except Exception as e:
            logger.debug(f"Error simulating human behavior: {str(e)}")
    
    def get_random_user_agent(self):
        """Get a random user agent to avoid detection."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42"
        ]
        return random.choice(user_agents)
    
    async def close_browser(self):
        """Close browser and release resources."""
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
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")

async def main():
    """Main function to run the multi-tool scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Tool ATM Scraper for Austender")
    parser.add_argument("--keyword", type=str, help="Keyword to search for ATMs")
    parser.add_argument("--state", type=str, help="State to filter by (e.g., NSW)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--proxy", action="store_true", help="Use proxy if configured in environment")
    parser.add_argument("--browser", type=str, choices=["chromium", "firefox", "webkit"], 
                       default="chromium", help="Browser to use")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = MultiToolATMScraper(
        headless=args.headless,
        debug=args.debug,
        browser_type=args.browser,
        use_proxy=args.proxy
    )
    
    # Set search parameters if provided
    if args.keyword:
        scraper.keyword = args.keyword
    if args.state:
        scraper.state = args.state
    
    try:
        # Execute with fallbacks
        print(f"\n{'=' * 60}")
        print("MULTI-TOOL AUSTENDER ATM SCRAPER")
        print(f"{'=' * 60}")
        print(f"Starting extraction with multiple fallback strategies")
        if args.keyword:
            print(f"Search keyword: {args.keyword}")
        if args.state:
            print(f"State filter: {args.state}")
        print(f"{'=' * 60}\n")
        
        results = await scraper.execute_with_fallbacks()
        
        # Process and save results
        if results["success"] and results["data"]:
            data_count = len(results["data"])
            print(f"\nSuccessfully extracted {data_count} ATM listings using {results['method']}")
            
            # Display preview
            for i, item in enumerate(results["data"][:3]):
                print(f"\n--- Item {i+1} ---")
                for key, value in item.items():
                    if key != "URL" or args.debug:
                        print(f"{key}: {value}")
            
            if data_count > 3:
                print(f"\n... and {data_count - 3} more items")
            
            # Save results
            output_file = args.output if args.output else f"output/atm_results_{results['timestamp']}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results["data"], f, indent=2)
            print(f"\nResults saved to {output_file}")
            
        else:
            print("\nNo ATM listings could be extracted.")
            print("Consider trying again later or with different parameters.")
        
        print(f"\n{'=' * 60}")
        print("EXECUTION COMPLETE")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"\nError in execution: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
            
    finally:
        if hasattr(scraper, 'close_browser'):
            await scraper.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
