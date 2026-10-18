#!/usr/bin/env python
"""
Austender Scraper Test with Compatible HTML

This script creates HTML files that match the exact structure expected by the Austender scraper
and then tests the scraper's parsing logic with these compatible files.

Usage:
    python test_austender_with_compatible_html.py
"""

import os
import sys
import datetime
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Any, List

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
logger = logging.getLogger("test_austender_compatible")

# Import scraper
try:
    from scrapers.austender_scraper import AustenderScraper
except ImportError as e:
    logger.error(f"Error importing AustenderScraper: {str(e)}")
    sys.exit(1)


def create_compatible_html_files() -> Dict[str, Path]:
    """
    Create HTML files that match the exact structure expected by the scraper.
    
    Returns:
        Dictionary mapping file types to their paths
    """
    data_dir = Path(__file__).parent / "tests" / "data" / "austender_compatible"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create search results HTML with compatible selectors
    search_results_path = data_dir / "search_results.html"
    with open(search_results_path, "w", encoding="utf-8") as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>AusTender: Search Results</title>
</head>
<body>
    <div class="search-results">
        <div class="opportunity-item">
            <div class="title"><a href="/cn/show/CN3837116">Office Building Construction</a></div>
            <div class="reference-id">CN3837116</div>
            <div class="dates">
                <div class="publish-date">15/04/2025</div>
                <div class="closing-date">15/05/2025</div>
            </div>
            <div class="value">$5,000,000.00 AUD</div>
            <div class="location">Sydney, NSW</div>
        </div>
        <div class="opportunity-item">
            <div class="title"><a href="/cn/show/CN3837117">Bridge Maintenance Project</a></div>
            <div class="reference-id">CN3837117</div>
            <div class="dates">
                <div class="publish-date">16/04/2025</div>
                <div class="closing-date">16/05/2025</div>
            </div>
            <div class="value">$2,500,000.00 - $3,000,000.00 AUD</div>
            <div class="location">Brisbane, QLD</div>
        </div>
        <div class="opportunity-item">
            <div class="title"><a href="/cn/show/CN3837118">Hospital Renovation Works</a></div>
            <div class="reference-id">CN3837118</div>
            <div class="dates">
                <div class="publish-date">17/04/2025</div>
                <div class="closing-date">17/05/2025</div>
            </div>
            <div class="value">Not disclosed</div>
            <div class="location">Melbourne, VIC</div>
        </div>
    </div>
</body>
</html>
        """)
    
    # Create opportunity details HTML with compatible selectors
    opportunity_details_path = data_dir / "opportunity_details.html"
    with open(opportunity_details_path, "w", encoding="utf-8") as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>AusTender: Opportunity Details</title>
</head>
<body>
    <div class="opportunity-details">
        <h1 class="opportunity-title">Office Building Construction</h1>
        <div class="atm-id">CN3837116</div>
        <div class="opportunity-description">
            <p>This tender is for the construction of a new government office building in Sydney's CBD.</p>
            <p>The project involves construction of a 6-story building with sustainable design features,
            underground parking, and modern facilities to meet government standards.</p>
        </div>
        
        <div class="detail-section">
            <div class="publish-date">15/04/2025</div>
            <div class="closing-date">15/05/2025</div>
            <div class="start-date">01/06/2025</div>
            <div class="estimated-value">$5,000,000.00 AUD</div>
            <div class="category">Construction</div>
            <div class="procurement-method">Open Tender</div>
            <div class="location">Sydney, NSW</div>
        </div>
        
        <div class="contact-section">
            <div class="contact-name">Sarah Johnson</div>
            <div class="contact-email">sarah.johnson@gov.au</div>
            <div class="contact-phone">02 9123 4567</div>
        </div>
        
        <div class="attachments-section">
            <div class="attachment">
                <div class="name">Tender Documentation.pdf</div>
                <a href="/cn/download/CN3837116/1">Download</a>
                <div class="description">Comprehensive tender documentation including requirements and submission details.</div>
            </div>
            <div class="attachment">
                <div class="name">Building Specifications.pdf</div>
                <a href="/cn/download/CN3837116/2">Download</a>
                <div class="description">Detailed specifications for the building construction and materials.</div>
            </div>
            <div class="attachment">
                <div class="name">Site Plans.zip</div>
                <a href="/cn/download/CN3837116/3">Download</a>
                <div class="description">Architectural and engineering plans for the site and building.</div>
            </div>
        </div>
    </div>
</body>
</html>
        """)
    
    return {
        "search_results": search_results_path,
        "opportunity_details": opportunity_details_path
    }


def test_with_compatible_html() -> None:
    """
    Test the scraper using HTML that is compatible with its expected selectors.
    """
    logger.info("Creating compatible HTML files")
    html_files = create_compatible_html_files()
    
    logger.info("Initializing scraper")
    scraper = AustenderScraper()
    
    # Test search results parsing
    logger.info("Testing search results parsing")
    with open(html_files["search_results"], "r", encoding="utf-8") as f:
        search_soup = BeautifulSoup(f.read(), "html.parser")
    
    try:
        search_results = scraper._parse_search_results(search_soup)
        logger.info(f"Found {len(search_results)} opportunities in search results")
        
        print("\nParsed Search Results:")
        print("="*80)
        
        for i, opportunity in enumerate(search_results, 1):
            print(f"\nOpportunity {i}:")
            print("-"*40)
            
            for key, value in opportunity.items():
                if isinstance(value, datetime.date):
                    value = value.strftime("%d/%m/%Y")
                print(f"{key.ljust(15)}: {value}")
    
    except Exception as e:
        logger.error(f"Error parsing search results: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test opportunity details parsing
    logger.info("Testing opportunity details parsing")
    with open(html_files["opportunity_details"], "r", encoding="utf-8") as f:
        details_soup = BeautifulSoup(f.read(), "html.parser")
    
    try:
        opportunity_details = scraper._parse_opportunity_details(
            details_soup, 
            "https://www.tenders.gov.au/cn/show/CN3837116"
        )
        
        logger.info("Successfully parsed opportunity details")
        
        print("\nParsed Opportunity Details:")
        print("="*80)
        
        # Print the details excluding attachments
        for key, value in opportunity_details.items():
            if key != "attachments":
                if isinstance(value, datetime.date):
                    value = value.strftime("%d/%m/%Y")
                if key == "description":
                    print("\nDescription:")
                    print("-"*40)
                    print(value)
                else:
                    print(f"{key.ljust(18)}: {value}")
        
        # Print attachments
        attachments = opportunity_details.get("attachments", [])
        if attachments:
            print("\nAttachments:")
            print("-"*40)
            
            for i, attachment in enumerate(attachments, 1):
                print(f"Attachment {i}:")
                for key, value in attachment.items():
                    print(f"  {key.ljust(12)}: {value}")
    
    except Exception as e:
        logger.error(f"Error parsing opportunity details: {str(e)}")
        import traceback
        traceback.print_exc()


def main() -> None:
    """Main function to run the test."""
    logger.info("Starting Austender scraper test with compatible HTML")
    
    try:
        test_with_compatible_html()
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
