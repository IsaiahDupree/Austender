#!/usr/bin/env python
"""
Firecrawl Integration for Austender Opportunities

This script leverages Firecrawl's advanced web scraping capabilities to extract
construction opportunities from government tender websites that implement sophisticated
anti-bot measures.

Usage:
    python firecrawl_scraper.py --site austender --category construction --pages 3

Requirements:
    - Running Firecrawl instance (via Docker)
    - requests library for API calls
"""

import os
import sys
import argparse
import json
import logging
import datetime
import time
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import project modules
try:
    from opportunity_finder import OpportunityDatabase
except ImportError as e:
    print(f"Failed to import project modules: {str(e)}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/firecrawl_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("firecrawl_scraper")

# Firecrawl API settings
FIRECRAWL_URL = os.getenv("FIRECRAWL_URL", "http://localhost:3002/v1")


class FirecrawlScraper:
    """Integration with Firecrawl for advanced web scraping."""
    
    def __init__(self, api_url: str = FIRECRAWL_URL):
        """
        Initialize the Firecrawl scraper.
        
        Args:
            api_url: URL of the Firecrawl API
        """
        self.api_url = api_url
        self.opportunity_db = OpportunityDatabase()
        self.sites = {
            "austender": {
                "url": "https://www.tenders.gov.au",
                "search_url": "https://www.tenders.gov.au/search/search-advanced.aspx",
                "pattern": {
                    "opportunities": ".opportunity-item, .search-result",
                    "opportunity_links": "a[href*='/cn/']",
                    "next_page": ".pagination a.next, .pagination-next"
                }
            },
            "nsw_etender": {
                "url": "https://www.tenders.nsw.gov.au",
                "search_url": "https://www.tenders.nsw.gov.au/nsw/?event=public.advancedsearch.list",
                "pattern": {
                    "opportunities": ".opportunity-list .opportunity, .opportunityTable tr",
                    "opportunity_links": "a[href*='tender']",
                    "next_page": ".pagination a:contains('Next')"
                }
            },
            # Add more sites as needed
        }
    
    def scrape_opportunities(self, site: str, category: str = "construction", max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape opportunities from a specified site using Firecrawl.
        
        Args:
            site: Site key (e.g. 'austender', 'nsw_etender')
            category: Category to search for
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of opportunity dictionaries
        """
        if site not in self.sites:
            logger.error(f"Unknown site: {site}")
            return []
        
        site_config = self.sites[site]
        opportunities = []
        current_url = site_config["search_url"]
        
        # Add category parameter to URL
        if "?" in current_url:
            current_url += f"&category={category}"
        else:
            current_url += f"?category={category}"
        
        for page_num in range(1, max_pages + 1):
            logger.info(f"Scraping page {page_num} from {site}")
            
            # Adjust URL for pagination if needed
            if page_num > 1:
                if "page=" in current_url:
                    current_url = current_url.replace(f"page={page_num-1}", f"page={page_num}")
                else:
                    if "?" in current_url:
                        current_url += f"&page={page_num}"
                    else:
                        current_url += f"?page={page_num}"
            
            try:
                # Use Firecrawl's Playwright method for better anti-bot evasion
                response = self._scrape_with_firecrawl(current_url, method="playwright")
                
                if not response or "html" not in response:
                    logger.warning(f"No HTML content returned for {current_url}")
                    break
                
                # Parse opportunities from the page
                html_content = response["html"]
                page_opportunities = self._extract_opportunities(html_content, site_config, site)
                
                if not page_opportunities:
                    logger.info(f"No opportunities found on page {page_num}")
                    break
                
                logger.info(f"Found {len(page_opportunities)} opportunities on page {page_num}")
                opportunities.extend(page_opportunities)
                
                # Get next page URL
                next_page_url = self._extract_next_page_url(html_content, site_config)
                if next_page_url:
                    current_url = next_page_url
                else:
                    logger.info("No next page found")
                    break
                
                # Add a delay between pages to be nice to the server
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {str(e)}")
                break
        
        logger.info(f"Finished scraping {site}, found {len(opportunities)} opportunities")
        return opportunities
    
    def get_opportunity_details(self, url: str, source: str) -> Dict[str, Any]:
        """
        Get detailed information about an opportunity.
        
        Args:
            url: URL of the opportunity detail page
            source: Source site (e.g. 'austender', 'nsw_etender')
            
        Returns:
            Dictionary with opportunity details
        """
        logger.info(f"Getting details for opportunity at {url}")
        
        try:
            # Use Firecrawl's Playwright method for better anti-bot evasion
            response = self._scrape_with_firecrawl(url, method="playwright")
            
            if not response or "html" not in response:
                logger.warning(f"No HTML content returned for {url}")
                return {"url": url, "source": source}
            
            # Parse opportunity details based on the source
            html_content = response["html"]
            
            if source == "austender":
                return self._parse_austender_details(html_content, url)
            elif source == "nsw_etender":
                return self._parse_nsw_etender_details(html_content, url)
            else:
                logger.warning(f"No parser available for source: {source}")
                return {"url": url, "source": source}
                
        except Exception as e:
            logger.error(f"Error getting opportunity details: {str(e)}")
            return {"url": url, "source": source}
    
    def _scrape_with_firecrawl(self, url: str, method: str = "playwright") -> Dict[str, Any]:
        """
        Use Firecrawl to scrape a URL.
        
        Args:
            url: URL to scrape
            method: Scraping method ('fetch', 'playwright', 'fetch-with-js')
            
        Returns:
            Firecrawl API response
        """
        logger.info(f"Scraping {url} with method: {method}")
        
        endpoint = f"{self.api_url}/crawl"
        payload = {
            "url": url,
            "method": method,
            "options": {
                "wait_for": {
                    "type": "selector",
                    "selector": "body",
                    "timeout": 30000
                },
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
            }
        }
        
        try:
            response = requests.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {}
    
    def _extract_opportunities(self, html: str, site_config: Dict[str, Any], source: str) -> List[Dict[str, Any]]:
        """
        Extract opportunities from HTML content.
        
        Args:
            html: HTML content
            site_config: Configuration for the site
            source: Source site name
            
        Returns:
            List of opportunity dictionaries
        """
        # Use Firecrawl's extract API to parse HTML
        extract_endpoint = f"{self.api_url}/extract"
        payload = {
            "html": html,
            "extract": {
                "opportunities": {
                    "selector": site_config["pattern"]["opportunities"],
                    "multiple": True,
                    "properties": {
                        "title": {
                            "selector": "h2, h3, .title, a",
                            "type": "text"
                        },
                        "url": {
                            "selector": "a",
                            "type": "attribute",
                            "attribute": "href"
                        }
                    }
                }
            }
        }
        
        try:
            response = requests.post(extract_endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if "opportunities" not in result or not result["opportunities"]:
                return []
            
            opportunities = []
            base_url = site_config["url"]
            
            for opp in result["opportunities"]:
                title = opp.get("title", "").strip()
                url = opp.get("url", "").strip()
                
                if title and url:
                    # Make URL absolute if it's relative
                    if url.startswith("/"):
                        url = f"{base_url}{url}"
                    
                    opportunities.append({
                        "title": title,
                        "url": url,
                        "source": source,
                        "scrape_date": datetime.date.today()
                    })
            
            return opportunities
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error extracting opportunities: {str(e)}")
            return []
    
    def _extract_next_page_url(self, html: str, site_config: Dict[str, Any]) -> Optional[str]:
        """
        Extract the URL of the next page from HTML content.
        
        Args:
            html: HTML content
            site_config: Configuration for the site
            
        Returns:
            URL of the next page or None if not found
        """
        extract_endpoint = f"{self.api_url}/extract"
        payload = {
            "html": html,
            "extract": {
                "next_page": {
                    "selector": site_config["pattern"]["next_page"],
                    "properties": {
                        "url": {
                            "type": "attribute",
                            "attribute": "href"
                        }
                    }
                }
            }
        }
        
        try:
            response = requests.post(extract_endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if "next_page" not in result or not result["next_page"] or "url" not in result["next_page"]:
                return None
            
            next_url = result["next_page"]["url"]
            
            # Make URL absolute if it's relative
            if next_url.startswith("/"):
                next_url = f"{site_config['url']}{next_url}"
            
            return next_url
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error extracting next page URL: {str(e)}")
            return None
    
    def _parse_austender_details(self, html: str, url: str) -> Dict[str, Any]:
        """
        Parse opportunity details from Austender HTML.
        
        Args:
            html: HTML content
            url: URL of the opportunity
            
        Returns:
            Dictionary with opportunity details
        """
        extract_endpoint = f"{self.api_url}/extract"
        payload = {
            "html": html,
            "extract": {
                "details": {
                    "properties": {
                        "title": {
                            "selector": "h1.opportunity-title, .tender-title h1, h1",
                            "type": "text"
                        },
                        "reference_id": {
                            "selector": ".atm-id, .cn-id, .reference-id",
                            "type": "text"
                        },
                        "publish_date": {
                            "selector": ".publish-date, .published-date, span:contains('Published:')",
                            "type": "text"
                        },
                        "closing_date": {
                            "selector": ".closing-date, .close-date, span:contains('Closing:')",
                            "type": "text"
                        },
                        "location": {
                            "selector": ".location, span:contains('Location:')",
                            "type": "text"
                        },
                        "capital_value": {
                            "selector": ".estimated-value, .value, span:contains('Value:')",
                            "type": "text"
                        },
                        "category": {
                            "selector": ".category, span:contains('Category:')",
                            "type": "text"
                        },
                        "description": {
                            "selector": ".opportunity-description, .description",
                            "type": "text"
                        }
                    }
                },
                "contact": {
                    "properties": {
                        "name": {
                            "selector": ".contact-name, span:contains('Contact:')",
                            "type": "text"
                        },
                        "email": {
                            "selector": ".contact-email, a[href^='mailto:']",
                            "type": "text"
                        },
                        "phone": {
                            "selector": ".contact-phone, span:contains('Phone:')",
                            "type": "text"
                        }
                    }
                },
                "attachments": {
                    "selector": ".attachment, .document-item",
                    "multiple": True,
                    "properties": {
                        "name": {
                            "selector": ".name, a",
                            "type": "text"
                        },
                        "url": {
                            "selector": "a",
                            "type": "attribute",
                            "attribute": "href"
                        },
                        "description": {
                            "selector": ".description, .document-description",
                            "type": "text"
                        }
                    }
                }
            }
        }
        
        try:
            response = requests.post(extract_endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Initialize with base details
            opportunity = {
                "url": url,
                "source": "austender",
                "scrape_date": datetime.date.today()
            }
            
            # Extract main details
            if "details" in result and result["details"]:
                for key, value in result["details"].items():
                    if value:
                        if key == "publish_date" or key == "closing_date":
                            # Try to parse date
                            parsed_date = self._parse_date(value)
                            if parsed_date:
                                opportunity[key] = parsed_date
                        elif key == "capital_value":
                            # Try to parse value
                            parsed_value = self._parse_value(value)
                            if parsed_value:
                                opportunity[key] = parsed_value
                        else:
                            opportunity[key] = value.strip()
            
            # Extract contact details
            if "contact" in result and result["contact"]:
                opportunity["contact_name"] = result["contact"].get("name", "").strip()
                opportunity["contact_email"] = result["contact"].get("email", "").strip()
                opportunity["contact_phone"] = result["contact"].get("phone", "").strip()
            
            # Extract attachments
            if "attachments" in result and result["attachments"]:
                attachments = []
                for attachment in result["attachments"]:
                    name = attachment.get("name", "").strip()
                    url = attachment.get("url", "").strip()
                    
                    if name and url:
                        # Make URL absolute if it's relative
                        if url.startswith("/"):
                            url = f"https://www.tenders.gov.au{url}"
                        
                        attachments.append({
                            "name": name,
                            "url": url,
                            "description": attachment.get("description", "").strip(),
                            "upload_date": datetime.date.today()
                        })
                
                opportunity["attachments"] = attachments
            
            return opportunity
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error parsing opportunity details: {str(e)}")
            return {"url": url, "source": "austender"}
    
    def _parse_nsw_etender_details(self, html: str, url: str) -> Dict[str, Any]:
        """
        Parse opportunity details from NSW eTender HTML.
        
        Args:
            html: HTML content
            url: URL of the opportunity
            
        Returns:
            Dictionary with opportunity details
        """
        # Similar to _parse_austender_details but with different selectors
        # Implement based on NSW eTender website structure
        return {"url": url, "source": "nsw_etender"}
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """
        Parse a date string into a datetime.date object.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Parsed date or None if parsing fails
        """
        if not date_str:
            return None
        
        # Extract date part (remove labels and extra content)
        date_str = date_str.split(":", 1)[-1].strip()
        date_str = date_str.split("AEST")[0].split("AEDT")[0].strip()
        
        formats = [
            "%d/%m/%Y",
            "%d/%m/%Y %H:%M %p",
            "%d/%m/%Y %H:%M:%S",
            "%d %b %Y",
            "%d %B %Y",
            "%B %d, %Y",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.datetime.strptime(date_str, fmt).date()
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
        if not value_str or "not disclosed" in value_str.lower():
            return None
        
        # Extract value part (remove labels)
        value_str = value_str.split(":", 1)[-1].strip()
        
        # Remove currency symbols and commas
        value_str = value_str.replace("$", "").replace(",", "").strip()
        
        # Handle ranges (e.g., "5,000,000 - 8,000,000")
        if "-" in value_str:
            parts = value_str.split("-")
            if len(parts) == 2:
                try:
                    # Extract numbers from strings
                    import re
                    first = float(re.search(r"[\d.]+", parts[0].strip()).group(0))
                    second = float(re.search(r"[\d.]+", parts[1].strip()).group(0))
                    return (first + second) / 2  # Return the average
                except (ValueError, AttributeError):
                    pass
        
        # Handle "AUD" or other currency codes
        value_str = value_str.split(" ")[0].strip()
        
        try:
            return float(value_str)
        except ValueError:
            logger.warning(f"Could not parse value: {value_str}")
            return None
    
    def save_opportunities(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        Save opportunities to the database.
        
        Args:
            opportunities: List of opportunity dictionaries
        """
        if not opportunities:
            logger.info("No opportunities to save")
            return
        
        logger.info(f"Saving {len(opportunities)} opportunities to the database")
        
        for opportunity in opportunities:
            self.opportunity_db.add_opportunity(opportunity)
        
        logger.info("Finished saving opportunities")


def scrape_site(args):
    """Scrape opportunities from a site."""
    scraper = FirecrawlScraper()
    
    try:
        # Scrape opportunities
        opportunities = scraper.scrape_opportunities(
            site=args.site,
            category=args.category,
            max_pages=args.pages
        )
        
        if not opportunities:
            print("No opportunities found.")
            return
        
        print(f"\nFound {len(opportunities)} opportunities from {args.site}.")
        
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
                print(f"\nFetching details for opportunity {i}/{len(opportunities)}")
                details = scraper.get_opportunity_details(opp["url"], opp["source"])
                detailed_opportunities.append({**opp, **details})
                
                # Print some info
                print(f"Title:     {details.get('title', 'Unknown')}")
                print(f"Reference: {details.get('reference_id', 'Unknown')}")
                
                # Be nice to the server
                time.sleep(3)
            
            opportunities = detailed_opportunities
        
        # Save to database if requested
        if args.save:
            scraper.save_opportunities(opportunities)
            print(f"\nSaved {len(opportunities)} opportunities to the database")
        
    except Exception as e:
        logger.error(f"Error scraping {args.site}: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main function to parse arguments and run the scraper."""
    parser = argparse.ArgumentParser(description="Firecrawl Scraper for Construction Opportunities")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Scrape site
    scrape_parser = subparsers.add_parser("scrape", help="Scrape opportunities from a site")
    scrape_parser.add_argument("--site", required=True, help="Site to scrape (austender, nsw_etender)")
    scrape_parser.add_argument("--category", default="construction", help="Category to search for")
    scrape_parser.add_argument("--pages", type=int, default=3, help="Maximum number of pages to scrape")
    scrape_parser.add_argument("--details", action="store_true", help="Get detailed information for each opportunity")
    scrape_parser.add_argument("--save", action="store_true", help="Save opportunities to the database")
    scrape_parser.set_defaults(func=scrape_site)
    
    args = parser.parse_args()
    
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
