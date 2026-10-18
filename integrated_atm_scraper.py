#!/usr/bin/env python3
"""
Integrated ATM Scraper for Austender
------------------------------------
Comprehensive scraper that integrates multiple approaches:
1. Multi-tool approach with Playwright
2. Specialized Firecrawl integration for government websites
3. Scheduled attempts for optimal access times

This represents our most comprehensive approach combining all techniques
to create a robust and adaptive solution.
"""

import os
import sys
import json
import time
import random
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import specialized scrapers
from multi_tool_atm_scraper import MultiToolATMScraper
from firecrawl_scraper import FirecrawlScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"logs/integrated_scraper_{datetime.now().strftime('%Y%m%d_%H%M')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("integrated_scraper")

# Create directories
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("reports", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)

class IntegratedATMScraper:
    """Integrates multiple scraping approaches with fallback mechanisms."""
    
    def __init__(self, config=None):
        """Initialize the integrated scraper with configuration."""
        self.config = config or {}
        
        # Configure Firecrawl
        self.firecrawl_url = os.getenv("FIRECRAWL_BASE_URL", "http://localhost:3005")
        
        # Scraper options
        self.headless = self.config.get("headless", False)
        self.debug = self.config.get("debug", True)
        self.use_proxy = self.config.get("use_proxy", False)
        self.proxy = self.config.get("proxy", None)
        self.browser_rotation = self.config.get("browser_rotation", True)
        
        # Initialize approaches
        self.multi_tool_scraper = None  # Will be initialized on demand
        self.firecrawl_scraper = None   # Will be initialized on demand
        
        # Credentials if available
        self.credentials = {
            "username": os.getenv("AUSTENDER_USERNAME", ""),
            "password": os.getenv("AUSTENDER_PASSWORD", "")
        }
        
        logger.info("Initialized Integrated ATM Scraper")
    
    async def scrape_with_multi_tool(self, keyword=None, state=None):
        """Attempt scraping using the multi-tool approach."""
        logger.info("Attempting to scrape with Multi-Tool approach")
        
        try:
            browser_type = random.choice(["chromium", "firefox", "webkit"]) if self.browser_rotation else "chromium"
            
            # Initialize multi-tool scraper if not already done
            if not self.multi_tool_scraper:
                self.multi_tool_scraper = MultiToolATMScraper(
                    headless=self.headless,
                    debug=self.debug,
                    browser_type=browser_type,
                    use_proxy=self.use_proxy
                )
            
            # Set search parameters if provided
            if keyword:
                self.multi_tool_scraper.keyword = keyword
            if state:
                self.multi_tool_scraper.state = state
            
            # Execute with fallbacks
            results = await self.multi_tool_scraper.execute_with_fallbacks()
            
            if results.get("success", False) and results.get("data", []):
                logger.info(f"Multi-Tool approach succeeded with {len(results['data'])} items")
                return {
                    "success": True,
                    "method": "multi_tool",
                    "data": results["data"],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.warning("Multi-Tool approach failed to extract data")
                return {
                    "success": False,
                    "method": "multi_tool",
                    "data": [],
                    "error": results.get("error", "No data extracted")
                }
        
        except Exception as e:
            logger.error(f"Error in Multi-Tool approach: {str(e)}")
            return {
                "success": False,
                "method": "multi_tool",
                "data": [],
                "error": str(e)
            }
    
    def scrape_with_firecrawl(self, category="construction", max_pages=3):
        """Attempt scraping using Firecrawl."""
        logger.info("Attempting to scrape with Firecrawl")
        
        try:
            # Initialize Firecrawl scraper if not already done
            if not self.firecrawl_scraper:
                self.firecrawl_scraper = FirecrawlScraper(api_url=self.firecrawl_url)
            
            # Scrape opportunities from Austender
            opportunities = self.firecrawl_scraper.scrape_opportunities(
                site="austender",
                category=category,
                max_pages=max_pages
            )
            
            if opportunities:
                logger.info(f"Firecrawl approach succeeded with {len(opportunities)} items")
                
                # Get detailed information for each opportunity
                detailed_opportunities = []
                for opp in opportunities:
                    details = self.firecrawl_scraper.get_opportunity_details(
                        opp["url"], opp["source"]
                    )
                    detailed_opportunities.append({**opp, **details})
                    
                    # Be nice to the server
                    time.sleep(random.uniform(2, 4))
                
                return {
                    "success": True,
                    "method": "firecrawl",
                    "data": detailed_opportunities,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.warning("Firecrawl approach failed to extract data")
                return {
                    "success": False,
                    "method": "firecrawl",
                    "data": [],
                    "error": "No data extracted"
                }
        
        except Exception as e:
            logger.error(f"Error in Firecrawl approach: {str(e)}")
            return {
                "success": False,
                "method": "firecrawl",
                "data": [],
                "error": str(e)
            }
    
    async def execute_with_both_approaches(self, keyword=None, state=None, category="construction"):
        """Execute both approaches and use the best result."""
        logger.info("Executing with both approaches")
        
        results = {
            "success": False,
            "method": None,
            "data": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Try Multi-Tool approach first
        multi_tool_result = await self.scrape_with_multi_tool(keyword, state)
        if multi_tool_result["success"]:
            logger.info("Multi-Tool approach succeeded, using its results")
            results = multi_tool_result
        else:
            logger.info("Multi-Tool approach failed, trying Firecrawl")
            
            # If Multi-Tool failed, try Firecrawl
            firecrawl_result = self.scrape_with_firecrawl(category)
            if firecrawl_result["success"]:
                logger.info("Firecrawl approach succeeded, using its results")
                results = firecrawl_result
        
        # Save results
        if results["success"]:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/integrated_results_{timestamp}.json"
            with open(filename, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved results to {filename}")
        
        return results
    
    async def run_with_parameters(self, keywords=None, states=None):
        """Run the scraper with multiple keyword and state combinations."""
        if not keywords:
            keywords = ["construction", "infrastructure", "bridge"]
        if not states:
            states = ["NSW", "VIC", "QLD", None]  # None means no state filter
        
        all_results = []
        
        # Try different combinations for better coverage
        for keyword in keywords:
            for state in states:
                logger.info(f"Trying combination: keyword={keyword}, state={state}")
                result = await self.execute_with_both_approaches(keyword, state)
                
                # Only save unique items
                if result["success"] and result["data"]:
                    all_results.append(result)
                
                # Add random delay between attempts
                delay = random.uniform(5, 10)
                logger.info(f"Waiting {delay:.1f} seconds before next attempt")
                await asyncio.sleep(delay)
        
        # Combine and deduplicate results
        combined_data = []
        unique_refs = set()
        
        for result in all_results:
            for item in result["data"]:
                ref_id = item.get("reference_id") or item.get("id")
                if ref_id and ref_id not in unique_refs:
                    unique_refs.add(ref_id)
                    combined_data.append(item)
        
        logger.info(f"Combined {len(combined_data)} unique items from all approaches")
        
        # Save combined results
        if combined_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/combined_results_{timestamp}.json"
            with open(filename, "w") as f:
                json.dump(combined_data, f, indent=2)
            logger.info(f"Saved combined results to {filename}")
        
        return {
            "success": bool(combined_data),
            "method": "integrated",
            "data": combined_data,
            "timestamp": datetime.now().isoformat(),
            "total_attempts": len(keywords) * len(states)
        }

async def run_test(config=None):
    """Run a test of the integrated scraper."""
    scraper = IntegratedATMScraper(config)
    result = await scraper.execute_with_both_approaches()
    return result

def main():
    """Main function to run the integrated scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Integrated ATM Scraper")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--use-proxy", action="store_true", help="Use proxy for requests")
    parser.add_argument("--keywords", type=str, help="Comma-separated list of keywords")
    parser.add_argument("--states", type=str, help="Comma-separated list of states")
    parser.add_argument("--test", action="store_true", help="Run a single test")
    
    args = parser.parse_args()
    
    # Parse config from arguments
    config = {
        "headless": args.headless,
        "debug": args.debug,
        "use_proxy": args.use_proxy
    }
    
    if args.test:
        # Run a single test
        print("Running test with integrated scraper...")
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(run_test(config))
        print(f"Test completed with success: {result['success']}")
        if result['success']:
            print(f"Extracted {len(result['data'])} items using {result['method']}")
    else:
        # Run with parameters
        keywords = args.keywords.split(",") if args.keywords else None
        states = args.states.split(",") if args.states else None
        
        scraper = IntegratedATMScraper(config)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(scraper.run_with_parameters(keywords, states))
        
        print(f"Completed with success: {result['success']}")
        print(f"Total unique items: {len(result['data'])}")
        print(f"Total attempts: {result['total_attempts']}")

if __name__ == "__main__":
    main()
