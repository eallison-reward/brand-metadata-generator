"""
Unit Tests for Evaluator Agent

Tests specific examples and edge cases for the Evaluator Agent tools.
"""

import pytest
from agents.evaluator.tools import (
    analyze_narratives,
    detect_payment_wallets,
    assess_mccid_consistency,
    calculate_confidence_score,
    generate_production_prompt,
    detect_ties
)


class TestAnalyzeNarratives:
    """Test narrative pattern analysis functionality."""
    
    def test_empty_combos(self):
        """Test handling of empty combo list."""
        result = analyze_narratives(123, [])
        
        assert result["brandid"] == 123
        assert result["pattern_count"] == 0
        assert result["consistency_level"] == "unknown"
        assert "error" in result
    
    def test_single_pattern_high_consistency(self):
        """Test that identical narratives result in high consistency."""
        combos = [
            {"narrative": "STARBUCKS #123"},
            {"narrative": "STARBUCKS #123"},
            {"narrative": "STARBUCKS #123"}
        ]
        
        result = analyze_narratives(123, combos)
        
        assert result["brandid"] == 123
        assert result["pattern_count"] == 1
        assert result["variance_score"] == 0.0
        assert result["consistency_level"] == "high"
        assert result["total_narratives"] == 3
    
    def test_multiple_patterns_medium_consistency(self):
        """Test narratives with moderate variation."""
        combos = [
            {"narrative": "STARBUCKS #123"},
            {"narrative": "STARBUCKS #456"},
            {"narrative": "STARBUCKS STORE"},
            {"narrative": "STARBUCKS #123"},
            {"narrative": "STARBUCKS #456"}
        ]
        
        result = analyze_narratives(123, combos)
        
        assert result["brandid"] == 123
        assert result["pattern_count"] == 3
        assert result["consistency_level"] in ["medium", "high"]
        assert len(result["common_patterns"]) > 0
    
    def test_high_variance_low_consistency(self):
        """Test narratives with high variation."""
        # Create narratives with very uneven distribution to get high variance
        combos = []
        # One pattern appears 50 times
        for i in range(50):
            combos.append({"narrative": "STARBUCKS #123"})
        # Many patterns appear once each (creates high standard deviation)
        for i in range(50):
            combos.append({"narrative": f"STARBUCKS UNIQUE PATTERN {i}"})
        
        result = analyze_narratives(123, combos)
        
        assert result["brandid"] == 123
        assert result["pattern_count"] == 51  # 1 common + 50 unique
        # With this distribution, variance should be > 1.5
        assert result["variance_score"] > 1.5
        assert result["consistency_level"] == "low"
    
    def test_common_patterns_extraction(self):
        """Test that most common patterns are identified."""
        combos = [
            {"narrative": "STARBUCKS #123"},
            {"narrative": "STARBUCKS #123"},
            {"narrative": "STARBUCKS #123"},
            {"narrative": "STARBUCKS #456"},
            {"narrative": "STARBUCKS #456"},
            {"narrative": "STARBUCKS STORE"}
        ]
        
        result = analyze_narratives(123, combos)
        
        assert len(result["common_patterns"]) > 0
        # Most common should be "STARBUCKS #123" with 3 occurrences
        assert result["common_patterns"][0]["pattern"] == "STARBUCKS #123"
        assert result["common_patterns"][0]["count"] == 3
        assert result["common_patterns"][0]["percentage"] == 0.5
    
    def test_missing_narratives_in_combos(self):
        """Test handling of combos without narrative field."""
        combos = [
            {"ccid": 1, "mccid": 5812},
            {"ccid": 2, "narrative": "STARBUCKS"},
            {"ccid": 3}
        ]
        
        result = analyze_narratives(123, combos)
        
        # Should only process the one combo with narrative
        assert result["total_narratives"] == 1


