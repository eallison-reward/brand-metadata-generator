"""Unit tests for error categorization logic.

Tests the comprehensive error categorization system that automatically
categorizes AWS SDK errors and Python exceptions into four categories:
user_input, backend_service, permission, and system.

Requirements tested: 9.1, 9.2, 9.3, 9.4
"""

import pytest
from unittest.mock import Mock
from shared.utils.error_handler import (
    ErrorType,
    ToolError,
    UserInputError,
    BackendServiceError,
    PermissionError,
    SystemError,
    handle_aws_error,
    categorize_error,
    get_error_suggestion,
    create_error_response,
)


class TestErrorCategories:
    """Test error category definitions and base classes."""
    
    def test_error_type_enum_values(self):
        """Test that ErrorType enum has all required categories."""
        assert ErrorType.USER_INPUT.value == "user_input"
        assert ErrorType.BACKEND_SERVICE.value == "backend_service"
        assert ErrorType.PERMISSION.value == "permission"
        assert ErrorType.SYSTEM.value == "system"
    
    def test_tool_error_to_dict(self):
        """Test ToolError serialization to dictionary."""
        error = UserInputError(
            message="Invalid input",
            details="Brand ID must be positive",
            suggestion="Provide a valid brand ID"
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["type"] == "user_input"
        assert error_dict["message"] == "Invalid input"
        assert error_dict["details"] == "Brand ID must be positive"
        assert error_dict["suggestion"] == "Provide a valid brand ID"
    
    def test_tool_error_default_suggestions(self):
        """Test that each error type has appropriate default suggestions."""
        user_error = UserInputError("Test")
        assert "check your input" in user_error.suggestion.lower()
        
        backend_error = BackendServiceError("Test")
        assert "try again" in backend_error.suggestion.lower()
        
        perm_error = PermissionError("Test")
        assert "administrator" in perm_error.suggestion.lower()
        
        sys_error = SystemError("Test")
        assert "contact support" in sys_error.suggestion.lower()


class TestAWSErrorCategorization:
    """Test AWS SDK error categorization (Requirement 9.1, 9.2, 9.3, 9.4)."""
    
    def create_aws_error(self, error_code: str, message: str = "Test error"):
        """Helper to create mock AWS error."""
        error = Exception(message)
        error.response = {
            "Error": {
                "Code": error_code,
                "Message": message
            }
        }
        return error
    
    # ========================================================================
    # PERMISSION ERRORS (Requirement 9.1)
    # ========================================================================
    
    def test_access_denied_categorized_as_permission(self):
        """Test AccessDenied error is categorized as permission error."""
        aws_error = self.create_aws_error("AccessDenied", "User not authorized")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, PermissionError)
        assert result.error_type == ErrorType.PERMISSION
        assert "permission" in result.message.lower()
        assert "administrator" in result.suggestion.lower()
    
    def test_unauthorized_operation_categorized_as_permission(self):
        """Test UnauthorizedOperation error is categorized as permission error."""
        aws_error = self.create_aws_error("UnauthorizedOperation")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, PermissionError)
        assert result.error_type == ErrorType.PERMISSION
    
    def test_forbidden_exception_categorized_as_permission(self):
        """Test ForbiddenException error is categorized as permission error."""
        aws_error = self.create_aws_error("ForbiddenException")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, PermissionError)
    
    # ========================================================================
    # USER INPUT ERRORS (Requirement 9.2)
    # ========================================================================
    
    def test_validation_exception_categorized_as_user_input(self):
        """Test ValidationException is categorized as user input error."""
        aws_error = self.create_aws_error("ValidationException", "Invalid parameter value")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, UserInputError)
        assert result.error_type == ErrorType.USER_INPUT
        assert "invalid input" in result.message.lower()
        assert "check your input" in result.suggestion.lower()
    
    def test_invalid_parameter_exception_categorized_as_user_input(self):
        """Test InvalidParameterException is categorized as user input error."""
        aws_error = self.create_aws_error("InvalidParameterException")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, UserInputError)
    
    def test_missing_parameter_categorized_as_user_input(self):
        """Test MissingParameter error is categorized as user input error."""
        aws_error = self.create_aws_error("MissingParameter", "Required parameter missing")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, UserInputError)
        assert "required" in result.suggestion.lower()
    
    def test_invalid_arn_categorized_as_user_input(self):
        """Test InvalidArn error is categorized as user input error."""
        aws_error = self.create_aws_error("InvalidArn", "ARN format invalid")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, UserInputError)
        assert "identifier" in result.message.lower()
    
    # ========================================================================
    # BACKEND SERVICE ERRORS (Requirement 9.3, 9.4)
    # ========================================================================
    
    def test_resource_not_found_categorized_as_backend_service(self):
        """Test ResourceNotFoundException is categorized as backend service error."""
        aws_error = self.create_aws_error("ResourceNotFoundException", "Resource not found")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, BackendServiceError)
        assert result.error_type == ErrorType.BACKEND_SERVICE
        assert "not found" in result.message.lower()
        assert "verify" in result.suggestion.lower()
    
    def test_throttling_exception_categorized_as_backend_service(self):
        """Test ThrottlingException is categorized as backend service error."""
        aws_error = self.create_aws_error("ThrottlingException", "Rate exceeded")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, BackendServiceError)
        assert "busy" in result.message.lower()
        assert "wait" in result.suggestion.lower()
    
    def test_timeout_error_categorized_as_backend_service(self):
        """Test timeout errors are categorized as backend service error (Requirement 9.3)."""
        aws_error = self.create_aws_error("RequestTimeout", "Request timed out")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, BackendServiceError)
        assert "timed out" in result.message.lower()
        assert "check system status" in result.suggestion.lower()
    
    def test_service_unavailable_categorized_as_backend_service(self):
        """Test ServiceUnavailable is categorized as backend service error."""
        aws_error = self.create_aws_error("ServiceUnavailable", "Service down")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, BackendServiceError)
        assert "unavailable" in result.message.lower()
        assert "try again" in result.suggestion.lower()
    
    def test_athena_query_error_categorized_as_backend_service(self):
        """Test Athena query errors are categorized correctly (Requirement 9.4)."""
        aws_error = self.create_aws_error(
            "InvalidRequestException",
            "Athena query syntax error: line 1:8: Column 'invalid_col' cannot be resolved"
        )
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, BackendServiceError)
        assert "athena" in result.message.lower()
        assert "query" in result.suggestion.lower()
    
    def test_step_functions_error_categorized_as_backend_service(self):
        """Test Step Functions errors are categorized as backend service error."""
        aws_error = self.create_aws_error("ExecutionAlreadyExists", "Execution exists")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, BackendServiceError)
        assert "workflow" in result.message.lower()
    
    def test_s3_bucket_error_categorized_as_backend_service(self):
        """Test S3 bucket errors are categorized as backend service error."""
        aws_error = self.create_aws_error("NoSuchBucket", "Bucket does not exist")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, BackendServiceError)
        assert "s3" in result.message.lower()
    
    # ========================================================================
    # SYSTEM ERRORS (Default fallback)
    # ========================================================================
    
    def test_unknown_error_code_categorized_as_system(self):
        """Test unknown AWS error codes are categorized as system error."""
        aws_error = self.create_aws_error("UnknownErrorCode123", "Unknown error")
        
        result = handle_aws_error(aws_error)
        
        assert isinstance(result, SystemError)
        assert result.error_type == ErrorType.SYSTEM
        assert "unexpected" in result.message.lower()


