#!/usr/bin/env python3
"""
Focused ATM Scraper for Austender
---------------------------------
This script implements a focused approach specifically for ATM listings on Austender
with targeted selectors, retries, and visual verification.
"""

import os
import json
import time
import random
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# OpenAI for content analysis
import openai
from openai import AsyncOpenAI

# Playwright for browser automation
from playwright.async_api import async_playwright, Page, Browser, ElementHandle, Error as PlaywrightError

# For stealth mode and anti-detection
from playwright_stealth import stealth_async

# Image analysis for verification
from PIL import Image
import io
import base64

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"focused_atm_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("focused_atm_scraper")

# Set system-wide socket timeout
import socket
socket.setdefaulttimeout(60)  # 60 seconds timeout

# Ensure directories exist
os.makedirs("screenshots", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("debug_html", exist_ok=True)

# Austender URL
AUSTENDER_URL = "https://www.tenders.gov.au/"
ATM_SEARCH_URL = "https://www.tenders.gov.au/ATM/Search"

# List of user agents to rotate for anti-bot evasion
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42"
]

# ATM Table selectors to try in order of specificity
ATM_TABLE_SELECTORS = [
    "table.searchResults tr[class^='row']",  # Most specific, targeting row classes
    ".results-table tbody tr",               # Common pattern for results tables
    "table#ATMSearchResults tr",             # Targeting by table ID if present
    "table tr.atm-result-row",               # Custom class that might be used
    "table tbody tr[data-atmid]",            # Rows with data attributes
    "table tr:has(td a[href*='ATM/View'])"   # Functional selector targeting rows with ATM links
]

# Column header indicators to identify data structure
COLUMN_INDICATORS = [
    "ATM ID", "Agency", "Title", "Published Date", "Closing Date", 
    "Category", "Location", "ATM Type", "Status"
]

