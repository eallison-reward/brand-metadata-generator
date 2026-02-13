"""
Property-Based Tests for Evaluator Agent

These tests validate universal correctness properties that should hold
across all valid inputs for the Evaluator Agent.

Properties tested:
- Property 4: Wallet Detection and Flagging
- Property 7: Consistency Assessment
- Property 10: Confidence Score Calculation
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from agents.evaluator.tools import (
    detect_payment_wallets,
    analyze_narratives,
    assess_mccid_consistency,
    calculate_confidence_score
)


# Strategy for generating narratives
@st.composite
def narrative_strategy(draw):
    """Generate realistic narrative strings."""
    brand_names = ["STARBUCKS", "MCDONALDS", "SHELL", "TESCO", "AMAZON"]
    wallet_prefixes = ["", "PAYPAL ", "PP *", "SQ *", "SQUARE "]
    suffixes = ["", " #123", " STORE", " ONLINE", " 456"]
    
    brand = draw(st.sampled_from(brand_names))
    wallet = draw(st.sampled_from(wallet_prefixes))
    suffix = draw(st.sampled_from(suffixes))
    
    return f"{wallet}{brand}{suffix}".strip()


# Strategy for generating combo records
@st.composite
def combo_strategy(draw, include_wallet=None):
    """Generate combo record dictionaries."""
    if include_wallet is None:
        narrative = draw(narrative_strategy())
    elif include_wallet:
        # Force wallet inclusion
        wallet = draw(st.sampled_from(["PAYPAL ", "PP *", "SQ *", "SQUARE "]))
        brand = draw(st.sampled_from(["STARBUCKS", "MCDONALDS", "SHELL"]))
        narrative = f"{wallet}{brand}"
    else:
        # Force no wallet
        brand = draw(st.sampled_from(["STARBUCKS", "MCDONALDS", "SHELL"]))
        suffix = draw(st.sampled_from(["", " #123", " STORE"]))
        narrative = f"{brand}{suffix}"
    
    return {
        "ccid": draw(st.integers(min_value=1, max_value=100000)),
        "narrative": narrative,
        "mccid": draw(st.integers(min_value=1000, max_value=9999)),
        "brandid": draw(st.integers(min_value=1, max_value=1000))
    }


# Strategy for MCC table records
@st.composite
def mcc_record_strategy(draw):
    """Generate MCC table records."""
    sectors = ["Food & Beverage", "Retail", "Fuel", "Services", "Entertainment"]
    return {
        "mccid": draw(st.integers(min_value=1000, max_value=9999)),
        "mcc_desc": draw(st.text(min_size=5, max_size=50)),
        "sector": draw(st.sampled_from(sectors))
    }


class TestProperty4WalletDetection:
    """
    Property 4: Wallet Detection and Flagging
    
    For any narrative containing payment wallet indicators ("PAYPAL", "PP", "SQ", 
    "SQUARE" - case insensitive), the associated combo record should be flagged 
    as wallet-affected by the Evaluator Agent.
    
    **Validates: Requirements 3.1, 3.2**
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(st.lists(combo_strategy(include_wallet=True), min_size=1, max_size=10))
    def test_wallet_indicators_are_detected(self, combos_with_wallets):
        """
        Property: Any narrative with wallet indicators must be detected.
        """
        narratives = [combo["narrative"] for combo in combos_with_wallets]
        result = detect_payment_wallets(narratives)
        
        # Property: Wallet must be detected
        assert result["wallet_detected"] is True, \
            f"Wallet not detected in narratives: {narratives}"
        
        # Property: At least one wallet indicator must be identified
        assert len(result["wallet_indicators"]) > 0, \
            "No wallet indicators identified"
        
        # Property: Affected count must be > 0
        assert result["affected_count"] > 0, \
            "No narratives marked as affected"
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(st.lists(combo_strategy(include_wallet=False), min_size=1, max_size=10))
    def test_clean_narratives_not_flagged(self, combos_without_wallets):
        """
        Property: Narratives without wallet indicators should not be flagged.
        """
        narratives = [combo["narrative"] for combo in combos_without_wallets]
        
        # Ensure no wallet indicators present
        wallet_patterns = ["PAYPAL", "PP *", "SQ *", "SQUARE"]
        for narrative in narratives:
            assume(not any(pattern.lower() in narrative.lower() for pattern in wallet_patterns))
        
        result = detect_payment_wallets(narratives)
        
        # Property: No wallet should be detected
        assert result["wallet_detected"] is False, \
            f"False positive wallet detection in: {narratives}"
        
        # Property: Affected count must be 0
        assert result["affected_count"] == 0, \
            "Clean narratives incorrectly flagged as wallet-affected"
    
    @given(
        st.lists(combo_strategy(include_wallet=True), min_size=1, max_size=10),
        st.lists(combo_strategy(include_wallet=False), min_size=1, max_size=10)
    )
    def test_mixed_narratives_correct_percentage(self, wallet_combos, clean_combos):
        """
        Property: Affected percentage must accurately reflect wallet presence.
        """
        # Ensure clean combos don't have wallet indicators
        wallet_patterns = ["PAYPAL", "PP *", "SQ *", "SQUARE"]
        clean_narratives = []
        for combo in clean_combos:
            narrative = combo["narrative"]
            if not any(pattern.lower() in narrative.lower() for pattern in wallet_patterns):
                clean_narratives.append(narrative)
        
        assume(len(clean_narratives) > 0)
        
        wallet_narratives = [combo["narrative"] for combo in wallet_combos]
        all_narratives = wallet_narratives + clean_narratives
        
        result = detect_payment_wallets(all_narratives)
        
        # Property: Affected percentage must be between 0 and 1
        assert 0.0 <= result["affected_percentage"] <= 1.0, \
            "Affected percentage out of valid range"
        
        # Property: Affected count must not exceed total count
        assert result["affected_count"] <= len(all_narratives), \
            "Affected count exceeds total narratives"
        
        # Property: If wallet detected, affected count must be > 0
        if result["wallet_detected"]:
            assert result["affected_count"] > 0, \
                "Wallet detected but no narratives affected"
    
    @given(st.text(min_size=5, max_size=100))
    def test_case_insensitive_detection(self, base_text):
        """
        Property: Wallet detection must be case-insensitive.
        """
        # Create variations with different cases
        variations = [
            f"PAYPAL {base_text}",
            f"paypal {base_text}",
            f"PayPal {base_text}",
            f"PP *{base_text}",
            f"pp *{base_text}",
            f"SQ *{base_text}",
            f"sq *{base_text}",
            f"SQUARE {base_text}",
            f"square {base_text}"
        ]
        
        for narrative in variations:
            result = detect_payment_wallets([narrative])
            
            # Property: All case variations must be detected
            assert result["wallet_detected"] is True, \
                f"Case-insensitive detection failed for: {narrative}"


