"""Structured error response utilities for conversational interface tools.

This module provides helper functions for creating consistent, user-friendly
error responses across all tool Lambda functions. It complements error_handler.py
by focusing on response formatting and common error scenarios.
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from .error_handler import ErrorType, ToolError


def format_error_response(
    error: ToolError,
    request_id: str,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Format a ToolError into a standardized response structure.
    
    Args:
        error: ToolError instance to format
        request_id: Request ID for tracing
        tool_name: Name of the tool (for context)
        
    Returns:
        Standardized error response dictionary
    """
    return {
        "success": False,
        "error": {
            "type": error.error_type.value,
            "message": error.message,
            "details": error.details,
            "suggestion": error.suggestion,
        },
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
    }


def create_user_input_error_response(
    message: str,
    request_id: str,
    details: Optional[str] = None,
    suggestion: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for invalid user input.
    
    Args:
        message: User-friendly error message
        request_id: Request ID for tracing
        details: Technical details (optional)
        suggestion: Actionable suggestion (optional)
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return {
        "success": False,
        "error": {
            "type": ErrorType.USER_INPUT.value,
            "message": message,
            "details": details or message,
            "suggestion": suggestion or "Please check your input parameters and try again.",
        },
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
    }


def create_backend_service_error_response(
    message: str,
    request_id: str,
    details: Optional[str] = None,
    suggestion: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for backend service failures.
    
    Args:
        message: User-friendly error message
        request_id: Request ID for tracing
        details: Technical details (optional)
        suggestion: Actionable suggestion (optional)
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return {
        "success": False,
        "error": {
            "type": ErrorType.BACKEND_SERVICE.value,
            "message": message,
            "details": details or message,
            "suggestion": suggestion or "Please try again later or check system status.",
        },
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
    }


def create_permission_error_response(
    message: str,
    request_id: str,
    details: Optional[str] = None,
    suggestion: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for permission/access issues.
    
    Args:
        message: User-friendly error message
        request_id: Request ID for tracing
        details: Technical details (optional)
        suggestion: Actionable suggestion (optional)
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return {
        "success": False,
        "error": {
            "type": ErrorType.PERMISSION.value,
            "message": message,
            "details": details or message,
            "suggestion": suggestion or "Please contact an administrator for access.",
        },
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
    }


def create_system_error_response(
    message: str,
    request_id: str,
    details: Optional[str] = None,
    suggestion: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for unexpected system failures.
    
    Args:
        message: User-friendly error message
        request_id: Request ID for tracing
        details: Technical details (optional)
        suggestion: Actionable suggestion (optional)
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return {
        "success": False,
        "error": {
            "type": ErrorType.SYSTEM.value,
            "message": message,
            "details": details or message,
            "suggestion": suggestion or "Please try again or contact support if the issue persists.",
        },
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
    }


# Common error scenario helpers

def missing_parameter_error(
    parameter_name: str,
    request_id: str,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for missing required parameter.
    
    Args:
        parameter_name: Name of the missing parameter
        request_id: Request ID for tracing
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return create_user_input_error_response(
        message=f"Missing required parameter: {parameter_name}",
        request_id=request_id,
        suggestion=f"Please provide a value for '{parameter_name}'.",
        tool_name=tool_name,
    )


def invalid_parameter_type_error(
    parameter_name: str,
    expected_type: str,
    request_id: str,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for invalid parameter type.
    
    Args:
        parameter_name: Name of the parameter
        expected_type: Expected type as string (e.g., "integer", "string")
        request_id: Request ID for tracing
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return create_user_input_error_response(
        message=f"Parameter '{parameter_name}' must be of type {expected_type}",
        request_id=request_id,
        suggestion=f"Please provide a valid {expected_type} value for '{parameter_name}'.",
        tool_name=tool_name,
    )


def resource_not_found_error(
    resource_type: str,
    resource_id: str,
    request_id: str,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for resource not found.
    
    Args:
        resource_type: Type of resource (e.g., "brand", "workflow", "metadata")
        resource_id: Identifier of the resource
        request_id: Request ID for tracing
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return create_backend_service_error_response(
        message=f"{resource_type.capitalize()} not found: {resource_id}",
        request_id=request_id,
        suggestion=f"Please verify the {resource_type} identifier and try again.",
        tool_name=tool_name,
    )


def service_unavailable_error(
    service_name: str,
    request_id: str,
    details: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for service unavailability.
    
    Args:
        service_name: Name of the unavailable service
        request_id: Request ID for tracing
        details: Technical details (optional)
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return create_backend_service_error_response(
        message=f"{service_name} is currently unavailable",
        request_id=request_id,
        details=details,
        suggestion="Please try again in a few moments or check system status.",
        tool_name=tool_name,
    )


def timeout_error(
    operation: str,
    request_id: str,
    timeout_seconds: Optional[int] = None,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for operation timeout.
    
    Args:
        operation: Description of the operation that timed out
        request_id: Request ID for tracing
        timeout_seconds: Timeout duration in seconds (optional)
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    timeout_msg = f" after {timeout_seconds} seconds" if timeout_seconds else ""
    return create_backend_service_error_response(
        message=f"Operation timed out: {operation}{timeout_msg}",
        request_id=request_id,
        suggestion="The operation is taking longer than expected. Please check system status and try again.",
        tool_name=tool_name,
    )


def permission_denied_error(
    operation: str,
    request_id: str,
    details: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for permission denied.
    
    Args:
        operation: Description of the operation that was denied
        request_id: Request ID for tracing
        details: Technical details (optional)
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return create_permission_error_response(
        message=f"Permission denied: {operation}",
        request_id=request_id,
        details=details,
        suggestion="You don't have permission to perform this operation. Please contact an administrator.",
        tool_name=tool_name,
    )


def invalid_query_error(
    query_issue: str,
    request_id: str,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for invalid query.
    
    Args:
        query_issue: Description of what's wrong with the query
        request_id: Request ID for tracing
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return create_user_input_error_response(
        message=f"Invalid query: {query_issue}",
        request_id=request_id,
        suggestion="Please check your query parameters and try again.",
        tool_name=tool_name,
    )


def workflow_execution_error(
    execution_arn: str,
    error_message: str,
    request_id: str,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for workflow execution failure.
    
    Args:
        execution_arn: ARN of the failed execution
        error_message: Error message from the workflow
        request_id: Request ID for tracing
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized error response dictionary
    """
    return create_backend_service_error_response(
        message="Workflow execution failed",
        request_id=request_id,
        details=f"Execution {execution_arn}: {error_message}",
        suggestion="Please check the workflow execution details and retry if appropriate.",
        tool_name=tool_name,
    )


def empty_result_error(
    query_description: str,
    request_id: str,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response for empty query results.
    
    Note: This is not technically an error, but provides a structured
    response for empty results with helpful suggestions.
    
    Args:
        query_description: Description of the query that returned no results
        request_id: Request ID for tracing
        tool_name: Name of the tool (optional)
        
    Returns:
        Standardized response dictionary
    """
    return {
        "success": True,
        "data": {
            "results": [],
            "total_count": 0,
            "message": f"No results found for: {query_description}",
            "suggestion": "Try broadening your search criteria or checking if the data exists.",
        },
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
    }
