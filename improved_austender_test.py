#!/usr/bin/env python
"""
Improved testing script for the Austender scraper with enhanced error handling.

This script provides a more robust way to test the Austender scraper by:
1. Adding detailed error handling
2. Including retry logic for transient issues
3. Providing more diagnostic information
4. Supporting mock data for testing in case of website issues

Usage:
    python improved_austender_test.py [--mock] [--debug] [--limit N]

Options:
    --mock      Use mock data instead of live website
    --debug     Show detailed debug information
    --limit N   Limit the number of opportunities to fetch (default: 3)
"""

import os
import sys
import argparse
import json
import datetime
import time
import logging
import traceback
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("improved_austender_test")

# Try to import the scraper - handle import errors gracefully
try:
    from scrapers.austender_scraper import AustenderScraper
    from config.config import AUSTENDER_URL, USER_AGENT
except ImportError as e:
    logger.error(f"Error importing required modules: {str(e)}")
    print(f"Import Error: {str(e)}")
    print("Please make sure all required modules are installed and in the correct paths.")
    sys.exit(1)


def create_mock_data() -> List[Dict[str, Any]]:
    """
    Create mock opportunity data for testing when the website is unavailable.
    
    Returns:
        List of mock opportunity dictionaries
    """
    current_date = datetime.date.today()
    closing_date = current_date + datetime.timedelta(days=30)
    
    return [
        {
            "title": "Construction of Government Office Building",
            "reference_id": "MOCK-2025-001",
            "url": f"{AUSTENDER_URL}/cn/detail.aspx?id=MOCK-2025-001",
            "publish_date": current_date,
            "closing_date": closing_date,
            "capital_value": 5000000.0,
            "capital_value_currency": "AUD",
            "location": "Sydney",
            "source": "Austender",
            "description": "Construction of a new 10-story government office building in Sydney CBD with sustainable features and modern facilities.",
            "category": "Construction",
            "subcategory": "Commercial Buildings",
            "procurement_method": "Open tender",
            "contact_name": "John Smith",
            "contact_email": "john.smith@gov.au",
            "contact_phone": "02 1234 5678",
            "attachments": [
                {
                    "name": "Tender Specifications.pdf",
                    "url": f"{AUSTENDER_URL}/attachments/MOCK-2025-001-specs.pdf",
                    "description": "Detailed specifications for the building construction."
                },
                {
                    "name": "Site Plans.pdf",
                    "url": f"{AUSTENDER_URL}/attachments/MOCK-2025-001-plans.pdf",
                    "description": "Architectural and engineering plans for the site."
                }
            ]
        },
        {
            "title": "Bridge Maintenance Project",
            "reference_id": "MOCK-2025-002",
            "url": f"{AUSTENDER_URL}/cn/detail.aspx?id=MOCK-2025-002",
            "publish_date": current_date,
            "closing_date": closing_date,
            "capital_value": 2000000.0,
            "capital_value_currency": "AUD",
            "location": "Brisbane",
            "source": "Austender",
            "description": "Comprehensive maintenance and structural repairs for the Brisbane River Bridge, including repainting and replacement of worn components.",
            "category": "Construction",
            "subcategory": "Bridge Maintenance",
            "procurement_method": "Limited tender",
            "contact_name": "Sarah Johnson",
            "contact_email": "sarah.johnson@gov.au",
            "contact_phone": "07 8765 4321",
            "attachments": [
                {
                    "name": "Maintenance Schedule.pdf",
                    "url": f"{AUSTENDER_URL}/attachments/MOCK-2025-002-schedule.pdf",
                    "description": "Detailed schedule for maintenance activities."
                }
            ]
        },
        {
            "title": "Hospital Renovation Project",
            "reference_id": "MOCK-2025-003",
            "url": f"{AUSTENDER_URL}/cn/detail.aspx?id=MOCK-2025-003",
            "publish_date": current_date,
            "closing_date": closing_date,
            "capital_value": 8000000.0,
            "capital_value_currency": "AUD",
            "location": "Melbourne",
            "source": "Austender",
            "description": "Major renovation of Melbourne General Hospital's west wing, including modernization of patient rooms, operating theaters, and common areas.",
            "category": "Construction",
            "subcategory": "Healthcare Facilities",
            "procurement_method": "Open tender",
            "contact_name": "Michael Wong",
            "contact_email": "michael.wong@gov.au",
            "contact_phone": "03 9876 5432",
            "attachments": [
                {
                    "name": "Renovation Plans.pdf",
                    "url": f"{AUSTENDER_URL}/attachments/MOCK-2025-003-plans.pdf",
                    "description": "Architectural plans for the hospital renovation."
                },
                {
                    "name": "Equipment Specifications.pdf",
                    "url": f"{AUSTENDER_URL}/attachments/MOCK-2025-003-equip.pdf",
                    "description": "Specifications for new medical equipment."
                }
            ]
        }
    ]


