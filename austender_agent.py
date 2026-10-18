#!/usr/bin/env python
"""
Austender Agent
Advanced web automation agent for navigating Austender with anti-bot protection
"""

import os
import json
import asyncio
import logging
import random
import argparse
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Import the tool integration framework
from multi_tool_integration import ToolIntegration

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("austender_agent")

# Placeholder for the actual adapter implementations
# These will be implemented as separate files to keep the codebase modular
class PlaywrightAdapter:
    """Adapter for Playwright browser automation"""
    
    def __init__(self, headless=False):
        """Initialize the Playwright adapter"""
        self.headless = headless
        self.browser = None
        self.page = None
    
    async def initialize(self):
        """Initialize Playwright browser"""
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        
        # Set realistic viewport size
        await self.page.set_viewport_size({"width": 1280, "height": 800})
        
        # Configure browser for more human-like behavior
        await self.page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        })
        
        logger.info("Playwright browser initialized")
        return True
    
    async def cleanup(self):
        """Clean up Playwright browser"""
        if self.browser:
            await self.browser.close()
            logger.info("Playwright browser closed")
        return True
    
    async def execute_action(self, action_type, params):
        """Execute an action with Playwright"""
        try:
            if action_type == "navigate":
                url = params.get("url", "")
                if not url:
                    logger.error("No URL provided for navigation")
                    return False
                
                await self.page.goto(url)
                await self.page.wait_for_load_state("networkidle")
                logger.info(f"Navigated to {url}")
                return True
                
            elif action_type == "click":
                selector = params.get("selector", "")
                if not selector:
                    logger.error("No selector provided for click")
                    return False
                
                # Add randomness to click behavior
                await asyncio.sleep(random.uniform(0.3, 1.0))
                
                # Try multiple ways to find and click the element
                try:
                    # First try to scroll element into view
                    await self.page.evaluate(f"document.querySelector('{selector}').scrollIntoView({{behavior: 'smooth', block: 'center'}})")
                    await asyncio.sleep(0.5)
                    
                    # Click with randomized delay
                    await self.page.click(selector, delay=random.randint(50, 150))
                    logger.info(f"Clicked element with selector: {selector}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to click with selector {selector}: {str(e)}")
                    
                    # Try clicking by JavaScript as fallback
                    try:
                        await self.page.evaluate(f"document.querySelector('{selector}').click()")
                        logger.info(f"Clicked element with JS fallback: {selector}")
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
                
                # Humanize typing
                try:
                    # First click to focus
                    await self.page.click(selector)
                    
                    # Clear any existing value
                    await self.page.evaluate(f"document.querySelector('{selector}').value = ''")
                    
                    # Type with variable speed
                    for char in value:
                        await self.page.type(selector, char, delay=random.randint(50, 200))
                        await asyncio.sleep(random.uniform(0.01, 0.05))
                    
                    logger.info(f"Entered text into input: {selector}")
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
                
                try:
                    await self.page.select_option(selector, value)
                    logger.info(f"Selected option {value} from {selector}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to select option: {str(e)}")
                    return False
                
            elif action_type == "wait":
                time_ms = params.get("time", 1000)
                await asyncio.sleep(time_ms / 1000)
                return True
                
            else:
                logger.warning(f"Unsupported action type: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing {action_type}: {str(e)}")
            return False
    
    async def get_page_content(self):
        """Get current page content"""
        try:
            # Get page title
            title = await self.page.title()
            
            # Get page URL
            url = self.page.url
            
            # Get page content
            content = await self.page.content()
            
            # Extract visible text
            visible_text = await self.page.evaluate("""() => {
                return document.body.innerText;
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
            
            # Create page content structure
            page_content = {
                "title": title,
                "url": url,
                "content": content[:5000],  # Limit content size
                "visible_text": visible_text[:5000],  # Limit text size
                "interactive_elements": interactive_elements
            }
            
            return page_content
            
        except Exception as e:
            logger.error(f"Error getting page content: {str(e)}")
            return {
                "title": "Error",
                "url": self.page.url if self.page else "",
                "error": str(e)
            }


class OpenAIAdapter:
    """Adapter for OpenAI API integration"""
    
    def __init__(self, api_key=None):
        """Initialize the OpenAI adapter"""
        from openai import AsyncOpenAI
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def initialize(self):
        """Initialize OpenAI adapter"""
        return True
    
    async def cleanup(self):
        """Clean up OpenAI adapter"""
        return True
    
    async def analyze_page(self, page_content, task):
        """Use OpenAI to analyze a page and determine next steps"""
        # Build system prompt
        system_prompt = """
        You are an expert web automation agent specialized in navigating the Australian Government's AusTender website.
        Your task is to understand the current page and suggest the next precise actions to accomplish the user's task.
        
        Important details about AusTender website:
        1. The site uses Drupal as its CMS and has forms for searching procurement opportunities
        2. The main sections include: Home, Approaches to Market (ATM), Contract Notices, and Agency Resources
        3. The ATM search page allows filtering by keyword, category, date, agency, etc.
        4. Tables of results show procurement opportunities with ID numbers, titles, categories, etc.
        5. Login forms typically need a username and password and might have CAPTCHA
        
        Guidelines for effective automation:
        1. Be precise with selectors - provide multiple selector alternatives when possible
        2. Focus on visible, interactive elements in the viewport first
        3. For search forms, identify the proper input fields and submit buttons
        4. Use page context to determine where you are in the workflow
        5. When extracting data from tables, identify the correct table rows and columns
        6. For pagination, look for next/previous links or page number indicators
        
        This is an agentic automation system with real impact - be precise and thoughtful.
        """
        
        # Extract interactive elements safely
        interactive_elements_json = json.dumps([{
            "type": el.get("type", ""),
            "text": el.get("text", ""),
            "purpose": el.get("purpose", ""),
            "selectors": el.get("selectors", [])[:2],  # Limit selector count
            "in_viewport": el.get("in_viewport", False)
        } for el in page_content.get("interactive_elements", [])[:10]], indent=2)
        
        # Build user prompt
        user_prompt = f"""
        Task: {task}

        Current page information:
        Title: {page_content.get('title', 'Unknown Title')}
        URL: {page_content.get('url', 'Unknown URL')}
        
        Interactive Elements (top 10):
        {interactive_elements_json}
        
        Based on the current page state and the task, analyze and suggest up to 3 concrete actions I should take next.
        For each action, provide:
        1. Action type (click, input, select, wait)
        2. Selector to use (provide the most reliable one)
        3. Value to input (if applicable)
        4. A clear explanation of why this action is appropriate
        
        If this is a results page and we need to extract data, please identify the table rows and provide instructions for extraction.
        
        Format your response as a JSON list of actions:
        [
          {{
            "action": "click|input|select|wait|extract",
            "selector": "css_selector",
            "value": "input value if needed",
            "explanation": "Why this action helps accomplish the task"
          }}
        ]
        
        Only include the JSON output.
        """
        
        # Call OpenAI API
        try:
            completion = await self.client.chat.completions.create(
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
                logger.info(f"OpenAI analysis complete, suggested {len(actions)} actions")
                return {"success": True, "actions": actions}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\[\s*{.*}\s*\]', response_text, re.DOTALL)
                if json_match:
                    try:
                        extracted_json = json_match.group(0)
                        actions = json.loads(extracted_json)
                        logger.info(f"Extracted JSON from response, found {len(actions)} actions")
                        return {"success": True, "actions": actions}
                    except json.JSONDecodeError:
                        pass
                
                # Create a simple fallback response
                fallback_actions = [
                    {
                        "action": "wait",
                        "selector": "",
                        "value": "3",
                        "explanation": "Waiting for the page to stabilize after failure to parse OpenAI response"
                    }
                ]
                
                return {"success": False, "error": "Failed to parse OpenAI response", "fallback_actions": fallback_actions}
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return {
                "success": False,
                "error": f"Error calling OpenAI API: {str(e)}",
                "fallback_actions": [{
                    "action": "wait",
                    "selector": "",
                    "value": "5",
                    "explanation": "Error recovery: waiting before retry"
                }]
            }


class AustenderAgent:
    """Main agent for executing Austender tasks with anti-bot capabilities"""
    
    def __init__(self, headless=False):
        """Initialize the agent with all available tools"""
        self.headless = headless
        self.tool_integration = ToolIntegration()
        self.session_data = {
            "loggedIn": False,
            "current_url": "",
            "current_page_content": {},
            "extracted_data": [],
            "steps_executed": [],
            "screenshots": []
        }
        
        # Ensure screenshots directory exists
        Path("screenshots").mkdir(exist_ok=True)
        
        # Initialize and register tools
        self._init_tools()
    
    def _init_tools(self):
        """Initialize and register all available tools"""
        # Register Playwright adapter
        self.tool_integration.register_tool("playwright", PlaywrightAdapter(headless=self.headless))
        
        # Register OpenAI adapter
        self.tool_integration.register_tool("openai", OpenAIAdapter(api_key=os.getenv("OPENAI_API_KEY")))
        
        # Add other tool adapters as they are implemented
        # self.tool_integration.register_tool("browser_use", BrowserUseAdapter())
        # self.tool_integration.register_tool("firecrawl", FirecrawlAdapter())
        # self.tool_integration.register_tool("stagehand", StagehandAdapter())
    
    async def start(self):
        """Start the agent and initialize all tools"""
        logger.info("Starting Austender Agent")
        
        # Initialize each tool
        for tool_name, tool in self.tool_integration.tools.items():
            if hasattr(tool, "initialize"):
                await tool.initialize()
        
        return True
    
    async def stop(self):
        """Stop the agent and clean up resources"""
        logger.info("Stopping Austender Agent")
        
        # Clean up each tool
        for tool_name, tool in self.tool_integration.tools.items():
            if hasattr(tool, "cleanup"):
                await tool.cleanup()
        
        return True
    
    async def login(self, username=None, password=None):
        """Login to Austender"""
        username = username or os.getenv("AUSTENDER_USERNAME")
        password = password or os.getenv("AUSTENDER_PASSWORD")
        
        if not username or not password:
            logger.error("Username or password not provided")
            return False
        
        # Navigate to login page
        login_params = {"url": "https://www.tenders.gov.au/user/login"}
        login_result = await self.tool_integration.execute_action("navigate", login_params)
        
        if not login_result.get("success", False):
            logger.error("Failed to navigate to login page")
            return False
        
        # Get the current page content
        playwright_tool = self.tool_integration.tools.get("playwright")
        if not playwright_tool:
            logger.error("Playwright tool not available")
            return False
            
        page_content = await playwright_tool.get_page_content()
        self.session_data["current_page_content"] = page_content
        
        # Take a screenshot
        screenshot_path = f"screenshots/login_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await playwright_tool.page.screenshot(path=screenshot_path)
        self.session_data["screenshots"].append(screenshot_path)
        
        # Fill username
        username_params = {
            "selector": "#edit-name",
            "value": username
        }
        await self.tool_integration.execute_action("input", username_params)
        
        # Fill password
        password_params = {
            "selector": "#edit-pass",
            "value": password
        }
        await self.tool_integration.execute_action("input", password_params)
        
        # Submit form
        submit_params = {
            "selector": "#edit-submit"
        }
        result = await self.tool_integration.execute_action("click", submit_params)
        
        if not result.get("success", False):
            logger.error("Failed to submit login form")
            return False
        
        # Wait for page to load
        await asyncio.sleep(3)
        
        # Check if login was successful
        page_content = await playwright_tool.get_page_content()
        
        # Take a screenshot after login attempt
        screenshot_path = f"screenshots/after_login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await playwright_tool.page.screenshot(path=screenshot_path)
        self.session_data["screenshots"].append(screenshot_path)
        
        # Check if login was successful
        logout_exists = any(
            "logout" in element.get("text", "").lower() or 
            "log out" in element.get("text", "").lower()
            for element in page_content.get("interactive_elements", [])
        )
        
        if logout_exists:
            logger.info("Login successful")
            self.session_data["loggedIn"] = True
            return True
        else:
            logger.error("Login failed")
            return False
    
    async def execute_task(self, task: str, max_steps=15):
        """Execute a complex task with AI guidance"""
        logger.info(f"Executing task: {task}")
        steps_taken = 0
        
        # Navigate to the starting URL
        start_params = {"url": "https://www.tenders.gov.au/"}
        start_result = await self.tool_integration.execute_action("navigate", start_params)
        
        if not start_result.get("success", False):
            logger.error("Failed to navigate to starting URL")
            return {"success": False, "error": "Failed to navigate to starting URL"}
        
        # Main task execution loop
        while steps_taken < max_steps:
            steps_taken += 1
            logger.info(f"Step {steps_taken}/{max_steps}: Analyzing current page...")
            
            # Get the current page content
            playwright_tool = self.tool_integration.tools.get("playwright")
            if not playwright_tool:
                logger.error("Playwright tool not available")
                return {"success": False, "error": "Playwright tool not available"}
                
            page_content = await playwright_tool.get_page_content()
            self.session_data["current_page_content"] = page_content
            self.session_data["current_url"] = page_content.get("url", "")
            
            # Take a screenshot
            screenshot_path = f"screenshots/step_{steps_taken}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await playwright_tool.page.screenshot(path=screenshot_path)
            self.session_data["screenshots"].append(screenshot_path)
            
            # Analyze the current page with AI
            analysis = await self.tool_integration.analyze_page(page_content, task)
            
            if not analysis.get("success", False):
                logger.error(f"AI analysis failed: {analysis.get('error', 'Unknown error')}")
                if "fallback_actions" in analysis.get("result", {}):
                    actions = analysis["result"]["fallback_actions"]
                else:
                    break
            else:
                actions = analysis.get("result", {}).get("actions", [])
            
            if not actions:
                logger.info("No actions suggested, task may be complete")
                break
            
            # Execute each action until one succeeds
            action_success = False
            for action in actions:
                action_type = action.get("action", "").lower()
                selector = action.get("selector", "")
                value = action.get("value", "")
                explanation = action.get("explanation", "No explanation")
                
                logger.info(f"Executing action: {action_type} - {explanation}")
                
                # Record this step
                self.session_data["steps_executed"].append({
                    "step": steps_taken,
                    "action": action,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Handle extract action separately
                if action_type == "extract":
                    try:
                        elements = await playwright_tool.page.query_selector_all(selector)
                        
                        extracted_items = []
                        for element in elements:
                            text = await element.text_content()
                            extracted_items.append({
                                "text": text.strip(),
                                "selector": selector,
                                "timestamp": datetime.now().isoformat()
                            })
                        
                        self.session_data["extracted_data"].extend(extracted_items)
                        logger.info(f"Extracted {len(extracted_items)} items")
                        action_success = True
                    
                    except Exception as e:
                        logger.error(f"Error extracting data: {str(e)}")
                        continue
                
                else:
                    # Prepare parameters for the action
                    action_params = {
                        "selector": selector,
                        "value": value
                    }
                    
                    # Execute the action
                    result = await self.tool_integration.execute_action(action_type, action_params)
                    
                    if result.get("success", False):
                        action_success = True
                        logger.info(f"Action executed successfully with {result.get('tool', 'unknown tool')}")
                        
                        # Wait for page to stabilize
                        await asyncio.sleep(2)
                        break
                    else:
                        logger.warning(f"Action failed: {action_type} {selector}")
            
            if not action_success:
                logger.error("All actions failed")
                break
            
            # Add random delay between actions for more human-like behavior
            await asyncio.sleep(random.uniform(1.0, 3.0))
        
        # Final report
        if steps_taken >= max_steps:
            logger.warning(f"Reached maximum steps ({max_steps})")
        else:
            logger.info(f"Task completed in {steps_taken} steps")
        
        # Take final screenshot
        final_screenshot = f"screenshots/task_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await playwright_tool.page.screenshot(path=final_screenshot)
        self.session_data["screenshots"].append(final_screenshot)
        
        # Mark as successful if we executed at least one step and didn't hit the limit
        success = steps_taken > 0 and (steps_taken < max_steps or len(self.session_data["extracted_data"]) > 0)
        self.session_data["success"] = success
        
        return self.session_data


async def main():
    """Main entry point for running Austender Agent"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Austender Agent")
    parser.add_argument("--task", type=str, 
                        default="Search for bridge construction opportunities in NSW and extract the details",
                        help="Task to execute")
    parser.add_argument("--headless", action="store_true", 
                        help="Run browser in headless mode")
    parser.add_argument("--max-steps", type=int, default=15, 
                        help="Maximum number of steps to execute")
    parser.add_argument("--output-file", type=str, default="austender_results.json",
                        help="File to save results to (JSON format)")
    parser.add_argument("--login", action="store_true",
                        help="Attempt to log in before executing task")
    parser.add_argument("--debug", action="store_true", 
                        help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging based on debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the agent
    agent = AustenderAgent(headless=args.headless)
    
    try:
        await agent.start()
        
        # Login if requested
        if args.login and os.getenv("AUSTENDER_USERNAME") and os.getenv("AUSTENDER_PASSWORD"):
            if not await agent.login():
                logger.warning("Login failed, continuing without authentication")
        
        # Execute the task
        results = await agent.execute_task(args.task, max_steps=args.max_steps)
        
        # Save results to file
        with open(args.output_file, "w") as f:
            # Convert to JSON-serializable format
            serializable_results = {
                "success": results.get("success", False),
                "steps_executed": results.get("steps_executed", []),
                "extracted_data": results.get("extracted_data", []),
                "screenshots": results.get("screenshots", []),
                "timestamp": datetime.now().isoformat()
            }
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Results saved to {args.output_file}")
        
        # Print summary
        print("\n" + "-"*50)
        print("EXECUTION SUMMARY:")
        print("-"*50)
        print(f"Task: {args.task}")
        print(f"Success: {results.get('success', False)}")
        print(f"Steps completed: {len(results.get('steps_executed', []))}")
        print(f"Data items extracted: {len(results.get('extracted_data', []))}")
        print(f"Screenshots: {len(results.get('screenshots', []))}")
        print("-"*50)
        
        return results
    
    finally:
        # Always stop the agent
        await agent.stop()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
