"""
Exception classes for PANFlow.

This module defines custom exceptions used throughout the PANFlow library.
"""

class PANFlowError(Exception):
    """
    Base exception class for all PANFlow errors.
    
    All custom exceptions in the library should inherit from this class.
    """
    pass

class ConfigError(PANFlowError):
    """Base class for configuration-related errors."""
    pass

class ValidationError(PANFlowError):
    """Exception raised when validation fails."""
    pass

class ParseError(PANFlowError):
    """Exception raised when parsing XML fails."""
    pass

class XPathError(PANFlowError):
    """Exception raised when an XPath operation fails."""
    pass

class ContextError(PANFlowError):
    """Exception raised when an operation fails due to invalid context."""
    pass

class ObjectError(PANFlowError):
    """Base class for object-related errors."""
    pass

class ObjectNotFoundError(ObjectError):
    """Exception raised when an object is not found."""
    pass

class ObjectExistsError(ObjectError):
    """Exception raised when an object already exists but shouldn't."""
    pass

class PolicyError(PANFlowError):
    """Base class for policy-related errors."""
    pass

class PolicyNotFoundError(PolicyError):
    """Exception raised when a policy is not found."""
    pass

class PolicyExistsError(PolicyError):
    """Exception raised when a policy already exists but shouldn't."""
    pass

class MergeError(PANFlowError):
    """Exception raised when merging objects or policies fails."""
    pass

class ConflictError(MergeError):
    """Exception raised when there's a conflict during a merge operation."""
    pass

class VersionError(PANFlowError):
    """Exception raised when there's a version compatibility issue."""
    pass

class FileOperationError(PANFlowError):
    """Exception raised when a file operation fails."""
    pass

class BulkOperationError(PANFlowError):
    """Exception raised when a bulk operation fails."""
    
    def __init__(self, message, successful=None, failed=None):
        """
        Initialize a BulkOperationError.
        
        Args:
            message: Error message
            successful: List of successful operations (optional)
            failed: Dictionary of failed operations with error messages (optional)
        """
        super().__init__(message)
        self.successful = successful or []
        self.failed = failed or {}

class SecurityError(PANFlowError):
    """Exception raised for security-related issues."""
    pass

class CacheError(PANFlowError):
    """Exception raised when caching operations fail."""
    pass

class DiffError(PANFlowError):
    """Exception raised when diff operations fail."""
    pass

class QueryError(PANFlowError):
    """Exception raised when query operations fail."""
    pass