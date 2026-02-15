"""Unit tests for query_brands_to_check Lambda handler.

Requirements: 7.1
"""

import pytest
from unittest.mock import MagicMock, patch

from lambda_functions.query_brands_to_check.handler import QueryBrandsToCheckHandler
from shared.utils.error_handler import UserInputError


class TestQueryBrandsToCheckHandler:
    """Test suite for QueryBrandsToCheckHandler."""

    @pytest.fixture
    def handler(self):
        """Create handler instance with mocked dependencies."""
        with patch('lambda_functions.query_brands_to_check.handler.AthenaClient'):
            handler = QueryBrandsToCheckHandler()
            handler.athena_client = MagicMock()
            return handler

    # ========== Parameter Validation Tests ==========

    def test_validate_parameters_valid_with_status_and_limit(self, handler):
        """Test parameter validation with valid status and limit."""
        parameters = {
            "status": "unprocessed",
            "limit": 50
        }
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_with_status_only(self, handler):
        """Test parameter validation with only status."""
        parameters = {
            "status": "processed"
        }
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_with_limit_only(self, handler):
        """Test parameter validation with only limit."""
        parameters = {
            "limit": 100
        }
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_empty(self, handler):
        """Test parameter validation with no parameters."""
        parameters = {}
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_invalid_limit_type(self, handler):
        """Test parameter validation fails when limit is not an integer."""
        parameters = {
            "limit": "not_an_int"
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "integer" in str(exc_info.value).lower()
        assert "limit" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_limit_zero(self, handler):
        """Test parameter validation fails when limit is zero."""
        parameters = {
            "limit": 0
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_limit_negative(self, handler):
        """Test parameter validation fails when limit is negative."""
        parameters = {
            "limit": -10
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "positive" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_limit_too_large(self, handler):
        """Test parameter validation fails when limit exceeds 1000."""
        parameters = {
            "limit": 1001
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "1000" in str(exc_info.value)
        assert "exceed" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_status_type(self, handler):
        """Test parameter validation fails when status is not a string."""
        parameters = {
            "status": 123
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "string" in str(exc_info.value).lower()
        assert "status" in str(exc_info.value).lower()

    # ========== Execute Tests with Status Filter ==========

    def test_execute_with_status_filter(self, handler):
        """Test execute with status filter."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 25
        handler.athena_client.query_table.return_value = [
            {
                "brandid": 101,
                "brandname": "Test Brand 1",
                "status": "unprocessed",
                "sector": "Retail"
            },
            {
                "brandid": 102,
                "brandname": "Test Brand 2",
                "status": "unprocessed",
                "sector": "Food & Beverage"
            }
        ]
        
        # Execute
        parameters = {
            "status": "unprocessed",
            "limit": 10
        }
        result = handler.execute(parameters)
        
        # Verify Athena calls
        handler.athena_client.get_table_count.assert_called_once_with(
            "brands_to_check",
            where="status = 'unprocessed'"
        )
        handler.athena_client.query_table.assert_called_once_with(
            table_name="brands_to_check",
            columns="brandid, brandname, status, sector",
            where="status = 'unprocessed'",
            limit=10
        )
        
        # Verify result
        assert result["total_count"] == 25
        assert len(result["brands"]) == 2
        assert result["brands"][0]["brandid"] == 101
        assert result["brands"][1]["brandname"] == "Test Brand 2"

    def test_execute_with_processed_status(self, handler):
        """Test execute with 'processed' status filter."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 150
        handler.athena_client.query_table.return_value = [
            {
                "brandid": 201,
                "brandname": "Processed Brand",
                "status": "processed",
                "sector": "Technology"
            }
        ]
        
        # Execute
        parameters = {
            "status": "processed"
        }
        result = handler.execute(parameters)
        
        # Verify WHERE clause includes status
        handler.athena_client.get_table_count.assert_called_once_with(
            "brands_to_check",
            where="status = 'processed'"
        )
        handler.athena_client.query_table.assert_called_once_with(
            table_name="brands_to_check",
            columns="brandid, brandname, status, sector",
            where="status = 'processed'",
            limit=10  # Default limit
        )

    # ========== Execute Tests with Limit Parameter ==========

    def test_execute_with_custom_limit(self, handler):
        """Test execute with custom limit parameter."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 500
        handler.athena_client.query_table.return_value = [
            {"brandid": i, "brandname": f"Brand {i}", "status": "unprocessed", "sector": "Retail"}
            for i in range(50)
        ]
        
        # Execute
        parameters = {
            "limit": 50
        }
        result = handler.execute(parameters)
        
        # Verify limit is passed correctly
        handler.athena_client.query_table.assert_called_once_with(
            table_name="brands_to_check",
            columns="brandid, brandname, status, sector",
            where=None,
            limit=50
        )
        
        assert result["total_count"] == 500
        assert len(result["brands"]) == 50

    def test_execute_with_default_limit(self, handler):
        """Test execute uses default limit of 10 when not specified."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 100
        handler.athena_client.query_table.return_value = []
        
        # Execute with no parameters
        parameters = {}
        result = handler.execute(parameters)
        
        # Verify default limit of 10 is used
        handler.athena_client.query_table.assert_called_once_with(
            table_name="brands_to_check",
            columns="brandid, brandname, status, sector",
            where=None,
            limit=10
        )

    def test_execute_with_limit_1(self, handler):
        """Test execute with limit of 1."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 1000
        handler.athena_client.query_table.return_value = [
            {
                "brandid": 999,
                "brandname": "Single Brand",
                "status": "unprocessed",
                "sector": "Finance"
            }
        ]
        
        # Execute
        parameters = {
            "limit": 1
        }
        result = handler.execute(parameters)
        
        # Verify
        handler.athena_client.query_table.assert_called_once_with(
            table_name="brands_to_check",
            columns="brandid, brandname, status, sector",
            where=None,
            limit=1
        )
        assert len(result["brands"]) == 1

    def test_execute_with_limit_1000(self, handler):
        """Test execute with maximum limit of 1000."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 5000
        handler.athena_client.query_table.return_value = []
        
        # Execute
        parameters = {
            "limit": 1000
        }
        result = handler.execute(parameters)
        
        # Verify maximum limit is accepted
        handler.athena_client.query_table.assert_called_once_with(
            table_name="brands_to_check",
            columns="brandid, brandname, status, sector",
            where=None,
            limit=1000
        )

    # ========== Execute Tests with Combined Parameters ==========

    def test_execute_with_status_and_limit(self, handler):
        """Test execute with both status and limit parameters."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 75
        handler.athena_client.query_table.return_value = [
            {
                "brandid": 301,
                "brandname": "Combined Test Brand",
                "status": "unprocessed",
                "sector": "Healthcare"
            }
        ]
        
        # Execute
        parameters = {
            "status": "unprocessed",
            "limit": 25
        }
        result = handler.execute(parameters)
        
        # Verify both parameters are used
        handler.athena_client.get_table_count.assert_called_once_with(
            "brands_to_check",
            where="status = 'unprocessed'"
        )
        handler.athena_client.query_table.assert_called_once_with(
            table_name="brands_to_check",
            columns="brandid, brandname, status, sector",
            where="status = 'unprocessed'",
            limit=25
        )

    # ========== Execute Tests for Edge Cases ==========

    def test_execute_with_no_results(self, handler):
        """Test execute when query returns no results."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 0
        handler.athena_client.query_table.return_value = []
        
        # Execute
        parameters = {
            "status": "nonexistent_status"
        }
        result = handler.execute(parameters)
        
        # Verify result structure
        assert result["total_count"] == 0
        assert result["brands"] == []
        assert isinstance(result["brands"], list)

    def test_execute_without_status_filter(self, handler):
        """Test execute without status filter returns all brands."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 200
        handler.athena_client.query_table.return_value = [
            {
                "brandid": 401,
                "brandname": "Any Status Brand 1",
                "status": "processed",
                "sector": "Retail"
            },
            {
                "brandid": 402,
                "brandname": "Any Status Brand 2",
                "status": "unprocessed",
                "sector": "Technology"
            }
        ]
        
        # Execute
        parameters = {}
        result = handler.execute(parameters)
        
        # Verify no WHERE clause is used
        handler.athena_client.get_table_count.assert_called_once_with(
            "brands_to_check",
            where=None
        )
        handler.athena_client.query_table.assert_called_once_with(
            table_name="brands_to_check",
            columns="brandid, brandname, status, sector",
            where=None,
            limit=10
        )

    def test_execute_result_structure(self, handler):
        """Test that execute returns correct result structure."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 3
        handler.athena_client.query_table.return_value = [
            {
                "brandid": 501,
                "brandname": "Structure Test Brand",
                "status": "unprocessed",
                "sector": "Entertainment"
            }
        ]
        
        # Execute
        result = handler.execute({})
        
        # Verify result structure
        assert "brands" in result
        assert "total_count" in result
        assert isinstance(result["brands"], list)
        assert isinstance(result["total_count"], int)
        
        # Verify brand structure
        if result["brands"]:
            brand = result["brands"][0]
            assert "brandid" in brand
            assert "brandname" in brand
            assert "status" in brand
            assert "sector" in brand

    # ========== Error Handling Tests ==========

    def test_execute_handles_athena_count_error(self, handler):
        """Test execute handles errors from get_table_count."""
        # Mock Athena error
        handler.athena_client.get_table_count.side_effect = Exception("Athena query failed")
        
        # Execute should raise the exception
        parameters = {"status": "unprocessed"}
        with pytest.raises(Exception) as exc_info:
            handler.execute(parameters)
        
        assert "Athena query failed" in str(exc_info.value)

    def test_execute_handles_athena_query_error(self, handler):
        """Test execute handles errors from query_table."""
        # Mock successful count but failed query
        handler.athena_client.get_table_count.return_value = 10
        handler.athena_client.query_table.side_effect = Exception("Query execution failed")
        
        # Execute should raise the exception
        parameters = {"limit": 5}
        with pytest.raises(Exception) as exc_info:
            handler.execute(parameters)
        
        assert "Query execution failed" in str(exc_info.value)

    # ========== Lambda Handler Integration Tests ==========

    def test_lambda_handler_success(self, handler):
        """Test lambda_handler with successful execution."""
        # Mock Athena responses
        handler.athena_client.get_table_count.return_value = 5
        handler.athena_client.query_table.return_value = [
            {
                "brandid": 601,
                "brandname": "Lambda Test Brand",
                "status": "unprocessed",
                "sector": "Retail"
            }
        ]
        
        # Create event
        event = {
            "parameters": {
                "status": "unprocessed",
                "limit": 10
            },
            "request_id": "test-request-123"
        }
        
        # Call handler
        response = handler.handle(event, None)
        
        # Verify response structure
        assert response["success"] is True
        assert "data" in response
        assert response["data"]["total_count"] == 5
        assert len(response["data"]["brands"]) == 1
        assert response["request_id"] == "test-request-123"

    def test_lambda_handler_validation_error(self, handler):
        """Test lambda_handler with validation error."""
        # Create event with invalid parameters
        event = {
            "parameters": {
                "limit": -5
            },
            "request_id": "test-request-456"
        }
        
        # Call handler
        response = handler.handle(event, None)
        
        # Verify error response
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["type"] == "user_input"
        assert "positive" in response["error"]["message"].lower()
        assert response["request_id"] == "test-request-456"
