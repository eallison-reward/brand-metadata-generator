"""Unit tests for workflow execution logging with dual storage.

This module tests that workflow execution logging correctly uses dual storage
to write execution details to both S3 and Athena.
"""

import json
import os
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

# Set environment variable before importing handlers
os.environ["STATE_MACHINE_ARN"] = "arn:aws:states:eu-west-1:123456789012:stateMachine:workflow"

from lambda_functions.start_workflow.handler import StartWorkflowHandler
from lambda_functions.check_workflow_status.handler import CheckWorkflowStatusHandler


class TestStartWorkflowLogging:
    """Test workflow execution logging in start_workflow handler."""

    @patch("lambda_functions.start_workflow.handler.DualStorageClient")
    @patch("lambda_functions.start_workflow.handler.DynamoDBClient")
    @patch("lambda_functions.start_workflow.handler.boto3")
    def test_logs_workflow_start_to_dual_storage(self, mock_boto3, mock_dynamodb_client_class, mock_dual_storage_class):
        """Test that starting a workflow logs execution start to dual storage."""
        # Arrange
        mock_sfn_client = MagicMock()
        mock_boto3.client.return_value = mock_sfn_client
        
        # Mock DynamoDB client for brand verification
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_instance.get_brand_by_id.return_value = {"brandid": 123}
        mock_dynamodb_client_class.return_value = mock_dynamodb_instance
        
        # Mock dual storage client
        mock_dual_storage = MagicMock()
        mock_dual_storage.write_workflow_execution.return_value = {
            "s3_key": "workflow-executions/exec-123.json",
            "status": "success"
        }
        mock_dual_storage_class.return_value = mock_dual_storage
        
        # Mock Step Functions response
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123"
        start_date = datetime.utcnow()
        mock_sfn_client.start_execution.return_value = {
            "executionArn": execution_arn,
            "startDate": start_date,
        }
        
        handler = StartWorkflowHandler()
        
        # Act
        result = handler.start_single_workflow(brandid=123)
        
        # Assert
        assert result["execution_arn"] == execution_arn
        
        # Verify dual storage was called with correct data
        mock_dual_storage.write_workflow_execution.assert_called_once()
        call_args = mock_dual_storage.write_workflow_execution.call_args[0][0]
        
        assert call_args["execution_arn"] == execution_arn
        assert call_args["brandid"] == 123
        assert call_args["status"] == "RUNNING"
        assert "start_time" in call_args
        assert "input_data" in call_args

    @patch("lambda_functions.start_workflow.handler.DualStorageClient")
    @patch("lambda_functions.start_workflow.handler.DynamoDBClient")
    @patch("lambda_functions.start_workflow.handler.boto3")
    def test_workflow_start_succeeds_even_if_logging_fails(self, mock_boto3, mock_dynamodb_client_class, mock_dual_storage_class):
        """Test that workflow start succeeds even if dual storage logging fails."""
        # Arrange
        mock_sfn_client = MagicMock()
        mock_boto3.client.return_value = mock_sfn_client
        
        # Mock DynamoDB client
        mock_dynamodb_instance = MagicMock()
        mock_dynamodb_instance.get_brand_by_id.return_value = {"brandid": 123}
        mock_dynamodb_client_class.return_value = mock_dynamodb_instance
        
        # Mock dual storage to raise exception
        mock_dual_storage = MagicMock()
        mock_dual_storage.write_workflow_execution.side_effect = Exception("Storage error")
        mock_dual_storage_class.return_value = mock_dual_storage
        
        # Mock Step Functions response
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123"
        start_date = datetime.utcnow()
        mock_sfn_client.start_execution.return_value = {
            "executionArn": execution_arn,
            "startDate": start_date,
        }
        
        handler = StartWorkflowHandler()
        
        # Act - should not raise exception
        result = handler.start_single_workflow(brandid=123)
        
        # Assert - workflow start should succeed despite logging failure
        assert result["execution_arn"] == execution_arn
        assert result["brandid"] == 123


