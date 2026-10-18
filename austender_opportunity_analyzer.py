#!/usr/bin/env python
"""
Austender Opportunity Analyzer
A tool for extracting and analyzing the latest opportunities from Austender
including addenda and attached files.
"""

import os
import json
import asyncio
import logging
import tempfile
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("austender_analyzer")

# Constants
AUSTENDER_URL = "https://www.tenders.gov.au/"
# Multiple URLs to try for finding opportunities
OPPORTUNITY_URLS = [
    "https://www.tenders.gov.au/atm/search/open",             # Open ATMs (most reliable)
    "https://www.tenders.gov.au/CN/CurrentTenders",          # Current tenders
    "https://www.tenders.gov.au/atm",                         # All ATMs
    "https://www.tenders.gov.au/ATM/ListOpenATMTenders"      # List view
]

# Keywords for targeted searches
SEARCH_KEYWORDS = [
    "construction",
    "building",
    "infrastructure",
    "bridge",
    "road",
    "engineering",
    "facility",
    "maintenance"
]

# Opportunity title blacklist to filter out navigation elements
TITLE_BLACKLIST = [
    "skip to",
    "homepage",
    "contact",
    "login",
    "about",
    "help",
    "search",
    "home",
    "menu",
    "content"
]
DOWNLOADS_DIR = "downloads"
ANALYSIS_DIR = "analysis"

