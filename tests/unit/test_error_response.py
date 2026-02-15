"""Unit tests for error response utilities."""

import pytest
from datetime import datetime
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
    invalid_query_error,
    workflow_execution_error,
    empty_result_error,
)
from shared.utils.error_handler import (
    ErrorType,
    UserInputError,
    BackendServiceError,
    PermissionError,
    SystemError,
)


class TestFormatErrorResponse:
    """Tests for format_error_response function."""
    
    def test_format_user_input_error(self):
        """Test formatting a UserInputError."""
        error = UserInputError(
            message="Invalid brand ID",
            details="Brand ID must be a positive integer",
            suggestion="Please provide a valid brand ID",
        )
        
        response = format_error_response(error, "req-123", "test_tool")
        
        assert response["success"] is False
        assert response["error"]["type"] == "user_input"
        assert response["error"]["message"] == "Invalid brand ID"
        assert response["error"]["details"] == "Brand ID must be a positive integer"
        assert response["error"]["suggestion"] == "Please provide a valid brand ID"
        assert response["request_id"] == "req-123"
        assert response["tool_name"] == "test_tool"
        assert "timestamp" in response
    
    def test_format_backend_service_error(self):
        """Test formatting a BackendServiceError."""
        error = BackendServiceError(
            message="Athena query failed",
            details="Query execution timed out",
        )
        
        response = format_error_response(error, "req-456")
        
        assert response["success"] is False
        assert response["error"]["type"] == "backend_service"
        assert response["error"]["message"] == "Athena query failed"
        assert response["error"]["details"] == "Query execution timed out"
        assert response["request_id"] == "req-456"
    
    def test_format_permission_error(self):
        """Test formatting a PermissionError."""
        error = PermissionError(
            message="Access denied",
            details="Insufficient IAM permissions",
        )
        
        response = format_error_response(error, "req-789")
        
        assert response["success"] is False
        assert response["error"]["type"] == "permission"
        assert response["error"]["message"] == "Access denied"
    
    def test_format_system_error(self):
        """Test formatting a SystemError."""
        error = SystemError(
            message="Unexpected error",
            details="Internal server error",
        )
        
        response = format_error_response(error, "req-999")
        
        assert response["success"] is False
        assert response["error"]["type"] == "system"
        assert response["error"]["message"] == "Unexpected error"


