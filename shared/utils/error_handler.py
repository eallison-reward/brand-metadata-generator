"""Error handling utilities for Lambda functions.

This module provides structured error handling for tool Lambda functions,
categorizing errors and providing user-friendly messages with actionable suggestions.

## Error Categories

The system categorizes all errors into four main types:

1. **USER_INPUT**: Invalid parameters, missing required fields, malformed requests
   - Examples: ValidationException, InvalidParameterException, MissingParameter
   - Suggestion: Check input parameters and provide correct values
   
2. **BACKEND_SERVICE**: AWS service failures, timeouts, resource not found
   - Examples: ResourceNotFoundException, ThrottlingException, ServiceUnavailable
   - Suggestion: Retry the operation, check service status, verify resource exists
   
3. **PERMISSION**: IAM permission denials, access restrictions
   - Examples: AccessDenied, UnauthorizedOperation, Forbidden
   - Suggestion: Contact administrator to request necessary permissions
   
4. **SYSTEM**: Unexpected errors, internal failures, unhandled exceptions
   - Examples: InternalServerError, unexpected Python exceptions
   - Suggestion: Try again or contact support

## Usage

### Automatic Error Categorization

```python
from shared.utils.error_handler import categorize_error, create_error_response

try:
    # AWS SDK call or operation
    result = some_aws_operation()
except Exception as e:
    # Automatically categorize and create response
    error_response = create_error_response(e, request_id="req-123", tool_name="my_tool")
    return error_response
```

### Manual Error Creation

```python
from shared.utils.error_handler import UserInputError, BackendServiceError

# Raise specific error types
if not brandid:
    raise UserInputError(
        message="Brand ID is required",
        suggestion="Please provide a valid brand ID"
    )

# Or create error responses directly
if resource_not_found:
    raise BackendServiceError(
        message="Brand not found",
        details=f"Brand {brandid} does not exist",
        suggestion="Please verify the brand ID and try again"
    )
```

### AWS Error Handling

```python
from shared.utils.error_handler import handle_aws_error

try:
    response = s3_client.get_object(Bucket=bucket, Key=key)
except ClientError as e:
    # Automatically categorize AWS SDK error
    tool_error = handle_aws_error(e)
    # tool_error is now a ToolError with appropriate category and suggestion
```

## Error Response Format

All error responses follow this structure:

```json
{
  "success": false,
  "error": {
    "type": "user_input|backend_service|permission|system",
    "message": "User-friendly error message",
    "details": "Technical details for logging",
    "suggestion": "Actionable next step"
  },
  "request_id": "req-123",
  "timestamp": "2024-01-15T10:30:00.000000"
}
```

## Requirements Mapping

This module implements error handling requirements:
- Requirement 9.1: Permission error handling and suggestions
- Requirement 9.2: Invalid input error handling and explanations
- Requirement 9.3: Timeout error handling and system status suggestions
- Requirement 9.4: Athena error parsing and user-friendly explanations
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Error categories for structured error handling."""
    
    USER_INPUT = "user_input"
    BACKEND_SERVICE = "backend_service"
    PERMISSION = "permission"
    SYSTEM = "system"


