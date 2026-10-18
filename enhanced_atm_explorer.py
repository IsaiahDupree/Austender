#!/usr/bin/env python
"""
Enhanced Austender ATM Explorer
A multi-tool integration approach to explore Austender opportunities
with anti-bot detection avoidance and resilient error handling.
"""

import os
import json
import asyncio
import random
import logging
import time
import re
import sys
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Try to import OpenAI for content analysis
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI library not available. Will use alternative methods for content analysis.")

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enhanced_explorer")

# Constants
AUSTENDER_URL = "https://www.tenders.gov.au/"
ATM_URL = "https://www.tenders.gov.au/atm"
OUTPUT_DIR = "output"

# User agents for rotation (anti-bot measure)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
]

class AntiDetectionMeasures:
    """Anti-bot detection measures"""
    
    @staticmethod
    def get_random_user_agent() -> str:
        """Get a random user agent"""
        return random.choice(USER_AGENTS)
    
    @staticmethod
    async def simulate_human_interaction(page):
        """Simulate human-like interaction patterns"""
        # Random mouse movements
        for _ in range(random.randint(2, 5)):
            await page.mouse.move(
                random.randint(100, 800),
                random.randint(100, 600)
            )
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Occasional scrolling
        if random.random() > 0.5:
            await page.evaluate("window.scrollBy(0, {})".format(random.randint(100, 500)))
            await asyncio.sleep(random.uniform(0.5, 1.5))
    
    @staticmethod
    async def add_browser_fingerprint_protection(page):
        """Add protection against browser fingerprinting"""
        await page.evaluate("""
        () => {
            // Override navigator properties
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            
            // Mask platform
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            
            // Add fake plugins
            Object.defineProperty(navigator, 'plugins', { 
                get: () => [{ name: 'Chrome PDF Plugin' }, { name: 'Chrome PDF Viewer' }, { name: 'Native Client' }]
            });
            
            // Modify canvas fingerprinting
            const originalGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type) {
                const context = originalGetContext.apply(this, arguments);
                if (type === '2d') {
                    const originalFillText = context.fillText;
                    context.fillText = function() {
                        arguments[0] = arguments[0] + ' '; // Small change to the text
                        return originalFillText.apply(this, arguments);
                    };
                }
                return context;
            };
        }
        """)

