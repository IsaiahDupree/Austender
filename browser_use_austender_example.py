#!/usr/bin/env python3
"""
Browser-Use Austender Example
A simple example of using Browser-Use to navigate the Austender website
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Add the browser-use directory to the path
sys.path.append(os.path.abspath('browser-use-main/browser-use-main'))

# Now import from the local browser-use
from langchain_openai import ChatOpenAI
try:
    from browser_use import Agent
    from browser_use.browser.browser import Browser, BrowserConfig
except ImportError as e:
    print(f"Error importing browser_use: {e}")
    print("Please ensure browser-use-main is in the correct location")
    print("Current path includes: {}".format(sys.path))
    sys.exit(1)

# Load environment variables
load_dotenv()

def format_output(output):
    """Format output for better readability"""
    if isinstance(output, str):
        return output
    elif isinstance(output, (dict, list)):
        return json.dumps(output, indent=2)
    else:
        return str(output)

async def run_austender_search(task, headless=False, save_results=True):
    """Run an Austender search using Browser-Use"""
    print(f"Task: {task}")
    
    # Create output directory if it doesn't exist
    os.makedirs("results", exist_ok=True)
    
    # Initialize the LLM
    llm = ChatOpenAI(
        model='gpt-4o',
        temperature=0.2,
    )
    
    # Initialize Browser-Use with custom configuration
    browser_config = BrowserConfig(
        headless=headless,
        viewport_width=1280,
        viewport_height=800,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    )
    
    # Create the agent with the given task
    agent = Agent(
        task=task,
        llm=llm,
        browser=Browser(config=browser_config),
    )
    
    # Run the agent
    result = await agent.run()
    
    # Print the result
    print("\nResult:")
    print(format_output(result))
    
    # Save the result to a file if requested
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results/austender_browser_use_{timestamp}.json"
        
        with open(filename, "w") as f:
            if isinstance(result, dict):
                json.dump(result, f, indent=2)
            else:
                f.write(str(result))
        
        print(f"Results saved to {filename}")
    
    return result

async def main():
    """Main function to run examples"""
    # Basic task - search for opportunities
    search_task = """
    Go to the Australian Government's tender website at https://www.tenders.gov.au/
    Navigate to the Approaches to Market (ATM) search page
    Search for 'bridge construction' and filter by New South Wales (NSW) if possible
    Extract details of the first 3 results including:
    - ATM ID
    - Title
    - Category
    - Closing date
    - Agency
    
    Return the results as a JSON object with an array of opportunities
    """
    
    await run_austender_search(search_task, headless=False)

if __name__ == "__main__":
    asyncio.run(main())
