"""
Document Analyzer Module

This module handles the analysis of opportunity documents using AI services:
- OpenAI for general document understanding and structuring
- Perplexity for detailed research and information extraction
- Firecrawl for web crawling and document discovery
"""

import os
import logging
import json
import openai
import tempfile
from typing import Dict, Any, List, Optional
import requests
from datetime import datetime

from config.config import OPENAI_API_KEY, PERPLEXITY_API_KEY, FIRECRAWL_API_KEY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/document_analyzer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("document_analyzer")

# Set API keys
openai.api_key = OPENAI_API_KEY


class DocumentAnalyzer:
    """Class for analyzing documents using various AI services."""
    
    def __init__(self):
        """Initialize the document analyzer."""
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.perplexity_api_key = PERPLEXITY_API_KEY
        self.firecrawl_api_key = FIRECRAWL_API_KEY
    
    def analyze_with_openai(self, text: str, task: str = "summarize") -> Dict[str, Any]:
        """
        Analyze text using OpenAI.
        
        Args:
            text (str): The text to analyze
            task (str): The analysis task (summarize, extract_info, etc.)
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            if task == "summarize":
                return self._openai_summarize(text)
            elif task == "extract_info":
                return self._openai_extract_info(text)
            else:
                logger.warning(f"Unknown OpenAI analysis task: {task}")
                return {"error": f"Unknown task: {task}"}
        except Exception as e:
            logger.error(f"Error in OpenAI analysis: {str(e)}")
            return {"error": str(e)}
    
    def _openai_summarize(self, text: str) -> Dict[str, Any]:
        """
        Summarize text using OpenAI.
        
        Args:
            text (str): The text to summarize
            
        Returns:
            Dict[str, Any]: Summary results
        """
        try:
            # Truncate if too long
            if len(text) > 15000:
                text = text[:15000] + "..."
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert in government construction projects. "
                                              "Provide a concise summary of the following opportunity document, "
                                              "focusing on key details that would be relevant to construction companies."},
                    {"role": "user", "content": text}
                ],
                max_tokens=500
            )
            
            return {
                "summary": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens
            }
        except Exception as e:
            logger.error(f"Error in OpenAI summarization: {str(e)}")
            return {"error": str(e)}
    
    def _openai_extract_info(self, text: str) -> Dict[str, Any]:
        """
        Extract structured information from text using OpenAI.
        
        Args:
            text (str): The text to extract information from
            
        Returns:
            Dict[str, Any]: Extracted information
        """
        try:
            # Truncate if too long
            if len(text) > 15000:
                text = text[:15000] + "..."
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert in government construction projects. "
                                              "Extract the following information in JSON format: "
                                              "project_scope, estimated_value, project_duration, "
                                              "key_requirements, special_conditions, evaluation_criteria."},
                    {"role": "user", "content": text}
                ],
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            return {
                "extracted_info": json.loads(response.choices[0].message.content),
                "tokens_used": response.usage.total_tokens
            }
        except Exception as e:
            logger.error(f"Error in OpenAI information extraction: {str(e)}")
            return {"error": str(e)}
    
    def analyze_with_perplexity(self, query: str) -> Dict[str, Any]:
        """
        Analyze a query using Perplexity API.
        
        Args:
            query (str): The query to analyze
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "query": query,
                "focus": "government construction opportunities",
                "stream": False
            }
            
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                return {"error": f"Perplexity API error: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error in Perplexity analysis: {str(e)}")
            return {"error": str(e)}
    
    def crawl_with_firecrawl(self, url: str, depth: int = 1) -> Dict[str, Any]:
        """
        Crawl a URL using Firecrawl API.
        
        Args:
            url (str): The URL to crawl
            depth (int): Crawling depth
            
        Returns:
            Dict[str, Any]: Crawling results
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.firecrawl_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "url": url,
                "depth": depth,
                "extract_text": True,
                "download_resources": ["pdf", "docx"]
            }
            
            response = requests.post(
                "https://api.firecrawl.dev/v1/crawl",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Firecrawl API error: {response.status_code} - {response.text}")
                return {"error": f"Firecrawl API error: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error in Firecrawl crawling: {str(e)}")
            return {"error": str(e)}
    
    def analyze_opportunity(self, opportunity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an opportunity using multiple AI services.
        
        Args:
            opportunity_data (Dict[str, Any]): Opportunity data including description and attachments
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        results = {
            "opportunity_id": opportunity_data.get("reference_id"),
            "timestamp": datetime.now().isoformat(),
            "analyses": {}
        }
        
        # Analyze description with OpenAI
        if opportunity_data.get("description"):
            summary = self.analyze_with_openai(
                opportunity_data["description"], 
                task="summarize"
            )
            
            extracted_info = self.analyze_with_openai(
                opportunity_data["description"], 
                task="extract_info"
            )
            
            results["analyses"]["description"] = {
                "summary": summary.get("summary"),
                "extracted_info": extracted_info.get("extracted_info")
            }
        
        # Research additional information with Perplexity
        if opportunity_data.get("title") and opportunity_data.get("reference_id"):
            query = f"Provide detailed information about government construction opportunity: {opportunity_data['title']} (ID: {opportunity_data['reference_id']})"
            perplexity_results = self.analyze_with_perplexity(query)
            
            if "error" not in perplexity_results:
                results["analyses"]["additional_research"] = perplexity_results
        
        # Crawl opportunity URL with Firecrawl if available
        if opportunity_data.get("url"):
            crawl_results = self.crawl_with_firecrawl(opportunity_data["url"])
            
            if "error" not in crawl_results:
                results["analyses"]["crawl_results"] = crawl_results
        
        return results

# Example usage
if __name__ == "__main__":
    analyzer = DocumentAnalyzer()
    
    # Test with a sample opportunity
    sample_opportunity = {
        "reference_id": "TEST-2023-001",
        "title": "Construction of Government Office Building",
        "description": "This project involves the construction of a 3-story government office building...",
        "url": "https://www.tenders.gov.au/example/opportunity"
    }
    
    results = analyzer.analyze_opportunity(sample_opportunity)
    print(json.dumps(results, indent=2))