class TestProperty7ConsistencyAssessment:
    """
    Property 7: Consistency Assessment
    
    For any brandid, the Evaluator Agent should assess both narrative pattern 
    consistency and MCCID association consistency across all combo records.
    
    **Validates: Requirements 4.1, 4.2**
    """
    
    @given(
        st.integers(min_value=1, max_value=1000),
        st.lists(combo_strategy(), min_size=1, max_size=50)
    )
    def test_narrative_analysis_completeness(self, brandid, combos):
        """
        Property: Narrative analysis must process all provided combos.
        """
        result = analyze_narratives(brandid, combos)
        
        # Property: Result must include brandid
        assert result["brandid"] == brandid, \
            "Result brandid doesn't match input"
        
        # Property: Must return consistency level
        assert "consistency_level" in result, \
            "Missing consistency_level in result"
        
        # Property: Consistency level must be valid
        valid_levels = ["high", "medium", "low", "unknown"]
        assert result["consistency_level"] in valid_levels, \
            f"Invalid consistency level: {result['consistency_level']}"
        
        # Property: Must return variance score
        assert "variance_score" in result, \
            "Missing variance_score in result"
        
        # Property: Variance score must be non-negative
        assert result["variance_score"] >= 0.0, \
            "Variance score cannot be negative"
    
    @given(
        st.integers(min_value=1, max_value=1000),
        st.lists(st.integers(min_value=1000, max_value=9999), min_size=1, max_size=20),
        st.sampled_from(["Food & Beverage", "Retail", "Fuel", "Services"]),
        st.lists(mcc_record_strategy(), min_size=10, max_size=50)
    )
    def test_mccid_consistency_assessment(self, brandid, mccids, sector, mcc_table):
        """
        Property: MCCID consistency must be assessed against sector.
        """
        result = assess_mccid_consistency(brandid, mccids, sector, mcc_table)
        
        # Property: Result must include brandid
        assert result["brandid"] == brandid, \
            "Result brandid doesn't match input"
        
        # Property: Must return consistency boolean
        assert "consistent" in result, \
            "Missing consistent field in result"
        
        # Property: Must return consistency percentage
        assert "consistency_percentage" in result, \
            "Missing consistency_percentage in result"
        
        # Property: Consistency percentage must be between 0 and 1
        assert 0.0 <= result["consistency_percentage"] <= 1.0, \
            "Consistency percentage out of valid range"
        
        # Property: Matching count must not exceed total
        assert result["matching_sector_count"] <= result["total_mccids"], \
            "Matching count exceeds total MCCIDs"
    
    @given(st.lists(combo_strategy(), min_size=2, max_size=10))
    def test_identical_narratives_high_consistency(self, combos):
        """
        Property: Identical narratives should result in high consistency.
        """
        # Make all narratives identical
        identical_narrative = "STARBUCKS #123"
        for combo in combos:
            combo["narrative"] = identical_narrative
        
        result = analyze_narratives(1, combos)
        
        # Property: Variance score should be 0 for identical patterns
        assert result["variance_score"] == 0.0, \
            "Identical narratives should have zero variance"
        
        # Property: Consistency level should be high
        assert result["consistency_level"] == "high", \
            "Identical narratives should have high consistency"
        
        # Property: Pattern count should be 1
        assert result["pattern_count"] == 1, \
            "Identical narratives should have only one pattern"