class TestPythonExceptionCategorization:
    """Test Python exception categorization."""
    
    def test_value_error_categorized_as_user_input(self):
        """Test ValueError is categorized as user input error."""
        error = ValueError("Invalid brand ID format")
        
        result = categorize_error(error)
        
        assert isinstance(result, UserInputError)
        assert "invalid value" in result.message.lower()
    
    def test_type_error_categorized_as_user_input(self):
        """Test TypeError is categorized as user input error."""
        error = TypeError("Expected int, got str")
        
        result = categorize_error(error)
        
        assert isinstance(result, UserInputError)
        assert "type" in result.message.lower()
    
    def test_key_error_categorized_as_user_input(self):
        """Test KeyError is categorized as user input error."""
        error = KeyError("brandid")
        
        result = categorize_error(error)
        
        assert isinstance(result, UserInputError)
        assert "missing" in result.message.lower()
    
    def test_timeout_error_categorized_as_backend_service(self):
        """Test TimeoutError is categorized as backend service error."""
        error = TimeoutError("Operation timed out")
        
        result = categorize_error(error)
        
        assert isinstance(result, BackendServiceError)
        assert "timed out" in result.message.lower()
    
    def test_file_not_found_categorized_as_backend_service(self):
        """Test FileNotFoundError is categorized as backend service error."""
        error = FileNotFoundError("File not found")
        
        result = categorize_error(error)
        
        assert isinstance(result, BackendServiceError)
        assert "not found" in result.message.lower()
    
    def test_permission_error_categorized_as_permission(self):
        """Test PermissionError is categorized as permission error."""
        # Use built-in PermissionError
        error = __builtins__["PermissionError"]("Access denied")
        
        result = categorize_error(error)
        
        assert isinstance(result, PermissionError)
        assert "permission denied" in result.message.lower()
    
    def test_generic_exception_categorized_as_system(self):
        """Test generic exceptions are categorized as system error."""
        error = Exception("Something went wrong")
        
        result = categorize_error(error)
        
        assert isinstance(result, SystemError)
        assert "unexpected" in result.message.lower()
    
    def test_already_categorized_error_returned_unchanged(self):
        """Test that ToolError instances are returned unchanged."""
        original_error = UserInputError("Test error")
        
        result = categorize_error(original_error)
        
        assert result is original_error


