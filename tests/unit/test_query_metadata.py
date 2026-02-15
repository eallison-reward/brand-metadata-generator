"""Unit tests for query_metadata Lambda handler.

Requirements: 7.6
"""

import os
import pytest
from unittest.mock import MagicMock, patch

# Set environment variables before importing handler
os.environ['S3_BUCKET'] = 'test-bucket'
os.environ['AWS_REGION'] = 'eu-west-1'

from lambda_functions.query_metadata.handler import QueryMetadataHandler
from shared.utils.error_handler import UserInputError, BackendServiceError


class TestQueryMetadataHandler:
    """Test suite for QueryMetadataHandler."""

    @pytest.fixture
    def handler(self):
        """Create handler instance with mocked dependencies."""
        with patch.dict('os.environ', {
            'S3_BUCKET': 'test-bucket',
            'AWS_REGION': 'eu-west-1'
        }):
            with patch('lambda_functions.query_metadata.handler.S3Client'):
                handler = QueryMetadataHandler()
                handler.s3_client = MagicMock()
                return handler

    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing."""
        return {
            "brandid": 123,
            "brandname": "Test Brand",
            "regex": "test.*brand",
            "mccids": [5411, 5812],
            "confidence_score": 0.85,
            "version": 1,
            "generated_at": "2024-01-01T12:00:00Z",
            "evaluator_issues": ["Minor issue"],
            "coverage_narratives_matched": 0.9,
            "coverage_false_positives": 0.1,
            "matched_combos": {
                "confirmed": [1, 2, 3],
                "excluded": [4],
                "requires_human_review": [5, 6]
            },
            "sector": "Retail"
        }

    # ========== Parameter Validation Tests ==========

    def test_validate_parameters_valid_brandid(self, handler):
        """Test parameter validation with valid brand ID."""
        parameters = {"brandid": 123}
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_with_version(self, handler):
        """Test parameter validation with version parameter."""
        parameters = {"brandid": 456, "version": 2}
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_with_latest_version(self, handler):
        """Test parameter validation with 'latest' version."""
        parameters = {"brandid": 789, "version": "latest"}
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

    def test_validate_parameters_converts_string_brandid(self, handler):
        """Test parameter validation converts string brandid to integer."""
        parameters = {"brandid": "123"}
        handler.validate_parameters(parameters)
        assert parameters["brandid"] == 123
        assert isinstance(parameters["brandid"], int)

    def test_validate_parameters_invalid_version_type(self, handler):
        """Test parameter validation fails when version is invalid type."""
        parameters = {"brandid": 123, "version": [1, 2]}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "version" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_version_zero(self, handler):
        """Test parameter validation fails when version is zero."""
        parameters = {"brandid": 123, "version": 0}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_version_negative(self, handler):
        """Test parameter validation fails when version is negative."""
        parameters = {"brandid": 123, "version": -2}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_converts_string_version(self, handler):
        """Test parameter validation converts string version to integer."""
        parameters = {"brandid": 123, "version": "5"}
        handler.validate_parameters(parameters)
        assert parameters["version"] == 5
        assert isinstance(parameters["version"], int)

    # ========== Metadata Retrieval Tests ==========

    def test_execute_retrieves_latest_metadata(self, handler, sample_metadata):
        """Test metadata retrieval for existing brand with latest version."""
        handler.s3_client.read_metadata.return_value = sample_metadata
        
        parameters = {"brandid": 123}
        result = handler.execute(parameters)
        
        assert result["found"] is True
        assert result["brandid"] == 123
        assert "metadata" in result
        assert result["metadata"]["brandname"] == "Test Brand"
        assert result["metadata"]["regex"] == "test.*brand"
        
        # Verify S3 client was called correctly
        handler.s3_client.read_metadata.assert_called_once_with(123, prefix="metadata")

    def test_execute_retrieves_specific_version(self, handler, sample_metadata):
        """Test metadata retrieval for specific version."""
        handler.s3_client.read_json.return_value = sample_metadata
        
        parameters = {"brandid": 456, "version": 3}
        result = handler.execute(parameters)
        
        assert result["found"] is True
        assert result["brandid"] == 456
        
        # Verify S3 client was called with correct key
        handler.s3_client.read_json.assert_called_once_with("metadata/brand_456_v3.json")

    def test_execute_handles_non_existent_brand(self, handler):
        """Test handling of non-existent brand."""
        handler.s3_client.read_metadata.return_value = None
        handler.s3_client.list_keys.return_value = []
        
        parameters = {"brandid": 999}
        result = handler.execute(parameters)
        
        assert result["found"] is False
        assert result["brandid"] == 999
        assert "message" in result
        assert "999" in result["message"]
        assert "metadata" not in result

    def test_execute_handles_non_existent_version(self, handler):
        """Test handling of non-existent version."""
        handler.s3_client.read_json.return_value = None
        
        parameters = {"brandid": 123, "version": 99}
        result = handler.execute(parameters)
        
        assert result["found"] is False
        assert result["brandid"] == 123
        assert result["version"] == 99
        assert "version 99" in result["message"]

    def test_execute_finds_latest_versioned_metadata(self, handler, sample_metadata):
        """Test finding latest version when no unversioned file exists."""
        # First call returns None (no unversioned file)
        handler.s3_client.read_metadata.return_value = None
        
        # List keys returns versioned files
        handler.s3_client.list_keys.return_value = [
            "metadata/brand_123_v1.json",
            "metadata/brand_123_v3.json",
            "metadata/brand_123_v2.json"
        ]
        
        # Read the latest version
        handler.s3_client.read_json.return_value = sample_metadata
        
        parameters = {"brandid": 123}
        result = handler.execute(parameters)
        
        assert result["found"] is True
        # Should read v3 (highest version)
        handler.s3_client.read_json.assert_called_once_with("metadata/brand_123_v3.json")

    # ========== Metadata Formatting Tests ==========

    def test_format_metadata_includes_all_fields(self, handler, sample_metadata):
        """Test that metadata formatting includes all expected fields."""
        handler.s3_client.read_metadata.return_value = sample_metadata
        
        parameters = {"brandid": 123}
        result = handler.execute(parameters)
        
        metadata = result["metadata"]
        assert metadata["brandid"] == 123
        assert metadata["brandname"] == "Test Brand"
        assert metadata["regex"] == "test.*brand"
        assert metadata["mccids"] == [5411, 5812]
        assert metadata["confidence_score"] == 0.85
        assert metadata["version"] == 1
        assert metadata["generated_at"] == "2024-01-01T12:00:00Z"

    def test_format_metadata_includes_optional_fields(self, handler, sample_metadata):
        """Test that metadata formatting includes optional fields when present."""
        handler.s3_client.read_metadata.return_value = sample_metadata
        
        parameters = {"brandid": 123}
        result = handler.execute(parameters)
        
        metadata = result["metadata"]
        assert "evaluator_issues" in metadata
        assert metadata["evaluator_issues"] == ["Minor issue"]
        assert "coverage_narratives_matched" in metadata
        assert metadata["coverage_narratives_matched"] == 0.9
        assert "coverage_false_positives" in metadata
        assert metadata["coverage_false_positives"] == 0.1
        assert "sector" in metadata
        assert metadata["sector"] == "Retail"

    def test_format_metadata_includes_matched_combos_summary(self, handler, sample_metadata):
        """Test that metadata formatting includes matched combos summary."""
        handler.s3_client.read_metadata.return_value = sample_metadata
        
        parameters = {"brandid": 123}
        result = handler.execute(parameters)
        
        metadata = result["metadata"]
        assert "matched_combos_summary" in metadata
        summary = metadata["matched_combos_summary"]
        assert summary["confirmed_count"] == 3
        assert summary["excluded_count"] == 1
        assert summary["requires_review_count"] == 2

    def test_format_metadata_handles_missing_optional_fields(self, handler):
        """Test that metadata formatting handles missing optional fields."""
        minimal_metadata = {
            "brandid": 123,
            "brandname": "Minimal Brand",
            "regex": "minimal",
            "mccids": [5411],
            "confidence_score": 0.75,
            "generated_at": "2024-01-01T12:00:00Z"
        }
        handler.s3_client.read_metadata.return_value = minimal_metadata
        
        parameters = {"brandid": 123}
        result = handler.execute(parameters)
        
        metadata = result["metadata"]
        # Should have defaults for missing fields
        assert metadata["brandname"] == "Minimal Brand"
        # Version defaults to 1 when not in metadata and version param is "latest"
        assert metadata["version"] in [1, "latest"]
        # Optional fields should not be present
        assert "evaluator_issues" not in metadata
        assert "sector" not in metadata
        assert "matched_combos_summary" not in metadata

    def test_format_metadata_handles_unknown_brandname(self, handler):
        """Test that metadata formatting handles missing brandname."""
        metadata_no_name = {
            "brandid": 123,
            "regex": "test",
            "mccids": [5411],
            "confidence_score": 0.8,
            "generated_at": "2024-01-01T12:00:00Z"
        }
        handler.s3_client.read_metadata.return_value = metadata_no_name
        
        parameters = {"brandid": 123}
        result = handler.execute(parameters)
        
        metadata = result["metadata"]
        assert metadata["brandname"] == "Unknown"

    def test_format_metadata_handles_empty_mccids(self, handler):
        """Test that metadata formatting handles empty mccids."""
        metadata_empty_mccids = {
            "brandid": 123,
            "brandname": "Test",
            "regex": "test",
            "mccids": [],
            "confidence_score": 0.8,
            "generated_at": "2024-01-01T12:00:00Z"
        }
        handler.s3_client.read_metadata.return_value = metadata_empty_mccids
        
        parameters = {"brandid": 123}
        result = handler.execute(parameters)
        
        metadata = result["metadata"]
        assert metadata["mccids"] == []

    # ========== Latest Version Finding Tests ==========

    def test_find_latest_version_with_multiple_versions(self, handler, sample_metadata):
        """Test finding latest version from multiple versioned files."""
        handler.s3_client.list_keys.return_value = [
            "metadata/brand_123_v1.json",
            "metadata/brand_123_v5.json",
            "metadata/brand_123_v3.json",
            "metadata/brand_123_v10.json"
        ]
        handler.s3_client.read_json.return_value = sample_metadata
        
        result = handler._find_latest_version(123)
        
        assert result is not None
        # Should read v10 (highest version)
        handler.s3_client.read_json.assert_called_once_with("metadata/brand_123_v10.json")

    def test_find_latest_version_with_no_versions(self, handler):
        """Test finding latest version when no versioned files exist."""
        handler.s3_client.list_keys.return_value = []
        
        result = handler._find_latest_version(123)
        
        assert result is None

    def test_find_latest_version_ignores_non_versioned_files(self, handler, sample_metadata):
        """Test that latest version finding ignores non-versioned files."""
        handler.s3_client.list_keys.return_value = [
            "metadata/brand_123.json",  # No version
            "metadata/brand_123_v2.json",
            "metadata/brand_123_backup.json"  # Not a version
        ]
        handler.s3_client.read_json.return_value = sample_metadata
        
        result = handler._find_latest_version(123)
        
        # Should only find v2
        handler.s3_client.read_json.assert_called_once_with("metadata/brand_123_v2.json")

    def test_find_latest_version_handles_malformed_filenames(self, handler, sample_metadata):
        """Test that latest version finding handles malformed filenames."""
        handler.s3_client.list_keys.return_value = [
            "metadata/brand_123_v2.json",
            "metadata/brand_123_vabc.json",  # Invalid version
            "metadata/brand_123_v.json",  # No version number
            "metadata/brand_123_v3.json"
        ]
        handler.s3_client.read_json.return_value = sample_metadata
        
        result = handler._find_latest_version(123)
        
        # Should find v3 (ignoring malformed files)
        handler.s3_client.read_json.assert_called_once_with("metadata/brand_123_v3.json")

    def test_find_latest_version_handles_s3_error(self, handler):
        """Test that latest version finding handles S3 errors gracefully."""
        handler.s3_client.list_keys.side_effect = Exception("S3 error")
        
        result = handler._find_latest_version(123)
        
        assert result is None

    # ========== Error Handling Tests ==========

    def test_execute_handles_s3_error(self, handler):
        """Test that execute handles S3 errors appropriately."""
        handler.s3_client.read_metadata.side_effect = Exception("S3 connection failed")
        
        parameters = {"brandid": 123}
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "s3" in str(exc_info.value).lower()
        # Error message includes the S3 error details
        assert "failed" in str(exc_info.value).lower()

    def test_execute_handles_json_parse_error(self, handler):
        """Test that execute handles JSON parsing errors."""
        handler.s3_client.read_metadata.side_effect = ValueError("Invalid JSON")
        
        parameters = {"brandid": 456}
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        # Error message includes the JSON error details
        assert "json" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

    # ========== Lambda Handler Integration Tests ==========

    def test_lambda_handler_success(self, handler, sample_metadata):
        """Test lambda_handler with successful execution."""
        handler.s3_client.read_metadata.return_value = sample_metadata
        
        event = {
            "parameters": {"brandid": 123},
            "request_id": "test-request-123"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is True
        assert "data" in response
        assert response["data"]["found"] is True
        assert response["data"]["brandid"] == 123
        assert response["request_id"] == "test-request-123"

    def test_lambda_handler_not_found(self, handler):
        """Test lambda_handler when metadata is not found."""
        handler.s3_client.read_metadata.return_value = None
        handler.s3_client.list_keys.return_value = []
        
        event = {
            "parameters": {"brandid": 999},
            "request_id": "test-request-456"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is True
        assert response["data"]["found"] is False
        assert response["data"]["brandid"] == 999

    def test_lambda_handler_validation_error(self, handler):
        """Test lambda_handler with validation error."""
        event = {
            "parameters": {"brandid": -5},
            "request_id": "test-request-789"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["type"] == "user_input"
        assert "positive" in response["error"]["message"].lower()

    def test_lambda_handler_backend_error(self, handler):
        """Test lambda_handler with backend service error."""
        handler.s3_client.read_metadata.side_effect = Exception("S3 error")
        
        event = {
            "parameters": {"brandid": 123},
            "request_id": "test-request-abc"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["type"] == "backend_service"

    # ========== Edge Cases ==========

    def test_execute_with_version_latest_string(self, handler, sample_metadata):
        """Test execute with explicit 'latest' version string."""
        handler.s3_client.read_metadata.return_value = sample_metadata
        
        parameters = {"brandid": 123, "version": "latest"}
        result = handler.execute(parameters)
        
        assert result["found"] is True
        handler.s3_client.read_metadata.assert_called_once_with(123, prefix="metadata")

    def test_execute_result_structure(self, handler, sample_metadata):
        """Test that execute returns correct result structure."""
        handler.s3_client.read_metadata.return_value = sample_metadata
        
        result = handler.execute({"brandid": 123})
        
        # Verify result structure
        assert "found" in result
        assert "brandid" in result
        assert "metadata" in result
        assert isinstance(result["found"], bool)
        assert isinstance(result["brandid"], int)
        assert isinstance(result["metadata"], dict)

    def test_get_required_params(self, handler):
        """Test that get_required_params returns correct list."""
        required = handler.get_required_params()
        assert required == ["brandid"]
