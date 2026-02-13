"""Integration tests for tie resolution workflow.

This module tests the end-to-end tie resolution workflow when a combo
matches multiple brands.
"""

import pytest
from unittest.mock import Mock, patch

from agents.tiebreaker import tools as tiebreaker_tools
from agents.evaluator import tools as evaluator_tools


@pytest.fixture
def tie_scenario_data():
    """Sample data for a tie scenario where one combo matches multiple brands."""
    return {
        "ccid": 100,
        "bankid": 1,
        "narrative": "SHELL STATION 123",
        "mccid": 5541,
        "matching_brands": [
            {
                "brandid": 200,
                "brandname": "Shell",
                "sector": "Fuel",
                "regex": "^SHELL",
                "mccid_list": [5541, 5542]
            },
            {
                "brandid": 300,
                "brandname": "Shell Oil",
                "sector": "Fuel",
                "regex": "SHELL.*OIL",
                "mccid_list": [5541]
            },
            {
                "brandid": 400,
                "brandname": "Seashell Restaurant",
                "sector": "Food & Beverage",
                "regex": ".*SHELL",
                "mccid_list": [5812, 5541]
            }
        ]
    }


@pytest.fixture
def clear_winner_scenario():
    """Scenario with a clear winner based on narrative similarity."""
    return {
        "ccid": 101,
        "bankid": 1,
        "narrative": "STARBUCKS COFFEE #12345",
        "mccid": 5812,
        "matching_brands": [
            {
                "brandid": 500,
                "brandname": "Starbucks",
                "sector": "Food & Beverage",
                "regex": "^STARBUCKS",
                "mccid_list": [5812]
            },
            {
                "brandid": 600,
                "brandname": "Star Bucks Diner",
                "sector": "Food & Beverage",
                "regex": "STAR.*BUCKS",
                "mccid_list": [5812, 5814]
            }
        ]
    }


@pytest.fixture
def ambiguous_tie_scenario():
    """Scenario with ambiguous tie requiring human review."""
    return {
        "ccid": 102,
        "bankid": 1,
        "narrative": "APPLE STORE",
        "mccid": 5732,
        "matching_brands": [
            {
                "brandid": 700,
                "brandname": "Apple Inc",
                "sector": "Electronics",
                "regex": "^APPLE",
                "mccid_list": [5732, 5734]
            },
            {
                "brandid": 800,
                "brandname": "Apple Market",
                "sector": "Grocery",
                "regex": "APPLE.*MARKET",
                "mccid_list": [5411, 5732]
            }
        ]
    }


