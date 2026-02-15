"""Unit tests for get_workflow_stats Lambda handler.

Requirements: 7.8
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Set environment variables before importing handler
os.environ['ATHENA_DATABASE'] = 'test_db'
os.environ['AWS_REGION'] = 'eu-west-1'
os.environ['ATHENA_OUTPUT_LOCATION'] = 's3://test-bucket/query-results/'

from lambda_functions.get_workflow_stats.handler import GetWorkflowStatsHandler
from shared.utils.error_handler import UserInputError, BackendServiceError


class TestGetWorkflowStatsHandler:
    """Test suite for GetWorkflowStatsHandler."""

    @pytest.fixture
    def handler(self):
        """Create handler instance with mocked dependencies."""
        with patch.dict('os.environ', {
            'ATHENA_DATABASE': 'test_db',
            'AWS_REGION': 'eu-west-1',
            'ATHENA_OUTPUT_LOCATION': 's3://test-bucket/query-results/'
        }):
            with patch('lambda_functions.get_workflow_stats.handler.AthenaClient'):
                handler = GetWorkflowStatsHandler()
                handler.athena_client = MagicMock()
                return handler

    # ========== Parameter Validation Tests ==========

    def test_validate_parameters_valid_last_hour(self, handler):
        """Test parameter validation with valid last_hour time period."""
        parameters = {"time_period": "last_hour"}
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_last_day(self, handler):
        """Test parameter validation with valid last_day time period."""
        parameters = {"time_period": "last_day"}
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_last_week(self, handler):
        """Test parameter validation with valid last_week time period."""
        parameters = {"time_period": "last_week"}
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_valid_with_include_details(self, handler):
        """Test parameter validation with include_details parameter."""
        parameters = {
            "time_period": "last_day",
            "include_details": True
        }
        # Should not raise any exception
        handler.validate_parameters(parameters)

    def test_validate_parameters_missing_time_period(self, handler):
        """Test parameter validation fails when time_period is missing."""
        parameters = {}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "time_period" in str(exc_info.value).lower()
        assert "required" in str(exc_info.value).lower()

    def test_validate_parameters_invalid_time_period(self, handler):
        """Test parameter validation fails when time_period is invalid."""
        parameters = {"time_period": "last_month"}
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "time_period must be one of" in str(exc_info.value)
        assert "last_month" in str(exc_info.value)

    def test_validate_parameters_invalid_include_details_type(self, handler):
        """Test parameter validation fails when include_details is not boolean."""
        parameters = {
            "time_period": "last_day",
            "include_details": "yes"
        }
        with pytest.raises(UserInputError) as exc_info:
            handler.validate_parameters(parameters)
        assert "include_details" in str(exc_info.value).lower()
        assert "boolean" in str(exc_info.value).lower()

    # ========== Time Threshold Calculation Tests ==========

    def test_calculate_time_threshold_last_hour(self, handler):
        """Test time threshold calculation for last_hour."""
        threshold = handler._calculate_time_threshold("last_hour")
        
        # Parse the ISO timestamp
        threshold_dt = datetime.fromisoformat(threshold)
        now = datetime.utcnow()
        expected = now - timedelta(hours=1)
        
        # Allow 1 second tolerance for test execution time
        assert abs((threshold_dt - expected).total_seconds()) < 1

    def test_calculate_time_threshold_last_day(self, handler):
        """Test time threshold calculation for last_day."""
        threshold = handler._calculate_time_threshold("last_day")
        
        threshold_dt = datetime.fromisoformat(threshold)
        now = datetime.utcnow()
        expected = now - timedelta(days=1)
        
        assert abs((threshold_dt - expected).total_seconds()) < 1

    def test_calculate_time_threshold_last_week(self, handler):
        """Test time threshold calculation for last_week."""
        threshold = handler._calculate_time_threshold("last_week")
        
        threshold_dt = datetime.fromisoformat(threshold)
        now = datetime.utcnow()
        expected = now - timedelta(weeks=1)
        
        assert abs((threshold_dt - expected).total_seconds()) < 1

    def test_calculate_time_threshold_returns_iso_format(self, handler):
        """Test that time threshold is returned in ISO 8601 format."""
        threshold = handler._calculate_time_threshold("last_day")
        
        # Should be parseable as ISO format
        datetime.fromisoformat(threshold)
        assert "T" in threshold  # ISO format includes T separator

    # ========== Statistics Query Building Tests ==========

    def test_build_stats_query_structure(self, handler):
        """Test that stats query has correct structure."""
        threshold = "2024-01-01T12:00:00"
        query = handler._build_stats_query(threshold)
        
        # Verify query contains expected elements
        assert "SELECT" in query
        assert "COUNT(*) as total_executions" in query
        assert "SUM(CASE WHEN status = 'SUCCEEDED' THEN 1 ELSE 0 END) as successful" in query
        assert "SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed" in query
        assert "SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END) as running" in query
        assert "AVG(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds ELSE 0 END) as avg_duration" in query
        assert "COUNT(DISTINCT brandid) as brands_processed" in query
        assert "FROM workflow_executions" in query
        assert f"WHERE start_time >= TIMESTAMP '{threshold}'" in query

    def test_build_details_query_structure(self, handler):
        """Test that details query has correct structure."""
        threshold = "2024-01-01T12:00:00"
        query = handler._build_details_query(threshold)
        
        # Verify query contains expected elements
        assert "SELECT" in query
        assert "execution_arn" in query
        assert "brandid" in query
        assert "status" in query
        assert "start_time" in query
        assert "stop_time" in query
        assert "duration_seconds" in query
        assert "error_message" in query
        assert "FROM workflow_executions" in query
        assert f"WHERE start_time >= TIMESTAMP '{threshold}'" in query
        assert "ORDER BY start_time DESC" in query
        assert "LIMIT 50" in query

    # ========== Statistics Parsing Tests ==========

    def test_parse_statistics_with_data(self, handler):
        """Test parsing statistics from query results with data."""
        results = [{
            "total_executions": 100,
            "successful": 85,
            "failed": 10,
            "running": 5,
            "avg_duration": 300.5,
            "brands_processed": 95
        }]
        
        stats = handler._parse_statistics(results, "last_day")
        
        assert stats["time_period"] == "last_day"
        assert stats["total_executions"] == 100
        assert stats["successful"] == 85
        assert stats["failed"] == 10
        assert stats["running"] == 5
        assert stats["success_rate"] == 89.47  # 85/(85+10)*100 = 89.47
        assert stats["average_duration_seconds"] == 300.5
        assert stats["brands_processed"] == 95

    def test_parse_statistics_empty_results(self, handler):
        """Test parsing statistics with empty results."""
        results = []
        
        stats = handler._parse_statistics(results, "last_hour")
        
        assert stats["time_period"] == "last_hour"
        assert stats["total_executions"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["running"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["average_duration_seconds"] == 0.0
        assert stats["brands_processed"] == 0

    def test_parse_statistics_all_running(self, handler):
        """Test parsing statistics when all executions are running."""
        results = [{
            "total_executions": 10,
            "successful": 0,
            "failed": 0,
            "running": 10,
            "avg_duration": 0.0,
            "brands_processed": 10
        }]
        
        stats = handler._parse_statistics(results, "last_hour")
        
        assert stats["total_executions"] == 10
        assert stats["running"] == 10
        assert stats["success_rate"] == 0.0  # No completed executions
        assert stats["successful"] == 0
        assert stats["failed"] == 0

    def test_parse_statistics_all_succeeded(self, handler):
        """Test parsing statistics when all executions succeeded."""
        results = [{
            "total_executions": 50,
            "successful": 50,
            "failed": 0,
            "running": 0,
            "avg_duration": 250.0,
            "brands_processed": 50
        }]
        
        stats = handler._parse_statistics(results, "last_week")
        
        assert stats["total_executions"] == 50
        assert stats["successful"] == 50
        assert stats["failed"] == 0
        assert stats["success_rate"] == 100.0
        assert stats["average_duration_seconds"] == 250.0

    def test_parse_statistics_all_failed(self, handler):
        """Test parsing statistics when all executions failed."""
        results = [{
            "total_executions": 20,
            "successful": 0,
            "failed": 20,
            "running": 0,
            "avg_duration": 150.0,
            "brands_processed": 20
        }]
        
        stats = handler._parse_statistics(results, "last_day")
        
        assert stats["total_executions"] == 20
        assert stats["successful"] == 0
        assert stats["failed"] == 20
        assert stats["success_rate"] == 0.0
        assert stats["average_duration_seconds"] == 150.0

    def test_parse_statistics_success_rate_calculation(self, handler):
        """Test success rate calculation with various scenarios."""
        # 50% success rate
        results = [{
            "total_executions": 100,
            "successful": 40,
            "failed": 40,
            "running": 20,
            "avg_duration": 200.0,
            "brands_processed": 80
        }]
        
        stats = handler._parse_statistics(results, "last_day")
        
        # Success rate = 40/(40+40)*100 = 50.0
        assert stats["success_rate"] == 50.0

    def test_parse_statistics_rounds_values(self, handler):
        """Test that statistics are rounded to 2 decimal places."""
        results = [{
            "total_executions": 100,
            "successful": 67,
            "failed": 33,
            "running": 0,
            "avg_duration": 123.456789,
            "brands_processed": 100
        }]
        
        stats = handler._parse_statistics(results, "last_day")
        
        # Success rate = 67/(67+33)*100 = 67.0
        assert stats["success_rate"] == 67.0
        # Average duration should be rounded to 2 decimals
        assert stats["average_duration_seconds"] == 123.46

    # ========== Execution Details Formatting Tests ==========

    def test_format_execution_details_with_data(self, handler):
        """Test formatting execution details with complete data."""
        results = [
            {
                "execution_arn": "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec1",
                "brandid": 123,
                "status": "SUCCEEDED",
                "start_time": "2024-01-01T12:00:00",
                "stop_time": "2024-01-01T12:05:00",
                "duration_seconds": 300,
                "error_message": None
            },
            {
                "execution_arn": "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec2",
                "brandid": 456,
                "status": "FAILED",
                "start_time": "2024-01-01T11:00:00",
                "stop_time": "2024-01-01T11:02:00",
                "duration_seconds": 120,
                "error_message": "Validation error"
            }
        ]
        
        details = handler._format_execution_details(results)
        
        assert len(details) == 2
        
        # First execution (succeeded)
        assert details[0]["execution_arn"] == "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec1"
        assert details[0]["brandid"] == 123
        assert details[0]["status"] == "SUCCEEDED"
        assert details[0]["start_time"] == "2024-01-01T12:00:00"
        assert details[0]["stop_time"] == "2024-01-01T12:05:00"
        assert details[0]["duration_seconds"] == 300
        assert "error_message" not in details[0]
        
        # Second execution (failed)
        assert details[1]["execution_arn"] == "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec2"
        assert details[1]["brandid"] == 456
        assert details[1]["status"] == "FAILED"
        assert details[1]["error_message"] == "Validation error"

    def test_format_execution_details_empty_results(self, handler):
        """Test formatting execution details with empty results."""
        results = []
        
        details = handler._format_execution_details(results)
        
        assert details == []

    def test_format_execution_details_excludes_none_error_message(self, handler):
        """Test that None error messages are excluded from details."""
        results = [
            {
                "execution_arn": "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec1",
                "brandid": 123,
                "status": "SUCCEEDED",
                "start_time": "2024-01-01T12:00:00",
                "stop_time": "2024-01-01T12:05:00",
                "duration_seconds": 300,
                "error_message": None
            }
        ]
        
        details = handler._format_execution_details(results)
        
        assert len(details) == 1
        assert "error_message" not in details[0]

    def test_format_execution_details_includes_error_message(self, handler):
        """Test that error messages are included when present."""
        results = [
            {
                "execution_arn": "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec1",
                "brandid": 789,
                "status": "FAILED",
                "start_time": "2024-01-01T12:00:00",
                "stop_time": "2024-01-01T12:01:00",
                "duration_seconds": 60,
                "error_message": "Brand not found"
            }
        ]
        
        details = handler._format_execution_details(results)
        
        assert len(details) == 1
        assert details[0]["error_message"] == "Brand not found"

    # ========== Execute Tests - Last Hour ==========

    def test_execute_last_hour_with_data(self, handler):
        """Test execute with last_hour time period and data."""
        handler.athena_client.execute_query.return_value = [{
            "total_executions": 25,
            "successful": 20,
            "failed": 3,
            "running": 2,
            "avg_duration": 180.5,
            "brands_processed": 23
        }]
        
        parameters = {"time_period": "last_hour"}
        result = handler.execute(parameters)
        
        assert result["time_period"] == "last_hour"
        assert result["total_executions"] == 25
        assert result["successful"] == 20
        assert result["failed"] == 3
        assert result["running"] == 2
        assert result["success_rate"] == 86.96  # 20/(20+3)*100
        assert result["average_duration_seconds"] == 180.5
        assert result["brands_processed"] == 23
        
        # Verify Athena was called
        handler.athena_client.execute_query.assert_called_once()

    # ========== Execute Tests - Last Day ==========

    def test_execute_last_day_with_data(self, handler):
        """Test execute with last_day time period and data."""
        handler.athena_client.execute_query.return_value = [{
            "total_executions": 500,
            "successful": 450,
            "failed": 40,
            "running": 10,
            "avg_duration": 250.0,
            "brands_processed": 490
        }]
        
        parameters = {"time_period": "last_day"}
        result = handler.execute(parameters)
        
        assert result["time_period"] == "last_day"
        assert result["total_executions"] == 500
        assert result["successful"] == 450
        assert result["failed"] == 40
        assert result["running"] == 10
        assert result["success_rate"] == 91.84  # 450/(450+40)*100
        assert result["average_duration_seconds"] == 250.0
        assert result["brands_processed"] == 490

    # ========== Execute Tests - Last Week ==========

    def test_execute_last_week_with_data(self, handler):
        """Test execute with last_week time period and data."""
        handler.athena_client.execute_query.return_value = [{
            "total_executions": 3500,
            "successful": 3200,
            "failed": 250,
            "running": 50,
            "avg_duration": 300.0,
            "brands_processed": 3450
        }]
        
        parameters = {"time_period": "last_week"}
        result = handler.execute(parameters)
        
        assert result["time_period"] == "last_week"
        assert result["total_executions"] == 3500
        assert result["successful"] == 3200
        assert result["failed"] == 250
        assert result["running"] == 50
        assert result["success_rate"] == 92.75  # 3200/(3200+250)*100
        assert result["average_duration_seconds"] == 300.0
        assert result["brands_processed"] == 3450

    # ========== Execute Tests - Empty Results ==========

    def test_execute_with_no_executions(self, handler):
        """Test execute when no executions exist in time period."""
        handler.athena_client.execute_query.return_value = []
        
        parameters = {"time_period": "last_hour"}
        result = handler.execute(parameters)
        
        assert result["time_period"] == "last_hour"
        assert result["total_executions"] == 0
        assert result["successful"] == 0
        assert result["failed"] == 0
        assert result["running"] == 0
        assert result["success_rate"] == 0.0
        assert result["average_duration_seconds"] == 0.0
        assert result["brands_processed"] == 0

    # ========== Execute Tests - With Details ==========

    def test_execute_with_include_details_true(self, handler):
        """Test execute with include_details=True."""
        # Mock stats query response
        handler.athena_client.execute_query.side_effect = [
            [{
                "total_executions": 10,
                "successful": 8,
                "failed": 2,
                "running": 0,
                "avg_duration": 200.0,
                "brands_processed": 10
            }],
            # Mock details query response
            [
                {
                    "execution_arn": "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec1",
                    "brandid": 123,
                    "status": "SUCCEEDED",
                    "start_time": "2024-01-01T12:00:00",
                    "stop_time": "2024-01-01T12:03:00",
                    "duration_seconds": 180,
                    "error_message": None
                },
                {
                    "execution_arn": "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec2",
                    "brandid": 456,
                    "status": "FAILED",
                    "start_time": "2024-01-01T11:00:00",
                    "stop_time": "2024-01-01T11:01:00",
                    "duration_seconds": 60,
                    "error_message": "Error occurred"
                }
            ]
        ]
        
        parameters = {
            "time_period": "last_day",
            "include_details": True
        }
        result = handler.execute(parameters)
        
        assert result["time_period"] == "last_day"
        assert result["total_executions"] == 10
        assert "execution_details" in result
        assert len(result["execution_details"]) == 2
        assert result["execution_details"][0]["brandid"] == 123
        assert result["execution_details"][1]["brandid"] == 456
        
        # Verify both queries were called
        assert handler.athena_client.execute_query.call_count == 2

    def test_execute_with_include_details_false(self, handler):
        """Test execute with include_details=False (default)."""
        handler.athena_client.execute_query.return_value = [{
            "total_executions": 10,
            "successful": 8,
            "failed": 2,
            "running": 0,
            "avg_duration": 200.0,
            "brands_processed": 10
        }]
        
        parameters = {
            "time_period": "last_day",
            "include_details": False
        }
        result = handler.execute(parameters)
        
        assert result["time_period"] == "last_day"
        assert "execution_details" not in result
        
        # Verify only stats query was called
        handler.athena_client.execute_query.assert_called_once()

    def test_execute_without_include_details_parameter(self, handler):
        """Test execute without include_details parameter (defaults to False)."""
        handler.athena_client.execute_query.return_value = [{
            "total_executions": 10,
            "successful": 8,
            "failed": 2,
            "running": 0,
            "avg_duration": 200.0,
            "brands_processed": 10
        }]
        
        parameters = {"time_period": "last_day"}
        result = handler.execute(parameters)
        
        assert "execution_details" not in result
        handler.athena_client.execute_query.assert_called_once()

    # ========== Error Handling Tests ==========

    def test_execute_handles_athena_error(self, handler):
        """Test error handling when Athena query fails."""
        handler.athena_client.execute_query.side_effect = Exception("Athena service error")
        
        parameters = {"time_period": "last_day"}
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "failed to query workflow statistics" in str(exc_info.value).lower()
        assert "athena" in str(exc_info.value).lower()

    def test_execute_handles_table_not_found_error(self, handler):
        """Test error handling when workflow_executions table doesn't exist."""
        handler.athena_client.execute_query.side_effect = Exception("TABLE_NOT_FOUND: workflow_executions")
        
        parameters = {"time_period": "last_hour"}
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "failed to query workflow statistics" in str(exc_info.value).lower()

    def test_execute_handles_details_query_error(self, handler):
        """Test error handling when details query fails."""
        # Stats query succeeds, details query fails
        handler.athena_client.execute_query.side_effect = [
            [{
                "total_executions": 10,
                "successful": 8,
                "failed": 2,
                "running": 0,
                "avg_duration": 200.0,
                "brands_processed": 10
            }],
            Exception("Details query failed")
        ]
        
        parameters = {
            "time_period": "last_day",
            "include_details": True
        }
        
        with pytest.raises(BackendServiceError) as exc_info:
            handler.execute(parameters)
        
        assert "failed to query workflow statistics" in str(exc_info.value).lower()

    # ========== Lambda Handler Integration Tests ==========

    def test_lambda_handler_success(self, handler):
        """Test lambda_handler with successful execution."""
        handler.athena_client.execute_query.return_value = [{
            "total_executions": 100,
            "successful": 90,
            "failed": 10,
            "running": 0,
            "avg_duration": 250.0,
            "brands_processed": 100
        }]
        
        event = {
            "parameters": {"time_period": "last_day"},
            "request_id": "test-request-123"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is True
        assert "data" in response
        assert response["data"]["time_period"] == "last_day"
        assert response["data"]["total_executions"] == 100
        assert response["request_id"] == "test-request-123"

    def test_lambda_handler_validation_error(self, handler):
        """Test lambda_handler with validation error."""
        event = {
            "parameters": {"time_period": "invalid_period"},
            "request_id": "test-request-456"
        }
        
        response = handler.handle(event, None)
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["type"] == "user_input"
        assert "time_period must be one of" in response["error"]["message"]
        assert response["request_id"] == "test-request-456"

    def test_lambda_handler_backend_error(self, handler):
        """Test lambda_handler with backend service error."""
        handler.athena_client.execute_query.side_effect = Exception("Athena error")
        
        event = {
            "parameters": {"time_period": "last_hour"},
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
        assert required == ["time_period"]

    def test_execute_result_structure(self, handler):
        """Test that execute returns correct result structure."""
        handler.athena_client.execute_query.return_value = [{
            "total_executions": 50,
            "successful": 45,
            "failed": 5,
            "running": 0,
            "avg_duration": 200.0,
            "brands_processed": 50
        }]
        
        result = handler.execute({"time_period": "last_day"})
        
        # Verify all required fields are present
        assert "time_period" in result
        assert "total_executions" in result
        assert "successful" in result
        assert "failed" in result
        assert "running" in result
        assert "success_rate" in result
        assert "average_duration_seconds" in result
        assert "brands_processed" in result
        
        # Verify types
        assert isinstance(result["time_period"], str)
        assert isinstance(result["total_executions"], int)
        assert isinstance(result["successful"], int)
        assert isinstance(result["failed"], int)
        assert isinstance(result["running"], int)
        assert isinstance(result["success_rate"], float)
        assert isinstance(result["average_duration_seconds"], float)
        assert isinstance(result["brands_processed"], int)

    def test_execute_with_all_execution_states(self, handler):
        """Test execute with mix of all execution states."""
        handler.athena_client.execute_query.return_value = [{
            "total_executions": 100,
            "successful": 70,
            "failed": 20,
            "running": 10,
            "avg_duration": 275.5,
            "brands_processed": 90
        }]
        
        parameters = {"time_period": "last_week"}
        result = handler.execute(parameters)
        
        assert result["total_executions"] == 100
        assert result["successful"] == 70
        assert result["failed"] == 20
        assert result["running"] == 10
        # Success rate = 70/(70+20)*100 = 77.78
        assert result["success_rate"] == 77.78
        assert result["brands_processed"] == 90
