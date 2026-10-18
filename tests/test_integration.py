"""
Integration tests for the Austender platform.

These tests verify that different components of the system work together correctly.
"""

import unittest
import os
import sys
import datetime
from unittest.mock import patch, MagicMock
import pytest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Opportunity, Attachment, setup_database
from scrapers.austender_scraper import AustenderScraper
from utils.document_analyzer import DocumentAnalyzer


@pytest.mark.integration
class TestIntegrationPipeline(unittest.TestCase):
    """Test the full pipeline from scraping to database storage."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use an in-memory SQLite database for testing
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        self.engine = setup_database()
        
        # Create scraper with mocked session
        self.scraper = AustenderScraper()
        
        # Create document analyzer with mocked clients
        self.analyzer = DocumentAnalyzer()
    
    @patch('scrapers.austender_scraper.requests.Session.get')
    def test_scrape_and_store(self, mock_get):
        """Test scraping opportunities and storing them in the database."""
        # Mock search results page
        search_html = """
        <html>
            <body>
                <div class="opportunity-item">
                    <div class="title"><a href="/test-opportunity">Test Construction Project</a></div>
                    <div class="reference-id">TEST-2023-001</div>
                    <div class="dates">
                        <div class="publish-date">01/06/2023</div>
                        <div class="closing-date">30/06/2023</div>
                    </div>
                    <div class="value">$1,000,000 AUD</div>
                    <div class="location">Sydney, NSW</div>
                </div>
            </body>
        </html>
        """
        
        # Mock opportunity details page
        details_html = """
        <html>
            <body>
                <h1 class="opportunity-title">Test Construction Project</h1>
                <div class="atm-id">TEST-2023-001</div>
                <div class="opportunity-description">This is a test construction project for building a government facility.</div>
                <div class="publish-date">01/06/2023</div>
                <div class="closing-date">30/06/2023</div>
                <div class="start-date">15/07/2023</div>
                <div class="estimated-value">$1,000,000 AUD</div>
                <div class="category">Construction</div>
                <div class="procurement-method">Open Tender</div>
                <div class="location">Sydney, NSW</div>
                <div class="contact-name">John Smith</div>
                <div class="contact-email">john.smith@example.gov.au</div>
                <div class="contact-phone">+61 2 1234 5678</div>
                <div class="attachment">
                    <div class="name">Project Requirements</div>
                    <a href="/documents/requirements.pdf">Download</a>
                    <div class="description">Detailed requirements for the project</div>
                </div>
            </body>
        </html>
        """
        
        # Configure the mock to return different responses based on URL
        def mock_response(url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            
            if "search" in url:
                mock_resp.text = search_html
            else:
                mock_resp.text = details_html
                
            return mock_resp
            
        mock_get.side_effect = mock_response
        
        # Execute the scraping process
        opportunities = self.scraper.search_opportunities(category="construction")
        self.assertEqual(len(opportunities), 1)
        
        # Get detailed information for the first opportunity
        opportunity_details = self.scraper.get_opportunity_details("https://example.com/opportunity")
        self.assertEqual(opportunity_details["title"], "Test Construction Project")
        
        # Save the opportunity to the database
        self.scraper.save_opportunities([opportunity_details])
        
        # Verify the opportunity was saved correctly
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=self.engine)
        
        with SessionLocal() as session:
            saved_opportunity = session.query(Opportunity).filter_by(reference_id="TEST-2023-001").first()
            
            self.assertIsNotNone(saved_opportunity)
            self.assertEqual(saved_opportunity.title, "Test Construction Project")
            self.assertEqual(saved_opportunity.source, "Austender")
            self.assertEqual(saved_opportunity.capital_value, 1000000.0)
            
            # Check that attachments were saved
            self.assertEqual(len(saved_opportunity.attachments), 1)
            self.assertEqual(saved_opportunity.attachments[0].name, "Project Requirements")
    
    @patch('utils.document_analyzer.openai.OpenAI')
    @patch('utils.document_analyzer.requests.post')
    def test_document_analysis(self, mock_post, mock_openai):
        """Test analyzing an opportunity document."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = '{"project_scope": "Test scope", "estimated_value": 1000000}'
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]
        
        mock_usage = MagicMock()
        mock_usage.total_tokens = 100
        mock_completion.usage = mock_usage
        
        # Mock Perplexity response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test-id", "choices": [{"message": {"content": "Additional research information"}}]}
        mock_post.return_value = mock_response
        
        # Test opportunity data
        opportunity_data = {
            "reference_id": "TEST-2023-001",
            "title": "Test Construction Project",
            "description": "This is a test construction project for a government facility.",
            "url": "https://example.com/opportunity"
        }
        
        # Analyze the opportunity
        analysis_results = self.analyzer.analyze_opportunity(opportunity_data)
        
        # Verify analysis results
        self.assertIn("analyses", analysis_results)
        self.assertIn("description", analysis_results["analyses"])
        
        # Verify OpenAI was called correctly
        mock_client.chat.completions.create.assert_called()
        
        # Verify Perplexity was called correctly
        mock_post.assert_called()


if __name__ == '__main__':
    unittest.main()