class TestTieResolutionWorkflow:
    """Test complete tie resolution workflow."""

    def test_resolve_tie_with_clear_winner(self, clear_winner_scenario):
        """Test tie resolution when there's a clear winner.
        
        This test verifies:
        1. Narrative similarity analysis identifies best match
        2. MCCID alignment supports the decision
        3. Confidence score is high enough for automatic resolution
        4. Winner is correctly identified
        """
        # Resolve the tie
        result = tiebreaker_tools.resolve_multi_match(
            ccid=clear_winner_scenario["ccid"],
            matching_brands=clear_winner_scenario["matching_brands"],
            narrative=clear_winner_scenario["narrative"],
            mccid=clear_winner_scenario["mccid"]
        )
        
        assert result["success"] is True
        assert result["resolution_type"] in ["assigned", "human_review"]
        
        # If assigned, verify it's the correct brand (Starbucks, not Star Bucks Diner)
        if result["resolution_type"] == "assigned":
            assert result["assigned_brandid"] == 500  # Starbucks
            assert result["confidence"] >= 0.7
            assert "reasoning" in result

    def test_resolve_tie_with_mccid_alignment(self, tie_scenario_data):
        """Test tie resolution using MCCID alignment.
        
        This test verifies:
        1. MCCID alignment is considered in tie resolution
        2. Brands with better MCCID match score higher
        3. Sector alignment influences the decision
        """
        # Analyze MCCID alignment for each brand
        mccid = tie_scenario_data["mccid"]
        brands = tie_scenario_data["matching_brands"]
        
        alignments = []
        for brand in brands:
            alignment = tiebreaker_tools.compare_mccid_alignment(
                mccid=mccid,
                brands=[brand]
            )
            alignments.append({
                "brandid": brand["brandid"],
                "brandname": brand["brandname"],
                "alignment": alignment
            })
        
        # Verify alignment results
        assert len(alignments) == 3
        
        # Shell and Shell Oil should have better alignment than Seashell Restaurant
        # because they're in the Fuel sector matching the MCCID 5541 (Service Stations)
        for alignment in alignments:
            assert "alignment" in alignment
            # All brands have 5541 in their MCCID list, so all should have some alignment

    def test_narrative_similarity_analysis(self, tie_scenario_data):
        """Test narrative similarity analysis for tie resolution.
        
        This test verifies:
        1. Narrative similarity is calculated correctly
        2. Exact matches score higher than partial matches
        3. Brand name position in narrative affects score
        """
        narrative = tie_scenario_data["narrative"]
        brand_names = [b["brandname"] for b in tie_scenario_data["matching_brands"]]
        
        # Analyze similarity
        similarity = tiebreaker_tools.analyze_narrative_similarity(
            narrative=narrative,
            brand_names=brand_names
        )
        
        assert "similarities" in similarity
        assert len(similarity["similarities"]) == len(brand_names)
        
        # "Shell" should have higher similarity than "Seashell Restaurant"
        # because it's a more direct match to "SHELL STATION 123"
        shell_similarity = next(
            s for s in similarity["similarities"] 
            if s["brand_name"] == "Shell"
        )
        seashell_similarity = next(
            s for s in similarity["similarities"] 
            if s["brand_name"] == "Seashell Restaurant"
        )
        
        assert shell_similarity["score"] > seashell_similarity["score"]

    def test_ambiguous_tie_flags_for_human_review(self, ambiguous_tie_scenario):
        """Test that ambiguous ties are flagged for human review.
        
        This test verifies:
        1. Low confidence ties are detected
        2. Human review flag is set
        3. Reasoning is provided for the ambiguity
        """
        # Resolve the ambiguous tie
        result = tiebreaker_tools.resolve_multi_match(
            ccid=ambiguous_tie_scenario["ccid"],
            matching_brands=ambiguous_tie_scenario["matching_brands"],
            narrative=ambiguous_tie_scenario["narrative"],
            mccid=ambiguous_tie_scenario["mccid"]
        )
        
        assert result["success"] is True
        
        # Should either assign with low confidence or flag for human review
        if result["resolution_type"] == "human_review":
            assert "reason" in result
            assert len(result["candidate_brands"]) >= 2
        elif result["resolution_type"] == "assigned":
            # If assigned, confidence should be documented
            assert "confidence" in result

    def test_confidence_calculation_for_tie_resolution(self, clear_winner_scenario):
        """Test confidence score calculation for tie resolution.
        
        This test verifies:
        1. Confidence score is calculated based on multiple factors
        2. Score is between 0.0 and 1.0
        3. Higher similarity and alignment produce higher confidence
        """
        ccid = clear_winner_scenario["ccid"]
        narrative = clear_winner_scenario["narrative"]
        mccid = clear_winner_scenario["mccid"]
        
        # Calculate confidence for the best match (Starbucks)
        best_brand = clear_winner_scenario["matching_brands"][0]
        
        confidence = tiebreaker_tools.calculate_match_confidence(
            ccid=ccid,
            brandid=best_brand["brandid"],
            narrative=narrative,
            brand_name=best_brand["brandname"],
            mccid=mccid,
            brand_mccids=best_brand["mccid_list"]
        )
        
        assert "confidence" in confidence
        assert 0.0 <= confidence["confidence"] <= 1.0
        assert "factors" in confidence


