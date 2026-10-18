#!/usr/bin/env python3
"""
Austender AI-Driven Browser Agent
--------------------------------
This script combines concepts from Browser Use with Playwright to create an
AI-driven browser agent for navigating and scraping the Austender website.
It uses OpenAI's GPT model to understand page contents and decide on navigation actions.
"""

import os
import json
import time
import random
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Set
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"austender_browser_use_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("austender_browser_agent")

# Create directories for outputs
os.makedirs("screenshots", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("logs", exist_ok=True)

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

class BrowserUseAustenderAgent:
    """AI-driven browser agent for navigating and scraping Austender."""
    
    def __init__(self, 
                 headless: bool = False, 
                 slow_mo: int = 100,
                 model: str = "gpt-4o",
                 api_key: str = None):
        """Initialize the agent with browser and LLM settings."""
        self.headless = headless
        self.slow_mo = slow_mo
        self.opportunities = []
        self.current_task = None
        self.task_history = []
        self.browser = None
        self.context = None
        self.page = None
        
        # LLM model settings
        self.model = model
        if api_key:
            openai.api_key = api_key
        else:
            openai.api_key = os.getenv("OPENAI_API_KEY")
            
        if not openai.api_key:
            raise ValueError("OpenAI API key is required. Set it in the .env file or pass it as a parameter.")
            
        # Austender credentials
        self.username = os.getenv("AUSTENDER_USERNAME")
        self.password = os.getenv("AUSTENDER_PASSWORD")
        if not self.username or not self.password:
            logger.warning("AUSTENDER_USERNAME or AUSTENDER_PASSWORD not set; login may be required.")
            
        logger.info("Initialized Browser Use Austender Agent")
    
    async def start_browser(self) -> None:
        """Start an async browser instance with anti-detection measures."""
        try:
            import random
            
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
            # Fill credentials
            await self.page.fill("input#edit-name", self.username)
            await self.page.fill("input#edit-pass", self.password)
            # Submit login form
            await self.page.click("input#edit-submit")
            # Wait for logout link as confirmation
            await self.page.wait_for_selector("a[href*='logout']", timeout=30000)
            logger.info("Login successful")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
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
        """Get the current page content for AI analysis."""
        try:
            # Get the page title
            title = await self.page.title()
            
            # Get visible text content
            content = await self.page.evaluate("""() => {
                return document.body.innerText;
            }""")
            
            # Get the current URL
            url = self.page.url
            
            # Get HTML structure of important elements
            html_structure = await self.page.evaluate("""() => {
                const getStructure = (element, maxDepth = 2, currentDepth = 0) => {
                    if (!element || currentDepth > maxDepth) return null;
                    
                    // Get relevant attributes
                    const attributes = {};
                    for (const attr of element.attributes || []) {
                        if (['id', 'class', 'name', 'href', 'src', 'alt', 'title', 'type', 'value'].includes(attr.name)) {
                            attributes[attr.name] = attr.value;
                        }
                    }
                    
                    // Get basic structure
                    const result = {
                        tag: element.tagName?.toLowerCase(),
                        id: element.id,
                        classes: Array.from(element.classList || []),
                        text: element.innerText?.slice(0, 100),
                        attributes
                    };
                    
                    // Only go deeper for important elements
                    if (currentDepth < maxDepth) {
                        const children = Array.from(element.children || [])
                            .filter(child => {
                                // Filter to important elements only
                                const tag = child.tagName?.toLowerCase();
                                return ['div', 'a', 'button', 'input', 'form', 'table', 'tr', 'th', 'td', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5'].includes(tag);
                            })
                            .map(child => getStructure(child, maxDepth, currentDepth + 1))
                            .filter(Boolean);
                        
                        if (children.length > 0) {
                            result.children = children;
                        }
                    }
                    
                    return result;
                };
                
                // Get important elements
                const mainContent = document.querySelector('main') || document.querySelector('#content') || document.body;
                return getStructure(mainContent);
            }""")
            
            # Find interactive elements
            interactive_elements = await self.page.evaluate("""() => {
                const interactives = [];
                
                // Get all interactive elements
                const elements = Array.from(document.querySelectorAll('a, button, input, select, [role="button"]'));
                
                // Extract basic info about each
                elements.forEach((el, index) => {
                    if (index > 50) return; // Limit to 50 elements
                    
                    // Skip hidden elements
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || 
                        style.opacity === '0' || el.offsetParent === null) {
                        return;
                    }
                    
                    // Get text content
                    const text = el.innerText || el.textContent || el.value || '';
                    if (text.length > 150) return; // Skip elements with too much text
                    
                    // Create a selector for this element
                    let selector = '';
                    if (el.id) {
                        selector = `#${el.id}`;
                    } else if (el.className && typeof el.className === 'string') {
                        selector = `.${el.className.split(' ').join('.')}`;
                    } else {
                        // Create a selector based on tag and attributes
                        selector = el.tagName.toLowerCase();
                        if (el.name) selector += `[name="${el.name}"]`;
                        if (el.type) selector += `[type="${el.type}"]`;
                        if (text.trim().length > 0 && text.trim().length < 50) {
                            selector += `:has-text("${text.trim().substring(0, 40)}")`;
                        }
                    }
                    
                    interactives.push({
                        type: el.tagName.toLowerCase(),
                        text: text.trim().substring(0, 100),
                        selector: selector,
                        visible: true,
                        attributes: {
                            href: el.href || null,
                            type: el.type || null,
                            name: el.name || null,
                            value: el.value || null,
                            placeholder: el.placeholder || null
                        }
                    });
                });
                
                return interactives;
            }""")
            
            return {
                "title": title,
                "url": url,
                "content": content,
                "structure": html_structure,
                "interactive_elements": interactive_elements
            }
            
        except Exception as e:
            logger.error(f"Error getting page content: {str(e)}")
            return {"error": str(e)}
    
    async def analyze_page_with_ai(self, task: str) -> Dict:
        """Analyze the page content with AI to determine next actions."""
        try:
            # Get current page content
            page_data = await self.get_page_content()
            
            # Prepare the prompt for the AI
            messages = [
                {"role": "system", "content": """
                You are an expert web automation agent. Your job is to analyze webpage content and provide clear,
                structured guidance for navigating and extracting information from the Austender government website.
                
                Focus on:
                1. Understanding the structure of the current page
                2. Identifying the best elements to interact with to accomplish the task
                3. Giving specific, actionable instructions with precise selectors
                4. Avoiding detection by anti-bot systems by recommending human-like interaction patterns
                5. Intelligently exploring links and content that are most relevant to the task
                6. Recognizing login walls and authentication requirements
                7. Making decisions about when to explore deeper vs breadth-first exploration
                
                When suggesting interactions:
                - Provide the exact CSS selector for elements to click/interact with
                - Suggest realistic waiting times between actions
                - Recommend when to use randomized mouse movements or scrolling
                - Identify when captchas or other anti-bot measures appear and how to handle them
                
                IMPORTANT: Format your response as a structured JSON with clear steps and explanations.
                Include an "observation" field in your response with any notable findings about the current page.
                """},
                {"role": "user", "content": f"""
                CURRENT TASK: {task}
                
                CURRENT PAGE:
                Title: {page_data['title']}
                URL: {page_data['url']}
                
                PAGE CONTENT (excerpt):
                {page_data['content'][:2000] if len(page_data['content']) > 2000 else page_data['content']}
                
                INTERACTIVE ELEMENTS:
                {json.dumps(page_data['interactive_elements'][:20], indent=2)}
                
                Based on this information, analyze the current page and provide:
                1. A description of what you see on the page
                2. The next action(s) to take to accomplish the task
                3. Exact CSS selectors for elements to interact with
                4. Any data to extract from the current page
                
                Format your response as a JSON object with:
                {
                    "page_analysis": "description of the current page",
                    "task_progress": "assessment of progress toward completing the task",
                    "next_actions": [
                        {
                            "action_type": "click|input|extract|scroll|wait",
                            "selector": "CSS selector",
                            "value": "value to input (if action_type is input)",
                            "explanation": "why this action is needed"
                        }
                    ],
                    "data_to_extract": [
                        {
                            "data_type": "type of data",
                            "selector": "CSS selector",
                            "processing_instructions": "how to process this data"
                        }
                    ],
                    "completed": boolean,
                    "observation": "any notable findings about the current page"
                }
                """
                }
            ]
            
            # Call the OpenAI API
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=1500
            )
            
            # Parse the API response
            try:
                completion = response.choices[0].message.content
                # Clean the JSON string in case it has markdown code blocks
                if "```json" in completion:
                    completion = completion.split("```json")[1].split("```")[0].strip()
                elif "```" in completion:
                    completion = completion.split("```")[1].split("```")[0].strip()
                analysis_result = json.loads(completion)
                
                logger.info(f"AI analysis complete, suggested {len(analysis_result.get('next_actions', []))} actions")
                return analysis_result
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response as JSON: {completion}")
                # Return a basic structure if parsing fails
                return {
                    "page_analysis": "Failed to parse AI response",
                    "task_progress": "Unknown",
                    "next_actions": [],
                    "data_to_extract": [],
                    "completed": False,
                    "raw_response": completion
                }
                
        except Exception as e:
            logger.error(f"Error analyzing page with AI: {str(e)}")
            return {"error": str(e)}

    async def execute_task(self, task: str, max_steps: int = 10) -> dict:
        """Execute a task by analyzing the page and taking appropriate actions."""
        self.current_task = task
        step_count = 0
        visited_urls = set()  # Track URLs to avoid revisiting
        current_url = await self.page.url()
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
                                    "timestamp": datetime.datetime.now().isoformat()
                                })
                        except Exception as e:
                            logger.warning(f"Error extracting data with selector {selector}: {str(e)}")
                
                # Check if this completes the task
                if "task_complete" in analysis and analysis["task_complete"]:
                    task_result["success"] = True
                    logger.info(f"Task completed successfully in {step_count} steps")
                    break
                    
                # Add observation if available
                if "observation" in analysis and analysis["observation"]:
                    task_result["observations"].append({
                        "step": step_count,
                        "url": current_url,
                        "observation": analysis["observation"]
                    })
                
                # Execute next actions
                next_actions = analysis.get("next_actions", [])
                if not next_actions:
                    logger.warning("No next actions provided by AI analysis")
                    break
                
                # Execute each action in sequence
                for action in next_actions:
                    action_success = await self.execute_action(action)
                    if not action_success:
                        logger.warning(f"Action failed: {action}")
                    
                    # Add human-like delay between actions
                    await asyncio.sleep(0.5 + random.random() * 1.5)
                
                # Update the step count
                step_count += 1
                task_result["steps_taken"] = step_count
                
                # Track visited pages
                new_url = await self.page.url()
                new_title = await self.page.title()
                if new_url != current_url:
                    visited_urls.add(new_url)
                    task_result["visited_pages"].append({
                        "url": new_url,
                        "title": new_title,
                        "step": step_count
                    })
                    current_url = new_url
                
                # Take screenshot after actions
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
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
                                  category: str = None,
                                  max_pages: int = 3) -> List[Dict]:
        """Search for opportunities based on keywords and category."""
        try:
            # Ensure we are logged in before searching
            await self.login()
            
            # Construct search task
            search_task = f"Search for opportunities with keyword '{keyword}'"
            if category:
                search_task += f" in category '{category}'"
            
            search_task += f". Retrieve basic details for up to {max_pages} pages of results."
            
            # Start from the homepage
            await self.navigate_to(AUSTENDER_URL)
            
            # Execute the search task
            search_result = await self.execute_task(search_task, max_steps=max_pages * 5)
            
            # Process and return the results
            return search_result.get("data_extracted", [])
            
        except Exception as e:
            logger.error(f"Error searching opportunities: {str(e)}")
            return []
    
    async def get_opportunity_details(self, opportunity_id: str = None, opportunity_url: str = None) -> Dict:
        """Get detailed information about a specific opportunity."""
        try:
            if not opportunity_id and not opportunity_url:
                logger.error("Either opportunity_id or opportunity_url must be provided")
                return {}
                
            # Construct the task for getting details
            if opportunity_id:
                detail_task = f"Get detailed information for opportunity with ID '{opportunity_id}'"
                if not opportunity_url:
                    opportunity_url = f"{AUSTENDER_URL}/ATM/Detail/{opportunity_id}"
            else:
                detail_task = f"Get detailed information for the opportunity at this URL"
            
            # Navigate to the opportunity page
            await self.navigate_to(opportunity_url)
            
            # Execute the detail retrieval task
            detail_result = await self.execute_task(detail_task, max_steps=5)
            
            # Process and return the results
            return {
                "id": opportunity_id,
                "url": opportunity_url,
                "details": detail_result.get("data_extracted", []),
                "success": detail_result.get("success", False)
            }
            
        except Exception as e:
            logger.error(f"Error getting opportunity details: {str(e)}")
            return {}
    
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
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI-driven browser agent for Austender")
    parser.add_argument("--keyword", type=str, default="construction", help="Keyword to search for")
    parser.add_argument("--explore", action="store_true", help="Run in exploratory mode with more autonomous decisions")
    parser.add_argument("--depth", type=int, default=3, help="Maximum depth for exploratory mode")
    parser.add_argument("--breadth", type=int, default=3, help="Maximum breadth per page for exploratory mode")
    parser.add_argument("--category", type=str, help="Category to filter by")
    parser.add_argument("--pages", type=int, default=2, help="Maximum number of pages to scrape")
    parser.add_argument("--details", action="store_true", help="Get detailed information for opportunities")
    parser.add_argument("--save", action="store_true", help="Save results to a file")
    parser.add_argument("--output", type=str, help="Output filename")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--model", type=str, default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--task", type=str, help="Custom task to execute")
    parser.add_argument("--api-key", type=str, help="OpenAI API key")
    
    args = parser.parse_args()
    
    # Create the agent
    agent = BrowserUseAustenderAgent(
        headless=args.headless,
        model=args.model,
        api_key=args.api_key
    )
    
    try:
        # Start the browser
        browser_started = await agent.start_browser()
        if not browser_started:
            logger.error("Failed to start browser")
            return
        
        results = []
        
        # Execute custom task if provided
        if args.task:
            logger.info(f"Executing custom task: {args.task}")
            await agent.navigate_to(AUSTENDER_URL)
            
            if args.explore:
                logger.info("Running in exploratory mode")
                exploring_task = f"{args.task} Explore thoroughly and document all findings. Go deep when you find relevant information."
                task_result = await agent.execute_task(exploring_task, max_steps=args.depth * args.breadth * 2)
            else:
                task_result = await agent.execute_task(args.task)
                
            results.append(task_result)
        else:
            # Search for opportunities
            logger.info(f"Searching for opportunities with keyword: {args.keyword}")
            opportunities = await agent.search_opportunities(
                keyword=args.keyword,
                category=args.category,
                max_pages=args.pages
            )
            
            results.extend(opportunities)
            
            # Get details if requested
            if args.details and opportunities:
                logger.info("Getting detailed information for opportunities")
                for opp in opportunities[:min(5, len(opportunities))]:  # Limit to 5 for testing
                    if "id" in opp:
                        details = await agent.get_opportunity_details(opportunity_id=opp["id"])
                        if details:
                            results.append(details)
        
        # Save results if requested
        if args.save:
            output_file = args.output or f"output/austender_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
    finally:
        # Clean up
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
