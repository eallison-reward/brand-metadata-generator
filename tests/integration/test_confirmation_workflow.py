"""Integration tests for confirmation workflow.

This module tests the end-to-end confirmation workflow where the Confirmation
Agent reviews matched combos and excludes false positives.
"""

import pytest
from unittest.mock import Mock, patch

from agents.confirmation import tools as confirmation_tools


@pytest.fixture
def specific_brand_scenario():
    """Scenario with a specific brand name (high confidence matches)."""
    return {
        "brandid": 100,
        "brandname": "Starbucks",
        "metadata": {
            "regex": "^STARBUCKS",
            "mccids": [5812],
            "sector": "Food & Beverage"
        },
        "matched_combos": [
            {
                "ccid": 1,
                "bankid": 1,
                "narrative": "STARBUCKS #12345",
                "mccid": 5812
            },
            {
                "ccid": 2,
                "bankid": 1,
                "narrative": "STARBUCKS COFFEE STORE",
                "mccid": 5812
            },
            {
                "ccid": 3,
                "bankid": 2,
                "narrative": "STARBUCKS CAFE",
                "mccid": 5812
            }
        ],
        "mcc_table": [
            {
                "mccid": 5812,
                "mcc_desc": "Eating Places",
                "sector": "Food & Beverage"
            }
        ]
    }


@pytest.fixture
def ambiguous_brand_scenario():
    """Scenario with ambiguous brand name (Apple - tech vs fruit)."""
    return {
        "brandid": 200,
        "brandname": "Apple",
        "metadata": {
            "regex": "\\bAPPLE\\b",
            "mccids": [5732, 5734],
            "sector": "Electronics"
        },
        "matched_combos": [
            {
                "ccid": 10,
                "bankid": 1,
                "narrative": "APPLE STORE #123",
                "mccid": 5732
            },
            {
                "ccid": 11,
                "bankid": 1,
                "narrative": "APPLE ORCHARD",
                "mccid": 5411
            },
            {
                "ccid": 12,
                "bankid": 2,
                "narrative": "APPLE",
                "mccid": 5732
            },
            {
                "ccid": 13,
                "bankid": 2,
                "narrative": "APPLE FRUIT MARKET",
                "mccid": 5411
            }
        ],
        "mcc_table": [
            {
                "mccid": 5732,
                "mcc_desc": "Electronics Stores",
                "sector": "Electronics"
            },
            {
                "mccid": 5411,
                "mcc_desc": "Grocery Stores",
                "sector": "Grocery"
            }
        ]
    }


@pytest.fixture
def shell_brand_scenario():
    """Scenario with Shell brand (fuel vs seafood ambiguity)."""
    return {
        "brandid": 300,
        "brandname": "Shell",
        "metadata": {
            "regex": "^SHELL",
            "mccids": [5541, 5542],
            "sector": "Fuel"
        },
        "matched_combos": [
            {
                "ccid": 20,
                "bankid": 1,
                "narrative": "SHELL STATION 456",
                "mccid": 5541
            },
            {
                "ccid": 21,
                "bankid": 1,
                "narrative": "SHELL FUEL",
                "mccid": 5541
            },
            {
                "ccid": 22,
                "bankid": 2,
                "narrative": "SHELL SEAFOOD RESTAURANT",
                "mccid": 5812
            },
            {
                "ccid": 23,
                "bankid": 2,
                "narrative": "SHELL BEACH SHOP",
                "mccid": 5999
            }
        ],
        "mcc_table": [
            {
                "mccid": 5541,
                "mcc_desc": "Service Stations",
                "sector": "Fuel"
            },
            {
                "mccid": 5542,
                "mcc_desc": "Automated Fuel Dispensers",
                "sector": "Fuel"
            },
            {
                "mccid": 5812,
                "mcc_desc": "Eating Places",
                "sector": "Food & Beverage"
            },
            {
                "mccid": 5999,
                "mcc_desc": "Miscellaneous Retail",
                "sector": "Retail"
            }
        ]
    }


