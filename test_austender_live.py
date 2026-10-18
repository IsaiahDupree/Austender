#!/usr/bin/env python
"""
Test script for the Austender scraper with live data.

This script demonstrates the functionality of the AustenderScraper by:
1. Running searches with different parameters
2. Displaying the search results
3. Retrieving and displaying detailed information for opportunities

Usage:
    python test_austender_live.py [--save] [--details] [--limit N]

Options:
    --save      Save the retrieved opportunities to the database
    --details   Fetch and display detailed information for each opportunity
    --limit N   Limit the number of opportunities to fetch (default: 5)
"""

import os
import sys
import argparse
import json
import datetime
import time
from typing import List, Dict, Any
import logging

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
logger = logging.getLogger("test_austender_live")

# Import scraper
from scrapers.austender_scraper import AustenderScraper


def display_opportunity_summary(opportunity: Dict[str, Any], index: int = 0) -> None:
    """
    Display a summary of an opportunity.
    
    Args:
        opportunity: The opportunity data
        index: Index number for display purposes
    """
    title = opportunity.get("title", "No Title")
    ref_id = opportunity.get("reference_id", "No Reference ID")
    location = opportunity.get("location", "No Location")
    value = opportunity.get("capital_value")
    value_str = f"${value:,.2f}" if value else "Not Specified"
    
    publish_date = opportunity.get("publish_date")
    publish_date_str = publish_date.strftime("%d/%m/%Y") if publish_date else "Not Specified"
    
    closing_date = opportunity.get("closing_date")
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


def display_opportunity_details(opportunity: Dict[str, Any]) -> None:
    """
    Display detailed information about an opportunity.
    
    Args:
        opportunity: The detailed opportunity data
    """
    # Display basic information first
    display_opportunity_summary(opportunity)
    
    # Display additional details
    print("\nAdditional Details:")
    print(f"{'='*80}")
    
    # Description
    description = opportunity.get("description")
    if description:
        print(f"\nDescription:")
        print(f"{'-'*40}")
        # Limit to 500 characters to keep the output manageable
        print(f"{description[:500]}...")
        if len(description) > 500:
            print("(Description truncated)")
    
    # Category
    category = opportunity.get("category")
    if category:
        print(f"\nCategory:        {category}")
    
    # Subcategory
    subcategory = opportunity.get("subcategory")
    if subcategory:
        print(f"Subcategory:     {subcategory}")
    
    # Procurement method
    procurement_method = opportunity.get("procurement_method")
    if procurement_method:
        print(f"Procurement:     {procurement_method}")
    
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
    
    print(f"\n{'='*80}")


def run_test_search(scraper: AustenderScraper, args: argparse.Namespace) -> None:
    """
    Run a test search for opportunities.
    
    Args:
        scraper: The AustenderScraper instance
        args: Command line arguments
    """
    limit = args.limit
    save_to_db = args.save
    fetch_details = args.details
    
    logger.info(f"Running test search for construction opportunities (limit: {limit})")
    
    try:
        # Search for opportunities
        opportunities = scraper.search_opportunities(
            category="construction",
            page=1
        )
        
        if not opportunities:
            logger.warning("No opportunities found.")
            return
        
        logger.info(f"Found {len(opportunities)} opportunities on page 1.")
        
        # Apply limit
        opportunities = opportunities[:limit]
        
        # Display summary of each opportunity
        for i, opp in enumerate(opportunities):
            if not fetch_details:
                display_opportunity_summary(opp, i)
            else:
                # Fetch detailed information
                if opp.get("url"):
                    logger.info(f"Fetching details for opportunity {i+1}: {opp.get('title', '')}")
                    details = scraper.get_opportunity_details(opp["url"])
                    display_opportunity_details(details)
                    # Be nice to the server
                    time.sleep(1)
                else:
                    logger.warning(f"No URL available for opportunity {i+1}")
                    display_opportunity_summary(opp, i)
        
        # Save to database if requested
        if save_to_db:
            logger.info("Saving opportunities to database...")
            if fetch_details:
                # We need to re-fetch the detailed opportunities
                detailed_opportunities = []
                for opp in opportunities:
                    if opp.get("url"):
                        details = scraper.get_opportunity_details(opp["url"])
                        detailed_opportunities.append(details)
                        # Be nice to the server
                        time.sleep(1)
                
                scraper.save_opportunities(detailed_opportunities)
            else:
                scraper.save_opportunities(opportunities)
            
            logger.info("Opportunities saved to database.")
    
    except Exception as e:
        logger.error(f"Error during test search: {str(e)}")


