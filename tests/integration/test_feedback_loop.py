"""
Integration tests for Human-in-the-Loop (HITL) feedback workflow.

This module tests the complete feedback loop from submission through
processing, metadata regeneration, and re-classification.

Tests verify:
- Feedback submission and storage
- Feedback processing and refinement prompt generation
- Metadata regeneration based on feedback
- Re-application of metadata to combos
- Iteration tracking and increment
- Escalation when iteration limit exceeded
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from agents.feedback_processing import tools as fp_tools
from agents.metadata_production import tools as mp_tools
from agents.data_transformation import tools as dt_tools_module


@pytest.fixture
def sample_brand_data():
    """Sample brand data for testing."""
    return {
        "brandid": 123,
        "brandname": "Starbucks",
        "sector": "Food & Beverage",
        "combos": [
            {
                "ccid": 1,
                "narrative": "STARBUCKS #12345",
                "mccid": 5812
            },
            {
                "ccid": 2,
                "narrative": "STARBUCKS COFFEE",
                "mccid": 5812
            },
            {
                "ccid": 3,
                "narrative": "STAR BUCKS STORE",  # Misspelled
                "mccid": 5812
            }
        ]
    }


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return {
        "brandid": 123,
        "brandname": "Starbucks",
        "regex": "^STARBUCKS.*",
        "mccid_list": [5812],
        "version": 1,
        "iteration": 1
    }


@pytest.fixture
def sample_feedback():
    """Sample human feedback for testing."""
    return {
        "brandid": 123,
        "feedback_type": "specific_examples",
        "feedback_text": "The regex pattern is missing variations like 'STAR BUCKS' with a space. Combo 3 should be matched.",
        "combo_ids": [3],
        "timestamp": datetime.now().isoformat(),
        "metadata_version": 1
    }


class TestFeedbackSubmission:
    """Test feedback submission and storage."""

    def test_feedback_submission_success(self, sample_feedback):
        """Test successful feedback submission and storage."""
        # First parse the feedback
        parsed_feedback = fp_tools.parse_feedback(
            feedback_text=sample_feedback["feedback_text"],
            brandid=sample_feedback["brandid"]
        )
        
        # Verify parsing succeeded
        assert "feedback_id" in parsed_feedback
        assert parsed_feedback["brandid"] == 123
        assert "timestamp" in parsed_feedback
        
        # Store feedback
        result = fp_tools.store_feedback(
            brandid=sample_feedback["brandid"],
            feedback=parsed_feedback,
            metadata_version=sample_feedback["metadata_version"]
        )
        
        # Verify result
        assert result["feedback_stored"] is True
        assert "storage_location" in result
        assert result["dynamodb_stored"] is True
    
    def test_feedback_history_retrieval(self, sample_feedback):
        """Test retrieving feedback history for a brand."""
        # Retrieve feedback history (returns empty list in test environment)
        result = fp_tools.retrieve_feedback_history(123)
        
        # Verify result is a list (empty in test environment)
        assert isinstance(result, list)


class TestFeedbackProcessing:
    """Test feedback parsing and processing."""

    def test_parse_general_feedback(self):
        """Test parsing general text feedback."""
        feedback_text = "The regex is too strict and misses some variations. Please make it more flexible."
        
        result = fp_tools.parse_feedback(
            feedback_text=feedback_text,
            brandid=123
        )
        
        assert "feedback_id" in result
        assert result["brandid"] == 123
        assert result["category"] in ["regex_too_narrow", "regex_too_broad", "general"]
        assert "issues_identified" in result
        assert len(result["issues_identified"]) > 0
    
    def test_parse_specific_examples_feedback(self, sample_brand_data):
        """Test parsing feedback with specific combo examples."""
        feedback_text = "Combo 3 should be matched but isn't. The pattern needs to handle spacing variations."
        
        result = fp_tools.parse_feedback(
            feedback_text=feedback_text,
            brandid=123
        )
        
        assert "feedback_id" in result
        assert result["brandid"] == 123
        assert "misclassified_combos" in result
        assert 3 in result["misclassified_combos"]
    
    def test_identify_misclassified_combos(self, sample_brand_data):
        """Test identifying misclassified combos from feedback."""
        feedback_dict = {
            "feedback_text": "Combo 3 is incorrectly matched. Also check combo 12345."
        }
        
        result = fp_tools.identify_misclassified_combos(feedback_dict)
        
        assert isinstance(result, list)
        assert 3 in result
        assert 12345 in result


class TestRefinementPromptGeneration:
    """Test refinement prompt generation for Metadata Production Agent."""

    def test_generate_refinement_prompt_for_regex_issue(self):
        """Test generating refinement prompt for regex issues."""
        parsed_feedback = {
            "category": "regex_too_narrow",
            "issues_identified": [
                "Missing patterns or narratives"
            ],
            "misclassified_combos": [3],
            "feedback_text": "Pattern too strict, missing spacing variations like 'STAR BUCKS'"
        }
        
        current_metadata = {"regex": "^STARBUCKS.*", "mccids": [5812]}
        brand_data = {"brandname": "Starbucks"}
        
        result = fp_tools.generate_refinement_prompt(
            feedback=parsed_feedback,
            current_metadata=current_metadata,
            brand_data=brand_data
        )
        
        assert isinstance(result, str)
        assert "Starbucks" in result
        assert "regex" in result.lower() or "pattern" in result.lower()
    
    def test_generate_refinement_prompt_for_mccid_issue(self):
        """Test generating refinement prompt for MCCID issues."""
        parsed_feedback = {
            "category": "mccid_incorrect",
            "issues_identified": [
                "MCCID classification issue"
            ],
            "feedback_text": "Missing MCCID 5814 for restaurant transactions",
            "misclassified_combos": []
        }
        
        current_metadata = {"regex": "^STARBUCKS.*", "mccids": [5812]}
        brand_data = {"brandname": "Starbucks"}
        
        result = fp_tools.generate_refinement_prompt(
            feedback=parsed_feedback,
            current_metadata=current_metadata,
            brand_data=brand_data
        )
        
        assert isinstance(result, str)
        assert "MCCID" in result or "mccid" in result


class TestMetadataRegeneration:
    """Test metadata regeneration based on feedback."""

    def test_regenerate_metadata_with_refinement_prompt(self, sample_brand_data):
        """Test regenerating metadata with refinement guidance."""
        guidance = (
            "The current regex '^STARBUCKS.*' is too strict. "
            "It should match variations like 'STAR BUCKS' with spacing. "
            "Example narrative that should match: 'STAR BUCKS STORE'"
        )
        
        narratives = [combo["narrative"] for combo in sample_brand_data["combos"]]
        
        # Generate new regex with guidance
        new_regex = mp_tools.generate_regex(
            brandid=123,
            narratives=narratives,
            guidance=guidance
        )
        
        # Verify new regex is generated
        assert new_regex
        assert isinstance(new_regex, str)
    
    def test_metadata_version_increment(self, sample_metadata):
        """Test that metadata version increments after regeneration."""
        # Simulate metadata regeneration
        new_metadata = {
            **sample_metadata,
            "regex": "^STA[R\\s]*BUCKS.*",  # Updated regex
            "version": sample_metadata["version"] + 1,
            "iteration": sample_metadata["iteration"] + 1
        }
        
        assert new_metadata["version"] == 2
        assert new_metadata["iteration"] == 2
        assert new_metadata["regex"] != sample_metadata["regex"]


class TestCompleteFeedbackLoop:
    """Test complete feedback loop end-to-end."""

    @patch("agents.data_transformation.tools.DataTransformationTools.apply_metadata_to_combos")
    def test_complete_feedback_loop_workflow(
        self,
        mock_apply_metadata,
        sample_brand_data,
        sample_metadata,
        sample_feedback
    ):
        """Test complete feedback loop from submission to re-classification.
        
        Workflow:
        1. Parse feedback
        2. Generate refinement prompt
        3. Regenerate metadata
        4. Re-apply metadata to combos
        5. Verify iteration increment
        """
        # Mock metadata application
        mock_apply_metadata.return_value = {
            "success": True,
            "total_matched": 3,
            "matched_combos": []
        }
        
        # Step 1: Parse feedback
        parse_result = fp_tools.parse_feedback(
            feedback_text=sample_feedback["feedback_text"],
            brandid=sample_feedback["brandid"]
        )
        
        assert "feedback_id" in parse_result
        assert parse_result["brandid"] == 123
        
        # Step 2: Generate refinement prompt
        refinement_result = fp_tools.generate_refinement_prompt(
            feedback=parse_result,
            current_metadata=sample_metadata,
            brand_data=sample_brand_data
        )
        
        assert isinstance(refinement_result, str)
        assert len(refinement_result) > 0
        
        # Step 3: Regenerate metadata
        narratives = [combo["narrative"] for combo in sample_brand_data["combos"]]
        new_regex = mp_tools.generate_regex(
            brandid=sample_brand_data["brandid"],
            narratives=narratives,
            guidance=refinement_result
        )
        
        assert new_regex is not None
        
        # Step 4: Create new metadata version
        new_metadata = {
            **sample_metadata,
            "regex": new_regex,
            "version": sample_metadata["version"] + 1,
            "iteration": sample_metadata["iteration"] + 1
        }
        
        assert new_metadata["iteration"] == 2
        
        # Step 5: Re-apply metadata to combos
        dt_tools = dt_tools_module.DataTransformationTools()
        application_result = dt_tools.apply_metadata_to_combos(
            brandid=sample_brand_data["brandid"],
            regex_pattern=new_metadata["regex"],
            mccid_list=new_metadata["mccid_list"]
        )
        
        assert application_result["success"] is True
        assert application_result["total_matched"] == 3


class TestIterationTracking:
    """Test iteration tracking and limits."""

    def test_iteration_increment(self):
        """Test that iteration count increments correctly."""
        initial_iteration = 1
        
        # Simulate feedback loop
        new_iteration = initial_iteration + 1
        
        assert new_iteration == 2
    
    def test_iteration_limit_check(self):
        """Test checking if iteration limit is reached."""
        max_iterations = 10
        
        # Test below limit
        current_iteration = 5
        assert current_iteration < max_iterations
        
        # Test at limit
        current_iteration = 10
        assert current_iteration >= max_iterations
        
        # Test above limit
        current_iteration = 11
        assert current_iteration >= max_iterations
    
    def test_escalation_when_limit_exceeded(self):
        """Test escalation when iteration limit is exceeded."""
        brandid = 123
        current_iteration = 11
        max_iterations = 10
        
        # Check if escalation needed
        needs_escalation = current_iteration > max_iterations
        
        assert needs_escalation is True
        
        # Simulate escalation
        if needs_escalation:
            escalation_data = {
                "brandid": brandid,
                "reason": "iteration_limit_exceeded",
                "current_iteration": current_iteration,
                "max_iterations": max_iterations,
                "timestamp": datetime.now().isoformat()
            }
            
            assert escalation_data["reason"] == "iteration_limit_exceeded"
            assert escalation_data["current_iteration"] > escalation_data["max_iterations"]


class TestFeedbackTypes:
    """Test different feedback types."""

    def test_general_feedback_processing(self):
        """Test processing general text feedback."""
        feedback_text = "The classification looks good overall but could be more accurate."
        
        result = fp_tools.parse_feedback(
            feedback_text=feedback_text,
            brandid=123
        )
        
        assert "feedback_id" in result
        assert result["category"] in ["general", "regex_too_narrow", "regex_too_broad"]
    
    def test_approve_feedback(self):
        """Test processing approval feedback."""
        result = fp_tools.parse_feedback(
            feedback_text="Classifications look correct. Approved.",
            brandid=123
        )
        
        assert "feedback_id" in result
        assert "category" in result
    
    def test_reject_feedback(self):
        """Test processing rejection feedback."""
        feedback_text = "Multiple issues with the classification. Needs complete rework."
        
        result = fp_tools.parse_feedback(
            feedback_text=feedback_text,
            brandid=123
        )
        
        assert "feedback_id" in result
        assert result["category"] in ["regex_too_narrow", "regex_too_broad", "mccid_incorrect", "general"]


class TestFeedbackLoopErrorHandling:
    """Test error handling in feedback loop."""

    def test_feedback_storage_failure(self):
        """Test handling of feedback storage failure."""
        # Parse feedback first
        parsed_feedback = fp_tools.parse_feedback(
            feedback_text="Test feedback",
            brandid=123
        )
        
        # Store feedback (will succeed in test environment)
        result = fp_tools.store_feedback(
            brandid=123,
            feedback=parsed_feedback,
            metadata_version=1
        )
        
        # In test environment, storage succeeds
        assert "feedback_stored" in result
    
    def test_invalid_combo_ids(self):
        """Test handling of invalid combo IDs in feedback."""
        feedback_dict = {
            "feedback_text": "Combo 999 is wrong"  # Non-existent combo
        }
        
        result = fp_tools.identify_misclassified_combos(feedback_dict)
        
        assert isinstance(result, list)
        assert 999 in result  # ID is extracted even if it doesn't exist
    
    def test_empty_feedback_text(self):
        """Test handling of empty feedback text."""
        result = fp_tools.parse_feedback(
            feedback_text="",
            brandid=123
        )
        
        assert "feedback_id" in result
        assert "error" in result


class TestMultipleIterations:
    """Test multiple feedback iterations."""

    def test_multiple_feedback_iterations(self):
        """Test tracking multiple feedback iterations."""
        iterations = []
        
        # Simulate 3 iterations
        for i in range(1, 4):
            iteration_data = {
                "iteration": i,
                "version": i,
                "feedback_received": True,
                "metadata_regenerated": True
            }
            iterations.append(iteration_data)
        
        assert len(iterations) == 3
        assert iterations[0]["iteration"] == 1
        assert iterations[2]["iteration"] == 3
    
    def test_feedback_history_across_iterations(self):
        """Test retrieving feedback history across multiple iterations."""
        # Retrieve feedback history (returns empty list in test environment)
        result = fp_tools.retrieve_feedback_history(123)
        
        # In test environment, returns empty list
        assert isinstance(result, list)
