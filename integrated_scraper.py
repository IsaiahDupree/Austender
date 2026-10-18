#!/usr/bin/env python3
"""
Integrated Austender Scraper
----------------------------
This script provides a unified interface for scraping Austender using
multiple tools and approaches, dynamically selecting the best method
based on success rates and anti-bot detection avoidance.
"""

import os
import json
import time
import logging
import argparse
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"integrated_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("integrated_scraper")

# Create output directories
os.makedirs("output", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)

# Load environment variables
load_dotenv()

# Default URLs and configurations
AUSTENDER_URL = "https://www.tenders.gov.au/Search/KeywordSearch?keyword=construction&type=ATM&dateType=ClosingDate"
BROWSER_USE_API_URL = "http://localhost:7788/api"
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

class IntegratedScraper:
    """
    Integrated scraper that can use multiple methods to extract data from Austender.
    """
    
    def __init__(self):
        self.opportunities = []
        self.current_strategy = None
        self.strategy_success_rates = {
            "browser_use": 0.0,
            "playwright": 0.0,
            "firecrawl": 0.0,
            "openai": 0.0
        }
        logger.info("Initialized Integrated Scraper")
    
    def scrape(self, strategy: str = "auto", url: str = AUSTENDER_URL, 
               max_pages: int = 1, get_details: bool = False) -> List[Dict]:
        """
        Scrape opportunities using the specified strategy or automatically select the best one.
        
        Args:
            strategy: The strategy to use ('auto', 'browser_use', 'playwright', 'firecrawl', 'openai')
            url: The URL to scrape
            max_pages: Maximum number of pages to scrape
            get_details: Whether to get detailed information for each opportunity
            
        Returns:
            List of opportunities
        """
        if strategy == "auto":
            strategy = self._select_best_strategy()
        
        logger.info(f"Using strategy: {strategy}")
        self.current_strategy = strategy
        
        try:
            if strategy == "browser_use":
                opportunities = self._scrape_with_browser_use(url, max_pages, get_details)
            elif strategy == "playwright":
                opportunities = self._scrape_with_playwright(url, max_pages, get_details)
            elif strategy == "firecrawl":
                opportunities = self._scrape_with_firecrawl(url, max_pages, get_details)
            elif strategy == "openai":
                opportunities = self._scrape_with_openai(url, max_pages, get_details)
            else:
                logger.error(f"Unknown strategy: {strategy}")
                return []
            
            self.opportunities = opportunities
            
            if opportunities:
                self._update_success_rate(strategy, 1.0)
                logger.info(f"Successfully scraped {len(opportunities)} opportunities using {strategy}")
            else:
                self._update_success_rate(strategy, 0.0)
                logger.warning(f"No opportunities found using {strategy}")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error scraping with {strategy}: {str(e)}")
            self._update_success_rate(strategy, 0.0)
            return []
    
    def _select_best_strategy(self) -> str:
        """
        Select the best strategy based on success rates and randomization to avoid detection.
        
        Returns:
            The selected strategy
        """
        # Add randomization factor to avoid predictable patterns
        randomized_rates = {}
        strategies = list(self.strategy_success_rates.keys())
        
        # If we have no data, randomize with higher weight for browser_use
        if all(rate == 0.0 for rate in self.strategy_success_rates.values()):
            weights = [0.4, 0.3, 0.2, 0.1]  # Weights for browser_use, playwright, firecrawl, openai
            return random.choices(strategies, weights=weights, k=1)[0]
        
        # Otherwise use success rates but add some randomization
        for strategy, rate in self.strategy_success_rates.items():
            # Add +/- 0.1 randomization but ensure rate stays between 0 and 1
            random_factor = random.uniform(-0.1, 0.1)
            randomized_rates[strategy] = max(0.0, min(1.0, rate + random_factor))
        
        # Select based on weighted random choice
        best_strategy = max(randomized_rates, key=randomized_rates.get)
        
        # But occasionally try a different strategy to explore
        if random.random() < 0.2:  # 20% chance to try a different strategy
            other_strategies = [s for s in strategies if s != best_strategy]
            return random.choice(other_strategies)
        
        return best_strategy
    
    def _update_success_rate(self, strategy: str, success_rate: float) -> None:
        """
        Update the success rate for a strategy.
        
        Args:
            strategy: The strategy to update
            success_rate: The success rate (0.0 to 1.0)
        """
        current_rate = self.strategy_success_rates.get(strategy, 0.0)
        # Weighted average: 70% old rate, 30% new rate
        new_rate = (current_rate * 0.7) + (success_rate * 0.3)
        self.strategy_success_rates[strategy] = new_rate
        logger.debug(f"Updated success rate for {strategy}: {new_rate:.2f}")
    
    def _scrape_with_browser_use(self, url: str, max_pages: int, get_details: bool) -> List[Dict]:
        """
        Scrape Austender using the Browser Use API.
        
        Args:
            url: The URL to scrape
            max_pages: Maximum number of pages to scrape
            get_details: Whether to get detailed information for each opportunity
            
        Returns:
            List of opportunities
        """
        try:
            from browser_use_austender_scraper import BrowserUseClient, AustenderScraper
            
            browser_client = BrowserUseClient(BROWSER_USE_API_URL)
            scraper = AustenderScraper(browser_client)
            
            opportunities = scraper.scrape_search_results(url, max_pages)
            
            if get_details and opportunities:
                for i, opp in enumerate(opportunities):
                    if 'id' in opp and opp['id']:
                        logger.info(f"Fetching details for opportunity {i+1}/{len(opportunities)}: {opp['id']}")
                        details = scraper.get_opportunity_details(opportunity_id=opp['id'])
                        if details:
                            opportunities[i].update(details)
                        time.sleep(1)  # Be nice to the server
            
            return opportunities
            
        except ImportError:
            logger.error("Failed to import browser_use_austender_scraper.py. Make sure it exists.")
            return []
        except Exception as e:
            logger.error(f"Error with Browser Use strategy: {str(e)}")
            return []
    
    def _scrape_with_playwright(self, url: str, max_pages: int, get_details: bool) -> List[Dict]:
        """
        Scrape Austender using Playwright directly.
        
        Args:
            url: The URL to scrape
            max_pages: Maximum number of pages to scrape
            get_details: Whether to get detailed information for each opportunity
            
        Returns:
            List of opportunities
        """
        try:
            from playwright_austender_scraper import AdvancedAustenderScraper
            
            scraper = AdvancedAustenderScraper(headless=False)
            
            opportunities = scraper.scrape_search_results(url, max_pages)
            
            if get_details and opportunities:
                detailed_opportunities = []
                
                for i, opp in enumerate(opportunities):
                    if 'id' in opp and opp['id']:
                        logger.info(f"Fetching details for opportunity {i+1}/{len(opportunities)}: {opp['id']}")
                        details = scraper.get_opportunity_details(opportunity_id=opp['id'])
                        if details:
                            detailed_opp = {**opp, **details}
                            detailed_opportunities.append(detailed_opp)
                        else:
                            detailed_opportunities.append(opp)
                        time.sleep(1)  # Be nice to the server
                    else:
                        detailed_opportunities.append(opp)
                
                opportunities = detailed_opportunities
            
            scraper.close()
            return opportunities
            
        except ImportError:
            logger.error("Failed to import playwright_austender_scraper.py. Make sure it exists.")
            return []
        except Exception as e:
            logger.error(f"Error with Playwright strategy: {str(e)}")
            return []
    
    def _scrape_with_firecrawl(self, url: str, max_pages: int, get_details: bool) -> List[Dict]:
        """
        Scrape Austender using the Firecrawl API.
        
        Args:
            url: The URL to scrape
            max_pages: Maximum number of pages to scrape
            get_details: Whether to get detailed information for each opportunity
            
        Returns:
            List of opportunities
        """
        try:
            import requests
            
            if not FIRECRAWL_API_KEY:
                logger.error("FIRECRAWL_API_KEY is not set in .env file")
                return []
            
            # Construct payload for Firecrawl API
            payload = {
                "url": url,
                "max_pages": max_pages,
                "get_details": get_details,
                "api_key": FIRECRAWL_API_KEY
            }
            
            # Make request to Firecrawl API
            response = requests.post(
                "https://api.firecrawl.dev/v1/scrape",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                opportunities = data.get("opportunities", [])
                return opportunities
            else:
                logger.error(f"Firecrawl API error: {response.status_code} {response.text}")
                return []
                
        except ImportError:
            logger.error("Failed to import required packages for Firecrawl API")
            return []
        except Exception as e:
            logger.error(f"Error with Firecrawl strategy: {str(e)}")
            return []
    
    def _scrape_with_openai(self, url: str, max_pages: int, get_details: bool) -> List[Dict]:
        """
        Scrape Austender using OpenAI for assistance with Playwright.
        
        Args:
            url: The URL to scrape
            max_pages: Maximum number of pages to scrape
            get_details: Whether to get detailed information for each opportunity
            
        Returns:
            List of opportunities
        """
        try:
            from playwright.sync_api import sync_playwright
            import openai
            
            if not OPENAI_API_KEY:
                logger.error("OPENAI_API_KEY is not set in .env file")
                return []
            
            openai.api_key = OPENAI_API_KEY
            
            # Initialize Playwright
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            # Navigate to the URL
            page.goto(url)
            
            # Take a screenshot for reference
            screenshot_path = os.path.join("screenshots", f"openai_scrape_{int(time.time())}.png")
            page.screenshot(path=screenshot_path)
            
            # Get the page HTML
            html_content = page.content()
            
            # Save HTML content for reference
            with open(os.path.join("logs", f"openai_page_{int(time.time())}.html"), "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Use OpenAI to analyze the HTML and extract opportunity data
            prompt = f"""
            I'm scraping construction opportunities from AusTender website. Here's the HTML content of the search results page.
            Please extract all tender opportunities in a structured JSON format with the following fields:
            - title: The title of the opportunity
            - id: The ATM ID or reference number
            - agency: The agency or department issuing the tender
            - category: The category or type of the opportunity
            - date: The closing date of the opportunity
            - location: The location of the opportunity
            
            Only return valid JSON format, nothing else. If you can't extract any opportunities, return an empty array [].
            
            HTML Content (first 20000 characters):
            {html_content[:20000]}
            """
            
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": "You are a helpful assistant that extracts structured data from HTML."}, 
                          {"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=2000
            )
            
            # Parse the response
            try:
                opportunities_json = response.choices[0].message.content
                # Extract the JSON part if it's wrapped in code blocks
                if "```json" in opportunities_json:
                    opportunities_json = opportunities_json.split("```json")[1].split("```")[0].strip()
                elif "```" in opportunities_json:
                    opportunities_json = opportunities_json.split("```")[1].split("```")[0].strip()
                
                opportunities = json.loads(opportunities_json)
                
                # Get details if requested
                if get_details and opportunities:
                    for i, opp in enumerate(opportunities):
                        if 'id' in opp and opp['id']:
                            # Navigate to the details page
                            details_url = f"https://www.tenders.gov.au/Atm/Show/{opp['id']}"
                            page.goto(details_url)
                            page.wait_for_load_state("networkidle")
                            
                            # Get details HTML
                            details_html = page.content()
                            
                            # Use OpenAI to extract details
                            details_prompt = f"""
                            I'm extracting detailed information about a tender opportunity from AusTender website.
                            Please extract the following details in a structured JSON format:
                            - description: The full description of the opportunity
                            - published: The published date
                            - closing: The closing date and time
                            - contact: Contact person information (name, email, phone)
                            - attachments: List of attachments with name and type
                            
                            Only return valid JSON format, nothing else.
                            
                            HTML Content (first 20000 characters):
                            {details_html[:20000]}
                            """
                            
                            details_response = openai.chat.completions.create(
                                model="gpt-4",
                                messages=[{"role": "system", "content": "You are a helpful assistant that extracts structured data from HTML."}, 
                                          {"role": "user", "content": details_prompt}],
                                temperature=0.0,
                                max_tokens=1500
                            )
                            
                            try:
                                details_json = details_response.choices[0].message.content
                                # Extract the JSON part if it's wrapped in code blocks
                                if "```json" in details_json:
                                    details_json = details_json.split("```json")[1].split("```")[0].strip()
                                elif "```" in details_json:
                                    details_json = details_json.split("```")[1].split("```")[0].strip()
                                
                                details_data = json.loads(details_json)
                                opportunities[i].update(details_data)
                            except Exception as e:
                                logger.error(f"Error parsing details JSON for opportunity {opp['id']}: {str(e)}")
                            
                            time.sleep(1)  # Be nice to the server
                
                return opportunities
                
            except Exception as e:
                logger.error(f"Error parsing JSON from OpenAI: {str(e)}")
                return []
                
        except ImportError:
            logger.error("Failed to import required packages for OpenAI + Playwright")
            return []
        except Exception as e:
            logger.error(f"Error with OpenAI strategy: {str(e)}")
            return []
        finally:
            if 'page' in locals():
                page.close()
            if 'context' in locals():
                context.close()
            if 'browser' in locals():
                browser.close()
            if 'playwright' in locals():
                playwright.stop()
    
    def save_opportunities(self, filename: str = None) -> str:
        """
        Save scraped opportunities to a JSON file.
        
        Args:
            filename: Output filename (optional)
            
        Returns:
            Path to the saved file
        """
        if not self.opportunities:
            logger.warning("No opportunities to save")
            return ""
        
        if not filename:
            strategy_name = self.current_strategy or "integrated"
            filename = f"output/austender_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.opportunities, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.opportunities)} opportunities to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving opportunities: {str(e)}")
            return ""

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Scrape construction opportunities from Austender")
    parser.add_argument("--strategy", type=str, default="auto", 
                       choices=["auto", "browser_use", "playwright", "firecrawl", "openai"],
                       help="Strategy to use for scraping")
    parser.add_argument("--pages", type=int, default=1, help="Maximum number of pages to scrape")
    parser.add_argument("--details", action="store_true", help="Fetch detailed information for each opportunity")
    parser.add_argument("--save", action="store_true", help="Save opportunities to a JSON file")
    parser.add_argument("--output", type=str, help="Output filename")
    parser.add_argument("--url", type=str, default=AUSTENDER_URL, help="URL to scrape")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    scraper = IntegratedScraper()
    
    try:
        # Scrape opportunities
        opportunities = scraper.scrape(
            strategy=args.strategy,
            url=args.url,
            max_pages=args.pages,
            get_details=args.details
        )
        
        if not opportunities:
            logger.warning("No opportunities found")
            return
        
        # Save opportunities if requested
        if args.save:
            filename = args.output if args.output else None
            scraper.save_opportunities(filename)
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    main()