class TestErrorSuggestions:
    """Test context-aware error suggestions."""
    
    def test_permission_error_athena_context(self):
        """Test permission error suggestion for Athena context."""
        suggestion = get_error_suggestion(
            ErrorType.PERMISSION,
            error_code="AccessDenied",
            context="athena_query"
        )
        
        assert "athena" in suggestion.lower()
        assert "administrator" in suggestion.lower()
    
    def test_permission_error_workflow_context(self):
        """Test permission error suggestion for workflow context."""
        suggestion = get_error_suggestion(
            ErrorType.PERMISSION,
            context="workflow_start"
        )
        
        assert "step functions" in suggestion.lower()
    
    def test_user_input_error_brandid_context(self):
        """Test user input error suggestion for brand ID context."""
        suggestion = get_error_suggestion(
            ErrorType.USER_INPUT,
            context="brandid_validation"
        )
        
        assert "brand id" in suggestion.lower()
        assert "positive integer" in suggestion.lower()
    
    def test_user_input_error_arn_context(self):
        """Test user input error suggestion for ARN context."""
        suggestion = get_error_suggestion(
            ErrorType.USER_INPUT,
            context="execution_arn"
        )
        
        assert "arn" in suggestion.lower()
        assert "format" in suggestion.lower()
    
    def test_backend_service_throttling_suggestion(self):
        """Test backend service error suggestion for throttling."""
        suggestion = get_error_suggestion(
            ErrorType.BACKEND_SERVICE,
            error_code="ThrottlingException"
        )
        
        assert "wait" in suggestion.lower()
        assert "seconds" in suggestion.lower()
    
    def test_backend_service_timeout_suggestion(self):
        """Test backend service error suggestion for timeout."""
        suggestion = get_error_suggestion(
            ErrorType.BACKEND_SERVICE,
            error_code="RequestTimeout"
        )
        
        assert "timeout" in suggestion.lower()
        assert "check system status" in suggestion.lower()
    
    def test_backend_service_not_found_brand_context(self):
        """Test backend service error suggestion for brand not found."""
        suggestion = get_error_suggestion(
            ErrorType.BACKEND_SERVICE,
            error_code="ResourceNotFoundException",
            context="brand_query"
        )
        
        assert "brand" in suggestion.lower()
        assert "verify" in suggestion.lower()
    
    def test_backend_service_athena_context(self):
        """Test backend service error suggestion for Athena context."""
        suggestion = get_error_suggestion(
            ErrorType.BACKEND_SERVICE,
            context="athena_query"
        )
        
        assert "athena" in suggestion.lower()
        assert "query" in suggestion.lower()
    
    def test_system_error_default_suggestion(self):
        """Test system error default suggestion."""
        suggestion = get_error_suggestion(ErrorType.SYSTEM)
        
        assert "unexpected" in suggestion.lower()
        assert "contact support" in suggestion.lower()


