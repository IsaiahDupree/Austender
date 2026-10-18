#!/usr/bin/env python
"""
Multi-Tool Integration Module for Austender Browser
Integrates multiple tools for maximum efficiency and anti-bot protection
"""

import os
import json
import asyncio
import logging
import random
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("multi_tool")

class ToolIntegration:
    """Integrates multiple tools for enhanced web automation"""
    
    def __init__(self):
        """Initialize the tool integration"""
        self.tools = {}
        self.current_tool = None
        
    def register_tool(self, name: str, tool: Any) -> None:
        """Register a tool with the integration manager"""
        self.tools[name] = tool
        logger.info(f"Registered tool: {name}")
    
    def select_tool(self, task_type: str) -> str:
        """Select the best tool for a given task type"""
        tool_mapping = {
            "navigation": "playwright",  # General navigation
            "login": "browser_use",      # Login with anti-bot protection
            "search": "playwright",      # Search functionality
            "extraction": "firecrawl",   # Data extraction
            "analysis": "openai",        # Content analysis
            "interaction": "stagehand"   # Human-like interaction
        }
        
        # Select the appropriate tool with some intelligence to avoid errors
        # First check if the preferred tool is available and supports this task type
        preferred_tool = tool_mapping.get(task_type, "playwright")
        
        # For analysis tasks, always use OpenAI if available
        if task_type == "analysis" and "openai" in self.tools:
            return "openai"
            
        # Add some randomness to vary behavior (but with validation)
        if random.random() < 0.2:  # 20% chance to vary from the default
            available_tools = []
            for tool_name in self.tools.keys():
                # Only include tools that might support this task
                if tool_name == "openai" and task_type == "analysis":
                    available_tools.append(tool_name)
                elif tool_name == "playwright" and task_type in ["navigation", "interaction", "extraction"]:
                    available_tools.append(tool_name)
                elif tool_name == "browser_use" and task_type in ["login", "interaction"]:
                    available_tools.append(tool_name)
                elif tool_name == "firecrawl" and task_type == "extraction":
                    available_tools.append(tool_name)
                elif tool_name == "stagehand" and task_type == "interaction":
                    available_tools.append(tool_name)
            
            if available_tools:
                selected = random.choice(available_tools)
                logger.info(f"Randomly selected {selected} for {task_type}")
                return selected
        
        # Use the default mapping
        selected_tool = tool_mapping.get(task_type, "playwright")
        
        # Ensure the tool is available
        if selected_tool not in self.tools:
            available_tools = list(self.tools.keys())
            selected_tool = available_tools[0] if available_tools else None
            logger.warning(f"Preferred tool {selected_tool} not available, using {selected_tool}")
        
        logger.info(f"Selected {selected_tool} for {task_type}")
        return selected_tool
    
    async def execute_action(self, action_type: str, params: Dict) -> Dict:
        """Execute an action using the most appropriate tool"""
        # Select the appropriate tool for this action
        task_mapping = {
            "click": "interaction",
            "input": "interaction",
            "select": "interaction",
            "navigate": "navigation",
            "wait": "navigation",
            "extract": "extraction",
            "analyze": "analysis",
            "login": "login"
        }
        
        task_type = task_mapping.get(action_type, "interaction")
        tool_name = self.select_tool(task_type)
        
        if not tool_name or tool_name not in self.tools:
            logger.error(f"No suitable tool found for {action_type}")
            return {"success": False, "error": "No suitable tool found"}
        
        # Get the tool and execute the action
        tool = self.tools[tool_name]
        self.current_tool = tool_name
        
        # Add anti-bot measures
        if action_type in ["click", "input", "select"]:
            # Add random delay for human-like interaction
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Vary mouse movement if supported by the tool
            if hasattr(tool, "move_mouse_randomly") and random.random() < 0.3:
                await tool.move_mouse_randomly()
        
        # Execute the action with the selected tool
        try:
            method_name = f"execute_{action_type}"
            if hasattr(tool, method_name):
                method = getattr(tool, method_name)
                result = await method(**params)
            elif hasattr(tool, "execute_action"):
                result = await tool.execute_action(action_type, params)
            else:
                logger.error(f"Tool {tool_name} does not support {action_type}")
                return {"success": False, "error": f"Tool {tool_name} does not support {action_type}"}
            
            logger.info(f"Executed {action_type} with {tool_name}")
            return {"success": True, "result": result, "tool": tool_name}
            
        except Exception as e:
            logger.error(f"Error executing {action_type} with {tool_name}: {str(e)}")
            return {"success": False, "error": str(e), "tool": tool_name}
    
    async def analyze_page(self, page_content: Dict, task: str) -> Dict:
        """Analyze page content using the best available tool"""
        tool_name = self.select_tool("analysis")
        
        if tool_name not in self.tools:
            logger.error("No analysis tool available")
            return {"success": False, "error": "No analysis tool available"}
        
        tool = self.tools[tool_name]
        
        try:
            if hasattr(tool, "analyze_page"):
                result = await tool.analyze_page(page_content, task)
            elif hasattr(tool, "analyze"):
                result = await tool.analyze(page_content, task)
            else:
                logger.error(f"Tool {tool_name} does not support page analysis")
                return {"success": False, "error": f"Tool {tool_name} does not support page analysis"}
            
            logger.info(f"Analyzed page with {tool_name}")
            return {"success": True, "result": result, "tool": tool_name}
            
        except Exception as e:
            logger.error(f"Error analyzing page with {tool_name}: {str(e)}")
            return {"success": False, "error": str(e), "tool": tool_name}
    
    async def extract_data(self, page_content: Dict, extraction_params: Dict) -> Dict:
        """Extract data using the best available tool"""
        tool_name = self.select_tool("extraction")
        
        if tool_name not in self.tools:
            logger.error("No extraction tool available")
            return {"success": False, "error": "No extraction tool available"}
        
        tool = self.tools[tool_name]
        
        try:
            if hasattr(tool, "extract_data"):
                result = await tool.extract_data(page_content, extraction_params)
            elif hasattr(tool, "extract"):
                result = await tool.extract(page_content, extraction_params)
            else:
                logger.error(f"Tool {tool_name} does not support data extraction")
                return {"success": False, "error": f"Tool {tool_name} does not support data extraction"}
            
            logger.info(f"Extracted data with {tool_name}")
            return {"success": True, "result": result, "tool": tool_name}
            
        except Exception as e:
            logger.error(f"Error extracting data with {tool_name}: {str(e)}")
            return {"success": False, "error": str(e), "tool": tool_name}

# The tool integration can be used as follows:
# 1. Create specific tool adapters for each tool (Playwright, Browser-Use, etc.)
# 2. Register these adapters with the ToolIntegration class
# 3. Use the ToolIntegration to execute actions, allowing it to select the best tool
