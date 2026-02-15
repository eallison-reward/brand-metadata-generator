"""Unit tests for check_workflow_status Lambda handler.

Requirements: 7.3
"""

import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from lambda_functions.check_workflow_status.handler import CheckWorkflowStatusHandler
from shared.utils.error_handler import UserInputError, BackendServiceError


class TestCheckWorkflowStatusHandler:
    """Test suite for CheckWorkflowStatusHandler."""

    @pytest.fixture
    def handler(self):
        """Create handler instance with mocked dependencies."""
        with patch('lambda_functions.check_workflow_status.handler.boto3.client'), \
             patch('lambda_functions.check_workflow_status.handler.DualStorageClient'):
            handler = CheckWorkflowStatusHandler()
            handler.sfn_client = MagicMock()
            handler.dual_storage = MagicMock()
            return handler

    # ========== Parameter Validation Tests ==========

    def test_validate_parameters_valid_arn(self, handler):
        """Test parameter validation with valid execution ARN."""
        parameters = {
            "execution_arn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123-20240101"
        }
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_missing_execution_arn(self, handler):
        """Test parameter validation fails when execution_arn is missing."""
        parameters = {}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "execution_arn" in str(exc_info.value).lower()
        assert "required" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_arn_type(self, handler):
        """Test parameter validation fails when execution_arn is not a string."""
        parameters = {"execution_arn": 123}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "string" in str(exc_info.value).lower()


    def test_validate_parameters_empty_arn(self, handler):
        """Test parameter validation fails when execution_arn is empty."""
        parameters = {"execution_arn": "   "}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "empty" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_arn_format(self, handler):
        """Test parameter validation fails when ARN format is invalid."""
        parameters = {"execution_arn": "invalid-arn-format"}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "invalid" in str(exc_info.value).lower()
        assert "format" in str(exc_info.value).lower()

    # ========== Output Parsing Tests ==========

    def test_parse_execution_output_valid_json(self, handler):
        """Test parsing valid JSON output."""
        output_str = '{"brandid": 123, "status": "completed"}'
        result = handler.parse_execution_output(output_str)
        
        assert result == {"brandid": 123, "status": "completed"}

    def test_parse_execution_output_none(self, handler):
        """Test parsing None output."""
        result = handler.parse_execution_output(None)
        assert result is None

    def test_parse_execution_output_empty_string(self, handler):
        """Test parsing empty string output."""
        result = handler.parse_execution_output("")
        assert result is None

    def test_parse_execution_output_invalid_json(self, handler):
        """Test parsing invalid JSON returns raw output."""
        output_str = "not valid json"
        result = handler.parse_execution_output(output_str)
        
        assert result == {"raw_output": "not valid json"}

    # ========== Format Execution Details Tests ==========

    def test_format_execution_details_running(self, handler):
        """Test formatting details for running execution."""
        execution = {
            "status": "RUNNING",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "name": "brand123-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 123}'
        }
        
        result = handler.format_execution_details(execution)
        
        assert result["status"] == "RUNNING"
        assert result["start_time"] == "2024-01-01T12:00:00"
        assert result["execution_name"] == "brand123-20240101"
        assert result["state_machine_arn"] == "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow"
        assert result["input"] == {"brandid": 123}
        assert "stop_time" not in result
        assert "output" not in result
        assert "error" not in result

    def test_format_execution_details_succeeded(self, handler):
        """Test formatting details for succeeded execution."""
        execution = {
            "status": "SUCCEEDED",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 12, 5, 0),
            "name": "brand123-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 123}',
            "output": '{"brandid": 123, "metadata": {"regex": "test.*"}}'
        }
        
        result = handler.format_execution_details(execution)
        
        assert result["status"] == "SUCCEEDED"
        assert result["start_time"] == "2024-01-01T12:00:00"
        assert result["stop_time"] == "2024-01-01T12:05:00"
        assert result["output"] == {"brandid": 123, "metadata": {"regex": "test.*"}}
        assert "error" not in result

    def test_format_execution_details_failed(self, handler):
        """Test formatting details for failed execution."""
        execution = {
            "status": "FAILED",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 12, 3, 0),
            "name": "brand123-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 123}',
            "error": "States.TaskFailed",
            "cause": "Lambda function failed with error"
        }
        
        result = handler.format_execution_details(execution)
        
        assert result["status"] == "FAILED"
        assert result["start_time"] == "2024-01-01T12:00:00"
        assert result["stop_time"] == "2024-01-01T12:03:00"
        assert result["error"] == "States.TaskFailed"
        assert result["cause"] == "Lambda function failed with error"
        assert "output" not in result

    def test_format_execution_details_timed_out(self, handler):
        """Test formatting details for timed out execution."""
        execution = {
            "status": "TIMED_OUT",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 13, 0, 0),
            "name": "brand123-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 123}',
            "error": "States.Timeout"
        }
        
        result = handler.format_execution_details(execution)
        
        assert result["status"] == "TIMED_OUT"
        assert result["error"] == "States.Timeout"

    def test_format_execution_details_aborted(self, handler):
        """Test formatting details for aborted execution."""
        execution = {
            "status": "ABORTED",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 12, 2, 0),
            "name": "brand123-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 123}',
            "cause": "Manually aborted by user"
        }
        
        result = handler.format_execution_details(execution)
        
        assert result["status"] == "ABORTED"
        assert result["cause"] == "Manually aborted by user"

    # ========== Execute Tests - Running Execution ==========

    def test_execute_running_execution(self, handler):
        """Test checking status of running execution."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123-20240101"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "RUNNING",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "name": "brand123-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 123}'
        }
        
        parameters = {"execution_arn": execution_arn}
        result = handler.execute(parameters)
        
        assert result["status"] == "RUNNING"
        assert result["start_time"] == "2024-01-01T12:00:00"
        assert result["execution_name"] == "brand123-20240101"
        assert "stop_time" not in result
        
        # Verify Step Functions was called
        handler.sfn_client.describe_execution.assert_called_once_with(
            executionArn=execution_arn
        )
        
        # Verify dual storage was NOT called for running execution
        handler.dual_storage.write_workflow_execution.assert_not_called()

    # ========== Execute Tests - Completed Execution ==========

    def test_execute_completed_execution(self, handler):
        """Test checking status of completed execution."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand456-20240101"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "SUCCEEDED",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 12, 5, 30),
            "name": "brand456-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 456}',
            "output": '{"brandid": 456, "metadata": {"regex": "test.*", "confidence_score": 0.95}}'
        }
        
        parameters = {"execution_arn": execution_arn}
        result = handler.execute(parameters)
        
        assert result["status"] == "SUCCEEDED"
        assert result["start_time"] == "2024-01-01T12:00:00"
        assert result["stop_time"] == "2024-01-01T12:05:30"
        assert result["output"]["brandid"] == 456
        assert result["output"]["metadata"]["confidence_score"] == 0.95
        
        # Verify dual storage was called for completed execution
        handler.dual_storage.write_workflow_execution.assert_called_once()
        call_args = handler.dual_storage.write_workflow_execution.call_args[0][0]
        assert call_args["execution_arn"] == execution_arn
        assert call_args["status"] == "SUCCEEDED"
        assert call_args["brandid"] == 456
        assert call_args["duration_seconds"] == 330  # 5 minutes 30 seconds

    # ========== Execute Tests - Failed Execution ==========

    def test_execute_failed_execution(self, handler):
        """Test checking status of failed execution."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand789-20240101"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "FAILED",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 12, 3, 15),
            "name": "brand789-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 789}',
            "error": "States.TaskFailed",
            "cause": "Lambda function returned error: Brand not found"
        }
        
        parameters = {"execution_arn": execution_arn}
        result = handler.execute(parameters)
        
        assert result["status"] == "FAILED"
        assert result["start_time"] == "2024-01-01T12:00:00"
        assert result["stop_time"] == "2024-01-01T12:03:15"
        assert result["error"] == "States.TaskFailed"
        assert result["cause"] == "Lambda function returned error: Brand not found"
        
        # Verify dual storage was called with error information
        handler.dual_storage.write_workflow_execution.assert_called_once()
        call_args = handler.dual_storage.write_workflow_execution.call_args[0][0]
        assert call_args["status"] == "FAILED"
        assert call_args["brandid"] == 789
        assert "States.TaskFailed" in call_args["error_message"]
        assert "Brand not found" in call_args["error_message"]

    # ========== Error Handling Tests - Invalid ARN ==========

    def test_execute_execution_does_not_exist(self, handler):
        """Test error handling when execution doesn't exist."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:nonexistent"
        
        error_response = {
            "Error": {
                "Code": "ExecutionDoesNotExist",
                "Message": "Execution does not exist"
            }
        }
        handler.sfn_client.describe_execution.side_effect = ClientError(error_response, "DescribeExecution")
        
        parameters = {"execution_arn": execution_arn}
        
        with pytest.raises(UserInputError) as exc_info:
            handler.execute(parameters)
        
        assert "not found" in str(exc_info.value).lower()
        assert execution_arn in str(exc_info.value)

    def test_execute_invalid_arn_error(self, handler):
        """Test error handling for invalid ARN format."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:invalid"
        
        error_response = {
            "Error": {
                "Code": "InvalidArn",
                "Message": "Invalid ARN format"
            }
        }
        handler.sfn_client.describe_execution.side_effect = ClientError(error_response, "DescribeExecution")
        
        parameters = {"execution_arn": execution_arn}
        
        with pytest.raises(UserInputError) as exc_info:
            handler.execute(parameters)
        
        assert "invalid" in str(exc_info.value).lower()
        assert execution_arn in str(exc_info.value)

    def test_execute_access_denied_error(self, handler):
        """Test error handling for access denied."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123"
        
        error_response = {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "User is not authorized to perform: states:DescribeExecution"
            }
        }
        handler.sfn_client.describe_execution.side_effect = ClientError(error_response, "DescribeExecution")
        
        parameters = {"execution_arn": execution_arn}
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "permission denied" in str(exc_info.value).lower()

    def test_execute_generic_error(self, handler):
        """Test error handling for generic Step Functions errors."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123"
        
        error_response = {
            "Error": {
                "Code": "ServiceException",
                "Message": "Internal service error"
            }
        }
        handler.sfn_client.describe_execution.side_effect = ClientError(error_response, "DescribeExecution")
        
        parameters = {"execution_arn": execution_arn}
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "failed to query execution status" in str(exc_info.value).lower()

    # ========== Dual Storage Logging Tests ==========

    def test_execute_logs_succeeded_execution(self, handler):
        """Test that succeeded execution is logged to dual storage."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand111"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "SUCCEEDED",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 12, 10, 0),
            "name": "brand111-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 111}',
            "output": '{"brandid": 111, "result": "success"}'
        }
        
        parameters = {"execution_arn": execution_arn}
        handler.execute(parameters)
        
        # Verify dual storage was called with correct data
        handler.dual_storage.write_workflow_execution.assert_called_once()
        call_args = handler.dual_storage.write_workflow_execution.call_args[0][0]
        
        assert call_args["execution_arn"] == execution_arn
        assert call_args["status"] == "SUCCEEDED"
        assert call_args["brandid"] == 111
        assert call_args["start_time"] == "2024-01-01T12:00:00"
        assert call_args["stop_time"] == "2024-01-01T12:10:00"
        assert call_args["duration_seconds"] == 600
        assert "input_data" in call_args
        assert "output_data" in call_args

    def test_execute_logs_failed_execution_with_error(self, handler):
        """Test that failed execution is logged with error details."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand222"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "FAILED",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 12, 2, 0),
            "name": "brand222-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 222}',
            "error": "States.TaskFailed",
            "cause": "Validation error"
        }
        
        parameters = {"execution_arn": execution_arn}
        handler.execute(parameters)
        
        # Verify error message is logged
        call_args = handler.dual_storage.write_workflow_execution.call_args[0][0]
        assert call_args["status"] == "FAILED"
        assert "error_message" in call_args
        assert "States.TaskFailed" in call_args["error_message"]
        assert "Validation error" in call_args["error_message"]

    def test_execute_logs_timed_out_execution(self, handler):
        """Test that timed out execution is logged."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand333"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "TIMED_OUT",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 13, 0, 0),
            "name": "brand333-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 333}',
            "error": "States.Timeout"
        }
        
        parameters = {"execution_arn": execution_arn}
        handler.execute(parameters)
        
        # Verify timeout is logged
        call_args = handler.dual_storage.write_workflow_execution.call_args[0][0]
        assert call_args["status"] == "TIMED_OUT"
        assert "error_message" in call_args
        assert "States.Timeout" in call_args["error_message"]

    def test_execute_logs_aborted_execution(self, handler):
        """Test that aborted execution is logged."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand444"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "ABORTED",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 12, 1, 0),
            "name": "brand444-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 444}',
            "cause": "User requested abort"
        }
        
        parameters = {"execution_arn": execution_arn}
        handler.execute(parameters)
        
        # Verify abort is logged
        call_args = handler.dual_storage.write_workflow_execution.call_args[0][0]
        assert call_args["status"] == "ABORTED"
        assert "error_message" in call_args
        assert "User requested abort" in call_args["error_message"]

    def test_execute_continues_on_logging_error(self, handler):
        """Test that status check succeeds even if logging fails."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand555"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "SUCCEEDED",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 12, 5, 0),
            "name": "brand555-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 555}',
            "output": '{"brandid": 555}'
        }
        
        # Mock logging error
        handler.dual_storage.write_workflow_execution.side_effect = Exception("Logging failed")
        
        parameters = {"execution_arn": execution_arn}
        # Should not raise exception
        result = handler.execute(parameters)
        
        # Status check should still succeed
        assert result["status"] == "SUCCEEDED"
        assert result["input"]["brandid"] == 555

    def test_execute_logs_execution_without_brandid(self, handler):
        """Test logging execution when input doesn't contain brandid."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:custom-exec"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "SUCCEEDED",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "stopDate": datetime(2024, 1, 1, 12, 5, 0),
            "name": "custom-exec",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"custom_param": "value"}',
            "output": '{"result": "success"}'
        }
        
        parameters = {"execution_arn": execution_arn}
        result = handler.execute(parameters)
        
        # Should still log without brandid
        handler.dual_storage.write_workflow_execution.assert_called_once()
        call_args = handler.dual_storage.write_workflow_execution.call_args[0][0]
        assert call_args["status"] == "SUCCEEDED"
        assert "brandid" not in call_args  # brandid should not be present

    # ========== Lambda Handler Integration Tests ==========

    def test_lambda_handler_success(self, handler):
        """Test lambda_handler with successful execution."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "RUNNING",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "name": "brand123-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 123}'
        }
        
        event = {
            "parameters": {"execution_arn": execution_arn},
            "request_id": "test-request-123"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is True
        assert "data" in response
        assert response["data"]["status"] == "RUNNING"
        assert response["request_id"] == "test-request-123"

    def test_lambda_handler_validation_error(self, handler):
        """Test lambda_handler with validation error."""
        event = {
            "parameters": {"execution_arn": "invalid-arn"},
            "request_id": "test-request-456"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["type"] == "user_input"
        assert "invalid" in response["error"]["message"].lower()
        assert response["request_id"] == "test-request-456"

    def test_lambda_handler_backend_error(self, handler):
        """Test lambda_handler with backend service error."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123"
        
        error_response = {
            "Error": {
                "Code": "ServiceException",
                "Message": "Service unavailable"
            }
        }
        handler.sfn_client.describe_execution.side_effect = ClientError(error_response, "DescribeExecution")
        
        event = {
            "parameters": {"execution_arn": execution_arn},
            "request_id": "test-request-789"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["type"] == "backend_service"
        assert response["request_id"] == "test-request-789"

    # ========== Edge Cases ==========

    def test_execute_result_structure(self, handler):
        """Test that execute returns correct result structure."""
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123"
        
        handler.sfn_client.describe_execution.return_value = {
            "status": "RUNNING",
            "startDate": datetime(2024, 1, 1, 12, 0, 0),
            "name": "brand123-20240101",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow",
            "input": '{"brandid": 123}'
        }
        
        result = handler.execute({"execution_arn": execution_arn})
        
        # Verify result structure
        assert "status" in result
        assert "start_time" in result
        assert "execution_name" in result
        assert "state_machine_arn" in result
        assert "input" in result
        assert isinstance(result["status"], str)
        assert isinstance(result["start_time"], str)