class TestDetectPaymentWallets:
    """Test payment wallet detection functionality."""
    
    def test_empty_narratives(self):
        """Test handling of empty narrative list."""
        result = detect_payment_wallets([])
        
        assert result["wallet_detected"] is False
        assert result["affected_count"] == 0
        assert result["affected_percentage"] == 0.0
    
    def test_paypal_detection(self):
        """Test detection of PAYPAL indicator."""
        narratives = [
            "PAYPAL *STARBUCKS",
            "STARBUCKS #123",
            "PAYPAL TRANSFER"
        ]
        
        result = detect_payment_wallets(narratives)
        
        assert result["wallet_detected"] is True
        assert "PAYPAL" in result["wallet_indicators"]
        assert result["affected_count"] == 2
        assert result["affected_percentage"] == pytest.approx(0.667, rel=0.01)
    
    def test_pp_prefix_detection(self):
        """Test detection of PP * prefix."""
        narratives = [
            "PP *STARBUCKS",
            "PP*MCDONALDS",
            "STARBUCKS"
        ]
        
        result = detect_payment_wallets(narratives)
        
        assert result["wallet_detected"] is True
        assert "PP" in result["wallet_indicators"]
        assert result["affected_count"] == 2
    
    def test_square_detection(self):
        """Test detection of Square indicators."""
        narratives = [
            "SQ *COFFEE SHOP",
            "SQUARE PAYMENT",
            "REGULAR STORE"
        ]
        
        result = detect_payment_wallets(narratives)
        
        assert result["wallet_detected"] is True
        assert "SQ" in result["wallet_indicators"] or "SQUARE" in result["wallet_indicators"]
        assert result["affected_count"] >= 2
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        narratives = [
            "paypal *store",
            "PAYPAL *STORE",
            "PayPal *Store",
            "pp *store",
            "PP *STORE",
            "sq *store",
            "SQ *STORE",
            "square store",
            "SQUARE STORE"
        ]
        
        result = detect_payment_wallets(narratives)
        
        assert result["wallet_detected"] is True
        assert result["affected_count"] == 9
    
    def test_no_wallet_indicators(self):
        """Test narratives without wallet indicators."""
        narratives = [
            "STARBUCKS #123",
            "MCDONALDS STORE",
            "SHELL STATION"
        ]
        
        result = detect_payment_wallets(narratives)
        
        assert result["wallet_detected"] is False
        assert len(result["wallet_indicators"]) == 0
        assert result["affected_count"] == 0
    
    def test_multiple_wallet_types(self):
        """Test detection of multiple wallet types."""
        narratives = [
            "PAYPAL *STORE1",
            "SQ *STORE2",
            "PP *STORE3",
            "SQUARE STORE4"
        ]
        
        result = detect_payment_wallets(narratives)
        
        assert result["wallet_detected"] is True
        # Should detect multiple wallet types
        assert len(result["wallet_indicators"]) >= 2
    
    def test_affected_indices_tracking(self):
        """Test that affected narrative indices are tracked."""
        narratives = [
            "CLEAN STORE",
            "PAYPAL *STORE",
            "ANOTHER CLEAN",
            "SQ *STORE"
        ]
        
        result = detect_payment_wallets(narratives)
        
        assert result["affected_indices"] == [1, 3]


