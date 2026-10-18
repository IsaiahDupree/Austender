"""
Tests for the Austender scraper module.
"""

import unittest
from unittest.mock import patch, MagicMock
import datetime
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.austender_scraper import AustenderScraper


class TestAustenderScraper(unittest.TestCase):
    """Test cases for the AustenderScraper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scraper = AustenderScraper()
    
    def test_init(self):
        """Test the initialization of the scraper."""
        self.assertIsNotNone(self.scraper)
        self.assertEqual(self.scraper.base_url, "https://www.tenders.gov.au")
        self.assertIsNotNone(self.scraper.session)
    
    @patch('scrapers.austender_scraper.requests.Session.get')
    def test_get_page(self, mock_get):
        """Test the get_page method."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = "<html><body><div>Test Content</div></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.scraper.get_page("https://test-url.com")
        
        # Assertions
        mock_get.assert_called_once_with("https://test-url.com", timeout=30)
        self.assertIsNotNone(result)
        self.assertEqual(result.find('div').text, "Test Content")
    
    def test_parse_date(self):
        """Test the _parse_date method."""
        # Test with DD/MM/YYYY format
        date_str = "15/06/2023"
        result = self.scraper._parse_date(date_str)
        self.assertEqual(result, datetime.date(2023, 6, 15))
        
        # Test with DD MMM YYYY format
        date_str = "15 Jun 2023"
        result = self.scraper._parse_date(date_str)
        self.assertEqual(result, datetime.date(2023, 6, 15))
        
        # Test with invalid date
        date_str = "invalid-date"
        result = self.scraper._parse_date(date_str)
        self.assertIsNone(result)
    
    def test_parse_value(self):
        """Test the _parse_value method."""
        # Test with currency symbol
        value_str = "$100,000.00"
        result = self.scraper._parse_value(value_str)
        self.assertEqual(result, 100000.0)
        
        # Test with range
        value_str = "100,000 - 200,000"
        result = self.scraper._parse_value(value_str)
        self.assertEqual(result, 150000.0)
        
        # Test with currency code
        value_str = "100,000 AUD"
        result = self.scraper._parse_value(value_str)
        self.assertEqual(result, 100000.0)
        
        # Test with invalid value
        value_str = "invalid-value"
        result = self.scraper._parse_value(value_str)
        self.assertIsNone(result)
    
    @patch('scrapers.austender_scraper.AustenderScraper.get_page')
    def test_search_opportunities(self, mock_get_page):
        """Test the search_opportunities method."""
        # Mock the _parse_search_results method
        with patch.object(self.scraper, '_parse_search_results') as mock_parse:
            # Set up the mock return values
            mock_get_page.return_value = "<html><body></body></html>"
            mock_parse.return_value = [
                {
                    "title": "Test Opportunity",
                    "reference_id": "TEST-2023-001",
                    "url": "https://www.tenders.gov.au/test",
                    "publish_date": datetime.date(2023, 1, 1),
                    "closing_date": datetime.date(2023, 2, 1),
                    "capital_value": 100000.0,
                    "location": "Test Location"
                }
            ]
            
            # Call the method
            result = self.scraper.search_opportunities(
                category="construction",
                keyword="test",
                location="Sydney",
                date_from=datetime.date(2023, 1, 1),
                date_to=datetime.date(2023, 12, 31),
                min_value=50000.0,
                max_value=500000.0,
                page=1
            )
            
            # Assertions
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["title"], "Test Opportunity")
            self.assertEqual(result[0]["reference_id"], "TEST-2023-001")


if __name__ == '__main__':
    unittest.main()
