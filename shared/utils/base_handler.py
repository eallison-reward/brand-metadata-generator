"""Base handler class for tool Lambda functions.

This module provides a base class that standardizes Lambda function structure,
error handling, logging, and response formatting for all tool functions.
"""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from shared.utils.error_handler import (
    ToolError,
    create_error_response,
    validate_required_params,
)
from shared.utils.logger import setup_logger, ToolLogger


class BaseToolHandler(ABC):
    """Base class for tool Lambda handlers.
    
    Provides standardized structure for:
    - Request parsing and validation
    - Error handling and logging
    - Response formatting
    - Execution timing
    """
    
    def __init__(self, tool_name: str):
        """Initialize base handler.
        
        Args:
            tool_name: Name of the tool (for logging and responses)
        """
        self.tool_name = tool_name
        self.logger = setup_logger(f"tool.{tool_name}")
    
    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Main Lambda handler entry point.
        
        Args:
            event: Lambda event dictionary
            context: Lambda context object
            
        Returns:
            Standardized response dictionary
        """
        # Generate request ID
        request_id = event.get("request_id", str(uuid.uuid4()))
        
        # Extract parameters
        parameters = event.get("parameters", {})
        
        # Log execution with context manager
        with ToolLogger(self.logger, self.tool_name, request_id, parameters) as tool_logger:
            try:
                # Validate parameters
                self.validate_parameters(parameters)
                
                # Execute tool logic
                result = self.execute(parameters)
                
                # Create success response
                response = self.create_success_response(result, request_id)
                
                # Set result for logging
                tool_logger.set_result(response)
                
                return response
                
            except ToolError as e:
                # Handle known tool errors
                tool_logger.set_error(e)
                return create_error_response(e, request_id, self.tool_name)
                
            except Exception as e:
                # Handle unexpected errors
                tool_logger.set_error(e)
                return create_error_response(e, request_id, self.tool_name)
    
    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool-specific logic.
        
        This method must be implemented by subclasses to perform the actual
        tool operation.
        
        Args:
            parameters: Validated input parameters
            
        Returns:
            Tool-specific result data
            
        Raises:
            ToolError: For expected error conditions
            Exception: For unexpected errors
        """
        pass
    
    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate input parameters.
        
        This method must be implemented by subclasses to validate tool-specific
        parameters. Should raise UserInputError for invalid input.
        
        Args:
            parameters: Input parameters to validate
            
        Raises:
            UserInputError: If parameters are invalid
        """
        pass
    
    def create_success_response(
        self,
        data: Dict[str, Any],
        request_id: str,
        execution_time_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create standardized success response.
        
        Args:
            data: Tool-specific response data
            request_id: Request ID for tracing
            execution_time_ms: Execution time in milliseconds (optional)
            
        Returns:
            Standardized success response
        """
        response = {
            "success": True,
            "data": data,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if execution_time_ms is not None:
            response["execution_time_ms"] = execution_time_ms
        
        return response
    
    def get_required_params(self) -> list[str]:
        """Get list of required parameter names.
        
        Override this method to specify required parameters.
        
        Returns:
            List of required parameter names
        """
        return []
    
    def validate_required_params(self, parameters: Dict[str, Any]) -> None:
        """Validate that required parameters are present.
        
        Args:
            parameters: Input parameters
            
        Raises:
            UserInputError: If required parameters are missing
        """
        required = self.get_required_params()
        if required:
            validate_required_params(parameters, required)


class RetryableToolHandler(BaseToolHandler):
    """Base handler with retry logic for transient failures.
    
    Extends BaseToolHandler to add automatic retry with exponential backoff
    for operations that may fail transiently.
    """
    
    def __init__(self, tool_name: str, max_retries: int = 1, initial_delay: float = 1.0):
        """Initialize retryable handler.
        
        Args:
            tool_name: Name of the tool
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds (doubles on each retry)
        """
        super().__init__(tool_name)
        self.max_retries = max_retries
        self.initial_delay = initial_delay
    
    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Handle with retry logic.
        
        Args:
            event: Lambda event dictionary
            context: Lambda context object
            
        Returns:
            Standardized response dictionary
        """
        import time
        
        last_error = None
        delay = self.initial_delay
        
        for attempt in range(self.max_retries + 1):
            try:
                # Call parent handler
                return super().handle(event, context)
                
            except Exception as e:
                last_error = e
                
                # Don't retry on last attempt
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}"
                    )
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    self.logger.error(
                        f"All {self.max_retries + 1} attempts failed: {str(e)}"
                    )
        
        # If we get here, all retries failed
        request_id = event.get("request_id", str(uuid.uuid4()))
        return create_error_response(last_error, request_id, self.tool_name)
    
    @abstractmethod
    def is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable.
        
        Override this method to specify which errors should trigger retries.
        
        Args:
            error: Exception that occurred
            
        Returns:
            True if error is retryable, False otherwise
        """
        pass
