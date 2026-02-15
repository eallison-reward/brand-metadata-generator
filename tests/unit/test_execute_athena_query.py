"""Unit tests for execute_athena_query Lambda handler.

Requirements: 7.5
"""

import os
import pytest
from unittest.mock import MagicMock, patch

# Set environment variables before importing handler
os.environ['S3_BUCKET'] = 'test-bucket'
os.environ['AWS_REGION'] = 'eu-west-1'
os.environ['ATHENA_DATABASE'] = 'test_db'

from lambda_functions.execute_athena_query.handler import (
    ExecuteAthenaQueryHandler,
    QUERY_TEMPLATES
)
from shared.utils.error_handler import UserInputError, BackendServiceError


class TestExecuteAthenaQueryHandler:
    """Test suite for ExecuteAthenaQueryHandler."""

    @pytest.fixture
    def handler(self):
        """Create handler instance with mocked dependencies."""
        with patch.dict('os.environ', {
            'S3_BUCKET': 'test-bucket',
            'AWS_REGION': 'eu-west-1',
            'ATHENA_DATABASE': 'test_db'
        }):
            with patch('lambda_functions.execute_athena_query.handler.AthenaClient'):
                handler = ExecuteAthenaQueryHandler()
                handler.athena_client = MagicMock()
                return handler

    # ========== Parameter Validation Tests ==========

    def test_validate_parameters_valid_predefined_query(self, handler):
        """Test parameter validation with valid predefined query type."""
        parameters = {
            "query_type": "brands_by_confidence",
            "parameters": {"min_confidence": 0.8, "max_confidence": 1.0}
        }
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_custom_query(self, handler):
        """Test parameter validation with valid custom query."""
        parameters = {
            "query_type": "custom",
            "parameters": {"sql": "SELECT * FROM brands_to_check LIMIT 10"}
        }
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_missing_query_type(self, handler):
        """Test parameter validation fails when query_type is missing."""
        parameters = {}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "query_type" in str(exc_info.value).lower()
        assert "required" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_query_type(self, handler):
        """Test parameter validation fails when query_type is invalid."""
        parameters = {"query_type": "invalid_query_type"}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "invalid query_type" in str(exc_info.value).lower()

    def test_validate_parameters_custom_query_missing_sql(self, handler):
        """Test parameter validation fails when custom query lacks sql parameter."""
        parameters = {
            "query_type": "custom",
            "parameters": {}
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "sql" in str(exc_info.value).lower()
        assert "custom query" in str(exc_info.value).lower()

    def test_validate_parameters_valid_limit(self, handler):
        """Test parameter validation with valid limit."""
        parameters = {
            "query_type": "escalations_pending",
            "limit": 50
        }
        handler.validate_parameters(parameters)
        assert parameters["limit"] == 50

    def test_validate_parameters_converts_string_limit(self, handler):
        """Test parameter validation converts string limit to integer."""
        parameters = {
            "query_type": "escalations_pending",
            "limit": "25"
        }
        handler.validate_parameters(parameters)
        assert parameters["limit"] == 25
        assert isinstance(parameters["limit"], int)

    def test_validate_parameters_invalid_limit_zero(self, handler):
        """Test parameter validation fails when limit is zero."""
        parameters = {
            "query_type": "escalations_pending",
            "limit": 0
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_limit_negative(self, handler):
        """Test parameter validation fails when limit is negative."""
        parameters = {
            "query_type": "escalations_pending",
            "limit": -10
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_limit_too_large(self, handler):
        """Test parameter validation fails when limit exceeds maximum."""
        parameters = {
            "query_type": "escalations_pending",
            "limit": 1500
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "1000" in str(exc_info.value)

    def test_validate_parameters_invalid_limit_type(self, handler):
        """Test parameter validation fails when limit is invalid type."""
        parameters = {
            "query_type": "escalations_pending",
            "limit": "not_a_number"
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "integer" in str(exc_info.value).lower()

    def test_validate_parameters_valid_page_size(self, handler):
        """Test parameter validation with valid page_size."""
        parameters = {
            "query_type": "escalations_pending",
            "page_size": 20
        }
        handler.validate_parameters(parameters)
        assert parameters["page_size"] == 20

    def test_validate_parameters_invalid_page_size_zero(self, handler):
        """Test parameter validation fails when page_size is zero."""
        parameters = {
            "query_type": "escalations_pending",
            "page_size": 0
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_page_size_too_large(self, handler):
        """Test parameter validation fails when page_size exceeds maximum."""
        parameters = {
            "query_type": "escalations_pending",
            "page_size": 150
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "100" in str(exc_info.value)

    # ========== Predefined Query Tests ==========

    def test_execute_brands_by_confidence_query(self, handler):
        """Test executing brands_by_confidence predefined query."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": 123, "brandname": "Brand A", "confidence_score": 0.95, "generated_at": "2024-01-01"},
            {"brandid": 456, "brandname": "Brand B", "confidence_score": 0.85, "generated_at": "2024-01-02"}
        ]
        
        parameters = {
            "query_type": "brands_by_confidence",
            "parameters": {"min_confidence": 0.8, "max_confidence": 1.0}
        }
        
        result = handler.execute(parameters)
        
        assert result["query_type"] == "brands_by_confidence"
        assert result["row_count"] == 2
        assert result["total_count"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["brandid"] == 123
        assert result["results"][1]["brandid"] == 456
        
        # Verify query was built correctly
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "confidence_score >=" in call_args
        assert "0.8" in call_args
        assert "1.0" in call_args

    def test_execute_brands_by_category_query(self, handler):
        """Test executing brands_by_category predefined query."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": 789, "brandname": "Retail Brand", "sector": "Retail", "confidence_score": 0.9}
        ]
        
        parameters = {
            "query_type": "brands_by_category",
            "parameters": {"sector": "Retail"}
        }
        
        result = handler.execute(parameters)
        
        assert result["query_type"] == "brands_by_category"
        assert result["row_count"] == 1
        assert result["results"][0]["sector"] == "Retail"
        
        # Verify query was built correctly
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "sector = 'Retail'" in call_args

    def test_execute_recent_workflows_query(self, handler):
        """Test executing recent_workflows predefined query."""
        handler.athena_client.execute_query.return_value = [
            {"execution_arn": "arn:123", "brandid": 111, "status": "SUCCEEDED", "start_time": "2024-01-01", "duration_seconds": 300}
        ]
        
        parameters = {
            "query_type": "recent_workflows",
            "parameters": {"days": 7}
        }
        
        result = handler.execute(parameters)
        
        assert result["query_type"] == "recent_workflows"
        assert result["row_count"] == 1
        
        # Verify query was built correctly
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "date_add('day', -7" in call_args

    def test_execute_escalations_pending_query(self, handler):
        """Test executing escalations_pending predefined query."""
        handler.athena_client.execute_query.return_value = [
            {"escalation_id": "esc-1", "brandid": 222, "brandname": "Test", "reason": "Low confidence", "confidence_score": 0.5, "escalated_at": "2024-01-01"}
        ]
        
        parameters = {
            "query_type": "escalations_pending"
        }
        
        result = handler.execute(parameters)
        
        assert result["query_type"] == "escalations_pending"
        assert result["row_count"] == 1
        assert result["results"][0]["escalation_id"] == "esc-1"
        
        # Verify query was built correctly
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "status = 'pending'" in call_args

    def test_execute_low_confidence_brands_query(self, handler):
        """Test executing low_confidence_brands predefined query."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": 333, "brandname": "Low Conf Brand", "confidence_score": 0.6, "generated_at": "2024-01-01"}
        ]
        
        parameters = {
            "query_type": "low_confidence_brands",
            "parameters": {"threshold": 0.7}
        }
        
        result = handler.execute(parameters)
        
        assert result["query_type"] == "low_confidence_brands"
        assert result["row_count"] == 1
        
        # Verify query was built correctly
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "confidence_score < 0.7" in call_args

    def test_execute_brands_by_status_query(self, handler):
        """Test executing brands_by_status predefined query."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": 444, "brandname": "Pending Brand", "status": "pending", "sector": "Food"}
        ]
        
        parameters = {
            "query_type": "brands_by_status",
            "parameters": {"status": "pending"}
        }
        
        result = handler.execute(parameters)
        
        assert result["query_type"] == "brands_by_status"
        assert result["row_count"] == 1
        
        # Verify query was built correctly
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "status = 'pending'" in call_args

    # ========== Custom SQL Tests ==========

    def test_execute_custom_sql_query(self, handler):
        """Test executing custom SQL query."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": 555, "custom_field": "value"}
        ]
        
        parameters = {
            "query_type": "custom",
            "parameters": {"sql": "SELECT brandid, custom_field FROM custom_table WHERE brandid = 555"}
        }
        
        result = handler.execute(parameters)
        
        assert result["query_type"] == "custom"
        assert result["row_count"] == 1
        assert result["results"][0]["brandid"] == 555
        
        # Verify custom SQL was used
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "custom_table" in call_args
        assert "custom_field" in call_args

    # ========== Pagination Tests ==========

    def test_execute_with_pagination_limit(self, handler):
        """Test query execution with limit parameter."""
        # Return 5 results
        handler.athena_client.execute_query.return_value = [
            {"brandid": i, "brandname": f"Brand {i}"} for i in range(1, 6)
        ]
        
        parameters = {
            "query_type": "escalations_pending",
            "limit": 5,
            "page_size": 5
        }
        
        result = handler.execute(parameters)
        
        assert result["row_count"] == 5
        assert result["total_count"] == 5
        assert result["has_more"] is True  # Because total_count >= limit
        
        # Verify LIMIT was added to query
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "LIMIT 5" in call_args

    def test_execute_with_pagination_offset(self, handler):
        """Test query execution with offset parameter."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": i, "brandname": f"Brand {i}"} for i in range(11, 16)
        ]
        
        parameters = {
            "query_type": "escalations_pending",
            "limit": 10,
            "offset": 10
        }
        
        result = handler.execute(parameters)
        
        assert result["pagination"]["offset"] == 10
        
        # Verify OFFSET was added to query
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "OFFSET 10" in call_args

    def test_execute_with_page_size_smaller_than_results(self, handler):
        """Test that page_size limits returned results."""
        # Return 10 results
        handler.athena_client.execute_query.return_value = [
            {"brandid": i, "brandname": f"Brand {i}"} for i in range(1, 11)
        ]
        
        parameters = {
            "query_type": "escalations_pending",
            "limit": 10,
            "page_size": 5
        }
        
        result = handler.execute(parameters)
        
        assert result["total_count"] == 10  # Total from Athena
        assert result["row_count"] == 5  # Limited by page_size
        assert len(result["results"]) == 5
        assert result["has_more"] is True
        assert result["next_offset"] == 5

    def test_execute_pagination_has_more_false(self, handler):
        """Test that has_more is False when results are less than limit."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": 1, "brandname": "Brand 1"}
        ]
        
        parameters = {
            "query_type": "escalations_pending",
            "limit": 10
        }
        
        result = handler.execute(parameters)
        
        assert result["total_count"] == 1
        assert result["has_more"] is False
        assert result["next_offset"] is None

    def test_execute_pagination_next_offset_calculation(self, handler):
        """Test that next_offset is calculated correctly."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": i, "brandname": f"Brand {i}"} for i in range(1, 11)
        ]
        
        parameters = {
            "query_type": "escalations_pending",
            "limit": 10,
            "offset": 20,
            "page_size": 10
        }
        
        result = handler.execute(parameters)
        
        assert result["has_more"] is True
        assert result["next_offset"] == 30  # offset + page_size

    # ========== Empty Result Handling Tests ==========

    def test_execute_with_empty_results(self, handler):
        """Test handling of empty query results."""
        handler.athena_client.execute_query.return_value = []
        
        parameters = {
            "query_type": "escalations_pending"
        }
        
        result = handler.execute(parameters)
        
        assert result["results"] == []
        assert result["row_count"] == 0
        assert result["total_count"] == 0
        assert result["has_more"] is False
        assert result["next_offset"] is None

    def test_execute_empty_results_with_pagination(self, handler):
        """Test empty results with pagination parameters."""
        handler.athena_client.execute_query.return_value = []
        
        parameters = {
            "query_type": "low_confidence_brands",
            "parameters": {"threshold": 0.5},
            "limit": 20,
            "page_size": 10,
            "offset": 0
        }
        
        result = handler.execute(parameters)
        
        assert result["results"] == []
        assert result["row_count"] == 0
        assert result["has_more"] is False

    # ========== Query Template Parameter Tests ==========

    def test_build_query_missing_required_parameters(self, handler):
        """Test that missing required parameters raises error."""
        parameters = {
            "query_type": "brands_by_category",
            "parameters": {}  # Missing sector (required, no default)
        }
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "missing required parameters" in str(exc_info.value).lower()
        assert "sector" in str(exc_info.value).lower()

    def test_build_query_with_defaults(self, handler):
        """Test that default values are applied for optional parameters."""
        handler.athena_client.execute_query.return_value = []
        
        parameters = {
            "query_type": "brands_by_confidence",
            "parameters": {
                "min_confidence": 0.5,
                "max_confidence": 0.9
            }
        }
        
        result = handler.execute(parameters)
        
        # Verify parameters were used
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "0.5" in call_args
        assert "0.9" in call_args

    def test_build_query_recent_workflows_default_days(self, handler):
        """Test that recent_workflows uses default days value."""
        handler.athena_client.execute_query.return_value = []
        
        parameters = {
            "query_type": "recent_workflows",
            "parameters": {"days": 14}  # Explicit value
        }
        
        result = handler.execute(parameters)
        
        # Verify value was used
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "-14" in call_args

    def test_build_query_low_confidence_default_threshold(self, handler):
        """Test that low_confidence_brands uses default threshold."""
        handler.athena_client.execute_query.return_value = []
        
        parameters = {
            "query_type": "low_confidence_brands",
            "parameters": {"threshold": 0.6}  # Explicit value
        }
        
        result = handler.execute(parameters)
        
        # Verify value was used
        call_args = handler.athena_client.execute_query.call_args[0][0]
        assert "0.6" in call_args

    # ========== Error Handling Tests ==========

    def test_execute_handles_athena_syntax_error(self, handler):
        """Test handling of Athena SQL syntax errors."""
        handler.athena_client.execute_query.side_effect = Exception("SYNTAX_ERROR: Invalid SQL syntax")
        
        parameters = {
            "query_type": "custom",
            "parameters": {"sql": "INVALID SQL"}
        }
        
        with pytest.raises(UserInputError) as exc_info:
            handler.execute(parameters)
        
        assert "syntax error" in str(exc_info.value).lower()

    def test_execute_handles_table_not_found_error(self, handler):
        """Test handling of table not found errors."""
        handler.athena_client.execute_query.side_effect = Exception("TABLE_NOT_FOUND: Table does not exist")
        
        parameters = {
            "query_type": "escalations_pending"
        }
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "table not found" in str(exc_info.value).lower()

    def test_execute_handles_column_not_found_error(self, handler):
        """Test handling of column not found errors."""
        handler.athena_client.execute_query.side_effect = Exception("COLUMN_NOT_FOUND: Column 'invalid_col'")
        
        parameters = {
            "query_type": "custom",
            "parameters": {"sql": "SELECT invalid_col FROM brands"}
        }
        
        with pytest.raises(UserInputError) as exc_info:
            handler.execute(parameters)
        
        assert "column not found" in str(exc_info.value).lower()

    def test_execute_handles_generic_athena_error(self, handler):
        """Test handling of generic Athena errors."""
        handler.athena_client.execute_query.side_effect = Exception("Unknown Athena error")
        
        parameters = {
            "query_type": "escalations_pending"
        }
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "query execution failed" in str(exc_info.value).lower()

    # ========== Result Structure Tests ==========

    def test_execute_result_structure(self, handler):
        """Test that execute returns correct result structure."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": 123, "brandname": "Test"}
        ]
        
        parameters = {
            "query_type": "escalations_pending"
        }
        
        result = handler.execute(parameters)
        
        # Verify all required fields are present
        assert "results" in result
        assert "row_count" in result
        assert "total_count" in result
        assert "execution_time_ms" in result
        assert "query_type" in result
        assert "has_more" in result
        assert "next_offset" in result
        assert "pagination" in result
        
        # Verify types
        assert isinstance(result["results"], list)
        assert isinstance(result["row_count"], int)
        assert isinstance(result["total_count"], int)
        assert isinstance(result["execution_time_ms"], int)
        assert isinstance(result["query_type"], str)
        assert isinstance(result["has_more"], bool)
        assert isinstance(result["pagination"], dict)

    def test_execute_includes_execution_time(self, handler):
        """Test that execution time is measured and included."""
        handler.athena_client.execute_query.return_value = []
        
        parameters = {
            "query_type": "escalations_pending"
        }
        
        result = handler.execute(parameters)
        
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] >= 0
        assert isinstance(result["execution_time_ms"], int)

    def test_execute_pagination_metadata(self, handler):
        """Test that pagination metadata is included correctly."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": i} for i in range(1, 6)
        ]
        
        parameters = {
            "query_type": "escalations_pending",
            "limit": 10,
            "page_size": 5,
            "offset": 20
        }
        
        result = handler.execute(parameters)
        
        assert result["pagination"]["page_size"] == 5
        assert result["pagination"]["offset"] == 20
        assert result["pagination"]["limit"] == 10

    # ========== Query Building Tests ==========

    def test_add_pagination_removes_existing_limit(self, handler):
        """Test that existing LIMIT clause is removed before adding new one."""
        query = "SELECT * FROM table LIMIT 100"
        result = handler._add_pagination(query, 50, 0)
        
        # Should have only one LIMIT clause with new value
        assert result.count("LIMIT") == 1
        assert "LIMIT 50" in result
        assert "LIMIT 100" not in result

    def test_add_pagination_with_offset_zero(self, handler):
        """Test that OFFSET is not added when offset is zero."""
        query = "SELECT * FROM table"
        result = handler._add_pagination(query, 10, 0)
        
        assert "LIMIT 10" in result
        assert "OFFSET" not in result

    def test_add_pagination_with_nonzero_offset(self, handler):
        """Test that OFFSET is added when offset is greater than zero."""
        query = "SELECT * FROM table"
        result = handler._add_pagination(query, 10, 5)
        
        assert "LIMIT 10" in result
        assert "OFFSET 5" in result

    def test_get_required_params_for_query_type(self, handler):
        """Test getting required parameters for each query type."""
        assert handler._get_required_params_for_query_type("brands_by_confidence") == ["min_confidence", "max_confidence"]
        assert handler._get_required_params_for_query_type("brands_by_category") == ["sector"]
        assert handler._get_required_params_for_query_type("recent_workflows") == ["days"]
        assert handler._get_required_params_for_query_type("escalations_pending") == []
        assert handler._get_required_params_for_query_type("low_confidence_brands") == ["threshold"]
        assert handler._get_required_params_for_query_type("brands_by_status") == ["status"]

    # ========== Lambda Handler Integration Tests ==========

    def test_lambda_handler_success(self, handler):
        """Test lambda_handler with successful execution."""
        handler.athena_client.execute_query.return_value = [
            {"brandid": 123, "brandname": "Test"}
        ]
        
        event = {
            "parameters": {
                "query_type": "escalations_pending"
            },
            "request_id": "test-request-123"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is True
        assert "data" in response
        assert response["data"]["query_type"] == "escalations_pending"
        assert response["request_id"] == "test-request-123"

    def test_lambda_handler_validation_error(self, handler):
        """Test lambda_handler with validation error."""
        event = {
            "parameters": {
                "query_type": "invalid_type"
            },
            "request_id": "test-request-456"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["type"] == "user_input"
        assert response["request_id"] == "test-request-456"

    def test_lambda_handler_backend_error(self, handler):
        """Test lambda_handler with backend service error."""
        handler.athena_client.execute_query.side_effect = Exception("Athena service error")
        
        event = {
            "parameters": {
                "query_type": "escalations_pending"
            },
            "request_id": "test-request-789"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["type"] == "backend_service"
        assert response["request_id"] == "test-request-789"

    # ========== Edge Cases ==========

    def test_get_required_params(self, handler):
        """Test that get_required_params returns correct list."""
        required = handler.get_required_params()
        assert required == ["query_type"]

    def test_query_templates_exist(self):
        """Test that all expected query templates are defined."""
        expected_templates = [
            "brands_by_confidence",
            "brands_by_category",
            "recent_workflows",
            "escalations_pending",
            "low_confidence_brands",
            "brands_by_status"
        ]
        
        for template in expected_templates:
            assert template in QUERY_TEMPLATES
            assert isinstance(QUERY_TEMPLATES[template], str)
            assert len(QUERY_TEMPLATES[template]) > 0
