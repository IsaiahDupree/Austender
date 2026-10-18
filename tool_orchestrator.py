"""
Tool Orchestrator for Austender - Multi-Tool Integration Framework
This module provides a unified interface for multiple web automation and analysis tools.
"""

import os
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('tool_orchestrator')

class Tool(ABC):
    """Base class for all tools"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f'tool.{name}')
    
    @abstractmethod
    async def setup(self):
        """Setup the tool and its dependencies"""
        pass
    
    @abstractmethod
    async def teardown(self):
        """Clean up resources used by the tool"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the tool is available for use"""
        pass

class PlaywrightTool(Tool):
    """Playwright browser automation tool"""
    
    def __init__(self):
        super().__init__('playwright')
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def setup(self):
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            
            # Configure browser with anti-bot detection measures
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Set to True in production
                slow_mo=random.randint(50, 150)  # Add random delays between actions
            )
            
            # Configure browser context with additional anti-detection settings
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent=self._get_random_user_agent(),
                locale='en-US',
                timezone_id='Australia/Sydney',
                has_touch=False,
                java_script_enabled=True,
                bypass_csp=True,
            )
            
            # Create a new page
            self.page = await self.context.new_page()
            
            # Apply additional fingerprint evasion scripts AFTER page is created
            await self._setup_fingerprint_evasion()
            
            # Set default navigation timeout
            self.page.set_default_timeout(60000)
            
            self.logger.info("Playwright tool setup successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup Playwright tool: {str(e)}")
            return False
    
    async def teardown(self):
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.logger.info("Playwright tool resources released")
            return True
        except Exception as e:
            self.logger.error(f"Error during Playwright teardown: {str(e)}")
            return False
    
    async def is_available(self) -> bool:
        try:
            from playwright.async_api import async_playwright
            return True
        except ImportError:
            return False
    
    async def _setup_fingerprint_evasion(self):
        """Setup scripts to evade fingerprinting detection"""
        if not self.page:
            self.logger.error("Cannot set up fingerprint evasion - page not initialized")
            return
            
        # Override navigator properties to appear more human-like
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            
            // Override other identifying properties
            if (typeof WebGLRenderingContext !== 'undefined') {
                const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    // Hide WebGL fingerprinting
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris Pro Graphics';
                    }
                    return originalGetParameter.call(this, parameter);
                };
            }
        """)
    
    def _get_random_user_agent(self) -> str:
        """Return a random user agent string to avoid detection"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 Edg/92.0.902.67'
        ]
        return random.choice(user_agents)

class OpenAITool(Tool):
    """OpenAI tool for content analysis and understanding"""
    
    def __init__(self):
        super().__init__('openai')
        self.client = None
        self.api_key = os.getenv('OPENAI_API_KEY')
    
    async def setup(self):
        try:
            if not self.api_key:
                self.logger.warning("OpenAI API key not found in environment variables")
                return False
                
            import openai
            from openai import OpenAI
            
            self.client = OpenAI(api_key=self.api_key)
            self.logger.info("OpenAI tool setup successfully")
            return True
        except ImportError:
            self.logger.warning("OpenAI package not installed")
            return False
        except Exception as e:
            self.logger.error(f"Failed to setup OpenAI tool: {str(e)}")
            return False
    
    async def teardown(self):
        # OpenAI client doesn't require explicit cleanup
        self.client = None
        return True
    
    async def is_available(self) -> bool:
        try:
            if not self.api_key:
                return False
                
            import openai
            return True
        except ImportError:
            return False
    
    async def analyze_page_content(self, html_content: str, task_description: str) -> Dict[str, Any]:
        """
        Use OpenAI to analyze HTML content and extract structured information
        
        Args:
            html_content: The HTML content to analyze
            task_description: Description of what to extract from the page
            
        Returns:
            Dict with structured information extracted from the page
        """
        if not self.client:
            self.logger.error("OpenAI client not initialized")
            return {}
            
        try:
            # Truncate HTML if it's too large
            if len(html_content) > 100000:
                html_content = html_content[:100000] + "... [content truncated]"
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured data from web pages. Extract only the information requested with high precision."},
                    {"role": "user", "content": f"Task: {task_description}\n\nHTML Content:\n{html_content}"}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            self.logger.info("OpenAI analysis completed successfully")
            try:
                # Try to parse as JSON first
                import json
                content = response.choices[0].message.content
                if content.startswith('```json') and content.endswith('```'):
                    content = content[7:-3]  # Remove ```json and ``` markers
                
                parsed_content = json.loads(content)
                return parsed_content
            except:
                # If not JSON, return as text
                return {"text_analysis": response.choices[0].message.content}
                
        except Exception as e:
            self.logger.error(f"Error during OpenAI analysis: {str(e)}")
            return {"error": str(e)}

class ToolOrchestrator:
    """
    Orchestrates multiple tools for web automation and data extraction
    """
    
    def __init__(self):
        self.tools = {}
        self.active_tools = {}
        self.logger = logging.getLogger('tool_orchestrator')
    
    def register_tool(self, tool: Tool):
        """Register a tool with the orchestrator"""
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")
    
    async def setup_tool(self, tool_name: str) -> bool:
        """Setup a specific tool"""
        if tool_name not in self.tools:
            self.logger.error(f"Tool not registered: {tool_name}")
            return False
            
        tool = self.tools[tool_name]
        
        # Check if tool is available
        if not await tool.is_available():
            self.logger.warning(f"Tool {tool_name} is not available")
            return False
            
        # Setup tool
        success = await tool.setup()
        if success:
            self.active_tools[tool_name] = tool
            self.logger.info(f"Tool {tool_name} is now active")
        return success
    
    async def setup_all_tools(self) -> Dict[str, bool]:
        """Setup all registered tools"""
        results = {}
        for tool_name in self.tools:
            results[tool_name] = await self.setup_tool(tool_name)
        return results
    
    async def teardown_tool(self, tool_name: str) -> bool:
        """Teardown a specific tool"""
        if tool_name not in self.active_tools:
            self.logger.warning(f"Tool {tool_name} is not active")
            return False
            
        tool = self.active_tools[tool_name]
        success = await tool.teardown()
        if success:
            del self.active_tools[tool_name]
            self.logger.info(f"Tool {tool_name} has been deactivated")
        return success
    
    async def teardown_all_tools(self) -> Dict[str, bool]:
        """Teardown all active tools"""
        results = {}
        active_tools = list(self.active_tools.keys())
        for tool_name in active_tools:
            results[tool_name] = await self.teardown_tool(tool_name)
        return results
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get an active tool by name"""
        return self.active_tools.get(tool_name)

    def get_active_tools(self) -> List[str]:
        """Get a list of all active tools"""
        return list(self.active_tools.keys())

# Example usage
async def main():
    # Create orchestrator
    orchestrator = ToolOrchestrator()
    
    # Register tools
    orchestrator.register_tool(PlaywrightTool())
    orchestrator.register_tool(OpenAITool())
    
    # Setup tools
    await orchestrator.setup_all_tools()
    
    # Use tools here...
    
    # Teardown tools
    await orchestrator.teardown_all_tools()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