class TestAssessMCCIDConsistency:
    """Test MCCID consistency assessment functionality."""
    
    def test_empty_mccids(self):
        """Test handling of empty MCCID list."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage"},
            {"mccid": 5814, "sector": "Food & Beverage"}
        ]
        
        result = assess_mccid_consistency(123, [], "Food & Beverage", mcc_table)
        
        assert result["brandid"] == 123
        assert result["consistent"] is True
        assert result["matching_sector_count"] == 0
        assert "error" in result
    
    def test_perfect_consistency(self):
        """Test MCCIDs that all match brand sector."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage"},
            {"mccid": 5814, "sector": "Food & Beverage"},
            {"mccid": 5411, "sector": "Retail"}
        ]
        
        mccids = [5812, 5814]
        
        result = assess_mccid_consistency(123, mccids, "Food & Beverage", mcc_table)
        
        assert result["brandid"] == 123
        assert result["consistent"] is True
        assert result["matching_sector_count"] == 2
        assert result["consistency_percentage"] == 1.0
        assert len(result["mismatched_mccids"]) == 0
    
    def test_partial_consistency(self):
        """Test MCCIDs with some mismatches."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage"},
            {"mccid": 5814, "sector": "Food & Beverage"},
            {"mccid": 5541, "sector": "Fuel"},
            {"mccid": 7399, "sector": "Services"}
        ]
        
        mccids = [5812, 5814, 5541]
        
        result = assess_mccid_consistency(123, mccids, "Food & Beverage", mcc_table)
        
        assert result["brandid"] == 123
        assert result["matching_sector_count"] == 2
        assert result["consistency_percentage"] == pytest.approx(0.667, rel=0.01)
        assert len(result["mismatched_mccids"]) == 1
        assert result["mismatched_mccids"][0]["mccid"] == 5541
    
    def test_wallet_mccid_identification(self):
        """Test identification of wallet-specific MCCIDs."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage"},
            {"mccid": 7399, "sector": "Services"},
            {"mccid": 6012, "sector": "Financial"}
        ]
        
        mccids = [5812, 7399, 6012]
        
        result = assess_mccid_consistency(123, mccids, "Food & Beverage", mcc_table)
        
        # 7399 and 6012 are known wallet MCCIDs
        assert len(result["wallet_specific_mccids"]) >= 2
        wallet_mccids = [w["mccid"] for w in result["wallet_specific_mccids"]]
        assert 7399 in wallet_mccids
        assert 6012 in wallet_mccids
    
    def test_consistency_threshold(self):
        """Test that >50% match is considered consistent."""
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage"},
            {"mccid": 5814, "sector": "Food & Beverage"},
            {"mccid": 5541, "sector": "Fuel"}
        ]
        
        # 2 out of 3 match = 66.7% = consistent
        mccids = [5812, 5814, 5541]
        result = assess_mccid_consistency(123, mccids, "Food & Beverage", mcc_table)
        assert result["consistent"] is True
        
        # 1 out of 3 match = 33.3% = inconsistent
        mccids = [5812, 5541, 5542]
        mcc_table.append({"mccid": 5542, "sector": "Fuel"})
        result = assess_mccid_consistency(123, mccids, "Food & Beverage", mcc_table)
        assert result["consistent"] is False


class TestCalculateConfidenceScore:
    """Test confidence score calculation functionality."""
    
    def test_empty_analysis_results(self):
        """Test score calculation with empty results."""
        score = calculate_confidence_score({})
        
        assert 0.0 <= score <= 1.0
    
    def test_high_quality_high_score(self):
        """Test that high quality data produces high confidence."""
        analysis_results = {
            "narrative_analysis": {
                "consistency_level": "high",
                "variance_score": 0.2
            },
            "wallet_detection": {
                "wallet_detected": False,
                "affected_percentage": 0.0
            },
            "mccid_consistency": {
                "consistent": True,
                "consistency_percentage": 0.95
            },
            "commercial_validation": {
                "confidence": 0.95
            }
        }
        
        score = calculate_confidence_score(analysis_results)
        
        assert score >= 0.8
    
    def test_low_quality_low_score(self):
        """Test that low quality data produces low confidence."""
        analysis_results = {
            "narrative_analysis": {
                "consistency_level": "low",
                "variance_score": 2.5
            },
            "wallet_detection": {
                "wallet_detected": True,
                "affected_percentage": 0.9
            },
            "mccid_consistency": {
                "consistent": False,
                "consistency_percentage": 0.2
            },
            "commercial_validation": {
                "confidence": 0.3
            }
        }
        
        score = calculate_confidence_score(analysis_results)
        
        assert score <= 0.5
    
    def test_medium_quality_medium_score(self):
        """Test that medium quality data produces medium confidence."""
        analysis_results = {
            "narrative_analysis": {
                "consistency_level": "medium"
            },
            "wallet_detection": {
                "affected_percentage": 0.3
            },
            "mccid_consistency": {
                "consistency_percentage": 0.6
            },
            "commercial_validation": {
                "confidence": 0.7
            }
        }
        
        score = calculate_confidence_score(analysis_results)
        
        assert 0.4 <= score <= 0.8
    
    def test_score_always_in_range(self):
        """Test that score is always between 0.0 and 1.0."""
        # Test various extreme combinations
        test_cases = [
            {"narrative_analysis": {"consistency_level": "high"}},
            {"wallet_detection": {"affected_percentage": 1.0}},
            {"mccid_consistency": {"consistency_percentage": 0.0}},
            {"commercial_validation": {"confidence": 0.0}},
            {}
        ]
        
        for analysis_results in test_cases:
            score = calculate_confidence_score(analysis_results)
            assert 0.0 <= score <= 1.0


