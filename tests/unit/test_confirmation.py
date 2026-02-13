"""
Unit Tests for Confirmation Agent

Tests the combo review and confirmation decision tools.
"""

import pytest
from agents.confirmation.tools import (
    review_matched_combos,
    confirm_combo,
    exclude_combo,
    flag_for_human_review
)


class TestReviewMatchedCombos:
    """Test the review_matched_combos tool."""
    
    def test_review_with_no_combos(self):
        """Test review with empty combo list."""
        result = review_matched_combos(
            brandid=1,
            brandname="TestBrand",
            metadata={"regex": "^TEST.*", "mccids": [5812]},
            matched_combos=[],
            mcc_table=[]
        )
        
        assert result["brandid"] == 1
        assert result["total_matched"] == 0
        assert result["likely_valid"] == []
        assert result["likely_false_positive"] == []
        assert result["ambiguous"] == []
    
    def test_review_specific_brand_high_confidence(self):
        """Test review with specific brand name and business context."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage", "mcc_desc": "Eating Places"}
        ]
        
        matched_combos = [
            {
                "ccid": 1,
                "narrative": "STARBUCKS STORE #1234",
                "mccid": 5812
            }
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Starbucks",
            metadata={"regex": "^STARBUCKS.*", "mccids": [5812], "sector": "Food & Beverage"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        assert 1 in result["likely_valid"]
        assert len(result["likely_false_positive"]) == 0
        assert len(result["analysis"]) == 1
        assert result["analysis"][0]["confidence"] >= 0.8
        assert result["analysis"][0]["recommendation"] == "confirm"
    
    def test_review_common_word_without_context(self):
        """Test review with common word brand name without business context."""
        mcc_table = [
            {"mccid": 5499, "sector": "Food Stores", "mcc_desc": "Misc Food Stores"}
        ]
        
        matched_combos = [
            {
                "ccid": 1,
                "narrative": "APPLE ORCHARD",
                "mccid": 5499
            }
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Apple",
            metadata={"regex": "^APPLE.*", "mccids": [5732], "sector": "Technology"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        assert 1 in result["likely_false_positive"]
        assert len(result["analysis"]) == 1
        assert result["analysis"][0]["confidence"] <= 0.4
        assert result["analysis"][0]["recommendation"] == "exclude"
    
    def test_review_common_word_with_business_context(self):
        """Test review with common word but strong business context."""
        mcc_table = [
            {"mccid": 5732, "sector": "Technology", "mcc_desc": "Electronics Stores"}
        ]
        
        matched_combos = [
            {
                "ccid": 1,
                "narrative": "APPLE STORE #123",
                "mccid": 5732
            }
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Apple",
            metadata={"regex": "^APPLE.*", "mccids": [5732], "sector": "Technology"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        assert 1 in result["likely_valid"]
        assert len(result["analysis"]) == 1
        assert result["analysis"][0]["confidence"] >= 0.8
    
    def test_review_sector_mismatch(self):
        """Test review with MCCID sector mismatch."""
        mcc_table = [
            {"mccid": 5541, "sector": "Fuel", "mcc_desc": "Service Stations"}
        ]
        
        matched_combos = [
            {
                "ccid": 1,
                "narrative": "STARBUCKS #123",
                "mccid": 5541
            }
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Starbucks",
            metadata={"regex": "^STARBUCKS.*", "mccids": [5541], "sector": "Food & Beverage"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        # Should be ambiguous or low confidence due to sector mismatch
        analysis = result["analysis"][0]
        assert "sector mismatch" in " ".join(analysis["factors"]).lower()
    
    def test_review_contradictory_terms(self):
        """Test review with contradictory terms in narrative."""
        mcc_table = [
            {"mccid": 5499, "sector": "Food Stores", "mcc_desc": "Misc Food Stores"}
        ]
        
        matched_combos = [
            {
                "ccid": 1,
                "narrative": "APPLE ORCHARD FARM",
                "mccid": 5499
            }
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Apple",
            metadata={"regex": "^APPLE.*", "mccids": [5732], "sector": "Technology"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        assert 1 in result["likely_false_positive"]
        analysis = result["analysis"][0]
        assert "contradictory" in " ".join(analysis["factors"]).lower()
    
    def test_review_multiple_combos_mixed_confidence(self):
        """Test review with multiple combos of varying confidence."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage", "mcc_desc": "Eating Places"},
            {"mccid": 5499, "sector": "Food Stores", "mcc_desc": "Misc Food Stores"}
        ]
        
        matched_combos = [
            {"ccid": 1, "narrative": "STARBUCKS STORE #123", "mccid": 5812},
            {"ccid": 2, "narrative": "STARBUCKS CAFE", "mccid": 5812},
            {"ccid": 3, "narrative": "STARBURST CANDY", "mccid": 5499},
            {"ccid": 4, "narrative": "STARBUCKS", "mccid": 5812}
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Starbucks",
            metadata={"regex": "^STARB.*", "mccids": [5812], "sector": "Food & Beverage"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 4
        # Should have some valid, some false positives
        assert len(result["likely_valid"]) > 0
        # STARBURST CANDY should be flagged as issue
        assert len(result["analysis"]) == 4
    
    def test_review_short_narrative(self):
        """Test review with very short narrative."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage", "mcc_desc": "Eating Places"}
        ]
        
        matched_combos = [
            {"ccid": 1, "narrative": "SBUX", "mccid": 5812}
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Starbucks",
            metadata={"regex": "^S(TARBUCKS|BUX).*", "mccids": [5812], "sector": "Food & Beverage"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        analysis = result["analysis"][0]
        # Short narrative should slightly reduce confidence
        assert any("short" in factor.lower() for factor in analysis["factors"])
    
    def test_review_detailed_narrative(self):
        """Test review with detailed narrative."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage", "mcc_desc": "Eating Places"}
        ]
        
        matched_combos = [
            {"ccid": 1, "narrative": "STARBUCKS COFFEE STORE #1234 LONDON", "mccid": 5812}
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Starbucks",
            metadata={"regex": "^STARBUCKS.*", "mccids": [5812], "sector": "Food & Beverage"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        analysis = result["analysis"][0]
        # Detailed narrative should boost confidence
        assert any("detailed" in factor.lower() for factor in analysis["factors"])


class TestConfirmCombo:
    """Test the confirm_combo tool."""
    
    def test_confirm_combo_basic(self):
        """Test basic combo confirmation."""
        result = confirm_combo(ccid=1, brandid=100)
        
        assert result["action"] == "confirm"
        assert result["ccid"] == 1
        assert result["brandid"] == 100
        assert "reason" in result
        assert "timestamp" in result
    
    def test_confirm_combo_with_reason(self):
        """Test combo confirmation with custom reason."""
        result = confirm_combo(
            ccid=1,
            brandid=100,
            reason="High confidence match with business context"
        )
        
        assert result["action"] == "confirm"
        assert result["reason"] == "High confidence match with business context"


class TestExcludeCombo:
    """Test the exclude_combo tool."""
    
    def test_exclude_combo_with_reason(self):
        """Test combo exclusion with reason."""
        result = exclude_combo(
            ccid=1,
            brandid=100,
            reason="MCCID sector mismatch - likely different business"
        )
        
        assert result["action"] == "exclude"
        assert result["ccid"] == 1
        assert result["brandid"] == 100
        assert result["reason"] == "MCCID sector mismatch - likely different business"
        assert "timestamp" in result
    
    def test_exclude_combo_without_reason(self):
        """Test combo exclusion without explicit reason."""
        result = exclude_combo(ccid=1, brandid=100, reason="")
        
        assert result["action"] == "exclude"
        assert "false positive" in result["reason"].lower()


class TestFlagForHumanReview:
    """Test the flag_for_human_review tool."""
    
    def test_flag_combo_with_reason(self):
        """Test flagging combo for human review."""
        result = flag_for_human_review(
            ccid=1,
            brandid=100,
            reason="Ambiguous match - common word without clear context"
        )
        
        assert result["action"] == "flag_for_review"
        assert result["ccid"] == 1
        assert result["brandid"] == 100
        assert result["requires_human_review"] is True
        assert result["reason"] == "Ambiguous match - common word without clear context"
        assert "timestamp" in result
    
    def test_flag_combo_without_reason(self):
        """Test flagging combo without explicit reason."""
        result = flag_for_human_review(ccid=1, brandid=100, reason="")
        
        assert result["action"] == "flag_for_review"
        assert result["requires_human_review"] is True
        assert "ambiguous" in result["reason"].lower()


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_review_with_missing_mcc_data(self):
        """Test review when MCC data is incomplete."""
        mcc_table = []  # Empty MCC table
        
        matched_combos = [
            {"ccid": 1, "narrative": "STARBUCKS #123", "mccid": 5812}
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Starbucks",
            metadata={"regex": "^STARBUCKS.*", "mccids": [5812], "sector": "Food & Beverage"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        # Should still work but with reduced confidence
        assert len(result["analysis"]) == 1
    
    def test_review_with_missing_narrative(self):
        """Test review when combo has missing narrative."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage", "mcc_desc": "Eating Places"}
        ]
        
        matched_combos = [
            {"ccid": 1, "narrative": "", "mccid": 5812}
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Starbucks",
            metadata={"regex": "^STARBUCKS.*", "mccids": [5812], "sector": "Food & Beverage"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        # Should handle gracefully
        assert len(result["analysis"]) == 1
    
    def test_review_shell_brand_gas_station(self):
        """Test Shell brand with gas station context."""
        mcc_table = [
            {"mccid": 5541, "sector": "Fuel", "mcc_desc": "Service Stations"}
        ]
        
        matched_combos = [
            {"ccid": 1, "narrative": "SHELL STATION 123", "mccid": 5541}
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Shell",
            metadata={"regex": "^SHELL.*", "mccids": [5541], "sector": "Fuel"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        assert 1 in result["likely_valid"]
    
    def test_review_shell_brand_seafood(self):
        """Test Shell brand with seafood context (false positive)."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage", "mcc_desc": "Eating Places"}
        ]
        
        matched_combos = [
            {"ccid": 1, "narrative": "SHELL SEAFOOD MARKET", "mccid": 5812}
        ]
        
        result = review_matched_combos(
            brandid=1,
            brandname="Shell",
            metadata={"regex": "^SHELL.*", "mccids": [5541], "sector": "Fuel"},
            matched_combos=matched_combos,
            mcc_table=mcc_table
        )
        
        assert result["total_matched"] == 1
        # Should detect contradictory term and sector mismatch
        assert 1 in result["likely_false_positive"]
        analysis = result["analysis"][0]
        assert analysis["confidence"] < 0.5