def test_website_connectivity() -> bool:
    """
    Test if the Austender website is accessible.
    
    Returns:
        True if accessible, False otherwise
    """
    logger.info(f"Testing connectivity to {AUSTENDER_URL}")
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        response = requests.get(AUSTENDER_URL, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully connected to {AUSTENDER_URL}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to {AUSTENDER_URL}: {str(e)}")
        return False


def display_opportunity(opportunity: Dict[str, Any], index: int = 0, show_details: bool = False) -> None:
    """
    Display information about an opportunity.
    
    Args:
        opportunity: The opportunity data
        index: Index number for display purposes
        show_details: Whether to show detailed information
    """
    title = opportunity.get("title", "No Title")
    ref_id = opportunity.get("reference_id", "No Reference ID")
    location = opportunity.get("location", "No Location")
    value = opportunity.get("capital_value")
    value_str = f"${value:,.2f}" if value else "Not Specified"
    
    publish_date = opportunity.get("publish_date")
    if isinstance(publish_date, str):
        publish_date_str = publish_date
    else:
        publish_date_str = publish_date.strftime("%d/%m/%Y") if publish_date else "Not Specified"
    
    closing_date = opportunity.get("closing_date")
    if isinstance(closing_date, str):
        closing_date_str = closing_date
    else:
        closing_date_str = closing_date.strftime("%d/%m/%Y") if closing_date else "Not Specified"
    
    print(f"\n{'-'*80}")
    print(f"Opportunity {index+1}:")
    print(f"{'-'*80}")
    print(f"Title:          {title}")
    print(f"Reference ID:   {ref_id}")
    print(f"Location:       {location}")
    print(f"Value:          {value_str}")
    print(f"Published:      {publish_date_str}")
    print(f"Closing:        {closing_date_str}")
    print(f"URL:            {opportunity.get('url', 'No URL')}")
    
    if show_details:
        # Display additional details
        print("\nAdditional Details:")
        print(f"{'='*80}")
        
        # Description
        description = opportunity.get("description")
        if description:
            print(f"\nDescription:")
            print(f"{'-'*40}")
            print(f"{description[:500]}...")
            if len(description) > 500:
                print("(Description truncated)")
        
        # Category & Subcategory
        category = opportunity.get("category")
        subcategory = opportunity.get("subcategory")
        if category:
            print(f"\nCategory:        {category}")
        if subcategory:
            print(f"Subcategory:     {subcategory}")
        
        # Contact information
        contact_name = opportunity.get("contact_name")
        contact_email = opportunity.get("contact_email")
        contact_phone = opportunity.get("contact_phone")
        
        if any([contact_name, contact_email, contact_phone]):
            print("\nContact Information:")
            print(f"{'-'*40}")
            if contact_name:
                print(f"Name:            {contact_name}")
            if contact_email:
                print(f"Email:           {contact_email}")
            if contact_phone:
                print(f"Phone:           {contact_phone}")
        
        # Attachments
        attachments = opportunity.get("attachments", [])
        if attachments:
            print("\nAttachments:")
            print(f"{'-'*40}")
            for i, attachment in enumerate(attachments, 1):
                name = attachment.get("name", "No Name")
                url = attachment.get("url", "No URL")
                print(f"{i}. {name}")
                print(f"   URL: {url}")


def run_scraper_test(args: argparse.Namespace) -> None:
    """
    Run a test of the Austender scraper.
    
    Args:
        args: Command line arguments
    """
    use_mock = args.mock
    debug_mode = args.debug
    limit = args.limit
    
    if debug_mode:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Test connectivity first if not using mock data
    if not use_mock and not test_website_connectivity():
        print("\nWarning: Unable to connect to the Austender website.")
        print("You can still run the test with --mock to use sample data.")
        if not args.force:
            print("Use --force to continue with live data despite connection issues.")
            return
        print("Continuing with live data as --force was specified.")
    
    # Initialize the scraper
    logger.info("Initializing AustenderScraper")
    scraper = AustenderScraper()
    
    if use_mock:
        logger.info("Using mock data for testing")
        opportunities = create_mock_data()
        
        # Display the mock opportunities
        print("\nMock Opportunities:")
        for i, opp in enumerate(opportunities[:limit]):
            display_opportunity(opp, i, show_details=args.details)
        
        print("\nMock data test completed successfully.")
        return
    
    # Try to search for opportunities
    try:
        logger.info("Searching for construction opportunities")
        
        # Print request URL for debugging
        if debug_mode:
            search_url = f"{scraper.search_url}?category=construction&page=1"
            logger.debug(f"Search URL: {search_url}")
        
        opportunities = scraper.search_opportunities(
            category="construction",
            page=1
        )
        
        if not opportunities:
            logger.warning("No opportunities found.")
            print("\nNo opportunities were found. Possible reasons:")
            print("1. The search criteria may be too restrictive")
            print("2. The website structure may have changed")
            print("3. There may be temporary issues with the website")
            return
        
        logger.info(f"Found {len(opportunities)} opportunities on page 1.")
        
        # Apply limit
        opportunities = opportunities[:limit]
        
        # Display the opportunities
        print(f"\nFound {len(opportunities)} construction opportunities:")
        for i, opp in enumerate(opportunities):
            if not args.details:
                display_opportunity(opp, i)
            else:
                # Fetch detailed information
                try:
                    if opp.get("url"):
                        logger.info(f"Fetching details for opportunity {i+1}: {opp.get('title', '')}")
                        details = scraper.get_opportunity_details(opp["url"])
                        display_opportunity(details, i, show_details=True)
                        # Be nice to the server
                        time.sleep(1)
                    else:
                        logger.warning(f"No URL available for opportunity {i+1}")
                        display_opportunity(opp, i)
                except Exception as e:
                    logger.error(f"Error fetching details for opportunity {i+1}: {str(e)}")
                    if debug_mode:
                        logger.debug(traceback.format_exc())
                    display_opportunity(opp, i)
        
        print("\nTest completed successfully.")
                
    except Exception as e:
        logger.error(f"Error running scraper test: {str(e)}")
        if debug_mode:
            logger.debug(traceback.format_exc())
        
        print(f"\nError testing scraper: {str(e)}")
        print("Possible issues:")
        print("1. The website structure may have changed")
        print("2. Network connectivity problems")
        print("3. Website rate limiting or blocking")
        
        # Offer solution
        print("\nTry the following:")
        print("1. Run with --mock to test with sample data")
        print("2. Run with --debug for more information")
        print("3. Check your internet connection")
        print("4. The scraper code may need to be updated to match website changes")


def main():
    """Main function to parse arguments and run the test."""
    parser = argparse.ArgumentParser(description="Improved testing for Austender scraper")
    parser.add_argument("--mock", action="store_true", help="Use mock data instead of live website")
    parser.add_argument("--debug", action="store_true", help="Show detailed debug information")
    parser.add_argument("--details", action="store_true", help="Show detailed opportunity information")
    parser.add_argument("--force", action="store_true", help="Force live data even if connectivity test fails")
    parser.add_argument("--limit", type=int, default=3, help="Limit number of opportunities to fetch")
    
    args = parser.parse_args()
    
    try:
        run_scraper_test(args)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        print("\nTest interrupted.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.debug(traceback.format_exc())
        print(f"\nUnexpected error: {str(e)}")
        print("Please run with --debug for more information.")


if __name__ == "__main__":
    main()