class TestProperty10ConfidenceScore:
    """
    Property 10: Confidence Score Calculation
    
    For any brand processed by the Evaluator Agent, a confidence score between 
    0.0 and 1.0 should be calculated based on data quality metrics.
    
    **Validates: Requirements 4.6**
    """
    
    @given(
        st.dictionaries(
            keys=st.sampled_from(["narrative_analysis", "wallet_detection", 
                                 "mccid_consistency", "commercial_validation"]),
            values=st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.one_of(
                    st.floats(min_value=0.0, max_value=1.0),
                    st.sampled_from(["high", "medium", "low"]),
                    st.booleans(),
                    st.integers(min_value=0, max_value=100)
                )
            ),
            min_size=1,
            max_size=4
        )
    )
    def test_confidence_score_range(self, analysis_results):
        """
        Property: Confidence score must always be between 0.0 and 1.0.
        """
        score = calculate_confidence_score(analysis_results)
        
        # Property: Score must be between 0.0 and 1.0 inclusive
        assert 0.0 <= score <= 1.0, \
            f"Confidence score {score} out of valid range [0.0, 1.0]"
    
    @given(st.floats(min_value=0.0, max_value=1.0))
    def test_high_quality_data_high_confidence(self, base_score):
        """
        Property: High quality data should result in high confidence scores.
        """
        # Create high-quality analysis results
        analysis_results = {
            "narrative_analysis": {
                "consistency_level": "high",
                "variance_score": 0.1
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
        
        # Property: High quality should result in score >= 0.7
        assert score >= 0.7, \
            f"High quality data should produce high confidence, got {score}"
    
    @given(st.floats(min_value=0.0, max_value=1.0))
    def test_low_quality_data_low_confidence(self, base_score):
        """
        Property: Low quality data should result in low confidence scores.
        """
        # Create low-quality analysis results
        analysis_results = {
            "narrative_analysis": {
                "consistency_level": "low",
                "variance_score": 2.5
            },
            "wallet_detection": {
                "wallet_detected": True,
                "affected_percentage": 0.8
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
        
        # Property: Low quality should result in score <= 0.5
        assert score <= 0.5, \
            f"Low quality data should produce low confidence, got {score}"
    
    def test_empty_analysis_results_valid_score(self):
        """
        Property: Even with empty results, score must be valid.
        """
        score = calculate_confidence_score({})
        
        # Property: Score must still be in valid range
        assert 0.0 <= score <= 1.0, \
            "Empty analysis should still produce valid score"
    
    @given(
        st.sampled_from(["high", "medium", "low"]),
        st.floats(min_value=0.0, max_value=1.0),
        st.floats(min_value=0.0, max_value=1.0)
    )
    def test_score_monotonicity(self, consistency_level, mccid_consistency, wallet_percentage):
        """
        Property: Better metrics should not decrease confidence score.
        """
        # Create two analysis results with different quality levels
        worse_results = {
            "narrative_analysis": {"consistency_level": "low"},
            "wallet_detection": {"affected_percentage": 0.9},
            "mccid_consistency": {"consistency_percentage": 0.1},
            "commercial_validation": {"confidence": 0.3}
        }
        
        better_results = {
            "narrative_analysis": {"consistency_level": "high"},
            "wallet_detection": {"affected_percentage": 0.1},
            "mccid_consistency": {"consistency_percentage": 0.9},
            "commercial_validation": {"confidence": 0.9}
        }
        
        worse_score = calculate_confidence_score(worse_results)
        better_score = calculate_confidence_score(better_results)
        
        # Property: Better quality should produce higher or equal score
        assert better_score >= worse_score, \
            f"Better quality ({better_score}) should not score lower than worse quality ({worse_score})"