class TestConfirmationWorkflow:
    """Test complete confirmation workflow."""

    def test_confirm_specific_brand_matches(self, specific_brand_scenario):
        """Test confirmation of matches for a specific brand name.
        
        This test verifies:
        1. All combos with specific brand name and matching sector are confirmed
        2. High confidence scores for clear matches
        3. No false positives identified
        """
        result = confirmation_tools.review_matched_combos(
            brandid=specific_brand_scenario["brandid"],
            brandname=specific_brand_scenario["brandname"],
            metadata=specific_brand_scenario["metadata"],
            matched_combos=specific_brand_scenario["matched_combos"],
            mcc_table=specific_brand_scenario["mcc_table"]
        )
        
        assert result["brandid"] == 100
        assert result["total_matched"] == 3
        
        # All should be likely valid (Starbucks is specific, not ambiguous)
        assert len(result["likely_valid"]) >= 2
        
        # Should have minimal or no false positives
        assert len(result["likely_false_positive"]) == 0
        
        # Verify analysis details
        assert len(result["analysis"]) == 3
        for analysis in result["analysis"]:
            assert "confidence" in analysis
            assert "recommendation" in analysis
            assert 0.0 <= analysis["confidence"] <= 1.0

    def test_exclude_ambiguous_brand_false_positives(self, ambiguous_brand_scenario):
        """Test exclusion of false positives for ambiguous brand name.
        
        This test verifies:
        1. Combos with contradictory terms are identified as false positives
        2. Sector mismatches reduce confidence
        3. Ambiguous matches are flagged appropriately
        """
        result = confirmation_tools.review_matched_combos(
            brandid=ambiguous_brand_scenario["brandid"],
            brandname=ambiguous_brand_scenario["brandname"],
            metadata=ambiguous_brand_scenario["metadata"],
            matched_combos=ambiguous_brand_scenario["matched_combos"],
            mcc_table=ambiguous_brand_scenario["mcc_table"]
        )
        
        assert result["brandid"] == 200
        assert result["total_matched"] == 4
        
        # Should have at least one likely valid (APPLE STORE with electronics MCCID)
        assert len(result["likely_valid"]) >= 1
        
        # Should identify false positives (APPLE ORCHARD, APPLE FRUIT MARKET)
        assert len(result["likely_false_positive"]) >= 1
        
        # Verify false positives have low confidence
        for analysis in result["analysis"]:
            if analysis["ccid"] in result["likely_false_positive"]:
                assert analysis["confidence"] <= 0.4
                assert analysis["recommendation"] == "exclude"

    def test_sector_mismatch_detection(self, shell_brand_scenario):
        """Test detection of sector mismatches in confirmation.
        
        This test verifies:
        1. Combos with matching sector have higher confidence
        2. Combos with mismatched sector have lower confidence
        3. Contradictory terms (SEAFOOD, BEACH) are detected
        """
        result = confirmation_tools.review_matched_combos(
            brandid=shell_brand_scenario["brandid"],
            brandname=shell_brand_scenario["brandname"],
            metadata=shell_brand_scenario["metadata"],
            matched_combos=shell_brand_scenario["matched_combos"],
            mcc_table=shell_brand_scenario["mcc_table"]
        )
        
        assert result["brandid"] == 300
        assert result["total_matched"] == 4
        
        # Fuel station combos should be likely valid
        fuel_combos = [20, 21]  # SHELL STATION, SHELL FUEL
        for ccid in fuel_combos:
            if ccid in result["likely_valid"]:
                # Find analysis for this combo
                analysis = next(a for a in result["analysis"] if a["ccid"] == ccid)
                assert analysis["confidence"] >= 0.5
        
        # Seafood/beach combos should be false positives or ambiguous
        non_fuel_combos = [22, 23]  # SHELL SEAFOOD, SHELL BEACH
        for ccid in non_fuel_combos:
            assert ccid in result["likely_false_positive"] or ccid in result["ambiguous"]

    def test_business_context_indicators(self):
        """Test that business context indicators increase confidence.
        
        This test verifies:
        1. Store numbers (#123) increase confidence
        2. Business terms (STORE, STATION) increase confidence
        3. Lack of context for common words decreases confidence
        """
        # Test with business context
        result_with_context = confirmation_tools.review_matched_combos(
            brandid=400,
            brandname="Target",
            metadata={"regex": "TARGET", "mccids": [5311], "sector": "Retail"},
            matched_combos=[
                {
                    "ccid": 30,
                    "bankid": 1,
                    "narrative": "TARGET STORE #1234",
                    "mccid": 5311
                }
            ],
            mcc_table=[
                {
                    "mccid": 5311,
                    "mcc_desc": "Department Stores",
                    "sector": "Retail"
                }
            ]
        )
        
        # Test without business context
        result_without_context = confirmation_tools.review_matched_combos(
            brandid=400,
            brandname="Target",
            metadata={"regex": "TARGET", "mccids": [5311], "sector": "Retail"},
            matched_combos=[
                {
                    "ccid": 31,
                    "bankid": 1,
                    "narrative": "TARGET",
                    "mccid": 7999
                }
            ],
            mcc_table=[
                {
                    "mccid": 7999,
                    "mcc_desc": "Recreation Services",
                    "sector": "Recreation"
                }
            ]
        )
        
        # With context should have higher confidence
        analysis_with = result_with_context["analysis"][0]
        analysis_without = result_without_context["analysis"][0]
        
        assert analysis_with["confidence"] > analysis_without["confidence"]


