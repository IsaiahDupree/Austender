"""
Tests for the document analyzer module.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.document_analyzer import DocumentAnalyzer


class TestDocumentAnalyzer(unittest.TestCase):
    """Test cases for the DocumentAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = DocumentAnalyzer()
    
    def test_init(self):
        """Test the initialization of the analyzer."""
        self.assertIsNotNone(self.analyzer)
    
    @patch('utils.document_analyzer.openai.OpenAI')
    def test_analyze_with_openai_summarize(self, mock_openai):
        """Test the analyze_with_openai method with summarize task."""
        # Set up the mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Summary of the document"
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]
        
        mock_usage = MagicMock()
        mock_usage.total_tokens = 100
        mock_completion.usage = mock_usage
        
        # Call the method
        result = self.analyzer.analyze_with_openai("Test document content", task="summarize")
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], "Summary of the document")
        self.assertEqual(result["tokens_used"], 100)
        
        # Verify the mock was called correctly
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('utils.document_analyzer.openai.OpenAI')
    def test_analyze_with_openai_extract_info(self, mock_openai):
        """Test the analyze_with_openai method with extract_info task."""
        # Set up the mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "project_scope": "Construction of a building",
            "estimated_value": 1000000,
            "project_duration": "12 months",
            "key_requirements": ["Requirement 1", "Requirement 2"],
            "special_conditions": "None",
            "evaluation_criteria": "Best value for money"
        })
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]
        
        mock_usage = MagicMock()
        mock_usage.total_tokens = 150
        mock_completion.usage = mock_usage
        
        # Call the method
        result = self.analyzer.analyze_with_openai("Test document content", task="extract_info")
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result["extracted_info"]["project_scope"], "Construction of a building")
        self.assertEqual(result["tokens_used"], 150)
        
        # Verify the mock was called correctly
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('utils.document_analyzer.requests.post')
    def test_analyze_with_perplexity(self, mock_post):
        """Test the analyze_with_perplexity method."""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-id",
            "model": "perplexity-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Perplexity response content"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Call the method
        result = self.analyzer.analyze_with_perplexity("Test query")
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "test-id")
        
        # Verify the mock was called correctly
        mock_post.assert_called_once()
    
    @patch('utils.document_analyzer.requests.post')
    def test_crawl_with_firecrawl(self, mock_post):
        """Test the crawl_with_firecrawl method."""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "url": "https://test-url.com",
            "pages": [
                {
                    "url": "https://test-url.com",
                    "title": "Test Page",
                    "text": "Test page content"
                }
            ],
            "resources": [
                {
                    "url": "https://test-url.com/document.pdf",
                    "type": "pdf",
                    "filename": "document.pdf"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Call the method
        result = self.analyzer.crawl_with_firecrawl("https://test-url.com")
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")
        
        # Verify the mock was called correctly
        mock_post.assert_called_once()


if __name__ == '__main__':
    unittest.main()
