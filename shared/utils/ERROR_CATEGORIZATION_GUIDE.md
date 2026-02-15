# Error Categorization Guide

This guide explains the comprehensive error categorization system implemented in `error_handler.py` for the Conversational Interface Agent.

## Overview

The error categorization system automatically categorizes all errors into four main types:

1. **USER_INPUT**: Invalid parameters, missing required fields, malformed requests
2. **BACKEND_SERVICE**: AWS service failures, timeouts, resource not found
3. **PERMISSION**: IAM permission denials, access restrictions
4. **SYSTEM**: Unexpected errors, internal failures, unhandled exceptions

Each error category provides:
- User-friendly error messages
- Technical details for logging
- Actionable suggestions for resolution
- Context-aware recommendations

## Requirements Mapping

This implementation satisfies the following requirements:

- **Requirement 9.1**: Permission error handling with administrator contact suggestions
- **Requirement 9.2**: Invalid input error handling with clear explanations
- **Requirement 9.3**: Timeout error handling with system status check suggestions
- **Requirement 9.4**: Athena error parsing with user-friendly explanations

## Quick Start

### Basic Usage

```python
from shared.utils.error_handler import create_error_response
import uuid

def lambda_handler(event, context):
    request_id = str(uuid.uuid4())
    
    try:
        # Your operation here
        result = perform_operation()
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "data": result,
                "request_id": request_id
            })
        }
    
    except Exception as e:
        # Automatically categorize and format error
        error_response = create_error_response(
            e,
            request_id=request_id,
            tool_name="my_tool"
        )
        
        return {
            "statusCode": 500,
            "body": json.dumps(error_response)
        }
```

## Error Categories in Detail

### 1. USER_INPUT Errors

**When to use**: Invalid parameters, missing data, malformed requests

**AWS Error Codes**:
- `ValidationException`
- `InvalidParameterException`
- `InvalidParameterValue`
- `MissingParameter`
- `InvalidRequest`
- `InvalidArn`
- `MalformedQueryString`

**Python Exceptions**:
- `ValueError`
- `TypeError`
- `KeyError`

**Example**:
```python
from shared.utils.error_handler import UserInputError

# Manual error creation
if not brandid or brandid <= 0:
    raise UserInputError(
        message="Invalid brand ID",
        details="Brand ID must be a positive integer",
        suggestion="Please provide a valid brand ID greater than 0"
    )
```

**Response Format**:
```json
{
  "success": false,
  "error": {
    "type": "user_input",
    "message": "Invalid brand ID",
    "details": "Brand ID must be a positive integer",
    "suggestion": "Please provide a valid brand ID greater than 0"
  },
  "request_id": "req-123",
  "timestamp": "2024-01-15T10:30:00.000000+00:00"
}
```

### 2. BACKEND_SERVICE Errors

**When to use**: AWS service failures, timeouts, resource not found

**AWS Error Codes**:
- `ResourceNotFoundException`
- `ThrottlingException`
- `RequestTimeout`
- `ServiceUnavailable`
- `InternalServerError`
- `ExecutionDoesNotExist`
- `NoSuchBucket`
- `QueryExecutionException` (Athena)

**Python Exceptions**:
- `TimeoutError`
- `FileNotFoundError`
- Connection errors

**Example**:
```python
from shared.utils.error_handler import BackendServiceError

# Manual error creation
if not metadata_exists:
    raise BackendServiceError(
        message="Metadata not found for this brand",
        details=f"Brand {brandid} has not been processed yet",
        suggestion="Please start a workflow to generate metadata for this brand"
    )
```

**Athena-Specific Handling** (Requirement 9.4):
```python
# Athena errors are automatically detected and categorized
try:
    result = athena_client.execute_query(query)
except ClientError as e:
    # Automatically categorized as backend_service with Athena-specific message
    error_response = create_error_response(e, request_id, "execute_athena_query")
    # Error message: "Athena query execution failed."
    # Suggestion: "Please check the query syntax and ensure the table/database exists."
```

### 3. PERMISSION Errors

