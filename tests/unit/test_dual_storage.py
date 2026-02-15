"""Unit tests for dual storage utility."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from shared.storage.dual_storage import DualStorageClient, DualStorageError


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    with patch("shared.storage.dual_storage.S3Client") as mock:
        yield mock.return_value


@pytest.fixture
def mock_athena_client():
    """Mock Athena client."""
    with patch("shared.storage.dual_storage.AthenaClient") as mock:
        yield mock.return_value


@pytest.fixture
def dual_storage_client(mock_s3_client, mock_athena_client):
    """Create dual storage client with mocked dependencies."""
    return DualStorageClient()


class TestWriteMetadata:
    """Test metadata writing functionality."""

    def test_write_metadata_success(self, dual_storage_client, mock_s3_client, mock_athena_client):
        """Test successful metadata write to both S3 and Athena."""
        # Arrange
        brandid = 123
        metadata = {
            "brandname": "Test Brand",
            "regex": "test.*",
            "mccids": [5411, 5412],
            "confidence_score": 0.95,
        }
        
        mock_s3_client.write_json.return_value = f"metadata/brand_{brandid}.json"
        mock_athena_client.execute_query.return_value = []
        
        # Act
        result = dual_storage_client.write_metadata(brandid, metadata)
        
        # Assert
        assert result["status"] == "success"
        assert result["s3_key"] == f"metadata/brand_{brandid}.json"
        assert result["table"] == "generated_metadata"
        
        # Verify S3 write was called
        mock_s3_client.write_json.assert_called_once()
        call_args = mock_s3_client.write_json.call_args
        assert call_args[0][0] == f"metadata/brand_{brandid}.json"
        
        # Verify data has required fields
        written_data = call_args[0][1]
        assert written_data["brandid"] == brandid
        assert "generated_at" in written_data
        
        # Verify Athena table verification was called
        mock_athena_client.execute_query.assert_called_once()

    def test_write_metadata_with_existing_fields(self, dual_storage_client, mock_s3_client, mock_athena_client):
        """Test metadata write overwrites brandid but preserves generated_at."""
        # Arrange
        brandid = 456
        generated_at = "2024-01-01T00:00:00"
        metadata = {
            "brandid": 999,  # Should be overwritten with the provided brandid
            "generated_at": generated_at,
            "brandname": "Test Brand",
        }
        
        mock_s3_client.write_json.return_value = f"metadata/brand_{brandid}.json"
        mock_athena_client.execute_query.return_value = []
        
        # Act
        result = dual_storage_client.write_metadata(brandid, metadata)
        
        # Assert
        assert result["status"] == "success"
        
        # Verify brandid was overwritten with the provided brandid parameter
        written_data = mock_s3_client.write_json.call_args[0][1]
        assert written_data["brandid"] == brandid  # Should be 456, not 999
        assert written_data["generated_at"] == generated_at

    def test_write_metadata_rollback_on_athena_failure(self, dual_storage_client, mock_s3_client, mock_athena_client):
        """Test rollback when Athena verification fails."""
        # Arrange
        brandid = 789
        metadata = {"brandname": "Test Brand"}
        
        mock_s3_client.write_json.return_value = f"metadata/brand_{brandid}.json"
        mock_athena_client.execute_query.side_effect = Exception("Athena table not found")
        
        # Act & Assert
        with pytest.raises(DualStorageError) as exc_info:
            dual_storage_client.write_metadata(brandid, metadata)
        
        assert "Failed to write to dual storage" in str(exc_info.value)
        
        # Verify S3 delete was called for rollback
        mock_s3_client.delete_key.assert_called_once_with(f"metadata/brand_{brandid}.json")

    def test_write_metadata_rollback_failure(self, dual_storage_client, mock_s3_client, mock_athena_client):
        """Test error handling when rollback also fails."""
        # Arrange
        brandid = 101
        metadata = {"brandname": "Test Brand"}
        
        mock_s3_client.write_json.return_value = f"metadata/brand_{brandid}.json"
        mock_athena_client.execute_query.side_effect = Exception("Athena error")
        mock_s3_client.delete_key.side_effect = Exception("S3 delete failed")
        
        # Act & Assert
        with pytest.raises(DualStorageError) as exc_info:
            dual_storage_client.write_metadata(brandid, metadata)
        
        error_msg = str(exc_info.value)
        assert "rollback also failed" in error_msg
        assert "Manual cleanup may be required" in error_msg


class TestWriteFeedback:
    """Test feedback writing functionality."""

    def test_write_feedback_success(self, dual_storage_client, mock_s3_client, mock_athena_client):
        """Test successful feedback write."""
        # Arrange
        brandid = 123
        feedback = {
            "feedback_text": "The regex is incorrect",
            "category": "regex_correction",
        }
        
        mock_s3_client.write_json.return_value = "feedback/brand_123_test.json"
        mock_athena_client.execute_query.return_value = []
        
        # Act
        result = dual_storage_client.write_feedback(brandid, feedback)
        
        # Assert
        assert result["status"] == "success"
        assert "feedback_id" in result
        assert result["table"] == "feedback_history"
        
        # Verify data has required fields
        written_data = mock_s3_client.write_json.call_args[0][1]
        assert written_data["brandid"] == brandid
        assert "submitted_at" in written_data
        assert "feedback_id" in written_data

    def test_write_feedback_with_existing_id(self, dual_storage_client, mock_s3_client, mock_athena_client):
        """Test feedback write preserves existing feedback_id."""
        # Arrange
        brandid = 456
        feedback_id = "existing-uuid-123"
        feedback = {
            "feedback_id": feedback_id,
            "feedback_text": "Test feedback",
        }
        
        mock_s3_client.write_json.return_value = f"feedback/brand_{brandid}_{feedback_id}.json"
        mock_athena_client.execute_query.return_value = []
        
        # Act
        result = dual_storage_client.write_feedback(brandid, feedback)
        
        # Assert
        assert result["feedback_id"] == feedback_id


class TestWriteWorkflowExecution:
    """Test workflow execution writing functionality."""

    def test_write_workflow_execution_success(self, dual_storage_client, mock_s3_client, mock_athena_client):
        """Test successful workflow execution write."""
        # Arrange
        execution_data = {
            "execution_arn": "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123",
            "brandid": 123,
            "status": "SUCCEEDED",
        }
        
        mock_s3_client.write_json.return_value = "workflow-executions/exec-123.json"
        mock_athena_client.execute_query.return_value = []
        
        # Act
        result = dual_storage_client.write_workflow_execution(execution_data)
        
        # Assert
        assert result["status"] == "success"
        assert result["table"] == "workflow_executions"
        
        # Verify data has required fields
        written_data = mock_s3_client.write_json.call_args[0][1]
        assert "start_time" in written_data

    def test_write_workflow_execution_without_arn(self, dual_storage_client, mock_s3_client, mock_athena_client):
        """Test workflow execution write generates ID when ARN is missing."""
        # Arrange
        execution_data = {
            "brandid": 123,
            "status": "RUNNING",
        }
        
        mock_s3_client.write_json.return_value = "workflow-executions/test.json"
        mock_athena_client.execute_query.return_value = []
        
        # Act
        result = dual_storage_client.write_workflow_execution(execution_data)
        
        # Assert
        assert result["status"] == "success"


class TestWriteEscalation:
    """Test escalation writing functionality."""

    def test_write_escalation_success(self, dual_storage_client, mock_s3_client, mock_athena_client):
        """Test successful escalation write."""
        # Arrange
        escalation = {
            "brandid": 123,
            "brandname": "Test Brand",
            "reason": "Low confidence score",
            "confidence_score": 0.45,
        }
        
        mock_s3_client.write_json.return_value = "escalations/brand_123_test.json"
        mock_athena_client.execute_query.return_value = []
        
        # Act
        result = dual_storage_client.write_escalation(escalation)
        
        # Assert
        assert result["status"] == "success"
        assert "escalation_id" in result
        assert result["table"] == "escalations"
        
        # Verify data has required fields
        written_data = mock_s3_client.write_json.call_args[0][1]
        assert written_data["brandid"] == 123
        assert "escalated_at" in written_data
        assert written_data["status"] == "pending"

    def test_write_escalation_with_custom_status(self, dual_storage_client, mock_s3_client, mock_athena_client):
        """Test escalation write preserves custom status."""
        # Arrange
        escalation = {
            "brandid": 456,
            "status": "resolved",
            "reason": "Test",
        }
        
        mock_s3_client.write_json.return_value = "escalations/brand_456_test.json"
        mock_athena_client.execute_query.return_value = []
        
        # Act
        result = dual_storage_client.write_escalation(escalation)
        
        # Assert
        written_data = mock_s3_client.write_json.call_args[0][1]
        assert written_data["status"] == "resolved"


class TestReadOperations:
    """Test read operations."""

    def test_read_metadata(self, dual_storage_client, mock_s3_client):
        """Test reading metadata from S3."""
        # Arrange
        brandid = 123
        expected_metadata = {"brandid": 123, "brandname": "Test"}
        mock_s3_client.read_metadata.return_value = expected_metadata
        
        # Act
        result = dual_storage_client.read_metadata(brandid)
        
        # Assert
        assert result == expected_metadata
        mock_s3_client.read_metadata.assert_called_once_with(brandid, prefix="metadata")

    def test_read_feedback(self, dual_storage_client, mock_s3_client):
        """Test reading feedback from S3."""
        # Arrange
        brandid = 123
        feedback_id = "test-uuid"
        expected_feedback = {"feedback_id": feedback_id}
        mock_s3_client.read_json.return_value = expected_feedback
        
        # Act
        result = dual_storage_client.read_feedback(brandid, feedback_id)
        
        # Assert
        assert result == expected_feedback
        mock_s3_client.read_json.assert_called_once_with(f"feedback/brand_{brandid}_{feedback_id}.json")

    def test_read_workflow_execution(self, dual_storage_client, mock_s3_client):
        """Test reading workflow execution from S3."""
        # Arrange
        execution_id = "exec-123"
        expected_execution = {"execution_arn": "test"}
        mock_s3_client.read_json.return_value = expected_execution
        
        # Act
        result = dual_storage_client.read_workflow_execution(execution_id)
        
        # Assert
        assert result == expected_execution
        mock_s3_client.read_json.assert_called_once_with(f"workflow-executions/{execution_id}.json")

    def test_read_escalation(self, dual_storage_client, mock_s3_client):
        """Test reading escalation from S3."""
        # Arrange
        brandid = 123
        escalation_id = "esc-uuid"
        expected_escalation = {"escalation_id": escalation_id}
        mock_s3_client.read_json.return_value = expected_escalation
        
        # Act
        result = dual_storage_client.read_escalation(brandid, escalation_id)
        
        # Assert
        assert result == expected_escalation
        mock_s3_client.read_json.assert_called_once_with(f"escalations/brand_{brandid}_{escalation_id}.json")