class TestConfirmationActions:
    """Test individual confirmation actions."""

    def test_confirm_combo_action(self):
        """Test confirming a combo belongs to a brand."""
        result = confirmation_tools.confirm_combo(
            ccid=100,
            brandid=200,
            reason="Clear match with business context"
        )
        
        assert result["action"] == "confirm"
        assert result["ccid"] == 100
        assert result["brandid"] == 200
        assert "reason" in result
        assert "timestamp" in result

    def test_exclude_combo_action(self):
        """Test excluding a combo as false positive."""
        result = confirmation_tools.exclude_combo(
            ccid=101,
            brandid=200,
            reason="Contradictory terms indicate different entity"
        )
        
        assert result["action"] == "exclude"
        assert result["ccid"] == 101
        assert result["brandid"] == 200
        assert "Contradictory" in result["reason"]
        assert "timestamp" in result

    def test_flag_for_human_review_action(self):
        """Test flagging a combo for human review."""
        result = confirmation_tools.flag_for_human_review(
            ccid=102,
            brandid=200,
            reason="Ambiguous match - common word without clear context"
        )
        
        assert result["action"] == "flag_for_review"
        assert result["ccid"] == 102
        assert result["brandid"] == 200
        assert result["requires_human_review"] is True
        assert "Ambiguous" in result["reason"]
        assert "timestamp" in result


class TestConfirmationEdgeCases:
    """Test edge cases in confirmation workflow."""

    def test_empty_matched_combos(self):
        """Test handling when no combos matched."""
        result = confirmation_tools.review_matched_combos(
            brandid=500,
            brandname="Test Brand",
            metadata={"regex": "^TEST", "mccids": [5999], "sector": "Test"},
            matched_combos=[],
            mcc_table=[]
        )
        
        assert result["brandid"] == 500
        assert result["total_matched"] == 0
        assert len(result["likely_valid"]) == 0
        assert len(result["likely_false_positive"]) == 0
        assert len(result["ambiguous"]) == 0

    def test_very_short_narrative(self):
        """Test handling of very short narratives."""
        result = confirmation_tools.review_matched_combos(
            brandid=600,
            brandname="ABC",
            metadata={"regex": "ABC", "mccids": [5999], "sector": "Retail"},
            matched_combos=[
                {
                    "ccid": 40,
                    "bankid": 1,
                    "narrative": "ABC",
                    "mccid": 5999
                }
            ],
            mcc_table=[
                {
                    "mccid": 5999,
                    "mcc_desc": "Miscellaneous Retail",
                    "sector": "Retail"
                }
            ]
        )
        
        # Very short narrative should have lower confidence
        analysis = result["analysis"][0]
        assert "short narrative" in str(analysis["factors"]).lower() or analysis["confidence"] < 0.7

    def test_detailed_narrative(self):
        """Test handling of detailed narratives."""
        result = confirmation_tools.review_matched_combos(
            brandid=700,
            brandname="Walmart",
            metadata={"regex": "WALMART", "mccids": [5411], "sector": "Retail"},
            matched_combos=[
                {
                    "ccid": 50,
                    "bankid": 1,
                    "narrative": "WALMART SUPERCENTER #1234 GROCERY DEPARTMENT",
                    "mccid": 5411
                }
            ],
            mcc_table=[
                {
                    "mccid": 5411,
                    "mcc_desc": "Grocery Stores",
                    "sector": "Retail"
                }
            ]
        )
        
        # Detailed narrative with business context should have high confidence
        analysis = result["analysis"][0]
        assert analysis["confidence"] >= 0.7
        assert analysis["recommendation"] in ["confirm", "human_review"]


class TestConfirmationIntegrationWithMetadata:
    """Test integration between metadata application and confirmation."""

    def test_confirmation_after_metadata_application(self):
        """Test confirmation workflow after metadata has been applied to combos.
        
        This test verifies the complete flow:
        1. Metadata (regex + MCCIDs) is applied to combos
        2. Matched combos are reviewed by Confirmation Agent
        3. False positives are identified and excluded
        4. Valid matches are confirmed
        """
        # Simulate metadata application results
        brand_metadata = {
            "brandid": 800,
            "brandname": "Amazon",
            "regex": "\\bAMAZON\\b",
            "mccids": [5942, 5999],
            "sector": "E-commerce"
        }
        
        # Combos that matched the regex and MCCID
        matched_combos = [
            {
                "ccid": 60,
                "bankid": 1,
                "narrative": "AMAZON.COM",
                "mccid": 5942
            },
            {
                "ccid": 61,
                "bankid": 1,
                "narrative": "AMAZON PRIME",
                "mccid": 5942
            },
            {
                "ccid": 62,
                "bankid": 2,
                "narrative": "AMAZON RAINFOREST TOURS",
                "mccid": 7999
            }
        ]
        
        mcc_table = [
            {
                "mccid": 5942,
                "mcc_desc": "Book Stores",
                "sector": "E-commerce"
            },
            {
                "mccid": 7999,
                "mcc_desc": "Recreation Services",
                "sector": "Recreation"
            }
        ]
        
        # Review matched combos
        result = confirmation_tools.review_matched_combos(
            brandid=brand_metadata["brandid"],
            brandname=brand_metadata["brandname"],
            metadata=brand_metadata,
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 3
        
        # Amazon.com and Amazon Prime should be valid
        assert len(result["likely_valid"]) >= 1
        
        # Amazon Rainforest Tours should be false positive or ambiguous
        rainforest_ccid = 62
        assert rainforest_ccid in result["likely_false_positive"] or rainforest_ccid in result["ambiguous"]