class ToolOrchestrator:
    """Manage and orchestrate multiple tools for Austender exploration"""
    
    def __init__(self, headless=False):
        """Initialize the orchestrator"""
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.opportunities = []
        self.html_content = ""
        self.anti_detection = AntiDetectionMeasures()
        
        # Ensure output directories exist
        Path("screenshots").mkdir(exist_ok=True)
        Path(OUTPUT_DIR).mkdir(exist_ok=True)
    
    async def start_browser(self):
        """Start browser with anti-detection measures"""
        logger.info("Starting browser with anti-detection measures...")
        
        try:
            playwright = await async_playwright().start()
            
            # Use anti-detection args
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-position=0,0",
                    "--ignore-certifcate-errors",
                    "--ignore-certifcate-errors-spki-list",
                    "--user-agent=" + self.anti_detection.get_random_user_agent()
                ]
            )
            
            # Create a browser context with customized settings
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=self.anti_detection.get_random_user_agent(),
                locale="en-AU",
                timezone_id="Australia/Sydney",
                # Add random geolocation for Australia
                geolocation={"latitude": -33.865143, "longitude": 151.2099}
            )
            
            # Create page with modified timeout
            self.page = await self.context.new_page()
            self.page.set_default_timeout(45000)  # 45 seconds
            
            # Apply anti-fingerprinting measures
            await self.anti_detection.add_browser_fingerprint_protection(self.page)
            
            logger.info("Browser started successfully with anti-detection measures")
            return True
        
        except Exception as e:
            logger.error(f"Error starting browser: {e}")
            return False
    
    async def stop_browser(self):
        """Stop the browser"""
        if self.browser:
            try:
                await self.browser.close()
                logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
    
    async def navigate_with_retry(self, url, max_retries=3, simulate_human=True):
        """Navigate to URL with retry and human simulation"""
        logger.info(f"Navigating to {url}")
        
        for attempt in range(max_retries):
            try:
                # Navigate with wait for load state
                await self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
                
                # Add a variable delay to appear more human-like
                delay = random.uniform(1, 3)
                await asyncio.sleep(delay)
                
                # Simulate human interaction if requested
                if simulate_human:
                    await self.anti_detection.simulate_human_interaction(self.page)
                
                # Take screenshot with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                await self.page.screenshot(path=f"screenshots/page_{timestamp}_attempt{attempt+1}.png")
                
                # Check page content for common errors
                content = await self.page.content()
                self.html_content = content
                
                # Store content for analysis
                with open(f"{OUTPUT_DIR}/page_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(content)
                
                title = await self.page.title()
                logger.info(f"Page loaded: {title}")
                
                # Check for errors
                error_terms = ["error", "404", "not found", "unavailable", "maintenance"]
                if any(term in content.lower() for term in error_terms):
                    logger.warning(f"Page may contain errors, trying again (attempt {attempt+1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(random.uniform(1, 2))
                        continue
                
                return True
                
            except PlaywrightTimeoutError:
                logger.warning(f"Timeout during navigation (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error("Navigation failed after all retries")
                    return False
                    
            except Exception as e:
                logger.error(f"Error during navigation: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    return False
        
        return False
    
    async def login(self):
        """Login to Austender"""
        logger.info("Attempting to login to Austender...")
        
        try:
            # Get credentials
            username = os.getenv("AUSTENDER_USERNAME")
            password = os.getenv("AUSTENDER_PASSWORD")
            
            if not username or not password:
                logger.error("Missing Austender credentials in .env")
                return False
            
            # Find login link using multiple strategies
            login_success = False
            
            # Strategy 1: Direct selector
            login_link = await self.page.query_selector("a:has-text('Login')")
            if login_link:
                logger.info("Found login link using 'Login' text")
                await login_link.click()
                await self.page.wait_for_load_state("networkidle")
                login_success = True
            
            # Strategy 2: JavaScript evaluation
            if not login_success:
                logger.info("Trying JavaScript approach for login link")
                login_result = await self.page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a')).filter(
                        a => a.textContent.toLowerCase().includes('login') || 
                             a.textContent.toLowerCase().includes('log in')
                    );
                    if (links.length > 0) {
                        links[0].click();
                        return true;
                    }
                    return false;
                }
                """)
                
                if login_result:
                    logger.info("Found and clicked login link via JavaScript")
                    await self.page.wait_for_load_state("networkidle")
                    login_success = True
            
            if not login_success:
                logger.error("Could not find login link")
                return False
            
            # Wait a moment and take screenshot
            await asyncio.sleep(random.uniform(1, 2))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.page.screenshot(path=f"screenshots/login_form_{timestamp}.png")
            
            # Fill credentials with human-like timing
            username_field = await self.page.query_selector("input[id*='user']")
            if username_field:
                # Type like a human, with pauses
                for char in username:
                    await username_field.type(char, delay=random.uniform(50, 150))
                    
                # Small pause between fields
                await asyncio.sleep(random.uniform(0.5, 1.2))
                
                password_field = await self.page.query_selector("input[type='password']")
                if password_field:
                    # Type password with varying speed
                    for char in password:
                        await password_field.type(char, delay=random.uniform(30, 100))
                
                    # Add small pause before submitting
                    await asyncio.sleep(random.uniform(0.8, 1.5))
                    
                    # Click the login button
                    submit_button = await self.page.query_selector("input[type='submit']")
                    if submit_button:
                        await submit_button.click()
                        await self.page.wait_for_load_state("networkidle")
                        
                        # Take screenshot after login attempt
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        await self.page.screenshot(path=f"screenshots/after_login_{timestamp}.png")
                        
                        # Check for successful login
                        welcome_text = await self.page.query_selector("text=Welcome")
                        if welcome_text:
                            logger.info("Login successful (Welcome message found)")
                            return True
                        
                        # Alternative success check - no longer on login page
                        current_url = self.page.url
                        if "login" not in current_url.lower():
                            logger.info("Login appears successful (no longer on login page)")
                            return True
                        
                        logger.warning("Login may have failed (still on login page)")
                        return False
                    else:
                        logger.error("Submit button not found")
                else:
                    logger.error("Password field not found")
            else:
                logger.error("Username field not found")
            
            return False
            
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False
    
    async def extract_opportunities(self):
        """Extract opportunities using multiple methods"""
        logger.info("Extracting opportunities using multiple methods...")
        all_opportunities = []
        
        try:
            # Take a screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.page.screenshot(path=f"screenshots/opportunity_page_{timestamp}.png")
            
            # Method 1: Direct selector approach
            try:
                logger.info("Method 1: Using direct CSS selectors")
                
                # Try multiple likely selectors
                selectors = [
                    "a[href*='ATM/Show']",
                    "a[href*='atm/view']", 
                    "td a[href*='ATM']",
                    "tr a:not(:has-text('View'))",  # Links excluding "View" text
                    "table tbody tr a"  # All links in table rows
                ]
                
                for selector in selectors:
                    opportunity_links = await self.page.query_selector_all(selector)
                    
                    if opportunity_links and len(opportunity_links) > 0:
                        logger.info(f"Found {len(opportunity_links)} links with selector: {selector}")
                        
                        for i, link in enumerate(opportunity_links):
                            try:
                                text = await link.text_content()
                                href = await link.get_attribute("href")
                                
                                if text and href and not any(term in text.lower() for term in ['login', 'home', 'about']):
                                    # Make URL absolute if needed
                                    if not href.startswith('http'):
                                        href = "https://www.tenders.gov.au" + href
                                    
                                    opportunity = {
                                        "id": f"selector_opp_{i+1}",
                                        "title": text.strip(),
                                        "url": href,
                                        "method": "direct_selector"
                                    }
                                    
                                    all_opportunities.append(opportunity)
                                    logger.info(f"Found opportunity: {text.strip()}")
                            except Exception as e:
                                logger.warning(f"Error extracting opportunity #{i+1}: {e}")
                        
                        # If we found opportunities, no need to try more selectors
                        if all_opportunities:
                            break
                
                logger.info(f"Method 1 found {len(all_opportunities)} opportunities")
                
            except Exception as e:
                logger.warning(f"Error in Method 1: {e}")
            
            # Method 2: JavaScript evaluation for more complex extraction
            if len(all_opportunities) < 3:  # If Method 1 didn't find enough
                try:
                    logger.info("Method 2: Using JavaScript evaluation")
                    
                    js_opportunities = await self.page.evaluate("""
                    () => {
                        const results = [];
                        
                        // Look for table rows that might contain opportunities
                        const rows = Array.from(document.querySelectorAll('tr'));
                        
                        for (let i = 0; i < rows.length; i++) {
                            const row = rows[i];
                            const links = row.querySelectorAll('a');
                            
                            // Skip rows without links
                            if (links.length === 0) continue;
                            
                            // Process the main link in the row
                            for (const link of links) {
                                const text = link.textContent.trim();
                                const url = link.href;
                                
                                // Skip navigation links
                                if (['home', 'login', 'about', 'contact', 'help'].some(term => 
                                    text.toLowerCase().includes(term))) {
                                    continue;
                                }
                                
                                // Skip very short texts or non-ATM links
                                if (text.length < 5 || (!url.includes('/ATM/') && !url.includes('/atm/'))) {
                                    continue;
                                }
                                
                                // Extract cells in the row for additional data
                                const cells = Array.from(row.querySelectorAll('td')).map(td => td.textContent.trim());
                                
                                const opportunity = {
                                    id: `js_opp_${results.length + 1}`,
                                    title: text,
                                    url: url,
                                    method: 'javascript'
                                };
                                
                                // Add additional data if available
                                if (cells.length >= 2) opportunity.category = cells[1];
                                if (cells.length >= 3) opportunity.agency = cells[2];
                                if (cells.length >= 4) opportunity.date = cells[3];
                                
                                results.push(opportunity);
                                break; // Only use the first qualifying link in the row
                            }
                        }
                        
                        return results;
                    }
                    """)
                    
                    if js_opportunities and len(js_opportunities) > 0:
                        logger.info(f"Method 2 found {len(js_opportunities)} opportunities")
                        
                        # Deduplicate based on URL
                        existing_urls = [opp["url"] for opp in all_opportunities]
                        for opp in js_opportunities:
                            if opp["url"] not in existing_urls:
                                all_opportunities.append(opp)
                                existing_urls.append(opp["url"])
                
                except Exception as e:
                    logger.warning(f"Error in Method 2: {e}")
            
            # Method 3: Extract from HTML if other methods failed
            if len(all_opportunities) < 3:
                try:
                    logger.info("Method 3: Parsing from HTML content")
                    
                    # Here we would normally use a library like BeautifulSoup
                    # Since we're trying to be minimal, we'll use a simple regex approach
                    
                    # Look for ATM IDs in the HTML
                    atm_pattern = r'(ATM-\d+|ATM ID[:\s]+([A-Za-z0-9-]+))'
                    
                    # This is a simplified extraction and would be more robust with BeautifulSoup
                    for match in set(re.findall(atm_pattern, self.html_content)):
                        atm_id = match[1] if match[1] else match[0]
                        
                        # Construct URL from ATM ID
                        url = f"https://www.tenders.gov.au/ATM/Show/{atm_id}"
                        
                        # Check if already found
                        existing_urls = [opp["url"] for opp in all_opportunities]
                        if url not in existing_urls:
                            opportunity = {
                                "id": f"html_opp_{len(all_opportunities) + 1}",
                                "title": f"Opportunity {atm_id}",
                                "url": url,
                                "atm_id": atm_id,
                                "method": "html_parsing"
                            }
                            
                            all_opportunities.append(opportunity)
                    
                    logger.info(f"Method 3 found additional opportunities, total now: {len(all_opportunities)}")
                    
                except Exception as e:
                    logger.warning(f"Error in Method 3: {e}")
            
            # Save all found opportunities
            if all_opportunities:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                with open(f"{OUTPUT_DIR}/all_opportunities_{timestamp}.json", "w", encoding="utf-8") as f:
                    json.dump(all_opportunities, f, indent=2)
                
                logger.info(f"Saved {len(all_opportunities)} opportunities to file")
                self.opportunities = all_opportunities
                
                return all_opportunities
            else:
                logger.warning("No opportunities found with any method")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting opportunities: {e}")
            return []
    
    async def analyze_opportunity_details(self, opportunity):
        """Analyze details of a specific opportunity"""
        logger.info(f"Analyzing details for opportunity: {opportunity.get('title')}")
        
        try:
            # Navigate to the opportunity page
            url = opportunity.get('url')
            if not url:
                logger.error("No URL provided for opportunity")
                return opportunity
            
            # Navigate with human simulation
            if not await self.navigate_with_retry(url, simulate_human=True):
                logger.error(f"Failed to navigate to opportunity at {url}")
                return opportunity
            
            # Take a screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            opp_id = opportunity.get('id', 'unknown')
            screenshot_path = f"screenshots/opportunity_{opp_id}_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Extract additional details
            details = {
                **opportunity,
                "analyzed_at": datetime.now().isoformat(),
                "description": None,
                "closing_date": None,
                "contact": None,
                "addenda": [],
                "documents": []
            }
            
            # Extract description
            try:
                description_selectors = [
                    "div.field--name-field-description",
                    "#edit-field-description",
                    ".description",
                    "div.field--name-body"
                ]
                
                for selector in description_selectors:
                    desc_element = await self.page.query_selector(selector)
                    if desc_element:
                        description = await desc_element.text_content()
                        if description and len(description.strip()) > 0:
                            details["description"] = description.strip()
                            break
            except Exception as e:
                logger.warning(f"Error extracting description: {e}")
            
            # Extract closing date
            try:
                date_selectors = [
                    "div:has-text('Closing Date')",
                    "td:has-text('Closing Date')",
                    ".date-display-single"
                ]
                
                for selector in date_selectors:
                    date_element = await self.page.query_selector(selector)
                    if date_element:
                        date_text = await date_element.text_content()
                        details["closing_date"] = date_text.strip()
                        break
            except Exception as e:
                logger.warning(f"Error extracting closing date: {e}")
            
            # Look for addenda
            try:
                addenda_selectors = [
                    "#addenda",
                    "div:has-text('Addenda')",
                    "table:has-text('Addendum')"
                ]
                
                for selector in addenda_selectors:
                    addenda_element = await self.page.query_selector(selector)
                    if addenda_element:
                        addenda_text = await addenda_element.text_content()
                        if addenda_text and len(addenda_text.strip()) > 10:
                            details["addenda"].append({
                                "text": addenda_text.strip()
                            })
                            break
            except Exception as e:
                logger.warning(f"Error extracting addenda: {e}")
            
            # Look for document links
            try:
                doc_selectors = [
                    "a[href*='.pdf']",
                    "a[href*='.doc']",
                    "a[href*='.xls']",
                    "a[href*='download']"
                ]
                
                for selector in doc_selectors:
                    doc_links = await self.page.query_selector_all(selector)
                    if doc_links and len(doc_links) > 0:
                        for i, link in enumerate(doc_links):
                            try:
                                text = await link.text_content()
                                href = await link.get_attribute("href")
                                
                                if text and href:
                                    if not href.startswith('http'):
                                        href = "https://www.tenders.gov.au" + href
                                    
                                    details["documents"].append({
                                        "title": text.strip(),
                                        "url": href
                                    })
                            except Exception as e:
                                logger.warning(f"Error processing document #{i+1}: {e}")
            except Exception as e:
                logger.warning(f"Error extracting documents: {e}")
            
            # Save detailed analysis
            analysis_path = f"{OUTPUT_DIR}/opportunity_{opp_id}_analysis.json"
            with open(analysis_path, "w", encoding="utf-8") as f:
                json.dump(details, f, indent=2)
            
            logger.info(f"Saved detailed analysis to {analysis_path}")
            
            return details
            
        except Exception as e:
            logger.error(f"Error analyzing opportunity details: {e}")
            return opportunity
    
    async def run(self, analyze_top_n=3):
        """Run the enhanced explorer process"""
        try:
            # Start browser
            if not await self.start_browser():
                return False
            
            # Navigate to Austender
            if not await self.navigate_with_retry(AUSTENDER_URL):
                return False
            
            # Login to Austender
            login_success = await self.login()
            if not login_success:
                logger.warning("Login failed, continuing as guest")
            
            # Navigate to ATM page
            if not await self.navigate_with_retry(ATM_URL):
                return False
            
            # Extract opportunities
            opportunities = await self.extract_opportunities()
            
            if not opportunities or len(opportunities) == 0:
                logger.error("No opportunities found")
                return False
            
            # Analyze top N opportunities in detail
            detailed_opportunities = []
            
            for i, opportunity in enumerate(opportunities[:analyze_top_n]):
                logger.info(f"Analyzing opportunity {i+1}/{analyze_top_n}")
                detailed = await self.analyze_opportunity_details(opportunity)
                detailed_opportunities.append(detailed)
                
                # Add a delay between analyses
                if i < analyze_top_n - 1:
                    await asyncio.sleep(random.uniform(2, 4))
            
            # Save final results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_path = f"{OUTPUT_DIR}/detailed_opportunities_{timestamp}.json"
            
            with open(final_path, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "analyzed_count": len(detailed_opportunities),
                    "total_found": len(opportunities),
                    "opportunities": detailed_opportunities
                }, f, indent=2)
            
            logger.info(f"Analysis complete. Analyzed {len(detailed_opportunities)} of {len(opportunities)} opportunities")
            logger.info(f"Results saved to {final_path}")
            
            return detailed_opportunities
            
        except Exception as e:
            logger.error(f"Error in enhanced ATM exploration: {e}")
            return False
            
        finally:
            # Always close the browser
            await self.stop_browser()

async def main():
    """Main function"""
    print("=== Enhanced Austender ATM Explorer ===")
    print("This script uses a multi-tool approach to explore Austender opportunities")
    print("with anti-bot detection avoidance and resilient error handling\n")
    
    explorer = ToolOrchestrator(headless=False)
    results = await explorer.run(analyze_top_n=3)
    
    # Print summary
    if isinstance(results, list) and len(results) > 0:
        print(f"\nAnalyzed {len(results)} opportunities:")
        print("-" * 80)
        
        for i, opportunity in enumerate(results):
            print(f"{i+1}. {opportunity.get('title', 'Unnamed Opportunity')}")
            
            if opportunity.get('closing_date'):
                print(f"   Closing: {opportunity['closing_date']}")
                
            if opportunity.get('documents') and len(opportunity['documents']) > 0:
                print(f"   Documents: {len(opportunity['documents'])}")
                
            if opportunity.get('addenda') and len(opportunity['addenda']) > 0:
                print(f"   Addenda: Found")
                
            print(f"   URL: {opportunity.get('url', 'No URL')}")
            print("-" * 80)
        
        print(f"\nDetailed results saved to {OUTPUT_DIR}/detailed_opportunities_*.json")
    else:
        print("\nNo opportunities analyzed or error occurred.")

if __name__ == "__main__":
    asyncio.run(main())
