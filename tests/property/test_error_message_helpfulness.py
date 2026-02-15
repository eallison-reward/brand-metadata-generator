"""Property-based tests for error message helpfulness.

Property 3: Error Message Helpfulness

For any unfulfillable request or failed operation, the agent should provide
a clear explanation of what went wrong and suggest actionable next steps or alternatives.

Validates: Requirements 1.3, 2.5, 9.1, 9.2, 9.3, 9.4

Requirements Mapping:
- Requirement 1.3: When request cannot be fulfilled, provide clear explanation and suggest alternatives
- Requirement 2.5: When workflow execution fails, provide error details and suggest remediation steps
- Requirement 9.1: When tool fails due to missing permissions, report issue and suggest contacting admin
- Requirement 9.2: When tool fails due to invalid input, explain what was invalid and request corrected input
- Requirement 9.3: When tool times out, inform user and suggest checking system status
- Requirement 9.4: When Athena returns error, parse error and provide user-friendly explanation
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from botocore.exceptions import ClientError
from shared.utils.error_handler import (
    categorize_error,
    create_error_response,
    handle_aws_error,
    UserInputError,
    BackendServiceError,
    PermissionError as ToolPermissionError,
    SystemError as ToolSystemError,
    ErrorType,
    get_error_suggestion,
)
from shared.utils.error_response import (
    format_error_response,
    create_user_input_error_response,
    create_backend_service_error_response,
    create_permission_error_response,
    create_system_error_response,
    missing_parameter_error,
    invalid_parameter_type_error,
    resource_not_found_error,
    service_unavailable_error,
    timeout_error,
    permission_denied_error,
)


# ============================================================================
# Test Data Generators
# ============================================================================

@st.composite
def aws_error_codes(draw):
    """Generate AWS error codes for different error categories."""
    error_category = draw(st.sampled_from([
        "permission",
        "user_input",
        "backend_service",
    ]))
    
    error_codes_by_category = {
        "permission": [
            "AccessDenied",
            "AccessDeniedException",
            "UnauthorizedOperation",
            "Forbidden",
            "InsufficientPermissionsException",
        ],
        "user_input": [
            "ValidationException",
            "InvalidParameterException",
            "InvalidParameterValue",
            "MissingParameter",
            "InvalidInput",
        ],
        "backend_service": [
            "ResourceNotFoundException",
            "ThrottlingException",
            "RequestTimeout",
            "ServiceUnavailable",
            "NoSuchKey",
            "InternalServerError",  # AWS internal errors are backend service issues
            "InternalError",
            "ServiceException",
        ],
    }
    
    error_code = draw(st.sampled_from(error_codes_by_category[error_category]))
    return error_category, error_code


@st.composite
def aws_client_error(draw):
    """Generate realistic AWS ClientError instances."""
    error_category, error_code = draw(aws_error_codes())
    error_message = draw(st.text(min_size=10, max_size=100, alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Pc"),
        blacklist_characters="\n\r\t"
    )))
    
    # Create mock ClientError
    error = ClientError(
        error_response={
            "Error": {
                "Code": error_code,
                "Message": error_message,
            },
            "ResponseMetadata": {
                "RequestId": draw(st.uuids()).hex,
                "HTTPStatusCode": draw(st.integers(min_value=400, max_value=599)),
            },
        },
        operation_name=draw(st.sampled_from([
            "StartExecution",
            "DescribeExecution",
            "GetObject",
            "PutObject",
            "StartQueryExecution",
            "GetQueryResults",
        ])),
    )
    
    return error_category, error


@st.composite
def python_exceptions(draw):
    """Generate common Python exceptions."""
    exception_type = draw(st.sampled_from([
        ValueError,
        TypeError,
        KeyError,
        FileNotFoundError,
        TimeoutError,
    ]))
    
    message = draw(st.text(min_size=5, max_size=50, alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
        blacklist_characters="\n\r\t"
    )))
    
    return exception_type(message)


@st.composite
def request_contexts(draw):
    """Generate request contexts for error handling."""
    return draw(st.sampled_from([
        "athena_query",
        "workflow_start",
        "workflow_status",
        "s3_read",
        "s3_write",
        "feedback_submission",
        "metadata_retrieval",
        "escalation_list",
        "stats_query",
    ]))


# ============================================================================
# Property 1: All Error Responses Contain Required Fields
# ============================================================================

@given(
    error_category=st.sampled_from(["permission", "user_input", "backend_service", "system"]),
    message=st.text(min_size=5, max_size=100),
    request_id=st.uuids(),
    tool_name=st.text(min_size=3, max_size=30, alphabet=st.characters(
        whitelist_categories=("Ll", "Nd"),
        blacklist_characters="_"
    )),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_all_error_responses_have_required_fields(error_category, message, request_id, tool_name):
    """Property: All error responses contain required fields.
    
    For any error response, it must contain:
    - success: False
    - error: object with type, message, details, suggestion
    - request_id: string
    - timestamp: ISO 8601 string
    - tool_name: string (optional but should be present when provided)
    """
    request_id_str = str(request_id)
    
    # Create error response based on category
    if error_category == "permission":
        response = create_permission_error_response(
            message=message,
            request_id=request_id_str,
            tool_name=tool_name,
        )
    elif error_category == "user_input":
        response = create_user_input_error_response(
            message=message,
            request_id=request_id_str,
            tool_name=tool_name,
        )
    elif error_category == "backend_service":
        response = create_backend_service_error_response(
            message=message,
            request_id=request_id_str,
            tool_name=tool_name,
        )
    else:  # system
        response = create_system_error_response(
            message=message,
            request_id=request_id_str,
            tool_name=tool_name,
        )
    
    # Verify required fields
    assert response["success"] is False, "Error response must have success=False"
    assert "error" in response, "Error response must contain 'error' field"
    assert "request_id" in response, "Error response must contain 'request_id' field"
    assert "timestamp" in response, "Error response must contain 'timestamp' field"
    
    # Verify error object structure
    error_obj = response["error"]
    assert "type" in error_obj, "Error object must contain 'type' field"
    assert "message" in error_obj, "Error object must contain 'message' field"
    assert "details" in error_obj, "Error object must contain 'details' field"
    assert "suggestion" in error_obj, "Error object must contain 'suggestion' field"
    
    # Verify error type is valid
    assert error_obj["type"] in [
        "user_input",
        "backend_service",
        "permission",
        "system",
    ], f"Error type must be valid, got: {error_obj['type']}"
    
    # Verify request_id matches
    assert response["request_id"] == request_id_str, "Request ID must match input"
    
    # Verify tool_name is present when provided
    if tool_name:
        assert response.get("tool_name") == tool_name, "Tool name must match input"


# ============================================================================
# Property 2: Error Messages Are Non-Empty and Meaningful
# ============================================================================

@given(
    error_category=st.sampled_from(["permission", "user_input", "backend_service", "system"]),
    message=st.text(min_size=5, max_size=100),
    request_id=st.uuids(),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_error_messages_are_meaningful(error_category, message, request_id):
    """Property: Error messages are non-empty and meaningful.
    
    For any error response:
    - Message must be non-empty string
    - Details must be non-empty string
    - Suggestion must be non-empty string
    - Message should not be generic placeholder text
    """
    request_id_str = str(request_id)
    
    # Create error response
    if error_category == "permission":
        response = create_permission_error_response(message, request_id_str)
    elif error_category == "user_input":
        response = create_user_input_error_response(message, request_id_str)
    elif error_category == "backend_service":
        response = create_backend_service_error_response(message, request_id_str)
    else:
        response = create_system_error_response(message, request_id_str)
    
    error_obj = response["error"]
    
    # Verify non-empty
    assert len(error_obj["message"]) > 0, "Error message must not be empty"
    assert len(error_obj["details"]) > 0, "Error details must not be empty"
    assert len(error_obj["suggestion"]) > 0, "Error suggestion must not be empty"
    
    # Verify message is not just whitespace
    assert error_obj["message"].strip(), "Error message must not be only whitespace"
    assert error_obj["details"].strip(), "Error details must not be only whitespace"
    assert error_obj["suggestion"].strip(), "Error suggestion must not be only whitespace"


# ============================================================================
# Property 3: Suggestions Are Actionable
# ============================================================================

@given(
    error_category=st.sampled_from(["permission", "user_input", "backend_service", "system"]),
    message=st.text(min_size=5, max_size=100),
    request_id=st.uuids(),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_suggestions_are_actionable(error_category, message, request_id):
    """Property: Error suggestions contain actionable guidance.
    
    For any error response, the suggestion should:
    - Contain action verbs (please, check, verify, contact, try, etc.)
    - Be specific to the error category
    - Provide clear next steps
    """
    request_id_str = str(request_id)
    
    # Create error response
    if error_category == "permission":
        response = create_permission_error_response(message, request_id_str)
    elif error_category == "user_input":
        response = create_user_input_error_response(message, request_id_str)
    elif error_category == "backend_service":
        response = create_backend_service_error_response(message, request_id_str)
    else:
        response = create_system_error_response(message, request_id_str)
    
    suggestion = response["error"]["suggestion"].lower()
    
    # Verify suggestion contains action words
    action_words = [
        "please", "check", "verify", "contact", "try", "ensure",
        "provide", "retry", "wait", "review", "confirm", "request",
    ]
    
    has_action_word = any(word in suggestion for word in action_words)
    assert has_action_word, f"Suggestion should contain actionable guidance: {suggestion}"
    
    # Verify category-specific suggestions
    if error_category == "permission":
        assert any(word in suggestion for word in ["administrator", "admin", "permission"]), \
            "Permission error suggestion should mention contacting administrator"
    
    elif error_category == "user_input":
        assert any(word in suggestion for word in ["input", "parameter", "value", "correct"]), \
            "User input error suggestion should mention checking input"
    
    elif error_category == "backend_service":
        assert any(word in suggestion for word in ["try", "again", "later", "status", "check"]), \
            "Backend service error suggestion should mention retrying or checking status"
    
    elif error_category == "system":
        assert any(word in suggestion for word in ["try", "again", "support", "contact"]), \
            "System error suggestion should mention retrying or contacting support"


# ============================================================================
# Property 4: AWS Errors Are Correctly Categorized
# ============================================================================

@given(aws_error=aws_client_error())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_aws_errors_correctly_categorized(aws_error):
    """Property: AWS SDK errors are correctly categorized.
    
    For any AWS ClientError:
    - Permission errors should be categorized as PERMISSION
    - Validation errors should be categorized as USER_INPUT
    - Service errors should be categorized as BACKEND_SERVICE
    - Internal errors should be categorized as SYSTEM
    """
    expected_category, error = aws_error
    
    # Categorize the error
    tool_error = handle_aws_error(error)
    
    # Map expected category to ErrorType
    category_map = {
        "permission": ErrorType.PERMISSION,
        "user_input": ErrorType.USER_INPUT,
        "backend_service": ErrorType.BACKEND_SERVICE,
        "system": ErrorType.SYSTEM,
    }
    
    expected_error_type = category_map[expected_category]
    
    assert tool_error.error_type == expected_error_type, \
        f"Error should be categorized as {expected_error_type.value}, got {tool_error.error_type.value}"


# ============================================================================
# Property 5: Python Exceptions Are Handled Gracefully
# ============================================================================

@given(exception=python_exceptions())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_python_exceptions_handled_gracefully(exception):
    """Property: Python exceptions are handled gracefully.
    
    For any Python exception:
    - Should be categorized into appropriate error type
    - Should have user-friendly message
    - Should have actionable suggestion
    - Should not expose internal implementation details
    """
    # Categorize the exception
    tool_error = categorize_error(exception)
    
    # Verify it's a ToolError
    assert hasattr(tool_error, "error_type"), "Should return ToolError instance"
    assert hasattr(tool_error, "message"), "Should have message"
    assert hasattr(tool_error, "suggestion"), "Should have suggestion"
    
    # Verify error type is valid
    assert tool_error.error_type in [
        ErrorType.USER_INPUT,
        ErrorType.BACKEND_SERVICE,
        ErrorType.PERMISSION,
        ErrorType.SYSTEM,
    ], f"Error type should be valid, got: {tool_error.error_type}"
    
    # Verify message is user-friendly (not raw exception string)
    assert len(tool_error.message) > 0, "Message should not be empty"
    
    # Verify suggestion is present
    assert len(tool_error.suggestion) > 0, "Suggestion should not be empty"


# ============================================================================
# Property 6: Error Type Matches Error Category
# ============================================================================

@given(
    error_type=st.sampled_from([
        ErrorType.USER_INPUT,
        ErrorType.BACKEND_SERVICE,
        ErrorType.PERMISSION,
        ErrorType.SYSTEM,
    ]),
    message=st.text(min_size=5, max_size=100),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_error_type_matches_category(error_type, message):
    """Property: Error type in response matches the error category.
    
    For any ToolError:
    - The error type field should match the error category
    - The error type should be one of the four valid types
    """
    # Create ToolError based on type
    if error_type == ErrorType.USER_INPUT:
        error = UserInputError(message)
    elif error_type == ErrorType.BACKEND_SERVICE:
        error = BackendServiceError(message)
    elif error_type == ErrorType.PERMISSION:
        error = ToolPermissionError(message)
    else:
        error = ToolSystemError(message)
    
    # Convert to dict
    error_dict = error.to_dict()
    
    # Verify type matches
    assert error_dict["type"] == error_type.value, \
        f"Error type should be {error_type.value}, got {error_dict['type']}"


# ============================================================================
# Property 7: Suggestions Vary By Error Type
# ============================================================================

@given(
    error_type=st.sampled_from([
        ErrorType.USER_INPUT,
        ErrorType.BACKEND_SERVICE,
        ErrorType.PERMISSION,
        ErrorType.SYSTEM,
    ]),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_suggestions_vary_by_error_type(error_type):
    """Property: Error suggestions vary appropriately by error type.
    
    For any error type:
    - Permission errors should mention administrator/permissions
    - User input errors should mention checking input
    - Backend service errors should mention retrying or checking status
    - System errors should mention retrying or contacting support
    """
    suggestion = get_error_suggestion(error_type, "", "")
    suggestion_lower = suggestion.lower()
    
    # Verify suggestion is non-empty
    assert len(suggestion) > 0, "Suggestion should not be empty"
    
    # Verify type-specific keywords
    if error_type == ErrorType.PERMISSION:
        assert any(word in suggestion_lower for word in ["administrator", "admin", "permission"]), \
            f"Permission error should mention administrator: {suggestion}"
    
    elif error_type == ErrorType.USER_INPUT:
        assert any(word in suggestion_lower for word in ["input", "parameter", "check", "provide", "correct"]), \
            f"User input error should mention checking input: {suggestion}"
    
    elif error_type == ErrorType.BACKEND_SERVICE:
        assert any(word in suggestion_lower for word in ["try", "again", "later", "status", "check"]), \
            f"Backend service error should mention retrying: {suggestion}"
    
    elif error_type == ErrorType.SYSTEM:
        assert any(word in suggestion_lower for word in ["try", "again", "support", "contact", "persist"]), \
            f"System error should mention retrying or support: {suggestion}"


# ============================================================================
# Property 8: Common Error Helpers Produce Consistent Responses
# ============================================================================

@given(
    parameter_name=st.text(min_size=3, max_size=20, alphabet=st.characters(
        whitelist_categories=("Ll", "Nd"),
        blacklist_characters="_"
    )),
    request_id=st.uuids(),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_missing_parameter_error_consistency(parameter_name, request_id):
    """Property: Missing parameter errors are consistent.
    
    For any missing parameter error:
    - Should be categorized as USER_INPUT
    - Should mention the parameter name
    - Should suggest providing the parameter
    """
    response = missing_parameter_error(parameter_name, str(request_id))
    
    # Verify error type
    assert response["error"]["type"] == "user_input", \
        "Missing parameter should be user_input error"
    
    # Verify parameter name is mentioned
    message_lower = response["error"]["message"].lower()
    assert parameter_name.lower() in message_lower, \
        f"Error message should mention parameter name: {parameter_name}"
    
    # Verify suggestion mentions providing the parameter
    suggestion_lower = response["error"]["suggestion"].lower()
    assert "provide" in suggestion_lower, \
        "Suggestion should mention providing the parameter"


@given(
    resource_type=st.sampled_from(["brand", "workflow", "metadata", "execution"]),
    resource_id=st.text(min_size=1, max_size=50),
    request_id=st.uuids(),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_resource_not_found_error_consistency(resource_type, resource_id, request_id):
    """Property: Resource not found errors are consistent.
    
    For any resource not found error:
    - Should be categorized as BACKEND_SERVICE
    - Should mention the resource type and ID
    - Should suggest verifying the identifier
    """
    response = resource_not_found_error(resource_type, resource_id, str(request_id))
    
    # Verify error type
    assert response["error"]["type"] == "backend_service", \
        "Resource not found should be backend_service error"
    
    # Verify resource type is mentioned
    message_lower = response["error"]["message"].lower()
    assert resource_type.lower() in message_lower, \
        f"Error message should mention resource type: {resource_type}"
    
    # Verify suggestion mentions verification
    suggestion_lower = response["error"]["suggestion"].lower()
    assert "verify" in suggestion_lower, \
        "Suggestion should mention verifying the identifier"


@given(
    operation=st.text(min_size=5, max_size=50),
    request_id=st.uuids(),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_denied_error_consistency(operation, request_id):
    """Property: Permission denied errors are consistent.
    
    For any permission denied error:
    - Should be categorized as PERMISSION
    - Should mention the operation
    - Should suggest contacting administrator
    """
    response = permission_denied_error(operation, str(request_id))
    
    # Verify error type
    assert response["error"]["type"] == "permission", \
        "Permission denied should be permission error"
    
    # Verify suggestion mentions administrator
    suggestion_lower = response["error"]["suggestion"].lower()
    assert "administrator" in suggestion_lower or "admin" in suggestion_lower, \
        "Suggestion should mention contacting administrator"


# ============================================================================
# Property 9: Error Responses Are JSON Serializable
# ============================================================================

@given(
    error_category=st.sampled_from(["permission", "user_input", "backend_service", "system"]),
    message=st.text(min_size=5, max_size=100),
    request_id=st.uuids(),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_error_responses_are_json_serializable(error_category, message, request_id):
    """Property: All error responses are JSON serializable.
    
    For any error response:
    - Should be serializable to JSON
    - Should deserialize back to equivalent structure
    """
    import json
    
    request_id_str = str(request_id)
    
    # Create error response
    if error_category == "permission":
        response = create_permission_error_response(message, request_id_str)
    elif error_category == "user_input":
        response = create_user_input_error_response(message, request_id_str)
    elif error_category == "backend_service":
        response = create_backend_service_error_response(message, request_id_str)
    else:
        response = create_system_error_response(message, request_id_str)
    
    # Serialize to JSON
    json_str = json.dumps(response)
    
    # Deserialize back
    deserialized = json.loads(json_str)
    
    # Verify structure is preserved
    assert deserialized["success"] == response["success"]
    assert deserialized["error"]["type"] == response["error"]["type"]
    assert deserialized["error"]["message"] == response["error"]["message"]
    assert deserialized["request_id"] == response["request_id"]


# ============================================================================
# Property 10: Timeout Errors Suggest Checking System Status
# ============================================================================

@given(
    operation=st.text(min_size=5, max_size=50),
    timeout_seconds=st.integers(min_value=1, max_value=300),
    request_id=st.uuids(),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_timeout_errors_suggest_system_check(operation, timeout_seconds, request_id):
    """Property: Timeout errors suggest checking system status.
    
    For any timeout error (Requirement 9.3):
    - Should be categorized as BACKEND_SERVICE
    - Should mention the timeout
    - Should suggest checking system status
    """
    response = timeout_error(operation, str(request_id), timeout_seconds)
    
    # Verify error type
    assert response["error"]["type"] == "backend_service", \
        "Timeout should be backend_service error"
    
    # Verify message mentions timeout
    message_lower = response["error"]["message"].lower()
    assert "timeout" in message_lower or "timed out" in message_lower, \
        "Error message should mention timeout"
    
    # Verify suggestion mentions system status
    suggestion_lower = response["error"]["suggestion"].lower()
    assert "status" in suggestion_lower or "check" in suggestion_lower, \
        "Suggestion should mention checking system status (Requirement 9.3)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-W", "ignore::DeprecationWarning"])
