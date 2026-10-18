"""
Logging Configuration Module

This module provides a centralized configuration for logging across the application.
It ensures consistent logging format, rotation, and levels across different components.
"""

import os
import logging
import logging.handlers
from pathlib import Path

from config.config import LOG_LEVEL, LOG_FORMAT, LOG_FILE


def setup_logging(name, log_file=None):
    """
    Set up logging configuration for a module.
    
    Args:
        name (str): Name of the logger, typically __name__ from the calling module
        log_file (str, optional): Specific log file for this logger. If None, uses the component name.
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Determine log file path
    if log_file is None:
        # Extract component name from the logger name (e.g., 'scrapers.austender_scraper' -> 'scrapers')
        parts = name.split('.')
        component = parts[0] if parts else name
        log_file = os.path.join(logs_dir, f"{component}.log")
    else:
        log_file = os.path.join(logs_dir, log_file)
    
    # Set up logger with the specified name
    logger = logging.getLogger(name)
    
    # Only configure if the logger doesn't already have handlers
    if not logger.handlers:
        # Convert log level string to numeric value
        level = getattr(logging, LOG_LEVEL, logging.INFO)
        logger.setLevel(level)
        
        # File handler with rotation (5 MB per file, keep 5 backup files)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger


# Set up root logger
def setup_root_logger():
    """Set up the root logger configuration."""
    root_logger = logging.getLogger()
    
    # Only configure if the logger doesn't already have handlers
    if not root_logger.handlers:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Convert log level string to numeric value
        level = getattr(logging, LOG_LEVEL, logging.INFO)
        root_logger.setLevel(level)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, 
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        
        # Add handlers to logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    return root_logger
