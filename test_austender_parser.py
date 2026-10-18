#!/usr/bin/env python
"""
Austender Parser Test Script

This script tests the parsing logic of the AustenderScraper without actually
making live requests to the website. It uses saved HTML files to verify that
the parser can correctly extract information from the Austender website format.

Usage:
    python test_austender_parser.py

This approach allows for testing the scraper's parsing logic separately from
the network requests, which is useful when the website is blocking automated access.
"""

import os
import sys
import json
import datetime
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional

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
logger = logging.getLogger("test_austender_parser")

# Import the scraper
try:
    from scrapers.austender_scraper import AustenderScraper
except ImportError as e:
    logger.error(f"Error importing AustenderScraper: {str(e)}")
    sys.exit(1)


def ensure_test_data_directory() -> Path:
    """
    Ensure the test data directory exists and create it if needed.
    
    Returns:
        Path to the test data directory
    """
    data_dir = Path(__file__).parent / "tests" / "data" / "austender"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def create_sample_html_files() -> Dict[str, Path]:
    """
    Create sample HTML files for testing the parser.
    
    Returns:
        Dictionary mapping file types to their paths
    """
    data_dir = ensure_test_data_directory()
    
    # Create sample search results HTML
    search_results_path = data_dir / "search_results.html"
    if not search_results_path.exists():
        with open(search_results_path, "w", encoding="utf-8") as f:
            f.write("""
            <html>
            <body>
                <div class="search-results">
                    <div class="search-result">
                        <h3><a href="/cn/detail.aspx?id=CN12345">Office Building Construction</a></h3>
                        <div class="result-details">
                            <p>Reference ID: CN12345</p>
                            <p>Published Date: 15/04/2025</p>
                            <p>Closing Date: 15/05/2025</p>
                            <p>Location: Sydney, NSW</p>
                            <p>Value: $5,000,000.00 AUD</p>
                        </div>
                    </div>
                    <div class="search-result">
                        <h3><a href="/cn/detail.aspx?id=CN12346">Road Construction Project</a></h3>
                        <div class="result-details">
                            <p>Reference ID: CN12346</p>
                            <p>Published Date: 16/04/2025</p>
                            <p>Closing Date: 16/05/2025</p>
                            <p>Location: Melbourne, VIC</p>
                            <p>Value: $8,000,000.00 - $10,000,000.00 AUD</p>
                        </div>
                    </div>
                    <div class="search-result">
                        <h3><a href="/cn/detail.aspx?id=CN12347">Hospital Renovation</a></h3>
                        <div class="result-details">
                            <p>Reference ID: CN12347</p>
                            <p>Published Date: 17/04/2025</p>
                            <p>Closing Date: 17/05/2025</p>
                            <p>Location: Brisbane, QLD</p>
                            <p>Value: Not disclosed</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """)
    
    # Create sample detail page HTML
    detail_page_path = data_dir / "opportunity_detail.html"
    if not detail_page_path.exists():
        with open(detail_page_path, "w", encoding="utf-8") as f:
            f.write("""
            <html>
            <body>
                <div class="opportunity-details">
                    <h1>Office Building Construction</h1>
                    <div class="details-section">
                        <div class="detail-item">
                            <span class="label">Reference ID:</span>
                            <span class="value">CN12345</span>
                        </div>
                        <div class="detail-item">
                            <span class="label">Published Date:</span>
                            <span class="value">15/04/2025</span>
                        </div>
                        <div class="detail-item">
                            <span class="label">Closing Date:</span>
                            <span class="value">15/05/2025</span>
                        </div>
                        <div class="detail-item">
                            <span class="label">Location:</span>
                            <span class="value">Sydney, NSW</span>
                        </div>
                        <div class="detail-item">
                            <span class="label">Value:</span>
                            <span class="value">$5,000,000.00 AUD</span>
                        </div>
                        <div class="detail-item">
                            <span class="label">Category:</span>
                            <span class="value">Construction</span>
                        </div>
                        <div class="detail-item">
                            <span class="label">Subcategory:</span>
                            <span class="value">Commercial Buildings</span>
                        </div>
                        <div class="detail-item">
                            <span class="label">Procurement Method:</span>
                            <span class="value">Open Tender</span>
                        </div>
                    </div>
                    <div class="description">
                        <h2>Description</h2>
                        <p>Construction of a new 10-story government office building in Sydney CBD with sustainable features and modern facilities.</p>
                    </div>
                    <div class="contact-info">
                        <h2>Contact Information</h2>
                        <div class="contact-item">
                            <span class="label">Name:</span>
                            <span class="value">John Smith</span>
                        </div>
                        <div class="contact-item">
                            <span class="label">Email:</span>
                            <span class="value">john.smith@gov.au</span>
                        </div>
                        <div class="contact-item">
                            <span class="label">Phone:</span>
                            <span class="value">02 1234 5678</span>
                        </div>
                    </div>
                    <div class="attachments">
                        <h2>Attachments</h2>
                        <div class="attachment-item">
                            <a href="/attachments/CN12345-specs.pdf">Tender Specifications.pdf</a>
                            <p>Detailed specifications for the building construction.</p>
                        </div>
                        <div class="attachment-item">
                            <a href="/attachments/CN12345-plans.pdf">Site Plans.pdf</a>
                            <p>Architectural and engineering plans for the site.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """)
    
    return {
        "search_results": search_results_path,
        "opportunity_detail": detail_page_path
    }