**When to use**: IAM permission denials, access restrictions

**AWS Error Codes**:
- `AccessDenied`
- `AccessDeniedException`
- `UnauthorizedOperation`
- `Forbidden`
- `ForbiddenException`
- `InsufficientPermissionsException`

**Python Exceptions**:
- `PermissionError` (built-in)

**Example**:
```python
from shared.utils.error_handler import PermissionError

# Manual error creation
if not has_permission:
    raise PermissionError(
        message="You don't have permission to start workflows",
        details="IAM role lacks stepfunctions:StartExecution permission",
        suggestion="Please contact an administrator to grant Step Functions execution permissions"
    )
```

**Context-Aware Suggestions** (Requirement 9.1):
```python
from shared.utils.error_handler import get_error_suggestion, ErrorType

# Get context-specific suggestion
suggestion = get_error_suggestion(
    ErrorType.PERMISSION,
    context="athena_query"
)
# Returns: "Please contact an administrator to grant Athena query execution permissions."

suggestion = get_error_suggestion(
    ErrorType.PERMISSION,
    context="workflow_start"
)
# Returns: "Please contact an administrator to grant Step Functions execution permissions."
```

### 4. SYSTEM Errors

**When to use**: Unexpected errors, internal failures, unhandled exceptions

**AWS Error Codes**:
- Unknown error codes
- Unexpected exceptions

**Python Exceptions**:
- Generic `Exception`
- Unhandled exceptions

**Example**:
```python
from shared.utils.error_handler import SystemError

# Manual error creation
try:
    result = complex_operation()
except Exception as e:
    raise SystemError(
        message="An unexpected error occurred during processing",
        details=str(e),
        suggestion="Please try again or contact support if the issue persists"
    )
```

## Advanced Features

### Automatic AWS Error Categorization

The `handle_aws_error()` function automatically categorizes AWS SDK errors:

```python
from shared.utils.error_handler import handle_aws_error
from botocore.exceptions import ClientError

try:
    response = s3_client.get_object(Bucket=bucket, Key=key)
except ClientError as e:
    # Automatically categorized based on error code
    tool_error = handle_aws_error(e)
    
    # tool_error is now a ToolError with:
    # - Appropriate error type (user_input, backend_service, permission, system)
    # - User-friendly message
    # - Technical details
    # - Actionable suggestion
```

### Comprehensive Error Categorization

The `categorize_error()` function handles both AWS and Python exceptions:

```python
from shared.utils.error_handler import categorize_error

try:
    # Any operation
    result = operation()
except Exception as e:
    # Automatically categorized regardless of exception type
    tool_error = categorize_error(e)
    
    # Works for:
    # - AWS SDK errors (ClientError)
    # - Python built-in exceptions (ValueError, TypeError, etc.)
    # - Custom ToolError instances (returned unchanged)
```

### Context-Aware Suggestions

Get specific suggestions based on error context:

```python
from shared.utils.error_handler import get_error_suggestion, ErrorType

# Brand ID validation context
suggestion = get_error_suggestion(
    ErrorType.USER_INPUT,
    context="brandid_validation"
)
# Returns: "Please provide a valid brand ID (positive integer)."

# Execution ARN context
suggestion = get_error_suggestion(
    ErrorType.USER_INPUT,
    context="execution_arn"
)
# Returns: "Please provide a valid ARN in the format: arn:aws:states:region:account:execution:stateMachine:executionName"

# Throttling context
suggestion = get_error_suggestion(
    ErrorType.BACKEND_SERVICE,
    error_code="ThrottlingException"
)
# Returns: "The service is experiencing high load. Wait 5-10 seconds and retry your request."

# Timeout context (Requirement 9.3)
suggestion = get_error_suggestion(
    ErrorType.BACKEND_SERVICE,
    error_code="RequestTimeout"
)
# Returns: "The operation is taking longer than expected. Check system status and try again with a longer timeout."
```

## Complete Lambda Handler Example

Here's a complete example showing best practices:

```python
import json
import uuid
from shared.utils.error_handler import (
    create_error_response,
    UserInputError,
    BackendServiceError,
    validate_required_params,
)
from shared.utils.logger import get_logger

logger = get_logger(__name__)

def lambda_handler(event, context):
    """Example Lambda handler with comprehensive error handling."""
    request_id = str(uuid.uuid4())
    tool_name = "query_metadata"
    
    try:
        # Parse input
        body = json.loads(event.get("body", "{}"))
        
        # Validate required parameters
        validate_required_params(body, ["brandid"])
        
        brandid = body["brandid"]
        
        # Validate parameter type
        if not isinstance(brandid, int) or brandid <= 0:
            raise UserInputError(
                message="Invalid brand ID",
                details=f"Brand ID must be a positive integer, got: {brandid}",
                suggestion="Please provide a valid brand ID greater than 0"
            )
        
        # Perform AWS operation
        try:
            metadata = get_metadata_from_s3(brandid)
            
            if metadata is None:
                raise BackendServiceError(
                    message="Metadata not found",
                    details=f"No metadata exists for brand {brandid}",
                    suggestion="Please start a workflow to generate metadata for this brand"
                )
            
            # Success response
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "success": True,
                    "data": metadata,
                    "request_id": request_id
                })
            }
            
        except Exception as aws_error:
            # Automatically categorize AWS errors
            error_response = create_error_response(
                aws_error,
                request_id=request_id,
                tool_name=tool_name
            )
            
            return {
                "statusCode": 500,
                "body": json.dumps(error_response)
            }
    
    except UserInputError as e:
        # User input errors return 400
        error_response = create_error_response(e, request_id, tool_name)
        return {
            "statusCode": 400,
            "body": json.dumps(error_response)
        }
    
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in {tool_name}: {str(e)}", exc_info=True)
        error_response = create_error_response(e, request_id, tool_name)
        return {
            "statusCode": 500,
            "body": json.dumps(error_response)
        }
```

## Error Response Structure

All error responses follow this consistent structure:

```json
{
  "success": false,
  "error": {
    "type": "user_input|backend_service|permission|system",
    "message": "User-friendly error message",
    "details": "Technical details for logging and debugging",
    "suggestion": "Actionable next step for the user"
  },
  "request_id": "unique-request-id",
  "timestamp": "2024-01-15T10:30:00.000000+00:00"
}
```

## Testing

The error categorization system includes comprehensive unit tests:

```bash
# Run error categorization tests
python -m pytest tests/unit/test_error_categorization.py -v

# Test coverage
python -m pytest tests/unit/test_error_categorization.py --cov=shared.utils.error_handler
```

Test coverage includes:
- All four error categories
- AWS SDK error codes (40+ error codes)
- Python exception types
- Context-aware suggestions
- End-to-end error flows

## Best Practices

1. **Always use create_error_response()**: This ensures consistent error formatting and automatic categorization

2. **Provide context**: Include tool_name in error responses for better debugging

3. **Use specific error types**: When manually creating errors, use the most specific type (UserInputError, BackendServiceError, etc.)

4. **Include actionable suggestions**: Always provide suggestions that tell users what to do next

5. **Log appropriately**: The system automatically logs errors at appropriate levels:
   - SYSTEM errors: ERROR level with stack trace
   - PERMISSION errors: WARNING level
   - Other errors: INFO level

6. **Validate early**: Use `validate_required_params()` to catch missing parameters before processing

7. **Handle AWS errors**: Let the system automatically categorize AWS SDK errors - don't try to parse them manually

## Summary

The error categorization system provides:

✅ Automatic categorization of AWS SDK errors  
✅ Support for Python built-in exceptions  
✅ Context-aware error suggestions  
✅ Consistent error response format  
✅ Comprehensive test coverage (41 tests)  
✅ Requirements compliance (9.1, 9.2, 9.3, 9.4)  
✅ User-friendly error messages  
✅ Actionable resolution suggestions  

This system ensures that all errors in the Conversational Interface Agent are handled consistently and provide helpful feedback to users.