class AustenderAnalyzer:
    """Class for analyzing latest opportunities on Austender"""
    
    def __init__(self, headless=False, max_opportunities=5):
        """Initialize the analyzer"""
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.opportunities = []
        self.max_opportunities = max_opportunities
        
        # Ensure output directories exist
        Path("screenshots").mkdir(exist_ok=True)
        Path(DOWNLOADS_DIR).mkdir(exist_ok=True)
        Path(ANALYSIS_DIR).mkdir(exist_ok=True)
    
    async def start(self):
        """Start the browser with anti-bot measures"""
        logger.info("Starting browser...")
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
        
        # Use random viewport and user agent for anti-bot
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            locale="en-AU",
            timezone_id="Australia/Sydney",
            # Set download path for opportunity files
            accept_downloads=True
        )
        
        self.page = await self.context.new_page()
        
        # Add more human-like behavior
        await self.page.evaluate("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        """)
        
        logger.info("Browser started successfully")
        return True
    
    async def stop(self):
        """Stop the browser"""
        if self.browser:
            await self.browser.close()
            logger.info("Browser closed")
    
    async def navigate_to(self, url):
        """Navigate to a URL with human-like timing"""
        logger.info(f"Navigating to {url}")
        
        await self.page.goto(url, wait_until="domcontentloaded")
        
        # Wait a bit like a human would
        await asyncio.sleep(2)
        
        # Take a screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshots/page_{timestamp}.png"
        await self.page.screenshot(path=screenshot_path)
        
        # Check the page title
        title = await self.page.title()
        logger.info(f"Page loaded: {title}")
        
        return True
    
    async def login(self):
        """Log in to Austender with credentials from .env file"""
        logger.info("Attempting to log in to Austender...")
        
        try:
            # Get username and password from environment variables
            username = os.getenv("AUSTENDER_USERNAME")
            password = os.getenv("AUSTENDER_PASSWORD")
            
            if not username or not password:
                logger.error("Missing Austender credentials in .env file")
                return False
            
            # Look for login link
            login_selectors = [
                "a:has-text('Log in')",
                "a:has-text('Login')",
                "a[href*='login']",
                "a[href*='auth']"
            ]
            
            # Find and click login link
            login_found = False
            for selector in login_selectors:
                try:
                    login_link = await self.page.query_selector(selector)
                    if login_link:
                        logger.info(f"Found login link with selector: {selector}")
                        await login_link.click()
                        await self.page.wait_for_load_state("networkidle")
                        login_found = True
                        break
                except Exception as e:
                    logger.warning(f"Error clicking login link with selector {selector}: {str(e)}")
            
            if not login_found:
                logger.error("Could not find login link")
                return False
            
            # Take a screenshot before login
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/before_login_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Find username and password fields
            # Try multiple selectors since the actual IDs might vary
            username_selectors = ["#username", "input[name='username']", "input[type='email']", "input[id*='user']", "input[id*='email']", "input[name*='user']", "input[name*='email']", "input[placeholder*='email']", "input[placeholder*='user']"] 
            password_selectors = ["#password", "input[name='password']", "input[type='password']", "input[id*='pass']", "input[name*='pass']", "input[placeholder*='pass']"] 
            
            # Fill in username
            username_filled = False
            for selector in username_selectors:
                try:
                    username_field = await self.page.query_selector(selector)
                    if username_field:
                        logger.info(f"Found username field with selector: {selector}")
                        await username_field.fill(username)
                        username_filled = True
                        break
                except Exception as e:
                    logger.warning(f"Error filling username with selector {selector}: {str(e)}")
            
            if not username_filled:
                logger.error("Could not find username field")
                return False
            
            # Fill in password
            password_filled = False
            for selector in password_selectors:
                try:
                    password_field = await self.page.query_selector(selector)
                    if password_field:
                        logger.info(f"Found password field with selector: {selector}")
                        await password_field.fill(password)
                        password_filled = True
                        break
                except Exception as e:
                    logger.warning(f"Error filling password with selector {selector}: {str(e)}")
            
            if not password_filled:
                logger.error("Could not find password field")
                return False
            
            # Find and click login button
            login_button_selectors = [
                "button:has-text('Login')",
                "button:has-text('Log in')",
                "button:has-text('Sign in')",
                "input[type='submit']",
                "button[type='submit']"
            ]
            
            login_clicked = False
            for selector in login_button_selectors:
                try:
                    login_button = await self.page.query_selector(selector)
                    if login_button:
                        logger.info(f"Found login button with selector: {selector}")
                        await login_button.click()
                        await self.page.wait_for_load_state("networkidle")
                        login_clicked = True
                        break
                except Exception as e:
                    logger.warning(f"Error clicking login button with selector {selector}: {str(e)}")
            
            if not login_clicked:
                logger.error("Could not find login button")
                return False
            
            # Wait for navigation after login
            await asyncio.sleep(3)
            
            # Take a screenshot after login attempt
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/after_login_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Check if login was successful
            success_indicators = [
                "text=Welcome",
                "text=Log out",
                "text=Logout",
                "text=My Account",
                "a:has-text('My Profile')",
                "a:has-text('Dashboard')"
            ]
            
            for indicator in success_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element:
                        logger.info(f"Login successful, found indicator: {indicator}")
                        return True
                except Exception:
                    pass
            
            # If we got here, let's check URL as fallback
            current_url = self.page.url
            if "login" in current_url.lower() or "auth" in current_url.lower():
                logger.warning("Still on login page, login may have failed")
                return False
            
            # No clear indicators, but not on login page
            logger.info("Login appears to be successful")
            return True
            
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False
    
    async def get_latest_opportunities(self):
        """Get the latest opportunities from Austender using multiple approaches"""
        logger.info("Getting latest opportunities using multiple approaches...")
        
        all_opportunities = []
        
        try:
            # Try each URL in our list until we find opportunities
            for url_index, url in enumerate(OPPORTUNITY_URLS):
                logger.info(f"Approach #{url_index+1}: Trying {url}")
                
                # Navigate to the URL
                await self.navigate_to(url)
                await self.page.wait_for_load_state("networkidle")
                
                # If we're on a search page, we might need to search first
                if "search" in url:
                    try:
                        # Try to fill search form if exists
                        search_terms = ["construction", "bridge", "infrastructure", "building"]
                        search_term = search_terms[url_index % len(search_terms)]
                        
                        logger.info(f"Trying search with term: {search_term}")
                        
                        # Try multiple selectors for search input
                        search_selectors = [
                            "input[name='keyword']", 
                            "#edit-keyword",
                            "input[placeholder*='search']",
                            "input[type='search']",
                            "input[id*='search']"
                        ]
                        
                        for selector in search_selectors:
                            try:
                                search_input = await self.page.query_selector(selector)
                                if search_input:
                                    logger.info(f"Found search input with selector: {selector}")
                                    await search_input.fill(search_term)
                                    
                                    # Try to find and click search button
                                    search_button_selectors = [
                                        "input[type='submit']",
                                        "button[type='submit']",
                                        "button:has-text('Search')",
                                        "input[value='Search']"
                                    ]
                                    
                                    for button_selector in search_button_selectors:
                                        try:
                                            search_button = await self.page.query_selector(button_selector)
                                            if search_button:
                                                logger.info(f"Clicking search button: {button_selector}")
                                                await search_button.click()
                                                await self.page.wait_for_load_state("networkidle")
                                                # Take a screenshot after search
                                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                                screenshot_path = f"screenshots/after_search_{url_index}_{timestamp}.png"
                                                await self.page.screenshot(path=screenshot_path)
                                                break
                                        except Exception as e:
                                            logger.warning(f"Error clicking search button {button_selector}: {str(e)}")
                                    
                                    break
                            except Exception as e:
                                logger.warning(f"Error with search input {selector}: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Error performing search on {url}: {str(e)}")
            
                # Take a screenshot of the opportunities list
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"screenshots/approach_{url_index+1}_{timestamp}.png"
                await self.page.screenshot(path=screenshot_path)
                
                # Find opportunity links for this approach
                url_opportunities = []
                
                # Various selectors to try for finding opportunity links
                selectors = [
                    ".result-title a",
                    "a[href*='ATM']",
                    "a[href*='atm/view']",
                    "a[href*='cn/view']",  # Contract Notices
                    "td a[href]",
                    "tr a[href*='view']",
                    "div.views-row a",
                    ".views-field a",
                    "h2 a",
                    "table a",
                    "a[class*='btn']",
                    "a[class*='button']"
                ]
                
                links_found = False
                for selector in selectors:
                    try:
                        opportunity_links = await self.page.query_selector_all(selector)
                        if opportunity_links and len(opportunity_links) > 0:
                            logger.info(f"Found {len(opportunity_links)} links with selector: {selector}")
                            
                            # Process all links
                            for i, link in enumerate(opportunity_links):
                                try:
                                    href = await link.get_attribute("href")
                                    text = await link.text_content()
                                    
                                    if href and text and len(text.strip()) > 5:
                                        # Filter out navigation elements and non-opportunities
                                        text_lower = text.strip().lower()
                                        
                                        # Check against blacklist
                                        blacklisted = False
                                        for blacklist_term in TITLE_BLACKLIST:
                                            if blacklist_term.lower() in text_lower:
                                                blacklisted = True
                                                break
                                        
                                        if blacklisted:
                                            continue
                                        
                                        # Check if it looks like a real opportunity
                                        is_opportunity = False
                                        
                                        # Check URL patterns that suggest it's an opportunity
                                        url_patterns = ['atm/view', 'cn/view', '/ATM/', '/CN/']
                                        for pattern in url_patterns:
                                            if pattern.lower() in href.lower():
                                                is_opportunity = True
                                                break
                                        
                                        # If URL doesn't clearly indicate an opportunity, check for keywords in title
                                        if not is_opportunity and len(text_lower) > 15:  # Real opportunities usually have longer titles
                                            # Look for procurement-related terms
                                            opp_indicators = ['tender', 'contract', 'procurement', 'opportunity', 'proposal', 
                                                              'project', 'service', 'supply', 'provision', 'delivery']
                                            
                                            for indicator in opp_indicators:
                                                if indicator.lower() in text_lower:
                                                    is_opportunity = True
                                                    break
                                        
                                        if not is_opportunity:
                                            continue
                                            
                                        # Check if it's a relative URL and make it absolute
                                        if href.startswith("/"):
                                            href = f"https://www.tenders.gov.au{href}"
                                        
                                        # Create a unique ID for this opportunity
                                        opp_id = f"opp_{url_index+1}_{i+1}"
                                        
                                        # Check if we already found this URL
                                        duplicate = False
                                        for existing_opp in all_opportunities:
                                            if existing_opp.get("url") == href:
                                                duplicate = True
                                                break
                                                
                                        if not duplicate:
                                            url_opportunities.append({
                                                "id": opp_id,
                                                "title": text.strip(),
                                                "url": href,
                                                "source": f"approach_{url_index+1}"
                                            })
                                except Exception as e:
                                    logger.warning(f"Error processing link #{i+1}: {str(e)}")
                            
                            links_found = True
                            
                            # Don't break, try all selectors to get maximum opportunities
                    except Exception as e:
                        logger.warning(f"Error finding opportunities with selector {selector}: {str(e)}")
                
                if not links_found or len(url_opportunities) == 0:
                    # Try JavaScript as a fallback for this approach
                    logger.info("Trying JavaScript to find opportunities...")
                    
                    # Create a simpler JavaScript filter without external parameters
                    js_result = await self.page.evaluate("""
                    () => {
                        // Hard-coded blacklist for filtering out navigation elements
                        const blacklistTerms = [
                            'skip to', 'homepage', 'contact', 'login', 'about',
                            'help', 'search', 'home', 'menu', 'content'
                        ];
                        
                        // Advanced selector for finding tender/opportunity links
                        const links = Array.from(document.querySelectorAll('a')).filter(a => {
                            if (!a.href || !a.textContent || a.textContent.trim().length < 5) return false;
                            
                            const href = a.href.toLowerCase();
                            const text = a.textContent.trim().toLowerCase();
                            
                            // Check against blacklist first
                            for (const term of blacklistTerms) {
                                if (text.includes(term.toLowerCase())) {
                                    return false; // Skip blacklisted items
                                }
                            }
                            
                            // Look for clear opportunity indicators in URL
                            if (href.includes('atm/view') || href.includes('cn/view') || 
                                href.includes('/atm/') || href.includes('/cn/')) {
                                return true;
                            }
                            
                            // For less clear cases, look for opportunity-related terms
                            if (text.length > 15) {  // Real opportunities usually have longer titles
                                const opportunityTerms = [
                                    'tender', 'contract', 'procurement', 'opportunity', 'proposal',
                                    'project', 'service', 'supply', 'provision', 'delivery',
                                    'construction', 'building', 'infrastructure', 'engineering'
                                ];
                                
                                for (const term of opportunityTerms) {
                                    if (text.includes(term)) {
                                        return true;
                                    }
                                }
                            }
                            
                            return false;
                        });
                        
                        return links.map((link, index) => ({
                            id: `js_opp_${index+1}`,
                            title: link.textContent.trim(),
                            url: link.href,
                            source: 'javascript'
                        }));
                    }
                    """)
                    
                    if js_result and len(js_result) > 0:
                        logger.info(f"Found {len(js_result)} opportunities via JavaScript")
                        
                        # Add non-duplicate opportunities from JS
                        for js_opp in js_result:
                            duplicate = False
                            for existing_opp in all_opportunities + url_opportunities:
                                if existing_opp.get("url") == js_opp.get("url"):
                                    duplicate = True
                                    break
                                    
                            if not duplicate:
                                url_opportunities.append(js_opp)
                
                # Add opportunities from this URL/approach to our overall list
                all_opportunities.extend(url_opportunities)
                logger.info(f"Approach #{url_index+1} found {len(url_opportunities)} opportunities")
                logger.info(f"Total unique opportunities so far: {len(all_opportunities)}")
                
                # If we have enough opportunities, we can stop trying more approaches
                if len(all_opportunities) >= self.max_opportunities:
                    logger.info(f"Found enough opportunities ({len(all_opportunities)}), stopping search")
                    break
            
            # Take the requested number of opportunities
            if len(all_opportunities) > self.max_opportunities:
                self.opportunities = all_opportunities[:self.max_opportunities]
            else:
                self.opportunities = all_opportunities
            
            logger.info(f"Final count: {len(self.opportunities)} opportunities for analysis")
            return self.opportunities
        
        except Exception as e:
            logger.error(f"Error getting latest opportunities: {str(e)}")
            return []
    
    async def analyze_opportunity(self, opportunity):
        """Analyze a single opportunity in detail"""
        logger.info(f"Analyzing opportunity: {opportunity.get('title')}")
        
        try:
            # Navigate to the opportunity page
            await self.navigate_to(opportunity.get('url'))
            
            # Wait for page to fully load
            await self.page.wait_for_load_state("networkidle")
            
            # Take a screenshot of the opportunity page
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/opportunity_{opportunity.get('id')}_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Extract basic opportunity details
            details = {
                "id": opportunity.get('id'),
                "title": opportunity.get('title'),
                "url": opportunity.get('url'),
                "atm_id": None,
                "category": None,
                "published_date": None,
                "closing_date": None,
                "addenda": [],
                "files": []
            }
            
            # Extract ATM ID
            try:
                atm_id_selectors = [
                    ".atm-id",
                    "span:has-text('ATM ID')",
                    "div:has-text('ATM ID')",
                    "td:has-text('ATM ID')"
                ]
                
                for selector in atm_id_selectors:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        # Extract ID using regex to handle various formats
                        atm_id_match = re.search(r'ATM\s*ID[:\s]*([A-Za-z0-9-]+)', text)
                        if atm_id_match:
                            details["atm_id"] = atm_id_match.group(1).strip()
                            break
            except Exception as e:
                logger.warning(f"Error extracting ATM ID: {str(e)}")
            
            # Extract key dates
            try:
                date_selectors = [
                    "div:has-text('Published Date')",
                    "div:has-text('Closing Date')",
                    "td:has-text('Published')",
                    "td:has-text('Closing')"
                ]
                
                for selector in date_selectors:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if "published" in text.lower():
                            published_match = re.search(r'published.*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text.lower(), re.IGNORECASE)
                            if published_match:
                                details["published_date"] = published_match.group(1)
                        
                        if "closing" in text.lower():
                            closing_match = re.search(r'closing.*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text.lower(), re.IGNORECASE)
                            if closing_match:
                                details["closing_date"] = closing_match.group(1)
            except Exception as e:
                logger.warning(f"Error extracting dates: {str(e)}")
            
            # Extract addenda information
            try:
                logger.info("Looking for addenda information...")
                
                # Addenda are typically in a separate section or table
                addenda_selectors = [
                    "table:has-text('Addenda')",
                    "div:has-text('Addenda')",
                    "section:has-text('Addenda')"
                ]
                
                for selector in addenda_selectors:
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found addenda section with selector: {selector}")
                        
                        # Extract all rows or items from the addenda section
                        addenda_items = await element.query_selector_all("tr, li, div.addendum")
                        
                        for i, item in enumerate(addenda_items):
                            item_text = await item.text_content()
                            if item_text and len(item_text.strip()) > 0:
                                # Extract date and description if possible
                                date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', item_text)
                                date = date_match.group(1) if date_match else None
                                
                                details["addenda"].append({
                                    "id": f"addendum_{i+1}",
                                    "date": date,
                                    "description": item_text.strip()
                                })
                        
                        logger.info(f"Extracted {len(details['addenda'])} addenda items")
                        break
            except Exception as e:
                logger.warning(f"Error extracting addenda: {str(e)}")
            
            # Extract and download document files
            try:
                logger.info("Looking for attached document files...")
                
                # Files are typically links with specific patterns
                file_selectors = [
                    "a[href*='.pdf']",
                    "a[href*='.doc']",
                    "a[href*='.xls']",
                    "a[href*='download']",
                    "a:has-text('Download')",
                    "a.document-link",
                    "a[type='application/pdf']"
                ]
                
                for selector in file_selectors:
                    file_links = await self.page.query_selector_all(selector)
                    if file_links and len(file_links) > 0:
                        logger.info(f"Found {len(file_links)} file links with selector: {selector}")
                        
                        # Create directory for this opportunity's files
                        opportunity_dir = Path(DOWNLOADS_DIR) / details.get("atm_id", opportunity.get("id"))
                        opportunity_dir.mkdir(exist_ok=True)
                        
                        for i, link in enumerate(file_links):
                            try:
                                href = await link.get_attribute("href")
                                text = await link.text_content()
                                
                                if href:
                                    # Generate a filename from the link text or href
                                    filename = text.strip() if text and len(text.strip()) > 0 else f"file_{i+1}"
                                    # Remove invalid chars from filename
                                    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
                                    # Limit filename length
                                    if len(filename) > 50:
                                        filename = filename[:47] + "..."
                                    
                                    # Try to determine file extension
                                    extension = ""
                                    if href.lower().endswith(".pdf"):
                                        extension = ".pdf"
                                    elif href.lower().endswith((".doc", ".docx")):
                                        extension = ".docx"
                                    elif href.lower().endswith((".xls", ".xlsx")):
                                        extension = ".xlsx"
                                    else:
                                        extension = ".pdf"  # Default to PDF
                                    
                                    # Add file to details
                                    file_info = {
                                        "id": f"file_{i+1}",
                                        "filename": f"{filename}{extension}",
                                        "url": href,
                                        "path": str(opportunity_dir / f"{filename}{extension}"),
                                        "downloaded": False,
                                        "analyzed": False,
                                        "content_summary": None
                                    }
                                    
                                    details["files"].append(file_info)
                                    
                                    # Try to download the file
                                    try:
                                        logger.info(f"Downloading file: {file_info['filename']}")
                                        # Click with download behavior
                                        
                                        # Create a Promise to wait for download
                                        download_promise = self.page.wait_for_download()
                                        
                                        # Click the link - use JS to avoid issues with navigation
                                        await self.page.evaluate(f"""(url) => {{
                                            const a = document.createElement('a');
                                            a.href = url;
                                            a.download = '';
                                            a.style.display = 'none';
                                            document.body.appendChild(a);
                                            a.click();
                                            document.body.removeChild(a);
                                        }}""", href)
                                        
                                        # Wait for download to complete (with timeout)
                                        download = await download_promise
                                        
                                        # Save the file
                                        await download.save_as(file_info["path"])
                                        
                                        # Mark as downloaded
                                        file_info["downloaded"] = True
                                        logger.info(f"Downloaded file to {file_info['path']}")
                                        
                                        # Add basic file analysis
                                        file_info["analyzed"] = True
                                        file_info["size_bytes"] = os.path.getsize(file_info["path"])
                                        
                                    except Exception as e:
                                        logger.warning(f"Error downloading file {file_info['filename']}: {str(e)}")
                            except Exception as e:
                                logger.warning(f"Error processing file link #{i+1}: {str(e)}")
                        
                        logger.info(f"Processed {len(details['files'])} document files")
                        break
            except Exception as e:
                logger.warning(f"Error extracting document files: {str(e)}")
            
            # Get full page content for analysis
            try:
                page_content = await self.page.content()
                
                # Save full page content
                content_path = Path(ANALYSIS_DIR) / f"{details.get('atm_id', opportunity.get('id'))}_content.html"
                with open(content_path, "w", encoding="utf-8") as f:
                    f.write(page_content)
                
                logger.info(f"Saved full page content to {content_path}")
                
                # Extract plain text content
                plain_text = await self.page.evaluate("""
                () => {
                    // Get main content area if possible
                    const main = document.querySelector('main') || document.querySelector('#main-content') || document.body;
                    return main.innerText;
                }
                """)
                
                # Save plain text content
                text_path = Path(ANALYSIS_DIR) / f"{details.get('atm_id', opportunity.get('id'))}_text.txt"
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(plain_text)
                
                logger.info(f"Saved plain text content to {text_path}")
                
                # Add text content to details
                details["content_text"] = plain_text[:1000] + "..." if len(plain_text) > 1000 else plain_text
                
            except Exception as e:
                logger.warning(f"Error extracting page content: {str(e)}")
            
            # Save the complete details to file
            analysis_path = Path(ANALYSIS_DIR) / f"{details.get('atm_id', opportunity.get('id'))}_analysis.json"
            with open(analysis_path, "w", encoding="utf-8") as f:
                json.dump(details, f, indent=2)
            
            logger.info(f"Saved opportunity analysis to {analysis_path}")
            
            # Return the detailed opportunity information
            return details
        
        except Exception as e:
            logger.error(f"Error analyzing opportunity {opportunity.get('title')}: {str(e)}")
            return opportunity
    
    async def run(self):
        """Run the full analysis process"""
        results = []
        
        try:
            # Start a browser
            if not await self.start():
                return False
            
            # Navigate to Austender homepage
            if not await self.navigate_to(AUSTENDER_URL):
                return False
            
            # Log in to Austender
            if not await self.login():
                logger.warning("Login failed, continuing as guest user...")
            else:
                logger.info("Successfully logged in to Austender")
            
            # Get the latest opportunities
            opportunities = await self.get_latest_opportunities()
            
            if not opportunities or len(opportunities) == 0:
                logger.error("No opportunities found")
                return False
            
            # Analyze each opportunity in detail
            for opportunity in opportunities:
                details = await self.analyze_opportunity(opportunity)
                results.append(details)
                
                # Take a small break between opportunities
                await asyncio.sleep(2)
            
            # Save all results to a summary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_path = Path(ANALYSIS_DIR) / f"opportunities_summary_{timestamp}.json"
            
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "opportunities_count": len(results),
                    "opportunities": results
                }, f, indent=2)
            
            logger.info(f"Analysis complete. Found {len(results)} opportunities")
            logger.info(f"Results saved to {summary_path}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error running analysis: {str(e)}")
            return False
            
        finally:
            # Always close the browser
            await self.stop()

