#!/usr/bin/env python
"""
OpenAI Adapter for Austender Agent
Handles intelligent analysis of page content and decision-making
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openai_adapter")

class OpenAIAdapter:
    """Adapter for OpenAI API integration"""
    
    def __init__(self, api_key=None, model="gpt-4"):
        """Initialize the OpenAI adapter"""
        from openai import AsyncOpenAI
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def initialize(self):
        """Initialize OpenAI adapter"""
        logger.info(f"OpenAI adapter initialized with model {self.model}")
        return True
    
    async def cleanup(self):
        """Clean up OpenAI adapter"""
        return True
    
    async def analyze_page(self, page_content: Dict, task: str) -> Dict:
        """Use OpenAI to analyze a page and determine next steps"""
        # Build system prompt with Austender-specific knowledge
        system_prompt = """
        You are an expert web automation agent specialized in navigating the Australian Government's AusTender website.
        Your task is to understand the current page and suggest the next precise actions to accomplish the user's task.
        
        Important details about AusTender website:
        1. The site uses Drupal as its CMS and has forms for searching procurement opportunities
        2. The main sections include: Home, Approaches to Market (ATM), Contract Notices, and Agency Resources
        3. The ATM search page allows filtering by keyword, category, date, agency, etc.
        4. The Advanced Search page has multiple filters including:
           - Keywords (free text)
           - ATM Type (dropdown)
           - Category (multi-select)
           - State/Territory selection
           - Date range filters
        5. Tables of results show procurement opportunities with ID numbers, titles, categories, etc.
        6. Pagination controls are typically at the bottom of result pages
        
        Guidelines for effective automation:
        1. Be precise with selectors - provide multiple selector alternatives when possible
        2. Focus on visible, interactive elements in the viewport first
        3. For search forms, identify the proper input fields and submit buttons
        4. Use page context to determine where you are in the workflow
        5. When extracting data from tables, identify the correct table rows and columns
        6. For pagination, look for next/previous links or page number indicators
        7. Be aware of anti-bot measures and use human-like interactions
        
        This is an agentic automation system with real impact - be precise and thoughtful.
        """
        
        # Extract interactive elements safely
        interactive_elements = page_content.get("interactive_elements", [])
        
        # Limit to the first 10 elements to save tokens
        interactive_elements = interactive_elements[:10]
        
        # Simplify selectors to save tokens
        for element in interactive_elements:
            if "selectors" in element and len(element["selectors"]) > 2:
                element["selectors"] = element["selectors"][:2]
        
        interactive_elements_json = json.dumps(interactive_elements, indent=2)
        
        # Determine page context
        page_context = "unknown"
        if (page_content.get("page_structure") and 
            "austender_specific" in page_content["page_structure"] and
            "page_context" in page_content["page_structure"]["austender_specific"]):
            page_context = page_content["page_structure"]["austender_specific"]["page_context"]
        
        # Extract table data if available
        table_summary = ""
        tables = page_content.get("tables", [])
        if tables and len(tables) > 0:
            table_summary = "Tables found on page:\n"
            for i, table in enumerate(tables):
                headers = table.get("headers", [])
                rows = table.get("rows", [])
                table_summary += f"Table {i+1}:\n"
                table_summary += f"  Headers: {headers}\n"
                table_summary += f"  Row count: {len(rows)}\n"
                if rows and len(rows) > 0:
                    table_summary += f"  Sample row: {rows[0]}\n"
        
        # Build user prompt
        user_prompt = f"""
        Task: {task}

        Current page information:
        Title: {page_content.get('title', 'Unknown Title')}
        URL: {page_content.get('url', 'Unknown URL')}
        Page Context: {page_context}
        
        {table_summary}
        
        Interactive Elements (top 10):
        {interactive_elements_json}
        
        Based on the current page state and the task, analyze and suggest up to 3 concrete actions I should take next.
        For each action, provide:
        1. Action type (click, input, select, wait, extract)
        2. Selector to use (provide the most reliable one)
        3. Value to input (if applicable)
        4. A clear explanation of why this action is appropriate
        
        If this is a results page and we need to extract data, please identify the table rows and provide instructions for extraction.
        
        Format your response as a JSON list of actions:
        [
          {
            "action": "click|input|select|wait|extract",
            "selector": "css_selector",
            "value": "input value if needed",
            "explanation": "Why this action helps accomplish the task"
          }
        ]
        
        Only include the JSON output.
        """
        
        # Call OpenAI API with multiple retries for resilience
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"OpenAI API call attempt {attempt+1}/{max_retries}")
                
                # Set a reasonable timeout
                completion = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.2
                    ),
                    timeout=30  # 30 second timeout
                )
                
                response_text = completion.choices[0].message.content
                
                # Parse the JSON response
                try:
                    actions = json.loads(response_text)
                    logger.info(f"OpenAI analysis complete, suggested {len(actions)} actions")
                    return {"success": True, "actions": actions}
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                    
                    # Try to extract JSON from the response
                    import re
                    json_match = re.search(r'\[\s*{.*}\s*\]', response_text, re.DOTALL)
                    if json_match:
                        try:
                            extracted_json = json_match.group(0)
                            actions = json.loads(extracted_json)
                            logger.info(f"Extracted JSON from response, found {len(actions)} actions")
                            return {"success": True, "actions": actions}
                        except json.JSONDecodeError:
                            pass
                    
                    # If we've tried all attempts, return fallback actions
                    if attempt == max_retries - 1:
                        fallback_actions = [
                            {
                                "action": "wait",
                                "selector": "",
                                "value": "3",
                                "explanation": "Waiting for the page to stabilize after failure to parse OpenAI response"
                            }
                        ]
                        return {"success": False, "error": "Failed to parse OpenAI response", "fallback_actions": fallback_actions}
                    
                    # Wait before retrying
                    await asyncio.sleep(retry_delay)
                    
            except asyncio.TimeoutError:
                logger.error(f"OpenAI API call timed out (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Error calling OpenAI API (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    # If we've exhausted all retries, use rule-based fallback
                    return self._rule_based_fallback(page_content, task)
        
        # If we get here, all retries failed
        return self._rule_based_fallback(page_content, task)
    
    def _rule_based_fallback(self, page_content: Dict, task: str) -> Dict:
        """Rule-based fallback when OpenAI API fails"""
        logger.info("Using rule-based fallback for page analysis")
        
        url = page_content.get('url', '').lower()
        title = page_content.get('title', '').lower()
        interactive_elements = page_content.get('interactive_elements', [])
        
        # Default action is to wait
        fallback_actions = [
            {
                "action": "wait",
                "selector": "",
                "value": "5",
                "explanation": "Error recovery: waiting before next action"
            }
        ]
        
        # Check if we're on the homepage
        if 'tenders.gov.au' in url and ('home' in title.lower() or url.endswith('/')):
            # Look for ATM link
            for element in interactive_elements:
                if any(term in element.get('text', '').lower() for term in ['atm', 'approach', 'market']):
                    return {
                        "success": True, 
                        "actions": [{
                            "action": "click",
                            "selector": element.get('selectors', [''])[0] if element.get('selectors') else "",
                            "value": "",
                            "explanation": "Clicking on Approaches to Market link to access search functionality"
                        }]
                    }
            
            # If ATM link not found, look for search link
            for element in interactive_elements:
                if 'search' in element.get('text', '').lower():
                    return {
                        "success": True, 
                        "actions": [{
                            "action": "click",
                            "selector": element.get('selectors', [''])[0] if element.get('selectors') else "",
                            "value": "",
                            "explanation": "Clicking on Search link to access search functionality"
                        }]
                    }
        
        # Check if we're on a search page
        elif 'search' in url or 'search' in title.lower():
            # Find a text input field
            for element in interactive_elements:
                if element.get('type', '').startswith('input') and 'text' in element.get('type', ''):
                    # Look for task-relevant terms
                    search_terms = ""
                    if 'bridge' in task.lower() and 'construction' in task.lower():
                        search_terms = "bridge construction"
                    elif 'construction' in task.lower():
                        search_terms = "construction"
                    elif 'bridge' in task.lower():
                        search_terms = "bridge"
                    
                    if search_terms:
                        return {
                            "success": True, 
                            "actions": [{
                                "action": "input",
                                "selector": element.get('selectors', [''])[0] if element.get('selectors') else "",
                                "value": search_terms,
                                "explanation": f"Entering search terms '{search_terms}' from the task"
                            }]
                        }
        
        # Check if we're on a results page
        elif 'result' in title.lower() or any('result' in element.get('text', '').lower() for element in interactive_elements[:5]):
            # Look for table rows to extract
            table_selectors = ['table tr', 'tr', '.view-content .views-row', '.result-item']
            
            for selector in table_selectors:
                return {
                    "success": True, 
                    "actions": [{
                        "action": "extract",
                        "selector": selector,
                        "value": "",
                        "explanation": "Extracting search results from the table"
                    }]
                }
        
        # Return default fallback action
        return {"success": True, "actions": fallback_actions}
    
    async def process_extraction(self, extracted_data: List[Dict], task: str) -> Dict:
        """Process and analyze extracted data"""
        if not extracted_data:
            return {"success": False, "error": "No data to process"}
        
        # Format the extracted data for analysis
        data_json = json.dumps(extracted_data[:20], indent=2)  # Limit to first 20 items
        
        system_prompt = """
        You are an expert data analyst specialized in processing procurement data from the Australian Government's AusTender website.
        Your task is to analyze extracted data and identify the most relevant items matching the user's task.
        
        Important details about AusTender data:
        1. ATM (Approach to Market) listings contain details about procurement opportunities
        2. Key fields include ID numbers, titles, categories, agencies, dates, and locations
        3. Construction opportunities are typically categorized under "Building and Construction"
        4. State/territory information may be abbreviated (NSW, QLD, VIC, etc.)
        
        Provide a concise analysis of the data focusing on:
        1. How many items match the search criteria
        2. The most relevant matches based on the task
        3. Any patterns or insights from the data
        4. Recommended next steps
        
        Format your analysis in a structured way and keep it concise.
        """
        
        user_prompt = f"""
        Task: {task}
        
        Extracted Data:
        {data_json}
        
        Please analyze this data to identify the most relevant items matching the task.
        Provide insights about the data and recommend any next steps.
        
        Format your response as JSON with the following structure:
        {{
          "analysis": "Your overall analysis of the data",
          "relevant_items": [List of indexes or IDs of the most relevant items],
          "patterns": ["Any patterns or insights from the data"],
          "next_steps": ["Recommended next steps"]
        }}
        
        Only include the JSON output.
        """
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            response_text = completion.choices[0].message.content
            
            # Parse the JSON response
            try:
                analysis = json.loads(response_text)
                logger.info(f"OpenAI data analysis complete")
                return {"success": True, "analysis": analysis}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'{.*}', response_text, re.DOTALL)
                if json_match:
                    try:
                        extracted_json = json_match.group(0)
                        analysis = json.loads(extracted_json)
                        logger.info(f"Extracted JSON from response")
                        return {"success": True, "analysis": analysis}
                    except json.JSONDecodeError:
                        pass
                
                return {"success": False, "error": "Failed to parse OpenAI response"}
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return {"success": False, "error": f"Error calling OpenAI API: {str(e)}"}
            
    async def execute_action(self, action_type: str, params: Dict) -> Dict:
        """OpenAI adapter doesn't directly execute actions but can process results"""
        logger.warning(f"OpenAI adapter cannot directly execute {action_type} actions")
        return {"success": False, "error": f"OpenAI adapter cannot directly execute {action_type} actions"}
