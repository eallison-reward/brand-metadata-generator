"""Unit tests for list_escalations Lambda handler.

Requirements: 7.7
"""

import os
import pytest
from unittest.mock import MagicMock, patch

# Set environment variables before importing handler
os.environ['ATHENA_DATABASE'] = 'test_db'
os.environ['AWS_REGION'] = 'eu-west-1'
os.environ['ATHENA_OUTPUT_LOCATION'] = 's3://test-bucket/query-results/'

from lambda_functions.list_escalations.handler import ListEscalationsHandler
from shared.utils.error_handler import UserInputError, BackendServiceError


class TestListEscalationsHandler:
    """Test suite for ListEscalationsHandler."""

    @pytest.fixture
    def handler(self):
        """Create handler instance with mocked dependencies."""
        with patch.dict('os.environ', {
            'ATHENA_DATABASE': 'test_db',
            'AWS_REGION': 'eu-west-1',
            'ATHENA_OUTPUT_LOCATION': 's3://test-bucket/query-results/'
        }):
            with patch('lambda_functions.list_escalations.handler.AthenaClient'):
                handler = ListEscalationsHandler()
                handler.athena_client = MagicMock()
                return handler

    @pytest.fixture
    def sample_escalations(self):
        """Sample escalation data for testing."""
        return [
            {
                "escalation_id": "esc-001",
                "brandid": 123,
                "brandname": "Test Brand A",
                "reason": "Low confidence score",
                "confidence_score": 0.45,
                "escalated_at": "2024-01-01T12:00:00Z",
                "status": "pending"
            },
            {
                "escalation_id": "esc-002",
                "brandid": 456,
                "brandname": "Test Brand B",
                "reason": "Conflicting evaluations",
                "confidence_score": 0.52,
                "escalated_at": "2024-01-02T14:30:00Z",
                "status": "pending"
            },
            {
                "escalation_id": "esc-003",
                "brandid": 789,
                "brandname": "Test Brand C",
                "reason": "Low confidence score",
                "confidence_score": 0.38,
                "escalated_at": "2024-01-03T09:15:00Z",
                "status": "pending"
            }
        ]

    # ========== Parameter Validation Tests ==========

    def test_validate_parameters_no_parameters(self, handler):
        """Test parameter validation with no parameters (all optional)."""
        parameters = {}
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_limit(self, handler):
        """Test parameter validation with valid limit."""
        parameters = {"limit": 20}
        handler.validate_parameters(parameters)
        assert parameters["limit"] == 20

    def test_validate_parameters_converts_string_limit(self, handler):
        """Test parameter validation converts string limit to integer."""
        parameters = {"limit": "15"}
        handler.validate_parameters(parameters)
        assert parameters["limit"] == 15
        assert isinstance(parameters["limit"], int)

    def test_validate_parameters_invalid_limit_zero(self, handler):
        """Test parameter validation fails when limit is zero."""
        parameters = {"limit": 0}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_limit_negative(self, handler):
        """Test parameter validation fails when limit is negative."""
        parameters = {"limit": -5}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_limit_too_large(self, handler):
        """Test parameter validation fails when limit exceeds maximum."""
        parameters = {"limit": 150}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "100" in str(exc_info.value)

    def test_validate_parameters_invalid_limit_type(self, handler):
        """Test parameter validation fails when limit is invalid type."""
        parameters = {"limit": "not_a_number"}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "integer" in str(exc_info.value).lower()

    def test_validate_parameters_valid_sort_by_escalated_at(self, handler):
        """Test parameter validation with valid sort_by escalated_at."""
        parameters = {"sort_by": "escalated_at"}
        handler.validate_parameters(parameters)
        assert parameters["sort_by"] == "escalated_at"

    def test_validate_parameters_valid_sort_by_confidence_score(self, handler):
        """Test parameter validation with valid sort_by confidence_score."""
        parameters = {"sort_by": "confidence_score"}
        handler.validate_parameters(parameters)
        assert parameters["sort_by"] == "confidence_score"

    def test_validate_parameters_valid_sort_by_brandid(self, handler):
        """Test parameter validation with valid sort_by brandid."""
        parameters = {"sort_by": "brandid"}
        handler.validate_parameters(parameters)
        assert parameters["sort_by"] == "brandid"

    def test_validate_parameters_valid_sort_by_brandname(self, handler):
        """Test parameter validation with valid sort_by brandname."""
        parameters = {"sort_by": "brandname"}
        handler.validate_parameters(parameters)
        assert parameters["sort_by"] == "brandname"

    def test_validate_parameters_invalid_sort_by(self, handler):
        """Test parameter validation fails when sort_by is invalid."""
        parameters = {"sort_by": "invalid_field"}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "sort_by" in str(exc_info.value).lower()
        assert "invalid_field" in str(exc_info.value)

    def test_validate_parameters_combined_valid(self, handler):
        """Test parameter validation with both limit and sort_by."""
        parameters = {"limit": 25, "sort_by": "confidence_score"}
        handler.validate_parameters(parameters)
        assert parameters["limit"] == 25
        assert parameters["sort_by"] == "confidence_score"

    # ========== Escalation Retrieval Tests ==========

    def test_execute_default_parameters(self, handler, sample_escalations):
        """Test execute with default parameters."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations,  # Main query
            [{"count": 3}]  # Count query
        ]
        
        parameters = {}
        result = handler.execute(parameters)
        
        assert result["returned_count"] == 3
        assert result["total_count"] == 3
        assert result["limit"] == 10
        assert result["sort_by"] == "escalated_at"
        assert len(result["escalations"]) == 3
        
        # Verify query was called
        assert handler.athena_client.execute_query.call_count == 2

    def test_execute_with_custom_limit(self, handler, sample_escalations):
        """Test execute with custom limit."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations[:2],  # Main query returns 2
            [{"count": 10}]  # Total count
        ]
        
        parameters = {"limit": 2}
        result = handler.execute(parameters)
        
        assert result["returned_count"] == 2
        assert result["total_count"] == 10
        assert result["limit"] == 2
        assert len(result["escalations"]) == 2
        
        # Verify LIMIT was added to query
        call_args = handler.athena_client.execute_query.call_args_list[0][0][0]
        assert "LIMIT 2" in call_args

    def test_execute_with_large_limit(self, handler, sample_escalations):
        """Test execute with large limit."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations,
            [{"count": 3}]
        ]
        
        parameters = {"limit": 50}
        result = handler.execute(parameters)
        
        assert result["limit"] == 50
        assert result["returned_count"] == 3
        
        # Verify LIMIT was added to query
        call_args = handler.athena_client.execute_query.call_args_list[0][0][0]
        assert "LIMIT 50" in call_args

    # ========== Sorting Tests ==========

    def test_execute_sort_by_escalated_at(self, handler, sample_escalations):
        """Test execute with sort_by escalated_at (default)."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations,
            [{"count": 3}]
        ]
        
        parameters = {"sort_by": "escalated_at"}
        result = handler.execute(parameters)
        
        assert result["sort_by"] == "escalated_at"
        
        # Verify ORDER BY escalated_at DESC was added
        call_args = handler.athena_client.execute_query.call_args_list[0][0][0]
        assert "ORDER BY escalated_at DESC" in call_args

    def test_execute_sort_by_confidence_score(self, handler, sample_escalations):
        """Test execute with sort_by confidence_score."""
        # Sort by confidence ascending (lowest first)
        sorted_escalations = sorted(sample_escalations, key=lambda x: x["confidence_score"])
        handler.athena_client.execute_query.side_effect = [
            sorted_escalations,
            [{"count": 3}]
        ]
        
        parameters = {"sort_by": "confidence_score"}
        result = handler.execute(parameters)
        
        assert result["sort_by"] == "confidence_score"
        
        # Verify ORDER BY confidence_score ASC was added
        call_args = handler.athena_client.execute_query.call_args_list[0][0][0]
        assert "ORDER BY confidence_score ASC" in call_args

    def test_execute_sort_by_brandid(self, handler, sample_escalations):
        """Test execute with sort_by brandid."""
        sorted_escalations = sorted(sample_escalations, key=lambda x: x["brandid"])
        handler.athena_client.execute_query.side_effect = [
            sorted_escalations,
            [{"count": 3}]
        ]
        
        parameters = {"sort_by": "brandid"}
        result = handler.execute(parameters)
        
        assert result["sort_by"] == "brandid"
        
        # Verify ORDER BY brandid ASC was added
        call_args = handler.athena_client.execute_query.call_args_list[0][0][0]
        assert "ORDER BY brandid ASC" in call_args

    def test_execute_sort_by_brandname(self, handler, sample_escalations):
        """Test execute with sort_by brandname."""
        sorted_escalations = sorted(sample_escalations, key=lambda x: x["brandname"])
        handler.athena_client.execute_query.side_effect = [
            sorted_escalations,
            [{"count": 3}]
        ]
        
        parameters = {"sort_by": "brandname"}
        result = handler.execute(parameters)
        
        assert result["sort_by"] == "brandname"
        
        # Verify ORDER BY brandname ASC was added
        call_args = handler.athena_client.execute_query.call_args_list[0][0][0]
        assert "ORDER BY brandname ASC" in call_args

    # ========== Pagination Tests ==========

    def test_execute_pagination_with_results(self, handler, sample_escalations):
        """Test pagination when results are returned."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations,
            [{"count": 3}]
        ]
        
        parameters = {"limit": 10}
        result = handler.execute(parameters)
        
        assert result["returned_count"] == 3
        assert result["total_count"] == 3
        assert len(result["escalations"]) == 3

    def test_execute_pagination_empty_results(self, handler):
        """Test pagination with empty results."""
        handler.athena_client.execute_query.side_effect = [
            [],  # No escalations
            [{"count": 0}]  # Zero count
        ]
        
        parameters = {"limit": 10}
        result = handler.execute(parameters)
        
        assert result["returned_count"] == 0
        assert result["total_count"] == 0
        assert result["escalations"] == []

    def test_execute_pagination_limit_smaller_than_total(self, handler, sample_escalations):
        """Test pagination when limit is smaller than total count."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations[:2],  # Return 2 results
            [{"count": 10}]  # But total is 10
        ]
        
        parameters = {"limit": 2}
        result = handler.execute(parameters)
        
        assert result["returned_count"] == 2
        assert result["total_count"] == 10
        assert len(result["escalations"]) == 2

    # ========== Query Building Tests ==========

    def test_build_query_filters_unresolved(self, handler):
        """Test that query filters for unresolved escalations."""
        query = handler._build_query("escalated_at", 10)
        
        # Should filter for pending or null status
        assert "status = 'pending'" in query
        assert "status IS NULL" in query
        assert "resolved_at IS NULL" in query
        assert "WHERE" in query

    def test_build_query_includes_all_fields(self, handler):
        """Test that query selects all required fields."""
        query = handler._build_query("escalated_at", 10)
        
        assert "escalation_id" in query
        assert "brandid" in query
        assert "brandname" in query
        assert "reason" in query
        assert "confidence_score" in query
        assert "escalated_at" in query
        assert "status" in query

    def test_build_query_from_escalations_table(self, handler):
        """Test that query selects from escalations table."""
        query = handler._build_query("escalated_at", 10)
        
        assert "FROM escalations" in query

    def test_build_query_with_different_limits(self, handler):
        """Test query building with different limit values."""
        query_10 = handler._build_query("escalated_at", 10)
        query_50 = handler._build_query("escalated_at", 50)
        query_100 = handler._build_query("escalated_at", 100)
        
        assert "LIMIT 10" in query_10
        assert "LIMIT 50" in query_50
        assert "LIMIT 100" in query_100

    # ========== Total Count Tests ==========

    def test_get_total_count_with_results(self, handler):
        """Test getting total count when escalations exist."""
        handler.athena_client.execute_query.return_value = [{"count": 15}]
        
        count = handler._get_total_count()
        
        assert count == 15
        
        # Verify count query was executed
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "COUNT(*)" in call_args
        assert "FROM escalations" in call_args
        assert "status = 'pending'" in call_args

    def test_get_total_count_zero(self, handler):
        """Test getting total count when no escalations exist."""
        handler.athena_client.execute_query.return_value = [{"count": 0}]
        
        count = handler._get_total_count()
        
        assert count == 0

    def test_get_total_count_empty_result(self, handler):
        """Test getting total count when query returns empty result."""
        handler.athena_client.execute_query.return_value = []
        
        count = handler._get_total_count()
        
        assert count == 0

    def test_get_total_count_handles_error(self, handler):
        """Test that total count returns 0 on error."""
        handler.athena_client.execute_query.side_effect = Exception("Query failed")
        
        count = handler._get_total_count()
        
        assert count == 0

    # ========== Escalation Formatting Tests ==========

    def test_format_escalations_all_fields(self, handler):
        """Test formatting escalations with all fields present."""
        raw_results = [
            {
                "escalation_id": "esc-123",
                "brandid": 456,
                "brandname": "Test Brand",
                "reason": "Low confidence",
                "confidence_score": 0.42,
                "escalated_at": "2024-01-01T10:00:00Z",
                "status": "pending"
            }
        ]
        
        formatted = handler._format_escalations(raw_results)
        
        assert len(formatted) == 1
        assert formatted[0]["escalation_id"] == "esc-123"
        assert formatted[0]["brandid"] == 456
        assert formatted[0]["brandname"] == "Test Brand"
        assert formatted[0]["reason"] == "Low confidence"
        assert formatted[0]["confidence_score"] == 0.42
        assert formatted[0]["escalated_at"] == "2024-01-01T10:00:00Z"
        assert formatted[0]["status"] == "pending"

    def test_format_escalations_missing_fields(self, handler):
        """Test formatting escalations with missing optional fields."""
        raw_results = [
            {
                "escalation_id": "esc-456",
                "brandid": 789
                # Missing other fields
            }
        ]
        
        formatted = handler._format_escalations(raw_results)
        
        assert len(formatted) == 1
        assert formatted[0]["escalation_id"] == "esc-456"
        assert formatted[0]["brandid"] == 789
        assert formatted[0]["brandname"] == "Unknown"  # Default
        assert formatted[0]["reason"] == ""  # Default
        assert formatted[0]["confidence_score"] == 0.0  # Default
        assert formatted[0]["escalated_at"] == ""  # Default
        assert formatted[0]["status"] == "pending"  # Default

    def test_format_escalations_multiple_records(self, handler, sample_escalations):
        """Test formatting multiple escalation records."""
        formatted = handler._format_escalations(sample_escalations)
        
        assert len(formatted) == 3
        assert formatted[0]["escalation_id"] == "esc-001"
        assert formatted[1]["escalation_id"] == "esc-002"
        assert formatted[2]["escalation_id"] == "esc-003"

    def test_format_escalations_empty_list(self, handler):
        """Test formatting empty escalation list."""
        formatted = handler._format_escalations([])
        
        assert formatted == []

    # ========== Error Handling Tests ==========

    def test_execute_handles_athena_error(self, handler):
        """Test that execute handles Athena query errors."""
        handler.athena_client.execute_query.side_effect = Exception("Athena query failed")
        
        parameters = {}
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "failed to query escalations" in str(exc_info.value).lower()
        assert "athena" in str(exc_info.value).lower()

    def test_execute_handles_table_not_found(self, handler):
        """Test handling when escalations table doesn't exist."""
        handler.athena_client.execute_query.side_effect = Exception("TABLE_NOT_FOUND: escalations")
        
        parameters = {}
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        # Should wrap as backend service error with escalations mentioned
        assert "escalations" in str(exc_info.value).lower()
        assert "athena" in str(exc_info.value).lower()

    def test_execute_handles_permission_error(self, handler):
        """Test handling permission errors."""
        handler.athena_client.execute_query.side_effect = Exception("AccessDeniedException")
        
        parameters = {}
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        # Should wrap as backend service error
        assert "failed to query escalations" in str(exc_info.value).lower()

    # ========== Lambda Handler Integration Tests ==========

    def test_lambda_handler_success(self, handler, sample_escalations):
        """Test lambda_handler with successful execution."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations,
            [{"count": 3}]
        ]
        
        event = {
            "parameters": {"limit": 10, "sort_by": "escalated_at"},
            "request_id": "test-request-123"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is True
        assert "data" in response
        assert response["data"]["returned_count"] == 3
        assert response["data"]["total_count"] == 3
        assert response["request_id"] == "test-request-123"

    def test_lambda_handler_empty_parameters(self, handler, sample_escalations):
        """Test lambda_handler with empty parameters."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations,
            [{"count": 3}]
        ]
        
        event = {
            "parameters": {},
            "request_id": "test-request-456"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is True
        assert response["data"]["limit"] == 10  # Default
        assert response["data"]["sort_by"] == "escalated_at"  # Default

    def test_lambda_handler_validation_error(self, handler):
        """Test lambda_handler with validation error."""
        event = {
            "parameters": {"limit": -5},
            "request_id": "test-request-789"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["type"] == "user_input"
        assert "positive" in response["error"]["message"].lower()

    def test_lambda_handler_backend_error(self, handler):
        """Test lambda_handler with backend service error."""
        handler.athena_client.execute_query.side_effect = Exception("Athena error")
        
        event = {
            "parameters": {},
            "request_id": "test-request-abc"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["type"] == "backend_service"

    # ========== Result Structure Tests ==========

    def test_execute_result_structure(self, handler, sample_escalations):
        """Test that execute returns correct result structure."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations,
            [{"count": 3}]
        ]
        
        result = handler.execute({})
        
        # Verify all required fields are present
        assert "escalations" in result
        assert "total_count" in result
        assert "returned_count" in result
        assert "limit" in result
        assert "sort_by" in result
        
        # Verify types
        assert isinstance(result["escalations"], list)
        assert isinstance(result["total_count"], int)
        assert isinstance(result["returned_count"], int)
        assert isinstance(result["limit"], int)
        assert isinstance(result["sort_by"], str)

    def test_get_required_params(self, handler):
        """Test that get_required_params returns empty list."""
        required = handler.get_required_params()
        assert required == []

    # ========== Edge Cases ==========

    def test_execute_with_null_status_escalations(self, handler):
        """Test that query includes escalations with null status."""
        query = handler._build_query("escalated_at", 10)
        
        # Should include OR status IS NULL
        assert "status IS NULL" in query

    def test_execute_with_null_resolved_at(self, handler):
        """Test that query includes escalations with null resolved_at."""
        query = handler._build_query("escalated_at", 10)
        
        # Should include OR resolved_at IS NULL
        assert "resolved_at IS NULL" in query

    def test_execute_combined_sorting_and_limit(self, handler, sample_escalations):
        """Test execute with both custom sorting and limit."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations[:2],
            [{"count": 10}]
        ]
        
        parameters = {"limit": 2, "sort_by": "confidence_score"}
        result = handler.execute(parameters)
        
        assert result["limit"] == 2
        assert result["sort_by"] == "confidence_score"
        assert result["returned_count"] == 2
        
        # Verify both were applied to query
        call_args = handler.athena_client.execute_query.call_args_list[0][0][0]
        assert "ORDER BY confidence_score ASC" in call_args
        assert "LIMIT 2" in call_args

    def test_execute_max_limit(self, handler, sample_escalations):
        """Test execute with maximum allowed limit."""
        handler.athena_client.execute_query.side_effect = [
            sample_escalations,
            [{"count": 3}]
        ]
        
        parameters = {"limit": 100}
        result = handler.execute(parameters)
        
        assert result["limit"] == 100
        
        # Verify LIMIT 100 was added
        call_args = handler.athena_client.execute_query.call_args_list[0][0][0]
        assert "LIMIT 100" in call_args
