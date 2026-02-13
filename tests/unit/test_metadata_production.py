"""
Unit Tests for Metadata Production Agent

Tests core functionality for regex generation and MCCID list creation.
"""

import pytest
import re
from agents.metadata_production.tools import (
    generate_regex,
    generate_mccid_list,
    filter_wallet_text,
    apply_disambiguation,
    validate_pattern_coverage
)


class TestGenerateRegex:
    """Test regex pattern generation."""
    
    def test_empty_narratives(self):
        """Test handling of empty narrative list."""
        result = generate_regex(123, [])
        assert result == ""
    
    def test_single_brand_pattern(self):
        """Test regex generation for consistent brand name."""
        narratives = [
            "STARBUCKS #123",
            "STARBUCKS #456",
            "STARBUCKS STORE"
        ]
        
        result = generate_regex(123, narratives)
        
        assert result != ""
        assert "STARBUCKS" in result
        # Should match all narratives
        pattern = re.compile(result, re.IGNORECASE)
        for narrative in narratives:
            assert pattern.search(narrative) is not None
    
    def test_wallet_prefix_removal(self):
        """Test that wallet prefixes are removed before pattern generation."""
        narratives = [
            "SQ *STARBUCKS",
            "PAYPAL *STARBUCKS",
            "STARBUCKS"
        ]
        
        result = generate_regex(123, narratives)
        
        # Pattern should focus on STARBUCKS, not wallet prefixes
        assert "STARBUCKS" in result
        assert "SQ" not in result
        assert "PAYPAL" not in result
    
    def test_multiple_brand_variants(self):
        """Test regex generation with brand name variations."""
        narratives = [
            "MCDONALDS #123",
            "MCDONALD'S STORE",
            "MCD RESTAURANT"
        ]
        
        result = generate_regex(123, narratives)
        
        assert result != ""
        # Should handle variations
        pattern = re.compile(result, re.IGNORECASE)
        assert pattern.search("MCDONALDS") is not None


class TestGenerateMCCIDList:
    """Test MCCID list generation."""
    
    def test_empty_mccids(self):
        """Test handling of empty MCCID list."""
        result = generate_mccid_list(123, [])
        assert result == []
    
    def test_wallet_mccid_filtering(self):
        """Test that wallet-specific MCCIDs are filtered out."""
        mccids = [5812, 7399, 6012, 5814, 7299]
        
        result = generate_mccid_list(123, mccids)
        
        # Wallet MCCIDs (7399, 6012, 7299) should be excluded
        assert 7399 not in result
        assert 6012 not in result
        assert 7299 not in result
        # Legitimate MCCIDs should be included
        assert 5812 in result
        assert 5814 in result
    
    def test_deduplication(self):
        """Test that duplicate MCCIDs are removed."""
        mccids = [5812, 5812, 5814, 5814, 5812]
        
        result = generate_mccid_list(123, mccids)
        
        assert len(result) == 2
        assert 5812 in result
        assert 5814 in result
    
    def test_sorted_output(self):
        """Test that MCCIDs are sorted."""
        mccids = [5814, 5411, 5812]
        
        result = generate_mccid_list(123, mccids)
        
        assert result == [5411, 5812, 5814]


class TestFilterWalletText:
    """Test wallet text filtering."""
    
    def test_empty_narratives(self):
        """Test handling of empty narrative list."""
        result = filter_wallet_text([], ["PAYPAL"])
        assert result == []
    
    def test_paypal_removal(self):
        """Test removal of PAYPAL prefix."""
        narratives = ["PAYPAL *STARBUCKS", "PAYPAL STARBUCKS"]
        
        result = filter_wallet_text(narratives, ["PAYPAL"])
        
        assert all("PAYPAL" not in n for n in result)
        assert all("STARBUCKS" in n for n in result)
    
    def test_square_removal(self):
        """Test removal of Square prefixes."""
        narratives = ["SQ *COFFEE SHOP", "SQUARE PAYMENT"]
        
        result = filter_wallet_text(narratives, ["SQ", "SQUARE"])
        
        assert "COFFEE SHOP" in result[0]
        assert "PAYMENT" in result[1]
    
    def test_pp_removal(self):
        """Test removal of PP * prefix."""
        narratives = ["PP *STORE NAME"]
        
        result = filter_wallet_text(narratives, ["PP"])
        
        assert "STORE NAME" in result[0]
        assert "PP" not in result[0]
    
    def test_case_insensitive_removal(self):
        """Test that removal is case-insensitive."""
        narratives = ["paypal *store", "PAYPAL *STORE", "PayPal *Store"]
        
        result = filter_wallet_text(narratives, ["PAYPAL"])
        
        for cleaned in result:
            assert "paypal" not in cleaned.lower() or cleaned.lower() == "store"


