"""Unit tests for feedback submission handler with dual storage."""

import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from lambda_functions.feedback_submission.handler import FeedbackSubmissionHandler
from shared.utils.error_handler import BackendServiceError, UserInputError


class TestFeedbackSubmissionHandler:
    """Test suite for FeedbackSubmissionHandler."""

    @pytest.fixture
    def handler(self):
        """Create handler instance with mocked dependencies."""
        with patch('lambda_functions.feedback_submission.handler.DualStorageClient'), \
             patch('lambda_functions.feedback_submission.handler.AthenaClient'):
            handler = FeedbackSubmissionHandler()
            handler.dual_storage = MagicMock()
            handler.athena_client = MagicMock()
            return handler

    def test_validate_parameters_valid(self, handler):
        """Test parameter validation with valid inputs."""
        parameters = {
            "brandid": 123,
            "feedback_text": "The regex pattern is incorrect",
            "metadata_version": 1
        }
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_missing_brandid(self, handler):
        """Test parameter validation fails when brandid is missing."""
        parameters = {
            "feedback_text": "Some feedback"
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "brandid" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_brandid_type(self, handler):
        """Test parameter validation fails when brandid is not an integer."""
        parameters = {
            "brandid": "not_an_int",
            "feedback_text": "Some feedback"
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "integer" in str(exc_info.value).lower()

    def test_validate_parameters_missing_feedback_text(self, handler):
        """Test parameter validation fails when feedback_text is missing."""
        parameters = {
            "brandid": 123
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "feedback_text" in str(exc_info.value).lower()

    def test_validate_parameters_empty_feedback_text(self, handler):
        """Test parameter validation fails when feedback_text is empty."""
        parameters = {
            "brandid": 123,
            "feedback_text": "   "
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "empty" in str(exc_info.value).lower()

    def test_store_feedback_uses_dual_storage(self, handler):
        """Test that store_feedback uses dual storage client."""
        feedback_record = {
            "feedback_id": "test-123",
            "brandid": 456,
            "feedback_text": "Test feedback",
            "category": "regex_error",
            "issues_identified": ["pattern_mismatch"],
            "misclassified_combos": [],
            "submitted_at": datetime.utcnow().isoformat(),
        }
        
        # Mock dual storage response
        handler.dual_storage.write_feedback.return_value = {
            "s3_key": "feedback/brand_456_test-123.json",
            "feedback_id": "test-123",
            "status": "success"
        }
        
        # Call store_feedback
        s3_key = handler.store_feedback(feedback_record, 456)
        
        # Verify dual storage was called correctly
        handler.dual_storage.write_feedback.assert_called_once_with(456, feedback_record)
        assert s3_key == "feedback/brand_456_test-123.json"

    def test_store_feedback_handles_dual_storage_failure(self, handler):
        """Test that store_feedback raises BackendServiceError on dual storage failure."""
        feedback_record = {
            "feedback_id": "test-123",
            "brandid": 456,
            "feedback_text": "Test feedback",
        }
        
        # Mock dual storage failure
        handler.dual_storage.write_feedback.side_effect = Exception("S3 write failed")
        
        # Should raise BackendServiceError
        with pytest.raises(BackendServiceError) as exc_info:
            handler.store_feedback(feedback_record, 456)
        
        assert "dual storage" in str(exc_info.value).lower()

    @patch('lambda_functions.feedback_submission.handler.parse_feedback')
    def test_execute_with_dual_storage(self, mock_parse_feedback, handler):
        """Test full execution flow uses dual storage."""
        # Mock parse_feedback response
        mock_parse_feedback.return_value = {
            "feedback_id": "parsed-123",
            "category": "regex_error",
            "issues_identified": ["pattern_mismatch"],
            "misclassified_combos": [],
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # Mock get_latest_metadata_version
        handler.athena_client.execute_query.return_value = [{"max_version": 2}]
        
        # Mock dual storage response
        handler.dual_storage.write_feedback.return_value = {
            "s3_key": "feedback/brand_789_parsed-123.json",
            "feedback_id": "parsed-123",
            "status": "success"
        }
        
        # Execute
        parameters = {
            "brandid": 789,
            "feedback_text": "The regex is wrong"
        }
        result = handler.execute(parameters)
        
        # Verify dual storage was used
        handler.dual_storage.write_feedback.assert_called_once()
        call_args = handler.dual_storage.write_feedback.call_args
        assert call_args[0][0] == 789  # brandid
        assert call_args[0][1]["feedback_id"] == "parsed-123"
        assert call_args[0][1]["metadata_version"] == 2
        
        # Verify result
        assert result["feedback_id"] == "parsed-123"
        assert result["stored"] is True
        assert "s3://" in result["storage_location"]

    def test_is_retryable_error(self, handler):
        """Test error retry logic."""
        # Backend errors should be retryable
        assert handler.is_retryable_error(BackendServiceError("S3 failed"))
        
        # User input errors should not be retryable
        assert not handler.is_retryable_error(UserInputError("Invalid input"))

    @patch('lambda_functions.feedback_submission.handler.parse_feedback')
    def test_feedback_parsing_extraction(self, mock_parse_feedback, handler):
        """Test that feedback is correctly parsed and extracted."""
        # Mock parse_feedback to return structured data
        mock_parse_feedback.return_value = {
            "feedback_id": "test-uuid-123",
            "category": "regex_error",
            "issues_identified": ["pattern_too_broad", "missing_edge_case"],
            "misclassified_combos": [101, 102, 103],
            "timestamp": "2024-01-15T10:30:00Z"
        }
        
        # Mock get_latest_metadata_version
        handler.athena_client.execute_query.return_value = [{"max_version": 3}]
        
        # Mock dual storage
        handler.dual_storage.write_feedback.return_value = {
            "s3_key": "feedback/brand_999_test-uuid-123.json",
            "feedback_id": "test-uuid-123",
            "status": "success"
        }
        
        # Execute with feedback text
        parameters = {
            "brandid": 999,
            "feedback_text": "The regex pattern matches too many transactions. Combos 101, 102, 103 are misclassified."
        }
        result = handler.execute(parameters)
        
        # Verify parse_feedback was called correctly
        mock_parse_feedback.assert_called_once_with(
            "The regex pattern matches too many transactions. Combos 101, 102, 103 are misclassified.",
            999
        )
        
        # Verify extracted data is in result
        assert result["feedback_id"] == "test-uuid-123"
        assert result["category"] == "regex_error"
        assert result["issues_identified"] == ["pattern_too_broad", "missing_edge_case"]
        assert result["misclassified_combos"] == [101, 102, 103]

    @patch('lambda_functions.feedback_submission.handler.parse_feedback')
    def test_feedback_parsing_with_category_adjustment(self, mock_parse_feedback, handler):
        """Test feedback parsing for category adjustment type."""
        mock_parse_feedback.return_value = {
            "feedback_id": "cat-uuid-456",
            "category": "category_error",
            "issues_identified": ["wrong_sector"],
            "misclassified_combos": [],
            "timestamp": "2024-01-15T11:00:00Z"
        }
        
        handler.athena_client.execute_query.return_value = [{"max_version": 1}]
        handler.dual_storage.write_feedback.return_value = {
            "s3_key": "feedback/brand_555_cat-uuid-456.json",
            "feedback_id": "cat-uuid-456",
            "status": "success"
        }
        
        parameters = {
            "brandid": 555,
            "feedback_text": "This brand should be in Retail sector, not Food & Beverage"
        }
        result = handler.execute(parameters)
        
        assert result["category"] == "category_error"
        assert "wrong_sector" in result["issues_identified"]

    @patch('lambda_functions.feedback_submission.handler.parse_feedback')
    def test_feedback_parsing_with_general_comments(self, mock_parse_feedback, handler):
        """Test feedback parsing for general comments type."""
        mock_parse_feedback.return_value = {
            "feedback_id": "gen-uuid-789",
            "category": "general_comment",
            "issues_identified": ["needs_review"],
            "misclassified_combos": [],
            "timestamp": "2024-01-15T12:00:00Z"
        }
        
        handler.athena_client.execute_query.return_value = [{"max_version": 2}]
        handler.dual_storage.write_feedback.return_value = {
            "s3_key": "feedback/brand_777_gen-uuid-789.json",
            "feedback_id": "gen-uuid-789",
            "status": "success"
        }
        
        parameters = {
            "brandid": 777,
            "feedback_text": "This brand needs manual review due to complex transaction patterns"
        }
        result = handler.execute(parameters)
        
        assert result["category"] == "general_comment"

    def test_get_latest_metadata_version_found(self, handler):
        """Test getting latest metadata version when metadata exists."""
        handler.athena_client.execute_query.return_value = [{"max_version": 5}]
        
        version = handler.get_latest_metadata_version(123)
        
        assert version == 5
        handler.athena_client.execute_query.assert_called_once()

    def test_get_latest_metadata_version_not_found(self, handler):
        """Test getting latest metadata version when no metadata exists."""
        handler.athena_client.execute_query.return_value = [{"max_version": None}]
        
        version = handler.get_latest_metadata_version(456)
        
        # Should default to version 1
        assert version == 1

    def test_get_latest_metadata_version_query_error(self, handler):
        """Test getting latest metadata version when query fails."""
        handler.athena_client.execute_query.side_effect = Exception("Athena error")
        
        version = handler.get_latest_metadata_version(789)
        
        # Should default to version 1 on error
        assert version == 1

    @patch('lambda_functions.feedback_submission.handler.parse_feedback')
    def test_storage_to_s3_and_athena(self, mock_parse_feedback, handler):
        """Test that feedback is stored to both S3 and Athena via dual storage."""
        mock_parse_feedback.return_value = {
            "feedback_id": "storage-test-123",
            "category": "regex_error",
            "issues_identified": ["test_issue"],
            "misclassified_combos": [],
            "timestamp": "2024-01-15T13:00:00Z"
        }
        
        handler.athena_client.execute_query.return_value = [{"max_version": 1}]
        
        # Mock dual storage to verify it's called
        handler.dual_storage.write_feedback.return_value = {
            "s3_key": "feedback/brand_888_storage-test-123.json",
            "feedback_id": "storage-test-123",
            "status": "success"
        }
        
        parameters = {
            "brandid": 888,
            "feedback_text": "Test feedback for storage",
            "metadata_version": 1
        }
        result = handler.execute(parameters)
        
        # Verify dual storage was called with correct parameters
        handler.dual_storage.write_feedback.assert_called_once()
        call_args = handler.dual_storage.write_feedback.call_args[0]
        
        # First argument should be brandid
        assert call_args[0] == 888
        
        # Second argument should be feedback record
        feedback_record = call_args[1]
        assert feedback_record["feedback_id"] == "storage-test-123"
        assert feedback_record["brandid"] == 888
        assert feedback_record["metadata_version"] == 1
        assert feedback_record["feedback_text"] == "Test feedback for storage"
        assert feedback_record["category"] == "regex_error"
        assert "submitted_at" in feedback_record
        assert "submitted_by" in feedback_record
        
        # Verify result contains storage location
        assert result["stored"] is True
        assert "s3://" in result["storage_location"]
        assert "brand_888_storage-test-123.json" in result["storage_location"]

    def test_retry_configuration(self, handler):
        """Test that handler is configured with correct retry settings."""
        # Verify handler has retry configuration
        assert handler.max_retries == 1
        assert handler.initial_delay == 2.0

    def test_is_retryable_error(self, handler):
        """Test error retry logic classification."""
        # Backend errors should be retryable
        assert handler.is_retryable_error(BackendServiceError("S3 failed"))
        
        # User input errors should not be retryable
        assert not handler.is_retryable_error(UserInputError("Invalid input"))
        
        # Generic exceptions should not be retryable
        assert not handler.is_retryable_error(Exception("Generic error"))

    @patch('lambda_functions.feedback_submission.handler.parse_feedback')
    def test_parsing_error_handling(self, mock_parse_feedback, handler):
        """Test handling of feedback parsing errors."""
        # Simulate parsing failure
        mock_parse_feedback.side_effect = Exception("Failed to parse feedback")
        
        handler.athena_client.execute_query.return_value = [{"max_version": 1}]
        
        parameters = {
            "brandid": 222,
            "feedback_text": "Invalid feedback format"
        }
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "Failed to parse feedback" in str(exc_info.value)

    @patch('lambda_functions.feedback_submission.handler.parse_feedback')
    def test_parsing_returns_error_field(self, mock_parse_feedback, handler):
        """Test handling when parse_feedback returns an error field."""
        # Simulate parse_feedback returning error
        mock_parse_feedback.return_value = {
            "feedback_id": "error-123",
            "error": "Invalid feedback format"
        }
        
        handler.athena_client.execute_query.return_value = [{"max_version": 1}]
        
        parameters = {
            "brandid": 333,
            "feedback_text": "Bad format"
        }
        
        with pytest.raises(UserInputError) as exc_info:
            handler.execute(parameters)
        
        assert "Invalid feedback format" in str(exc_info.value)

    def test_validate_parameters_invalid_metadata_version_type(self, handler):
        """Test parameter validation fails when metadata_version is not an integer."""
        parameters = {
            "brandid": 123,
            "feedback_text": "Some feedback",
            "metadata_version": "not_an_int"
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "integer" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_metadata_version_value(self, handler):
        """Test parameter validation fails when metadata_version is less than 1."""
        parameters = {
            "brandid": 123,
            "feedback_text": "Some feedback",
            "metadata_version": 0
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "at least 1" in str(exc_info.value).lower()

    def test_validate_parameters_negative_brandid(self, handler):
        """Test parameter validation fails when brandid is negative."""
        parameters = {
            "brandid": -5,
            "feedback_text": "Some feedback"
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_zero_brandid(self, handler):
        """Test parameter validation fails when brandid is zero."""
        parameters = {
            "brandid": 0,
            "feedback_text": "Some feedback"
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()