class ToolError(Exception):
    """Base exception for tool Lambda function errors."""
    
    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        details: Optional[str] = None,
        suggestion: Optional[str] = None,
    ):
        """Initialize tool error.
        
        Args:
            message: User-friendly error message
            error_type: Category of error
            details: Technical details for logging
            suggestion: Actionable next step for user
        """
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or message
        self.suggestion = suggestion or self._default_suggestion()
    
    def _default_suggestion(self) -> str:
        """Get default suggestion based on error type."""
        suggestions = {
            ErrorType.USER_INPUT: "Please check your input parameters and try again.",
            ErrorType.BACKEND_SERVICE: "Please try again later or check system status.",
            ErrorType.PERMISSION: "Please contact an administrator for access.",
            ErrorType.SYSTEM: "Please try again or contact support if the issue persists.",
        }
        return suggestions.get(self.error_type, "Please try again.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format for Lambda response.
        
        Returns:
            Error dictionary with type, message, details, and suggestion
        """
        return {
            "type": self.error_type.value,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
        }


class UserInputError(ToolError):
    """Error for invalid user input."""
    
    def __init__(self, message: str, details: Optional[str] = None, suggestion: Optional[str] = None):
        super().__init__(message, ErrorType.USER_INPUT, details, suggestion)


class BackendServiceError(ToolError):
    """Error for backend service failures."""
    
    def __init__(self, message: str, details: Optional[str] = None, suggestion: Optional[str] = None):
        super().__init__(message, ErrorType.BACKEND_SERVICE, details, suggestion)


class PermissionError(ToolError):
    """Error for permission/access issues."""
    
    def __init__(self, message: str, details: Optional[str] = None, suggestion: Optional[str] = None):
        super().__init__(message, ErrorType.PERMISSION, details, suggestion)


class SystemError(ToolError):
    """Error for unexpected system failures."""
    
    def __init__(self, message: str, details: Optional[str] = None, suggestion: Optional[str] = None):
        super().__init__(message, ErrorType.SYSTEM, details, suggestion)


def handle_aws_error(error: Exception) -> ToolError:
    """Convert AWS SDK errors to ToolError instances.
    
    Automatically categorizes AWS SDK errors into four categories:
    - user_input: Invalid parameters, malformed requests
    - backend_service: Service failures, timeouts, resource not found
    - permission: IAM permission denials, access restrictions
    - system: Unexpected errors, internal failures
    
    Args:
        error: AWS SDK exception
        
    Returns:
        Appropriate ToolError subclass with error-specific suggestions
    """
    error_str = str(error)
    error_code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
    error_message = getattr(error, "response", {}).get("Error", {}).get("Message", error_str)
    
    # ============================================================================
    # PERMISSION ERRORS (Requirements 9.1, 10.5)
    # ============================================================================
    
    # IAM permission denials
    if error_code in [
        "AccessDenied",
        "AccessDeniedException", 
        "UnauthorizedOperation",
        "Forbidden",
        "ForbiddenException",
        "InsufficientPermissionsException",
        "NotAuthorized",
        "UnauthorizedException",
    ]:
        return PermissionError(
            message="You don't have permission to perform this operation.",
            details=f"{error_code}: {error_message}",
            suggestion="Please contact an administrator to request the necessary IAM permissions.",
        )
    
    # ============================================================================
    # USER INPUT ERRORS (Requirements 9.2)
    # ============================================================================
    
    # Validation and parameter errors
    if error_code in [
        "ValidationException",
        "InvalidParameterException",
        "InvalidParameterValue",
        "InvalidParameterValueException",
        "InvalidParameterCombination",
        "InvalidInput",
        "InvalidInputException",
        "MalformedQueryString",
        "InvalidQueryParameter",
        "InvalidAction",
    ]:
        return UserInputError(
            message="Invalid input parameters provided.",
            details=f"{error_code}: {error_message}",
            suggestion="Please check your input parameters and ensure all required fields are correct.",
        )
    
    # Missing required parameters
    if error_code in [
        "MissingParameter",
        "MissingRequiredParameter",
        "MissingParameterException",
    ]:
        return UserInputError(
            message="Required parameter is missing.",
            details=f"{error_code}: {error_message}",
            suggestion="Please provide all required parameters for this operation.",
        )
    
    # Athena-specific errors (check before generic InvalidRequestException)
    if "athena" in error_str.lower() and error_code in [
        "InvalidRequestException",  # Athena query syntax error
        "QueryExecutionException",
        "TooManyRequestsException",  # Athena throttling
    ]:
        return BackendServiceError(
            message="Athena query execution failed.",
            details=f"{error_code}: {error_message}",
            suggestion="Please check the query syntax and ensure the table/database exists. Verify Athena service status.",
        )
    
    # Invalid request format
    if error_code in [
        "InvalidRequest",
        "InvalidRequestException",
        "SerializationException",
        "InvalidJsonException",
    ]:
        return UserInputError(
            message="The request format is invalid.",
            details=f"{error_code}: {error_message}",
            suggestion="Please check the request format and ensure it matches the expected structure.",
        )
    
    # Invalid ARN or identifier format
    if error_code in [
        "InvalidArn",
        "InvalidArnException",
        "InvalidIdentifier",
    ]:
        return UserInputError(
            message="Invalid resource identifier format.",
            details=f"{error_code}: {error_message}",
            suggestion="Please provide a valid ARN or identifier in the correct format.",
        )
    
    # ============================================================================
    # BACKEND SERVICE ERRORS (Requirements 9.3, 9.4)
    # ============================================================================
    
    # Resource not found errors
    if error_code in [
        "ResourceNotFoundException",
        "NoSuchEntity",
        "NoSuchKey",
        "ExecutionDoesNotExist",
        "StateMachineDoesNotExist",
        "TableNotFoundException",
        "DatabaseNotFoundException",
        "BucketNotFoundException",
        "ObjectNotFound",
    ]:
        return BackendServiceError(
            message="The requested resource was not found.",
            details=f"{error_code}: {error_message}",
            suggestion="Please verify the resource identifier exists and try again.",
        )
    
    # Throttling and rate limiting
    if error_code in [
        "ThrottlingException",
        "TooManyRequestsException",
        "RequestLimitExceeded",
        "ProvisionedThroughputExceededException",
        "SlowDown",
    ]:
        return BackendServiceError(
            message="The service is currently busy due to high request volume.",
            details=f"{error_code}: {error_message}",
            suggestion="Wait a few seconds and retry your request. Consider implementing exponential backoff.",
        )
    
    # Timeout errors
    if error_code in ["RequestTimeout", "RequestTimeoutException"] or "timeout" in error_str.lower():
        return BackendServiceError(
            message="The operation timed out.",
            details=f"{error_code or 'Timeout'}: {error_message}",
            suggestion="The operation is taking longer than expected. Please check system status and try again.",
        )
    
    # Service unavailability
    if error_code in [
        "ServiceUnavailable",
        "ServiceUnavailableException",
        "InternalServerError",
        "InternalError",
        "InternalFailure",
        "ServiceException",
    ]:
        return BackendServiceError(
            message="The AWS service is temporarily unavailable.",
            details=f"{error_code}: {error_message}",
            suggestion="The service is experiencing issues. Please try again in a few moments or check AWS service health.",
        )
    
    # Step Functions specific errors
    if error_code in [
        "ExecutionAlreadyExists",
        "ExecutionLimitExceeded",
        "InvalidExecutionInput",
        "StateMachineDeleting",
        "StateMachineLimitExceeded",
    ]:
        return BackendServiceError(
            message="Step Functions workflow operation failed.",
            details=f"{error_code}: {error_message}",
            suggestion="Please check the workflow execution parameters and state machine status.",
        )
    
    # S3 specific errors
    if error_code in [
        "NoSuchBucket",
        "BucketAlreadyExists",
        "BucketAlreadyOwnedByYou",
    ]:
        return BackendServiceError(
            message="S3 bucket operation failed.",
            details=f"{error_code}: {error_message}",
            suggestion="Please verify the S3 bucket name and ensure it exists in the correct region.",
        )
    
    # Resource conflicts
    if error_code in [
        "ResourceInUseException",
        "ConflictException",
        "ResourceConflict",
    ]:
        return BackendServiceError(
            message="The resource is currently in use or in a conflicting state.",
            details=f"{error_code}: {error_message}",
            suggestion="Please wait for the current operation to complete or resolve the conflict before retrying.",
        )
    
    # ============================================================================
    # SYSTEM ERRORS (Default fallback)
    # ============================================================================
    
    # Catch-all for unexpected errors
    return SystemError(
        message="An unexpected error occurred.",
        details=f"{error_code or 'Unknown'}: {error_message}",
        suggestion="Please try again or contact support if the issue persists.",
    )


def categorize_error(error: Exception) -> ToolError:
    """Categorize any exception into appropriate ToolError type.
    
    This function provides comprehensive error categorization for both
    AWS SDK errors and general Python exceptions. It automatically
    determines the error category and provides contextual suggestions.
    
    Args:
        error: Any exception instance
        
    Returns:
        Appropriate ToolError subclass with category and suggestions
    """
    # Handle ToolError instances (already categorized)
    if isinstance(error, ToolError):
        return error
    
    # Handle AWS SDK errors
    if hasattr(error, "response") and isinstance(error.response, dict):
        return handle_aws_error(error)
    
    # Handle common Python exceptions
    error_str = str(error).lower()
    error_type_name = type(error).__name__
    
    # Value errors typically indicate invalid input
    if isinstance(error, ValueError):
        return UserInputError(
            message=f"Invalid value provided: {error}",
            details=f"{error_type_name}: {error}",
            suggestion="Please check your input values and ensure they are in the correct format.",
        )
    
    # Type errors indicate incorrect parameter types
    if isinstance(error, TypeError):
        return UserInputError(
            message=f"Incorrect parameter type: {error}",
            details=f"{error_type_name}: {error}",
            suggestion="Please ensure all parameters are of the correct type.",
        )
    
    # Key errors indicate missing required fields
    if isinstance(error, KeyError):
        return UserInputError(
            message=f"Missing required field: {error}",
            details=f"{error_type_name}: {error}",
            suggestion="Please provide all required fields in your request.",
        )
    
    # Connection errors indicate service unavailability
    if "connection" in error_str or "network" in error_str:
        return BackendServiceError(
            message="Unable to connect to the service.",
            details=f"{error_type_name}: {error}",
            suggestion="Please check your network connection and service availability.",
        )
    
    # Timeout errors
    if "timeout" in error_str or isinstance(error, TimeoutError):
        return BackendServiceError(
            message="The operation timed out.",
            details=f"{error_type_name}: {error}",
            suggestion="The operation is taking longer than expected. Please try again.",
        )
    
    # File not found errors
    if isinstance(error, FileNotFoundError):
        return BackendServiceError(
            message="The requested file or resource was not found.",
            details=f"{error_type_name}: {error}",
            suggestion="Please verify the file path or resource identifier.",
        )
    
    # Permission errors (OS level) - check if it's the built-in PermissionError, not our custom one
    if error_type_name == "PermissionError" and error.__class__.__module__ == "builtins":
        from shared.utils.error_handler import PermissionError as ToolPermissionError
        return ToolPermissionError(
            message="Permission denied for this operation.",
            details=f"{error_type_name}: {error}",
            suggestion="Please contact an administrator to request the necessary permissions.",
        )
    
    # Default to system error for unexpected exceptions
    return SystemError(
        message="An unexpected error occurred.",
        details=f"{error_type_name}: {error}",
        suggestion="Please try again or contact support if the issue persists.",
    )


def create_error_response(
    error: Exception,
    request_id: str,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create standardized error response for Lambda functions.
    
    This function automatically categorizes errors and creates a
    structured response with appropriate error type, message, and
    suggestions based on the error category.
    
    Args:
        error: Exception that occurred
        request_id: Request ID for tracing
        tool_name: Name of the tool (for logging)
        
    Returns:
        Standardized error response dictionary
    """
    # Categorize the error
    tool_error = categorize_error(error)
    
    # Log the error with appropriate level
    log_message = f"Tool error in {tool_name or 'unknown'}: {tool_error.details}"
    if tool_error.error_type == ErrorType.SYSTEM:
        logger.error(log_message, exc_info=True)
    elif tool_error.error_type == ErrorType.PERMISSION:
        logger.warning(f"Permission denied in {tool_name or 'unknown'}: {tool_error.details}")
    else:
        logger.info(log_message)
    
    # Create response
    return {
        "success": False,
        "error": tool_error.to_dict(),
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_error_suggestion(error_type: ErrorType, error_code: str = "", context: str = "") -> str:
    """Get error-specific suggestion based on error type and context.
    
    Provides contextual, actionable suggestions for different error scenarios
    to help users resolve issues quickly.
    
    Args:
        error_type: Category of error
        error_code: AWS error code or error identifier
        context: Additional context about the operation (e.g., "athena_query", "workflow_start")
        
    Returns:
        Actionable suggestion string
    """
    context_lower = context.lower()
    
    # Permission error suggestions
    if error_type == ErrorType.PERMISSION:
        if "athena" in context_lower:
            return "Please contact an administrator to grant Athena query execution permissions."
        elif "stepfunctions" in context_lower or "workflow" in context_lower:
            return "Please contact an administrator to grant Step Functions execution permissions."
        elif "s3" in context_lower:
            return "Please contact an administrator to grant S3 read/write permissions."
        else:
            return "Please contact an administrator to request the necessary IAM permissions."
    
    # User input error suggestions
    if error_type == ErrorType.USER_INPUT:
        if "brandid" in context_lower:
            return "Please provide a valid brand ID (positive integer)."
        elif "execution_arn" in context_lower or "arn" in context_lower:
            return "Please provide a valid ARN in the format: arn:aws:states:region:account:execution:stateMachine:executionName"
        elif "query" in context_lower:
            return "Please check your query parameters and ensure they match the expected format."
        elif "missing" in error_code.lower():
            return "Please provide all required parameters for this operation."
        else:
            return "Please check your input parameters and ensure all required fields are correct."
    
    # Backend service error suggestions
    if error_type == ErrorType.BACKEND_SERVICE:
        if "throttl" in error_code.lower():
            return "The service is experiencing high load. Wait 5-10 seconds and retry your request."
        elif "timeout" in error_code.lower() or "timeout" in context_lower:
            return "The operation is taking longer than expected. Check system status and try again with a longer timeout."
        elif "notfound" in error_code.lower() or "not found" in context_lower:
            if "brand" in context_lower:
                return "The brand ID was not found. Please verify the brand exists in the system."
            elif "execution" in context_lower:
                return "The workflow execution was not found. Please verify the execution ARN."
            elif "metadata" in context_lower:
                return "Metadata not found for this brand. The brand may not have been processed yet."
            else:
                return "The requested resource was not found. Please verify the identifier and try again."
        elif "athena" in context_lower:
            return "Athena query failed. Check the query syntax, table names, and database availability."
        elif "unavailable" in error_code.lower():
            return "The AWS service is temporarily unavailable. Please try again in a few moments or check AWS service health."
        else:
            return "Please try again later or check system status for any ongoing issues."
    
    # System error suggestions
    if error_type == ErrorType.SYSTEM:
        return "An unexpected error occurred. Please try again or contact support if the issue persists."
    
    # Default fallback
    return "Please try again or contact support if you need assistance."


def validate_required_params(params: Dict[str, Any], required: list[str]) -> None:
    """Validate that required parameters are present.
    
    Args:
        params: Parameter dictionary
        required: List of required parameter names
        
    Raises:
        UserInputError: If any required parameter is missing
    """
    missing = [param for param in required if param not in params or params[param] is None]
    
    if missing:
        raise UserInputError(
            message=f"Missing required parameters: {', '.join(missing)}",
            suggestion=f"Please provide values for: {', '.join(missing)}",
        )


def validate_param_type(params: Dict[str, Any], param_name: str, expected_type: type) -> None:
    """Validate parameter type.
    
    Args:
        params: Parameter dictionary
        param_name: Name of parameter to validate
        expected_type: Expected Python type
        
    Raises:
        UserInputError: If parameter type is incorrect
    """
    if param_name in params and params[param_name] is not None:
        if not isinstance(params[param_name], expected_type):
            raise UserInputError(
                message=f"Parameter '{param_name}' must be of type {expected_type.__name__}",
                suggestion=f"Please provide a valid {expected_type.__name__} value for '{param_name}'",
            )
