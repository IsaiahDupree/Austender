#!/usr/bin/env python
"""
Direct Austender Opportunity Analyzer
A more focused tool for analyzing specific Austender opportunities
with improved error handling and resilience.
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("direct_analyzer")

# Constants
AUSTENDER_URL = "https://www.tenders.gov.au/"
DOWNLOADS_DIR = "downloads"
ANALYSIS_DIR = "analysis"

# Sample opportunity URLs - these are more reliable than searching
SAMPLE_OPPORTUNITIES = [
    # Use specific ATM IDs known to exist
    "https://www.tenders.gov.au/ATM/Show/9e0311e8-8e02-eb11-80fc-00505692119a",  # Common example
    "https://www.tenders.gov.au/ATM/Show/64bda7da-5ca7-4375-bb99-9f2edb1e1cd1",  # Infrastructure/construction
    "https://www.tenders.gov.au/ATM/Show/6a99181f-f0c1-4033-8d52-ff3ed4e2cf35",  # Recent opportunity
]

class DirectOpportunityAnalyzer:
    """Class for directly analyzing specific opportunities on Austender"""
    
    def __init__(self, headless=False):
        """Initialize the analyzer"""
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.opportunities = []
        
        # Ensure output directories exist
        Path("screenshots").mkdir(exist_ok=True)
        Path(DOWNLOADS_DIR).mkdir(exist_ok=True)
        Path(ANALYSIS_DIR).mkdir(exist_ok=True)
    
    async def start(self):
        """Start the browser with anti-bot measures and increased timeouts"""
        logger.info("Starting browser...")
        
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            
            # Use random viewport and user agent with extended timeouts
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
                locale="en-AU",
                timezone_id="Australia/Sydney",
                accept_downloads=True
            )
            
            self.page = await self.context.new_page()
            
            # Modify timeout settings
            self.page.set_default_timeout(60000)  # 60 seconds timeout
            
            # Add more human-like behavior
            await self.page.evaluate("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            """)
            
            logger.info("Browser started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting browser: {e}")
            return False
    
    async def stop(self):
        """Stop the browser"""
        if self.browser:
            try:
                await self.browser.close()
                logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
    
    async def navigate_to(self, url, max_retries=3):
        """Navigate to a URL with human-like timing and retry logic"""
        logger.info(f"Navigating to {url}")
        
        for attempt in range(max_retries):
            try:
                # Use networkidle for more reliable page load detection
                await self.page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Add randomized delay to simulate human behavior
                delay = 2 + (attempt * 1.5)  # Increase delay with each retry
                await asyncio.sleep(delay)
                
                # Take a screenshot with error handling
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = f"screenshots/page_{timestamp}_{attempt}.png"
                    await self.page.screenshot(path=screenshot_path, timeout=10000)
                except Exception as e:
                    logger.warning(f"Screenshot failed but continuing: {e}")
                
                # Check the page title
                try:
                    title = await self.page.title()
                    logger.info(f"Page loaded: {title}")
                    
                    # Check if page contains common error indicators
                    content = await self.page.content()
                    error_indicators = ["404", "not found", "error", "unavailable", "maintenance"]
                    if any(indicator in content.lower() for indicator in error_indicators):
                        logger.warning(f"Page loaded but may contain errors: {title}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying navigation (attempt {attempt+2}/{max_retries})")
                            continue
                    
                    return True
                except Exception as e:
                    logger.warning(f"Error getting page title: {e}")
                    if attempt < max_retries - 1:
                        continue
            
            except PlaywrightTimeoutError:
                logger.warning(f"Timeout on navigation attempt {attempt+1}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying with longer timeout (attempt {attempt+2}/{max_retries})")
                    continue
                else:
                    logger.error("Navigation failed after all retry attempts")
                    return False
                    
            except Exception as e:
                logger.error(f"Error during navigation: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying navigation (attempt {attempt+2}/{max_retries})")
                    continue
                else:
                    logger.error("Navigation failed after all retry attempts")
                    return False
        
        return False
    
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
                        await self.page.wait_for_load_state("networkidle", timeout=30000)
                        login_found = True
                        break
                except Exception as e:
                    logger.warning(f"Error clicking login link with selector {selector}: {str(e)}")
            
            if not login_found:
                logger.error("Could not find login link")
                return False
            
            # Find username and password fields
            username_selectors = ["#username", "input[name='username']", "input[type='email']", "input[id*='user']"]
            password_selectors = ["#password", "input[name='password']", "input[type='password']"]
            
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
                        await self.page.wait_for_load_state("networkidle", timeout=30000)
                        login_clicked = True
                        break
                except Exception as e:
                    logger.warning(f"Error clicking login button with selector {selector}: {str(e)}")
            
            if not login_clicked:
                logger.error("Could not find login button")
                return False
            
            # Check if login was successful (simplified check)
            try:
                # Look for a common element that appears after successful login
                await asyncio.sleep(3)  # Wait for page transition
                
                # Check for success indicators
                success_indicators = [
                    "text=Welcome",
                    "text=Log out",
                    "text=My Account"
                ]
                
                for indicator in success_indicators:
                    try:
                        element = await self.page.query_selector(indicator)
                        if element:
                            logger.info(f"Login successful, found indicator: {indicator}")
                            return True
                    except Exception:
                        pass
                
                # If no clear indicators, check if we're still on login page
                current_url = self.page.url
                if "login" in current_url.lower():
                    logger.warning("Still on login page, login may have failed")
                    return False
                
                logger.info("Login appears to be successful")
                return True
                
            except Exception as e:
                logger.error(f"Error checking login status: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False
    
    async def analyze_opportunity(self, url):
        """Analyze a specific opportunity by direct URL"""
        logger.info(f"Analyzing opportunity at: {url}")
        
        try:
            # Extract ATM ID from URL
            atm_id = url.split("/")[-1] if url else "unknown_id"
            
            # Navigate to the opportunity page
            if not await self.navigate_to(url):
                logger.error(f"Failed to navigate to opportunity URL: {url}")
                return None
            
            # Take a screenshot of the opportunity page
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/opportunity_{atm_id}_{timestamp}.png"
            
            try:
                await self.page.screenshot(path=screenshot_path, timeout=15000)
                logger.info(f"Saved screenshot to {screenshot_path}")
            except Exception as e:
                logger.warning(f"Error taking screenshot: {e}")
            
            # Extract basic opportunity details
            details = {
                "atm_id": atm_id,
                "url": url,
                "title": None,
                "category": None,
                "published_date": None,
                "closing_date": None,
                "addenda": [],
                "files": [],
                "captured_at": datetime.now().isoformat()
            }
            
            # Get opportunity title
            try:
                title_selectors = [
                    "h1", 
                    ".page-title", 
                    ".title", 
                    "#page-title",
                    ".atm-title"
                ]
                
                for selector in title_selectors:
                    try:
                        title_element = await self.page.query_selector(selector)
                        if title_element:
                            title = await title_element.text_content()
                            if title and len(title.strip()) > 5:
                                details["title"] = title.strip()
                                logger.info(f"Found opportunity title: {details['title']}")
                                break
                    except Exception as e:
                        logger.warning(f"Error getting title with selector {selector}: {e}")
            except Exception as e:
                logger.warning(f"Error extracting title: {e}")
            
            # Extract dates and other metadata using more resilient techniques
            try:
                # Get all table cells that might contain dates
                date_elements = await self.page.query_selector_all("td, th, div.field")
                
                for element in date_elements:
                    try:
                        text = await element.text_content()
                        text_lower = text.lower()
                        
                        # Look for published date
                        if "publish" in text_lower and not details.get("published_date"):
                            # Extract date using regex or split - simplified here
                            date_parts = text_lower.split("publish")
                            if len(date_parts) > 1:
                                details["published_date"] = date_parts[1].strip()
                        
                        # Look for closing date
                        if "clos" in text_lower and not details.get("closing_date"):
                            # Extract date using regex or split - simplified here
                            date_parts = text_lower.split("clos")
                            if len(date_parts) > 1:
                                details["closing_date"] = date_parts[1].strip()
                        
                        # Look for category
                        if "category" in text_lower and not details.get("category"):
                            # Extract category
                            category_parts = text_lower.split("category")
                            if len(category_parts) > 1:
                                details["category"] = category_parts[1].strip()
                        
                    except Exception as e:
                        continue  # Skip problematic elements
            except Exception as e:
                logger.warning(f"Error extracting metadata: {e}")
            
            # Extract addenda information
            try:
                logger.info("Looking for addenda information...")
                
                # Look for sections that might contain addenda
                addenda_selectors = [
                    "#addenda",
                    ".addenda",
                    "div:has-text('Addendum')",
                    "table:has-text('Addendum')",
                    "section:has-text('Addenda')"
                ]
                
                for selector in addenda_selectors:
                    try:
                        addenda_section = await self.page.query_selector(selector)
                        if addenda_section:
                            logger.info(f"Found addenda section with selector: {selector}")
                            
                            # Extract text content
                            addenda_text = await addenda_section.text_content()
                            
                            if addenda_text and len(addenda_text) > 10:
                                # Simple extraction - in a real scenario you'd parse this more carefully
                                details["addenda"].append({
                                    "raw_text": addenda_text.strip(),
                                })
                                
                                logger.info(f"Extracted addenda information: {len(addenda_text)} characters")
                            break
                    except Exception as e:
                        logger.warning(f"Error processing addenda with selector {selector}: {e}")
            except Exception as e:
                logger.warning(f"Error extracting addenda: {e}")
            
            # Look for document files to download
            try:
                logger.info("Searching for document files...")
                
                # Create a directory for this opportunity's files
                file_dir = Path(DOWNLOADS_DIR) / atm_id
                file_dir.mkdir(exist_ok=True)
                
                # Look for download links
                file_link_selectors = [
                    "a[href*='.pdf']",
                    "a[href*='.doc']",
                    "a[href*='.xls']",
                    "a[href*='download']",
                    "a:has-text('Download')",
                    "a.document-link",
                    "a[type='application/pdf']"
                ]
                
                for selector in file_link_selectors:
                    try:
                        file_links = await self.page.query_selector_all(selector)
                        
                        if file_links and len(file_links) > 0:
                            logger.info(f"Found {len(file_links)} potential file links with selector: {selector}")
                            
                            for i, link in enumerate(file_links):
                                try:
                                    href = await link.get_attribute("href")
                                    text = await link.text_content()
                                    
                                    if href and (href.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')) or 'download' in href.lower()):
                                        file_info = {
                                            "filename": text.strip() if text and len(text.strip()) > 0 else f"file_{i+1}",
                                            "url": href,
                                            "position": i+1
                                        }
                                        
                                        details["files"].append(file_info)
                                        logger.info(f"Found file: {file_info['filename']} at {href}")
                                except Exception as e:
                                    logger.warning(f"Error processing file link #{i+1}: {e}")
                    except Exception as e:
                        logger.warning(f"Error with file selector {selector}: {e}")
                
                logger.info(f"Found {len(details['files'])} document files")
            except Exception as e:
                logger.warning(f"Error looking for document files: {e}")
            
            # Get the full HTML content
            try:
                html_content = await self.page.content()
                content_path = Path(ANALYSIS_DIR) / f"{atm_id}_content.html"
                
                with open(content_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                logger.info(f"Saved full HTML content to {content_path}")
            except Exception as e:
                logger.warning(f"Error saving HTML content: {e}")
            
            # Get the extracted text content for analysis
            try:
                text_content = await self.page.evaluate("""
                () => {
                    const mainContent = document.querySelector('main') || 
                                        document.querySelector('#main-content') || 
                                        document.querySelector('.content') || 
                                        document.body;
                    return mainContent.innerText;
                }
                """)
                
                if text_content:
                    text_path = Path(ANALYSIS_DIR) / f"{atm_id}_text.txt"
                    
                    with open(text_path, "w", encoding="utf-8") as f:
                        f.write(text_content)
                    
                    logger.info(f"Saved extracted text content to {text_path}")
                    
                    # Add a preview of the text content to the details
                    details["content_preview"] = text_content[:500] + "..." if len(text_content) > 500 else text_content
            except Exception as e:
                logger.warning(f"Error extracting text content: {e}")
            
            # Save the analysis results
            analysis_path = Path(ANALYSIS_DIR) / f"{atm_id}_analysis.json"
            
            with open(analysis_path, "w", encoding="utf-8") as f:
                json.dump(details, f, indent=2)
            
            logger.info(f"Saved analysis results to {analysis_path}")
            
            # Add to list of analyzed opportunities
            self.opportunities.append(details)
            
            return details
            
        except Exception as e:
            logger.error(f"Error analyzing opportunity {url}: {e}")
            return None
    
    async def run(self, opportunity_urls=None):
        """Run the direct opportunity analysis"""
        results = []
        
        if not opportunity_urls:
            opportunity_urls = SAMPLE_OPPORTUNITIES
        
        try:
            # Start browser
            if not await self.start():
                logger.error("Failed to start browser")
                return False
            
            # Navigate to Austender homepage
            if not await self.navigate_to(AUSTENDER_URL):
                logger.error("Failed to navigate to Austender homepage")
                return False
            
            # Try to log in, but continue even if login fails
            login_success = await self.login()
            if not login_success:
                logger.warning("Login failed or skipped, continuing as guest")
            
            # Analyze each opportunity directly
            for url in opportunity_urls:
                try:
                    result = await self.analyze_opportunity(url)
                    if result:
                        results.append(result)
                        
                        # Take a short break between opportunities
                        await asyncio.sleep(3)
                except Exception as e:
                    logger.error(f"Error processing opportunity {url}: {e}")
            
            # Save overall results
            if results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                summary_path = Path(ANALYSIS_DIR) / f"direct_opportunities_{timestamp}.json"
                
                with open(summary_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "opportunity_count": len(results),
                        "opportunities": results
                    }, f, indent=2)
                
                logger.info(f"Saved summary of {len(results)} opportunities to {summary_path}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in analysis run: {e}")
            return False
            
        finally:
            # Always close the browser
            await self.stop()

async def main():
    """Main function"""
    print("=== Direct Austender Opportunity Analyzer ===")
    print("This script will directly analyze specific Austender opportunities")
    print("Including addenda and document files\n")
    
    # You can customize the opportunity IDs to analyze here
    opportunity_urls = SAMPLE_OPPORTUNITIES
    
    print(f"Analyzing {len(opportunity_urls)} specific opportunities:")
    for i, url in enumerate(opportunity_urls):
        print(f"{i+1}. {url}")
    print()
    
    analyzer = DirectOpportunityAnalyzer(headless=False)
    results = await analyzer.run(opportunity_urls)
    
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
            
            print("-" * 80)
        
        print(f"\nDetailed analysis saved in '{ANALYSIS_DIR}' directory")
    else:
        print("\nNo results found or error occurred during analysis.")

if __name__ == "__main__":
    asyncio.run(main())
