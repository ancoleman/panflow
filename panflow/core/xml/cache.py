"""
XML caching utilities for PANFlow.

This module provides caching for XML operations to improve performance,
particularly for frequently accessed elements and XPath queries.
"""

import logging
import time
import threading
import weakref
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from functools import wraps
from lxml import etree

# Import custom exceptions
from ..exceptions import PANFlowError, CacheError

# Initialize logger
logger = logging.getLogger("panflow")

class LRUCache:
    """
    LRU (Least Recently Used) cache implementation.
    
    This cache evicts the least recently used items when the cache reaches its capacity.
    """
    
    def __init__(self, capacity: int = 1000, ttl: int = 3600):
        """
        Initialize the LRU cache.
        
        Args:
            capacity: Maximum number of items to store in the cache
            ttl: Time-to-live in seconds for cache entries (default: 1 hour)
        """
        self.capacity = capacity
        self.ttl = ttl
        self.cache: Dict[Any, Tuple[Any, float]] = {}  # {key: (value, timestamp)}
        self.usage_order: List[Any] = []  # Most recently used at the end
        self.lock = threading.RLock()
        
    def get(self, key: Any) -> Any:
        """
        Get an item from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        with self.lock:
            if key not in self.cache:
                return None
                
            value, timestamp = self.cache[key]
            
            # Check if the entry has expired
            if self.ttl > 0 and time.time() - timestamp > self.ttl:
                # Remove expired entry
                self.cache.pop(key)
                self.usage_order.remove(key)
                return None
                
            # Update usage order
            self.usage_order.remove(key)
            self.usage_order.append(key)
            
            return value
            
    def put(self, key: Any, value: Any) -> None:
        """
        Add an item to the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            # If key exists, update value and timestamp
            if key in self.cache:
                self.cache[key] = (value, time.time())
                self.usage_order.remove(key)
                self.usage_order.append(key)
                return
                
            # If cache is at capacity, remove least recently used item
            if len(self.cache) >= self.capacity:
                lru_key = self.usage_order.pop(0)
                self.cache.pop(lru_key)
                
            # Add new item
            self.cache[key] = (value, time.time())
            self.usage_order.append(key)
            
    def clear(self) -> None:
        """Clear the cache."""
        with self.lock:
            self.cache.clear()
            self.usage_order.clear()
            
    def remove(self, key: Any) -> None:
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key
        """
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
                self.usage_order.remove(key)
                
    def size(self) -> int:
        """
        Get the current size of the cache.
        
        Returns:
            Number of items in the cache
        """
        with self.lock:
            return len(self.cache)

# Create global caches
_xpath_result_cache = LRUCache(capacity=10000, ttl=300)  # 5-minute TTL
_element_cache = weakref.WeakValueDictionary()  # Cache elements referenced by their path

def cache_xpath_result(xpath: str, root_id: int, namespaces: Optional[Dict[str, str]] = None) -> Any:
    """
    Get cached XPath query result.
    
    Args:
        xpath: XPath expression
        root_id: ID of the root element (used as part of the cache key)
        namespaces: Optional namespace mappings
        
    Returns:
        Cached result or None if not cached
    """
    # Create a stable cache key
    key = (xpath, root_id, str(namespaces) if namespaces else None)
    return _xpath_result_cache.get(key)
    
def store_xpath_result(xpath: str, root_id: int, result: List[etree._Element], 
                     namespaces: Optional[Dict[str, str]] = None) -> None:
    """
    Store XPath query result in the cache.
    
    Args:
        xpath: XPath expression
        root_id: ID of the root element
        result: Query result to cache
        namespaces: Optional namespace mappings
    """
    # Create a stable cache key
    key = (xpath, root_id, str(namespaces) if namespaces else None)
    _xpath_result_cache.put(key, result)

def clear_xpath_cache() -> None:
    """Clear the XPath result cache."""
    _xpath_result_cache.clear()
    
def cache_element(element_path: str, element: etree._Element) -> None:
    """
    Cache an element by its path.
    
    Args:
        element_path: Unique path to the element
        element: Element to cache
    """
    _element_cache[element_path] = element
    
def get_cached_element(element_path: str) -> Optional[etree._Element]:
    """
    Get an element from the cache by its path.
    
    Args:
        element_path: Unique path to the element
        
    Returns:
        Cached element or None if not found
    """
    return _element_cache.get(element_path)
    
def invalidate_element_cache(element_path: Optional[str] = None) -> None:
    """
    Invalidate the element cache.
    
    Args:
        element_path: Specific element path to invalidate (if None, clear all)
    """
    if element_path:
        if element_path in _element_cache:
            del _element_cache[element_path]
    else:
        _element_cache.clear()
    
def cached_xpath(func: Callable) -> Callable:
    """
    Decorator for caching XPath query results.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function with caching
    """
    @wraps(func)
    def wrapper(root, xpath, namespaces=None, *args, **kwargs):
        # Skip caching for dynamic queries containing variables
        if "{" in xpath:
            return func(root, xpath, namespaces, *args, **kwargs)
            
        # Use id(root) to uniquely identify the root element
        root_id = id(root)
        cached_result = cache_xpath_result(xpath, root_id, namespaces)
        
        if cached_result is not None:
            logger.debug(f"Using cached result for XPath: {xpath}")
            return cached_result
            
        # Call the original function
        result = func(root, xpath, namespaces, *args, **kwargs)
        
        # Cache the result
        store_xpath_result(xpath, root_id, result, namespaces)
        
        return result
    return wrapper