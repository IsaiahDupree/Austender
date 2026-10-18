#!/usr/bin/env python
"""
Run Austender Task
This script uses enhanced page analysis to navigate and extract data from Austender
"""

import os
import json
import asyncio
import logging
import argparse
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from enhanced_page_analysis import EnhancedPageAnalyzer
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("austender_task")

# Constants
AUSTENDER_URL = "https://www.tenders.gov.au/"
AUSTENDER_LOGIN_URL = "https://www.tenders.gov.au/user/login"
AUSTENDER_USERNAME = os.getenv("AUSTENDER_USERNAME")
AUSTENDER_PASSWORD = os.getenv("AUSTENDER_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class AustenderTaskRunner:
    """Class to run Austender tasks with enhanced page awareness"""
    
    def __init__(self, headless=False):
        """Initialize with browser options"""
        self.headless = headless
        self.browser = None
        self.page = None
        self.analyzer = None
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.results = {
            "success": False,
            "steps": [],
            "data_extracted": [],
            "screenshots": []
        }
        
        # Ensure screenshots directory exists
        Path("screenshots").mkdir(exist_ok=True)
    
    async def start(self):
        """Start the browser and set up page analyzer"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        
        # Set realistic viewport size
        await self.page.set_viewport_size({"width": 1280, "height": 800})
        
        # Create enhanced page analyzer
        self.analyzer = EnhancedPageAnalyzer(self.page)
        
        logger.info("Browser started successfully")
        return True
    
    async def stop(self):
        """Close the browser and clean up resources"""
        if self.browser:
            await self.browser.close()
            logger.info("Browser closed")
    
    async def navigate_to(self, url):
        """Navigate to a URL and wait for it to load"""
        logger.info(f"Navigating to {url}")
        await self.page.goto(url)
        await self.page.wait_for_load_state("networkidle")
        title = await self.page.title()
        logger.info(f"Page loaded: {title}")
        
        # Take screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshots/navigation_{timestamp}.png"
        await self.page.screenshot(path=screenshot_path)
        self.results["screenshots"].append(screenshot_path)
        
        return True
    
    async def login(self):
        """Log in to Austender with credentials from .env file"""
        if not AUSTENDER_USERNAME or not AUSTENDER_PASSWORD:
            logger.error("Austender credentials not found in environment variables")
            return False
        
        # Check if already logged in
        content = await self.analyzer.get_enhanced_page_content()
        
        # Check for login indicator
        if await self.page.query_selector("a[href*='logout']"):
            logger.info("Already logged in")
            return True
        
        # Navigate to login page
        await self.navigate_to(AUSTENDER_LOGIN_URL)
        
        # Fill username
        await self.analyzer.execute_action("input", "#edit-name", AUSTENDER_USERNAME, "Entering username")
        
        # Fill password
        await self.analyzer.execute_action("input", "#edit-pass", AUSTENDER_PASSWORD, "Entering password")
        
        # Click login button
        await self.analyzer.execute_action("click", "#edit-submit", "", "Clicking login button")
        
        # Wait for page to load
        await self.page.wait_for_load_state("networkidle")
        
        # Check if login was successful
        if await self.page.query_selector("a[href*='logout']"):
            logger.info("Login successful")
            return True
        else:
            logger.error("Login failed")
            await self.page.screenshot(path="screenshots/login_failed.png")
            return False
    
    async def analyze_with_ai(self, task):
        """Use OpenAI to analyze the page and determine next steps"""
        # Get enhanced page content
        page_content = await self.analyzer.get_enhanced_page_content()
        
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
        
        # Determine the current page context
        page_context = "unknown"
        if page_content.get("page_structure") and "austender_specific" in page_content["page_structure"]:
            austender_specific = page_content["page_structure"]["austender_specific"]
            page_context = austender_specific.get("page_context", "unknown")
        
        # Build user prompt with rich context
        # Extract interactive elements safely
        interactive_elements_json = json.dumps([{
            "type": el.get("type", ""),
            "text": el.get("text", ""),
            "purpose": el.get("purpose", ""),
            "selectors": el.get("selectors", []),
            "in_viewport": el.get("in_viewport", False)
        } for el in page_content.get("interactive_elements", [])[:10]], indent=2)
        
        # Build user prompt with safer formatting
        user_prompt = f"""
        Task: {task}

        Current page information:
        Title: {page_content.get('title', 'Unknown Title')}
        URL: {page_content.get('url', 'Unknown URL')}
        Page Context: {page_context}
        
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
          {
            "action": "click|input|select|wait|extract",
            "selector": "css_selector",
            "value": "input value if needed",
            "explanation": "Why this action helps accomplish the task"
          }
        ]
        
        Only include the JSON output.
        """
        
        # Call OpenAI API
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
            logger.info(f"AI analysis complete, suggested {len(actions)} actions")
            return {"success": True, "actions": actions}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            
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
                    "explanation": "Waiting for the page to stabilize after failure to parse AI response"
                }
            ]
            
            return {"success": False, "error": "Failed to parse AI response", "fallback_actions": fallback_actions}
    
    async def extract_data(self, selector):
        """Extract data from the current page"""
        try:
            # Get the elements matching the selector
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
            
            return data
        except Exception as e:
            logger.error(f"Error extracting data: {str(e)}")
            return []
    
    async def execute_task(self, task, max_steps=15):
        """Execute the task with AI guidance"""
        logger.info(f"Executing task: {task}")
        steps_taken = 0
        
        # Navigate to the starting URL
        await self.navigate_to(AUSTENDER_URL)
        
        # Main task execution loop
        while steps_taken < max_steps:
            steps_taken += 1
            logger.info(f"Step {steps_taken}/{max_steps}: Analyzing current page...")
            
            # Analyze the current page with AI
            analysis = await self.analyze_with_ai(task)
            
            if not analysis.get("success", False):
                logger.error(f"AI analysis failed: {analysis.get('error', 'Unknown error')}")
                if "fallback_actions" in analysis:
                    actions = analysis["fallback_actions"]
                else:
                    break
            else:
                actions = analysis.get("actions", [])
            
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
                self.results["steps"].append({
                    "step": steps_taken,
                    "action": action,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Handle extract action separately
                if action_type == "extract":
                    extracted_data = await self.extract_data(selector)
                    if extracted_data:
                        logger.info(f"Extracted {len(extracted_data)} items")
                        self.results["data_extracted"].extend(extracted_data)
                        action_success = True
                    break
                
                # Execute the action
                if await self.analyzer.execute_action(action_type, selector, value, explanation):
                    action_success = True
                    logger.info("Action executed successfully")
                    
                    # Wait for page to stabilize
                    try:
                        await self.page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception as e:
                        logger.warning(f"Timeout waiting for page to stabilize: {str(e)}")
                    
                    # Add random delay for more human-like behavior
                    await asyncio.sleep(1 + random.random() * 2)
                    break
                else:
                    logger.warning(f"Action failed: {action_type} {selector}")
            
            if not action_success:
                logger.error("All actions failed")
                break
            
            # Take screenshot after actions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/step_{steps_taken}_{timestamp}.png"
            await self.page.screenshot(path=screenshot_path)
            self.results["screenshots"].append(screenshot_path)
        
        # Final report
        if steps_taken >= max_steps:
            logger.warning(f"Reached maximum steps ({max_steps})")
        else:
            logger.info(f"Task completed in {steps_taken} steps")
        
        # Take final screenshot
        final_screenshot = f"screenshots/task_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await self.page.screenshot(path=final_screenshot)
        self.results["screenshots"].append(final_screenshot)
        
        # Mark as successful if we executed at least one step and didn't hit the limit
        if steps_taken > 0 and steps_taken < max_steps:
            self.results["success"] = True
        
        return self.results

async def main():
    """Main entry point for running Austender tasks"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Austender Task")
    parser.add_argument("--task", type=str, 
                        default="Go to Austender, navigate to the ATM search page, search for 'bridge construction' opportunities in NSW, and extract details for the first 5 results.",
                        help="Task to execute")
    parser.add_argument("--headless", action="store_true", 
                        help="Run browser in headless mode")
    parser.add_argument("--max-steps", type=int, default=15, 
                        help="Maximum number of steps to execute")
    parser.add_argument("--output-file", type=str, 
                        help="File to save results to (JSON format)")
    parser.add_argument("--debug", action="store_true", 
                        help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging based on debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the task
    runner = AustenderTaskRunner(headless=args.headless)
    
    try:
        await runner.start()
        
        # Login first (optional)
        if AUSTENDER_USERNAME and AUSTENDER_PASSWORD:
            if not await runner.login():
                logger.warning("Login failed, continuing without authentication")
        
        # Execute the task
        results = await runner.execute_task(args.task, max_steps=args.max_steps)
        
        # Save results to file if requested
        if args.output_file:
            with open(args.output_file, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {args.output_file}")
        
        # Print summary
        print("\n" + "-"*50)
        print("EXECUTION SUMMARY:")
        print("-"*50)
        print(f"Task: {args.task}")
        print(f"Success: {results['success']}")
        print(f"Steps completed: {len(results['steps'])}")
        print(f"Data items extracted: {len(results['data_extracted'])}")
        print(f"Screenshots: {len(results['screenshots'])}")
        print("-"*50)
        
        # Return the results
        return results
    
    finally:
        # Always close the browser
        await runner.stop()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