def run_category_search(scraper: AustenderScraper, args: argparse.Namespace) -> None:
    """
    Run a search for opportunities across multiple categories.
    
    Args:
        scraper: The AustenderScraper instance
        args: Command line arguments
    """
    limit = args.limit
    categories = ["construction", "building", "maintenance", "renovation"]
    
    logger.info(f"Searching for opportunities across {len(categories)} categories")
    
    for category in categories:
        try:
            logger.info(f"Searching for '{category}' opportunities...")
            
            opportunities = scraper.search_opportunities(
                category=category,
                page=1
            )
            
            if not opportunities:
                logger.warning(f"No opportunities found for category '{category}'.")
                continue
            
            logger.info(f"Found {len(opportunities)} opportunities for category '{category}'.")
            
            # Apply limit and display summary
            for i, opp in enumerate(opportunities[:limit]):
                display_opportunity_summary(opp, i)
                
            # Wait between categories
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error during category search for '{category}': {str(e)}")


def run_value_search(scraper: AustenderScraper, args: argparse.Namespace) -> None:
    """
    Run a search for opportunities with different value ranges.
    
    Args:
        scraper: The AustenderScraper instance
        args: Command line arguments
    """
    limit = args.limit
    value_ranges = [
        (0, 100000, "0 - $100,000"),
        (100000, 1000000, "$100,000 - $1,000,000"),
        (1000000, 10000000, "$1,000,000 - $10,000,000"),
        (10000000, None, "$10,000,000+")
    ]
    
    logger.info(f"Searching for opportunities across {len(value_ranges)} value ranges")
    
    for min_value, max_value, label in value_ranges:
        try:
            logger.info(f"Searching for opportunities in value range {label}...")
            
            opportunities = scraper.search_opportunities(
                category="construction",
                min_value=min_value,
                max_value=max_value,
                page=1
            )
            
            if not opportunities:
                logger.warning(f"No opportunities found in value range {label}.")
                continue
            
            logger.info(f"Found {len(opportunities)} opportunities in value range {label}.")
            
            # Apply limit and display summary
            for i, opp in enumerate(opportunities[:limit]):
                display_opportunity_summary(opp, i)
                
            # Wait between value ranges
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error during value search for range {label}: {str(e)}")


def run_location_search(scraper: AustenderScraper, args: argparse.Namespace) -> None:
    """
    Run a search for opportunities across different locations.
    
    Args:
        scraper: The AustenderScraper instance
        args: Command line arguments
    """
    limit = args.limit
    locations = ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Canberra"]
    
    logger.info(f"Searching for opportunities across {len(locations)} locations")
    
    for location in locations:
        try:
            logger.info(f"Searching for opportunities in {location}...")
            
            opportunities = scraper.search_opportunities(
                category="construction",
                location=location,
                page=1
            )
            
            if not opportunities:
                logger.warning(f"No opportunities found in {location}.")
                continue
            
            logger.info(f"Found {len(opportunities)} opportunities in {location}.")
            
            # Apply limit and display summary
            for i, opp in enumerate(opportunities[:limit]):
                display_opportunity_summary(opp, i)
                
            # Wait between locations
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error during location search for {location}: {str(e)}")


def main():
    """Main function to parse arguments and run the tests."""
    parser = argparse.ArgumentParser(description="Test Austender scraper with live data")
    parser.add_argument("--save", action="store_true", help="Save opportunities to database")
    parser.add_argument("--details", action="store_true", help="Fetch detailed information")
    parser.add_argument("--limit", type=int, default=5, help="Limit number of opportunities to fetch")
    parser.add_argument("--test", choices=["basic", "category", "value", "location", "all"], 
                        default="basic", help="Type of test to run")
    
    args = parser.parse_args()
    
    # Create scraper
    logger.info("Initializing AustenderScraper")
    scraper = AustenderScraper()
    
    # Run the selected test
    if args.test == "basic" or args.test == "all":
        run_test_search(scraper, args)
    
    if args.test == "category" or args.test == "all":
        run_category_search(scraper, args)
    
    if args.test == "value" or args.test == "all":
        run_value_search(scraper, args)
    
    if args.test == "location" or args.test == "all":
        run_location_search(scraper, args)
    
    logger.info("Test completed.")


if __name__ == "__main__":
    main()
