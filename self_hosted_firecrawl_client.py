#!/usr/bin/env python
"""
Self-Hosted Firecrawl Client

This script provides a robust client for interacting with our self-hosted Firecrawl
instance to extract construction opportunities from government tender websites
that implement sophisticated anti-bot measures.

Usage:
    python self_hosted_firecrawl_client.py scrape --site austender --category construction
"""

import os
import sys
import json
import time
import logging
import argparse
import datetime
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/firecrawl_client.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("firecrawl_client")

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import database modules - provide helpful error if not available
try:
    from opportunity_finder import OpportunityDatabase
except ImportError as e:
    logger.error(f"Failed to import project modules: {str(e)}")
    print(f"Import Error: {str(e)}")
    print("Make sure opportunity_finder.py is in the current directory.")

# Firecrawl API settings
FIRECRAWL_BASE_URL = os.getenv("FIRECRAWL_BASE_URL", "http://localhost:3005")
FIRECRAWL_API_VERSION = os.getenv("FIRECRAWL_API_VERSION", "v1")
API_KEY = os.getenv("FIRECRAWL_API_KEY", __import__('os').environ['FIRECRAWL_API_KEY'])


class FirecrawlClient:
    """Client for interacting with self-hosted Firecrawl instance."""
    
    def __init__(self, base_url: str = FIRECRAWL_BASE_URL, api_key: str = API_KEY, api_version: str = FIRECRAWL_API_VERSION):
        """
        Initialize the Firecrawl client.
        
        Args:
            base_url: URL of the Firecrawl API
            api_key: API key for authentication
            api_version: API version to use (e.g., v1)
        """
        self.base_url = base_url
        self.api_key = api_key
        self.api_version = api_version
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if api_key:
            self.headers["X-API-Key"] = api_key
            
        # Add opportunity database for storing results
        self.opportunity_db = OpportunityDatabase()
        
        # Setup tender site configurations
        self.sites = {
            "austender": {
                "base_url": "https://www.tenders.gov.au",
                "search_url": "https://www.tenders.gov.au/Search/KeywordSearch",
                "search_params": {
                    "keyword": "construction",
                    "type": "ATM",
                    "dateType": "ClosingDate"
                },
                "selectors": {
                    "opportunity_list": ".search-results .opportunity-item",
                    "opportunity_title": "h3 a",
                    "opportunity_link": "h3 a",
                    "opportunity_id": ".opportunity-id",
                    "opportunity_dates": ".dates",
                    "opportunity_location": ".location",
                    "opportunity_value": ".value",
                    "next_page": ".pagination .next"
                }
            },
            "nsw_etender": {
                "base_url": "https://www.tenders.nsw.gov.au",
                "search_url": "https://www.tenders.nsw.gov.au/nsw/?event=public.advancedsearch.keyword",
                "search_params": {
                    "keyword": "construction",
                    "type": "Current"
                },
                "selectors": {
                    "opportunity_list": "table.tenders tr:not(:first-child)",
                    "opportunity_title": "td:nth-child(2) a",
                    "opportunity_link": "td:nth-child(2) a",
                    "opportunity_id": "td:nth-child(1)",
                    "opportunity_dates": "td:nth-child(4)",
                    "opportunity_location": "td:nth-child(3)",
                    "opportunity_value": "td:nth-child(5)",
                    "next_page": "a:contains('Next')"
                }
            }
        }
    
    def check_service_health(self) -> bool:
        """
        Check if the Firecrawl service is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # First try the base endpoint
            response = requests.get(self.base_url, timeout=5)
            
            if response.status_code == 200:
                logger.info("Firecrawl service is responding")
                return True
                
            # If that fails, try a simple scrape with the v1 API
            scrape_url = f"{self.base_url}/{self.api_version}/scrape"
            test_payload = {
                "url": "https://example.com"
            }
            response = requests.post(scrape_url, headers=self.headers, json=test_payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Firecrawl service is responding to scrape requests")
                return True
            
            logger.error(f"Firecrawl service is not healthy: {response.status_code}")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Firecrawl service: {str(e)}")
            return False
    
    def scrape_url(self, url: str, wait_for_selector: str = None) -> Dict[str, Any]:
        """
        Scrape a URL using Firecrawl.
        
        Args:
            url: URL to scrape
            wait_for_selector: CSS selector to wait for before scraping
            
        Returns:
            Scraped content and metadata
        """
        logger.info(f"Scraping {url}")
        
        # Use the v1 API endpoint
        endpoint = f"{self.base_url}/{self.api_version}/scrape"
        
        payload = {
            "url": url
        }
        
        # Add scraping options if needed
        if wait_for_selector:
            payload["options"] = {
                "waitForSelector": wait_for_selector,
                "timeout": 30000
            }
        
        # Add user agent rotation
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36 Edg/91.0.864.71"
        ]
        
        import random
        payload["options"]["userAgent"] = random.choice(user_agents)
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success') and 'data' in result:
                if 'html' in result['data']:
                    logger.info(f"Successfully scraped {url} ({len(result['data']['html'])} bytes)")
                else:
                    logger.info(f"Successfully scraped {url}")
                    
                return result
            else:
                logger.warning(f"Scraped {url} but no success/data in response")
                logger.debug(f"Response content: {result}")
                return {"success": False, "error": "No success or data in response", "original_response": result}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def extract_from_html(self, html: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract data from HTML content using Firecrawl.
        
        Args:
            html: HTML content
            selectors: Dictionary of selectors to extract
            
        Returns:
            Extracted data
        """
        logger.info("Extracting data from HTML content")
        
        endpoint = f"{self.base_url}/{self.api_version}/extract"
        
        # For v1 API, we need to use a simplified extraction model
        # This approach uses a selector-based extraction
        selectors_list = []
        
        for key, selector in selectors.items():
            # Convert our selectors to the v1 API format
            is_list = "list" in key.lower()
            
            selector_item = {
                "name": key,
                "selector": selector,
                "multiple": is_list,
                "attributes": [
                    {"name": "text", "property": "innerText"},
                    {"name": "href", "property": "href"}
                ]
            }
            
            selectors_list.append(selector_item)
        
        payload = {
            "html": html,
            "selectors": selectors_list
        }
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Successfully extracted data from HTML content")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error extracting data from HTML: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def scrape_opportunities(self, site: str, category: str = "construction", max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape opportunities from a specified government tender site.
        
        Args:
            site: Site key (e.g., 'austender', 'nsw_etender')
            category: Category to search for
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of opportunities
        """
        if site not in self.sites:
            logger.error(f"Unknown site: {site}")
            return []
        
        site_config = self.sites[site]
        opportunities = []
        
        # Build the search URL with parameters
        search_url = site_config["search_url"]
        params = site_config["search_params"].copy()
        
        # Replace default keyword with category if different
        if category != "construction":
            params["keyword"] = category
        
        # Convert params to query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        if "?" in search_url:
            search_url = f"{search_url}&{query_string}"
        else:
            search_url = f"{search_url}?{query_string}"
        
        logger.info(f"Starting search at: {search_url}")
        
        # Start with the initial search page
        current_url = search_url
        
        for page_num in range(1, max_pages + 1):
            logger.info(f"Scraping page {page_num} from {site}")
            
            # Scrape the current page
            result = self.scrape_url(
                url=current_url,
                wait_for_selector=site_config["selectors"]["opportunity_list"]
            )
            
            if not result or "html" not in result:
                logger.warning(f"Failed to get HTML content from {current_url}")
                break
            
            # Extract opportunities from the page
            if not result.get('success') or 'data' not in result:
                logger.warning(f"No data in result from {current_url}")
                break
            
            # Check for HTML content in the response
            if 'html' not in result['data']:
                logger.warning(f"No HTML content in data from {current_url}")
                break
                
            html_content = result['data']['html']
            
            # Use the extract endpoint to get opportunities data
            extracted = self.extract_from_html(
                html=html_content,
                selectors=site_config["selectors"]
            )
            
            if not extracted or "opportunity_list" not in extracted:
                logger.warning(f"Failed to extract opportunities from page {page_num}")
                break
            
            # Process the extracted opportunities
            page_opportunities = self._process_opportunity_list(extracted, site_config, site)
            
            if not page_opportunities:
                logger.info(f"No opportunities found on page {page_num}")
                break
            
            logger.info(f"Found {len(page_opportunities)} opportunities on page {page_num}")
            opportunities.extend(page_opportunities)
            
            # Check if there's a next page
            # With the new API structure, we need to check in the data property
            if isinstance(extracted, dict) and extracted.get('success', False) and 'data' in extracted:
                extracted_data = extracted['data']
            else:
                extracted_data = extracted
                
            if "next_page" in extracted_data and extracted_data["next_page"]:
                next_data = extracted_data["next_page"]
                next_url = None
                
                # Handle both direct href and object structure
                if isinstance(next_data, str):
                    next_url = next_data
                elif isinstance(next_data, dict) and "href" in next_data:
                    next_url = next_data.get("href")
                elif isinstance(next_data, list) and len(next_data) > 0:
                    if isinstance(next_data[0], dict) and "href" in next_data[0]:
                        next_url = next_data[0].get("href")
                        
                if next_url:
                    # Make the URL absolute if it's relative
                    if next_url.startswith("/"):
                        next_url = f"{site_config['base_url']}{next_url}"
                    
                    current_url = next_url
                    logger.info(f"Moving to next page: {current_url}")
                    
                    # Add a delay between pages
                    time.sleep(5)
                else:
                    logger.info("No valid next page URL found")
                    break
            else:
                logger.info("No next page found")
                break
        
        logger.info(f"Finished scraping {site}, found {len(opportunities)} opportunities")
        return opportunities
    
    def _process_opportunity_list(self, extracted: Dict[str, Any], site_config: Dict[str, Any], site: str) -> List[Dict[str, Any]]:
        """
        Process the list of extracted opportunities.
        
        Args:
            extracted: Extracted data
            site_config: Site configuration
            site: Site key
            
        Returns:
            List of processed opportunities
        """
        opportunities = []
        
        if "opportunity_list" not in extracted or not extracted["opportunity_list"]:
            return opportunities
        
        for item in extracted["opportunity_list"]:
            try:
                # Extract basic details
                opportunity = {
                    "title": item.get("text", "").strip(),
                    "url": item.get("href", ""),
                    "source": site,
                    "scrape_date": datetime.date.today().isoformat()
                }
                
                # Make URL absolute if it's relative
                if opportunity["url"] and opportunity["url"].startswith("/"):
                    opportunity["url"] = f"{site_config['base_url']}{opportunity['url']}"
                
                # Only add valid opportunities
                if opportunity["title"] and opportunity["url"]:
                    opportunities.append(opportunity)
            except Exception as e:
                logger.warning(f"Error processing opportunity item: {str(e)}")
                continue
        
        return opportunities
    
    def get_opportunity_details(self, url: str, site: str) -> Dict[str, Any]:
        """
        Get detailed information about an opportunity.
        
        Args:
            url: URL of the opportunity detail page
            site: Site key
            
        Returns:
            Dictionary with opportunity details
        """
        logger.info(f"Getting details for opportunity at {url}")
        
        # Base opportunity with the URL and source
        opportunity = {
            "url": url,
            "source": site,
            "scrape_date": datetime.date.today().isoformat()
        }
        
        # Scrape the detail page
        result = self.scrape_url(
            url=url,
            method="playwright",
            wait_for_selector="body"
        )
        
        if not result or "html" not in result:
            logger.warning(f"Failed to get HTML content from {url}")
            return opportunity
        
        html_content = result["html"]
        
        # Create site-specific selectors for the detail page
        detail_selectors = {
            "title": "h1, .opportunity-title, .tender-title",
            "reference_id": ".atm-id, .opportunity-id, [data-test='reference-id']",
            "description": ".description, .opportunity-description, [data-test='description']",
            "publish_date": ".publish-date, [data-test='publish-date']",
            "closing_date": ".closing-date, [data-test='closing-date']",
            "location": ".location, [data-test='location']",
            "category": ".category, [data-test='category']",
            "value": ".value, .estimated-value, [data-test='value']",
            "contact_name": ".contact-name, [data-test='contact-name']",
            "contact_email": ".contact-email, [data-test='contact-email']",
            "contact_phone": ".contact-phone, [data-test='contact-phone']",
            "attachment_list": ".attachment, .document-item, [data-test='attachment']"
        }
        
        # Extract details from the page
        extract_result = self.extract_from_html(
            html=html_content,
            selectors=detail_selectors
        )
        
        # Handle the v1 API response format
        if isinstance(extract_result, dict) and extract_result.get('success') and 'data' in extract_result:
            extracted = extract_result['data']
        else:
            extracted = extract_result
            
        if not extracted:
            logger.warning(f"Failed to extract details from {url}")
            return opportunity
        
        # Process the extracted details
        if isinstance(extracted, dict) and extracted.get('success') and 'data' in extracted:
            extracted_data = extracted['data']
        else:
            extracted_data = extracted
            
        for key, value in extracted_data.items():
            if key == "attachment_list":
                # Process attachments separately
                continue
                
            if value and isinstance(value, dict) and "text" in value:
                text_value = value["text"].strip()
                if text_value:
                    # Handle specific fields differently
                    if key == "publish_date" or key == "closing_date":
                        date_value = self._parse_date(text_value)
                        if date_value:
                            opportunity[key] = date_value
                    elif key == "value":
                        value_amount = self._parse_value(text_value)
                        if value_amount is not None:
                            opportunity["capital_value"] = value_amount
                    else:
                        opportunity[key] = text_value
        
        # Process attachments if present
        if "attachment_list" in extracted and extracted["attachment_list"]:
            attachments = []
            
            for item in extracted["attachment_list"]:
                if "text" in item and "href" in item:
                    name = item["text"].strip()
                    url = item["href"]
                    
                    if name and url:
                        # Make URL absolute if it's relative
                        if url.startswith("/"):
                            if site in self.sites:
                                url = f"{self.sites[site]['base_url']}{url}"
                        
                        attachments.append({
                            "name": name,
                            "url": url,
                            "upload_date": datetime.date.today().isoformat()
                        })
            
            if attachments:
                opportunity["attachments"] = attachments
        
        logger.info(f"Successfully extracted details for opportunity: {opportunity.get('title', url)}")
        return opportunity
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse a date string into an ISO format date string.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            ISO format date string or None if parsing fails
        """
        if not date_str:
            return None
        
        # Clean up the string
        date_str = date_str.strip()
        
        # Handle cases where the field name might be in the string
        if ":" in date_str:
            date_str = date_str.split(":", 1)[1].strip()
        
        # Remove timezone information
        date_str = date_str.split(" AEST")[0].split(" AEDT")[0].strip()
        
        # Try different date formats
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d %b %Y",
            "%d %B %Y",
            "%B %d, %Y",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                date_obj = datetime.datetime.strptime(date_str, fmt).date()
                return date_obj.isoformat()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _parse_value(self, value_str: str) -> Optional[float]:
        """
        Parse a monetary value string into a float.
        
        Args:
            value_str: Value string to parse
            
        Returns:
            Parsed value or None if parsing fails
        """
        if not value_str:
            return None
        
        # Clean up the string
        value_str = value_str.strip().lower()
        
        # Handle cases where the field name might be in the string
        if ":" in value_str:
            value_str = value_str.split(":", 1)[1].strip()
        
        # Handle 'not disclosed' or similar
        if "not disclosed" in value_str or "not available" in value_str or "n/a" in value_str:
            return None
        
        # Remove currency symbols and commas
        value_str = value_str.replace("$", "").replace(",", "").strip()
        
        # Handle ranges
        if "-" in value_str:
            parts = value_str.split("-")
            if len(parts) == 2:
                try:
                    # Extract numbers
                    import re
                    first_match = re.search(r"[\d.]+", parts[0].strip())
                    second_match = re.search(r"[\d.]+", parts[1].strip())
                    
                    if first_match and second_match:
                        first = float(first_match.group(0))
                        second = float(second_match.group(0))
                        return (first + second) / 2  # Return the average
                except (ValueError, AttributeError):
                    pass
        
        # Handle currency codes
        value_parts = value_str.split()
        if value_parts:
            try:
                # Take the first part that looks like a number
                for part in value_parts:
                    if part and part[0].isdigit():
                        return float(part)
            except ValueError:
                pass
        
        logger.warning(f"Could not parse value: {value_str}")
        return None
    
    def save_opportunities(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        Save opportunities to the database.
        
        Args:
            opportunities: List of opportunities to save
        """
        if not opportunities:
            logger.info("No opportunities to save")
            return
        
        logger.info(f"Saving {len(opportunities)} opportunities to the database")
        
        for opportunity in opportunities:
            opportunity_id = self.opportunity_db.add_opportunity(opportunity)
            if opportunity_id > 0:
                logger.debug(f"Saved opportunity with ID {opportunity_id}: {opportunity.get('title', 'Unknown')}")
            else:
                logger.warning(f"Failed to save opportunity: {opportunity.get('title', 'Unknown')}")
        
        logger.info("Finished saving opportunities to database")


def scrape_site(args):
    """Scrape opportunities from a site."""
    client = FirecrawlClient()
    
    # Check if the Firecrawl service is healthy
    if not client.check_service_health():
        logger.error("Firecrawl service is not healthy. Please check the service status.")
        sys.exit(1)
    
    # Scrape opportunities
    opportunities = client.scrape_opportunities(
        site=args.site,
        category=args.category,
        max_pages=args.pages
    )
    
    if not opportunities:
        logger.warning("No opportunities found.")
        return
    
    logger.info(f"Found {len(opportunities)} opportunities.")
    
    # Print summary
    for i, opp in enumerate(opportunities, 1):
        print(f"\n{'-'*80}")
        print(f"Opportunity {i}/{len(opportunities)}:")
        print(f"{'-'*80}")
        print(f"Title:     {opp.get('title', 'Unknown')}")
        print(f"URL:       {opp.get('url', 'Unknown')}")
        print(f"Source:    {opp.get('source', 'Unknown')}")
    
    # Get details if requested
    if args.details:
        detailed_opportunities = []
        
        for i, opp in enumerate(opportunities, 1):
            logger.info(f"Getting details for opportunity {i}/{len(opportunities)}")
            
            if "url" in opp and opp["url"]:
                details = client.get_opportunity_details(opp["url"], opp["source"])
                detailed_opportunities.append(details)
                
                # Print a brief summary
                print(f"\nDetails for opportunity {i}:")
                print(f"Title:        {details.get('title', 'Unknown')}")
                print(f"Reference ID: {details.get('reference_id', 'Unknown')}")
                print(f"Location:     {details.get('location', 'Unknown')}")
                
                # Be nice to the server
                time.sleep(3)
        
        opportunities = detailed_opportunities
    
    # Save to database if requested
    if args.save:
        client.save_opportunities(opportunities)
        logger.info(f"Saved {len(opportunities)} opportunities to the database")


def main():
    """Main function to parse arguments and run the client."""
    parser = argparse.ArgumentParser(description="Self-Hosted Firecrawl Client")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape opportunities from a site")
    scrape_parser.add_argument("--site", choices=["austender", "nsw_etender"], required=True, help="Site to scrape")
    scrape_parser.add_argument("--category", default="construction", help="Category to search for")
    scrape_parser.add_argument("--pages", type=int, default=3, help="Maximum number of pages to scrape")
    scrape_parser.add_argument("--details", action="store_true", help="Get detailed information for each opportunity")
    scrape_parser.add_argument("--save", action="store_true", default=True, help="Save opportunities to the database")
    scrape_parser.set_defaults(func=scrape_site)
    
    # Health check command
    health_parser = subparsers.add_parser("health", help="Check if the Firecrawl service is healthy")
    health_parser.set_defaults(func=lambda args: FirecrawlClient().check_service_health())
    
    args = parser.parse_args()
    
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
