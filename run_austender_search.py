#!/usr/bin/env python
"""
Austender Search Script
A simplified script for searching bridge construction opportunities on Austender
"""

import os
import json
import asyncio
import logging
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
logger = logging.getLogger("austender_search")

# Constants
AUSTENDER_URL = "https://www.tenders.gov.au/"

class AustenderSearcher:
    """Class for searching on Austender without complex AI integration"""
    
    def __init__(self, headless=False):
        """Initialize the searcher"""
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.results = []
        
        # Ensure output directories exist
        Path("screenshots").mkdir(exist_ok=True)
        Path("results").mkdir(exist_ok=True)
    
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
        
        # Use random viewport and user agent
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            locale="en-AU",
            timezone_id="Australia/Sydney"
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
    
    async def go_to_search_page(self):
        """Navigate to the ATM search page"""
        logger.info("Finding the ATM search link...")
        
        # Try to find the ATM link
        selectors = [
            "[href*='atm']", 
            "[href*='ATM']", 
            ":text-matches('Approaches to Market', 'i')",
            "a:has-text('ATM')",
            "a:has-text('Approaches')"
        ]
        
        for selector in selectors:
            try:
                # Check if the element exists
                element = await self.page.query_selector(selector)
                if element:
                    logger.info(f"Found ATM link with selector: {selector}")
                    
                    # Scroll into view
                    await self.page.evaluate(f"""(selector) => {{
                        const element = document.querySelector(selector);
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        }}
                    }}""", selector)
                    
                    # Wait a bit after scrolling
                    await asyncio.sleep(1)
                    
                    # Click the link
                    await self.page.click(selector)
                    
                    # Wait for navigation
                    await self.page.wait_for_load_state("networkidle")
                    
                    # Take a screenshot
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = f"screenshots/search_page_{timestamp}.png"
                    await self.page.screenshot(path=screenshot_path)
                    
                    # Check if we're on the search page
                    url = self.page.url
                    if "search" in url.lower() or "atm" in url.lower():
                        logger.info("Successfully navigated to search page")
                        return True
                    else:
                        logger.warning("Clicked a link but didn't reach the search page")
            except Exception as e:
                logger.warning(f"Error with selector {selector}: {str(e)}")
                continue
        
        # If we're here, we couldn't find the link
        logger.error("Could not find the ATM search link")
        return False
    
    async def search_for_bridge_construction(self, state="NSW"):
        """Search for bridge construction opportunities"""
        logger.info(f"Searching for bridge construction in {state}...")
        
        try:
            # First, check if we need to select the ATM tab
            atm_tab_selectors = [
                "a:has-text('Search ATM')",
                "a:has-text('Approaches to Market')",
                "#block-atm-search-block",
                "[href*='search/atm']"
            ]
            
            for selector in atm_tab_selectors:
                tab_element = await self.page.query_selector(selector)
                if tab_element:
                    logger.info(f"Found ATM tab with selector: {selector}")
                    await tab_element.click()
                    await self.page.wait_for_load_state("networkidle")
                    break
            
            # Find the keyword input field
            keyword_selectors = [
                "#edit-keyword",
                "input[name='keyword']",
                "input[placeholder*='keyword']",
                "input[placeholder*='search']"
            ]
            
            keyword_field = None
            for selector in keyword_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    keyword_field = element
                    break
            
            if not keyword_field:
                logger.error("Could not find the keyword input field")
                return False
            
            # Enter the search terms
            logger.info("Entering search keywords: bridge construction")
            await keyword_field.fill("bridge construction")
            await asyncio.sleep(1)
            
            # Try to select NSW state if possible
            state_selectors = [
                "#edit-state",
                "select[name*='state']",
                "select[aria-label*='state']"
            ]
            
            for selector in state_selectors:
                state_element = await self.page.query_selector(selector)
                if state_element:
                    logger.info(f"Found state selection with selector: {selector}")
                    await self.page.select_option(selector, state)
                    await asyncio.sleep(1)
                    break
            
            # Find and click the search button
            search_button_selectors = [
                "#edit-submit-search",
                "input[type='submit']",
                "button[type='submit']",
                "button:has-text('Search')",
                "input[value='Search']"
            ]
            
            for selector in search_button_selectors:
                button = await self.page.query_selector(selector)
                if button:
                    logger.info(f"Found search button with selector: {selector}")
                    await button.click()
                    await self.page.wait_for_load_state("networkidle")
                    
                    # Take a screenshot of search results
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = f"screenshots/search_results_{timestamp}.png"
                    await self.page.screenshot(path=screenshot_path)
                    
                    logger.info("Search completed successfully")
                    return True
            
            logger.error("Could not find the search button")
            return False
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return False
    
    async def alternative_search_approach(self):
        """Alternative approach using different techniques to handle complex DOM"""
        logger.info("Attempting alternative search approach...")
        
        try:
            # Get the current URL to determine our location
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")
            
            # Take a screenshot of current state
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/alternative_approach_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Check if we're already on the search page
            if "search" in current_url or "atm" in current_url:
                logger.info("We're on a search-related page")
                
                # Sometimes the search form is in an iframe or has complex JS behaviors
                # Try using Playwright's evaluate to inject and execute a search directly
                logger.info("Attempting direct JS search injection...")
                
                # Try different approaches to search form manipulation
                script_approaches = [
                    # Approach 1: Try to find and fill the form using JS
                    """
                    (function() {
                        // Find keyword field through various methods
                        let keywordField = document.querySelector('#edit-keyword') || 
                                           document.querySelector('input[name="keyword"]') ||
                                           document.querySelector('input[placeholder*="keyword"]');
                        
                        if (keywordField) {
                            keywordField.value = 'bridge construction';
                            keywordField.dispatchEvent(new Event('input', { bubbles: true }));
                            
                            // Try to find state selector
                            let stateField = document.querySelector('#edit-state') ||
                                            document.querySelector('select[name*="state"]');
                            
                            if (stateField) {
                                // Try to select NSW
                                for (let option of stateField.options) {
                                    if (option.value === 'NSW' || option.text.includes('NSW') || option.text.includes('New South Wales')) {
                                        stateField.value = option.value;
                                        stateField.dispatchEvent(new Event('change', { bubbles: true }));
                                        break;
                                    }
                                }
                            }
                            
                            // Find and click search button
                            let searchButton = document.querySelector('#edit-submit-search') ||
                                              document.querySelector('input[type="submit"]') ||
                                              document.querySelector('button[type="submit"]');
                            
                            if (searchButton) {
                                searchButton.click();
                                return 'Search initiated via JS injection';
                            }
                        }
                        
                        return 'Could not find appropriate form elements';
                    })();
                    """,
                    
                    # Approach 2: Try direct form submission
                    """
                    (function() {
                        // Find the search form
                        let form = document.querySelector('form[action*="search"]') ||
                                  document.querySelector('form[id*="search"]');
                        
                        if (form) {
                            // Create hidden input for keyword if it doesn't exist
                            let keywordInput = form.querySelector('input[name="keyword"]');
                            if (!keywordInput) {
                                keywordInput = document.createElement('input');
                                keywordInput.type = 'hidden';
                                keywordInput.name = 'keyword';
                                form.appendChild(keywordInput);
                            }
                            keywordInput.value = 'bridge construction';
                            
                            // Add state if possible
                            let stateInput = form.querySelector('input[name*="state"], select[name*="state"]');
                            if (stateInput) {
                                if (stateInput.tagName === 'SELECT') {
                                    for (let option of stateInput.options) {
                                        if (option.value === 'NSW' || option.text.includes('NSW')) {
                                            stateInput.value = option.value;
                                            break;
                                        }
                                    }
                                } else {
                                    stateInput.value = 'NSW';
                                }
                            }
                            
                            // Submit the form
                            form.submit();
                            return 'Form submitted directly';
                        }
                        
                        return 'No search form found';
                    })();
                    """,
                    
                    # Approach 3: Try to use URL parameters directly
                    """
                    (function() {
                        // Get current URL parts
                        let url = new URL(window.location.href);
                        
                        // Add search parameters
                        url.searchParams.set('keyword', 'bridge construction');
                        url.searchParams.set('state', 'NSW');
                        
                        // Navigate to the new URL
                        window.location.href = url.toString();
                        return 'Redirecting with URL parameters';
                    })();
                    """
                ]
                
                # Try each approach
                for i, script in enumerate(script_approaches):
                    try:
                        logger.info(f"Trying JS approach #{i+1}")
                        result = await self.page.evaluate(script)
                        logger.info(f"JS approach #{i+1} result: {result}")
                        
                        # Wait for navigation/change
                        try:
                            await self.page.wait_for_load_state("networkidle", timeout=10000)
                            # Take a screenshot after JS execution
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            screenshot_path = f"screenshots/after_js_approach_{i+1}_{timestamp}.png"
                            await self.page.screenshot(path=screenshot_path)
                            
                            # Check if we see search results
                            page_content = await self.page.content()
                            if "search results" in page_content.lower() or "atm-id" in page_content.lower():
                                logger.info("Search appears successful!")
                                return True
                        except Exception as e:
                            logger.warning(f"Error waiting for navigation: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Error with JS approach #{i+1}: {str(e)}")
                
                # If JS approaches fail, try direct URL navigation
                logger.info("Trying direct navigation to search results page")
                search_urls = [
                    "https://www.tenders.gov.au/Search/KeywordSearch?keyword=bridge+construction&state=NSW",
                    "https://www.tenders.gov.au/search/atm?keyword=bridge+construction&state=NSW",
                ]
                
                for url in search_urls:
                    try:
                        await self.navigate_to(url)
                        # Check if we see search results
                        page_content = await self.page.content()
                        if "search results" in page_content.lower() or "atm-id" in page_content.lower():
                            logger.info("Direct URL navigation successful!")
                            return True
                    except Exception as e:
                        logger.warning(f"Error navigating to {url}: {str(e)}")
            
            # If we're still not on a search page, try to find it from the homepage
            elif "tenders.gov.au" in current_url:
                logger.info("Not on search page, attempting to navigate from homepage")
                # Go back to the homepage
                await self.navigate_to(AUSTENDER_URL)
                
                # Look for direct search URL or form
                try:
                    # Try to find a direct link to the search page with our parameters
                    search_link_selectors = [
                        "a[href*='search'][href*='atm']",
                        "a:has-text('Search Approaches to Market')",
                        "a:has-text('Search ATM')"
                    ]
                    
                    for selector in search_link_selectors:
                        element = await self.page.query_selector(selector)
                        if element:
                            logger.info(f"Found direct search link with selector: {selector}")
                            await element.click()
                            await self.page.wait_for_load_state("networkidle")
                            
                            # Now try the search again
                            return await self.search_for_bridge_construction()
                except Exception as e:
                    logger.warning(f"Error finding direct search link: {str(e)}")
            
            # If all else fails, try a completely different approach
            logger.warning("All standard approaches failed, trying emergency measures")
            
            # Emergency measure: Try to use keyboard navigation and shortcuts
            try:
                # Go to the homepage
                await self.navigate_to(AUSTENDER_URL)
                
                # Press Tab multiple times to navigate through elements
                for _ in range(10):
                    await self.page.keyboard.press("Tab")
                    await asyncio.sleep(0.3)
                
                # Try to press Enter on what might be a search link
                await self.page.keyboard.press("Enter")
                await self.page.wait_for_load_state("networkidle")
                
                # Check if we're on a search page now
                current_url = self.page.url
                if "search" in current_url:
                    logger.info("Successfully navigated to search page via keyboard")
                    # Now try the search again
                    return await self.search_for_bridge_construction()
            except Exception as e:
                logger.warning(f"Error with keyboard navigation: {str(e)}")
            
            # Last resort: Try a completely different approach
            return False
            
        except Exception as e:
            logger.error(f"Error in alternative search approach: {str(e)}")
            return False

    async def extract_results(self, max_results=5):
        """Extract search results from the page"""
        logger.info(f"Extracting up to {max_results} search results...")
        
        try:
            # Different potential selectors for result items
            result_selectors = [
                ".search-result",
                ".views-row",
                "tr.views-row",
                "div.view-content > *",
                "table tbody tr"
            ]
            
            results = []
            result_elements = []
            
            # Try different selectors until we find one that works
            for selector in result_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    logger.info(f"Found {len(elements)} results with selector: {selector}")
                    result_elements = elements[:max_results]
                    break
            
            if not result_elements:
                logger.error("Could not find any search results")
                return []
            
            # Process each result
            for i, element in enumerate(result_elements):
                try:
                    # Extract text content
                    text_content = await element.text_content()
                    
                    # Try to extract structured data
                    result = {
                        "position": i + 1,
                        "raw_text": text_content.strip(),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Try to extract ATM ID
                    atm_id_element = await element.query_selector("*:text-matches('ATM ID|ID:|ATM:','i')")
                    if atm_id_element:
                        atm_id_text = await atm_id_element.text_content()
                        atm_id = atm_id_text.split(":")[-1].strip() if ":" in atm_id_text else atm_id_text.strip()
                        result["atm_id"] = atm_id
                    
                    # Try to extract title
                    title_element = await element.query_selector("a, h3, h4, strong")
                    if title_element:
                        result["title"] = (await title_element.text_content()).strip()
                    
                    # Try to extract URL
                    link_element = await element.query_selector("a")
                    if link_element:
                        href = await link_element.get_attribute("href")
                        if href:
                            # Convert to absolute URL if needed
                            if href.startswith("/"):
                                href = f"https://www.tenders.gov.au{href}"
                            result["url"] = href
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.warning(f"Error extracting data from result {i+1}: {str(e)}")
            
            logger.info(f"Extracted {len(results)} results")
            self.results = results
            return results
            
        except Exception as e:
            logger.error(f"Error extracting results: {str(e)}")
            return []
    
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
            
            # Take a screenshot after login attempt
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/after_login_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Check if login was successful (look for elements that indicate logged-in state)
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
            
            # Check if we're still on a login page or if there's an error message
            error_indicators = [
                "text=Invalid username",
                "text=Invalid password",
                "text=Incorrect login",
                "text=Try again",
                "div.error",
                "span.error"
            ]
            
            for indicator in error_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element:
                        logger.error(f"Login failed, found error indicator: {indicator}")
                        return False
                except Exception:
                    pass
            
            # If we got here, there were no strong indicators either way
            # Let's check the URL as a fallback
            current_url = self.page.url
            if "login" in current_url.lower() or "auth" in current_url.lower():
                logger.warning("Still on login page, login may have failed")
                return False
            
            # No clear indicators, but we're not on login page anymore
            logger.info("Login appears to be successful")
            return True
            
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False

    async def run_search(self):
        """Run the full search process"""
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
            
            # Find the ATM search link
            if not await self.go_to_search_page():
                logger.error("Failed to navigate to search page")
                return False
            
            # Search for bridge construction in NSW
            # Add a pause to ensure page is fully loaded and stabilized
            logger.info("Pausing to ensure page is fully loaded...")
            await asyncio.sleep(3)
            
            # Take a screenshot before search
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/before_search_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Try multiple search approaches
            search_success = await self.search_for_bridge_construction()
            
            if not search_success:
                logger.warning("Standard search failed, trying alternative approach...")
                search_success = await self.alternative_search_approach()
                
            if not search_success:
                logger.error("All search methods failed")
                return False
            
            # Extract results
            results = await self.extract_results(5)
            
            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results/austender_results_{timestamp}.json"
            
            with open(filename, "w") as f:
                json.dump({
                    "search_query": "bridge construction",
                    "state": "NSW",
                    "timestamp": datetime.now().isoformat(),
                    "results": results
                }, f, indent=2)
            
            logger.info(f"Results saved to {filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error running search: {str(e)}")
            return False
            
        finally:
            # Always close the browser
            await self.stop()

async def main():
    """Main function"""
    print("=== Austender Bridge Construction Search ===")
    print("This script will search for bridge construction opportunities in NSW")
    
    searcher = AustenderSearcher(headless=False)
    await searcher.run_search()
    
    # Print summary of results
    if searcher.results:
        print("\nSEARCH RESULTS SUMMARY:")
        print("-" * 60)
        for i, result in enumerate(searcher.results):
            print(f"{i+1}. {result.get('title', 'Unnamed Opportunity')}")
            if "atm_id" in result:
                print(f"   ID: {result['atm_id']}")
            if "url" in result:
                print(f"   URL: {result['url']}")
            print(f"   Raw Text Length: {len(result.get('raw_text', ''))}")
            print("-" * 60)
    else:
        print("\nNo results found or error occurred during search.")
    
    return searcher.results

if __name__ == "__main__":
    asyncio.run(main())