class TestCreateErrorResponses:
    """Tests for create_*_error_response functions."""
    
    def test_create_user_input_error_response(self):
        """Test creating user input error response."""
        response = create_user_input_error_response(
            message="Missing parameter",
            request_id="req-123",
            details="Parameter 'brandid' is required",
            suggestion="Please provide brandid",
            tool_name="query_metadata",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "user_input"
        assert response["error"]["message"] == "Missing parameter"
        assert response["error"]["details"] == "Parameter 'brandid' is required"
        assert response["error"]["suggestion"] == "Please provide brandid"
        assert response["tool_name"] == "query_metadata"
    
    def test_create_user_input_error_response_with_defaults(self):
        """Test creating user input error response with default values."""
        response = create_user_input_error_response(
            message="Invalid input",
            request_id="req-123",
        )
        
        assert response["error"]["details"] == "Invalid input"
        assert "check your input parameters" in response["error"]["suggestion"]
    
    def test_create_backend_service_error_response(self):
        """Test creating backend service error response."""
        response = create_backend_service_error_response(
            message="Service unavailable",
            request_id="req-456",
            details="Step Functions API error",
            suggestion="Retry in a few moments",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "backend_service"
        assert response["error"]["message"] == "Service unavailable"
    
    def test_create_permission_error_response(self):
        """Test creating permission error response."""
        response = create_permission_error_response(
            message="Access denied",
            request_id="req-789",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "permission"
        assert "administrator" in response["error"]["suggestion"]
    
    def test_create_system_error_response(self):
        """Test creating system error response."""
        response = create_system_error_response(
            message="Internal error",
            request_id="req-999",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "system"
        assert "contact support" in response["error"]["suggestion"]


class TestCommonErrorHelpers:
    """Tests for common error scenario helper functions."""
    
    def test_missing_parameter_error(self):
        """Test missing parameter error helper."""
        response = missing_parameter_error(
            parameter_name="brandid",
            request_id="req-123",
            tool_name="start_workflow",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "user_input"
        assert "brandid" in response["error"]["message"]
        assert "provide a value" in response["error"]["suggestion"]
        assert response["tool_name"] == "start_workflow"
    
    def test_invalid_parameter_type_error(self):
        """Test invalid parameter type error helper."""
        response = invalid_parameter_type_error(
            parameter_name="limit",
            expected_type="integer",
            request_id="req-456",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "user_input"
        assert "limit" in response["error"]["message"]
        assert "integer" in response["error"]["message"]
        assert "valid integer" in response["error"]["suggestion"]
    
    def test_resource_not_found_error(self):
        """Test resource not found error helper."""
        response = resource_not_found_error(
            resource_type="brand",
            resource_id="12345",
            request_id="req-789",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "backend_service"
        assert "Brand not found" in response["error"]["message"]
        assert "12345" in response["error"]["message"]
        assert "verify" in response["error"]["suggestion"]
    
    def test_service_unavailable_error(self):
        """Test service unavailable error helper."""
        response = service_unavailable_error(
            service_name="Athena",
            request_id="req-111",
            details="Connection timeout",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "backend_service"
        assert "Athena" in response["error"]["message"]
        assert "unavailable" in response["error"]["message"]
        assert response["error"]["details"] == "Connection timeout"
    
    def test_timeout_error_with_duration(self):
        """Test timeout error helper with duration."""
        response = timeout_error(
            operation="Athena query execution",
            request_id="req-222",
            timeout_seconds=30,
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "backend_service"
        assert "timed out" in response["error"]["message"]
        assert "30 seconds" in response["error"]["message"]
        assert "Athena query execution" in response["error"]["message"]
    
    def test_timeout_error_without_duration(self):
        """Test timeout error helper without duration."""
        response = timeout_error(
            operation="Data retrieval",
            request_id="req-333",
        )
        
        assert response["success"] is False
        assert "timed out" in response["error"]["message"]
        assert "Data retrieval" in response["error"]["message"]
    
    def test_permission_denied_error(self):
        """Test permission denied error helper."""
        response = permission_denied_error(
            operation="Start workflow",
            request_id="req-444",
            details="IAM role lacks stepfunctions:StartExecution",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "permission"
        assert "Permission denied" in response["error"]["message"]
        assert "Start workflow" in response["error"]["message"]
        assert "IAM role" in response["error"]["details"]
    
    def test_invalid_query_error(self):
        """Test invalid query error helper."""
        response = invalid_query_error(
            query_issue="Invalid SQL syntax",
            request_id="req-555",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "user_input"
        assert "Invalid query" in response["error"]["message"]
        assert "Invalid SQL syntax" in response["error"]["message"]
    
    def test_workflow_execution_error(self):
        """Test workflow execution error helper."""
        response = workflow_execution_error(
            execution_arn="arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123",
            error_message="Task failed: InvalidBrandData",
            request_id="req-666",
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "backend_service"
        assert "Workflow execution failed" in response["error"]["message"]
        assert "exec-123" in response["error"]["details"]
        assert "InvalidBrandData" in response["error"]["details"]
    
    def test_empty_result_error(self):
        """Test empty result error helper."""
        response = empty_result_error(
            query_description="brands with confidence < 0.5",
            request_id="req-777",
            tool_name="execute_athena_query",
        )
        
        # Note: empty_result_error returns success=True with helpful message
        assert response["success"] is True
        assert response["data"]["results"] == []
        assert response["data"]["total_count"] == 0
        assert "No results found" in response["data"]["message"]
        assert "brands with confidence < 0.5" in response["data"]["message"]
        assert "broaden" in response["data"]["suggestion"]


class TestResponseStructure:
    """Tests for response structure consistency."""
    
    def test_all_error_responses_have_required_fields(self):
        """Test that all error responses have required fields."""
        error_functions = [
            lambda: create_user_input_error_response("msg", "req-1"),
            lambda: create_backend_service_error_response("msg", "req-2"),
            lambda: create_permission_error_response("msg", "req-3"),
            lambda: create_system_error_response("msg", "req-4"),
            lambda: missing_parameter_error("param", "req-5"),
            lambda: invalid_parameter_type_error("param", "type", "req-6"),
            lambda: resource_not_found_error("resource", "id", "req-7"),
            lambda: service_unavailable_error("service", "req-8"),
            lambda: timeout_error("operation", "req-9"),
            lambda: permission_denied_error("operation", "req-10"),
            lambda: invalid_query_error("issue", "req-11"),
            lambda: workflow_execution_error("arn", "error", "req-12"),
        ]
        
        for func in error_functions:
            response = func()
            assert "success" in response
            assert response["success"] is False
            assert "error" in response
            assert "type" in response["error"]
            assert "message" in response["error"]
            assert "details" in response["error"]
            assert "suggestion" in response["error"]
            assert "request_id" in response
            assert "timestamp" in response
    
    def test_error_types_are_valid(self):
        """Test that all error types are from the ErrorType enum."""
        valid_types = {e.value for e in ErrorType}
        
        responses = [
            create_user_input_error_response("msg", "req-1"),
            create_backend_service_error_response("msg", "req-2"),
            create_permission_error_response("msg", "req-3"),
            create_system_error_response("msg", "req-4"),
        ]
        
        for response in responses:
            assert response["error"]["type"] in valid_types
    
    def test_timestamps_are_iso_format(self):
        """Test that timestamps are in ISO 8601 format."""
        response = create_user_input_error_response("msg", "req-1")
        
        # Should be parseable as ISO 8601
        timestamp = response["timestamp"]
        parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert isinstance(parsed, datetime)
    
    def test_empty_result_has_different_structure(self):
        """Test that empty_result_error has a different structure (success=True)."""
        response = empty_result_error("query", "req-1")
        
        assert response["success"] is True
        assert "data" in response
        assert "error" not in response
        assert "results" in response["data"]
        assert "total_count" in response["data"]
        assert "message" in response["data"]
        assert "suggestion" in response["data"]


class TestErrorMessageQuality:
    """Tests for error message quality and helpfulness."""
    
    def test_error_messages_are_user_friendly(self):
        """Test that error messages are user-friendly (no technical jargon)."""
        response = missing_parameter_error("brandid", "req-1")
        
        message = response["error"]["message"]
        assert "Missing required parameter" in message
        assert "brandid" in message
        # Should not contain technical terms like "null", "undefined", etc.
        assert "null" not in message.lower()
        assert "undefined" not in message.lower()
    
    def test_suggestions_are_actionable(self):
        """Test that suggestions provide actionable next steps."""
        response = resource_not_found_error("brand", "12345", "req-1")
        
        suggestion = response["error"]["suggestion"]
        # Should contain action verbs
        assert any(verb in suggestion.lower() for verb in ["verify", "check", "provide", "contact", "try"])
    
    def test_permission_errors_suggest_contacting_admin(self):
        """Test that permission errors suggest contacting an administrator."""
        response = permission_denied_error("operation", "req-1")
        
        suggestion = response["error"]["suggestion"]
        assert "administrator" in suggestion.lower()
    
    def test_backend_errors_suggest_retry_or_status_check(self):
        """Test that backend errors suggest retry or status check."""
        response = service_unavailable_error("Athena", "req-1")
        
        suggestion = response["error"]["suggestion"]
        assert any(word in suggestion.lower() for word in ["try again", "retry", "status"])
    
    def test_timeout_errors_explain_duration(self):
        """Test that timeout errors explain the duration when provided."""
        response = timeout_error("operation", "req-1", timeout_seconds=30)
        
        message = response["error"]["message"]
        assert "30 seconds" in message
    
    def test_workflow_errors_include_execution_arn(self):
        """Test that workflow errors include execution ARN for tracing."""
        arn = "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123"
        response = workflow_execution_error(arn, "error", "req-1")
        
        details = response["error"]["details"]
        assert "exec-123" in details


class TestIntegrationWithErrorHandler:
    """Tests for integration with error_handler module."""
    
    def test_format_error_response_with_user_input_error(self):
        """Test format_error_response with UserInputError from error_handler."""
        error = UserInputError("Invalid input")
        response = format_error_response(error, "req-1", "test_tool")
        
        assert response["error"]["type"] == ErrorType.USER_INPUT.value
        assert response["tool_name"] == "test_tool"
    
    def test_format_error_response_with_backend_service_error(self):
        """Test format_error_response with BackendServiceError from error_handler."""
        error = BackendServiceError("Service failed")
        response = format_error_response(error, "req-1")
        
        assert response["error"]["type"] == ErrorType.BACKEND_SERVICE.value
    
    def test_format_error_response_with_permission_error(self):
        """Test format_error_response with PermissionError from error_handler."""
        error = PermissionError("Access denied")
        response = format_error_response(error, "req-1")
        
        assert response["error"]["type"] == ErrorType.PERMISSION.value
    
    def test_format_error_response_with_system_error(self):
        """Test format_error_response with SystemError from error_handler."""
        error = SystemError("System failure")
        response = format_error_response(error, "req-1")
        
        assert response["error"]["type"] == ErrorType.SYSTEM.value