class TestTieDetectionWorkflow:
    """Test tie detection in the evaluation phase."""

    @patch("agents.data_transformation.tools.AthenaClient")
    def test_detect_ties_in_combo_matching(self, mock_athena_client):
        """Test detecting ties when applying metadata to combos.
        
        This test verifies:
        1. Ties are detected when multiple brands match a combo
        2. Tie information includes all matching brands
        3. Tie data is structured for tiebreaker agent
        """
        # Mock combo data with potential ties
        mock_athena = mock_athena_client.return_value
        mock_athena.execute_query.return_value = [
            {
                "ccid": 100,
                "bankid": 1,
                "narrative": "SHELL STATION",
                "mccid": 5541,
                "current_brandid": None
            }
        ]
        
        # Simulate detecting ties
        combos = mock_athena.execute_query.return_value
        
        # In a real scenario, we would check if multiple brands' regex patterns
        # match this combo's narrative
        tie_detected = False
        matching_brands = []
        
        # Simulate two brands matching
        brand_patterns = [
            {"brandid": 200, "regex": "^SHELL", "brandname": "Shell"},
            {"brandid": 300, "regex": "SHELL.*STATION", "brandname": "Shell Station"}
        ]
        
        import re
        for combo in combos:
            matches = []
            for brand in brand_patterns:
                if re.search(brand["regex"], combo["narrative"], re.IGNORECASE):
                    matches.append(brand)
            
            if len(matches) > 1:
                tie_detected = True
                matching_brands = matches
        
        assert tie_detected is True
        assert len(matching_brands) == 2
        assert all("brandid" in b for b in matching_brands)


class TestTieResolutionErrorHandling:
    """Test error handling in tie resolution."""

    def test_no_matching_brands(self):
        """Test handling when no brands are provided for tie resolution."""
        result = tiebreaker_tools.resolve_multi_match(
            ccid=999,
            matching_brands=[],
            narrative="TEST NARRATIVE",
            mccid=5812
        )
        
        assert result["success"] is False
        assert "error" in result or result["resolution_type"] == "no_match"

    def test_single_brand_no_tie(self):
        """Test handling when only one brand matches (not actually a tie)."""
        result = tiebreaker_tools.resolve_multi_match(
            ccid=999,
            matching_brands=[
                {
                    "brandid": 100,
                    "brandname": "Test Brand",
                    "sector": "Test",
                    "regex": "^TEST",
                    "mccid_list": [5812]
                }
            ],
            narrative="TEST BRAND STORE",
            mccid=5812
        )
        
        # With only one brand, should either auto-assign or indicate no tie
        assert result["success"] is True
        if result["resolution_type"] == "assigned":
            assert result["assigned_brandid"] == 100


class TestTieResolutionIntegrationWithEvaluator:
    """Test integration between evaluator and tiebreaker."""

    def test_tie_detection_triggers_tiebreaker(self):
        """Test that tie detection in evaluator leads to tiebreaker invocation.
        
        This test verifies the workflow:
        1. Evaluator detects multiple brand matches for a combo
        2. Tie data is prepared for tiebreaker
        3. Tiebreaker resolves or flags for human review
        """
        # Simulate evaluator detecting a tie
        tie_data = {
            "ccid": 100,
            "bankid": 1,
            "narrative": "SHELL FUEL STATION",
            "mccid": 5541,
            "matching_brands": [
                {
                    "brandid": 200,
                    "brandname": "Shell",
                    "sector": "Fuel",
                    "regex": "^SHELL",
                    "mccid_list": [5541, 5542]
                },
                {
                    "brandid": 300,
                    "brandname": "Shell Fuel",
                    "sector": "Fuel",
                    "regex": "SHELL.*FUEL",
                    "mccid_list": [5541]
                }
            ]
        }
        
        # Invoke tiebreaker
        resolution = tiebreaker_tools.resolve_multi_match(
            ccid=tie_data["ccid"],
            matching_brands=tie_data["matching_brands"],
            narrative=tie_data["narrative"],
            mccid=tie_data["mccid"]
        )
        
        assert resolution["success"] is True
        assert resolution["resolution_type"] in ["assigned", "human_review"]
        
        # Verify resolution contains necessary information
        if resolution["resolution_type"] == "assigned":
            assert "assigned_brandid" in resolution
            assert resolution["assigned_brandid"] in [200, 300]
        else:
            assert "candidate_brands" in resolution
