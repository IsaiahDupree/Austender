#!/usr/bin/env python
"""
Run Integrated Austender Agent
Run the enhanced agent with all integrated tools for maximum effectiveness
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Import our custom modules
from multi_tool_integration import ToolIntegration
from adapters.playwright_adapter import PlaywrightAdapter
from adapters.openai_adapter import OpenAIAdapter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("austender_agent.log")
    ]
)
logger = logging.getLogger("austender_integrated")

class IntegratedAustenderAgent:
    """Main class for the integrated agent with multi-tool capabilities"""
    
    def __init__(self, headless=False):
        """Initialize the integrated agent"""
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
        
        # Ensure required directories exist
        Path("screenshots").mkdir(exist_ok=True)
        Path("results").mkdir(exist_ok=True)
        
        # Initialize and register tools
        self._init_tools()
    
    def _init_tools(self):
        """Initialize and register all available tools"""
        # Register Playwright adapter
        self.tool_integration.register_tool(
            "playwright", 
            PlaywrightAdapter(headless=self.headless)
        )
        
        # Register OpenAI adapter
        self.tool_integration.register_tool(
            "openai", 
            OpenAIAdapter(api_key=os.getenv("OPENAI_API_KEY"))
        )
        
        # Add more tool adapters here as they become available
        # self.tool_integration.register_tool("browser_use", BrowserUseAdapter())
        # self.tool_integration.register_tool("firecrawl", FirecrawlAdapter())
        # self.tool_integration.register_tool("stagehand", StagehandAdapter())
    
    async def start(self):
        """Start the agent and initialize all tools"""
        logger.info("Starting Integrated Austender Agent")
        
        # Initialize each tool
        for tool_name, tool in self.tool_integration.tools.items():
            if hasattr(tool, "initialize"):
                await tool.initialize()
        
        return True
    
    async def stop(self):
        """Stop the agent and clean up resources"""
        logger.info("Stopping Integrated Austender Agent")
        
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshots/login_page_{timestamp}.png"
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshots/after_login_{timestamp}.png"
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
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/step_{steps_taken}_{timestamp}.png"
            await playwright_tool.page.screenshot(path=screenshot_path)
            self.session_data["screenshots"].append(screenshot_path)
            
            # Analyze the current page - directly use OpenAI for most reliable results
            openai_tool = self.tool_integration.tools.get("openai")
            if not openai_tool:
                logger.error("OpenAI tool not available for page analysis")
                actions = [{
                    "action": "wait",
                    "selector": "",
                    "value": "3",
                    "explanation": "OpenAI tool not available - waiting before retry"
                }]
            else:
                try:
                    # Direct call to OpenAI adapter for analysis
                    logger.info("Analyzing page with OpenAI...")
                    analysis_result = await openai_tool.analyze_page(page_content, task)
                    
                    if analysis_result.get("success", False):
                        actions = analysis_result.get("actions", [])
                        logger.info(f"OpenAI analysis successful, found {len(actions)} actions")
                    else:
                        logger.warning(f"OpenAI analysis failed: {analysis_result.get('error', 'Unknown error')}")
                        fallback_actions = analysis_result.get("fallback_actions", [])
                        if fallback_actions:
                            actions = fallback_actions
                            logger.info(f"Using {len(actions)} fallback actions")
                        else:
                            actions = []
                except Exception as e:
                    logger.error(f"Error during OpenAI page analysis: {str(e)}")
                    actions = [{
                        "action": "wait",
                        "selector": "",
                        "value": "3",
                        "explanation": f"Error recovery: {str(e)}"
                    }]
            
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
                    extract_params = {"selector": selector}
                    extract_result = await self.tool_integration.execute_action("extract", extract_params)
                    
                    if extract_result.get("success", False) and isinstance(extract_result.get("result", []), list):
                        extracted_items = extract_result.get("result", [])
                        
                        if extracted_items:
                            self.session_data["extracted_data"].extend(extracted_items)
                            logger.info(f"Extracted {len(extracted_items)} items")
                            action_success = True
                            
                            # Process the extracted data with OpenAI
                            openai_tool = self.tool_integration.tools.get("openai")
                            if openai_tool and len(extracted_items) > 0:
                                analysis_result = await openai_tool.process_extraction(extracted_items, task)
                                if analysis_result.get("success", False):
                                    self.session_data["data_analysis"] = analysis_result.get("analysis", {})
                    
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
        
        # Final report
        if steps_taken >= max_steps:
            logger.warning(f"Reached maximum steps ({max_steps})")
        else:
            logger.info(f"Task completed in {steps_taken} steps")
        
        # Take final screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_screenshot = f"screenshots/task_complete_{timestamp}.png"
        await playwright_tool.page.screenshot(path=final_screenshot)
        self.session_data["screenshots"].append(final_screenshot)
        
        # Mark as successful if we executed at least one step and extracted data or didn't hit the limit
        success = (steps_taken > 0 and (steps_taken < max_steps or len(self.session_data["extracted_data"]) > 0))
        self.session_data["success"] = success
        
        return self.session_data
    
    async def save_results(self, filename=None):
        """Save results to a file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results/austender_results_{timestamp}.json"
        
        # Convert to JSON-serializable format
        serializable_results = {
            "success": self.session_data.get("success", False),
            "steps_executed": self.session_data.get("steps_executed", []),
            "extracted_data": self.session_data.get("extracted_data", []),
            "screenshots": self.session_data.get("screenshots", []),
            "data_analysis": self.session_data.get("data_analysis", {}),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filename, "w") as f:
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Results saved to {filename}")
        return filename

