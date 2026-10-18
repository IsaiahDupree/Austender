#!/usr/bin/env python
"""
Test script for the Austender Agent
This script runs a basic test of the agent with minimal configuration
"""
import asyncio
import logging
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("austender_test")

# Import the agent
from austender_agent import AustenderAgent

async def run_test():
    """Run a basic test of the Austender Agent"""
    # Create results directory
    Path("results").mkdir(exist_ok=True)
    
    # Create the agent (non-headless for visual inspection)
    agent = AustenderAgent(headless=False)
    
    try:
        # Start the agent
        logger.info("Starting agent...")
        await agent.start()
        
        # Simple test task
        test_task = "Navigate to the ATM search page, search for bridge construction opportunities in NSW"
        logger.info(f"Executing test task: {test_task}")
        
        # Execute the task with a limit of 10 steps
        results = await agent.execute_task(test_task, max_steps=10)
        
        # Save detailed results
        with open("results/test_results_detailed.json", "w") as f:
            json.dump(results, f, indent=2)
        
        # Create a simplified summary
        summary = {
            "success": results.get("success", False),
            "steps_completed": len(results.get("steps_executed", [])),
            "data_extracted": len(results.get("extracted_data", [])),
            "screenshots": results.get("screenshots", [])
        }
        
        # Save summary
        with open("results/test_results_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print("\n" + "-"*50)
        print("TEST RESULTS:")
        print("-"*50)
        print(f"Task: {test_task}")
        print(f"Success: {summary['success']}")
        print(f"Steps completed: {summary['steps_completed']}")
        print(f"Data items extracted: {summary['data_extracted']}")
        print(f"Screenshots: {len(summary['screenshots'])}")
        print("-"*50)
        
        return summary
        
    finally:
        # Always stop the agent
        logger.info("Stopping agent...")
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(run_test())
