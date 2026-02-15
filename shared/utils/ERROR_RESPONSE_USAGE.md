# Error Response Utility Usage Guide

This guide demonstrates how to use the `error_response.py` utility for creating consistent, user-friendly error responses across all tool Lambda functions.

## Overview

The error response utility provides:
- Structured error response formatting
- Four error categories (user_input, backend_service, permission, system)
- Helper functions for common error scenarios
- Integration with existing `error_handler.py` module

## Basic Usage

### 1. Format a ToolError

```python
from shared.utils.error_handler import UserInputError
from shared.utils.error_response import format_error_response

# Create a ToolError
error = UserInputError(
    message="Invalid brand ID",
    details="Brand ID must be a positive integer",
    suggestion="Please provide a valid brand ID"
)

# Format it into a response
response = format_error_response(error, request_id="req-123", tool_name="query_metadata")
```

### 2. Create Error Responses Directly

```python
from shared.utils.error_response import (
    create_user_input_error_response,
    create_backend_service_error_response,
    create_permission_error_response,
    create_system_error_response,
)

# User input error
response = create_user_input_error_response(
    message="Missing required parameter",
    request_id="req-123",
    details="Parameter 'brandid' is required",
    suggestion="Please provide brandid",
    tool_name="start_workflow"
)

# Backend service error
response = create_backend_service_error_response(
    message="Athena query failed",
    request_id="req-456",
    details="Query execution timed out",
    suggestion="Please try again later"
)

# Permission error
response = create_permission_error_response(
    message="Access denied",
    request_id="req-789",
    details="Insufficient IAM permissions"
)

# System error
response = create_system_error_response(
    message="Unexpected error occurred",
    request_id="req-999"
)
```

## Common Error Scenarios

The utility provides helper functions for common error scenarios:

### Missing Parameter

```python
from shared.utils.error_response import missing_parameter_error

response = missing_parameter_error(
    parameter_name="brandid",
    request_id="req-123",
    tool_name="start_workflow"
)
```

### Invalid Parameter Type

```python
from shared.utils.error_response import invalid_parameter_type_error

response = invalid_parameter_type_error(
    parameter_name="limit",
    expected_type="integer",
    request_id="req-456"
)
```

### Resource Not Found

```python
from shared.utils.error_response import resource_not_found_error

response = resource_not_found_error(
    resource_type="brand",
    resource_id="12345",
    request_id="req-789"
)
```

### Service Unavailable

```python
from shared.utils.error_response import service_unavailable_error

response = service_unavailable_error(
    service_name="Athena",
    request_id="req-111",
    details="Connection timeout"
)
```

### Timeout Error

```python
from shared.utils.error_response import timeout_error

response = timeout_error(
    operation="Athena query execution",
    request_id="req-222",
    timeout_seconds=30
)
```

### Permission Denied

```python
from shared.utils.error_response import permission_denied_error

response = permission_denied_error(
    operation="Start workflow",
    request_id="req-444",
    details="IAM role lacks stepfunctions:StartExecution"
)
```

### Invalid Query

```python
from shared.utils.error_response import invalid_query_error

response = invalid_query_error(
    query_issue="Invalid SQL syntax",
    request_id="req-555"
)
```

### Workflow Execution Error

```python
from shared.utils.error_response import workflow_execution_error

response = workflow_execution_error(
    execution_arn="arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123",
    error_message="Task failed: InvalidBrandData",
    request_id="req-666"
)
```

### Empty Results (Not an Error)

```python
from shared.utils.error_response import empty_result_error

# Note: This returns success=True with helpful message
response = empty_result_error(
    query_description="brands with confidence < 0.5",
    request_id="req-777",
    tool_name="execute_athena_query"
)
```

## Response Structure

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
  "timestamp": "2024-01-15T10:30:00.000000+00:00",
  "tool_name": "query_metadata"
}
```

## Lambda Handler Example

Here's a complete example of using the error response utility in a Lambda handler:

```python
import json
import uuid
from shared.utils.error_response import (
    missing_parameter_error,
    resource_not_found_error,
    service_unavailable_error,
    create_system_error_response,
)
from shared.utils.error_handler import handle_aws_error
from shared.utils.logger import get_logger

logger = get_logger(__name__)

def lambda_handler(event, context):
    """Example Lambda handler with error response utility."""
    request_id = str(uuid.uuid4())
    tool_name = "example_tool"
    
    try:
        # Parse input
        body = json.loads(event.get("body", "{}"))
        
        # Validate required parameters
        if "brandid" not in body:
            return {
                "statusCode": 400,
                "body": json.dumps(missing_parameter_error(
                    parameter_name="brandid",
                    request_id=request_id,
                    tool_name=tool_name
                ))
            }
        
        brandid = body["brandid"]
        
        # Perform operation
        try:
            result = perform_operation(brandid)
            
            if result is None:
                return {
                    "statusCode": 404,
                    "body": json.dumps(resource_not_found_error(
                        resource_type="brand",
                        resource_id=str(brandid),
                        request_id=request_id,
                        tool_name=tool_name
                    ))
                }
            
            # Success response
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "success": True,
                    "data": result,
                    "request_id": request_id
                })
            }
            
        except Exception as aws_error:
            # Handle AWS SDK errors
            tool_error = handle_aws_error(aws_error)
            return {
                "statusCode": 500,
                "body": json.dumps(format_error_response(
                    tool_error,
                    request_id=request_id,
                    tool_name=tool_name
                ))
            }
    
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in {tool_name}: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps(create_system_error_response(
                message="An unexpected error occurred",
                request_id=request_id,
                details=str(e),
                tool_name=tool_name
            ))
        }
```

## Best Practices

1. **Always include request_id**: This enables tracing and debugging
2. **Use specific error helpers**: They provide better error messages than generic functions
3. **Include tool_name**: Helps identify which Lambda function had the error
4. **Provide actionable suggestions**: Tell users what they can do to fix the issue
5. **Log technical details**: Use the `details` field for debugging information
6. **Keep messages user-friendly**: Avoid technical jargon in the `message` field
7. **Use appropriate error types**: Choose the correct category for better error handling

## Error Categories

- **user_input**: Invalid parameters, missing data, malformed requests
- **backend_service**: AWS service failures, timeouts, resource not found
- **permission**: IAM permission denials, access restrictions
- **system**: Unexpected errors, internal failures, unhandled exceptions

## Integration with error_handler.py

The error response utility works seamlessly with the existing `error_handler.py` module:

```python
from shared.utils.error_handler import UserInputError, handle_aws_error
from shared.utils.error_response import format_error_response

# Create a ToolError using error_handler
error = UserInputError("Invalid input")

# Format it using error_response
response = format_error_response(error, request_id="req-123")

# Or handle AWS errors
try:
    # AWS SDK call
    pass
except Exception as e:
    tool_error = handle_aws_error(e)
    response = format_error_response(tool_error, request_id="req-123")
```
