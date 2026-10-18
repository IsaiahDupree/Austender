#!/usr/bin/env python3
"""
Austender Scraper using Browser-Use
-----------------------------------
This script leverages the browser-use API to scrape construction opportunities
from the Australian Government's tender website (Austender) while bypassing
anti-bot measures.
"""

import requests
import json
import time
import os
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"austender_browser_use_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("austender_scraper")

# Browser-Use API configuration
BROWSER_USE_URL = "http://localhost:7788/api"
AUSTENDER_URL = "https://www.tenders.gov.au/Search/KeywordSearch?keyword=construction&type=ATM&dateType=ClosingDate"

class BrowserUseClient:
    """Client for interacting with the Browser-Use API."""
    
    def __init__(self, api_url: str = BROWSER_USE_URL):
        self.api_url = api_url
        self.session_id = None
        logger.info(f"Initialized Browser-Use client with API URL: {api_url}")
    
    def start_session(self) -> str:
        """Start a new browser session."""
        response = requests.post(f"{self.api_url}/session/start")
        if response.status_code == 200:
            data = response.json()
            self.session_id = data.get("session_id")
            logger.info(f"Started new session with ID: {self.session_id}")
            return self.session_id
        else:
            error_msg = f"Failed to start session: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def end_session(self) -> bool:
        """End the current browser session."""
        if not self.session_id:
            logger.warning("No active session to end")
            return False
        
        response = requests.post(f"{self.api_url}/session/end", json={"session_id": self.session_id})
        if response.status_code == 200:
            logger.info(f"Ended session with ID: {self.session_id}")
            self.session_id = None
            return True
        else:
            error_msg = f"Failed to end session: {response.text}"
            logger.error(error_msg)
            return False
    
    def navigate(self, url: str) -> Dict:
        """Navigate to a URL."""
        if not self.session_id:
            self.start_session()
        
        payload = {
            "session_id": self.session_id,
            "url": url
        }
        
        response = requests.post(f"{self.api_url}/navigation/navigate", json=payload)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Navigated to: {url}")
            return data
        else:
            error_msg = f"Failed to navigate to {url}: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_html(self) -> str:
        """Get the current page HTML."""
        if not self.session_id:
            error_msg = "No active session to get HTML from"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        payload = {
            "session_id": self.session_id
        }
        
        response = requests.post(f"{self.api_url}/page/html", json=payload)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Retrieved HTML content (length: {len(data.get('html', ''))}")
            return data.get("html", "")
        else:
            error_msg = f"Failed to get HTML: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def take_screenshot(self, filename: str = None) -> str:
        """Take a screenshot of the current page."""
        if not self.session_id:
            error_msg = "No active session to take screenshot from"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        if not filename:
            os.makedirs("screenshots", exist_ok=True)
            filename = f"screenshots/austender_{int(time.time())}.png"
        
        payload = {
            "session_id": self.session_id
        }
        
        response = requests.post(f"{self.api_url}/page/screenshot", json=payload)
        if response.status_code == 200:
            data = response.json()
            base64_image = data.get("screenshot", "")
            
            # Save the base64 image as a file
            import base64
            with open(filename, "wb") as f:
                f.write(base64.b64decode(base64_image.split(",")[1]))
            
            logger.info(f"Saved screenshot to {filename}")
            return filename
        else:
            error_msg = f"Failed to take screenshot: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def click(self, selector: str) -> bool:
        """Click on an element identified by the selector."""
        if not self.session_id:
            error_msg = "No active session to perform click action"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        payload = {
            "session_id": self.session_id,
            "selector": selector
        }
        
        response = requests.post(f"{self.api_url}/page/click", json=payload)
        if response.status_code == 200:
            logger.info(f"Clicked on selector: {selector}")
            return True
        else:
            error_msg = f"Failed to click on {selector}: {response.text}"
            logger.error(error_msg)
            return False
    
    def extract_data(self, selectors: Dict[str, str]) -> Dict:
        """Extract data from the page using selectors."""
        if not self.session_id:
            error_msg = "No active session to extract data from"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        payload = {
            "session_id": self.session_id,
            "selectors": selectors
        }
        
        response = requests.post(f"{self.api_url}/page/extract", json=payload)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Extracted data using {len(selectors)} selectors")
            return data
        else:
            error_msg = f"Failed to extract data: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def execute_script(self, script: str) -> Any:
        """Execute JavaScript on the page."""
        if not self.session_id:
            error_msg = "No active session to execute script on"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        payload = {
            "session_id": self.session_id,
            "script": script
        }
        
        response = requests.post(f"{self.api_url}/page/execute", json=payload)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Executed script: {script[:50]}...")
            return data.get("result")
        else:
            error_msg = f"Failed to execute script: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)

class AustenderScraper:
    """Scraper for extracting opportunities from Austender."""
    
    def __init__(self, browser_client: BrowserUseClient = None):
        self.browser = browser_client or BrowserUseClient()
        self.opportunities = []
        logger.info("Initialized Austender Scraper")
    
    def scrape_search_results(self, url: str = AUSTENDER_URL, max_pages: int = 1) -> List[Dict]:
        """Scrape opportunity listings from search results pages."""
        try:
            # Navigate to the search URL
            self.browser.navigate(url)
            time.sleep(3)  # Allow page to fully load
            
            # Take a screenshot for debugging
            self.browser.take_screenshot("screenshots/search_results_initial.png")
            
            opportunities = []
            current_page = 1
            
            while current_page <= max_pages:
                logger.info(f"Processing page {current_page}")
                
                # Extract opportunities from the current page
                page_opportunities = self._extract_opportunities_from_page()
                if page_opportunities:
                    opportunities.extend(page_opportunities)
                    logger.info(f"Found {len(page_opportunities)} opportunities on page {current_page}")
                else:
                    logger.warning(f"No opportunities found on page {current_page}")
                    break
                
                # Check if there's a next page
                if current_page < max_pages:
                    has_next = self._go_to_next_page()
                    if not has_next:
                        logger.info("No more pages available")
                        break
                    current_page += 1
                    time.sleep(2)  # Wait for page to load
                else:
                    break
            
            self.opportunities = opportunities
            logger.info(f"Total opportunities found: {len(opportunities)}")
            return opportunities
            
        except Exception as e:
            logger.error(f"Error scraping search results: {str(e)}")
            self.browser.take_screenshot("screenshots/error_screenshot.png")
            return []
    
    def _extract_opportunities_from_page(self) -> List[Dict]:
        """Extract opportunities from the current page."""
        try:
            # Get the HTML content of the page
            html = self.browser.get_html()
            
            # Use JavaScript to extract the opportunities
            # This is more reliable than trying to extract via selectors directly
            script = """
                const opportunities = [];
                const rows = document.querySelectorAll('table.search-results tr');
                
                for (let i = 1; i < rows.length; i++) {  // Skip header row
                    const row = rows[i];
                    const titleElement = row.querySelector('td a');
                    
                    if (titleElement) {
                        const title = titleElement.textContent.trim();
                        const url = titleElement.href;
                        const cells = row.querySelectorAll('td');
                        
                        // Extract other details if available
                        const agencyDiv = cells[1] ? cells[1].textContent.trim() : '';
                        const categoryDiv = cells[2] ? cells[2].textContent.trim() : '';
                        const dateDiv = cells[3] ? cells[3].textContent.trim() : '';
                        const locationDiv = cells[4] ? cells[4].textContent.trim() : '';
                        
                        opportunities.push({
                            title: title,
                            url: url,
                            agency: agencyDiv,
                            category: categoryDiv,
                            date: dateDiv,
                            location: locationDiv,
                            id: url.split('/').pop()
                        });
                    }
                }
                
                return opportunities;
            """
            
            result = self.browser.execute_script(script)
            
            # Take a screenshot for reference
            self.browser.take_screenshot(f"screenshots/results_page_{int(time.time())}.png")
            
            if not result or not isinstance(result, list):
                logger.warning("No opportunities found or result is not a list")
                
                # Alternative method with selectors
                selectors = {
                    "titles": "table.search-results tr td a",
                    "agencies": "table.search-results tr td:nth-child(2)",
                    "categories": "table.search-results tr td:nth-child(3)",
                    "dates": "table.search-results tr td:nth-child(4)",
                    "locations": "table.search-results tr td:nth-child(5)"
                }
                
                extracted_data = self.browser.extract_data(selectors)
                
                # Process the extracted data if available
                if extracted_data and 'titles' in extracted_data and len(extracted_data['titles']) > 0:
                    result = []
                    for i in range(len(extracted_data['titles'])):
                        result.append({
                            'title': extracted_data['titles'][i] if i < len(extracted_data['titles']) else '',
                            'agency': extracted_data['agencies'][i] if i < len(extracted_data['agencies']) else '',
                            'category': extracted_data['categories'][i] if i < len(extracted_data['categories']) else '',
                            'date': extracted_data['dates'][i] if i < len(extracted_data['dates']) else '',
                            'location': extracted_data['locations'][i] if i < len(extracted_data['locations']) else '',
                            'url': '',  # No URL available from this method
                            'id': f"unknown_{i}"
                        })
                
            return result or []
            
        except Exception as e:
            logger.error(f"Error extracting opportunities from page: {str(e)}")
            self.browser.take_screenshot("screenshots/extraction_error.png")
            return []
    
    def _go_to_next_page(self) -> bool:
        """Navigate to the next page of results."""
        try:
            # Check if next page button exists and click it
            script = """
                const nextPageLink = document.querySelector('a[class*="next"]') || 
                                     document.querySelector('a:has([class*="next"])') ||
                                     document.querySelector('a[aria-label*="next"]') ||
                                     document.querySelector('a.next-page') ||
                                     document.querySelector('a[rel="next"]') ||
                                     document.querySelector('a:has(svg[aria-label="Next page"])');
                
                if (nextPageLink) {
                    nextPageLink.click();
                    return true;
                }
                return false;
            """
            
            result = self.browser.execute_script(script)
            
            if result:
                logger.info("Navigated to next page")
                time.sleep(3)  # Allow page to load
                return True
            else:
                logger.info("No next page button found")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to next page: {str(e)}")
            return False
    
    def get_opportunity_details(self, opportunity_id: str = None, opportunity_url: str = None) -> Dict:
        """Get detailed information about a specific opportunity."""
        if not opportunity_id and not opportunity_url:
            raise ValueError("Either opportunity_id or opportunity_url must be provided")
        
        try:
            # Determine the URL to navigate to
            url = opportunity_url
            if not url and opportunity_id:
                url = f"https://www.tenders.gov.au/Atm/Show/{opportunity_id}"
            
            # Navigate to the opportunity page
            self.browser.navigate(url)
            time.sleep(3)  # Allow page to fully load
            
            # Take screenshot for reference
            self.browser.take_screenshot(f"screenshots/opportunity_{opportunity_id or 'unknown'}.png")
            
            # Extract details using JavaScript
            script = """
                function getElementTextBySelector(selector) {
                    const el = document.querySelector(selector);
                    return el ? el.textContent.trim() : '';
                }
                
                function getAttachments() {
                    const attachments = [];
                    const attachmentRows = document.querySelectorAll('table.attachment-list tr');
                    
                    for (let i = 1; i < attachmentRows.length; i++) {  // Skip header row
                        const row = attachmentRows[i];
                        const cells = row.querySelectorAll('td');
                        
                        if (cells.length >= 2) {
                            const nameEl = cells[0].querySelector('a');
                            attachments.push({
                                name: nameEl ? nameEl.textContent.trim() : '',
                                url: nameEl ? nameEl.href : '',
                                type: cells[1] ? cells[1].textContent.trim() : ''
                            });
                        }
                    }
                    
                    return attachments;
                }
                
                return {
                    title: getElementTextBySelector('.opportunity-details h1') || 
                           getElementTextBySelector('h1.title'),
                    id: getElementTextBySelector('.opportunity-id') || 
                        getElementTextBySelector('.atm-id'),
                    agency: getElementTextBySelector('.agency-name') || 
                            getElementTextBySelector('.department-name'),
                    published: getElementTextBySelector('.published-date') || 
                               getElementTextBySelector('.date-published'),
                    closing: getElementTextBySelector('.closing-date') || 
                             getElementTextBySelector('.date-closing'),
                    description: getElementTextBySelector('.description') || 
                                 getElementTextBySelector('.summary'),
                    category: getElementTextBySelector('.category') || 
                              getElementTextBySelector('.categories'),
                    contact: {
                        name: getElementTextBySelector('.contact-name') || 
                              getElementTextBySelector('.contact .name'),
                        email: getElementTextBySelector('.contact-email') || 
                               getElementTextBySelector('.contact .email'),
                        phone: getElementTextBySelector('.contact-phone') || 
                               getElementTextBySelector('.contact .phone')
                    },
                    attachments: getAttachments()
                };
            """
            
            details = self.browser.execute_script(script)
            
            if not details or not isinstance(details, dict):
                logger.warning("Failed to extract opportunity details")
                return {}
            
            logger.info(f"Successfully extracted details for opportunity: {details.get('title', 'Unknown')}")
            return details
            
        except Exception as e:
            logger.error(f"Error getting opportunity details: {str(e)}")
            self.browser.take_screenshot("screenshots/details_error.png")
            return {}
    
    def save_opportunities(self, filename: str = None) -> str:
        """Save scraped opportunities to a JSON file."""
        if not self.opportunities:
            logger.warning("No opportunities to save")
            return ""
        
        if not filename:
            os.makedirs("output", exist_ok=True)
            filename = f"output/austender_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.opportunities, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.opportunities)} opportunities to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving opportunities: {str(e)}")
            return ""
    
    def close(self):
        """Close the browser session."""
        if self.browser:
            self.browser.end_session()
            logger.info("Closed browser session")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Scrape construction opportunities from Austender")
    parser.add_argument("--pages", type=int, default=1, help="Maximum number of pages to scrape")
    parser.add_argument("--details", action="store_true", help="Fetch detailed information for each opportunity")
    parser.add_argument("--save", action="store_true", help="Save opportunities to a JSON file")
    parser.add_argument("--output", type=str, help="Output filename")
    parser.add_argument("--url", type=str, default=AUSTENDER_URL, help="URL to scrape")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    scraper = AustenderScraper()
    
    try:
        # Scrape search results
        opportunities = scraper.scrape_search_results(args.url, args.pages)
        
        if not opportunities:
            logger.warning("No opportunities found")
            return
        
        # Get detailed information if requested
        if args.details:
            logger.info("Fetching detailed information for each opportunity")
            for i, opp in enumerate(opportunities):
                if 'id' in opp and opp['id']:
                    logger.info(f"Fetching details for opportunity {i+1}/{len(opportunities)}: {opp['id']}")
                    details = scraper.get_opportunity_details(opportunity_id=opp['id'])
                    if details:
                        opportunities[i].update(details)
                    time.sleep(1)  # Be nice to the server
        
        # Save opportunities if requested
        if args.save:
            filename = args.output if args.output else None
            scraper.save_opportunities(filename)
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
    finally:
        # Clean up
        scraper.close()

if __name__ == "__main__":
    main()
