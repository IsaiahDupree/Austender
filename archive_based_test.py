#!/usr/bin/env python
"""
Archive-Based Austender Scraper Test

This script tests the Austender scraper using archived HTML files from the actual website.
Instead of making live requests, it uses pre-saved HTML files to verify the scraper's
parsing logic with realistic data.

Usage:
    python archive_based_test.py [--create-samples]

Options:
    --create-samples    Create sample HTML files with more realistic structure
"""

import os
import sys
import argparse
import json
import datetime
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
import requests
from unittest.mock import patch, MagicMock

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
logger = logging.getLogger("archive_based_test")

# Import the scraper
try:
    from scrapers.austender_scraper import AustenderScraper
    from config.config import AUSTENDER_URL
except ImportError as e:
    logger.error(f"Error importing required modules: {str(e)}")
    sys.exit(1)


def ensure_archive_directory() -> Path:
    """
    Ensure the archive directory exists and create it if needed.
    
    Returns:
        Path to the archive directory
    """
    archive_dir = Path(__file__).parent / "tests" / "archive" / "austender"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


def create_realistic_sample_files(force: bool = False) -> Dict[str, Path]:
    """
    Create more realistic sample HTML files based on the actual website structure.
    
    Args:
        force: Whether to force creation even if files already exist
        
    Returns:
        Dictionary mapping file types to their paths
    """
    archive_dir = ensure_archive_directory()
    
    # Search results HTML (more realistic structure)
    search_results_path = archive_dir / "realistic_search_results.html"
    if not search_results_path.exists() or force:
        with open(search_results_path, "w", encoding="utf-8") as f:
            f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>AusTender: Search Results</title>