class TestCheckWorkflowStatusLogging:
    """Test workflow execution logging in check_workflow_status handler."""

    @patch("lambda_functions.check_workflow_status.handler.DualStorageClient")
    @patch("lambda_functions.check_workflow_status.handler.boto3")
    def test_logs_completed_workflow_to_dual_storage(self, mock_boto3, mock_dual_storage_class):
        """Test that checking a completed workflow logs execution details to dual storage."""
        # Arrange
        mock_sfn_client = MagicMock()
        mock_boto3.client.return_value = mock_sfn_client
        
        # Mock dual storage client
        mock_dual_storage = MagicMock()
        mock_dual_storage.write_workflow_execution.return_value = {
            "s3_key": "workflow-executions/exec-123.json",
            "status": "success"
        }
        mock_dual_storage_class.return_value = mock_dual_storage
        
        # Mock Step Functions response for completed execution
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123"
        start_date = datetime.utcnow()
        stop_date = datetime.utcnow()
        
        workflow_input = json.dumps({"brandid": 123, "action": "start_workflow"})
        workflow_output = json.dumps({"result": "success"})
        
        mock_sfn_client.describe_execution.return_value = {
            "executionArn": execution_arn,
            "status": "SUCCEEDED",
            "startDate": start_date,
            "stopDate": stop_date,
            "input": workflow_input,
            "output": workflow_output,
            "name": "test-execution",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:workflow",
        }
        
        handler = CheckWorkflowStatusHandler()
        
        # Act
        result = handler.execute({"execution_arn": execution_arn})
        
        # Assert
        assert result["status"] == "SUCCEEDED"
        
        # Verify dual storage was called with correct data
        mock_dual_storage.write_workflow_execution.assert_called_once()
        call_args = mock_dual_storage.write_workflow_execution.call_args[0][0]
        
        assert call_args["execution_arn"] == execution_arn
        assert call_args["brandid"] == 123
        assert call_args["status"] == "SUCCEEDED"
        assert "start_time" in call_args
        assert "stop_time" in call_args
        assert "duration_seconds" in call_args
        assert "input_data" in call_args
        assert "output_data" in call_args

    @patch("lambda_functions.check_workflow_status.handler.DualStorageClient")
    @patch("lambda_functions.check_workflow_status.handler.boto3")
    def test_logs_failed_workflow_with_error_message(self, mock_boto3, mock_dual_storage_class):
        """Test that checking a failed workflow logs error details to dual storage."""
        # Arrange
        mock_sfn_client = MagicMock()
        mock_boto3.client.return_value = mock_sfn_client
        
        # Mock dual storage client
        mock_dual_storage = MagicMock()
        mock_dual_storage.write_workflow_execution.return_value = {
            "s3_key": "workflow-executions/exec-123.json",
            "status": "success"
        }
        mock_dual_storage_class.return_value = mock_dual_storage
        
        # Mock Step Functions response for failed execution
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123"
        start_date = datetime.utcnow()
        stop_date = datetime.utcnow()
        
        workflow_input = json.dumps({"brandid": 456, "action": "start_workflow"})
        
        mock_sfn_client.describe_execution.return_value = {
            "executionArn": execution_arn,
            "status": "FAILED",
            "startDate": start_date,
            "stopDate": stop_date,
            "input": workflow_input,
            "error": "States.TaskFailed",
            "cause": "Lambda function failed",
            "name": "test-execution",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:workflow",
        }
        
        handler = CheckWorkflowStatusHandler()
        
        # Act
        result = handler.execute({"execution_arn": execution_arn})
        
        # Assert
        assert result["status"] == "FAILED"
        
        # Verify dual storage was called with error details
        mock_dual_storage.write_workflow_execution.assert_called_once()
        call_args = mock_dual_storage.write_workflow_execution.call_args[0][0]
        
        assert call_args["execution_arn"] == execution_arn
        assert call_args["brandid"] == 456
        assert call_args["status"] == "FAILED"
        assert "error_message" in call_args
        assert "States.TaskFailed" in call_args["error_message"]
        assert "Lambda function failed" in call_args["error_message"]

    @patch("lambda_functions.check_workflow_status.handler.DualStorageClient")
    @patch("lambda_functions.check_workflow_status.handler.boto3")
    def test_does_not_log_running_workflow(self, mock_boto3, mock_dual_storage_class):
        """Test that checking a running workflow does not log to dual storage."""
        # Arrange
        mock_sfn_client = MagicMock()
        mock_boto3.client.return_value = mock_sfn_client
        
        # Mock dual storage client
        mock_dual_storage = MagicMock()
        mock_dual_storage_class.return_value = mock_dual_storage
        
        # Mock Step Functions response for running execution
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123"
        start_date = datetime.utcnow()
        
        workflow_input = json.dumps({"brandid": 789, "action": "start_workflow"})
        
        mock_sfn_client.describe_execution.return_value = {
            "executionArn": execution_arn,
            "status": "RUNNING",
            "startDate": start_date,
            "input": workflow_input,
            "name": "test-execution",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:workflow",
        }
        
        handler = CheckWorkflowStatusHandler()
        
        # Act
        result = handler.execute({"execution_arn": execution_arn})
        
        # Assert
        assert result["status"] == "RUNNING"
        
        # Verify dual storage was NOT called for running execution
        mock_dual_storage.write_workflow_execution.assert_not_called()

    @patch("lambda_functions.check_workflow_status.handler.DualStorageClient")
    @patch("lambda_functions.check_workflow_status.handler.boto3")
    def test_status_check_succeeds_even_if_logging_fails(self, mock_boto3, mock_dual_storage_class):
        """Test that status check succeeds even if dual storage logging fails."""
        # Arrange
        mock_sfn_client = MagicMock()
        mock_boto3.client.return_value = mock_sfn_client
        
        # Mock dual storage to raise exception
        mock_dual_storage = MagicMock()
        mock_dual_storage.write_workflow_execution.side_effect = Exception("Storage error")
        mock_dual_storage_class.return_value = mock_dual_storage
        
        # Mock Step Functions response for completed execution
        execution_arn = "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123"
        start_date = datetime.utcnow()
        stop_date = datetime.utcnow()
        
        workflow_input = json.dumps({"brandid": 123, "action": "start_workflow"})
        workflow_output = json.dumps({"result": "success"})
        
        mock_sfn_client.describe_execution.return_value = {
            "executionArn": execution_arn,
            "status": "SUCCEEDED",
            "startDate": start_date,
            "stopDate": stop_date,
            "input": workflow_input,
            "output": workflow_output,
            "name": "test-execution",
            "stateMachineArn": "arn:aws:states:eu-west-1:123456789012:stateMachine:workflow",
        }
        
        handler = CheckWorkflowStatusHandler()
        
        # Act - should not raise exception
        result = handler.execute({"execution_arn": execution_arn})
        
        # Assert - status check should succeed despite logging failure
        assert result["status"] == "SUCCEEDED"
        assert "output" in result