async def main():
    """Main entry point for running the Integrated Austender Agent"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Integrated Austender Agent")
    parser.add_argument("--task", type=str, 
                        default="Search for bridge construction opportunities in NSW and extract the details",
                        help="Task to execute")
    parser.add_argument("--headless", action="store_true", 
                        help="Run browser in headless mode")
    parser.add_argument("--max-steps", type=int, default=15, 
                        help="Maximum number of steps to execute")
    parser.add_argument("--output-file", type=str, 
                        help="File to save results to (JSON format)")
    parser.add_argument("--login", action="store_true",
                        help="Attempt to log in before executing task")
    parser.add_argument("--debug", action="store_true", 
                        help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging based on debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Print welcome message
    print("\n" + "="*70)
    print("INTEGRATED AUSTENDER AGENT".center(70))
    print("="*70)
    print(f"Task: {args.task}")
    print(f"Headless mode: {'Yes' if args.headless else 'No'}")
    print(f"Maximum steps: {args.max_steps}")
    print("="*70 + "\n")
    
    # Run the agent
    agent = IntegratedAustenderAgent(headless=args.headless)
    
    try:
        await agent.start()
        
        # Login if requested
        if args.login and os.getenv("AUSTENDER_USERNAME") and os.getenv("AUSTENDER_PASSWORD"):
            print("Attempting to log in...")
            if not await agent.login():
                print("Login failed, continuing without authentication")
        
        # Execute the task
        print(f"Executing task: {args.task}")
        print("This may take several minutes depending on the complexity of the task.\n")
        
        results = await agent.execute_task(args.task, max_steps=args.max_steps)
        
        # Save results to file
        output_file = args.output_file
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"results/austender_results_{timestamp}.json"
        
        saved_file = await agent.save_results(output_file)
        
        # Print summary
        print("\n" + "-"*70)
        print("EXECUTION SUMMARY:".center(70))
        print("-"*70)
        print(f"Task: {args.task}")
        print(f"Success: {results.get('success', False)}")
        print(f"Steps completed: {len(results.get('steps_executed', []))}")
        print(f"Data items extracted: {len(results.get('extracted_data', []))}")
        print(f"Screenshots: {len(results.get('screenshots', []))}")
        print(f"Results saved to: {saved_file}")
        print("-"*70)
        
        # Print data analysis if available
        if "data_analysis" in results and results["data_analysis"]:
            print("\nDATA ANALYSIS:".center(70))
            print("-"*70)
            analysis = results["data_analysis"]
            
            if "analysis" in analysis:
                print(f"Analysis: {analysis['analysis']}")
            
            if "relevant_items" in analysis:
                print(f"Relevant items: {analysis['relevant_items']}")
            
            if "patterns" in analysis and analysis["patterns"]:
                print("Patterns:")
                for pattern in analysis["patterns"]:
                    print(f"- {pattern}")
            
            if "next_steps" in analysis and analysis["next_steps"]:
                print("Recommended next steps:")
                for step in analysis["next_steps"]:
                    print(f"- {step}")
            
            print("-"*70)
        
        return results
    
    finally:
        # Always stop the agent
        await agent.stop()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
