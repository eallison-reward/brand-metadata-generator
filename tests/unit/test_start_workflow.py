"""Unit tests for start_workflow Lambda handler.

Requirements: 7.2
"""

import json
import os
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call
from botocore.exceptions import ClientError

# Set environment variable before importing handler
os.environ['STATE_MACHINE_ARN'] = 'arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow'

from lambda_functions.start_workflow.handler import StartWorkflowHandler
from shared.utils.error_handler import UserInputError, BackendServiceError


class TestStartWorkflowHandler:
    """Test suite for StartWorkflowHandler."""

    @pytest.fixture
    def handler(self):
        """Create handler instance with mocked dependencies."""
        with patch.dict('os.environ', {'STATE_MACHINE_ARN': 'arn:aws:states:eu-west-1:123456789012:stateMachine:test-workflow'}):
            with patch('lambda_functions.start_workflow.handler.boto3.client'), \
                 patch('lambda_functions.start_workflow.handler.DynamoDBClient'), \
                 patch('lambda_functions.start_workflow.handler.DualStorageClient'):
                handler = StartWorkflowHandler()
                handler.sfn_client = MagicMock()
                handler.dynamodb_client = MagicMock()
                handler.dual_storage = MagicMock()
                return handler

    # ========== Parameter Validation Tests ==========

    def test_validate_parameters_valid_single_brandid(self, handler):
        """Test parameter validation with valid single brand ID."""
        parameters = {"brandid": 123}
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_multiple_brandids(self, handler):
        """Test parameter validation with valid list of brand IDs."""
        parameters = {"brandid": [101, 102, 103]}
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_with_execution_name(self, handler):
        """Test parameter validation with execution name."""
        parameters = {
            "brandid": 456,
            "execution_name": "my-custom-execution"
        }
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_missing_brandid(self, handler):
        """Test parameter validation fails when brandid is missing."""
        parameters = {}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "brandid" in str(exc_info.value).lower()
        assert "required" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_brandid_type(self, handler):
        """Test parameter validation fails when brandid is wrong type."""
        parameters = {"brandid": "not_an_int"}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "integer" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_brandid_zero(self, handler):
        """Test parameter validation fails when brandid is zero."""
        parameters = {"brandid": 0}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_brandid_negative(self, handler):
        """Test parameter validation fails when brandid is negative."""
        parameters = {"brandid": -5}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_brandid_list_empty(self, handler):
        """Test parameter validation fails when brandid list is empty."""
        parameters = {"brandid": []}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "empty" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_brandid_list_contains_non_int(self, handler):
        """Test parameter validation fails when brandid list contains non-integers."""
        parameters = {"brandid": [101, "102", 103]}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "integer" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_brandid_list_contains_negative(self, handler):
        """Test parameter validation fails when brandid list contains negative values."""
        parameters = {"brandid": [101, -102, 103]}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_execution_name_type(self, handler):
        """Test parameter validation fails when execution_name is not a string."""
        parameters = {
            "brandid": 123,
            "execution_name": 456
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "execution_name" in str(exc_info.value).lower()
        assert "string" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_execution_name_empty(self, handler):
        """Test parameter validation fails when execution_name is empty."""
        parameters = {
            "brandid": 123,
            "execution_name": "   "
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "execution_name" in str(exc_info.value).lower()
        assert "empty" in str(exc_info.value).lower()

    # ========== Brand Verification Tests ==========

    def test_verify_brand_exists_found(self, handler):
        """Test verify_brand_exists returns True when brand is found."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        
        result = handler.verify_brand_exists(123)
        
        assert result is True
        handler.dynamodb_client.get_brand_by_id.assert_called_once_with(123)

    def test_verify_brand_exists_not_found(self, handler):
        """Test verify_brand_exists returns False when brand is not found."""
        handler.dynamodb_client.get_brand_by_id.return_value = None
        
        result = handler.verify_brand_exists(999)
        
        assert result is False

    def test_verify_brand_exists_handles_error(self, handler):
        """Test verify_brand_exists returns True on error (fail open)."""
        handler.dynamodb_client.get_brand_by_id.side_effect = Exception("DynamoDB error")
        
        result = handler.verify_brand_exists(123)
        
        # Should return True to let workflow handle verification
        assert result is True

    # ========== Execution Name Generation Tests ==========

    def test_generate_execution_name_without_base(self, handler):
        """Test execution name generation without base name."""
        execution_name = handler.generate_execution_name(123)
        
        assert execution_name.startswith("brand123-")
        assert len(execution_name) > 10  # Should include timestamp

    def test_generate_execution_name_with_base(self, handler):
        """Test execution name generation with base name."""
        execution_name = handler.generate_execution_name(456, "my-workflow")
        
        assert "my-workflow" in execution_name
        assert "brand456" in execution_name
        assert len(execution_name) > 20  # Should include base, brand ID, and timestamp

    def test_generate_execution_name_sanitizes_base(self, handler):
        """Test execution name generation sanitizes special characters."""
        execution_name = handler.generate_execution_name(789, "my@workflow#test!")
        
        # Special characters should be replaced with hyphens
        assert "@" not in execution_name
        assert "#" not in execution_name
        assert "!" not in execution_name
        assert "brand789" in execution_name

    def test_generate_execution_name_uniqueness(self, handler):
        """Test that generated execution names are unique."""
        import time
        
        name1 = handler.generate_execution_name(123)
        time.sleep(0.001)  # Small delay to ensure different timestamp
        name2 = handler.generate_execution_name(123)
        
        # Names should be different due to timestamp
        assert name1 != name2

    # ========== Single Workflow Start Tests ==========

    def test_start_single_workflow_success(self, handler):
        """Test starting workflow for a single brand successfully."""
        # Mock brand verification
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        
        # Mock Step Functions response
        handler.sfn_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123-20240101-120000",
            "startDate": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        result = handler.start_single_workflow(123)
        
        # Verify result
        assert result["brandid"] == 123
        assert "execution_arn" in result
        assert "start_time" in result
        assert "arn:aws:states" in result["execution_arn"]
        
        # Verify Step Functions was called
        handler.sfn_client.start_execution.assert_called_once()
        call_args = handler.sfn_client.start_execution.call_args
        assert call_args[1]["stateMachineArn"] == handler.state_machine_arn
        
        # Verify input contains brand ID
        workflow_input = json.loads(call_args[1]["input"])
        assert workflow_input["brandid"] == 123
        assert workflow_input["action"] == "start_workflow"

    def test_start_single_workflow_with_custom_execution_name(self, handler):
        """Test starting workflow with custom execution name."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 456}
        handler.sfn_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:custom-brand456-20240101-120000",
            "startDate": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        result = handler.start_single_workflow(456, "custom-execution")
        
        # Verify execution name includes custom base
        call_args = handler.sfn_client.start_execution.call_args
        execution_name = call_args[1]["name"]
        assert "custom-execution" in execution_name
        assert "brand456" in execution_name

    def test_start_single_workflow_brand_not_found(self, handler):
        """Test starting workflow fails when brand doesn't exist."""
        handler.dynamodb_client.get_brand_by_id.return_value = None
        
        with pytest.raises(UserInputError) as exc_info:
            handler.start_single_workflow(999)
        
        assert "999" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()
        
        # Step Functions should not be called
        handler.sfn_client.start_execution.assert_not_called()

    def test_start_single_workflow_execution_already_exists(self, handler):
        """Test starting workflow fails when execution name already exists."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        
        # Mock Step Functions error
        error_response = {
            "Error": {
                "Code": "ExecutionAlreadyExists",
                "Message": "Execution already exists"
            }
        }
        handler.sfn_client.start_execution.side_effect = ClientError(error_response, "StartExecution")
        
        with pytest.raises(UserInputError) as exc_info:
            handler.start_single_workflow(123)
        
        assert "already exists" in str(exc_info.value).lower()

    def test_start_single_workflow_invalid_arn(self, handler):
        """Test starting workflow fails with invalid state machine ARN."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        
        # Mock Step Functions error
        error_response = {
            "Error": {
                "Code": "InvalidArn",
                "Message": "Invalid ARN"
            }
        }
        handler.sfn_client.start_execution.side_effect = ClientError(error_response, "StartExecution")
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.start_single_workflow(123)
        
        assert "invalid" in str(exc_info.value).lower()
        assert "arn" in str(exc_info.value).lower()

    def test_start_single_workflow_generic_error(self, handler):
        """Test starting workflow handles generic Step Functions errors."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        
        # Mock Step Functions error
        error_response = {
            "Error": {
                "Code": "ServiceException",
                "Message": "Service unavailable"
            }
        }
        handler.sfn_client.start_execution.side_effect = ClientError(error_response, "StartExecution")
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.start_single_workflow(123)
        
        assert "failed to start workflow" in str(exc_info.value).lower()

    def test_start_single_workflow_logs_to_dual_storage(self, handler):
        """Test that workflow start is logged to dual storage."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        handler.sfn_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123-20240101-120000",
            "startDate": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        handler.start_single_workflow(123)
        
        # Verify dual storage was called
        handler.dual_storage.write_workflow_execution.assert_called_once()
        call_args = handler.dual_storage.write_workflow_execution.call_args[0][0]
        assert call_args["brandid"] == 123
        assert call_args["status"] == "RUNNING"
        assert "execution_arn" in call_args

    def test_start_single_workflow_continues_on_logging_error(self, handler):
        """Test that workflow start succeeds even if logging fails."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        handler.sfn_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123-20240101-120000",
            "startDate": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        # Mock logging error
        handler.dual_storage.write_workflow_execution.side_effect = Exception("Logging failed")
        
        # Should not raise exception
        result = handler.start_single_workflow(123)
        
        # Workflow should still succeed
        assert result["brandid"] == 123
        assert "execution_arn" in result

    # ========== Multiple Workflow Start Tests ==========

    def test_execute_single_brand(self, handler):
        """Test execute with single brand ID."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        handler.sfn_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123-20240101-120000",
            "startDate": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        parameters = {"brandid": 123}
        result = handler.execute(parameters)
        
        assert result["success"] is True
        assert len(result["executions"]) == 1
        assert result["executions"][0]["brandid"] == 123
        assert "errors" not in result

    def test_execute_multiple_brands_all_success(self, handler):
        """Test execute with multiple brand IDs, all succeed."""
        # Mock brand verification for all brands
        handler.dynamodb_client.get_brand_by_id.side_effect = [
            {"brandid": 101},
            {"brandid": 102},
            {"brandid": 103}
        ]
        
        # Mock Step Functions responses
        handler.sfn_client.start_execution.side_effect = [
            {
                "executionArn": f"arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand{i}-20240101-120000",
                "startDate": datetime(2024, 1, 1, 12, 0, 0)
            }
            for i in [101, 102, 103]
        ]
        
        parameters = {"brandid": [101, 102, 103]}
        result = handler.execute(parameters)
        
        assert result["success"] is True
        assert len(result["executions"]) == 3
        assert result["executions"][0]["brandid"] == 101
        assert result["executions"][1]["brandid"] == 102
        assert result["executions"][2]["brandid"] == 103
        assert "errors" not in result
        assert "partial_success" not in result

    def test_execute_multiple_brands_partial_success(self, handler):
        """Test execute with multiple brands, some fail."""
        # Mock brand verification - second brand not found
        handler.dynamodb_client.get_brand_by_id.side_effect = [
            {"brandid": 101},
            None,  # Brand 102 not found
            {"brandid": 103}
        ]
        
        # Mock Step Functions responses for successful brands
        handler.sfn_client.start_execution.side_effect = [
            {
                "executionArn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand101-20240101-120000",
                "startDate": datetime(2024, 1, 1, 12, 0, 0)
            },
            {
                "executionArn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand103-20240101-120000",
                "startDate": datetime(2024, 1, 1, 12, 0, 0)
            }
        ]
        
        parameters = {"brandid": [101, 102, 103]}
        result = handler.execute(parameters)
        
        assert result["success"] is True
        assert result["partial_success"] is True
        assert len(result["executions"]) == 2
        assert len(result["errors"]) == 1
        assert result["errors"][0]["brandid"] == 102

    def test_execute_multiple_brands_all_fail(self, handler):
        """Test execute with multiple brands, all fail."""
        # Mock brand verification - all brands not found
        handler.dynamodb_client.get_brand_by_id.return_value = None
        
        parameters = {"brandid": [201, 202, 203]}
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "all" in str(exc_info.value).lower()
        assert "3" in str(exc_info.value)

    def test_execute_with_execution_name_multiple_brands(self, handler):
        """Test execute with custom execution name for multiple brands."""
        handler.dynamodb_client.get_brand_by_id.side_effect = [
            {"brandid": 101},
            {"brandid": 102}
        ]
        
        handler.sfn_client.start_execution.side_effect = [
            {
                "executionArn": f"arn:aws:states:eu-west-1:123456789012:execution:test-workflow:custom-brand{i}-20240101-120000",
                "startDate": datetime(2024, 1, 1, 12, 0, 0)
            }
            for i in [101, 102]
        ]
        
        parameters = {
            "brandid": [101, 102],
            "execution_name": "batch-process"
        }
        result = handler.execute(parameters)
        
        assert result["success"] is True
        assert len(result["executions"]) == 2
        
        # Verify execution names include custom base
        for call_args in handler.sfn_client.start_execution.call_args_list:
            execution_name = call_args[1]["name"]
            assert "batch-process" in execution_name

    # ========== Lambda Handler Integration Tests ==========

    def test_lambda_handler_success(self, handler):
        """Test lambda_handler with successful execution."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        handler.sfn_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123-20240101-120000",
            "startDate": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        event = {"brandid": 123}
        
        response = handler.handle(event, None)
        
        # Response should be direct (not wrapped)
        assert response["success"] is True
        assert len(response["executions"]) == 1

    def test_lambda_handler_validation_error(self, handler):
        """Test lambda_handler with validation error."""
        event = {"brandid": -5}
        
        with pytest.raises(UserInputError):
            handler.handle(event, None)

    def test_lambda_handler_backend_error(self, handler):
        """Test lambda_handler with backend service error."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        
        error_response = {
            "Error": {
                "Code": "ServiceException",
                "Message": "Service unavailable"
            }
        }
        handler.sfn_client.start_execution.side_effect = ClientError(error_response, "StartExecution")
        
        event = {"brandid": 123}
        
        with pytest.raises(BackendServiceError):
            handler.handle(event, None)

    # ========== Edge Cases ==========

    def test_execute_result_structure(self, handler):
        """Test that execute returns correct result structure."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        handler.sfn_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123-20240101-120000",
            "startDate": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        result = handler.execute({"brandid": 123})
        
        # Verify result structure
        assert "executions" in result
        assert "success" in result
        assert isinstance(result["executions"], list)
        assert isinstance(result["success"], bool)
        
        # Verify execution structure
        execution = result["executions"][0]
        assert "brandid" in execution
        assert "execution_arn" in execution
        assert "start_time" in execution

    def test_workflow_input_structure(self, handler):
        """Test that workflow input has correct structure."""
        handler.dynamodb_client.get_brand_by_id.return_value = {"brandid": 123}
        handler.sfn_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:eu-west-1:123456789012:execution:test-workflow:brand123-20240101-120000",
            "startDate": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        handler.start_single_workflow(123)
        
        # Verify workflow input structure
        call_args = handler.sfn_client.start_execution.call_args
        workflow_input = json.loads(call_args[1]["input"])
        
        assert workflow_input["action"] == "start_workflow"
        assert workflow_input["brandid"] == 123
        assert "config" in workflow_input
        assert "max_iterations" in workflow_input["config"]
        assert "confidence_threshold" in workflow_input["config"]
        assert "enable_confirmation" in workflow_input["config"]
        assert "enable_tiebreaker" in workflow_input["config"]
