#!/usr/bin/env python
"""
Austender ATM Opportunity Explorer
A focused script to login and explore the ATM opportunities page.
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
logger = logging.getLogger("atm_explorer")

# Constants
AUSTENDER_URL = "https://www.tenders.gov.au/"
ATM_URL = "https://www.tenders.gov.au/atm"
OUTPUT_DIR = "output"

class ATMExplorer:
    """A focused class to explore the ATM opportunities page"""
    
    def __init__(self, headless=False):
        """Initialize the explorer"""
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.opportunities = []
        
        # Ensure output directories exist
        Path("screenshots").mkdir(exist_ok=True)
        Path(OUTPUT_DIR).mkdir(exist_ok=True)
    
    async def start(self):
        """Start the browser"""
        logger.info("Starting browser...")
        
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.headless
            )
            
            # Create browser context with increased timeouts
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
            )
            
            # Create page and increase timeouts
            self.page = await self.context.new_page()
            self.page.set_default_timeout(60000)  # 60 seconds timeout
            
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
    
    async def navigate_to(self, url):
        """Navigate to a URL"""
        logger.info(f"Navigating to {url}")
        
        try:
            await self.page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)  # Wait a moment for any JavaScript to load
            
            # Take a screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/page_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Check the page title
            title = await self.page.title()
            logger.info(f"Page loaded: {title}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return False
    
    async def login(self):
        """Log in to Austender"""
        logger.info("Attempting to log in to Austender...")
        
        try:
            # Get credentials from environment
            username = os.getenv("AUSTENDER_USERNAME")
            password = os.getenv("AUSTENDER_PASSWORD")
            
            if not username or not password:
                logger.error("Missing Austender credentials in .env file")
                return False
            
            # Find and click login link
            login_link = await self.page.query_selector("a:has-text('Login')")
            if not login_link:
                logger.error("Login link not found")
                return False
                
            await login_link.click()
            await self.page.wait_for_load_state("networkidle")
            
            # Take a screenshot before entering credentials
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.page.screenshot(path=f"screenshots/before_login_{timestamp}.png")
            
            # Fill in username
            username_field = await self.page.query_selector("input[id*='user']")
            if not username_field:
                logger.error("Username field not found")
                return False
                
            await username_field.fill(username)
            
            # Fill in password
            password_field = await self.page.query_selector("input[type='password']")
            if not password_field:
                logger.error("Password field not found")
                return False
                
            await password_field.fill(password)
            
            # Click login button
            login_button = await self.page.query_selector("input[type='submit']")
            if not login_button:
                logger.error("Login button not found")
                return False
                
            await login_button.click()
            await self.page.wait_for_load_state("networkidle")
            
            # Take a screenshot after login attempt
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.page.screenshot(path=f"screenshots/after_login_{timestamp}.png")
            
            # Check if login was successful
            success_indicator = await self.page.query_selector("text=Welcome")
            if success_indicator:
                logger.info("Login successful")
                return True
            else:
                # Check for additional indicators of success
                url = self.page.url
                if "login" not in url:
                    logger.info("Login appears to be successful (not on login page)")
                    return True
                else:
                    logger.error("Login failed")
                    return False
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False
    
    async def extract_opportunities(self):
        """Extract opportunities from the ATM page"""
        logger.info("Extracting opportunities from the ATM page...")
        
        try:
            # Take a screenshot of the opportunities page
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.page.screenshot(path=f"screenshots/atm_page_{timestamp}.png")
            
            # Save the HTML for analysis
            html = await self.page.content()
            with open(f"{OUTPUT_DIR}/atm_page_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html)
            
            # Find all opportunity links
            opportunity_links = await self.page.query_selector_all("a[href*='ATM/Show']")
            if not opportunity_links:
                # Try alternative selectors if the first one doesn't work
                opportunity_links = await self.page.query_selector_all("a[href*='atm/view']")
            
            if not opportunity_links:
                # Try to find any table rows with links that might be opportunities
                opportunity_links = await self.page.query_selector_all("table tr a")
            
            if not opportunity_links:
                logger.error("No opportunity links found on the page")
                return []
            
            logger.info(f"Found {len(opportunity_links)} potential opportunity links")
            
            # Extract information for each opportunity
            opportunities = []
            
            for i, link in enumerate(opportunity_links):
                try:
                    # Get the link text and URL
                    text = await link.text_content()
                    href = await link.get_attribute("href")
                    
                    if text and href:
                        # Skip navigation links or non-opportunity links
                        if any(nav_term in text.lower() for nav_term in ['home', 'login', 'about', 'help', 'contact']):
                            continue
                        
                        # Create opportunity object
                        opportunity = {
                            "id": f"opp_{i+1}",
                            "title": text.strip(),
                            "url": href if href.startswith("http") else f"https://www.tenders.gov.au{href}"
                        }
                        
                        # Try to get more details about the opportunity from the surrounding row
                        try:
                            # Find the parent row if in a table
                            row = await link.evaluate("node => node.closest('tr')")
                            if row:
                                # Get all cells in the row
                                cells_text = await self.page.evaluate("""
                                (row) => {
                                    const cells = row.querySelectorAll('td');
                                    return Array.from(cells).map(cell => cell.textContent.trim());
                                }
                                """, row)
                                
                                if cells_text and len(cells_text) > 0:
                                    # Use extra details if available
                                    if len(cells_text) >= 2:
                                        opportunity["category"] = cells_text[1] if len(cells_text) > 1 else None
                                    
                                    if len(cells_text) >= 3:
                                        opportunity["agency"] = cells_text[2] if len(cells_text) > 2 else None
                                    
                                    if len(cells_text) >= 4:
                                        opportunity["date"] = cells_text[3] if len(cells_text) > 3 else None
                        except Exception as cell_error:
                            logger.warning(f"Error extracting additional details: {cell_error}")
                        
                        opportunities.append(opportunity)
                        logger.info(f"Extracted opportunity: {opportunity['title']}")
                        
                except Exception as e:
                    logger.warning(f"Error extracting opportunity #{i+1}: {e}")
            
            # Save the extracted opportunities to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(f"{OUTPUT_DIR}/opportunities_{timestamp}.json", "w", encoding="utf-8") as f:
                json.dump(opportunities, f, indent=2)
            
            logger.info(f"Extracted {len(opportunities)} opportunities")
            self.opportunities = opportunities
            return opportunities
            
        except Exception as e:
            logger.error(f"Error extracting opportunities: {e}")
            return []
    
    async def run(self):
        """Run the ATM exploration process"""
        try:
            # Start browser
            if not await self.start():
                return False
            
            # Navigate to Austender homepage
            if not await self.navigate_to(AUSTENDER_URL):
                return False
            
            # Log in to Austender
            login_success = await self.login()
            if not login_success:
                logger.warning("Login failed, continuing as guest")
            
            # Navigate to the ATM page
            if not await self.navigate_to(ATM_URL):
                return False
            
            # Extract opportunities
            opportunities = await self.extract_opportunities()
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error in ATM exploration: {e}")
            return False
            
        finally:
            # Always close the browser
            await self.stop()

async def main():
    """Main function"""
    print("=== Austender ATM Opportunity Explorer ===")
    print("This script will login to Austender and explore the ATM opportunities page\n")
    
    explorer = ATMExplorer(headless=False)
    opportunities = await explorer.run()
    
    # Print summary
    if opportunities and len(opportunities) > 0:
        print(f"\nFound {len(opportunities)} opportunities:")
        print("-" * 80)
        
        for i, opportunity in enumerate(opportunities):
            print(f"{i+1}. {opportunity.get('title', 'Unnamed Opportunity')}")
            
            if opportunity.get('category'):
                print(f"   Category: {opportunity['category']}")
            
            if opportunity.get('agency'):
                print(f"   Agency: {opportunity['agency']}")
            
            if opportunity.get('date'):
                print(f"   Date: {opportunity['date']}")
                
            print(f"   URL: {opportunity.get('url', 'No URL')}")
            print("-" * 80)
        
        print(f"\nOpportunities saved to {OUTPUT_DIR}/opportunities_*.json")
    else:
        print("\nNo opportunities found or error occurred.")

if __name__ == "__main__":
    asyncio.run(main())
