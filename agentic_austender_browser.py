#!/usr/bin/env python3
"""
Agentic Austender Browser
------------------------
This script demonstrates a sophisticated agentic browser for navigating and
extracting data from the Austender website using OpenAI for decision-making
and Playwright for browser automation.
"""

import os
import json
import time
import random
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

# OpenAI for decision making
import openai
from openai import AsyncOpenAI

# Playwright for browser automation
from playwright.async_api import async_playwright, Page, Browser

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"agentic_austender_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("agentic_austender")

# Ensure directories exist
os.makedirs("screenshots", exist_ok=True)
os.makedirs("output", exist_ok=True)

# Austender URL
AUSTENDER_URL = "https://www.tenders.gov.au/"

# List of user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42"
]

class AgenticAustenderBrowser:
    """AI-driven browser agent for navigating and scraping Austender."""
    
    def __init__(self, 
                 headless: bool = False, 
                 slow_mo: int = 100,
                 model: str = "gpt-4o",
                 api_key: str = None,
                 max_retries: int = 3):
        """Initialize the agent with browser and LLM settings."""
        self.headless = headless
        self.slow_mo = slow_mo
        self.opportunities = []
        self.current_task = None
        self.task_history = []
        self.browser = None
        self.context = None
        self.page = None
        self.max_retries = max_retries
        
        # LLM model settings
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
        if not self.username or not self.password:
            logger.warning("AUSTENDER_USERNAME or AUSTENDER_PASSWORD not set; login may be required.")
            
        logger.info("Initialized Agentic Austender Browser")
    
    async def start_browser(self) -> None:
        """Start an async browser instance with anti-detection measures."""
        try:
            logger.info("Starting browser...")
            # Start Playwright in async mode
            self.playwright = await async_playwright().start()
            
            # Launch browser with specific options to avoid detection
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials"
                ]
            )
            
            # Create a context with custom viewport and user agent
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(USER_AGENTS),
                java_script_enabled=True,
                accept_downloads=True,
                ignore_https_errors=True
            )
            
            # Set additional properties to avoid detection
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                
                // Override properties used for bot detection
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en', 'es']
                });
                
                // Override permissions to appear more human-like
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            # Create a new page
            self.page = await self.context.new_page()
            
            # Add human-like behaviors and event listeners
            await self.page.evaluate("""
                // Add random mouse movements
                function randomMouseMovement() {
                    const event = new MouseEvent('mousemove', {
                        'view': window,
                        'bubbles': true,
                        'cancelable': true,
                        'clientX': Math.random() * window.innerWidth,
                        'clientY': Math.random() * window.innerHeight
                    });
                    document.dispatchEvent(event);
                    
                    if (Math.random() > 0.95) {
                        // Occasionally scroll a bit
                        window.scrollBy({
                            top: (Math.random() - 0.5) * 100,
                            behavior: 'smooth'
                        });
                    }
                    
                    setTimeout(randomMouseMovement, Math.random() * 2000 + 500);
                }
                
                randomMouseMovement();
            """)
            
            logger.info("Browser started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting browser: {str(e)}")
            await self.close()
            return False
    
    async def login(self) -> bool:
        """Log in to Austender if not already authenticated."""
        try:
            # Check if already logged in
            if await self.page.query_selector("a[href*='logout']"):
                logger.info("Already logged in")
                return True
                
            # Navigate to login page
            login_url = AUSTENDER_URL + "user/login"
            logger.info(f"Navigating to login page: {login_url}")
            await self.page.goto(login_url, wait_until="networkidle")
            
            # Take a screenshot for debugging
            await self.page.screenshot(path=f"screenshots/login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            # Add a small delay to appear more human-like
            await asyncio.sleep(1 + random.random() * 2)
            
            # Fill credentials with human-like typing
            await self.page.fill("input#edit-name", self.username, timeout=5000)
            await asyncio.sleep(0.5 + random.random())
            await self.page.fill("input#edit-pass", self.password, timeout=5000)
            await asyncio.sleep(0.3 + random.random() * 1.5)
            
            # Submit login form
            await self.page.click("input#edit-submit")
            
            # Wait for logout link as confirmation
            await self.page.wait_for_selector("a[href*='logout']", timeout=30000)
            logger.info("Login successful")
            
            # Take a screenshot after login
            await self.page.screenshot(path=f"screenshots/login_success_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            await self.page.screenshot(path=f"screenshots/login_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return False
    
    async def navigate_to(self, url: str) -> bool:
        """Navigate to a URL with human-like timing."""
        try:
            logger.info(f"Navigating to {url}")
            
            # Navigate to the URL with a timeout
            response = await self.page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Add random waiting time to simulate human behavior
            wait_time = 1 + (2 * random.random())
            await asyncio.sleep(wait_time)
            
            # Take a screenshot for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.page.screenshot(path=f"screenshots/navigation_{timestamp}.png")
            
            # Log page title to confirm we're on the right page
            title = await self.page.title()
            logger.info(f"Page loaded: {title}")
            
            # Add to history
            self.task_history.append({
                "action": "navigate",
                "url": url,
                "timestamp": timestamp,
                "success": response.ok if response else False,
                "title": title
            })
            
            return response.ok if response else False
            
        except Exception as e:
            logger.error(f"Error navigating to {url}: {str(e)}")
            return False
    
    async def get_page_content(self) -> Dict:
        """Get the current page content for AI analysis with enhanced awareness."""
        try:
            # Take a screenshot for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/page_analysis_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Get the page title
            title = await self.page.title()
            
            # Get the current URL
            url = self.page.url
            
            # Enhanced content extraction with metadata about page state
            page_metadata = await self.page.evaluate("""() => {
                return {
                    viewport_width: window.innerWidth,
                    viewport_height: window.innerHeight,
                    document_height: document.body.scrollHeight,
                    scroll_position: window.scrollY,
                    has_forms: document.forms.length > 0,
                    form_count: document.forms.length,
                    iframe_count: document.querySelectorAll('iframe').length,
                    is_login_page: document.body.innerHTML.toLowerCase().includes('login') || 
                                  document.body.innerHTML.toLowerCase().includes('sign in'),
                    has_captcha: document.body.innerHTML.toLowerCase().includes('captcha') || 
                                document.body.innerHTML.toLowerCase().includes('robot'),
                    page_load_time: window.performance ? 
                        (window.performance.timing.loadEventEnd - window.performance.timing.navigationStart) : null
                };
            }""")
            
            # Get visible text content with better parsing
            content = await self.page.evaluate("""() => {
                // Function to clean text content
                const cleanText = (text) => {
                    return text.replace(/\s+/g, ' ').trim();
                };
                
                // Get main content
                const mainContent = document.querySelector('main') || 
                                   document.querySelector('#content') || 
                                   document.querySelector('.content') ||
                                   document.body;
                                   
                // Get headings for structure awareness
                const headings = Array.from(document.querySelectorAll('h1, h2, h3')).map(h => {
                    return {
                        level: parseInt(h.tagName.substring(1)),
                        text: cleanText(h.innerText)
                    };
                });
                
                // Look for specific sections in Austender
                const austenderSections = {
                    search_form: document.querySelector('form#search-form') ? true : false,
                    results_table: document.querySelector('table.views-table') ? true : false,
                    pagination: document.querySelector('.pager') ? true : false,
                    navigation_menu: document.querySelector('nav') ? true : false,
                    login_form: document.querySelector('form#user-login-form') ? true : false
                };
                
                return {
                    full_text: document.body.innerText,
                    main_content_text: mainContent.innerText,
                    headings: headings,
                    page_sections: austenderSections,
                    meta_description: document.querySelector('meta[name="description"]')?.content || ''
                };
            }""")
            
            # Enhanced interactive element analysis with better detection and classification
            interactive_elements = await self.page.evaluate("""() => {
                // Better, more nuanced element detection
                const getAccessibleName = (el) => {
                    // Check aria-label
                    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
                    
                    // Check inner text
                    if (el.innerText) return el.innerText.trim();
                    
                    // Check alt text for images
                    const img = el.querySelector('img');
                    if (img && img.alt) return img.alt;
                    
                    // Check title attribute
                    if (el.title) return el.title;
                    
                    // Check placeholder for inputs
                    if (el.placeholder) return el.placeholder;
                    
                    // Check value for inputs
                    if (el.value && typeof el.value === 'string') return el.value;
                    
                    // Check aria-describedby
                    if (el.getAttribute('aria-describedby')) {
                        const describedBy = document.getElementById(el.getAttribute('aria-describedby'));
                        if (describedBy) return describedBy.innerText.trim();
                    }
                    
                    return '';
                };
                
                // Get all potentially interactive elements
                const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [role="tab"], [role="menuitem"], [role="combobox"], [role="search"], [tabindex="0"]';
                const elements = Array.from(document.querySelectorAll(interactiveSelectors));
                
                // Process elements
                const processedElements = [];
                elements.forEach(el => {
                    // Skip truly hidden elements
                    const style = window.getComputedStyle(el);
                    const isHidden = style.display === 'none' || 
                                    style.visibility === 'hidden' || 
                                    style.opacity === '0' || 
                                    el.offsetParent === null ||
                                    (el.getAttribute('aria-hidden') === 'true' && !el.hasAttribute('tabindex'));
                    
                    if (isHidden) return;
                    
                    // Get accessible name and visible text
                    const name = getAccessibleName(el);
                    const text = el.innerText || el.textContent || '';
                    const cleanedText = text.replace(/\s+/g, ' ').trim().substring(0, 100);
                    
                    // Determine element purpose/type
                    let purpose = 'unknown';
                    
                    // Check for search-related elements
                    if (el.id && el.id.toLowerCase().includes('search') || 
                        el.name && el.name.toLowerCase().includes('search') ||
                        el.placeholder && el.placeholder.toLowerCase().includes('search') ||
                        name.toLowerCase().includes('search')) {
                        purpose = 'search';
                    }
                    // Check for navigation elements
                    else if (el.tagName === 'A' || el.getAttribute('role') === 'link') {
                        purpose = 'navigation';
                    }
                    // Check for form controls
                    else if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName) || 
                             ['checkbox', 'radio', 'combobox'].includes(el.getAttribute('role'))) {
                        purpose = 'form_control';
                    }
                    // Check for buttons/actions
                    else if (el.tagName === 'BUTTON' || 
                             el.getAttribute('role') === 'button' || 
                             (el.tagName === 'INPUT' && ['submit', 'button', 'reset'].includes(el.type))) {
                        purpose = 'action';
                    }
                    
                    // Create robust selectors - try multiple strategies
                    const selectors = [];
                    
                    // ID-based selector (most reliable)
                    if (el.id) {
                        selectors.push(`#${el.id}`);
                    }
                    
                    // Name-based selector for form elements
                    if (el.name) {
                        selectors.push(`[name="${el.name}"]`);
                    }
                    
                    // Class-based selector
                    if (el.className && typeof el.className === 'string' && el.className.trim()) {
                        const classes = el.className.trim().split(/\s+/).join('.');
                        selectors.push(`.${classes}`);
                    }
                    
                    // Attribute-based selectors
                    if (el.type) {
                        selectors.push(`${el.tagName.toLowerCase()}[type="${el.type}"]`);
                    }
                    
                    // Position-based selector (fallback)
                    const parent = el.parentElement;
                    if (parent && parent.children.length < 10) {
                        const index = Array.from(parent.children).indexOf(el);
                        const parentSelector = parent.id ? `#${parent.id}` : parent.tagName.toLowerCase();
                        selectors.push(`${parentSelector} > ${el.tagName.toLowerCase()}:nth-child(${index + 1})`);
                    }
                    
                    // Text-based selector (can be fragile)
                    if (cleanedText && cleanedText.length < 50) {
                        const safeText = cleanedText.replace(/"/g, '\\\'').substring(0, 40);
                        selectors.push(`${el.tagName.toLowerCase()}:contains("${safeText}")`);
                    }
                    
                    // Get bounding client rect for visibility and positioning
                    const rect = el.getBoundingClientRect();
                    const inViewport = rect.top >= 0 && 
                                        rect.left >= 0 && 
                                        rect.bottom <= window.innerHeight && 
                                        rect.right <= window.innerWidth;
                    
                    processedElements.push({
                        type: el.tagName.toLowerCase(),
                        text: cleanedText,
                        purpose: purpose,
                        name: name,
                        selectors: selectors, // Multiple selectors for better targeting
                        primary_selector: selectors[0] || el.tagName.toLowerCase(), // Best selector to use
                        in_viewport: inViewport,
                        position: {
                            top: rect.top,
                            left: rect.left,
                            bottom: rect.bottom,
                            right: rect.right,
                            width: rect.width,
                            height: rect.height
                        },
                        attributes: {
                            href: el.tagName === 'A' ? el.href : null,
                            type: el.type || null,
                            name: el.name || null,
                            value: el.value || null,
                            placeholder: el.placeholder || null,
                            role: el.getAttribute('role') || null,
                            aria_label: el.getAttribute('aria-label') || null
                        }
                    });
                });
                
                // Sort by viewport visibility and size (bigger, more central elements first)
                return processedElements.sort((a, b) => {
                    // Viewport elements get priority
                    if (a.in_viewport && !b.in_viewport) return -1;
                    if (!a.in_viewport && b.in_viewport) return 1;
                    
                    // Then by vertical position (top to bottom)
                    return a.position.top - b.position.top;
                }).slice(0, 50); // Limit to top 50 elements
            }""")
            
            # Get specific page structures and extract key information
            page_structure = await self.page.evaluate("""() => {
                // Detect common types of structured data
                const findTableData = () => {
                    const tables = Array.from(document.querySelectorAll('table'));
                    return tables.map(table => {
                        // Get header data
                        const headers = Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim());
                        
                        // Get row data
                        const rows = Array.from(table.querySelectorAll('tr')).slice(headers.length > 0 ? 1 : 0);
                        const rowData = rows.map(row => {
                            const cells = Array.from(row.querySelectorAll('td')).map(td => td.innerText.trim());
                            // Create row object with header names as keys when available
                            if (headers.length > 0 && headers.length === cells.length) {
                                const rowObj = {};
                                headers.forEach((header, i) => {
                                    rowObj[header] = cells[i];
                                });
                                return rowObj;
                            }
                            return cells;
                        });
                        
                        return {
                            headers,
                            rows: rowData,
                            table_id: table.id || null,
                            table_class: table.className || null,
                            row_count: rows.length
                        };
                    });
                };
                
                // Detect forms - very important for Austender
                const findForms = () => {
                    const forms = Array.from(document.querySelectorAll('form'));
                    return forms.map(form => {
                        const inputs = Array.from(form.querySelectorAll('input, select, textarea')).map(input => {
                            return {
                                type: input.tagName.toLowerCase(),
                                input_type: input.type || null,
                                name: input.name || null,
                                id: input.id || null,
                                placeholder: input.placeholder || null,
                                label: input.labels && input.labels[0] ? input.labels[0].innerText.trim() : null,
                                value: input.value || null,
                                options: input.tagName === 'SELECT' ? 
                                         Array.from(input.options).map(opt => opt.innerText.trim()) : null
                            };
                        });
                        
                        const submitButtons = Array.from(form.querySelectorAll('button[type="submit"], input[type="submit"]')).map(btn => {
                            return {
                                id: btn.id || null,
                                text: btn.innerText || btn.value || null,
                                class: btn.className || null
                            };
                        });
                        
                        return {
                            form_id: form.id || null,
                            form_name: form.name || null,
                            form_action: form.action || null,
                            form_method: form.method || null,
                            inputs: inputs,
                            submit_buttons: submitButtons
                        };
                    });
                };
                
                // Find navigation structures
                const findNavigation = () => {
                    const navElements = Array.from(document.querySelectorAll('nav, [role="navigation"], .navigation, .menu, .nav, .navbar'));
                    return navElements.map(nav => {
                        const links = Array.from(nav.querySelectorAll('a')).map(link => {
                            return {
                                text: link.innerText.trim(),
                                href: link.href,
                                active: link.classList.contains('active') || 
                                       link.classList.contains('current') || 
                                       link.getAttribute('aria-current') === 'page'
                            };
                        });
                        
                        return {
                            nav_id: nav.id || null,
                            nav_class: nav.className || null,
                            links: links
                        };
                    });
                };
                
                // Austender-specific structures
                const findAustenderStructures = () => {
                    // Look for the search form
                    const searchForm = document.querySelector('#search-form, form[action*="search"], form[action*="atm"]');
                    
                    // Look for opportunity listings
                    const opportunityTable = document.querySelector('table.views-table, table.atm-table, table[summary*="opportunities"]');
                    
                    // Look for pagination
                    const pagination = document.querySelector('.pager, .pagination, nav[role="navigation"][aria-labelledby*="pagination"]');
                    
                    // Look for ATM details
                    const atmDetails = document.querySelector('.atm-details, .node--type-atm, [about*="atm"]');
                    
                    // Detect current page context
                    let pageContext = 'unknown';
                    if (document.body.innerHTML.toLowerCase().includes('login') && document.querySelector('form[action*="user"]')) {
                        pageContext = 'login_page';
                    } else if (searchForm) {
                        pageContext = 'search_page';
                    } else if (opportunityTable) {
                        pageContext = 'results_page';
                    } else if (atmDetails) {
                        pageContext = 'opportunity_details_page';
                    } else if (document.location.pathname === '/' || document.location.pathname === '') {
                        pageContext = 'home_page';
                    }
                    
                    return {
                        page_context: pageContext,
                        has_search_form: searchForm !== null,
                        has_opportunity_table: opportunityTable !== null,
                        has_pagination: pagination !== null,
                        has_atm_details: atmDetails !== null
                    };
                };
                
                return {
                    tables: findTableData(),
                    forms: findForms(),
                    navigation: findNavigation(),
                    austender_specific: findAustenderStructures()
                };
            }""")
            
            # Return comprehensive data
            return {
                "title": title,
                "url": url,
                "screenshot": screenshot_path,
                "page_metadata": page_metadata,
                "content": content,
                "interactive_elements": interactive_elements,
                "page_structure": page_structure
            }
            
        except Exception as e:
            logger.error(f"Error getting page content: {str(e)}")
            # Take error screenshot
            await self.page.screenshot(path=f"screenshots/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return {"error": str(e)}
    
    async def analyze_page_with_ai(self, task: str) -> Dict:
        """Analyze the page content with AI to determine next actions with enhanced page awareness."""
        try:
            # Get enhanced page content with detailed structure
            page_data = await self.get_page_content()
            
            # Build improved system prompt with Austender-specific knowledge
            system_prompt = """
            You are an expert web automation agent specialized in the Australian Government's AusTender website.
            Your job is to analyze webpage content and provide clear, structured guidance for navigating
            and extracting procurement information.
            
            Important details about AusTender website:
            1. The site uses Drupal as its CMS and has forms for searching procurement opportunities
            2. The main sections include: Home, Approaches to Market (ATM), Contract Notices, and Agency Resources
            3. The ATM search page allows filtering by keyword, category, date, agency, etc.
            4. Tables of results show procurement opportunities with ID numbers, titles, categories, etc.
            5. Login forms typically need a username and password and might have CAPTCHA
            
            Focus on:
            1. Identifying the current page context (home, search, results, details, login)
            2. Finding the most relevant interactive elements for the task
            3. Providing precise selectors with alternatives for reliability
            4. Taking human-like actions that won't trigger anti-bot measures
            5. Intelligently navigating through the site's structure
            
            Provide clear, actionable instructions with specific selectors and values.
            """
            
            # Extract key information from the enhanced page data
            page_title = page_data.get('title', 'Unknown Title')
            page_url = page_data.get('url', 'Unknown URL')
            screenshot_path = page_data.get('screenshot', 'No screenshot')
            
            # Get content structure information
            if isinstance(page_data.get('content'), dict):
                content_text = page_data['content'].get('full_text', '')[:1500] + '...'
                headings = page_data['content'].get('headings', [])
                page_sections = page_data['content'].get('page_sections', {})
            else:  # Fallback for older format
                content_text = str(page_data.get('content', ''))[:1500] + '...'
                headings = []
                page_sections = {}
            
            # Get interactive elements and page structure
            interactive_elements = page_data.get('interactive_elements', [])
            page_structure = page_data.get('page_structure', {})
            page_metadata = page_data.get('page_metadata', {})
            
            # Determine the current page context
            page_context = 'unknown'
            if page_structure and 'austender_specific' in page_structure:
                page_context = page_structure['austender_specific'].get('page_context', 'unknown')
            
            # Build detailed user prompt
            user_prompt = f"""
            Task: {task}
            
            Current page:
            - Title: {page_title}
            - URL: {page_url}
            - Context: {page_context}
            - Screenshot saved: {screenshot_path}
            
            Page analysis:
            - Has forms: {page_metadata.get('has_forms', False)}
            - Is login page: {page_metadata.get('is_login_page', False)}
            - Has CAPTCHA: {page_metadata.get('has_captcha', False)}
            
            Key headings:
            {json.dumps(headings[:3], indent=2)}
            
            Available interactive elements (top 10):
            {json.dumps([{
                'type': el.get('type', ''),
                'text': el.get('text', ''),
                'purpose': el.get('purpose', ''),
                'selectors': el.get('selectors', [el.get('primary_selector', '')]),
                'in_viewport': el.get('in_viewport', False),
                'attributes': el.get('attributes', {})
            } for el in interactive_elements[:10]], indent=2)}
            
            Form details (if any):
            {json.dumps(page_structure.get('forms', [])[:1], indent=2)}
            
            Table data (if any):
            {json.dumps(page_structure.get('tables', [])[:1], indent=2)}
            
            Austender-specific context:
            {json.dumps(page_structure.get('austender_specific', {}), indent=2)}
            
            Based on this analysis, suggest 1-3 specific actions to progress the task.
            For each action, provide:
            1. Action type (click, input, select, scroll, etc.)
            2. Multiple selectors for better targeting (provide at least 2 if possible)
            3. Value to input (if applicable)
            4. A clear explanation of why this action is appropriate
            
            Format your response as a JSON array of actions:
            [
              {
                "action": "click|input|select|etc",
                "selectors": ["primary-selector", "alternative-selector"],
                "value": "input value if needed",
                "explanation": "Why this action helps accomplish the task"
              }
            ]
            
            Only include the JSON output, no additional text or explanation.
            """
            
            # Call OpenAI API
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            completion = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            
            response_text = completion.choices[0].message.content
            
            # Parse the JSON response
            try:
                actions = json.loads(response_text)
                logger.info(f"AI analysis complete, suggested {len(actions)} actions")
                return {"success": True, "actions": actions}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}\nResponse: {response_text}")
                # Attempt to extract JSON from the response
                json_match = re.search(r'\[\s*{.*}\s*\]', response_text, re.DOTALL)
                if json_match:
                    try:
                        extracted_json = json_match.group(0)
                        actions = json.loads(extracted_json)
                        logger.info(f"Extracted JSON from response, found {len(actions)} actions")
                        return {"success": True, "actions": actions}
                    except json.JSONDecodeError:
                        pass
                
                # If everything fails, create a simple response to continue navigation
                fallback_actions = [
                    {
                        "action": "reload",
                        "selectors": [],
                        "explanation": "Reload the page due to analysis failure and try again."
                    }
                ]
                
                return {"success": False, "error": "Failed to parse AI response as JSON", "raw_response": response_text, "fallback_actions": fallback_actions}
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            # Take an error screenshot
            await self.page.screenshot(path=f"screenshots/analysis_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return {"success": False, "error": str(e)}
    async def execute_action(self, action: Dict) -> bool:
        """Execute a single action as directed by the AI with enhanced selector handling."""
        try:
            # Extract action details (using updated field names)
            action_type = action.get("action", "").lower()  # Changed from action_type to action
            selectors = action.get("selectors", [])  # Now supports an array of selectors
            value = action.get("value", "")
            explanation = action.get("explanation", "No explanation provided")
            
            # Handle single selector format (backward compatibility)
            if "selector" in action and not selectors:
                selectors = [action["selector"]]
            
            # If we still don't have selectors, check if there's just a single selector string
            if not selectors and isinstance(action.get("selector", ""), str) and action.get("selector", ""):
                selectors = [action.get("selector")]
            
            logger.info(f"Executing action: {action_type} with {len(selectors)} selector(s) - {explanation}")
            
            # Handle special action types
            if action_type == "reload":
                logger.info("Reloading the page")
                await self.page.reload()
                await self.page.wait_for_load_state("networkidle")
                return True
            
            if action_type == "scroll":
                direction = value.lower() if value else "down"
                scroll_amount = 300 if direction == "down" else -300
                
                logger.info(f"Scrolling {direction}")
                await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(1)  # Wait for scroll to complete
                return True
            
            if action_type == "wait":
                wait_time = int(value) if value and value.isdigit() else 3
                logger.info(f"Waiting for {wait_time} seconds")
                await asyncio.sleep(wait_time)
                return True
            
            # For element interactions, try all provided selectors
            if not selectors:  # If we somehow still don't have selectors
                logger.error(f"No selectors provided for {action_type} action")
                return False
            
            # If this is for keywords, add common Austender keyword input selectors
            if any("keyword" in s.lower() for s in selectors) and action_type == "input":
                extra_selectors = [
                    "input[name='keyword']", 
                    "#search-text",
                    "input.searchField",
                    "#keyword",
                    "input[title*='keyword']",
                    "input.form-text",
                    "#edit-keyword",
                    ".search-input"
                ]
                # Add these selectors if they're not already in the list
                for s in extra_selectors:
                    if s not in selectors:
                        selectors.append(s)
            
            # Try each selector until one works
            success = False
            for selector in selectors:
                try:
                    # For visible elements only, use this stricter check
                    js_visible_check = f"""
                    () => {{  
                        const el = document.querySelector("{selector}");
                        if (!el) return false;
                        
                        const style = window.getComputedStyle(el);
                        return el.offsetParent !== null && 
                               style.display !== 'none' && 
                               style.visibility !== 'hidden' && 
                               parseFloat(style.opacity) > 0 &&
                               el.getBoundingClientRect().width > 0 &&
                               el.getBoundingClientRect().height > 0;
                    }}
                    """
                    
                    is_visible = await self.page.evaluate(js_visible_check)
                    if not is_visible:
                        logger.debug(f"Element with selector '{selector}' is not visible or doesn't exist")
                        continue
                    
                    # Wait for selector with timeout
                    element = await self.page.wait_for_selector(selector, timeout=3000, state="visible")
                    if not element:
                        logger.debug(f"Element with selector '{selector}' not found or not visible")
                        continue
                        
                    # Execute the appropriate action
                    if action_type == "click":
                        # Try a more human-like click with random offset from center
                        try:
                            # Get element dimensions
                            rect = await element.bounding_box()
                            if rect:
                                # Click with a slightly random position within the element
                                import random
                                x_offset = random.uniform(5, max(6, rect['width'] - 5))
                                y_offset = random.uniform(5, max(6, rect['height'] - 5))
                                
                                # Click with a position
                                await element.click(position={"x": x_offset, "y": y_offset})
                            else:
                                # Fallback to regular click
                                await element.click()
                        except Exception as e:
                            logger.warning(f"Human-like click failed: {str(e)}. Trying standard click.")
                            # Fallback to JavaScript click
                            await self.page.evaluate(f"document.querySelector('{selector}').click()")
                            
                        logger.info(f"Successfully clicked on {selector}")
                        success = True
                        break
                        
                    elif action_type == "input":
                        # Clear the input first
                        await element.fill("")
                        # Type the value with a human-like delay
                        await element.type(value, delay=random.uniform(50, 150))
                        logger.info(f"Successfully entered '{value}' into {selector}")
                        success = True
                        break
                        
                    elif action_type == "select":
                        # For dropdown selection
                        await element.select_option(value=value)
                        logger.info(f"Successfully selected '{value}' from {selector}")
                        success = True
                        break
                        
                    elif action_type == "check" or action_type == "uncheck":
                        # For checkboxes
                        current_state = await element.is_checked()
                        target_state = action_type == "check"
                        
                        if current_state != target_state:
                            await element.check() if target_state else await element.uncheck()
                            logger.info(f"Successfully {'checked' if target_state else 'unchecked'} {selector}")
                        else:
                            logger.info(f"Checkbox {selector} already in desired state ({action_type})")
                        
                        success = True
                        break
                        
                except Exception as e:
                    logger.debug(f"Failed to interact with {selector}: {str(e)}")
                    # Continue trying the next selector
            
            if not success:
                logger.error(f"All selectors failed for {action_type} action: {selectors}")
                
                # Take a screenshot of the failure
                await self.page.screenshot(path=f"screenshots/action_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                
                # If it was a click action and all selectors failed, try looking for text-based links
                if action_type == "click" and value:
                    logger.info(f"Trying to find element by text content: '{value}'")
                    try:
                        # Try to find by text content
                        text_selector = f"text='{value}'"
                        text_element = await self.page.wait_for_selector(text_selector, timeout=3000)
                        if text_element:
                            await text_element.click()
                            logger.info(f"Successfully clicked on element with text: {value}")
                            return True
                    except Exception as e:
                        logger.error(f"Could not find element by text content: {str(e)}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            await self.page.screenshot(path=f"screenshots/action_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return False
            
    # Special case for state dropdown on Austender
    async def handle_state_selection(self, selector: str, value: str) -> bool:
        """Handle selection of Australian state in dropdowns - special case for Austender."""
        try:
            possible_selectors = [
                "select[name='state']",
                "#edit-field-atm-state-value",
                ".form-select[name*='state']",
                "select.form-select"
            ]
            
            for possible_selector in possible_selectors:
                try:
                    element = await self.page.query_selector(possible_selector)
                    if element:
                        logger.info(f"Found state dropdown with selector: {possible_selector}")
                        # Try to select the value
                        await self.page.select_option(possible_selector, value)
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.warning(f"Failed with selector {possible_selector}: {str(e)}")
                    continue
            
            # If we get here, try to find any form element that might work for state
            try:
                # Try to find a dropdown or radio button for states
                await self.page.evaluate(f"""() => {{
                    // Try to find any input related to states
                    const stateElements = Array.from(document.querySelectorAll('select, input[type="radio"], input[type="checkbox"]'));
                    const stateElement = stateElements.find(el => 
                        (el.name && el.name.toLowerCase().includes('state')) || 
                        (el.id && el.id.toLowerCase().includes('state')) ||
                        (el.className && el.className.toLowerCase().includes('state')));
                        
                    if (stateElement) {{
                        if (stateElement.tagName === 'SELECT') {{
                            // It's a dropdown
                            const option = Array.from(stateElement.options).find(opt => 
                                opt.text.includes('{value}') || opt.value.includes('{value}'));
                            if (option) stateElement.value = option.value;
                        }} else {{
                            // It's a radio button or checkbox
                            stateElement.checked = true;
                        }}
                        stateElement.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}""")
                await asyncio.sleep(1)
                return True
            except Exception as e:
                logger.error(f"Error with fallback state selection: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error in handle_state_selection: {str(e)}")
            return False
            
    # Special case for submitting searches on Austender
    async def handle_submit(self, selector: str) -> bool:
        """Handle submit buttons on search forms - special case for Austender."""
        try:
            possible_selectors = [
                "button[type='submit']",
                "#search-submit",
                "input[type='submit']",
                ".btn-search",
                "button.form-submit",
                "#edit-submit-atm-search"
            ]
            
            for possible_selector in possible_selectors:
                try:
                    element = await self.page.query_selector(possible_selector)
                    if element:
                        logger.info(f"Found submit button with selector: {possible_selector}")
                        await self.page.click(possible_selector)
                        await asyncio.sleep(2 + random.random() * 2)
                        return True
                except Exception as e:
                    logger.warning(f"Failed with selector {possible_selector}: {str(e)}")
            print(f"Task: {custom_task}")
            print(f"Steps completed: {len(results.get('steps', []))}")
            if results.get("success", False):
                print("Status: SUCCESS")
                    
            if box:
                # Click with a specific position for more human-like behavior
                await self.page.click(selector, position={"x": box["x"], "y": box["y"]}, timeout=5000)
                        # Fallback to regular click
                        await self.page.click(selector, timeout=5000)
                        
                        const element = document.querySelector('{selector}');
                        if (element) element.value = '';
                    }}""")
                    
                    # Type the value with human-like typing speed
                    await self.page.fill(selector, value, timeout=5000)
                    
                    # Add a small delay after typing
                    await asyncio.sleep(0.5 + random.random())
                    return True
                except Exception as e:
                    logger.warning(f"Standard input failed: {str(e)}. Trying JavaScript input.")
                    # Try JavaScript input as fallback
                    try:
                        await self.page.evaluate(f"""() => {{
                            const element = document.querySelector('{selector}');
                            if (element) {{
                                element.value = '{value}';
                                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}""")
                        await asyncio.sleep(0.5 + random.random())
                        return True
                    except Exception as e2:
                        logger.error(f"JavaScript input also failed: {str(e2)}")
                        return False
                
            elif action_type == "scroll":
                # Extract scroll parameters
                direction = value.lower() if value else "down"
                
                if direction == "down":
                    await self.page.evaluate("""() => {
                        window.scrollBy({
                            top: 300 + Math.random() * 200,
                            behavior: 'smooth'
                        });
                    }""")
                elif direction == "up":
                    await self.page.evaluate("""() => {
                        window.scrollBy({
                            top: -300 - Math.random() * 200,
                            behavior: 'smooth'
                        });
                    }""")
                elif direction == "bottom":
                    await self.page.evaluate("""() => {
                        window.scrollTo({
                            top: document.body.scrollHeight,
                            behavior: 'smooth'
                        });
                    }""")
                elif direction == "top":
                    await self.page.evaluate("""() => {
                        window.scrollTo({
                            top: 0,
                            behavior: 'smooth'
                        });
                    }""")
                
                # Add a small delay after scrolling
                await asyncio.sleep(1 + random.random())
                return True
                
            elif action_type == "wait":
                # Wait for the specified amount of time
                wait_time = float(value) if value and value.replace('.', '').isdigit() else 2
                await asyncio.sleep(wait_time)
                return True
                
            elif action_type == "extract":
                # This is handled separately in execute_task
                return True
                
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing action {action}: {str(e)}")
            # Take a screenshot when an action fails
            await self.page.screenshot(path=f"screenshots/action_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return False
    
    async def execute_task(self, task: str, max_steps: int = 20) -> Dict:
        """Execute a task by analyzing the page and taking appropriate actions."""
        self.current_task = task
        step_count = 0
        visited_urls = set()  # Track URLs to avoid revisiting
        current_url = self.page.url
        visited_urls.add(current_url)
        
        task_result = {
            "success": False,
            "steps_taken": 0,
            "data_extracted": [],
            "visited_pages": [],
            "observations": [],
            "error": None
        }
        
        logger.info(f"Starting task: {task}")
        
        try:
            while step_count < max_steps:
                # Analyze the current page to determine next actions
                analysis = await self.analyze_page_with_ai(task)
                
                # Check for errors in analysis
                if "error" in analysis:
                    task_result["error"] = analysis["error"]
                    break
                
                # Store any extracted data
                if "data_to_extract" in analysis and analysis["data_to_extract"]:
                    for data_item in analysis["data_to_extract"]:
                        try:
                            # Wait for the element to be visible
                            selector = data_item.get("selector", "")
                            if selector:
                                await self.page.wait_for_selector(selector, state="visible", timeout=5000)
                                
                                # Extract text content
                                content = await self.page.text_content(selector)
                                
                                # Add to results
                                task_result["data_extracted"].append({
                                    "data_type": data_item.get("data_type", "text"),
                                    "selector": selector,
                                    "content": content,
                                    "timestamp": datetime.now().isoformat()
                        "step": step_count
                    })
                    current_url = new_url
                
                # Take screenshot after actions
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                await self.page.screenshot(path=f"screenshots/task_step_{step_count}_{timestamp}.png")
                
                # Wait for network activity to settle
                await asyncio.sleep(1 + random.random() * 2)
            
            # Check if we reached max steps without completion
            if step_count >= max_steps and not task_result["success"]:
                logger.warning(f"Task not completed within maximum {max_steps} steps")
                task_result["error"] = f"Maximum steps reached ({max_steps})"
            
            return task_result
            
        except Exception as e:
            error_msg = f"Error executing task: {str(e)}"
            logger.error(error_msg)
            task_result["error"] = error_msg
            return task_result
    
    async def search_opportunities(self, 
                                  keyword: str = "construction", 
                                  max_results: int = 20) -> List[Dict]:
        """Search for opportunities based on keywords."""
        try:
            # Ensure we're logged in before searching
            await self.login()
            
            # Construct search task
            search_task = f"Search for construction opportunities with keyword '{keyword}'. Find up to {max_results} opportunities and extract their details including title, ID, category, closing date, and budget/value (if available). Focus on opportunities related to infrastructure, buildings, and construction services."
            
            # Start from the homepage
            await self.navigate_to(AUSTENDER_URL)
            
            # Execute the search task
            search_result = await self.execute_task(search_task, max_steps=max_results * 3)
            
            # Process and format the extracted data
            opportunities = []
            for data in search_result.get("data_extracted", []):
                # Try to categorize and structure the extracted data
                if data.get("data_type") == "opportunity":
                    opportunities.append(data.get("content", {}))
                    
            # Save the results to a file
            output_file = f"output/austender_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "keyword": keyword,
                    "extracted_at": datetime.now().isoformat(),
                    "total_found": len(opportunities),
                    "opportunities": opportunities,
                    "raw_data": search_result
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(opportunities)} opportunities to {output_file}")
            return opportunities
            
        except Exception as e:
            logger.error(f"Error searching opportunities: {str(e)}")
            return []
            
    async def close(self) -> None:
        """Close the browser and release resources."""
        try:
            if self.page:
                await self.page.close()
            
            if self.context:
                await self.context.close()
            
            if self.browser:
                await self.browser.close()
            
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
            
            logger.info("Browser closed")
            
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
        
        # Reset attributes
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

async def main():
    """Main function to run the agentic browser."""
    import argparse
    import json
    from pathlib import Path
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the Agentic Austender Browser with Enhanced Page Awareness")
    parser.add_argument("--custom-task", type=str, help="Custom task to execute (e.g., 'Search for bridge construction opportunities in NSW')")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--max-steps", type=int, default=15, help="Maximum number of steps to execute")
    parser.add_argument("--output-file", type=str, help="File to save results to (JSON format)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging based on debug flag
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # Ensure screenshots directory exists
    Path("screenshots").mkdir(exist_ok=True)
    
    # Run the browser with enhanced page awareness
    logger.info("Starting Agentic Austender Browser with Enhanced Page Awareness")
    browser = AgenticAustenderBrowser(headless=args.headless)
    
    try:
        await browser.start_browser()
        
        # Default task if none provided
        custom_task = args.custom_task or "Go to Austender, navigate to the ATM search page, search for 'bridge construction' opportunities in NSW, and extract details for the first 5 results."
        
        # Execute the task with enhanced awareness
        results = await browser.execute_task(custom_task, max_steps=args.max_steps)
        
        # Log results summary
        if results.get("success", False):
            logger.info("Task completed successfully!")
            if results.get("data_extracted"):
                logger.info(f"Extracted {len(results['data_extracted'])} data items")
        else:
            logger.warning("Task did not complete successfully")
            if "error" in results:
                logger.error(f"Error: {results['error']}")
        
        logger.info(f"Completed {len(results.get('steps', []))} steps")
        
        # Save results to file if requested
        if args.output_file:
            output_path = Path(args.output_file)
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {output_path}")
            # Search for opportunities
            logger.info(f"Searching for opportunities with keyword: {args.keyword}")
            opportunities = await browser.search_opportunities(
                keyword=args.keyword,
                max_results=args.max_results
            )
            
            logger.info(f"Found {len(opportunities)} opportunities matching '{args.keyword}'")
    
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
    finally:
        # Clean up
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