class FocusedATMScraper:
    """Focused scraper class specifically for ATM listings on Austender."""
    
    def __init__(self, 
                 headless: bool = False, 
                 slow_mo: int = 100,
                 model: str = "gpt-4o",
                 api_key: str = None,
                 max_retries: int = 5,
                 debug: bool = False):
        """Initialize the focused ATM scraper with browser settings."""
        self.headless = headless
        self.slow_mo = slow_mo
        self.opportunities = []
        self.browser = None
        self.context = None
        self.page = None
        self.max_retries = max_retries
        self.debug = debug
        
        # Set up debug mode
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            
        # Proxy configuration for rotating IPs (if available)
        self.proxy = os.getenv("PROXY_SERVER")
        
        # Additional browser rotation settings
        self.rotate_browsers = True  # Try different browser types if one fails
        
        # LLM model settings for screenshot analysis
        self.model = model
        
        # Setup OpenAI client
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key)
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key is required. Set it in the .env file or pass it as a parameter.")
            self.client = AsyncOpenAI(api_key=api_key)
            
        # Austender credentials
        self.username = os.getenv("AUSTENDER_USERNAME")
        self.password = os.getenv("AUSTENDER_PASSWORD")
        
        logger.info("Initialized Focused ATM Scraper")
    
    async def start_browser(self, browser_type: str = "chromium") -> None:
        """Start browser with anti-detection measures using specified browser type."""
        try:
            logger.info("Starting browser...")
            # Start Playwright in async mode
            self.playwright = await async_playwright().start()
            
            # Select browser type based on parameter
            browser_launcher = getattr(self.playwright, browser_type)
            
            # Launch browser with specific options to avoid detection
            self.browser = await browser_launcher.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                    "--window-size=1920,1080"  # Set consistent window size
                ]
            )
            
            # Create context with enhanced anti-detection settings
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": random.choice(USER_AGENTS),
                "bypass_csp": True,  # Bypass Content Security Policy
                "locale": "en-AU",   # Set Australian locale
                "timezone_id": "Australia/Sydney",  # Set Australian timezone
                "geolocation": {"latitude": -33.865143, "longitude": 151.2099},  # Sydney coordinates
                "permissions": ["geolocation"],
                "http_credentials": {
                    "username": self.username,
                    "password": self.password
                } if self.username and self.password else None,
                "java_script_enabled": True,
                "extra_http_headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-AU,en-US;q=0.9,en;q=0.8",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1"
                }
            }
            
            # Add proxy if configured
            if self.proxy:
                context_options["proxy"] = {"server": self.proxy}
                
            self.context = await self.browser.new_context(**context_options)
            
            # Create new page
            self.page = await self.context.new_page()
            
            # Apply stealth mode for advanced anti-bot protection
            await stealth_async(self.page)
            
            # Add custom scripts for enhanced anti-bot measures
            await self.context.add_init_script("""
                // Overwrite navigator properties to avoid detection
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                
                // Create a dummy notification API
                if (!window.Notification) {
                    window.Notification = {
                        permission: 'default',
                        requestPermission: async () => 'granted'
                    };
                }
                
                // Add consistent fingerprint properties
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin' }
                    ]
                });
            """)
            
            # Configure additional page settings
            await self.page.route('**/*.{png,jpg,jpeg,svg,gif}', lambda route: route.continue_())
            
            # Set default timeout and custom error handling
            self.page.set_default_timeout(60000)  # 60 seconds
            
            # Add event listeners for error monitoring
            self.page.on("pageerror", lambda error: logger.error(f"Page error: {error}"))
            self.page.on("console", lambda msg: logger.debug(f"Console {msg.type}: {msg.text}") if msg.type == "error" else None)
            
            logger.info("Browser started successfully")
        
        except Exception as e:
            logger.error(f"Error starting browser: {str(e)}")
            raise
    
    async def navigate_to_atm_search(self) -> bool:
        """Navigate directly to the ATM search page using a multi-stage approach to avoid detection."""
        try:
            logger.info(f"Starting multi-stage navigation to ATM search page")
            
            # First stage: Visit the main site like a normal user
            logger.info("Stage 1: Visiting main Austender site...")
            await self.page.goto(AUSTENDER_URL)
            await asyncio.sleep(random.uniform(2.5, 4.2))  # More human-like waiting
            
            # Perform some random mousemove actions to simulate human behavior
            await self.simulate_human_behavior()
            
            # Second stage: Look for ATM link and click it instead of direct navigation
            logger.info("Stage 2: Looking for ATM navigation elements...")
            
            # Define navigation methods as regular async functions for clarity
            async def method1():
                return await self.try_click("a[href*='ATM/Search'], a:text('ATM'), nav a:has-text('ATM')")
                
            async def method2():
                return await self.navigate_through_menus()
                
            async def method3():
                await self.page.goto(ATM_SEARCH_URL)
                return True
                
            # List of methods to try in sequence
            nav_methods = [method1, method2, method3]
            
            # Try each navigation method in sequence
            for i, method in enumerate(nav_methods):
                try:
                    logger.debug(f"Trying navigation method {i+1}...")
                    await method()
                    await asyncio.sleep(random.uniform(1.5, 3))
                    
                    # Check if we reached ATM page
                    current_url = self.page.url
                    page_title = await self.page.title()
                    if "ATM/Search" in current_url or (page_title and "ATM" in page_title):
                        logger.info(f"Successfully reached ATM page using method {i+1}")
                        break
                except Exception as e:
                    logger.debug(f"Navigation method {i+1} failed: {str(e)}")
                    if i == len(nav_methods) - 1:
                        raise  # Re-raise if last method
                    await asyncio.sleep(1)  # Brief pause before trying next method
            
            # Take a screenshot for verification
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/atm_search_page_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Save HTML for debugging
            if self.debug:
                html_content = await self.page.content()
                with open(f"debug_html/atm_search_page_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
            
            # Verify we're on the ATM search page
            url = self.page.url
            title = await self.page.title()
            logger.info(f"Current page: {url} - Title: {title}")
            
            return "ATM/Search" in url or "ATM" in title
            
        except Exception as e:
            logger.error(f"Error navigating to ATM search: {str(e)}")
            return False
    
    async def search_atm(self, keyword: str = None, state: str = None) -> bool:
        """Perform ATM search with given criteria."""
        try:
            logger.info(f"Searching ATMs with keyword: {keyword}, state: {state}")
            
            # Clear any existing filters first
            try:
                clear_button = await self.page.query_selector("input[value='Clear']")
                if clear_button:
                    await clear_button.click()
                    await asyncio.sleep(random.uniform(1, 2))
            except Exception as e:
                logger.warning(f"Error clearing filters: {str(e)}")
            
            # Fill keyword if provided
            if keyword:
                try:
                    # Try multiple possible selectors for keyword field
                    for selector in ["#keyword", "input[name='keyword']", "input[placeholder*='keyword']"]:
                        keyword_field = await self.page.query_selector(selector)
                        if keyword_field:
                            await keyword_field.fill(keyword)
                            logger.info(f"Filled keyword: {keyword}")
                            break
                except Exception as e:
                    logger.error(f"Error filling keyword: {str(e)}")
            
            # Select state if provided
            if state:
                try:
                    # Try multiple possible selectors for state dropdown
                    for selector in ["select#Location", "select[name='Location']", "select[aria-label*='Location']"]:
                        state_dropdown = await self.page.query_selector(selector)
                        if state_dropdown:
                            await state_dropdown.select_option(state)
                            logger.info(f"Selected state: {state}")
                            break
                except Exception as e:
                    logger.error(f"Error selecting state: {str(e)}")
            
            # Click search button
            try:
                # Try multiple possible selectors for search button
                for selector in ["input[value='Search']", "button[type='submit']", "button:has-text('Search')"]:
                    search_button = await self.page.query_selector(selector)
                    if search_button:
                        # Add a human-like delay before clicking
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        await search_button.click()
                        logger.info("Clicked search button")
                        
                        # Wait for navigation or content to load
                        await self.page.wait_for_load_state("networkidle")
                        break
            except Exception as e:
                logger.error(f"Error clicking search: {str(e)}")
                return False
            
            # Take a screenshot after search
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/atm_search_results_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"Search results screenshot saved: {screenshot_path}")
            
            # Save HTML for debugging
            if self.debug:
                html_content = await self.page.content()
                with open(f"debug_html/atm_search_results_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
            
            return True
            
        except Exception as e:
            logger.error(f"Error searching ATM: {str(e)}")
            return False
    
    async def extract_atm_listings(self) -> List[Dict[str, str]]:
        """Extract ATM listings using multiple fallback selectors."""
        listings = []
        
        try:
            logger.info("Extracting ATM listings from search results...")
            
            # Wait for results to stabilize
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # Additional wait for any JS rendering
            
            # Take a screenshot for verification
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/atm_listings_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Try all selectors in order until we find matching elements
            working_selector = None
            rows = []
            
            for selector in ATM_TABLE_SELECTORS:
                logger.debug(f"Trying selector: {selector}")
                rows = await self.page.query_selector_all(selector)
                count = len(rows)
                logger.debug(f"Found {count} elements with selector: {selector}")
                
                if count > 0:
                    working_selector = selector
                    logger.info(f"Found {count} ATM listings with selector: {selector}")
                    break
            
            if not working_selector:
                logger.warning("No ATM listings found with any selector!")
                
                # Analyze HTML structure to debug
                if self.debug:
                    html_content = await self.page.content()
                    with open(f"debug_html/atm_listings_failed_{timestamp}.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    
                    # Use screenshot analysis to help debug
                    analysis = await self.analyze_screenshot_with_ai(screenshot_path)
                    logger.info(f"AI Screenshot Analysis: {analysis}")
                
                return []
            
            # Determine table structure - can be either data-attributes or traditional cells
            if "data-atmid" in working_selector or await self.page.query_selector(f"{working_selector}[data-atmid]"):
                # Using data attributes for extraction
                for row in rows:
                    try:
                        atm_id = await row.get_attribute("data-atmid") or ""
                        agency = await row.get_attribute("data-agency") or ""
                        title = await row.get_attribute("data-title") or ""
                        published = await row.get_attribute("data-published") or ""
                        closing = await row.get_attribute("data-closing") or ""
                        category = await row.get_attribute("data-category") or ""
                        location = await row.get_attribute("data-location") or ""
                        
                        # Extract URL if possible
                        atm_link = await row.query_selector("a[href*='ATM/View']")
                        url = await atm_link.get_attribute("href") if atm_link else ""
                        
                        listings.append({
                            "ATM ID": atm_id,
                            "Agency": agency,
                            "Title": title,
                            "Published Date": published,
                            "Closing Date": closing,
                            "Category": category,
                            "Location": location,
                            "URL": url
                        })
                    except Exception as e:
                        logger.error(f"Error extracting data attributes: {str(e)}")
            else:
                # Traditional cell-based extraction
                for row in rows:
                    try:
                        cells = await row.query_selector_all("td")
                        
                        # Skip header row or rows with no cells
                        if len(cells) < 3:
                            continue
                        
                        # Extract data from cells
                        atm_id_cell = cells[0] if len(cells) > 0 else None
                        agency_cell = cells[1] if len(cells) > 1 else None
                        title_cell = cells[2] if len(cells) > 2 else None
                        published_cell = cells[3] if len(cells) > 3 else None
                        closing_cell = cells[4] if len(cells) > 4 else None
                        
                        # Extract text content
                        atm_id = await atm_id_cell.text_content() if atm_id_cell else ""
                        agency = await agency_cell.text_content() if agency_cell else ""
                        title = await title_cell.text_content() if title_cell else ""
                        published = await published_cell.text_content() if published_cell else ""
                        closing = await closing_cell.text_content() if closing_cell else ""
                        
                        # Extract URL if available
                        atm_link = await row.query_selector("a[href*='ATM/View']")
                        url = await atm_link.get_attribute("href") if atm_link else ""
                        
                        listings.append({
                            "ATM ID": atm_id.strip(),
                            "Agency": agency.strip(),
                            "Title": title.strip(),
                            "Published Date": published.strip(),
                            "Closing Date": closing.strip(),
                            "URL": url
                        })
                    except Exception as e:
                        logger.error(f"Error extracting row data: {str(e)}")
            
            logger.info(f"Successfully extracted {len(listings)} ATM listings")
            
            # Save listings to file
            output_file = f"output/atm_listings_{timestamp}.json"
            with open(output_file, "w") as f:
                json.dump(listings, f, indent=2)
            logger.info(f"Saved listings to {output_file}")
            
            return listings
            
        except Exception as e:
            logger.error(f"Error extracting ATM listings: {str(e)}")
            return []
    
    async def simulate_human_behavior(self) -> None:
        """Simulate realistic human browsing behavior to avoid bot detection."""
        try:
            # Get page dimensions
            dimensions = await self.page.evaluate("""
                () => {
                    return {
                        width: document.documentElement.clientWidth,
                        height: document.documentElement.clientHeight
                    }
                }
            """)
            
            # Simulate random mouse movements
            for _ in range(random.randint(3, 8)):
                x = random.randint(100, dimensions['width'] - 200)
                y = random.randint(100, dimensions['height'] - 200)
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Random scrolling
            scroll_length = random.randint(300, 1000)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_length})")
            await asyncio.sleep(random.uniform(0.8, 1.5))
            
            # Sometimes scroll back up a bit
            if random.random() > 0.6:
                await self.page.evaluate(f"window.scrollBy(0, {-random.randint(100, 300)})")
                await asyncio.sleep(random.uniform(0.5, 1.2))
                
        except Exception as e:
            logger.debug(f"Error simulating human behavior: {str(e)}")
    
    async def try_click(self, selector: str) -> bool:
        """Try to click an element using multiple selectors."""
        selectors = selector.split(", ")
        for sel in selectors:
            try:
                element = await self.page.query_selector(sel)
                if element:
                    # Scroll element into view
                    await element.scroll_into_view_if_needed()
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    
                    # Move mouse to element and click
                    await element.hover()
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    await element.click()
                    return True
            except Exception as e:
                logger.debug(f"Failed to click {sel}: {str(e)}")
        return False
    
    async def navigate_through_menus(self) -> bool:
        """Navigate through menu dropdowns if direct links aren't available."""
        try:
            # First try to find and expand menu items that might contain ATM
            menu_selectors = [
                "li.has-dropdown a, button.dropdown-toggle, .nav-item.dropdown",
                ".menu-item-has-children, .nav-item:has(ul), .dropdown",
                "nav .has-submenu, header .nav-link"
            ]
            
            for selector in menu_selectors:
                menu_items = await self.page.query_selector_all(selector)
                for item in menu_items:
                    try:
                        # Check text content for relevant keywords
                        text = await item.text_content()
                        if text and any(keyword in text.lower() for keyword in ["atm", "tender", "opportunity", "market", "search"]):
                            await item.hover()
                            await asyncio.sleep(random.uniform(0.5, 1.0))
                            await item.click()
                            await asyncio.sleep(random.uniform(0.8, 1.2))
                            
                            # Now look for ATM link in the expanded menu
                            atm_link = await self.page.query_selector(
                                "a[href*='ATM/Search'], a:text('ATM'), li a:has-text('Advanced')"
                            )
                            if atm_link:
                                await atm_link.click()
                                return True
                    except Exception as e:
                        continue  # Try next menu item
            return False
        except Exception as e:
            logger.debug(f"Error navigating through menus: {str(e)}")
            return False
            
    async def analyze_screenshot_with_ai(self, screenshot_path: str) -> str:
        """Use AI to analyze screenshot content for debugging."""
        try:
            logger.info(f"Analyzing screenshot with AI: {screenshot_path}")
            
            # Read the image file
            with open(screenshot_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode("utf-8")
            
            # Call OpenAI API with the image
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert web scraper assistant specializing in government websites like Austender. Analyze this screenshot and provide detailed information about what's visible, including: 1. Is this a successful page load or an error? 2. If it's a search results page, describe the table structure and suggest specific CSS selectors. 3. If it's an error page, diagnose the likely cause (e.g., site down, bot protection, access denied). 4. Recommend specific next steps for the scraper to take."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Analyze this screenshot of an Austender page and help debug our focused ATM scraper:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                    ]}
                ],
                max_tokens=800
            )
            
            analysis = response.choices[0].message.content
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing screenshot: {str(e)}")
            return f"Screenshot analysis failed: {str(e)}"
    
    async def execute_with_retries(self, function, *args, **kwargs):
        """Execute a function with retries and exponential backoff with enhanced recovery strategies."""
        browser_types = ["chromium", "firefox", "webkit"] if self.rotate_browsers else ["chromium"]
        current_browser_index = 0
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempt {attempt+1}/{self.max_retries} for {function.__name__}")
                
                # Rotate browser type for better anti-detection if previous attempts failed
                if attempt > 0 and self.rotate_browsers and current_browser_index < len(browser_types) - 1:
                    current_browser_index += 1
                    logger.info(f"Switching to {browser_types[current_browser_index]} browser for better stealth")
                    
                    # Close existing browser if there is one
                    await self.close()
                    
                    # Restart with different browser type
                    await self.start_browser(browser_type=browser_types[current_browser_index])
                    
                    # If this is a navigation function, we need to start fresh
                    if function.__name__ == "navigate_to_atm_search":
                        pass  # Just use the new browser with fresh state
                    else:
                        # Otherwise we need to navigate to the ATM search page again
                        await self.navigate_to_atm_search()
                
                # Try executing the function
                result = await function(*args, **kwargs)
                return result
                
            except PlaywrightError as e:
                logger.warning(f"Playwright error on attempt {attempt+1}: {str(e)}")
                
                # Handle specific error conditions
                error_str = str(e).lower()
                if "timeout" in error_str:
                    logger.info("Timeout detected, clearing cache and cookies before retry")
                    if self.context:
                        await self.context.clear_cookies()
                elif "target closed" in error_str or "navigation" in error_str:
                    logger.info("Page closed or navigation issue, will restart page")
                    if self.page:
                        await self.page.close()
                    if self.context:
                        self.page = await self.context.new_page()
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(1, 3)  # More variance in waiting time
                    logger.info(f"Waiting {wait_time:.2f} seconds before retrying...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
                    raise
                    
            except Exception as e:
                logger.warning(f"General error on attempt {attempt+1}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(1, 3)  # More variance in waiting time
                    logger.info(f"Waiting {wait_time:.2f} seconds before retrying...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
                    raise
    
    async def close(self) -> None:
        """Close browser and cleanup resources."""
        try:
            if self.page:
                await self.page.close()
            
            if self.context:
                await self.context.close()
            
            if self.browser:
                await self.browser.close()
            
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            
            logger.info("Browser closed and resources released")
            
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")

async def main():
    """Main function to run the focused ATM scraper."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Focused ATM Scraper for Austender")
    parser.add_argument("--keyword", type=str, default="construction", help="Keyword to search for")
    parser.add_argument("--state", type=str, help="State to filter by (e.g., NSW, VIC)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--output", type=str, help="Custom output filename (default is timestamped)")
    parser.add_argument("--retries", type=int, default=5, help="Maximum number of retries for operations")
    parser.add_argument("--proxy", type=str, help="Proxy server to use (format: http://user:pass@host:port)")
    parser.add_argument("--no-browser-rotation", action="store_true", help="Disable browser type rotation on retries")
    parser.add_argument("--browser-type", type=str, choices=["chromium", "firefox", "webkit"], default="chromium", help="Browser type to use")
    args = parser.parse_args()
    
    # Set proxy from argument if provided
    if args.proxy:
        os.environ["PROXY_SERVER"] = args.proxy
    
    # Initialize the scraper with enhanced options
    scraper = FocusedATMScraper(
        headless=args.headless, 
        debug=args.debug,
        max_retries=args.retries
    )
    
    # Disable browser rotation if requested
    if args.no_browser_rotation:
        scraper.rotate_browsers = False
    
    try:
        # Start browser
        await scraper.start_browser()
        
        # Navigate to ATM search page
        success = await scraper.execute_with_retries(scraper.navigate_to_atm_search)
        if not success:
            logger.error("Failed to navigate to ATM search page")
            return
        
        # Perform search
        search_success = await scraper.execute_with_retries(
            scraper.search_atm, 
            keyword=args.keyword, 
            state=args.state
        )
        if not search_success:
            logger.error("Failed to perform ATM search")
            return
        
        # Extract listings
        listings = await scraper.execute_with_retries(scraper.extract_atm_listings)
        
        # Output results summary
        if listings:
            logger.info(f"Successfully extracted {len(listings)} ATM listings")
            print(f"\nExtracted {len(listings)} ATM listings")
            
            # Custom output filename if provided
            if args.output:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"output/{args.output}_{timestamp}.json"
                with open(output_file, "w") as f:
                    json.dump(listings, f, indent=2)
                logger.info(f"Saved listings to custom output file: {output_file}")
        else:
            logger.warning("No ATM listings were extracted")
            print("\nNo ATM listings were extracted")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Ensure browser is closed
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