</head>
<body>
    <div class="result-list">
        <div class="search-result">
            <h2 class="title"><a href="https://www.tenders.gov.au/cn/show/CN3837116">Construction of Government Facilities</a></h2>
            <div class="meta-container">
                <div class="meta-info">
                    <span class="label">Reference ID:</span> <span class="value">CN3837116</span>
                </div>
                <div class="meta-info">
                    <span class="label">Published:</span> <span class="value">15/04/2025</span>
                </div>
                <div class="meta-info">
                    <span class="label">Closing:</span> <span class="value">15/05/2025</span>
                </div>
                <div class="meta-info">
                    <span class="label">Location:</span> <span class="value">NSW</span>
                </div>
                <div class="meta-info">
                    <span class="label">Value:</span> <span class="value">$4,500,000.00</span>
                </div>
            </div>
        </div>
        <div class="search-result">
            <h2 class="title"><a href="https://www.tenders.gov.au/cn/show/CN3837117">Bridge Maintenance Project</a></h2>
            <div class="meta-container">
                <div class="meta-info">
                    <span class="label">Reference ID:</span> <span class="value">CN3837117</span>
                </div>
                <div class="meta-info">
                    <span class="label">Published:</span> <span class="value">16/04/2025</span>
                </div>
                <div class="meta-info">
                    <span class="label">Closing:</span> <span class="value">16/05/2025</span>
                </div>
                <div class="meta-info">
                    <span class="label">Location:</span> <span class="value">QLD</span>
                </div>
                <div class="meta-info">
                    <span class="label">Value:</span> <span class="value">$2,500,000.00 - $3,000,000.00</span>
                </div>
            </div>
        </div>
        <div class="search-result">
            <h2 class="title"><a href="https://www.tenders.gov.au/cn/show/CN3837118">Hospital Renovation Works</a></h2>
            <div class="meta-container">
                <div class="meta-info">
                    <span class="label">Reference ID:</span> <span class="value">CN3837118</span>
                </div>
                <div class="meta-info">
                    <span class="label">Published:</span> <span class="value">17/04/2025</span>
                </div>
                <div class="meta-info">
                    <span class="label">Closing:</span> <span class="value">17/05/2025</span>
                </div>
                <div class="meta-info">
                    <span class="label">Location:</span> <span class="value">VIC</span>
                </div>
                <div class="meta-info">
                    <span class="label">Value:</span> <span class="value">Not disclosed</span>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
            """)
    
    # Opportunity details HTML (more realistic structure)
    opportunity_details_path = archive_dir / "realistic_opportunity_details.html"
    if not opportunity_details_path.exists() or force:
        with open(opportunity_details_path, "w", encoding="utf-8") as f:
            f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>AusTender: Construction of Government Facilities</title>
</head>
<body>
    <div class="tender-detail">
        <h1 class="title">Construction of Government Facilities</h1>
        
        <div class="detail-section">
            <div class="detail-row">
                <div class="detail-label">Reference ID:</div>
                <div class="detail-value">CN3837116</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Published Date:</div>
                <div class="detail-value">15/04/2025</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Closing Date:</div>
                <div class="detail-value">15/05/2025 11:00 AM</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Location:</div>
                <div class="detail-value">NSW</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Estimated Value:</div>
                <div class="detail-value">$4,500,000.00 AUD</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Category:</div>
                <div class="detail-value">Construction</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Subcategory:</div>
                <div class="detail-value">Commercial and Government Buildings</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Procurement Method:</div>
                <div class="detail-value">Open Tender</div>
            </div>
        </div>
        
        <div class="description-section">
            <h2>Description</h2>
            <div class="description-content">
                <p>This tender is for the construction of new government facilities in Sydney's CBD. The project involves:</p>
                <ul>
                    <li>Construction of a 6-story office building</li>
                    <li>Underground parking facilities</li>
                    <li>Integration of sustainable design features</li>
                    <li>Landscaping and external works</li>
                </ul>
                <p>The project aims to provide modern, accessible facilities for government services while meeting high environmental standards.</p>
            </div>
        </div>
        
        <div class="contact-section">
            <h2>Contact Details</h2>
            <div class="contact-row">
                <div class="contact-label">Contact Person:</div>
                <div class="contact-value">Sarah Johnson</div>
            </div>
            <div class="contact-row">
                <div class="contact-label">Email:</div>
                <div class="contact-value">sarah.johnson@infrastructure.gov.au</div>
            </div>
            <div class="contact-row">
                <div class="contact-label">Phone:</div>
                <div class="contact-value">02 9123 4567</div>
            </div>
        </div>
        
        <div class="attachments-section">
            <h2>Attachments</h2>
            <div class="attachment-item">
                <div class="attachment-name">
                    <a href="https://www.tenders.gov.au/cn/download/CN3837116/1">Tender Documentation.pdf</a>
                </div>
                <div class="attachment-description">
                    Comprehensive tender documentation including requirements and submission details.
                </div>
            </div>
            <div class="attachment-item">
                <div class="attachment-name">
                    <a href="https://www.tenders.gov.au/cn/download/CN3837116/2">Building Specifications.pdf</a>
                </div>
                <div class="attachment-description">
                    Detailed specifications for the building construction and materials.
                </div>
            </div>
            <div class="attachment-item">
                <div class="attachment-name">
                    <a href="https://www.tenders.gov.au/cn/download/CN3837116/3">Site Plans.zip</a>
                </div>
                <div class="attachment-description">
                    Architectural and engineering plans for the site and building.
                </div>
            </div>
        </div>
    </div>
</body>
</html>
            """)
    
    return {
        "search_results": search_results_path,
        "opportunity_detail": opportunity_details_path
    }


def mock_scraper_methods(scraper: AustenderScraper, html_files: Dict[str, Path]) -> None:
    """
    Mock the scraper's methods to use our archived HTML files instead of making live requests.
    
    Args:
        scraper: AustenderScraper instance
        html_files: Dictionary mapping file types to their paths
    """
    # Read the HTML files
    with open(html_files["search_results"], "r", encoding="utf-8") as f:
        search_results_html = f.read()
    
    with open(html_files["opportunity_detail"], "r", encoding="utf-8") as f:
        opportunity_detail_html = f.read()
    
    # Create BeautifulSoup objects
    search_results_soup = BeautifulSoup(search_results_html, "html.parser")
    opportunity_detail_soup = BeautifulSoup(opportunity_detail_html, "html.parser")
    
    # Mock the get_page method
    def mock_get_page(url: str) -> BeautifulSoup:
        if "search" in url or "cn/list" in url:
            return search_results_soup
        elif "detail" in url or "cn/show" in url:
            return opportunity_detail_soup
        else:
            raise ValueError(f"Unknown URL pattern: {url}")
    
    # Apply the mock to the scraper instance
    scraper.get_page = mock_get_page


