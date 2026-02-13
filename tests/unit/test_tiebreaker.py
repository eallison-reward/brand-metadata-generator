"""
Unit Tests for Tiebreaker Agent

Tests the tie resolution and decision logic tools.
"""

import pytest
from agents.tiebreaker.tools import (
    resolve_multi_match,
    analyze_narrative_similarity,
    compare_mccid_alignment,
    calculate_match_confidence
)


class TestResolveMultiMatch:
    """Test the resolve_multi_match tool."""
    
    def test_resolve_with_no_brands(self):
        """Test resolution with empty brand list."""
        result = resolve_multi_match(
            ccid=1,
            matching_brands=[],
            combo_data={"narrative": "TEST", "mccid": 5812}
        )
        
        assert result["resolution_type"] == "error"
        assert result["requires_human_review"] is True
    
    def test_resolve_with_single_brand(self):
        """Test resolution with only one brand (no tie)."""
        brands = [
            {"brandid": 1, "brandname": "Starbucks", "sector": "Food & Beverage",
             "metadata": {"regex": "^STARBUCKS.*", "mccids": [5812]}}
        ]
        
        result = resolve_multi_match(
            ccid=1,
            matching_brands=brands,
            combo_data={"narrative": "STARBUCKS #123", "mccid": 5812}
        )
        
        assert result["resolution_type"] == "single_brand"
        assert result["assigned_brandid"] == 1
        assert result["confidence"] == 1.0
        assert result["requires_human_review"] is False
    
    def test_resolve_with_clear_winner(self):
        """Test resolution where one brand is clearly better."""
        brands = [
            {"brandid": 1, "brandname": "Shell", "sector": "Fuel",
             "metadata": {"regex": "^SHELL.*", "mccids": [5541, 5542]}},
            {"brandid": 2, "brandname": "Shell Station Convenience", "sector": "Retail",
             "metadata": {"regex": "^SHELL STATION.*", "mccids": [5411, 5541]}}
        ]
        
        result = resolve_multi_match(
            ccid=1,
            matching_brands=brands,
            combo_data={"narrative": "SHELL STATION 123", "mccid": 5541}
        )
        
        # Should have scores for both brands
        assert "all_scores" in result
        assert len(result["all_scores"]) == 2
        # Both brands should have reasonable scores
        assert all(0.0 <= s["score"] <= 1.0 for s in result["all_scores"])
    
    def test_resolve_with_ambiguous_tie(self):
        """Test resolution where brands are too similar."""
        brands = [
            {"brandid": 1, "brandname": "McDonald's", "sector": "Food & Beverage",
             "metadata": {"regex": "^MCD.*", "mccids": [5812]}},
            {"brandid": 2, "brandname": "McDonald's UK", "sector": "Food & Beverage",
             "metadata": {"regex": "^MCD.*", "mccids": [5812]}}
        ]
        
        result = resolve_multi_match(
            ccid=1,
            matching_brands=brands,
            combo_data={"narrative": "MCD #123", "mccid": 5812}
        )
        
        # Should flag for human review due to ambiguity
        assert result["resolution_type"] == "manual_review"
        assert result["assigned_brandid"] is None
        assert result["requires_human_review"] is True
    
    def test_resolve_with_narrative_match(self):
        """Test resolution based on strong narrative match."""
        brands = [
            {"brandid": 1, "brandname": "Apple", "sector": "Technology",
             "metadata": {"regex": "^APPLE.*", "mccids": [5732]}},
            {"brandid": 2, "brandname": "Apple Store", "sector": "Retail",
             "metadata": {"regex": "^APPLE STORE.*", "mccids": [5732]}}
        ]
        
        result = resolve_multi_match(
            ccid=1,
            matching_brands=brands,
            combo_data={"narrative": "APPLE STORE #456", "mccid": 5732}
        )
        
        # Should resolve or at least have Apple Store with higher score
        assert "all_scores" in result
        apple_store_score = next(s for s in result["all_scores"] if s["brandname"] == "Apple Store")
        apple_score = next(s for s in result["all_scores"] if s["brandname"] == "Apple")
        assert apple_store_score["score"] > apple_score["score"]


