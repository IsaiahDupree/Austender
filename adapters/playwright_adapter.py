#!/usr/bin/env python
"""
Playwright Adapter for Austender Agent
Implements human-like browser interactions to avoid bot detection
"""

import os
import json
import asyncio
import logging
import random
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("playwright_adapter")

class PlaywrightAdapter:
    """Adapter for Playwright browser automation with human-like behavior"""
    
    def __init__(self, headless=False, screenshot_dir="screenshots"):
        """Initialize the Playwright adapter"""
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.screenshot_dir = screenshot_dir
        
        # Ensure screenshot directory exists
        Path(screenshot_dir).mkdir(exist_ok=True)
        
        # User agents for rotations
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
    
    async def initialize(self):
        """Initialize Playwright browser with anti-bot protections"""
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        
        # Select a random user agent
        user_agent = random.choice(self.user_agents)
        
        # Set up browser with anti-bot mitigations
        self.browser = await playwright.chromium.launch(
            headless=self.headless
        )
        
        # Create context with specific options to avoid fingerprinting
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=user_agent,
            locale="en-US",
            timezone_id="Australia/Sydney",  # Australian timezone for Austender
            geolocation={"longitude": 151.2099, "latitude": -33.8651},  # Sydney coordinates
            permissions=["geolocation"]
        )
        
        # Setup cookie handling
        await self.context.add_cookies([{
            "name": "cookieConsent", 
            "value": "accepted",
            "domain": "tenders.gov.au",
            "path": "/"
        }])
        
        # Create a new page
        self.page = await self.context.new_page()
        
        # Enable console logging
        self.page.on("console", lambda msg: logger.debug(f"Browser console: {msg.text}"))
        
        # Add human behavior to evade bot detection
        await self._add_human_behavior()
        
        logger.info("Playwright browser initialized with anti-bot protections")
        return True
    
    async def _add_human_behavior(self):
        """Add human-like behavior to the browser page"""
        # Inject scripts to mask automation
        await self.page.add_init_script("""
        // Override navigator properties to avoid detection
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        
        // Add noise to canvas fingerprinting
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            const dataURL = originalToDataURL.apply(this, arguments);
            if (dataURL.length > 1000) {
                // Add slight noise to the canvas data
                const modifiedDataURL = dataURL.substring(0, dataURL.length - 10) + 
                    Math.floor(Math.random() * 10).toString() + 
                    dataURL.substring(dataURL.length - 9);
                return modifiedDataURL;
            }
            return dataURL;
        };
        """)
    
    async def cleanup(self):
        """Clean up Playwright browser"""
        if self.browser:
            await self.browser.close()
            logger.info("Playwright browser closed")
        return True
    
    async def move_mouse_randomly(self):
        """Move the mouse in a human-like pattern"""
        if not self.page:
            return False
        
        try:
            # Get viewport size
            viewport = await self.page.evaluate("""() => {
                return {
                    width: window.innerWidth,
                    height: window.innerHeight
                };
            }""")
            
            # Generate random points within the viewport
            points = []
            num_points = random.randint(3, 8)
            
            for _ in range(num_points):
                points.append({
                    "x": random.randint(10, viewport["width"] - 10),
                    "y": random.randint(10, viewport["height"] - 10)
                })
            
            # Move the mouse through these points
            for point in points:
                await self.page.mouse.move(point["x"], point["y"], 
                                         steps=random.randint(5, 15))
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            return True
            
        except Exception as e:
            logger.error(f"Error moving mouse: {str(e)}")
            return False
    
    async def scroll_randomly(self):
        """Scroll the page in a human-like pattern"""
        if not self.page:
            return False
        
        try:
            # Get page height
            page_height = await self.page.evaluate("document.body.scrollHeight")
            viewport_height = await self.page.evaluate("window.innerHeight")
            
            # Calculate a random scroll distance
            max_scroll = page_height - viewport_height
            if max_scroll <= 0:
                return True  # Nothing to scroll
            
            # Create random scroll points
            scroll_points = []
            current_pos = 0
            
            # Add some randomness to the scrolling pattern
            while current_pos < max_scroll:
                # Random scroll amount between 100 and 500 pixels
                scroll_amount = random.randint(100, 500)
                current_pos = min(current_pos + scroll_amount, max_scroll)
                scroll_points.append(current_pos)
                
                # Sometimes scroll back up a bit (like a human searching)
                if random.random() < 0.2 and current_pos > 300:
                    backtrack = random.randint(50, 200)
                    current_pos = max(current_pos - backtrack, 0)
                    scroll_points.append(current_pos)
            
            # Execute the scrolling
            for position in scroll_points:
                await self.page.evaluate(f"window.scrollTo(0, {position})")
                # Variable wait time between scrolls
                await asyncio.sleep(random.uniform(0.3, 1.2))
            
            return True
            
        except Exception as e:
            logger.error(f"Error scrolling: {str(e)}")
            return False
    
    async def execute_action(self, action_type, params):
        """Execute an action with Playwright"""
        if not self.page:
            logger.error("Page not initialized")
            return False
        
        try:
            if action_type == "navigate":
                url = params.get("url", "")
                if not url:
                    logger.error("No URL provided for navigation")
                    return False
                
                logger.info(f"Navigating to {url}")
                
                # Add randomness to request headers
                extra_headers = {
                    "Accept-Language": random.choice(["en-US,en;q=0.9", "en-AU,en;q=0.8,en-US;q=0.6"]),
                    "Cache-Control": random.choice(["max-age=0", "no-cache", "no-store"]),
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-User": "?1",
                }
                
                await self.page.set_extra_http_headers(extra_headers)
                
                # Navigate with timeout and wait options
                await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                # Random wait after navigation to simulate human reading
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                # Take screenshot
                await self._take_screenshot(f"navigate_{url.replace('://', '_').replace('/', '_')}")
                
                # Scroll randomly to simulate human behavior
                await self.scroll_randomly()
                
                return True
                
            elif action_type == "click":
                selector = params.get("selector", "")
                force = params.get("force", False)
                
                if not selector:
                    logger.error("No selector provided for click")
                    return False
                
                logger.info(f"Clicking element with selector: {selector}")
                
                # Add randomness to click behavior
                await asyncio.sleep(random.uniform(0.3, 1.0))
                
                # Move mouse randomly before clicking
                await self.move_mouse_randomly()
                
                # Try multiple ways to find and click the element
                try:
                    # First check if element exists
                    element = await self.page.query_selector(selector)
                    
                    if not element:
                        logger.warning(f"Element with selector {selector} not found")
                        return False
                    
                    # Scroll element into view with smooth behavior
                    await self.page.evaluate(f"""(selector) => {{
                        const element = document.querySelector(selector);
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        }}
                    }}""", selector)
                    
                    # Wait a bit after scrolling
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    
                    # Click with randomized delay
                    await self.page.click(selector, delay=random.randint(50, 150), force=force)
                    
                    # Take screenshot after click
                    await self._take_screenshot(f"click_{selector.replace(' > ', '_').replace(':', '_')}")
                    
                    # Wait a bit after clicking
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                    return True
                    
                except Exception as e:
                    logger.warning(f"Failed to click with selector {selector}: {str(e)}")
                    
                    # Try clicking by JavaScript as fallback
                    try:
                        await self.page.evaluate(f"""(selector) => {{
                            const element = document.querySelector(selector);
                            if (element) {{
                                element.click();
                            }}
                        }}""", selector)
                        
                        logger.info(f"Clicked element with JS fallback: {selector}")
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        return True
                    except Exception as js_e:
                        logger.error(f"JS click fallback failed: {str(js_e)}")
                        return False
                
            elif action_type == "input":
                selector = params.get("selector", "")
                value = params.get("value", "")
                
                if not selector:
                    logger.error("No selector provided for input")
                    return False
                
                logger.info(f"Entering text into input: {selector}")
                
                # Humanize typing
                try:
                    # First check if element exists
                    element = await self.page.query_selector(selector)
                    
                    if not element:
                        logger.warning(f"Input element with selector {selector} not found")
                        return False
                    
                    # Scroll to the element
                    await self.page.evaluate(f"""(selector) => {{
                        const element = document.querySelector(selector);
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        }}
                    }}""", selector)
                    
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    
                    # Click to focus with a delay
                    await self.page.click(selector, delay=random.randint(30, 100))
                    
                    # Clear any existing value
                    await self.page.evaluate(f"""(selector) => {{
                        const element = document.querySelector(selector);
                        if (element) {{
                            element.value = '';
                        }}
                    }}""", selector)
                    
                    # Type with variable speed like a human
                    for char in value:
                        # Add random pauses for more realistic typing
                        if random.random() < 0.1:  # 10% chance for a longer pause
                            await asyncio.sleep(random.uniform(0.1, 0.3))
                        
                        await self.page.type(selector, char, delay=random.randint(50, 200))
                        await asyncio.sleep(random.uniform(0.01, 0.05))
                    
                    # Take screenshot after input
                    await self._take_screenshot(f"input_{selector.replace(' > ', '_').replace(':', '_')}")
                    
                    # Simulate a short pause after typing (like a human checking their input)
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Failed to input text: {str(e)}")
                    return False
                
            elif action_type == "select":
                selector = params.get("selector", "")
                value = params.get("value", "")
                
                if not selector:
                    logger.error("No selector provided for select")
                    return False
                
                logger.info(f"Selecting option {value} from {selector}")
                
                try:
                    # Check if element exists
                    element = await self.page.query_selector(selector)
                    
                    if not element:
                        logger.warning(f"Select element with selector {selector} not found")
                        return False
                    
                    # Scroll to the element
                    await self.page.evaluate(f"""(selector) => {{
                        const element = document.querySelector(selector);
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        }}
                    }}""", selector)
                    
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    
                    # Click to open dropdown with delay
                    await self.page.click(selector, delay=random.randint(30, 100))
                    
                    # Wait for the dropdown to open
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    
                    # Select the option
                    await self.page.select_option(selector, value)
                    
                    # Take screenshot after selection
                    await self._take_screenshot(f"select_{selector.replace(' > ', '_').replace(':', '_')}")
                    
                    # Wait after selection
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Failed to select option: {str(e)}")
                    return False
                
            elif action_type == "wait":
                time_ms = params.get("time", 1000)
                reason = params.get("reason", "general wait")
                
                logger.info(f"Waiting {time_ms}ms - {reason}")
                
                # Add slight randomness to the wait time
                adjusted_time = time_ms * random.uniform(0.9, 1.1)
                await asyncio.sleep(adjusted_time / 1000)
                
                return True
                
            elif action_type == "extract":
                selector = params.get("selector", "")
                
                if not selector:
                    logger.error("No selector provided for extraction")
                    return False
                
                logger.info(f"Extracting data from elements with selector: {selector}")
                
                try:
                    # Find all matching elements
                    elements = await self.page.query_selector_all(selector)
                    
                    if not elements:
                        logger.warning(f"No elements found with selector: {selector}")
                        return []
                    
                    # Extract data from each element
                    data = []
                    for element in elements:
                        text = await element.text_content()
                        data.append({
                            "text": text.strip(),
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    logger.info(f"Extracted {len(data)} items")
                    return data
                    
                except Exception as e:
                    logger.error(f"Error extracting data: {str(e)}")
                    return []
                
            else:
                logger.warning(f"Unsupported action type: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing {action_type}: {str(e)}")
            return False
    
    async def _take_screenshot(self, name_prefix):
        """Take a screenshot with timestamp and prefix"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name_prefix}_{timestamp}.png"
            path = os.path.join(self.screenshot_dir, filename)
            
            await self.page.screenshot(path=path)
            logger.debug(f"Screenshot saved: {path}")
            return path
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return None
    
    async def get_page_content(self):
        """Get current page content with enhanced extraction"""
        if not self.page:
            logger.error("Page not initialized")
            return {
                "title": "Error",
                "url": "",
                "error": "Page not initialized"
            }
        
        try:
            # Get page title
            title = await self.page.title()
            
            # Get page URL
            url = self.page.url
            
            # Extract visible text
            visible_text = await self.page.evaluate("""() => {
                return document.body.innerText;
            }""")
            
            # Extract form fields
            form_fields = await self.page.evaluate("""() => {
                const forms = document.querySelectorAll('form');
                const fields = [];
                
                forms.forEach(form => {
                    const formFields = form.querySelectorAll('input, select, textarea');
                    formFields.forEach(field => {
                        const type = field.tagName.toLowerCase() === 'input' ? field.type : field.tagName.toLowerCase();
                        const name = field.name || '';
                        const id = field.id || '';
                        const value = field.value || '';
                        const placeholder = field.placeholder || '';
                        
                        fields.push({
                            type,
                            name,
                            id,
                            value,
                            placeholder
                        });
                    });
                });
                
                return fields;
            }""")
            
            # Extract interactive elements
            interactive_elements = await self.page.evaluate("""() => {
                const elements = [];
                const interactiveSelector = 'a, button, input, select, textarea, [role="button"], [role="link"]';
                const nodes = document.querySelectorAll(interactiveSelector);
                
                nodes.forEach(node => {
                    // Get element rect
                    const rect = node.getBoundingClientRect();
                    const inViewport = (
                        rect.top >= 0 &&
                        rect.left >= 0 &&
                        rect.bottom <= window.innerHeight &&
                        rect.right <= window.innerWidth
                    );
                    
                    // Get text content
                    let text = node.innerText || node.value || node.placeholder || '';
                    text = text.trim().substring(0, 100);
                    
                    // Get type
                    let type = node.tagName.toLowerCase();
                    if (node.hasAttribute('type')) {
                        type = `${type}[${node.getAttribute('type')}]`;
                    }
                    
                    // Determine purpose
                    let purpose = '';
                    if (node.tagName === 'A') purpose = 'link';
                    else if (node.tagName === 'BUTTON') purpose = 'button';
                    else if (node.tagName === 'INPUT') purpose = node.type || 'input';
                    else if (node.tagName === 'SELECT') purpose = 'dropdown';
                    else if (node.hasAttribute('role')) purpose = node.getAttribute('role');
                    
                    // Get CSS selector
                    let selector = '';
                    if (node.id) selector = `#${node.id}`;
                    else if (node.className) {
                        const classes = Array.from(node.classList).join('.');
                        if (classes) selector = `.${classes}`;
                    }
                    
                    // Add other selectors
                    const selectors = [];
                    if (selector) selectors.push(selector);
                    
                    // Add a CSS path
                    let path = '';
                    let current = node;
                    while (current && current !== document.body) {
                        let name = current.tagName.toLowerCase();
                        if (current.id) {
                            name += '#' + current.id;
                            path = name + (path ? ' > ' + path : '');
                            break;
                        } else {
                            let sibling = current, nth = 1;
                            while (sibling = sibling.previousElementSibling) {
                                if (sibling.tagName === current.tagName) nth++;
                            }
                            name += `:nth-child(${nth})`;
                        }
                        path = name + (path ? ' > ' + path : '');
                        current = current.parentElement;
                    }
                    if (path) selectors.push(path);
                    
                    // Add XPath
                    selectors.push(`//body//${node.tagName.toLowerCase()}[contains(text(),'${text.substring(0, 20).replace(/'/g, "\\'")}')]`);
                    
                    elements.push({
                        type,
                        text,
                        purpose,
                        inViewport,
                        selectors
                    });
                });
                
                return elements;
            }""")
            
            # Extract tables
            tables = await self.page.evaluate("""() => {
                const tableData = [];
                const tables = document.querySelectorAll('table');
                
                tables.forEach((table, tableIndex) => {
                    const headers = [];
                    const headerCells = table.querySelectorAll('th');
                    headerCells.forEach(th => {
                        headers.push(th.innerText.trim());
                    });
                    
                    const rows = [];
                    const tableRows = table.querySelectorAll('tbody tr');
                    tableRows.forEach(row => {
                        const cells = [];
                        const rowCells = row.querySelectorAll('td');
                        rowCells.forEach(cell => {
                            cells.push(cell.innerText.trim());
                        });
                        rows.push(cells);
                    });
                    
                    tableData.push({
                        index: tableIndex,
                        headers,
                        rows
                    });
                });
                
                return tableData;
            }""")
            
            # Extract Austender-specific elements
            austender_specific = await self.page.evaluate("""() => {
                // Determine current page context
                let pageContext = 'unknown';
                const url = window.location.href;
                
                if (url.includes('/atm/')) {
                    pageContext = 'atm_details';
                } else if (url.includes('/search/atm')) {
                    pageContext = 'atm_search';
                } else if (url.includes('/cn/')) {
                    pageContext = 'contract_notice_details';
                } else if (url.includes('/search/cn')) {
                    pageContext = 'contract_notice_search';
                } else if (url.includes('/user/login')) {
                    pageContext = 'login';
                } else if (url.includes('tenders.gov.au') && url.endsWith('/')) {
                    pageContext = 'homepage';
                }
                
                // Extract search form fields if on a search page
                let searchFields = [];
                if (pageContext.includes('search')) {
                    const searchForm = document.querySelector('form#search-form');
                    if (searchForm) {
                        const formFields = searchForm.querySelectorAll('input, select');
                        formFields.forEach(field => {
                            searchFields.push({
                                type: field.tagName.toLowerCase(),
                                name: field.name || '',
                                id: field.id || '',
                                value: field.value || ''
                            });
                        });
                    }
                }
                
                return {
                    page_context: pageContext,
                    search_fields: searchFields
                };
            }""")
            
            # Create page content structure
            page_content = {
                "title": title,
                "url": url,
                "visible_text": visible_text[:5000],  # Limit text size
                "interactive_elements": interactive_elements,
                "form_fields": form_fields,
                "tables": tables,
                "page_structure": {
                    "austender_specific": austender_specific
                }
            }
            
            return page_content
            
        except Exception as e:
            logger.error(f"Error getting page content: {str(e)}")
            return {
                "title": "Error",
                "url": self.page.url if self.page else "",
                "error": str(e)
            }
