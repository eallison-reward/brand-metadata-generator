"""Property-based tests for CloudWatch logging.

**Validates: Requirements 9.5**
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone
import json
import logging

from shared.utils.logger import (
    setup_logger,
    log_tool_execution,
    ToolLogger,
)
from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import UserInputError, BackendServiceError

# Feature: conversational-interface-agent, Property 23: CloudWatch Logging
# For any tool execution (successful or failed), a log entry should be written
# to CloudWatch containing the tool name, input parameters, execution result,
# and timestamp.


# Hypothesis strategies for generating test data
@st.composite
def tool_name_strategy(draw):
    """Generate tool names."""
    return draw(st.sampled_from([
        "query_brands_to_check",
        "start_workflow",
        "check_workflow_status",
        "submit_feedback",
        "query_metadata",
        "execute_athena_query",
        "list_escalations",
        "get_workflow_stats",
    ]))


@st.composite
def request_id_strategy(draw):
    """Generate request IDs."""
    return f"req-{draw(st.uuids())}"


@st.composite
def parameters_strategy(draw):
    """Generate parameter dictionaries."""
    param_types = draw(st.sampled_from([
        {"brandid": draw(st.integers(min_value=1, max_value=10000))},
        {"execution_arn": f"arn:aws:states:eu-west-1:123456789012:execution:workflow:{draw(st.text(min_size=5, max_size=20))}"},
        {"feedback_text": draw(st.text(min_size=1, max_size=200))},
        {"query_type": draw(st.sampled_from(["brands_by_confidence", "brands_by_category"]))},
    ]))
    return param_types


@st.composite
def result_strategy(draw):
    """Generate result dictionaries."""
    return {
        "success": True,
        "data": draw(st.lists(st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.integers(),
            min_size=1,
            max_size=5
        ), min_size=0, max_size=10)),
        "row_count": draw(st.integers(min_value=0, max_value=100)),
    }


# Mock handler for testing
class MockToolHandler(BaseToolHandler):
    """Mock tool handler for testing."""
    
    def __init__(self, tool_name: str, should_fail: bool = False, fail_with: Exception = None):
        super().__init__(tool_name)
        self.should_fail = should_fail
        self.fail_with = fail_with
    
    def validate_parameters(self, parameters):
        if self.should_fail and isinstance(self.fail_with, UserInputError):
            raise self.fail_with
    
    def execute(self, parameters):
        if self.should_fail and not isinstance(self.fail_with, UserInputError):
            raise self.fail_with
        return {"result": "success", "data": parameters}


@pytest.mark.property
class TestCloudWatchLogging:
    """Property 23: CloudWatch Logging
    
    Property: For any tool execution (successful or failed), a log entry should
    be written to CloudWatch containing the tool name, input parameters,
    execution result, and timestamp.
    
    Validates: Requirements 9.5
    """

    @given(
        tool_name=tool_name_strategy(),
        request_id=request_id_strategy(),
        parameters=parameters_strategy(),
        result=result_strategy(),
    )
    @settings(max_examples=100, deadline=1000)
    def test_successful_execution_logging(self, tool_name, request_id, parameters, result):
        """Property: Successful tool execution is logged with all required fields.
        
        For any successful tool execution, a log entry should contain tool name,
        request ID, parameters, result, and timestamp.
        """
        # Create mock logger
        mock_logger = MagicMock(spec=logging.Logger)
        
        # Execute logging
        log_tool_execution(
            logger=mock_logger,
            tool_name=tool_name,
            request_id=request_id,
            parameters=parameters,
            result=result,
            error=None,
        )
        
        # Property 1: Logger.info was called (success case)
        assert mock_logger.info.called
        
        # Property 2: Log message contains JSON data
        log_call = mock_logger.info.call_args[0][0]
        assert "Tool execution completed:" in log_call
        
        # Property 3: Log contains tool name
        assert tool_name in log_call
        
        # Property 4: Log contains request ID
        assert request_id in log_call
        
        # Property 5: Log data is valid JSON
        json_start = log_call.index("{")
        json_data = log_call[json_start:]
        parsed_data = json.loads(json_data)
        
        # Property 6: Parsed data has required fields
        assert "tool_name" in parsed_data
        assert "request_id" in parsed_data
        assert "timestamp" in parsed_data
        assert "parameters" in parsed_data
        assert "status" in parsed_data
        
        # Property 7: Field values match inputs
        assert parsed_data["tool_name"] == tool_name
        assert parsed_data["request_id"] == request_id
        assert parsed_data["status"] == "success"
        
        # Property 8: Timestamp is valid ISO format
        timestamp = datetime.fromisoformat(parsed_data["timestamp"].replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)

    @given(
        tool_name=tool_name_strategy(),
        request_id=request_id_strategy(),
        parameters=parameters_strategy(),
        error_message=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=100, deadline=1000)
    def test_failed_execution_logging(self, tool_name, request_id, parameters, error_message):
        """Property: Failed tool execution is logged with error details.
        
        For any failed tool execution, a log entry should contain tool name,
        request ID, parameters, error details, and timestamp.
        """
        # Create mock logger
        mock_logger = MagicMock(spec=logging.Logger)
        
        # Create error
        error = UserInputError(error_message)
        
        # Execute logging
        log_tool_execution(
            logger=mock_logger,
            tool_name=tool_name,
            request_id=request_id,
            parameters=parameters,
            result=None,
            error=error,
        )
        
        # Property 1: Logger.error was called (failure case)
        assert mock_logger.error.called
        
        # Property 2: Log message contains JSON data
        log_call = mock_logger.error.call_args[0][0]
        assert "Tool execution failed:" in log_call
        
        # Property 3: Log contains tool name
        assert tool_name in log_call
        
        # Property 4: Log data is valid JSON
        json_start = log_call.index("{")
        json_data = log_call[json_start:]
        parsed_data = json.loads(json_data)
        
        # Property 5: Parsed data has required fields
        assert "tool_name" in parsed_data
        assert "request_id" in parsed_data
        assert "timestamp" in parsed_data
        assert "parameters" in parsed_data
        assert "status" in parsed_data
        assert "error" in parsed_data
        assert "error_type" in parsed_data
        
        # Property 6: Field values match inputs
        assert parsed_data["tool_name"] == tool_name
        assert parsed_data["request_id"] == request_id
        assert parsed_data["status"] == "error"
        assert error_message in parsed_data["error"]
        assert parsed_data["error_type"] == "UserInputError"

    @given(
        tool_name=tool_name_strategy(),
        request_id=request_id_strategy(),
        parameters=parameters_strategy(),
    )
    @settings(max_examples=50, deadline=1000)
    def test_tool_logger_context_manager_success(self, tool_name, request_id, parameters):
        """Property: ToolLogger context manager logs execution start and completion.
        
        The ToolLogger context manager should log when entering and exiting,
        with appropriate success status.
        """
        # Create mock logger
        mock_logger = MagicMock(spec=logging.Logger)
        
        # Use context manager
        with ToolLogger(mock_logger, tool_name, request_id, parameters) as tool_logger:
            # Property 1: Entry log was created
            assert mock_logger.info.called
            entry_call = mock_logger.info.call_args_list[0][0][0]
            assert "Starting tool execution" in entry_call
            assert tool_name in entry_call
            assert request_id in entry_call
            
            # Set result
            result = {"success": True, "data": "test"}
            tool_logger.set_result(result)
        
        # Property 2: Exit log was created
        assert mock_logger.info.call_count >= 2
        exit_call = mock_logger.info.call_args_list[-1][0][0]
        assert "Tool execution completed" in exit_call
        
        # Property 3: Exit log contains execution time
        json_start = exit_call.index("{")
        json_data = exit_call[json_start:]
        parsed_data = json.loads(json_data)
        assert "execution_time_ms" in parsed_data
        assert isinstance(parsed_data["execution_time_ms"], int)
        assert parsed_data["execution_time_ms"] >= 0

    @given(
        tool_name=tool_name_strategy(),
        request_id=request_id_strategy(),
        parameters=parameters_strategy(),
        error_message=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=50, deadline=1000)
    def test_tool_logger_context_manager_failure(self, tool_name, request_id, parameters, error_message):
        """Property: ToolLogger context manager logs exceptions.
        
        When an exception occurs within the context, it should be logged
        with error status.
        """
        # Create mock logger
        mock_logger = MagicMock(spec=logging.Logger)
        
        # Use context manager with exception
        try:
            with ToolLogger(mock_logger, tool_name, request_id, parameters):
                raise BackendServiceError(error_message)
        except BackendServiceError:
            pass  # Expected
        
        # Property 1: Error log was created
        assert mock_logger.error.called
        error_call = mock_logger.error.call_args[0][0]
        assert "Tool execution failed" in error_call
        
        # Property 2: Error details are in log
        json_start = error_call.index("{")
        json_data = error_call[json_start:]
        parsed_data = json.loads(json_data)
        assert parsed_data["status"] == "error"
        assert error_message in parsed_data["error"]


@pytest.mark.property
class TestLoggingDataSanitization:
    """Property tests for logging data sanitization."""

    @given(
        tool_name=tool_name_strategy(),
        request_id=request_id_strategy(),
        sensitive_key=st.sampled_from(["password", "token", "secret", "api_key", "credential"]),
        sensitive_value=st.text(min_size=10, max_size=50, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
    )
    @settings(max_examples=50, deadline=500)
    def test_sensitive_parameters_are_redacted(self, tool_name, request_id, sensitive_key, sensitive_value):
        """Property: Sensitive parameters are redacted in logs.
        
        Parameters with sensitive keys (password, token, etc.) should be
        redacted in log output.
        """
        # Create mock logger
        mock_logger = MagicMock(spec=logging.Logger)
        
        # Create parameters with sensitive data
        parameters = {
            sensitive_key: sensitive_value,
            "brandid": 123,
        }
        
        # Execute logging
        log_tool_execution(
            logger=mock_logger,
            tool_name=tool_name,
            request_id=request_id,
            parameters=parameters,
            result={"success": True},
        )
        
        # Property 1: Log was created
        assert mock_logger.info.called
        log_call = mock_logger.info.call_args[0][0]
        
        # Property 2: Redaction marker IS in log
        assert "REDACTED" in log_call
        
        # Property 3: Sensitive key is in parameters section
        json_start = log_call.index("{")
        json_data = log_call[json_start:]
        parsed_data = json.loads(json_data)
        assert sensitive_key in parsed_data["parameters"]
        assert parsed_data["parameters"][sensitive_key] == "***REDACTED***"
        
        # Property 4: Non-sensitive data IS in log
        assert "brandid" in log_call

    @given(
        tool_name=tool_name_strategy(),
        request_id=request_id_strategy(),
        long_text=st.text(min_size=250, max_size=500, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
    )
    @settings(max_examples=30, deadline=500)
    def test_long_parameters_are_truncated(self, tool_name, request_id, long_text):
        """Property: Long parameter values are truncated in logs.
        
        Parameter values longer than 200 characters should be truncated
        to prevent excessive log size.
        """
        # Create mock logger
        mock_logger = MagicMock(spec=logging.Logger)
        
        # Create parameters with long text
        parameters = {
            "long_field": long_text,
            "brandid": 123,
        }
        
        # Execute logging
        log_tool_execution(
            logger=mock_logger,
            tool_name=tool_name,
            request_id=request_id,
            parameters=parameters,
            result={"success": True},
        )
        
        # Property 1: Log was created
        assert mock_logger.info.called
        log_call = mock_logger.info.call_args[0][0]
        
        # Property 2: Truncation marker IS in log
        assert "truncated" in log_call.lower()
        
        # Property 3: Parse JSON and check truncation
        json_start = log_call.index("{")
        json_data = log_call[json_start:]
        parsed_data = json.loads(json_data)
        logged_value = parsed_data["parameters"]["long_field"]
        
        # Property 4: Logged value is shorter than original
        assert len(logged_value) < len(long_text)
        
        # Property 5: Logged value contains truncation marker
        assert "truncated" in logged_value.lower()


@pytest.mark.property
class TestBaseHandlerLogging:
    """Property tests for BaseToolHandler logging integration."""

    @given(
        tool_name=tool_name_strategy(),
        parameters=parameters_strategy(),
    )
    @settings(max_examples=50, deadline=1000)
    def test_handler_logs_successful_execution(self, tool_name, parameters):
        """Property: BaseToolHandler logs successful executions.
        
        When a tool handler executes successfully, it should log the execution
        with all required fields.
        """
        # Create handler
        handler = MockToolHandler(tool_name, should_fail=False)
        
        # Mock the logger
        with patch.object(handler.logger, 'info') as mock_info:
            # Execute handler
            event = {
                "request_id": "test-request-123",
                "parameters": parameters,
            }
            response = handler.handle(event, None)
            
            # Property 1: Handler succeeded
            assert response["success"] is True
            
            # Property 2: Logger was called
            assert mock_info.called
            
            # Property 3: At least two log calls (start and completion)
            assert mock_info.call_count >= 2
            
            # Property 4: Start log contains tool name
            start_call = mock_info.call_args_list[0][0][0]
            assert tool_name in start_call
            assert "Starting tool execution" in start_call
            
            # Property 5: Completion log contains success status
            completion_call = mock_info.call_args_list[-1][0][0]
            assert "completed" in completion_call.lower()

    @given(
        tool_name=tool_name_strategy(),
        parameters=parameters_strategy(),
        error_message=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=50, deadline=1000)
    def test_handler_logs_failed_execution(self, tool_name, parameters, error_message):
        """Property: BaseToolHandler logs failed executions.
        
        When a tool handler fails, it should log the error with all required
        fields including error details.
        """
        # Create handler that will fail
        error = UserInputError(error_message)
        handler = MockToolHandler(tool_name, should_fail=True, fail_with=error)
        
        # Mock the logger
        with patch.object(handler.logger, 'info') as mock_info, \
             patch.object(handler.logger, 'error') as mock_error:
            # Execute handler
            event = {
                "request_id": "test-request-456",
                "parameters": parameters,
            }
            response = handler.handle(event, None)
            
            # Property 1: Handler failed
            assert response["success"] is False
            
            # Property 2: Error logger was called
            assert mock_error.called
            
            # Property 3: Error log contains error message
            error_call = mock_error.call_args[0][0]
            assert "failed" in error_call.lower()
            
            # Property 4: Error log contains tool name
            assert tool_name in error_call


@pytest.mark.property
class TestLoggingConsistency:
    """Property tests for logging consistency."""

    @given(
        num_executions=st.integers(min_value=1, max_value=5),
        tool_name=tool_name_strategy(),
    )
    @settings(max_examples=30, deadline=1000)
    def test_multiple_executions_have_consistent_log_structure(self, num_executions, tool_name):
        """Property: Multiple executions produce consistent log structure.
        
        All log entries should have the same structure regardless of
        execution count or parameters.
        """
        # Create mock logger
        mock_logger = MagicMock(spec=logging.Logger)
        
        log_structures = []
        
        for i in range(num_executions):
            # Execute logging
            log_tool_execution(
                logger=mock_logger,
                tool_name=tool_name,
                request_id=f"req-{i}",
                parameters={"iteration": i},
                result={"success": True, "iteration": i},
            )
            
            # Extract log structure
            log_call = mock_logger.info.call_args[0][0]
            json_start = log_call.index("{")
            json_data = log_call[json_start:]
            parsed_data = json.loads(json_data)
            log_structures.append(set(parsed_data.keys()))
        
        # Property 1: All logs have same keys
        first_structure = log_structures[0]
        for structure in log_structures[1:]:
            assert structure == first_structure, "Log structures are inconsistent"
        
        # Property 2: All logs have required keys
        required_keys = {"tool_name", "request_id", "timestamp", "parameters", "status"}
        for structure in log_structures:
            assert required_keys.issubset(structure)