class TestAnalyzeNarrativeSimilarity:
    """Test the analyze_narrative_similarity tool."""
    
    def test_exact_match(self):
        """Test with exact brand name in narrative."""
        result = analyze_narrative_similarity(
            narrative="STARBUCKS STORE #123",
            brand_names=["Starbucks", "Starburst"]
        )
        
        assert result["best_match"] == "Starbucks"
        assert result["best_similarity"] > 0.5
        assert result["similarities"][0]["substring_match"] is True
    
    def test_partial_match(self):
        """Test with partial brand name match."""
        result = analyze_narrative_similarity(
            narrative="SBUX COFFEE",
            brand_names=["Starbucks", "Subway"]
        )
        
        # Should have some similarity but not perfect
        assert len(result["similarities"]) == 2
        assert all(0.0 <= s["similarity"] <= 1.0 for s in result["similarities"])
    
    def test_word_match(self):
        """Test word-level matching."""
        result = analyze_narrative_similarity(
            narrative="SHELL STATION 123",
            brand_names=["Shell", "Shell Station"]
        )
        
        # "Shell Station" should match better
        shell_station_sim = next(s for s in result["similarities"] if s["brand_name"] == "Shell Station")
        shell_sim = next(s for s in result["similarities"] if s["brand_name"] == "Shell")
        
        assert shell_station_sim["similarity"] >= shell_sim["similarity"]
        assert shell_station_sim["word_match"] is True
    
    def test_no_match(self):
        """Test with completely different names."""
        result = analyze_narrative_similarity(
            narrative="WALMART SUPERCENTER",
            brand_names=["Starbucks", "McDonald's"]
        )
        
        # Should have low similarity for both
        assert all(s["similarity"] < 0.5 for s in result["similarities"])
    
    def test_case_insensitive(self):
        """Test that matching is case-insensitive."""
        result1 = analyze_narrative_similarity(
            narrative="starbucks store",
            brand_names=["Starbucks"]
        )
        
        result2 = analyze_narrative_similarity(
            narrative="STARBUCKS STORE",
            brand_names=["Starbucks"]
        )
        
        # Should have same similarity regardless of case
        assert result1["best_similarity"] == result2["best_similarity"]


class TestCompareMccidAlignment:
    """Test the compare_mccid_alignment tool."""
    
    def test_mccid_in_first_position(self):
        """Test MCCID that's first in brand's list."""
        brands = [
            {"brandid": 1, "brandname": "Starbucks", "sector": "Food & Beverage",
             "metadata": {"mccids": [5812, 5814]}},
            {"brandid": 2, "brandname": "Subway", "sector": "Food & Beverage",
             "metadata": {"mccids": [5814, 5812]}}
        ]
        
        result = compare_mccid_alignment(mccid=5812, brands=brands)
        
        # Starbucks should have higher score (5812 is first)
        starbucks_alignment = result["alignments"][0]
        subway_alignment = result["alignments"][1]
        
        assert starbucks_alignment["in_mccid_list"] is True
        assert subway_alignment["in_mccid_list"] is True
        assert starbucks_alignment["alignment_score"] > subway_alignment["alignment_score"]
    
    def test_mccid_not_in_list(self):
        """Test MCCID that's not in brand's list."""
        brands = [
            {"brandid": 1, "brandname": "Starbucks", "sector": "Food & Beverage",
             "metadata": {"mccids": [5812, 5814]}},
            {"brandid": 2, "brandname": "Shell", "sector": "Fuel",
             "metadata": {"mccids": [5541, 5542]}}
        ]
        
        result = compare_mccid_alignment(mccid=5999, brands=brands)
        
        # Neither should have the MCCID
        assert all(a["in_mccid_list"] is False for a in result["alignments"])
        assert all(a["alignment_score"] == 0.0 for a in result["alignments"])
    
    def test_mccid_in_one_brand_only(self):
        """Test MCCID that's only in one brand's list."""
        brands = [
            {"brandid": 1, "brandname": "Starbucks", "sector": "Food & Beverage",
             "metadata": {"mccids": [5812, 5814]}},
            {"brandid": 2, "brandname": "Shell", "sector": "Fuel",
             "metadata": {"mccids": [5541, 5542]}}
        ]
        
        result = compare_mccid_alignment(mccid=5812, brands=brands)
        
        assert result["best_match"] == "Starbucks"
        assert result["alignments"][0]["in_mccid_list"] is True
        assert result["alignments"][1]["in_mccid_list"] is False


