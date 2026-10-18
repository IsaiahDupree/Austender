"""
Security Module

This module provides security features for the application including:
- API key validation
- Rate limiting
- Request authentication
- Input validation
"""

import time
import hashlib
import hmac
import base64
import secrets
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, List, Any, Union

from fastapi import HTTPException, Request, Depends, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, validator

# Import logging configuration
from utils.logging_config import setup_logging

# Set up logger
logger = setup_logging(__name__)


class RateLimiter:
    """Rate limiter implementation using a simple in-memory store."""
    
    def __init__(self, rate_limit: int = 60, time_window: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            rate_limit (int): Maximum number of requests allowed in the time window
            time_window (int): Time window in seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.requests = {}  # {ip: [(timestamp, endpoint), ...]}
    
    def check_rate_limit(self, ip: str, endpoint: str) -> bool:
        """
        Check if a request from the given IP to the endpoint should be rate limited.
        
        Args:
            ip (str): IP address of the requester
            endpoint (str): API endpoint being accessed
            
        Returns:
            bool: True if request is allowed, False if it should be rate limited
        """
        now = time.time()
        
        # Initialize client's request history if not present
        if ip not in self.requests:
            self.requests[ip] = []
        
        # Remove requests outside the time window
        self.requests[ip] = [req for req in self.requests[ip] 
                            if now - req[0] < self.time_window]
        
        # Check if client has exceeded rate limit
        if len(self.requests[ip]) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for IP: {ip}, endpoint: {endpoint}")
            return False
        
        # Add current request to history
        self.requests[ip].append((now, endpoint))
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


# API Key validation
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def validate_api_key(api_key: str = Depends(api_key_header)) -> str:
    """
    Validate the API key from the request header.
    
    Args:
        api_key (str): API key from the request header
        
    Returns:
        str: API key if valid
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    # In a real application, you would check the API key against a database
    # For now, we'll use a simple check against the environment variable
    from config.config import API_KEY
    
    if not api_key:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "APIKey"},
        )
    
    if API_KEY and api_key == API_KEY:
        return api_key
    
    logger.warning(f"Invalid API key provided: {api_key[:5]}...")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "APIKey"},
    )


async def rate_limit_dependency(request: Request) -> None:
    """
    Rate limiting dependency for FastAPI endpoints.
    
    Args:
        request (Request): FastAPI request object
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    client_ip = request.client.host
    endpoint = request.url.path
    
    if not rate_limiter.check_rate_limit(client_ip, endpoint):
        logger.warning(f"Rate limit exceeded for {client_ip} on {endpoint}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )


class InputSanitizer:
    """Utility class for sanitizing user input."""
    
    @staticmethod
    def sanitize_string(input_str: Optional[str]) -> Optional[str]:
        """
        Sanitize a string input to prevent injection attacks.
        
        Args:
            input_str (Optional[str]): Input string to sanitize
            
        Returns:
            Optional[str]: Sanitized string or None if input is None
        """
        if input_str is None:
            return None
        
        # Remove potential script tags and other dangerous patterns
        sanitized = re.sub(r'<script.*?>.*?</script>', '', input_str, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'<.*?javascript:.*?>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'<.*?\s+on\w+=["\'].*?["\'"].*?>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        return sanitized
    
    @staticmethod
    def sanitize_dict(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize all string values in a dictionary.
        
        Args:
            input_dict (Dict[str, Any]): Dictionary with values to sanitize
            
        Returns:
            Dict[str, Any]: Dictionary with sanitized string values
        """
        sanitized_dict = {}
        
        for key, value in input_dict.items():
            if isinstance(value, str):
                sanitized_dict[key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized_dict[key] = InputSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized_dict[key] = [
                    InputSanitizer.sanitize_string(item) if isinstance(item, str)
                    else item for item in value
                ]
            else:
                sanitized_dict[key] = value
        
        return sanitized_dict


# Function to generate a secure random API key
def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.
    
    Args:
        length (int): Length of the API key in bytes
        
    Returns:
        str: Generated API key
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode('utf-8').rstrip('=')


# HMAC Signature validation
def verify_hmac_signature(payload: str, signature: str, secret_key: str) -> bool:
    """
    Verify an HMAC signature for a payload.
    
    Args:
        payload (str): The payload that was signed
        signature (str): The signature to verify
        secret_key (str): Secret key used for signing
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    computed_signature = hmac.new(
        secret_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, signature)