class TestErrorResponseCreation:
    """Test error response creation and formatting."""
    
    def test_create_error_response_structure(self):
        """Test that error response has correct structure."""
        error = UserInputError("Invalid input")
        
        response = create_error_response(
            error,
            request_id="req-123",
            tool_name="test_tool"
        )
        
        assert response["success"] is False
        assert "error" in response
        assert "request_id" in response
        assert "timestamp" in response
        assert response["request_id"] == "req-123"
        
        error_dict = response["error"]
        assert error_dict["type"] == "user_input"
        assert error_dict["message"] == "Invalid input"
        assert "details" in error_dict
        assert "suggestion" in error_dict
    
    def test_create_error_response_categorizes_exception(self):
        """Test that create_error_response automatically categorizes exceptions."""
        error = ValueError("Invalid value")
        
        response = create_error_response(error, request_id="req-456")
        
        assert response["success"] is False
        assert response["error"]["type"] == "user_input"
    
    def test_create_error_response_handles_aws_error(self):
        """Test that create_error_response handles AWS errors."""
        aws_error = Exception("Test")
        aws_error.response = {
            "Error": {
                "Code": "AccessDenied",
                "Message": "Access denied"
            }
        }
        
        response = create_error_response(aws_error, request_id="req-789")
        
        assert response["success"] is False
        assert response["error"]["type"] == "permission"


class TestErrorCategorizationIntegration:
    """Integration tests for complete error categorization flow."""
    
    def test_end_to_end_permission_error_flow(self):
        """Test complete flow from AWS error to response for permission error."""
        # Simulate AWS SDK error
        aws_error = Exception("Access denied")
        aws_error.response = {
            "Error": {
                "Code": "AccessDenied",
                "Message": "User: arn:aws:iam::123:user/test is not authorized"
            }
        }
        
        # Create error response
        response = create_error_response(
            aws_error,
            request_id="req-integration-1",
            tool_name="start_workflow"
        )
        
        # Verify complete response structure
        assert response["success"] is False
        assert response["error"]["type"] == "permission"
        assert "permission" in response["error"]["message"].lower()
        assert "administrator" in response["error"]["suggestion"].lower()
        assert response["request_id"] == "req-integration-1"
    
    def test_end_to_end_user_input_error_flow(self):
        """Test complete flow for user input error."""
        error = ValueError("Brand ID must be positive")
        
        response = create_error_response(
            error,
            request_id="req-integration-2",
            tool_name="query_metadata"
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "user_input"
        assert "invalid value" in response["error"]["message"].lower()
    
    def test_end_to_end_backend_service_error_flow(self):
        """Test complete flow for backend service error."""
        aws_error = Exception("Resource not found")
        aws_error.response = {
            "Error": {
                "Code": "ResourceNotFoundException",
                "Message": "Brand 12345 not found"
            }
        }
        
        response = create_error_response(
            aws_error,
            request_id="req-integration-3",
            tool_name="query_metadata"
        )
        
        assert response["success"] is False
        assert response["error"]["type"] == "backend_service"
        assert "not found" in response["error"]["message"].lower()
        assert "verify" in response["error"]["suggestion"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