def test_parse_search_results(scraper: AustenderScraper, html_file: Path) -> None:
    """
    Test the parsing of search results.
    
    Args:
        scraper: AustenderScraper instance
        html_file: Path to the HTML file with search results
    """
    logger.info("Testing search results parsing")
    
    # Read the HTML file
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Parse the HTML
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Call the parser method
    try:
        results = scraper._parse_search_results(soup)
        
        # Verify the results
        if not results:
            logger.error("No results parsed from search results HTML")
            return
        
        logger.info(f"Successfully parsed {len(results)} search results")
        
        # Display the parsed results
        print("\nParsed Search Results:")
        print("="*80)
        
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print("-"*40)
            for key, value in result.items():
                print(f"{key.ljust(15)}: {value}")
        
    except Exception as e:
        logger.error(f"Error parsing search results: {str(e)}")


def test_parse_opportunity_details(scraper: AustenderScraper, html_file: Path) -> None:
    """
    Test the parsing of opportunity details.
    
    Args:
        scraper: AustenderScraper instance
        html_file: Path to the HTML file with opportunity details
    """
    logger.info("Testing opportunity details parsing")
    
    # Read the HTML file
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Parse the HTML
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Call the parser method
    try:
        details = scraper._parse_opportunity_details(soup, "https://www.tenders.gov.au/cn/detail.aspx?id=CN12345")
        
        # Verify the results
        if not details:
            logger.error("No details parsed from opportunity details HTML")
            return
        
        logger.info("Successfully parsed opportunity details")
        
        # Display the parsed details
        print("\nParsed Opportunity Details:")
        print("="*80)
        
        # Print main details
        for key in ["title", "reference_id", "url", "publish_date", "closing_date", 
                    "capital_value", "location", "category", "subcategory", 
                    "procurement_method", "description"]:
            if key in details:
                print(f"{key.ljust(20)}: {details[key]}")
        
        # Print contact information
        if any(key in details for key in ["contact_name", "contact_email", "contact_phone"]):
            print("\nContact Information:")
            print("-"*40)
            for key in ["contact_name", "contact_email", "contact_phone"]:
                if key in details:
                    print(f"{key.ljust(20)}: {details[key]}")
        
        # Print attachments
        attachments = details.get("attachments", [])
        if attachments:
            print("\nAttachments:")
            print("-"*40)
            for i, attachment in enumerate(attachments, 1):
                print(f"Attachment {i}:")
                for key, value in attachment.items():
                    print(f"  {key.ljust(15)}: {value}")
        
    except Exception as e:
        logger.error(f"Error parsing opportunity details: {str(e)}")


def test_parsing_functions(scraper: AustenderScraper) -> None:
    """
    Test the date and value parsing functions.
    
    Args:
        scraper: AustenderScraper instance
    """
    logger.info("Testing parsing utility functions")
    
    # Test date parsing
    print("\nDate Parsing Tests:")
    print("="*80)
    date_tests = [
        "15/04/2025",
        "15 Apr 2025",
        "April 15, 2025",
        "2025-04-15",
        "invalid date"
    ]
    
    for date_str in date_tests:
        try:
            result = scraper._parse_date(date_str)
            print(f"'{date_str}' -> {result}")
        except Exception as e:
            print(f"'{date_str}' -> Error: {str(e)}")
    
    # Test value parsing
    print("\nValue Parsing Tests:")
    print("="*80)
    value_tests = [
        "$5,000,000.00",
        "5,000,000.00 AUD",
        "$5,000,000 - $8,000,000",
        "5M - 8M AUD",
        "Not disclosed",
        "invalid value"
    ]
    
    for value_str in value_tests:
        try:
            result = scraper._parse_value(value_str)
            print(f"'{value_str}' -> {result}")
        except Exception as e:
            print(f"'{value_str}' -> Error: {str(e)}")


def main() -> None:
    """Main function to run the tests."""
    logger.info("Starting Austender parser tests")
    
    # Create sample HTML files
    html_files = create_sample_html_files()
    
    # Initialize the scraper
    scraper = AustenderScraper()
    
    # Test the parsing functions
    test_parsing_functions(scraper)
    
    # Test parsing search results
    test_parse_search_results(scraper, html_files["search_results"])
    
    # Test parsing opportunity details
    test_parse_opportunity_details(scraper, html_files["opportunity_detail"])
    
    logger.info("Austender parser tests completed")


if __name__ == "__main__":
    main()