async def main():
    """Main function"""
    print("=== Austender Opportunity Analyzer ===")
    print("This script will extract and analyze the latest opportunities from Austender")
    print("Including addenda and document files\n")
    
    # Get max opportunities from command line or use default
    max_opportunities = 3
    print(f"Analyzing up to {max_opportunities} latest opportunities\n")
    
    analyzer = AustenderAnalyzer(headless=False, max_opportunities=max_opportunities)
    results = await analyzer.run()
    
    # Print summary
    if results and len(results) > 0:
        print("\nRESULTS SUMMARY:")
        print("-" * 80)
        
        for i, result in enumerate(results):
            print(f"{i+1}. {result.get('title', 'Unnamed Opportunity')}")
            
            if result.get('atm_id'):
                print(f"   ATM ID: {result['atm_id']}")
            
            if result.get('closing_date'):
                print(f"   Closing: {result['closing_date']}")
            
            if 'addenda' in result and len(result['addenda']) > 0:
                print(f"   Addenda: {len(result['addenda'])} items")
            
            if 'files' in result and len(result['files']) > 0:
                print(f"   Files: {len(result['files'])} documents")
                downloaded = sum(1 for f in result['files'] if f.get('downloaded', False))
                print(f"   Downloaded: {downloaded} files")
            
            print("-" * 80)
        
        print(f"\nDetailed analysis saved in '{ANALYSIS_DIR}' directory")
        print(f"Downloaded files saved in '{DOWNLOADS_DIR}' directory")
    else:
        print("\nNo results found or error occurred during analysis.")

if __name__ == "__main__":
    asyncio.run(main())
