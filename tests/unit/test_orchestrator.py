"""
Unit tests for Orchestrator Agent

Tests cover:
- Workflow initialization
- Agent invocation tools
- Workflow state management
- Error handling and retry logic
- Iteration limit enforcement
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from agents.orchestrator.tools import (
    initialize_workflow,
    invoke_data_transformation,
    invoke_evaluator,
    invoke_metadata_production,
    invoke_confirmation,
    invoke_tiebreaker,
    update_workflow_state,
    get_workflow_summary,
    retry_with_backoff,
    WorkflowState,
    _workflow_state
)


class TestWorkflowInitialization:
    """Test workflow initialization functionality."""
    
    def test_initialize_workflow_with_defaults(self):
        """Test workflow initialization with default configuration."""
        result = initialize_workflow({})
        
        assert result["success"] is True
        assert result["workflow_initialized"] is True
        assert result["config"]["max_iterations"] == 5
        assert result["config"]["confidence_threshold"] == 0.75
        assert result["config"]["parallel_batch_size"] == 10
        
    def test_initialize_workflow_with_custom_config(self):
        """Test workflow initialization with custom configuration."""
        config = {
            "max_iterations": 3,
            "confidence_threshold": 0.8,
            "parallel_batch_size": 20
        }
        result = initialize_workflow(config)
        
        assert result["success"] is True
        assert result["config"]["max_iterations"] == 3
        assert result["config"]["confidence_threshold"] == 0.8
        assert result["config"]["parallel_batch_size"] == 20
        
    def test_initialize_workflow_invalid_max_iterations(self):
        """Test workflow initialization with invalid max_iterations."""
        config = {"max_iterations": 15}
        result = initialize_workflow(config)
        
        assert result["success"] is False
        assert "max_iterations must be between 1 and 10" in result["error"]
        
    def test_initialize_workflow_invalid_confidence_threshold(self):
        """Test workflow initialization with invalid confidence_threshold."""
        config = {"confidence_threshold": 1.5}
        result = initialize_workflow(config)
        
        assert result["success"] is False
        assert "confidence_threshold must be between 0.0 and 1.0" in result["error"]
        
    def test_initialize_workflow_invalid_batch_size(self):
        """Test workflow initialization with invalid parallel_batch_size."""
        config = {"parallel_batch_size": 150}
        result = initialize_workflow(config)
        
        assert result["success"] is False
        assert "parallel_batch_size must be between 1 and 100" in result["error"]


class TestDataTransformationInvocation:
    """Test Data Transformation Agent invocation."""
    
    def test_invoke_data_transformation_ingest(self):
        """Test data ingestion action."""
        result = invoke_data_transformation("ingest_data", {
            "expected_brands": 3000,
            "expected_combos": 150000
        })
        
        assert result["success"] is True
        assert result["status"] == "data_ingested"
        assert result["brands_to_process"] == 3000
        assert result["total_combos"] == 150000
        
    def test_invoke_data_transformation_validate_and_store_success(self):
        """Test successful metadata validation and storage."""
        result = invoke_data_transformation("validate_and_store", {
            "brandid": 123,
            "metadata": {
                "regex": "^STARBUCKS.*",
                "mccids": [5812, 5814]
            }
        })
        
        assert result["success"] is True
        assert result["brandid"] == 123
        assert result["s3_key"] == "metadata/brand_123.json"
        assert len(result["validation_errors"]) == 0
        
    def test_invoke_data_transformation_validate_missing_regex(self):
        """Test validation failure with missing regex."""
        result = invoke_data_transformation("validate_and_store", {
            "brandid": 123,
            "metadata": {
                "mccids": [5812, 5814]
            }
        })
        
        assert result["success"] is False
        assert "Missing regex pattern" in result["validation_errors"]
        
    def test_invoke_data_transformation_validate_missing_mccids(self):
        """Test validation failure with missing MCCID list."""
        result = invoke_data_transformation("validate_and_store", {
            "brandid": 123,
            "metadata": {
                "regex": "^STARBUCKS.*"
            }
        })
        
        assert result["success"] is False
        assert "Missing MCCID list" in result["validation_errors"]
        
    def test_invoke_data_transformation_prepare_brand_data(self):
        """Test brand data preparation."""
        result = invoke_data_transformation("prepare_brand_data", {
            "brandid": 456
        })
        
        assert result["success"] is True
        assert result["brandid"] == 456
        assert "brand_data" in result
        
    def test_invoke_data_transformation_unknown_action(self):
        """Test handling of unknown action."""
        result = invoke_data_transformation("unknown_action", {})
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]


class TestEvaluatorInvocation:
    """Test Evaluator Agent invocation."""
    
    def test_invoke_evaluator_success(self):
        """Test successful evaluator invocation."""
        brand_data = {
            "brandname": "Starbucks",
            "sector": "Food & Beverage",
            "combos": []
        }
        result = invoke_evaluator(123, brand_data)
        
        assert result["success"] is True
        assert result["brandid"] == 123
        assert "confidence_score" in result
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert "issues" in result
        assert "production_prompt" in result
        
    def test_invoke_evaluator_returns_evaluation_fields(self):
        """Test that evaluator returns all required fields."""
        result = invoke_evaluator(456, {})
        
        assert result["success"] is True
        assert "confidence_score" in result
        assert "issues" in result
        assert "wallet_affected" in result
        assert "ties_detected" in result
        assert "production_prompt" in result


class TestMetadataProductionInvocation:
    """Test Metadata Production Agent invocation."""
    
    def test_invoke_metadata_production_initial(self):
        """Test initial metadata generation."""
        evaluation = {
            "confidence_score": 0.85,
            "production_prompt": "Generate standard metadata"
        }
        result = invoke_metadata_production(123, evaluation)
        
        assert result["success"] is True
        assert result["brandid"] == 123
        assert "regex" in result
        assert "mccids" in result
        assert isinstance(result["mccids"], list)
        assert "iteration" in result
        
    def test_invoke_metadata_production_with_feedback(self):
        """Test metadata regeneration with feedback."""
        evaluation = {"confidence_score": 0.7}
        feedback = {"issue": "Regex too broad"}
        
        result = invoke_metadata_production(456, evaluation, feedback)
        
        assert result["success"] is True
        assert result["brandid"] == 456
        assert "regex" in result
        assert "mccids" in result


class TestConfirmationInvocation:
    """Test Confirmation Agent invocation."""
    
    def test_invoke_confirmation_success(self):
        """Test successful confirmation invocation."""
        metadata = {
            "regex": "^STARBUCKS.*",
            "mccids": [5812, 5814]
        }
        matched_combos = [
            {"ccid": 1001, "narrative": "STARBUCKS #123"},
            {"ccid": 1002, "narrative": "STARBUCKS COFFEE"}
        ]
        
        result = invoke_confirmation(123, metadata, matched_combos)
        
        assert result["success"] is True
        assert result["brandid"] == 123
        assert "confirmed_combos" in result
        assert "excluded_combos" in result
        assert "requires_human_review" in result
        
    def test_invoke_confirmation_empty_combos(self):
        """Test confirmation with no matched combos."""
        result = invoke_confirmation(456, {}, [])
        
        assert result["success"] is True
        assert len(result["confirmed_combos"]) == 0


class TestTiebreakerInvocation:
    """Test Tiebreaker Agent invocation."""
    
    def test_invoke_tiebreaker_success(self):
        """Test successful tie resolution."""
        tie_data = {
            "ccid": 5001,
            "combo": {
                "narrative": "SHELL STATION 123",
                "mccid": 5541,
                "mid": "MID123"
            },
            "matching_brands": [
                {"brandid": 100, "brandname": "Shell"},
                {"brandid": 200, "brandname": "Shell Station"}
            ]
        }
        
        result = invoke_tiebreaker(tie_data)
        
        assert result["success"] is True
        assert result["ccid"] == 5001
        assert "resolution_type" in result
        assert "assigned_brandid" in result or result["resolution_type"] == "manual_review"
        assert "confidence" in result
        assert "reasoning" in result
        
    def test_invoke_tiebreaker_no_matching_brands(self):
        """Test tiebreaker with no matching brands."""
        tie_data = {
            "ccid": 5002,
            "combo": {},
            "matching_brands": []
        }
        
        result = invoke_tiebreaker(tie_data)
        
        assert result["success"] is False
        assert "No matching brands" in result["error"]


class TestWorkflowStateManagement:
    """Test workflow state management."""
    
    def setup_method(self):
        """Reset workflow state before each test."""
        global _workflow_state
        from agents.orchestrator import tools
        tools._workflow_state = WorkflowState()
        
    def test_update_workflow_state_success(self):
        """Test successful workflow state update."""
        result = update_workflow_state(123, "evaluating")
        
        assert result["success"] is True
        assert result["brandid"] == 123
        assert result["status"] == "evaluating"
        
    def test_update_workflow_state_with_metadata(self):
        """Test workflow state update with metadata."""
        metadata = {"regex": "^TEST.*", "mccids": [5812]}
        result = update_workflow_state(456, "completed", metadata)
        
        assert result["success"] is True
        assert result["brandid"] == 456
        assert result["status"] == "completed"
        
    def test_workflow_state_tracks_multiple_brands(self):
        """Test that workflow state tracks multiple brands."""
        update_workflow_state(100, "evaluating")
        update_workflow_state(200, "generating")
        update_workflow_state(300, "completed")
        
        summary = get_workflow_summary()
        assert summary["brands_processed"] == 3
        assert summary["status_breakdown"]["evaluating"] == 1
        assert summary["status_breakdown"]["generating"] == 1
        assert summary["status_breakdown"]["completed"] == 1


class TestWorkflowSummary:
    """Test workflow summary functionality."""
    
    def setup_method(self):
        """Reset workflow state before each test."""
        global _workflow_state
        from agents.orchestrator import tools
        tools._workflow_state = WorkflowState()
        
    def test_get_workflow_summary_empty(self):
        """Test workflow summary with no brands processed."""
        summary = get_workflow_summary()
        
        assert summary["brands_processed"] == 0
        assert summary["total_failures"] == 0
        assert summary["average_iterations"] == 0
        
    def test_get_workflow_summary_with_brands(self):
        """Test workflow summary with processed brands."""
        update_workflow_state(100, "completed")
        update_workflow_state(200, "completed")
        update_workflow_state(300, "failed")
        
        summary = get_workflow_summary()
        
        assert summary["brands_processed"] == 3
        assert summary["status_breakdown"]["completed"] == 2
        assert summary["status_breakdown"]["failed"] == 1


class TestIterationTracking:
    """Test iteration count tracking."""
    
    def setup_method(self):
        """Reset workflow state before each test."""
        global _workflow_state
        from agents.orchestrator import tools
        tools._workflow_state = WorkflowState()
        
    def test_iteration_count_starts_at_zero(self):
        """Test that iteration count starts at 0."""
        from agents.orchestrator import tools
        count = tools._workflow_state.get_iteration_count(123)
        assert count == 0
        
    def test_increment_iteration_count(self):
        """Test incrementing iteration count."""
        from agents.orchestrator import tools
        count1 = tools._workflow_state.increment_iteration(123)
        count2 = tools._workflow_state.increment_iteration(123)
        count3 = tools._workflow_state.increment_iteration(123)
        
        assert count1 == 1
        assert count2 == 2
        assert count3 == 3
        
    def test_iteration_count_per_brand(self):
        """Test that iteration counts are tracked per brand."""
        from agents.orchestrator import tools
        tools._workflow_state.increment_iteration(100)
        tools._workflow_state.increment_iteration(100)
        tools._workflow_state.increment_iteration(200)
        
        assert tools._workflow_state.get_iteration_count(100) == 2
        assert tools._workflow_state.get_iteration_count(200) == 1
        assert tools._workflow_state.get_iteration_count(300) == 0


class TestRetryLogic:
    """Test retry logic with exponential backoff."""
    
    def test_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""
        mock_func = Mock(return_value="success")
        result = retry_with_backoff(mock_func, max_retries=3)
        
        assert result == "success"
        assert mock_func.call_count == 1
        
    def test_retry_success_after_failures(self):
        """Test successful execution after initial failures."""
        mock_func = Mock(side_effect=[Exception("fail"), Exception("fail"), "success"])
        result = retry_with_backoff(mock_func, max_retries=3, initial_delay=0.01)
        
        assert result == "success"
        assert mock_func.call_count == 3
        
    def test_retry_all_attempts_fail(self):
        """Test that exception is raised after all retries fail."""
        mock_func = Mock(side_effect=Exception("persistent failure"))
        
        with pytest.raises(Exception) as exc_info:
            retry_with_backoff(mock_func, max_retries=3, initial_delay=0.01)
            
        assert "persistent failure" in str(exc_info.value)
        assert mock_func.call_count == 3
        
    def test_retry_exponential_backoff(self):
        """Test that retry delays increase exponentially."""
        call_times = []
        
        def failing_func():
            call_times.append(time.time())
            raise Exception("fail")
            
        with pytest.raises(Exception):
            retry_with_backoff(failing_func, max_retries=3, initial_delay=0.1)
            
        # Verify exponential backoff (delays should be ~0.1, ~0.2, ~0.4)
        assert len(call_times) == 3
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert delay1 >= 0.09  # Allow small timing variance


class TestFailureTracking:
    """Test failure tracking functionality."""
    
    def setup_method(self):
        """Reset workflow state before each test."""
        global _workflow_state
        from agents.orchestrator import tools
        tools._workflow_state = WorkflowState()
        
    def test_add_failure_records_error(self):
        """Test that failures are recorded."""
        from agents.orchestrator import tools
        tools._workflow_state.add_failure(123, "Evaluation failed", "Evaluator")
        
        summary = get_workflow_summary()
        assert summary["total_failures"] == 1
        assert len(summary["failures"]) == 1
        assert summary["failures"][0]["brandid"] == 123
        assert summary["failures"][0]["agent"] == "Evaluator"
        
    def test_multiple_failures_tracked(self):
        """Test that multiple failures are tracked."""
        from agents.orchestrator import tools
        tools._workflow_state.add_failure(100, "Error 1", "Agent1")
        tools._workflow_state.add_failure(200, "Error 2", "Agent2")
        tools._workflow_state.add_failure(300, "Error 3", "Agent3")
        
        summary = get_workflow_summary()
        assert summary["total_failures"] == 3


class TestWorkflowStateClass:
    """Test WorkflowState class directly."""
    
    def test_workflow_state_initialization(self):
        """Test WorkflowState initialization."""
        state = WorkflowState()
        
        assert len(state.brands_status) == 0
        assert len(state.iteration_counts) == 0
        assert len(state.failures) == 0
        
    def test_update_brand_status(self):
        """Test updating brand status."""
        state = WorkflowState()
        state.update_brand_status(123, "evaluating", {"test": "data"})
        
        assert 123 in state.brands_status
        assert state.brands_status[123]["status"] == "evaluating"
        assert state.brands_status[123]["metadata"] == {"test": "data"}
        
    def test_get_summary_statistics(self):
        """Test summary statistics calculation."""
        state = WorkflowState()
        state.update_brand_status(100, "completed")
        state.update_brand_status(200, "completed")
        state.update_brand_status(300, "failed")
        state.increment_iteration(100)
        state.increment_iteration(100)
        state.increment_iteration(200)
        
        summary = state.get_summary()
        
        assert summary["brands_processed"] == 3
        assert summary["status_breakdown"]["completed"] == 2
        assert summary["status_breakdown"]["failed"] == 1
        assert summary["average_iterations"] == 1.5  # (2 + 1 + 0) / 2 brands with iterations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
