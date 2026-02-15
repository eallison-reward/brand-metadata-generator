"""Logging utilities for Lambda functions.

This module provides structured logging for tool Lambda functions,
ensuring consistent log format and CloudWatch integration.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Set up logger with consistent formatting.
    
    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, level.upper()))
        
        # Create console handler for Lambda (writes to CloudWatch)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper()))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger


def log_tool_execution(
    logger: logging.Logger,
    tool_name: str,
    request_id: str,
    parameters: Dict[str, Any],
    result: Optional[Dict[str, Any]] = None,
    error: Optional[Exception] = None,
    execution_time_ms: Optional[int] = None,
) -> None:
    """Log tool execution with structured data.
    
    Args:
        logger: Logger instance
        tool_name: Name of the tool
        request_id: Request ID for tracing
        parameters: Input parameters
        result: Execution result (if successful)
        error: Exception (if failed)
        execution_time_ms: Execution time in milliseconds
    """
    log_data = {
        "tool_name": tool_name,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "parameters": _sanitize_params(parameters),
    }
    
    if execution_time_ms is not None:
        log_data["execution_time_ms"] = execution_time_ms
    
    if error:
        log_data["status"] = "error"
        log_data["error"] = str(error)
        log_data["error_type"] = type(error).__name__
        logger.error(f"Tool execution failed: {json.dumps(log_data)}")
    else:
        log_data["status"] = "success"
        if result:
            log_data["result_summary"] = _summarize_result(result)
        logger.info(f"Tool execution completed: {json.dumps(log_data)}")


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize parameters for logging (remove sensitive data).
    
    Args:
        params: Parameter dictionary
        
    Returns:
        Sanitized parameter dictionary
    """
    sanitized = {}
    sensitive_keys = ["password", "token", "secret", "key", "credential"]
    
    for key, value in params.items():
        # Check if key contains sensitive terms
        if any(term in key.lower() for term in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        # Truncate long strings
        elif isinstance(value, str) and len(value) > 200:
            sanitized[key] = value[:200] + "...[truncated]"
        # Truncate long lists
        elif isinstance(value, list) and len(value) > 10:
            sanitized[key] = value[:10] + ["...[truncated]"]
        else:
            sanitized[key] = value
    
    return sanitized


def _summarize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Create summary of result for logging.
    
    Args:
        result: Result dictionary
        
    Returns:
        Summarized result
    """
    summary = {}
    
    # Include success status
    if "success" in result:
        summary["success"] = result["success"]
    
    # Include counts if present
    for key in ["row_count", "total_count", "execution_count"]:
        if key in result:
            summary[key] = result[key]
    
    # Include data length if present
    if "data" in result:
        if isinstance(result["data"], list):
            summary["data_length"] = len(result["data"])
        elif isinstance(result["data"], dict):
            summary["data_keys"] = list(result["data"].keys())
    
    return summary


class ToolLogger:
    """Context manager for tool execution logging."""
    
    def __init__(
        self,
        logger: logging.Logger,
        tool_name: str,
        request_id: str,
        parameters: Dict[str, Any],
    ):
        """Initialize tool logger.
        
        Args:
            logger: Logger instance
            tool_name: Name of the tool
            request_id: Request ID for tracing
            parameters: Input parameters
        """
        self.logger = logger
        self.tool_name = tool_name
        self.request_id = request_id
        self.parameters = parameters
        self.start_time = None
        self.result = None
        self.error = None
    
    def __enter__(self):
        """Enter context - log execution start."""
        self.start_time = datetime.utcnow()
        self.logger.info(
            f"Starting tool execution: {self.tool_name} "
            f"(request_id={self.request_id})"
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - log execution completion."""
        execution_time_ms = None
        if self.start_time:
            duration = datetime.utcnow() - self.start_time
            execution_time_ms = int(duration.total_seconds() * 1000)
        
        log_tool_execution(
            logger=self.logger,
            tool_name=self.tool_name,
            request_id=self.request_id,
            parameters=self.parameters,
            result=self.result,
            error=exc_val if exc_type else self.error,
            execution_time_ms=execution_time_ms,
        )
        
        # Don't suppress exceptions
        return False
    
    def set_result(self, result: Dict[str, Any]) -> None:
        """Set execution result.
        
        Args:
            result: Result dictionary
        """
        self.result = result
    
    def set_error(self, error: Exception) -> None:
        """Set execution error.
        
        Args:
            error: Exception that occurred
        """
        self.error = error
