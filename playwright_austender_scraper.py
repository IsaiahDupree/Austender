#!/usr/bin/env python3
"""
Austender Advanced Scraper using Playwright
-------------------------------------------
This script uses Playwright to scrape construction opportunities from Austender
with advanced anti-bot measures and detailed data extraction.
"""

import os
import json
import time
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"austender_playwright_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("austender_scraper")

# Create directories for outputs
os.makedirs("screenshots", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Austender URL
AUSTENDER_URL = "https://www.tenders.gov.au/Search/KeywordSearch?keyword=construction&type=ATM&dateType=ClosingDate"

# List of user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42"
]

class AdvancedAustenderScraper:
    """Advanced scraper for extracting opportunities from Austender using Playwright."""
    
    def __init__(self, headless: bool = False, slow_mo: int = 100):
        self.headless = headless
        self.slow_mo = slow_mo
        self.opportunities = []
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        logger.info("Initialized Advanced Austender Scraper")
    
    def start_browser(self) -> None:
        """Start a browser instance with anti-detection measures."""
        try:
            import random
            
            # Start Playwright
            self.playwright = sync_playwright().start()
            
            # Launch browser with specific options to avoid detection
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials"
                ]
            )
            
            # Create a context with custom viewport and user agent
            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(USER_AGENTS),
                java_script_enabled=True,
                accept_downloads=True,
                ignore_https_errors=True
            )
            
            # Set additional properties to avoid detection
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                
                // Fix hairline issue
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {
                                type: "application/x-google-chrome-pdf",
                                suffixes: "pdf",
                                description: "Portable Document Format",
                                enabledPlugin: Plugin
                            },
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {
                                type: "application/pdf",
                                suffixes: "pdf",
                                description: "Portable Document Format",
                                enabledPlugin: Plugin
                            },
                            description: "Portable Document Format",
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        },
                        {
                            0: {
                                type: "application/x-nacl",
                                suffixes: "",
                                description: "Native Client Executable",
                                enabledPlugin: Plugin
                            },
                            1: {
                                type: "application/x-pnacl",
                                suffixes: "",
                                description: "Portable Native Client Executable",
                                enabledPlugin: Plugin
                            },
                            description: "",
                            filename: "internal-nacl-plugin",
                            length: 2,
                            name: "Native Client"
                        }
                    ]
                });
                
                // Fix languages issues
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en', 'es']
                });
                
                // Fix permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            # Create a new page
            self.page = self.context.new_page()
            
            # Add additional headers to appear more like a regular browser
            self.page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Sec-Ch-Ua": '"Chromium";v="113", "Not-A.Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Cache-Control": "max-age=0",
                "DNT": "1"
            })
            
            # Add event listeners for network requests
            self.page.on("request", lambda request: logger.debug(f"Request: {request.method} {request.url}"))
            self.page.on("response", lambda response: logger.debug(f"Response: {response.status} {response.url}"))
            
            logger.info("Browser started with anti-detection configuration")
            return True
            
        except Exception as e:
            logger.error(f"Error starting browser: {str(e)}")
            self.close()
            return False
    
    def scrape_search_results(self, url: str = AUSTENDER_URL, max_pages: int = 1) -> List[Dict]:
        """Scrape opportunity listings from search results pages."""
        if not self.page:
            if not self.start_browser():
                raise Exception("Failed to start browser")
        
        try:
            logger.info(f"Searching for construction opportunities, max {max_pages} pages")
            logger.info(f"Searching with URL: {url}")
            
            # Navigate to the search URL
            self.page.goto(url, wait_until="networkidle")
            self.page.wait_for_load_state("domcontentloaded")
            
            # Take a screenshot for debugging
            self._take_screenshot("search_results_initial.png")
            
            opportunities = []
            current_page = 1
            
            while current_page <= max_pages:
                logger.info(f"Processing page {current_page}")
                
                # Wait for the results table to be visible
                try:
                    self.page.wait_for_selector("table.search-results", timeout=10000)
                except Exception:
                    try:
                        # Alternative selector
                        self.page.wait_for_selector(".search-results-table", timeout=5000)
                    except Exception as e:
                        logger.warning(f"Could not find results table: {str(e)}")
                        self._save_debug_info(f"search_results_{int(time.time())}")
                
                # Take screenshot for reference
                self._take_screenshot(f"search_results_{current_page}.png")
                
                # Extract opportunities from the current page
                page_opportunities = self._extract_opportunities_from_page()
                if page_opportunities:
                    opportunities.extend(page_opportunities)
                    logger.info(f"Found {len(page_opportunities)} opportunity items")
                else:
                    logger.info(f"No opportunities found on page {current_page}")
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
            self._save_debug_info("error_screenshot")
            return []
    
    def _extract_opportunities_from_page(self) -> List[Dict]:
        """Extract opportunities from the current page."""
        try:
            # Log current page info
            current_url = self.page.url
            page_title = self.page.title()
            logger.info(f"Current page title: {page_title}")
            logger.info(f"Current URL: {current_url}")
            
            # Save debug info
            self._save_debug_info(f"search_results_{int(time.time())}")
            
            # Use JavaScript to extract the opportunities
            script = """
                const opportunities = [];
                const rows = document.querySelectorAll('table.search-results tr:not(:first-child)');
                
                if (rows.length === 0) {
                    // Try alternative selector
                    const altRows = document.querySelectorAll('.search-results-table tr:not(:first-child)');
                    if (altRows.length > 0) {
                        altRows.forEach(row => {
                            const titleElement = row.querySelector('td a');
                            if (titleElement) {
                                const title = titleElement.textContent.trim();
                                const url = titleElement.href;
                                const cells = row.querySelectorAll('td');
                                
                                opportunities.push({
                                    title: title,
                                    url: url,
                                    agency: cells[1] ? cells[1].textContent.trim() : '',
                                    category: cells[2] ? cells[2].textContent.trim() : '',
                                    date: cells[3] ? cells[3].textContent.trim() : '',
                                    location: cells[4] ? cells[4].textContent.trim() : '',
                                    id: url.split('/').pop()
                                });
                            }
                        });
                    }
                } else {
                    rows.forEach(row => {
                        const titleElement = row.querySelector('td a');
                        if (titleElement) {
                            const title = titleElement.textContent.trim();
                            const url = titleElement.href;
                            const cells = row.querySelectorAll('td');
                            
                            opportunities.push({
                                title: title,
                                url: url,
                                agency: cells[1] ? cells[1].textContent.trim() : '',
                                category: cells[2] ? cells[2].textContent.trim() : '',
                                date: cells[3] ? cells[3].textContent.trim() : '',
                                location: cells[4] ? cells[4].textContent.trim() : '',
                                id: url.split('/').pop()
                            });
                        }
                    });
                }
                
                return opportunities;
            """
            
            opportunities = self.page.evaluate(script)
            
            # If no opportunities found, try a different approach
            if not opportunities:
                logger.warning("No opportunities found with primary selector, trying alternative approach")
                
                # Try to find all link items that might be opportunities
                links = self.page.query_selector_all('table a')
                
                if not links:
                    links = self.page.query_selector_all('.search-results-table a')
                
                if not links:
                    # Try more generic selectors
                    links = self.page.query_selector_all('tbody tr td a')
                
                if links:
                    for link in links:
                        href = link.get_attribute('href')
                        if href and ('Atm/Show' in href or 'atm/' in href.lower()):
                            title = link.inner_text().strip()
                            row = link.evaluate('node => node.closest("tr")')
                            
                            if row:
                                agency = row.query_selector('td:nth-child(2)')
                                category = row.query_selector('td:nth-child(3)')
                                date = row.query_selector('td:nth-child(4)')
                                location = row.query_selector('td:nth-child(5)')
                                
                                opportunities.append({
                                    'title': title,
                                    'url': href,
                                    'agency': agency.inner_text().strip() if agency else '',
                                    'category': category.inner_text().strip() if category else '',
                                    'date': date.inner_text().strip() if date else '',
                                    'location': location.inner_text().strip() if location else '',
                                    'id': href.split('/')[-1] if '/' in href else ''
                                })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error extracting opportunities from page: {str(e)}")
            self._save_debug_info(f"extraction_error_{int(time.time())}")
            return []
    
    def _go_to_next_page(self) -> bool:
        """Navigate to the next page of results."""
        try:
            # Try different selectors for the next page button
            next_selectors = [
                'a[class*="next"]',
                'a.next-page',
                'a:has-text("Next")',
                'a:has-text("Next page")',
                'a[aria-label*="next"]',
                'a[rel="next"]',
                'li.pager-next a'
            ]
            
            for selector in next_selectors:
                next_button = self.page.query_selector(selector)
                if next_button:
                    logger.info(f"Found next page button with selector: {selector}")
                    next_button.click()
                    self.page.wait_for_load_state("networkidle")
                    return True
            
            # Try JavaScript approach if direct selectors fail
            has_next = self.page.evaluate("""
                const nextPageLink = document.querySelector('a[class*="next"]') || 
                                     document.querySelector('a:has([class*="next"])') ||
                                     document.querySelector('a[aria-label*="next"]') ||
                                     document.querySelector('a.next-page') ||
                                     document.querySelector('a[rel="next"]') ||
                                     document.querySelector('a:has-text("Next")') ||
                                     document.querySelector('li.pager-next a');
                
                if (nextPageLink) {
                    nextPageLink.click();
                    return true;
                }
                return false;
            """)
            
            if has_next:
                logger.info("Navigated to next page via JavaScript")
                self.page.wait_for_load_state("networkidle")
                return True
            
            logger.info("No next page button found")
            return False
                
        except Exception as e:
            logger.error(f"Error navigating to next page: {str(e)}")
            return False
    
    def get_opportunity_details(self, opportunity_id: str = None, opportunity_url: str = None) -> Dict:
        """Get detailed information about a specific opportunity."""
        if not opportunity_id and not opportunity_url:
            raise ValueError("Either opportunity_id or opportunity_url must be provided")
        
        if not self.page:
            if not self.start_browser():
                raise Exception("Failed to start browser")
        
        try:
            # Determine the URL to navigate to
            url = opportunity_url
            if not url and opportunity_id:
                url = f"https://www.tenders.gov.au/Atm/Show/{opportunity_id}"
            
            logger.info(f"Getting details for opportunity at URL: {url}")
            
            # Navigate to the opportunity page
            self.page.goto(url, wait_until="networkidle")
            self.page.wait_for_load_state("domcontentloaded")
            
            # Take screenshot for reference
            self._take_screenshot(f"opportunity_{opportunity_id or 'unknown'}.png")
            
            # Save debug info
            self._save_debug_info(f"opportunity_{opportunity_id or 'unknown'}")
            
            # Extract details using JavaScript
            details = self.page.evaluate("""
                function getElementTextBySelector(selector) {
                    const el = document.querySelector(selector);
                    return el ? el.textContent.trim() : '';
                }
                
                function getElementTextByXPath(xpath) {
                    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                    return result.singleNodeValue ? result.singleNodeValue.textContent.trim() : '';
                }
                
                function getAttachments() {
                    const attachments = [];
                    const attachmentRows = document.querySelectorAll('table.attachment-list tr:not(:first-child)');
                    
                    if (attachmentRows.length === 0) {
                        // Try alternative selector
                        const altRows = document.querySelectorAll('.attachments-table tr:not(:first-child)');
                        altRows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 2) {
                                const nameEl = cells[0].querySelector('a');
                                attachments.push({
                                    name: nameEl ? nameEl.textContent.trim() : cells[0].textContent.trim(),
                                    url: nameEl ? nameEl.href : '',
                                    type: cells[1] ? cells[1].textContent.trim() : ''
                                });
                            }
                        });
                    } else {
                        attachmentRows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 2) {
                                const nameEl = cells[0].querySelector('a');
                                attachments.push({
                                    name: nameEl ? nameEl.textContent.trim() : cells[0].textContent.trim(),
                                    url: nameEl ? nameEl.href : '',
                                    type: cells[1] ? cells[1].textContent.trim() : ''
                                });
                            }
                        });
                    }
                    
                    return attachments;
                }
                
                // Try multiple selectors to be robust against site changes
                return {
                    title: getElementTextBySelector('.opportunity-details h1') || 
                           getElementTextBySelector('h1.title') ||
                           getElementTextBySelector('h1') ||
                           getElementTextByXPath('//h1[contains(text(), "ATM")]'),
                    
                    id: getElementTextBySelector('.opportunity-id') || 
                        getElementTextBySelector('.atm-id') ||
                        getElementTextBySelector('.reference-id') ||
                        getElementTextByXPath('//div[contains(text(), "ATM ID")]/following-sibling::div'),
                    
                    agency: getElementTextBySelector('.agency-name') || 
                            getElementTextBySelector('.department-name') ||
                            getElementTextBySelector('.agency') ||
                            getElementTextByXPath('//div[contains(text(), "Agency")]/following-sibling::div'),
                    
                    published: getElementTextBySelector('.published-date') || 
                               getElementTextBySelector('.date-published') ||
                               getElementTextByXPath('//div[contains(text(), "Published")]/following-sibling::div'),
                    
                    closing: getElementTextBySelector('.closing-date') || 
                             getElementTextBySelector('.date-closing') ||
                             getElementTextByXPath('//div[contains(text(), "Closing")]/following-sibling::div'),
                    
                    description: getElementTextBySelector('.description') || 
                                 getElementTextBySelector('.summary') ||
                                 getElementTextBySelector('.opportunity-description') ||
                                 getElementTextByXPath('//div[contains(text(), "Description")]/following-sibling::div'),
                    
                    category: getElementTextBySelector('.category') || 
                              getElementTextBySelector('.categories') ||
                              getElementTextByXPath('//div[contains(text(), "Category")]/following-sibling::div'),
                    
                    contact: {
                        name: getElementTextBySelector('.contact-name') || 
                              getElementTextBySelector('.contact .name') ||
                              getElementTextByXPath('//div[contains(text(), "Contact")]/following-sibling::div'),
                        
                        email: getElementTextBySelector('.contact-email') || 
                               getElementTextBySelector('.contact .email') ||
                               getElementTextByXPath('//div[contains(text(), "Email")]/following-sibling::div'),
                        
                        phone: getElementTextBySelector('.contact-phone') || 
                               getElementTextBySelector('.contact .phone') ||
                               getElementTextByXPath('//div[contains(text(), "Phone")]/following-sibling::div')
                    },
                    
                    attachments: getAttachments(),
                    
                    // Extract key dates
                    dates: {
                        published: getElementTextBySelector('.published-date') || 
                                   getElementTextByXPath('//div[contains(text(), "Published")]/following-sibling::div'),
                        
                        closing: getElementTextBySelector('.closing-date') || 
                                 getElementTextByXPath('//div[contains(text(), "Closing")]/following-sibling::div'),
                        
                        decision: getElementTextBySelector('.decision-date') || 
                                  getElementTextByXPath('//div[contains(text(), "Decision")]/following-sibling::div')
                    }
                };
            """)
            
            if details:
                logger.info(f"Successfully extracted details for opportunity: {details.get('title', 'Unknown')}")
            else:
                logger.warning("Failed to extract opportunity details")
            
            return details or {}
            
        except Exception as e:
            logger.error(f"Error getting opportunity details: {str(e)}")
            self._save_debug_info("details_error")
            return {}
    
    def _take_screenshot(self, filename: str) -> str:
        """Take a screenshot of the current page."""
        try:
            filepath = os.path.join("screenshots", filename)
            self.page.screenshot(path=filepath)
            logger.debug(f"Saved screenshot to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return ""
    
    def _save_debug_info(self, prefix: str) -> None:
        """Save debug information for troubleshooting."""
        try:
            # Take a screenshot
            self._take_screenshot(f"{prefix}.png")
            
            # Save the HTML content
            html_content = self.page.content()
            html_filepath = os.path.join("logs", f"{prefix}.html")
            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.debug(f"Saved HTML to {html_filepath}")
            
        except Exception as e:
            logger.error(f"Error saving debug info: {str(e)}")
    
    def save_opportunities(self, filename: str = None) -> str:
        """Save scraped opportunities to a JSON file."""
        if not self.opportunities:
            logger.warning("No opportunities to save")
            return ""
        
        if not filename:
            filename = f"output/austender_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.opportunities, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.opportunities)} opportunities to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving opportunities: {str(e)}")
            return ""
    
    def close(self) -> None:
        """Close the browser and Playwright instance."""
        try:
            if self.page:
                self.page.close()
            
            if self.context:
                self.context.close()
            
            if self.browser:
                self.browser.close()
            
            if self.playwright:
                self.playwright.stop()
            
            logger.info("Browser closed")
            
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
        
        # Reset attributes
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Scrape construction opportunities from Austender")
    parser.add_argument("--pages", type=int, default=1, help="Maximum number of pages to scrape")
    parser.add_argument("--details", action="store_true", help="Fetch detailed information for each opportunity")
    parser.add_argument("--save", action="store_true", help="Save opportunities to a JSON file")
    parser.add_argument("--output", type=str, help="Output filename")
    parser.add_argument("--url", type=str, default=AUSTENDER_URL, help="URL to scrape")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    scraper = AdvancedAustenderScraper(headless=args.headless)
    
    try:
        # Scrape search results
        opportunities = scraper.scrape_search_results(args.url, args.pages)
        
        if not opportunities:
            logger.warning("No opportunities found")
            return
        
        # Get detailed information if requested
        if args.details:
            logger.info("Fetching detailed information for each opportunity")
            detailed_opportunities = []
            
            for i, opp in enumerate(opportunities):
                if 'id' in opp and opp['id']:
                    logger.info(f"Fetching details for opportunity {i+1}/{len(opportunities)}: {opp['id']}")
                    details = scraper.get_opportunity_details(opportunity_id=opp['id'])
                    if details:
                        # Merge the basic opportunity info with the detailed info
                        detailed_opp = {**opp, **details}
                        detailed_opportunities.append(detailed_opp)
                    else:
                        # If we couldn't get details, just use the basic info
                        detailed_opportunities.append(opp)
                    time.sleep(1)  # Be nice to the server
                else:
                    detailed_opportunities.append(opp)
            
            scraper.opportunities = detailed_opportunities
        
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
