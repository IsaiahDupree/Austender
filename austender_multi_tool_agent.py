"""
Austender Multi-Tool Agent - Core Implementation
Leverages multiple tools to efficiently extract opportunities from Austender
"""

import os
import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Import the tool orchestrator
from tool_orchestrator import ToolOrchestrator, PlaywrightTool, OpenAITool

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('austender_agent')

# Constants
AUSTENDER_BASE_URL = "https://www.tenders.gov.au"
ATM_URL = f"{AUSTENDER_BASE_URL}/atm"
LOGIN_URL = f"{AUSTENDER_BASE_URL}/login"
OPPORTUNITY_URLS = [
    "https://www.tenders.gov.au/atm",
    "https://www.tenders.gov.au/atm/search"
]

class AustenderMultiToolAgent:
    """
    An enhanced agent for Austender that utilizes multiple tools for greater
    resilience and anti-bot detection avoidance.
    """
    
    def __init__(self):
        self.orchestrator = ToolOrchestrator()
        self.username = os.getenv('AUSTENDER_USERNAME')
        self.password = os.getenv('AUSTENDER_PASSWORD')
        self.output_dir = Path("output")
        self.screenshots_dir = Path("screenshots")
        
        # Create output directories if they don't exist
        self.output_dir.mkdir(exist_ok=True)
        self.screenshots_dir.mkdir(exist_ok=True)
        
        # Register tools with the orchestrator
        self.orchestrator.register_tool(PlaywrightTool())
        self.orchestrator.register_tool(OpenAITool())
        
        # For storing extracted opportunities
        self.opportunities = []
    
    async def setup(self):
        """Initialize the agent and required tools"""
        logger.info("Setting up Austender Multi-Tool Agent...")
        
        # Setup all registered tools
        results = await self.orchestrator.setup_all_tools()
        
        # Check if essential tools are available
        if not results.get('playwright', False):
            logger.error("Playwright tool is required but not available")
            return False
        
        logger.info(f"Active tools: {self.orchestrator.get_active_tools()}")
        return True
    
    async def teardown(self):
        """Clean up resources"""
        logger.info("Tearing down Austender Multi-Tool Agent...")
        await self.orchestrator.teardown_all_tools()
        logger.info("Teardown complete")
    
    async def login(self) -> bool:
        """
        Login to Austender using the provided credentials
        
        Returns:
            bool: True if login was successful, False otherwise
        """
        playwright_tool = self.orchestrator.get_tool('playwright')
        if not playwright_tool:
            logger.error("Playwright tool not available for login")
            return False
        
        page = playwright_tool.page
        if not page:
            logger.error("Playwright page not initialized")
            return False
        
        logger.info("Attempting to login to Austender...")
        
        try:
            # Navigate to the homepage
            await page.goto(AUSTENDER_BASE_URL, wait_until="networkidle")
            logger.info(f"Page loaded: {await page.title()}")
            
            # Take screenshot of the page before login
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await page.screenshot(path=str(self.screenshots_dir / f"before_login_{timestamp}.png"))
            
            # Find and click the login link - trying different approaches
            login_link_found = False
            
            # Approach 1: Look for login text
            try:
                login_link = page.locator("text=Login").first
                await login_link.click()
                logger.info("Found login link using 'Login' text")
                login_link_found = True
            except Exception as e:
                logger.warning(f"Could not find login link by text: {str(e)}")
            
            # Approach 2: Use a selector if approach 1 fails
            if not login_link_found:
                try:
                    await page.click("a[href*='login']")
                    logger.info("Found login link using href selector")
                    login_link_found = True
                except Exception as e:
                    logger.warning(f"Could not find login link by href: {str(e)}")
            
            # Approach 3: Navigate directly to login page if both approaches fail
            if not login_link_found:
                logger.warning("Could not find login link, navigating directly to login page")
                await page.goto(LOGIN_URL, wait_until="networkidle")
            
            # Wait for the login form to be visible
            await page.wait_for_selector("input#password", state="visible", timeout=10000)
            
            # Take a screenshot of the login form
            await page.screenshot(path=str(self.screenshots_dir / f"login_form_{timestamp}.png"))
            
            # Fill in credentials with variable typing speed to appear more human-like
            await page.fill("input#userName", self.username, timeout=5000)
            
            # Random delay between username and password entry
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            await page.fill("input#password", self.password, timeout=5000)
            
            # Add human-like delay before clicking login
            await asyncio.sleep(random.uniform(0.7, 1.3))
            
            # Submit the form
            await page.click("input[type='submit']", timeout=5000)
            
            # Wait for navigation to complete
            await page.wait_for_load_state("networkidle", timeout=30000)
            
            # Take screenshot after login attempt
            await page.screenshot(path=str(self.screenshots_dir / f"after_login_{timestamp}.png"))
            
            # Verify login success - look for welcome message or username display
            success_indicators = [
                "Welcome",
                "Log out",
                self.username,
                "My Account"
            ]
            
            # Check for any of the success indicators
            for indicator in success_indicators:
                if await page.locator(f"text='{indicator}'").count() > 0:
                    logger.info(f"Login successful ({indicator} found)")
                    return True
            
            # If no success indicators found, check for error messages
            error_selectors = [
                ".error-message",
                ".alert-danger",
                "text='Invalid username or password'"
            ]
            
            for selector in error_selectors:
                try:
                    error_element = page.locator(selector)
                    if await error_element.count() > 0:
                        error_text = await error_element.text_content()
                        logger.error(f"Login failed with error: {error_text}")
                        return False
                except:
                    pass
            
            logger.warning("Login status unclear - no success indicators or error messages found")
            return False
            
        except Exception as e:
            logger.error(f"Error during login process: {str(e)}")
            return False
    
    async def navigate_to_opportunities(self):
        """Navigate to the ATM opportunities page"""
        playwright_tool = self.orchestrator.get_tool('playwright')
        if not playwright_tool or not playwright_tool.page:
            logger.error("Playwright tool not available for navigation")
            return False
        
        page = playwright_tool.page
        logger.info(f"Navigating to {ATM_URL}")
        
        try:
            await page.goto(ATM_URL, wait_until="networkidle")
            logger.info(f"Page loaded: {await page.title()}")
            
            # Take a screenshot of the opportunities page
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await page.screenshot(path=str(self.screenshots_dir / f"opportunity_page_{timestamp}.png"))
            
            # Wait for the opportunities to load
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            return True
        except Exception as e:
            logger.error(f"Error navigating to opportunities page: {str(e)}")
            return False
    
    async def extract_opportunities(self) -> List[Dict[str, Any]]:
        """
        Extract opportunities from the ATM page using multiple methods
        
        Returns:
            List[Dict[str, Any]]: A list of extracted opportunities
        """
        playwright_tool = self.orchestrator.get_tool('playwright')
        openai_tool = self.orchestrator.get_tool('openai')
        
        if not playwright_tool or not playwright_tool.page:
            logger.error("Playwright tool not available for opportunity extraction")
            return []
        
        page = playwright_tool.page
        logger.info("Extracting opportunities using multiple methods...")
        
        all_opportunities = []
        
        # Method 1: Using direct CSS selectors
        try:
            logger.info("Method 1: Using direct CSS selectors")
            opportunity_elements = await page.locator("div.search-panel").locator("div.opportunity-result").all()
            
            if not opportunity_elements:
                # Try alternative selectors if the first one doesn't work
                opportunity_elements = await page.locator("div.opportunity-item").all()
            
            if not opportunity_elements:
                # Try another alternative selector
                opportunity_elements = await page.locator("table tr.opportunity-row").all()
            
            for element in opportunity_elements:
                try:
                    # Extract opportunity details
                    title_element = await element.locator("a.opportunity-title, a.title, td:first-child a").first
                    title = await title_element.text_content() if title_element else "Unknown Title"
                    
                    # Get the URL
                    href = await title_element.get_attribute("href") if title_element else None
                    url = f"{AUSTENDER_BASE_URL}{href}" if href and href.startswith("/") else href
                    
                    # Try to get category
                    category_element = await element.locator("div.category, td:nth-child(2)").first
                    category = await category_element.text_content() if category_element else "Unknown Category"
                    
                    # Try to get closing date
                    date_element = await element.locator("div.closing-date, td:nth-child(3)").first
                    closing_date = await date_element.text_content() if date_element else "Unknown Closing Date"
                    
                    opportunity = {
                        "title": title.strip() if title else "Unknown Title",
                        "url": url,
                        "category": category.strip() if category else "Unknown Category",
                        "closing_date": closing_date.strip() if closing_date else "Unknown Closing Date",
                        "extraction_method": "direct_css_selectors"
                    }
                    
                    all_opportunities.append(opportunity)
                except Exception as e:
                    logger.warning(f"Error extracting opportunity details with Method 1: {str(e)}")
            
            logger.info(f"Method 1 found {len(all_opportunities)} opportunities")
        except Exception as e:
            logger.warning(f"Error in Method 1: {str(e)}")
        
        # Method 2: Using JavaScript evaluation
        try:
            logger.info("Method 2: Using JavaScript evaluation")
            js_opportunities = await page.evaluate("""() => {
                // This function will run in the browser context
                const opportunities = [];
                
                // Try different selectors to find opportunity elements
                const selectors = [
                    'div.search-panel div.opportunity-result',
                    'div.opportunity-item',
                    'table tr.opportunity-row',
                    '.atm-container table tbody tr'
                ];
                
                let elements = [];
                for (const selector of selectors) {
                    const found = document.querySelectorAll(selector);
                    if (found && found.length > 0) {
                        elements = Array.from(found);
                        break;
                    }
                }
                
                // Process each element
                for (const element of elements) {
                    try {
                        // Find title and link
                        let titleElement = element.querySelector('a.opportunity-title, a.title, td:first-child a, a');
                        if (!titleElement) {
                            // If no direct link found, try to find any link
                            titleElement = element.querySelector('a');
                        }
                        
                        const title = titleElement ? titleElement.textContent.trim() : 'Unknown Title';
                        const url = titleElement ? titleElement.href : '';
                        
                        // Try to find category
                        let categoryElement = element.querySelector('div.category, td:nth-child(2)');
                        if (!categoryElement && element.children.length > 1) {
                            categoryElement = element.children[1]; // Second column might contain category
                        }
                        const category = categoryElement ? categoryElement.textContent.trim() : 'Unknown Category';
                        
                        // Try to find closing date
                        let dateElement = element.querySelector('div.closing-date, td:nth-child(3)');
                        if (!dateElement && element.children.length > 2) {
                            dateElement = element.children[2]; // Third column might contain date
                        }
                        const closingDate = dateElement ? dateElement.textContent.trim() : 'Unknown Closing Date';
                        
                        // Only add if we have at least a title or URL
                        if (title !== 'Unknown Title' || url) {
                            opportunities.push({
                                title,
                                url,
                                category,
                                closing_date: closingDate,
                                extraction_method: 'javascript_evaluation'
                            });
                        }
                    } catch (e) {
                        console.error('Error processing element:', e);
                    }
                }
                
                return opportunities;
            }""")
            
            # Filter out opportunities that are just navigation elements
            filtered_js_opportunities = [
                opp for opp in js_opportunities 
                if not any(nav_text in opp.get('title', '').lower() for nav_text in 
                          ['next', 'previous', 'page', 'first', 'last', 'navigation', 'go to'])
            ]
            
            # Add to our combined results
            for opp in filtered_js_opportunities:
                if opp not in all_opportunities:
                    all_opportunities.append(opp)
            
            logger.info(f"Method 2: Added opportunities, total now: {len(all_opportunities)}")
        except Exception as e:
            logger.warning(f"Error in Method 2: {str(e)}")
        
        # Method 3: Using OpenAI to analyze HTML content if available
        if openai_tool:
            try:
                logger.info("Method 3: Using OpenAI to analyze page content")
                
                # Get the HTML content
                html_content = await page.content()
                
                # Save HTML for debugging
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html_file = self.output_dir / f"page_content_{timestamp}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # Use OpenAI to analyze the content
                analysis_result = await openai_tool.analyze_page_content(
                    html_content=html_content,
                    task_description="""
                    Extract all tender opportunities from this Austender page.
                    For each opportunity, provide:
                    1. Title
                    2. URL (complete URL if available, or relative path)
                    3. Category/Type
                    4. Closing Date
                    5. Agency/Department (if available)
                    
                    Return the results as a JSON array of objects with the keys:
                    title, url, category, closing_date, agency
                    
                    Ignore any navigation elements or pagination controls.
                    """
                )
                
                # Process OpenAI results
                if isinstance(analysis_result, dict) and "text_analysis" in analysis_result:
                    # Try to extract JSON from text response
                    import re
                    json_match = re.search(r'```json(.+?)```', analysis_result["text_analysis"], re.DOTALL)
                    
                    if json_match:
                        try:
                            openai_opportunities = json.loads(json_match.group(1))
                            for opp in openai_opportunities:
                                opp["extraction_method"] = "openai_analysis"
                                # Fix relative URLs
                                if opp.get("url", "").startswith("/"):
                                    opp["url"] = f"{AUSTENDER_BASE_URL}{opp['url']}"
                                all_opportunities.append(opp)
                        except:
                            logger.warning("Failed to parse JSON from OpenAI response")
                    else:
                        logger.warning("No JSON found in OpenAI response")
                
                elif isinstance(analysis_result, list):
                    # If OpenAI returned a list directly
                    for opp in analysis_result:
                        if isinstance(opp, dict):
                            opp["extraction_method"] = "openai_analysis"
                            # Fix relative URLs
                            if opp.get("url", "").startswith("/"):
                                opp["url"] = f"{AUSTENDER_BASE_URL}{opp['url']}"
                            all_opportunities.append(opp)
                
                logger.info(f"Method 3: Added opportunities, total now: {len(all_opportunities)}")
            except Exception as e:
                logger.warning(f"Error in Method 3: {str(e)}")
        
        # Deduplicate opportunities based on URL or title
        deduplicated_opportunities = []
        seen_urls = set()
        seen_titles = set()
        
        for opp in all_opportunities:
            url = opp.get('url', '')
            title = opp.get('title', '')
            
            # Skip duplicates
            if url and url in seen_urls:
                continue
            if title and title in seen_titles and not url:
                continue
            
            if url:
                seen_urls.add(url)
            if title:
                seen_titles.add(title)
            
            deduplicated_opportunities.append(opp)
        
        # Store the extracted opportunities
        self.opportunities = deduplicated_opportunities
        
        # If we found very few opportunities, it may be an error
        if len(deduplicated_opportunities) < 3:
            logger.warning("Very few opportunities found, this may indicate a problem with extraction")
        
        if not deduplicated_opportunities:
            logger.warning("No opportunities found with any method")
        
        return deduplicated_opportunities
    
    async def analyze_opportunity_details(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze details of a specific opportunity
        
        Args:
            opportunity: Basic opportunity information
            
        Returns:
            Dict with enhanced opportunity details
        """
        playwright_tool = self.orchestrator.get_tool('playwright')
        openai_tool = self.orchestrator.get_tool('openai')
        
        if not playwright_tool or not playwright_tool.page:
            logger.error("Playwright tool not available for opportunity analysis")
            return opportunity
        
        page = playwright_tool.page
        url = opportunity.get('url')
        if not url:
            logger.error("No URL provided for opportunity analysis")
            return opportunity
        
        logger.info(f"Analyzing opportunity: {opportunity.get('title', 'Unknown')}")
        
        try:
            # Navigate to the opportunity page
            await page.goto(url, wait_until="networkidle")
            logger.info(f"Loaded opportunity page: {await page.title()}")
            
            # Take a screenshot
            opportunity_id = url.split('/')[-1] if '/' in url else "unknown"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = str(self.screenshots_dir / f"opportunity_{opportunity_id}_{timestamp}.png")
            await page.screenshot(path=screenshot_path)
            
            # Extract detailed information using JavaScript
            details = await page.evaluate("""() => {
                const details = {};
                
                // Basic details
                const titleElement = document.querySelector('h1, .opportunity-title, .title');
                details.title = titleElement ? titleElement.textContent.trim() : null;
                
                // Try to find agency/department
                const agencyElement = document.querySelector('.agency, .department, .organisation');
                details.agency = agencyElement ? agencyElement.textContent.trim() : null;
                
                // Try to find description
                const descriptionElement = document.querySelector('.description, .summary, .overview');
                details.description = descriptionElement ? descriptionElement.textContent.trim() : null;
                
                // Dates
                details.dates = {};
                const dateElements = document.querySelectorAll('.date, .date-label, .closing-date');
                dateElements.forEach(el => {
                    const label = el.querySelector('label, .label');
                    const value = el.querySelector('span, .value');
                    if (label && value) {
                        details.dates[label.textContent.trim()] = value.textContent.trim();
                    }
                });
                
                // Addenda
                details.addenda = [];
                const addendaElements = document.querySelectorAll('.addenda table tr, .addendum');
                addendaElements.forEach(el => {
                    const cells = el.querySelectorAll('td');
                    if (cells.length > 1) {
                        const addendum = {
                            number: cells[0] ? cells[0].textContent.trim() : null,
                            date: cells[1] ? cells[1].textContent.trim() : null,
                            description: cells[2] ? cells[2].textContent.trim() : null
                        };
                        details.addenda.push(addendum);
                    }
                });
                
                // Attached documents
                details.documents = [];
                const documentElements = document.querySelectorAll('.documents table tr, .document, a[href*=".pdf"], a[href*=".doc"]');
                documentElements.forEach(el => {
                    if (el.tagName === 'A') {
                        details.documents.push({
                            name: el.textContent.trim(),
                            url: el.href
                        });
                    } else {
                        const cells = el.querySelectorAll('td');
                        if (cells.length > 1) {
                            const docLink = cells[0] ? cells[0].querySelector('a') : null;
                            const document = {
                                name: docLink ? docLink.textContent.trim() : (cells[0] ? cells[0].textContent.trim() : null),
                                url: docLink ? docLink.href : null,
                                type: cells[1] ? cells[1].textContent.trim() : null,
                                date: cells[2] ? cells[2].textContent.trim() : null
                            };
                            details.documents.push(document);
                        }
                    }
                });
                
                return details;
            }""")
            
            # Enhance with OpenAI analysis if available
            if openai_tool:
                try:
                    # Get the HTML content
                    html_content = await page.content()
                    
                    # Use OpenAI to analyze the opportunity details
                    analysis_result = await openai_tool.analyze_page_content(
                        html_content=html_content,
                        task_description=f"""
                        Analyze this Austender opportunity page for tender ID: {opportunity_id}
                        
                        Extract comprehensive details including:
                        1. Title and ID
                        2. Agency/Department
                        3. Category/Type
                        4. All relevant dates (Published, Closing, etc.)
                        5. Description or summary
                        6. ATM details
                        7. Complete list of addenda with dates and descriptions
                        8. Complete list of attached documents with links
                        9. Contact information
                        10. Any other relevant information for a potential bidder
                        
                        Return as structured JSON.
                        """
                    )
                    
                    # Merge the OpenAI analysis with our JavaScript extraction
                    if isinstance(analysis_result, dict) and not "error" in analysis_result:
                        # If we have structured data from OpenAI
                        enhanced_details = {**details, **analysis_result}
                        details = enhanced_details
                except Exception as e:
                    logger.warning(f"Error during OpenAI analysis of opportunity: {str(e)}")
            
            # Update the opportunity with the enhanced details
            opportunity = {**opportunity, **details}
            
            # Save the detailed opportunity to file
            output_file = self.output_dir / f"opportunity_{opportunity_id}_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(opportunity, f, indent=2)
            
            logger.info(f"Saved detailed analysis to {output_file}")
            return opportunity
            
        except Exception as e:
            logger.error(f"Error analyzing opportunity details: {str(e)}")
            return opportunity
    
    async def run(self):
        """
        Main execution method for the Austender agent
        """
        try:
            # Setup the agent and tools
            if not await self.setup():
                logger.error("Failed to setup agent")
                return False
            
            # Login to Austender
            if not await self.login():
                logger.warning("Login failed, continuing as guest user...")
            
            # Navigate to opportunities page
            if not await self.navigate_to_opportunities():
                logger.error("Failed to navigate to opportunities page")
                return False
            
            # Extract opportunities
            opportunities = await self.extract_opportunities()
            if not opportunities:
                logger.error("No opportunities found")
                return False
            
            logger.info(f"Found {len(opportunities)} opportunities")
            
            # Save the list of opportunities
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            opportunities_file = self.output_dir / f"opportunities_{timestamp}.json"
            with open(opportunities_file, 'w', encoding='utf-8') as f:
                json.dump(opportunities, f, indent=2)
            
            logger.info(f"Saved opportunities list to {opportunities_file}")
            
            # Analyze the first few opportunities in detail
            detailed_opportunities = []
            for i, opp in enumerate(opportunities[:5]):  # Limit to first 5
                detailed_opp = await self.analyze_opportunity_details(opp)
                detailed_opportunities.append(detailed_opp)
                # Add a delay between requests to appear more human-like
                if i < len(opportunities[:5]) - 1:
                    await asyncio.sleep(random.uniform(2, 5))
            
            # Save detailed opportunities
            detailed_file = self.output_dir / f"detailed_opportunities_{timestamp}.json"
            with open(detailed_file, 'w', encoding='utf-8') as f:
                json.dump(detailed_opportunities, f, indent=2)
            
            logger.info(f"Saved detailed opportunities to {detailed_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during agent execution: {str(e)}")
            return False
        finally:
            # Always teardown to release resources
            await self.teardown()

async def main():
    """Main entry point"""
    print("=== Austender Multi-Tool Agent ===")
    print("Exploring opportunities using systematic multi-tool approach")
    print("with anti-bot detection avoidance and resilient error handling\n")
    
    agent = AustenderMultiToolAgent()
    success = await agent.run()
    
    if success:
        print(f"\nSuccess! Analyzed {len(agent.opportunities)} opportunities.")
        print(f"Results saved to the 'output' directory.")
    else:
        print("\nNo opportunities analyzed or error occurred.")

if __name__ == "__main__":
    asyncio.run(main())
