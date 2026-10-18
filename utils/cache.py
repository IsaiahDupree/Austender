"""
Caching Module

This module provides a caching mechanism to improve performance by storing 
frequently accessed data and computational results in memory.
"""

import time
import threading
import functools
import json
from typing import Dict, Any, Optional, Callable, Tuple, List, Union
import hashlib
from datetime import datetime, timedelta

# Import logging configuration
from utils.logging_config import setup_logging

# Set up logger
logger = setup_logging(__name__)


class Cache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize the cache.
        
        Args:
            default_ttl (int): Default time-to-live in seconds (default: 5 minutes)
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}  # {key: (value, expiry_time)}
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        
        # Start a background thread to clean expired entries
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_expired_entries, 
            daemon=True
        )
        self._running = True
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key (str): Cache key
            
        Returns:
            Optional[Any]: Cached value or None if not found or expired
        """
        with self._lock:
            if key in self._cache:
                value, expiry_time = self._cache[key]
                
                # Check if expired
                if time.time() < expiry_time:
                    logger.debug(f"Cache hit for key: {key}")
                    return value
                else:
                    # Remove expired entry
                    logger.debug(f"Cache entry expired for key: {key}")
                    del self._cache[key]
            
            logger.debug(f"Cache miss for key: {key}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key (str): Cache key
            value (Any): Value to cache
            ttl (Optional[int]): Time-to-live in seconds, uses default if None
        """
        ttl = ttl if ttl is not None else self._default_ttl
        expiry_time = time.time() + ttl
        
        with self._lock:
            self._cache[key] = (value, expiry_time)
            logger.debug(f"Cached value for key: {key}, TTL: {ttl}s")
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key (str): Cache key
            
        Returns:
            bool: True if key was found and deleted, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted cache entry for key: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")
    
    def _cleanup_expired_entries(self) -> None:
        """Background thread to clean up expired entries."""
        while self._running:
            time.sleep(60)  # Check every minute
            
            with self._lock:
                current_time = time.time()
                # Find keys with expired values
                expired_keys = [
                    key for key, (_, expiry_time) in self._cache.items()
                    if current_time >= expiry_time
                ]
                
                # Delete expired entries
                for key in expired_keys:
                    del self._cache[key]
                
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def stop(self) -> None:
        """Stop the cleanup thread."""
        self._running = False
        self._cleanup_thread.join(timeout=1)
        logger.debug("Cache cleanup thread stopped")


# Global cache instance
_cache = Cache()


def memoize(ttl: Optional[int] = None):
    """
    Decorator to memoize function results.
    
    Args:
        ttl (Optional[int]): Time-to-live in seconds, uses default if None
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a unique key based on function name and arguments
            key_parts = [func.__name__]
            
            # Add positional arguments
            for arg in args:
                key_parts.append(str(arg))
            
            # Add keyword arguments (sorted to ensure consistency)
            for k in sorted(kwargs.keys()):
                key_parts.append(f"{k}:{kwargs[k]}")
            
            # Create a hash of the key parts for a shorter key
            key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Check cache first
            cached_value = _cache.get(key)
            if cached_value is not None:
                return cached_value
            
            # Call the function if not in cache
            result = func(*args, **kwargs)
            
            # Cache the result
            _cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator


def cache_key_with_prefix(prefix: str, *parts: Any) -> str:
    """
    Generate a cache key with a prefix and parts.
    
    Args:
        prefix (str): Prefix for the cache key
        *parts (Any): Additional parts to include in the key
        
    Returns:
        str: Generated cache key
    """
    key_parts = [prefix]
    for part in parts:
        if isinstance(part, (dict, list)):
            key_parts.append(json.dumps(part, sort_keys=True))
        else:
            key_parts.append(str(part))
    
    return hashlib.md5(":".join(key_parts).encode()).hexdigest()


# Convenience functions to access the global cache
def get_cache(key: str) -> Optional[Any]:
    """Get a value from the global cache."""
    return _cache.get(key)

def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """Set a value in the global cache."""
    _cache.set(key, value, ttl)

def delete_cache(key: str) -> bool:
    """Delete a value from the global cache."""
    return _cache.delete(key)

def clear_cache() -> None:
    """Clear all entries from the global cache."""
    _cache.clear()

def stop_cache() -> None:
    """Stop the cache cleanup thread."""
    _cache.stop()