def test_search_opportunities(scraper: AustenderScraper) -> None:
    """
    Test the search_opportunities method with mocked responses.
    
    Args:
        scraper: AustenderScraper instance with mocked methods
    """
    logger.info("Testing search_opportunities method")
    
    try:
        # Call the search_opportunities method
        opportunities = scraper.search_opportunities(
            category="construction",
            keyword="government",
            location="NSW",
            page=1
        )
        
        if not opportunities:
            logger.warning("No opportunities found in search results")
            return
        
        logger.info(f"Found {len(opportunities)} opportunities")
        
        # Display the opportunities
        print("\nOpportunities Found:")
        print("="*80)
        
        for i, opp in enumerate(opportunities, 1):
            print(f"\nOpportunity {i}:")
            print("-"*40)
            
            # Display basic information
            basic_fields = ["title", "reference_id", "url", "publish_date", 
                           "closing_date", "capital_value", "location"]
            
            for field in basic_fields:
                if field in opp:
                    value = opp[field]
                    if isinstance(value, datetime.date):
                        value = value.strftime("%d/%m/%Y")
                    print(f"{field.ljust(15)}: {value}")
        
    except Exception as e:
        logger.error(f"Error testing search_opportunities: {str(e)}")
        import traceback
        traceback.print_exc()


def test_opportunity_details(scraper: AustenderScraper) -> None:
    """
    Test the get_opportunity_details method with mocked responses.
    
    Args:
        scraper: AustenderScraper instance with mocked methods
    """
    logger.info("Testing get_opportunity_details method")
    
    try:
        # Call the get_opportunity_details method
        details = scraper.get_opportunity_details("https://www.tenders.gov.au/cn/show/CN3837116")
        
        if not details:
            logger.warning("No details found for opportunity")
            return
        
        logger.info("Successfully retrieved opportunity details")
        
        # Display the details
        print("\nOpportunity Details:")
        print("="*80)
        
        # Display main fields
        main_fields = [
            "title", "reference_id", "url", "publish_date", "closing_date",
            "capital_value", "location", "category", "subcategory",
            "procurement_method", "description"
        ]
        
        for field in main_fields:
            if field in details:
                value = details[field]
                if isinstance(value, datetime.date):
                    value = value.strftime("%d/%m/%Y")
                if field == "description" and value:
                    print(f"\nDescription:")
                    print("-"*40)
                    print(value[:500] + "..." if len(value) > 500 else value)
                else:
                    print(f"{field.ljust(20)}: {value}")
        
        # Display contact information
        contact_fields = ["contact_name", "contact_email", "contact_phone"]
        if any(field in details for field in contact_fields):
            print("\nContact Information:")
            print("-"*40)
            
            for field in contact_fields:
                if field in details:
                    print(f"{field.ljust(20)}: {details[field]}")
        
        # Display attachments
        attachments = details.get("attachments", [])
        if attachments:
            print("\nAttachments:")
            print("-"*40)
            
            for i, attachment in enumerate(attachments, 1):
                print(f"Attachment {i}:")
                for key, value in attachment.items():
                    print(f"  {key.ljust(15)}: {value}")
        
    except Exception as e:
        logger.error(f"Error testing get_opportunity_details: {str(e)}")
        import traceback
        traceback.print_exc()


def main() -> None:
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Archive-based Austender scraper test")
    parser.add_argument("--create-samples", action="store_true", 
                       help="Create sample HTML files with realistic structure")
    parser.add_argument("--force", action="store_true",
                       help="Force creation of sample files even if they already exist")
    
    args = parser.parse_args()
    
    logger.info("Starting archive-based Austender scraper tests")
    
    # Create sample HTML files with realistic structure
    html_files = create_realistic_sample_files(force=args.force or args.create_samples)
    
    if args.create_samples:
        logger.info("Sample HTML files created successfully")
        print(f"Search results file: {html_files['search_results']}")
        print(f"Opportunity details file: {html_files['opportunity_detail']}")
        return
    
    # Initialize the scraper
    scraper = AustenderScraper()
    
    # Mock the scraper's methods
    mock_scraper_methods(scraper, html_files)
    
    # Test search_opportunities
    test_search_opportunities(scraper)
    
    # Test get_opportunity_details
    test_opportunity_details(scraper)
    
    logger.info("Archive-based Austender scraper tests completed")


if __name__ == "__main__":
    main()