class TestCalculateMatchConfidence:
    """Test the calculate_match_confidence tool."""
    
    def test_high_confidence_match(self):
        """Test confidence calculation for strong match."""
        confidence = calculate_match_confidence(
            ccid=1,
            brandid=100,
            narrative="STARBUCKS STORE #123",
            brand_data={
                "brandname": "Starbucks",
                "metadata": {"regex": "^STARBUCKS\\s+STORE\\s+#\\d+$"}
            }
        )
        
        assert 0.7 <= confidence <= 1.0
    
    def test_low_confidence_match(self):
        """Test confidence calculation for weak match."""
        confidence = calculate_match_confidence(
            ccid=1,
            brandid=100,
            narrative="WALMART",
            brand_data={
                "brandname": "Starbucks",
                "metadata": {"regex": "^S.*"}
            }
        )
        
        assert confidence < 0.5
    
    def test_partial_match(self):
        """Test confidence for partial match."""
        confidence = calculate_match_confidence(
            ccid=1,
            brandid=100,
            narrative="SBUX COFFEE",
            brand_data={
                "brandname": "Starbucks",
                "metadata": {"regex": "^S(TARBUCKS|BUX).*"}
            }
        )
        
        assert 0.3 <= confidence <= 0.8


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_resolve_with_empty_narrative(self):
        """Test resolution with empty narrative."""
        brands = [
            {"brandid": 1, "brandname": "Starbucks", "sector": "Food & Beverage",
             "metadata": {"regex": "^STARBUCKS.*", "mccids": [5812]}}
        ]
        
        result = resolve_multi_match(
            ccid=1,
            matching_brands=brands,
            combo_data={"narrative": "", "mccid": 5812}
        )
        
        # Should still work but with low confidence
        assert "resolution_type" in result
    
    def test_analyze_similarity_with_empty_names(self):
        """Test narrative similarity with empty brand names."""
        result = analyze_narrative_similarity(
            narrative="STARBUCKS",
            brand_names=[]
        )
        
        assert result["similarities"] == []
        assert result["best_match"] is None
        assert result["best_similarity"] == 0.0
    
    def test_compare_alignment_with_no_mccids(self):
        """Test MCCID alignment when brands have no MCCIDs."""
        brands = [
            {"brandid": 1, "brandname": "Starbucks", "sector": "Food & Beverage",
             "metadata": {"mccids": []}}
        ]
        
        result = compare_mccid_alignment(mccid=5812, brands=brands)
        
        assert result["alignments"][0]["in_mccid_list"] is False
        assert result["alignments"][0]["alignment_score"] == 0.0
    
    def test_resolve_three_way_tie(self):
        """Test resolution with three matching brands."""
        brands = [
            {"brandid": 1, "brandname": "Shell", "sector": "Fuel",
             "metadata": {"regex": "^SHELL.*", "mccids": [5541]}},
            {"brandid": 2, "brandname": "Shell Station", "sector": "Retail",
             "metadata": {"regex": "^SHELL STATION.*", "mccids": [5541]}},
            {"brandid": 3, "brandname": "Shell Express", "sector": "Fuel",
             "metadata": {"regex": "^SHELL EXPRESS.*", "mccids": [5541]}}
        ]
        
        result = resolve_multi_match(
            ccid=1,
            matching_brands=brands,
            combo_data={"narrative": "SHELL STATION 123", "mccid": 5541}
        )
        
        # Should resolve to Shell Station (most specific match)
        assert "resolution_type" in result
        assert "all_scores" in result
        assert len(result["all_scores"]) == 3
    
    def test_resolve_with_special_characters(self):
        """Test resolution with special characters in narrative."""
        brands = [
            {"brandid": 1, "brandname": "McDonald's", "sector": "Food & Beverage",
             "metadata": {"regex": "^MCD.*", "mccids": [5812]}}
        ]
        
        result = resolve_multi_match(
            ccid=1,
            matching_brands=brands,
            combo_data={"narrative": "MCD'S #123", "mccid": 5812}
        )
        
        assert result["resolution_type"] == "single_brand"
    
    def test_narrative_similarity_with_numbers(self):
        """Test narrative similarity with store numbers."""
        result = analyze_narrative_similarity(
            narrative="STARBUCKS #12345",
            brand_names=["Starbucks"]
        )
        
        assert result["best_match"] == "Starbucks"
        assert result["best_similarity"] > 0.5
