#!/usr/bin/env python
"""
Enhanced Page Analysis Module for Agentic Austender Browser
This module provides improved page content extraction and analysis capabilities
"""

import os
import re
import json
import asyncio
import logging
import random
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from playwright.async_api import Page

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("page_analysis")

class EnhancedPageAnalyzer:
    """Enhanced page analysis capabilities for web automation"""
    
    def __init__(self, page: Page):
        """Initialize with a Playwright page object"""
        self.page = page
        # Ensure screenshots directory exists
        Path("screenshots").mkdir(exist_ok=True)
    
    async def get_enhanced_page_content(self) -> Dict:
        """Get detailed, structured information about the current page"""
        try:
            # Take a screenshot for debugging and analysis
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
                    return text.replace(/\\s+/g, ' ').trim();
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
                    const cleanedText = text.replace(/\\s+/g, ' ').trim().substring(0, 100);
                    
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
                        const classes = el.className.trim().split(/\\s+/).join('.');
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
                        const safeText = cleanedText.replace(/"/g, '\\\\\\'').substring(0, 40);
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
            logger.error(f"Error getting enhanced page content: {str(e)}")
            # Take error screenshot
            await self.page.screenshot(path=f"screenshots/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return {"error": str(e)}
    
    async def execute_action(self, action_type: str, selector: str, value: str = "", explanation: str = "") -> bool:
        """Execute an action on the page with enhanced reliability"""
        try:
            logger.info(f"Executing action: {action_type} on {selector} - {explanation}")
            
            # Split the selector into multiple possible selectors if it contains a "|"
            selectors = [s.strip() for s in selector.split("|")]
            
            # Try each selector until one works
            for sel in selectors:
                try:
                    # Check if element is visible
                    is_visible = await self.page.evaluate(f"""
                    () => {{
                        const el = document.querySelector("{sel}");
                        if (!el) return false;
                        
                        const style = window.getComputedStyle(el);
                        return el.offsetParent !== null && 
                               style.display !== 'none' && 
                               style.visibility !== 'hidden' && 
                               parseFloat(style.opacity) > 0;
                    }}
                    """)
                    
                    if not is_visible:
                        logger.debug(f"Element with selector '{sel}' is not visible")
                        continue
                    
                    # Execute the appropriate action
                    if action_type == "click":
                        # Try different click strategies
                        try:
                            # Human-like click with random offset
                            await self.page.click(sel, 
                                       position={"x": random.randint(5, 10), "y": random.randint(5, 10)}, 
                                       delay=random.randint(50, 150))
                        except Exception as e:
                            logger.warning(f"Standard click failed: {str(e)}. Trying JS click.")
                            # Try JavaScript click as fallback
                            await self.page.evaluate(f"""() => {{
                                document.querySelector("{sel}").click();
                            }}""")
                        
                        # Wait a moment after clicking
                        await asyncio.sleep(1 + random.random())
                        return True
                        
                    elif action_type == "input":
                        # Clear the field first
                        await self.page.evaluate(f"""() => {{
                            const el = document.querySelector("{sel}");
                            if (el) el.value = '';
                        }}""")
                        
                        # Type with random delays for a more human-like interaction
                        await self.page.type(sel, value, delay=random.randint(50, 150))
                        return True
                        
                    elif action_type == "select":
                        # Handle dropdown selection
                        await self.page.select_option(sel, value)
                        return True
                        
                    else:
                        logger.warning(f"Unsupported action type: {action_type}")
                        return False
                        
                except Exception as e:
                    logger.debug(f"Failed with selector {sel}: {str(e)}")
                    # Continue to the next selector
            
            # If we get here, all selectors failed
            logger.error(f"All selectors failed for {action_type} action")
            return False
            
        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            await self.page.screenshot(path=f"screenshots/action_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return False

# This can be used as a standalone script for testing
if __name__ == "__main__":
    import argparse
    from playwright.async_api import async_playwright
    
    async def main():
        # Parse arguments
        parser = argparse.ArgumentParser(description="Test enhanced page analysis")
        parser.add_argument("--url", type=str, default="https://www.tenders.gov.au/", 
                           help="URL to analyze")
        parser.add_argument("--headless", action="store_true", 
                           help="Run browser in headless mode")
        args = parser.parse_args()
        
        # Start browser
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=args.headless)
            page = await browser.new_page()
            
            # Create analyzer
            analyzer = EnhancedPageAnalyzer(page)
            
            # Navigate to URL
            await page.goto(args.url)
            await page.wait_for_load_state("networkidle")
            
            # Analyze page
            logger.info(f"Analyzing page: {args.url}")
            analysis = await analyzer.get_enhanced_page_content()
            
            # Save analysis to file
            output_file = f"page_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, "w") as f:
                json.dump(analysis, f, indent=2)
            
            logger.info(f"Analysis saved to {output_file}")
            
            # Close browser
            await browser.close()
    
    # Run the main function
    asyncio.run(main())
