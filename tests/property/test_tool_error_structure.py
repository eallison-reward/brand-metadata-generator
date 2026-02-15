"""Property-based tests for tool error structure.

**Validates: Requirements 7.9**
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone
from typing import Any, Dict
import json

from shared.utils.error_response import (
    format_error_response,
    create_user_input_error_response,
    create_backend_service_error_response,
)
from shared.utils.error_handler import (
    ToolError,
    ErrorType,
    UserInputError,
    BackendServiceError,
    PermissionError as ToolPermissionError,
    SystemError as ToolSystemError,
)

# Feature: conversational-interface-agent, Property 22: Tool Error Structure
# For any tool execution failure, the tool should return a structured error
# response containing an error message, error type, and sufficient context
# for the agent to explain the issue to the user.


# Hypothesis strategies for generating test data
@st.composite
def error_message_strategy(draw):
    """Generate realistic error messages."""
    templates = [
        "Parameter '{param}' is required",
        "Invalid {param}: {reason}",
        "Failed to {action}: {reason}",
        "{resource} not found",
        "Permission denied for {action}",
        "Service unavailable: {reason}",
    ]
    template = draw(st.sampled_from(templates))
    
    # Fill in template placeholders
    message = template.format(
        param=draw(st.sampled_from(["brandid", "execution_arn", "feedback_text", "query"])),
        reason=draw(st.sampled_from(["invalid format", "empty value", "timeout", "connection error"])),
        action=draw(st.sampled_from(["query database", "start workflow", "submit feedback"])),
        resource=draw(st.sampled_from(["Brand", "Workflow", "Metadata", "Execution"])),
    )
    return message


@st.composite
def request_id_strategy(draw):
    """Generate realistic request IDs."""
    return f"req-{draw(st.uuids())}"


@st.composite
def tool_name_strategy(draw):
    """Generate tool names."""
    return draw(st.sampled_from([
        "query_brands_to_check",
        "start_workflow",
        "check_workflow_status",
        "submit_feedback",
        "query_metadata",
        "execute_athena_query",
        "list_escalations",
        "get_workflow_stats",
    ]))


@pytest.mark.property
class TestToolErrorStructure:
    """Property 22: Tool Error Structure
    
    Property: For any tool execution failure, the tool should return a structured
    error response containing an error message, error type, and sufficient context
    for the agent to explain the issue to the user.
    
    Validates: Requirements 7.9
    """

    @given(
        message=error_message_strategy(),
        request_id=request_id_strategy(),
        tool_name=tool_name_strategy(),
    )
    @settings(max_examples=100, deadline=500)
    def test_user_input_error_structure(self, message, request_id, tool_name):
        """Property: User input errors have complete structured response.
        
        For any user input error, the response should contain all required
        fields with appropriate values.
        """
        response = create_user_input_error_response(
            message=message,
            request_id=request_id,
            tool_name=tool_name,
        )
        
        # Property 1: Response has success=False
        assert response["success"] is False
        
        # Property 2: Response has error object
        assert "error" in response
        assert isinstance(response["error"], dict)
        
        # Property 3: Error has type field
        assert "type" in response["error"]
        assert response["error"]["type"] == ErrorType.USER_INPUT.value
        
        # Property 4: Error has message field
        assert "message" in response["error"]
        assert isinstance(response["error"]["message"], str)
        assert len(response["error"]["message"]) > 0
        assert response["error"]["message"] == message
        
        # Property 5: Error has details field
        assert "details" in response["error"]
        assert isinstance(response["error"]["details"], str)
        assert len(response["error"]["details"]) > 0
        
        # Property 6: Error has suggestion field
        assert "suggestion" in response["error"]
        assert isinstance(response["error"]["suggestion"], str)
        assert len(response["error"]["suggestion"]) > 0
        
        # Property 7: Response has request_id
        assert "request_id" in response
        assert response["request_id"] == request_id
        
        # Property 8: Response has timestamp
        assert "timestamp" in response
        assert isinstance(response["timestamp"], str)
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(response["timestamp"].replace('Z', '+00:00'))
        
        # Property 9: Response has tool_name
        assert "tool_name" in response
        assert response["tool_name"] == tool_name
        
        # Property 10: Response is JSON serializable
        json_str = json.dumps(response)
        assert json_str is not None
        
        # Property 11: Deserialized response matches original
        deserialized = json.loads(json_str)
        assert deserialized["success"] == response["success"]
        assert deserialized["error"]["type"] == response["error"]["type"]

    @given(
        message=error_message_strategy(),
        request_id=request_id_strategy(),
        tool_name=tool_name_strategy(),
    )
    @settings(max_examples=100, deadline=500)
    def test_backend_service_error_structure(self, message, request_id, tool_name):
        """Property: Backend service errors have complete structured response.
        
        For any backend service error, the response should contain all required
        fields with appropriate values.
        """
        response = create_backend_service_error_response(
            message=message,
            request_id=request_id,
            tool_name=tool_name,
        )
        
        # Property 1: Response has success=False
        assert response["success"] is False
        
        # Property 2: Error type is backend_service
        assert response["error"]["type"] == ErrorType.BACKEND_SERVICE.value
        
        # Property 3: All required fields present
        assert "message" in response["error"]
        assert "details" in response["error"]
        assert "suggestion" in response["error"]
        assert "request_id" in response
        assert "timestamp" in response
        assert "tool_name" in response
        
        # Property 4: Message matches input
        assert response["error"]["message"] == message
        
        # Property 5: Response is JSON serializable
        json_str = json.dumps(response)
        assert json_str is not None

    @given(
        error_type=st.sampled_from([
            ErrorType.USER_INPUT,
            ErrorType.BACKEND_SERVICE,
            ErrorType.PERMISSION,
            ErrorType.SYSTEM,
        ]),
        message=error_message_strategy(),
        request_id=request_id_strategy(),
        tool_name=tool_name_strategy(),
    )
    @settings(max_examples=100, deadline=500)
    def test_format_error_response_structure(self, error_type, message, request_id, tool_name):
        """Property: format_error_response creates complete structured response.
        
        For any ToolError, format_error_response should create a response with
        all required fields.
        """
        # Create appropriate error based on type
        if error_type == ErrorType.USER_INPUT:
            error = UserInputError(message)
        elif error_type == ErrorType.BACKEND_SERVICE:
            error = BackendServiceError(message)
        elif error_type == ErrorType.PERMISSION:
            error = ToolPermissionError(message)
        else:
            error = ToolSystemError(message)
        
        response = format_error_response(
            error=error,
            request_id=request_id,
            tool_name=tool_name,
        )
        
        # Property 1: Response has success=False
        assert response["success"] is False
        
        # Property 2: Error type matches input
        assert response["error"]["type"] == error_type.value
        
        # Property 3: All required fields present
        required_fields = ["success", "error", "request_id", "timestamp", "tool_name"]
        for field in required_fields:
            assert field in response, f"Missing required field: {field}"
        
        # Property 4: Error object has all required fields
        error_fields = ["type", "message", "details", "suggestion"]
        for field in error_fields:
            assert field in response["error"], f"Missing error field: {field}"
        
        # Property 5: All string fields are non-empty
        assert len(response["error"]["message"]) > 0
        assert len(response["error"]["details"]) > 0
        assert len(response["error"]["suggestion"]) > 0
        
        # Property 6: Response is JSON serializable
        json_str = json.dumps(response)
        assert json_str is not None


@pytest.mark.property
class TestErrorResponseConsistency:
    """Property tests for error response consistency across tools."""

    @given(
        message=error_message_strategy(),
        request_id=request_id_strategy(),
        details=st.text(min_size=1, max_size=200),
        suggestion=st.text(min_size=1, max_size=200),
    )
    @settings(max_examples=50, deadline=500)
    def test_custom_details_and_suggestions(self, message, request_id, details, suggestion):
        """Property: Custom details and suggestions are preserved.
        
        When custom details and suggestions are provided, they should be
        included in the response exactly as given.
        """
        response = create_user_input_error_response(
            message=message,
            request_id=request_id,
            details=details,
            suggestion=suggestion,
        )
        
        # Property 1: Custom details are preserved
        assert response["error"]["details"] == details
        
        # Property 2: Custom suggestion is preserved
        assert response["error"]["suggestion"] == suggestion
        
        # Property 3: Message is preserved
        assert response["error"]["message"] == message

    @given(
        message=error_message_strategy(),
        request_id=request_id_strategy(),
    )
    @settings(max_examples=50, deadline=500)
    def test_default_details_and_suggestions(self, message, request_id):
        """Property: Default details and suggestions are provided when omitted.
        
        When details and suggestions are not provided, sensible defaults
        should be used.
        """
        response = create_user_input_error_response(
            message=message,
            request_id=request_id,
        )
        
        # Property 1: Details default to message
        assert response["error"]["details"] == message
        
        # Property 2: Suggestion has default value
        assert len(response["error"]["suggestion"]) > 0
        assert "check" in response["error"]["suggestion"].lower() or \
               "try" in response["error"]["suggestion"].lower()

    @given(
        num_errors=st.integers(min_value=1, max_value=5),
        request_id=request_id_strategy(),
    )
    @settings(max_examples=30, deadline=1000)
    def test_multiple_errors_have_consistent_structure(self, num_errors, request_id):
        """Property: Multiple errors from same request have consistent structure.
        
        All error responses should have the same structure regardless of
        error type or content.
        """
        error_types = [
            ErrorType.USER_INPUT,
            ErrorType.BACKEND_SERVICE,
            ErrorType.PERMISSION,
            ErrorType.SYSTEM,
        ]
        
        responses = []
        for i in range(num_errors):
            error_type = error_types[i % len(error_types)]
            message = f"Error {i}: Test error"
            
            if error_type == ErrorType.USER_INPUT:
                error = UserInputError(message)
            elif error_type == ErrorType.BACKEND_SERVICE:
                error = BackendServiceError(message)
            elif error_type == ErrorType.PERMISSION:
                error = ToolPermissionError(message)
            else:
                error = ToolSystemError(message)
            
            response = format_error_response(
                error=error,
                request_id=request_id,
                tool_name="test_tool",
            )
            responses.append(response)
        
        # Property 1: All responses have same top-level keys
        first_keys = set(responses[0].keys())
        for response in responses[1:]:
            assert set(response.keys()) == first_keys
        
        # Property 2: All error objects have same keys
        first_error_keys = set(responses[0]["error"].keys())
        for response in responses[1:]:
            assert set(response["error"].keys()) == first_error_keys
        
        # Property 3: All responses have success=False
        for response in responses:
            assert response["success"] is False
        
        # Property 4: All responses have same request_id
        for response in responses:
            assert response["request_id"] == request_id


@pytest.mark.property
class TestErrorResponseValidation:
    """Property tests for error response validation."""

    @given(
        message=error_message_strategy(),
        request_id=request_id_strategy(),
        tool_name=tool_name_strategy(),
    )
    @settings(max_examples=50, deadline=500)
    def test_error_type_is_valid_enum(self, message, request_id, tool_name):
        """Property: Error type is always a valid ErrorType enum value.
        
        The error type field should always contain a valid ErrorType enum value.
        """
        response = create_user_input_error_response(
            message=message,
            request_id=request_id,
            tool_name=tool_name,
        )
        
        # Property 1: Error type is a valid enum value
        valid_types = [e.value for e in ErrorType]
        assert response["error"]["type"] in valid_types
        
        # Property 2: Error type can be converted back to enum
        error_type = ErrorType(response["error"]["type"])
        assert isinstance(error_type, ErrorType)

    @given(
        message=error_message_strategy(),
        request_id=request_id_strategy(),
    )
    @settings(max_examples=50, deadline=500)
    def test_timestamp_is_valid_iso_format(self, message, request_id):
        """Property: Timestamp is always valid ISO 8601 format.
        
        The timestamp field should always be a valid ISO 8601 datetime string.
        """
        response = create_user_input_error_response(
            message=message,
            request_id=request_id,
        )
        
        # Property 1: Timestamp can be parsed as datetime
        timestamp_str = response["timestamp"]
        parsed_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        assert isinstance(parsed_dt, datetime)
        
        # Property 2: Timestamp is recent (within last minute)
        now = datetime.now(timezone.utc)
        time_diff = abs((now - parsed_dt).total_seconds())
        assert time_diff < 60, f"Timestamp is too old: {time_diff} seconds"

    @given(
        error_type=st.sampled_from([
            ErrorType.USER_INPUT,
            ErrorType.BACKEND_SERVICE,
            ErrorType.PERMISSION,
            ErrorType.SYSTEM,
        ]),
        message=error_message_strategy(),
    )
    @settings(max_examples=50, deadline=500)
    def test_suggestion_is_actionable(self, error_type, message):
        """Property: Suggestion field contains actionable guidance.
        
        The suggestion field should contain helpful, actionable text that
        guides the user on what to do next.
        """
        # Create error based on type
        if error_type == ErrorType.USER_INPUT:
            error = UserInputError(message)
        elif error_type == ErrorType.BACKEND_SERVICE:
            error = BackendServiceError(message)
        elif error_type == ErrorType.PERMISSION:
            error = ToolPermissionError(message)
        else:
            error = ToolSystemError(message)
        
        response = format_error_response(
            error=error,
            request_id="test-request",
        )
        
        suggestion = response["error"]["suggestion"]
        
        # Property 1: Suggestion is non-empty
        assert len(suggestion) > 0
        
        # Property 2: Suggestion contains actionable words
        actionable_words = [
            "check", "verify", "try", "contact", "provide",
            "ensure", "review", "confirm", "retry", "wait",
        ]
        has_actionable_word = any(word in suggestion.lower() for word in actionable_words)
        assert has_actionable_word, f"Suggestion lacks actionable guidance: {suggestion}"
        
        # Property 3: Suggestion is a complete sentence (ends with punctuation)
        assert suggestion[-1] in ['.', '!', '?'], f"Suggestion is not a complete sentence: {suggestion}"