class TestGenerateProductionPrompt:
    """Test production prompt generation functionality."""
    
    def test_basic_prompt_structure(self):
        """Test that prompt includes brand information."""
        prompt = generate_production_prompt(
            brandid=123,
            brandname="Starbucks",
            issues=[],
            wallet_info={"wallet_detected": False}
        )
        
        assert "Brand 123" in prompt
        assert "Starbucks" in prompt
        assert "REQUIREMENTS:" in prompt
    
    def test_wallet_guidance_low_impact(self):
        """Test prompt for low wallet impact."""
        wallet_info = {
            "wallet_detected": True,
            "wallet_indicators": ["PAYPAL"],
            "affected_percentage": 0.15
        }
        
        prompt = generate_production_prompt(
            brandid=123,
            brandname="Starbucks",
            issues=[],
            wallet_info=wallet_info
        )
        
        assert "PAYMENT WALLET DETECTED" in prompt
        assert "PAYPAL" in prompt
        assert "Focus on clean narratives" in prompt
    
    def test_wallet_guidance_high_impact(self):
        """Test prompt for high wallet impact."""
        wallet_info = {
            "wallet_detected": True,
            "wallet_indicators": ["SQ", "SQUARE"],
            "affected_percentage": 0.65
        }
        
        prompt = generate_production_prompt(
            brandid=123,
            brandname="Starbucks",
            issues=[],
            wallet_info=wallet_info
        )
        
        assert "PAYMENT WALLET DETECTED" in prompt
        assert "excluding wallet prefixes" in prompt
    
    def test_issue_specific_guidance(self):
        """Test that issues are included in prompt."""
        issues = [
            {
                "type": "payment_wallet",
                "description": "Square wallet detected in 40% of narratives"
            },
            {
                "type": "mccid_mismatch",
                "description": "MCCID 7399 inconsistent with sector"
            }
        ]
        
        prompt = generate_production_prompt(
            brandid=123,
            brandname="Starbucks",
            issues=issues,
            wallet_info={"wallet_detected": True, "wallet_indicators": ["SQ"]}
        )
        
        assert "IDENTIFIED ISSUES" in prompt
        assert "Square wallet" in prompt
        assert "MCCID 7399" in prompt
    
    def test_requirements_always_included(self):
        """Test that requirements section is always present."""
        prompt = generate_production_prompt(
            brandid=123,
            brandname="Starbucks",
            issues=[],
            wallet_info={"wallet_detected": False}
        )
        
        assert "REQUIREMENTS:" in prompt
        assert "Regex must match brand name variations" in prompt
        assert "MCCID list should include only legitimate" in prompt


class TestDetectTies:
    """Test tie detection functionality."""
    
    def test_preliminary_tie_detection(self):
        """Test that preliminary tie detection returns expected structure."""
        combos = [
            {"ccid": 1, "narrative": "SHELL STATION", "mccid": 5541}
        ]
        
        result = detect_ties(123, combos, {})
        
        assert result["brandid"] == 123
        assert "ties_detected" in result
        assert "potential_ties" in result
        assert "tie_count" in result
        # Note: Full tie detection happens in Phase 3
        assert "note" in result
