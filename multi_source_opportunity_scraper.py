#!/usr/bin/env python3
"""
Multi-Source Opportunity Scraper
--------------------------------
This script integrates Browser-Use with multiple scraping strategies to extract 
construction opportunities from government websites including Austender, ANI, ICN, and SAM.
It builds a searchable database of opportunities with details like market timing,
capital value, scope, source links, procurement panels, and more.
"""

import os
import json
import time
import random
import logging
import asyncio
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Set

# Browser-Use imports
from browser_use.agent.service import Agent
from browser_use.browser.browser import Browser, BrowserConfig, BrowserContextConfig
from browser_use.controller.service import Controller

# LLM provider
from langchain_openai import ChatOpenAI

# Local imports
from scrapers.austender_scraper import AustenderScraper
from scrapers.ani_scraper import ANIScraper
from scrapers.icn_scraper import ICNScraper
from scrapers.sam_scraper import SAMScraper
from utils.database import OpportunityDatabase
from utils.email_notifier import EmailNotifier

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/multi_source_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("multi_source_scraper")

# Ensure directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("data", exist_ok=True)

class MultiSourceOpportunityScraper:
    """
    Integrated scraper that coordinates scraping operations across multiple
    government websites to build a comprehensive opportunity database.
    """
    
    def __init__(self, 
                 headless: bool = False,
                 model: str = "gpt-4o",
                 db_path: str = "data/opportunities.db"):
        """Initialize the multi-source scraper."""
        self.headless = headless
        self.model = model
        self.db_path = db_path
        
        # Initialize the controller for custom functions
        self.controller = Controller()
        
        # Initialize the database
        self.db = OpportunityDatabase(db_path)
        
        # Initialize individual site scrapers
        self.scrapers = {
            "austender": AustenderScraper(headless=headless, model=model),
            "ani": ANIScraper(headless=headless, model=model),
            "icn": ICNScraper(headless=headless, model=model),
            "sam": SAMScraper(headless=headless, model=model)
        }
        
        # Initialize email notifier
        self.email_notifier = EmailNotifier()
        
        logger.info("Initialized Multi-Source Opportunity Scraper")
    
    async def run_scraping_job(self, 
                              keywords: List[str] = ["construction"],
                              max_opportunities_per_source: int = 50) -> Dict:
        """
        Run a full scraping job across all sources.
        
        Args:
            keywords: List of keywords to search for
            max_opportunities_per_source: Maximum number of opportunities to gather per source
            
        Returns:
            Dict containing statistics about the scraping job
        """
        start_time = time.time()
        results = {
            "started_at": datetime.now().isoformat(),
            "sources_scraped": 0,
            "opportunities_found": 0,
            "new_opportunities": 0,
            "updated_opportunities": 0,
            "errors": [],
            "source_stats": {}
        }
        
        try:
            # Scrape each source
            for source_name, scraper in self.scrapers.items():
                logger.info(f"Starting scraping job for {source_name}")
                source_results = {
                    "opportunities_found": 0,
                    "new_opportunities": 0,
                    "updated_opportunities": 0,
                    "errors": 0
                }
                
                try:
                    # Initialize the scraper
                    await scraper.initialize()
                    
                    # Scrape opportunities for each keyword
                    for keyword in keywords:
                        try:
                            opportunities = await scraper.search_opportunities(
                                keyword=keyword,
                                max_results=max_opportunities_per_source // len(keywords)
                            )
                            
                            # Process opportunities
                            for opp in opportunities:
                                try:
                                    # Get full details
                                    if "id" in opp:
                                        details = await scraper.get_opportunity_details(
                                            opportunity_id=opp["id"],
                                            opportunity_url=opp.get("url")
                                        )
                                        
                                        # Combine basic info with details
                                        opportunity_data = {**opp, **details}
                                        
                                        # Add source info
                                        opportunity_data["source"] = source_name
                                        opportunity_data["last_updated"] = datetime.now().isoformat()
                                        
                                        # Store in database
                                        is_new = self.db.add_or_update_opportunity(opportunity_data)
                                        
                                        # Update statistics
                                        source_results["opportunities_found"] += 1
                                        if is_new:
                                            source_results["new_opportunities"] += 1
                                        else:
                                            source_results["updated_opportunities"] += 1
                                    
                                except Exception as e:
                                    logger.error(f"Error processing opportunity {opp.get('id', 'unknown')}: {str(e)}")
                                    source_results["errors"] += 1
                                    results["errors"].append(f"{source_name} - {str(e)}")
                        
                        except Exception as e:
                            logger.error(f"Error searching {source_name} with keyword '{keyword}': {str(e)}")
                            source_results["errors"] += 1
                            results["errors"].append(f"{source_name} - {str(e)}")
                    
                    # Update overall results
                    results["sources_scraped"] += 1
                    results["opportunities_found"] += source_results["opportunities_found"]
                    results["new_opportunities"] += source_results["new_opportunities"]
                    results["updated_opportunities"] += source_results["updated_opportunities"]
                    results["source_stats"][source_name] = source_results
                    
                except Exception as e:
                    logger.error(f"Error scraping {source_name}: {str(e)}")
                    results["errors"].append(f"{source_name} - {str(e)}")
                
                finally:
                    # Ensure the scraper closes properly
                    await scraper.close()
            
            # Send email notification about new opportunities
            if results["new_opportunities"] > 0:
                new_opportunities = self.db.get_recent_opportunities(
                    limit=results["new_opportunities"],
                    hours=24  # Only get opportunities from the last 24 hours
                )
                
                self.email_notifier.send_new_opportunities_notification(new_opportunities)
                logger.info(f"Sent email notification about {len(new_opportunities)} new opportunities")
            
            # Calculate timing information
            end_time = time.time()
            results["duration_seconds"] = end_time - start_time
            results["completed_at"] = datetime.now().isoformat()
            
            # Save results to file
            output_file = f"output/scraping_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {output_file}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in scraping job: {str(e)}")
            results["errors"].append(f"Global error - {str(e)}")
            return results
    
    async def close(self):
        """Close all resources."""
        for scraper in self.scrapers.values():
            await scraper.close()
        self.db.close()
        logger.info("Closed all resources")

async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Source Government Opportunity Scraper")
    parser.add_argument("--keywords", type=str, nargs="+", default=["construction"], 
                        help="Keywords to search for")
    parser.add_argument("--max-per-source", type=int, default=50, 
                        help="Maximum number of opportunities per source")
    parser.add_argument("--headless", action="store_true", 
                        help="Run browsers in headless mode")
    parser.add_argument("--model", type=str, default="gpt-4o", 
                        help="OpenAI model to use")
    parser.add_argument("--db-path", type=str, default="data/opportunities.db", 
                        help="Path to SQLite database")
    parser.add_argument("--sources", type=str, nargs="+", 
                        choices=["austender", "ani", "icn", "sam", "all"], 
                        default=["all"], help="Sources to scrape")
    
    args = parser.parse_args()
    
    # Create the scraper
    scraper = MultiSourceOpportunityScraper(
        headless=args.headless,
        model=args.model,
        db_path=args.db_path
    )
    
    try:
        # Run the scraping job
        results = await scraper.run_scraping_job(
            keywords=args.keywords,
            max_opportunities_per_source=args.max_per_source
        )
        
        logger.info(f"Scraping job completed with {results['opportunities_found']} opportunities found")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
    finally:
        # Clean up
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