class TestApplyDisambiguation:
    """Test disambiguation application."""
    
    def test_empty_regex(self):
        """Test handling of empty regex."""
        result = apply_disambiguation("", {"strategy": "add_word_boundary"})
        assert result == ""
    
    def test_empty_guidance(self):
        """Test handling of empty guidance."""
        result = apply_disambiguation("^SHELL", {})
        assert result == "^SHELL"
    
    def test_add_word_boundary(self):
        """Test adding word boundary."""
        result = apply_disambiguation("^SHELL", {"strategy": "add_word_boundary"})
        assert result.endswith(r"\b")
    
    def test_add_negative_lookahead(self):
        """Test adding negative lookahead."""
        guidance = {
            "strategy": "add_negative_lookahead",
            "exclude_patterns": ["HOTEL", "STATION"]
        }
        
        result = apply_disambiguation("^SHELL", guidance)
        
        assert "(?!" in result
        assert "HOTEL" in result
        assert "STATION" in result
    
    def test_make_more_specific(self):
        """Test making pattern more specific."""
        guidance = {
            "strategy": "make_more_specific",
            "required_suffix": r"\s+STORE"
        }
        
        result = apply_disambiguation("^BRAND", guidance)
        
        assert result.endswith(r"\s+STORE")


class TestValidatePatternCoverage:
    """Test pattern coverage validation."""
    
    def test_empty_regex(self):
        """Test handling of empty regex."""
        result = validate_pattern_coverage("", ["STARBUCKS"])
        
        assert result["valid"] is False
        assert "error" in result
    
    def test_empty_narratives(self):
        """Test handling of empty narratives."""
        result = validate_pattern_coverage("^STARBUCKS", [])
        
        assert result["valid"] is True
        assert result["narratives_matched"] == 0.0
        assert result["total_count"] == 0
    
    def test_full_coverage(self):
        """Test pattern with 100% coverage."""
        narratives = ["STARBUCKS #123", "STARBUCKS STORE", "STARBUCKS COFFEE"]
        
        result = validate_pattern_coverage("^STARBUCKS", narratives)
        
        assert result["valid"] is True
        assert result["narratives_matched"] == 1.0
        assert result["match_count"] == 3
        assert result["total_count"] == 3
    
    def test_partial_coverage(self):
        """Test pattern with partial coverage."""
        narratives = ["STARBUCKS #123", "SHELL STATION", "STARBUCKS STORE"]
        
        result = validate_pattern_coverage("^STARBUCKS", narratives)
        
        assert result["valid"] is True
        assert result["narratives_matched"] == pytest.approx(0.667, rel=0.01)
        assert result["match_count"] == 2
        assert result["total_count"] == 3
    
    def test_invalid_regex(self):
        """Test handling of invalid regex."""
        result = validate_pattern_coverage("^[INVALID(", ["STARBUCKS"])
        
        assert result["valid"] is False
        assert "error" in result
        assert "Invalid regex" in result["error"]
    
    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        narratives = ["starbucks", "STARBUCKS", "StArBuCkS"]
        
        result = validate_pattern_coverage("^STARBUCKS", narratives)
        
        assert result["valid"] is True
        assert result["narratives_matched"] == 1.0


class TestIntegration:
    """Test integration between tools."""
    
    def test_complete_metadata_generation_workflow(self):
        """Test complete workflow from narratives to validated metadata."""
        # Step 1: Start with wallet-contaminated narratives
        narratives = [
            "SQ *STARBUCKS #123",
            "PAYPAL *STARBUCKS",
            "STARBUCKS STORE",
            "STARBUCKS COFFEE"
        ]
        mccids = [5812, 7399, 5814, 6012]
        
        # Step 2: Filter wallet text
        cleaned_narratives = filter_wallet_text(narratives, ["SQ", "PAYPAL"])
        assert all("SQ" not in n and "PAYPAL" not in n for n in cleaned_narratives)
        
        # Step 3: Generate regex
        regex = generate_regex(123, cleaned_narratives)
        assert regex != ""
        assert "STARBUCKS" in regex
        
        # Step 4: Generate MCCID list
        mccid_list = generate_mccid_list(123, mccids)
        assert 7399 not in mccid_list  # Wallet MCCID excluded
        assert 6012 not in mccid_list  # Wallet MCCID excluded
        assert 5812 in mccid_list
        assert 5814 in mccid_list
        
        # Step 5: Validate coverage
        coverage = validate_pattern_coverage(regex, cleaned_narratives)
        assert coverage["valid"] is True
        assert coverage["narratives_matched"] >= 0.75  # Good coverage
