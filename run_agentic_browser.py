#!/usr/bin/env python
# Enhanced Agentic Browser Runner for Austender
# This script executes the enhanced agentic browser to perform custom tasks

import os
import json
import asyncio
import logging
import argparse
from pathlib import Path
from datetime import datetime
from agentic_austender_browser import AgenticAustenderBrowser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('agentic_runner')

async def main(args):
    """Main function to run the enhanced agentic browser."""
    logger.info("Starting Enhanced Agentic Browser for Austender")
    
    # Ensure screenshots directory exists
    Path("screenshots").mkdir(exist_ok=True)
    
    # Create and start the browser
    browser = AgenticAustenderBrowser(headless=args.headless)
    
    try:
        # Start the browser
        await browser.start()
        
        # Define the custom task or use default
        custom_task = args.custom_task or "Go to Austender, navigate to the ATM search page, search for 'bridge construction' opportunities in NSW, and extract details for the first 5 results."
        
        logger.info(f"Executing task: {custom_task}")
        
        # Execute the task
        results = await browser.execute_task(custom_task, max_steps=args.max_steps)
        
        # Log the results
        if results.get("success", False):
            logger.info("Task completed successfully!")
            if "data_extracted" in results and results["data_extracted"]:
                logger.info(f"Extracted {len(results['data_extracted'])} data items")
        else:
            logger.warning("Task did not complete successfully")
            if "error" in results:
                logger.error(f"Error: {results['error']}")
        
        # Save results to file if requested
        if args.output_file:
            output_path = Path(args.output_file)
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {output_path}")
        
        # Print summary to console
        print("\n" + "-"*50)
        print("EXECUTION SUMMARY:")
        print("-"*50)
        print(f"Task: {custom_task}")
        print(f"Success: {results.get('success', False)}")
        print(f"Steps completed: {len(results.get('steps', []))}")
        if "error" in results:
            print(f"Error: {results['error']}")
        if "final_screenshot" in results:
            print(f"Final screenshot: {results['final_screenshot']}")
        print("-"*50)
        
        return results
    
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    
    finally:
        # Ensure browser is closed properly
        await browser.stop()
        logger.info("Browser closed, execution complete")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Enhanced Agentic Austender Browser")
    parser.add_argument("--custom-task", type=str, 
                        help="Custom task to execute (e.g., 'Search for bridge construction opportunities in NSW')")
    parser.add_argument("--headless", action="store_true", 
                        help="Run browser in headless mode")
    parser.add_argument("--max-steps", type=int, default=15, 
                        help="Maximum number of steps to execute")
    parser.add_argument("--output-file", type=str, 
                        help="File to save results to (JSON format)")
    parser.add_argument("--debug", action="store_true", 
                        help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the main function
    results = asyncio.run(main(args))
