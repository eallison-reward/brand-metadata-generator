"""
Property-Based Tests for Confirmation Agent

Tests universal properties that must hold for the confirmation agent.

**Property 12: Confirmation Decision Completeness**
Every matched combo must receive exactly one decision: confirm, exclude, or flag for review.
No combo should be left without a decision, and no combo should receive multiple decisions.

**Validates: Requirements 6.5**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from agents.confirmation.tools import review_matched_combos


# Strategy for generating combo records
@st.composite
def combo_record(draw):
    """Generate a valid combo record."""
    ccid = draw(st.integers(min_value=1, max_value=100000))
    
    # Generate narrative with various patterns
    brand_words = ["STARBUCKS", "APPLE", "SHELL", "TARGET", "AMAZON"]
    context_words = ["STORE", "SHOP", "STATION", "CAFE", "MARKET", "INC", "LTD"]
    common_contexts = ["ORCHARD", "FARM", "BEACH", "SEAFOOD", "SHOOTING", "RANGE"]
    
    brand = draw(st.sampled_from(brand_words))
    
    # Sometimes add business context, sometimes contradictory context
    context_type = draw(st.sampled_from(["business", "contradictory", "none", "number"]))
    
    if context_type == "business":
        context = draw(st.sampled_from(context_words))
        narrative = f"{brand} {context}"
    elif context_type == "contradictory":
        context = draw(st.sampled_from(common_contexts))
        narrative = f"{brand} {context}"
    elif context_type == "number":
        number = draw(st.integers(min_value=1, max_value=9999))
        narrative = f"{brand} #{number}"
    else:
        narrative = brand
    
    mccid = draw(st.integers(min_value=1000, max_value=9999))
    
    return {
        "ccid": ccid,
        "narrative": narrative,
        "mccid": mccid
    }


# Strategy for generating MCC table entries
@st.composite
def mcc_entry(draw):
    """Generate a valid MCC table entry."""
    mccid = draw(st.integers(min_value=1000, max_value=9999))
    sectors = ["Food & Beverage", "Technology", "Fuel", "Retail", "Food Stores"]
    sector = draw(st.sampled_from(sectors))
    descriptions = {
        "Food & Beverage": "Eating Places",
        "Technology": "Electronics Stores",
        "Fuel": "Service Stations",
        "Retail": "Misc Retail",
        "Food Stores": "Misc Food Stores"
    }
    
    return {
        "mccid": mccid,
        "sector": sector,
        "mcc_desc": descriptions[sector]
    }


@given(
    brandid=st.integers(min_value=1, max_value=10000),
    brandname=st.sampled_from(["Starbucks", "Apple", "Shell", "Target", "Amazon"]),
    matched_combos=st.lists(combo_record(), min_size=1, max_size=20),
    mcc_table=st.lists(mcc_entry(), min_size=1, max_size=50)
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_property_12_confirmation_decision_completeness(brandid, brandname, matched_combos, mcc_table):
    """
    **Property 12: Confirmation Decision Completeness**
    
    Every matched combo must receive exactly one decision: confirm, exclude, or flag for review.
    
    This property ensures that:
    1. All matched combos are reviewed
    2. Each combo gets exactly one decision
    3. No combo is left without a decision
    4. The sum of confirmed + excluded + ambiguous equals total matched
    
    **Validates: Requirements 6.5**
    """
    # Ensure unique ccids
    ccids = [combo["ccid"] for combo in matched_combos]
    assume(len(ccids) == len(set(ccids)))  # All ccids must be unique
    
    # Create metadata
    metadata = {
        "regex": f"^{brandname.upper()}.*",
        "mccids": [combo["mccid"] for combo in matched_combos[:3]],  # Use some MCCIDs
        "sector": "Food & Beverage"
    }
    
    # Review matched combos
    result = review_matched_combos(
        brandid=brandid,
        brandname=brandname,
        metadata=metadata,
        matched_combos=matched_combos,
        mcc_table=mcc_table
    )
    
    # Property 12: Every combo must receive exactly one decision
    total_matched = result["total_matched"]
    likely_valid = set(result["likely_valid"])
    likely_false_positive = set(result["likely_false_positive"])
    ambiguous = set(result["ambiguous"])
    
    # Check 1: Total matched equals input count
    assert total_matched == len(matched_combos), \
        f"Total matched ({total_matched}) should equal input count ({len(matched_combos)})"
    
    # Check 2: No overlap between decision categories
    assert len(likely_valid & likely_false_positive) == 0, \
        "Combo cannot be both valid and false positive"
    assert len(likely_valid & ambiguous) == 0, \
        "Combo cannot be both valid and ambiguous"
    assert len(likely_false_positive & ambiguous) == 0, \
        "Combo cannot be both false positive and ambiguous"
    
    # Check 3: All combos are categorized
    all_categorized = likely_valid | likely_false_positive | ambiguous
    assert len(all_categorized) == total_matched, \
        f"All combos must be categorized: {len(all_categorized)} categorized vs {total_matched} total"
    
    # Check 4: Sum of categories equals total
    assert len(likely_valid) + len(likely_false_positive) + len(ambiguous) == total_matched, \
        "Sum of decision categories must equal total matched"
    
    # Check 5: All input ccids are present in results
    input_ccids = set(ccids)
    assert all_categorized == input_ccids, \
        "All input ccids must be present in results"
    
    # Check 6: Analysis count matches total
    assert len(result["analysis"]) == total_matched, \
        f"Analysis count ({len(result['analysis'])}) should match total ({total_matched})"
    
    # Check 7: Each analysis has required fields
    for analysis in result["analysis"]:
        assert "ccid" in analysis, "Analysis must include ccid"
        assert "confidence" in analysis, "Analysis must include confidence score"
        assert "recommendation" in analysis, "Analysis must include recommendation"
        assert 0.0 <= analysis["confidence"] <= 1.0, \
            f"Confidence must be between 0 and 1, got {analysis['confidence']}"
        assert analysis["recommendation"] in ["confirm", "exclude", "human_review"], \
            f"Invalid recommendation: {analysis['recommendation']}"


@given(
    brandid=st.integers(min_value=1, max_value=10000),
    brandname=st.sampled_from(["Starbucks", "Apple", "Shell"]),
    combo_count=st.integers(min_value=1, max_value=10)
)
def test_property_12_empty_mcc_table_handling(brandid, brandname, combo_count):
    """
    Property 12 variant: Completeness even with missing MCC data.
    
    Even when MCC table is empty or incomplete, all combos must still
    receive a decision.
    """
    # Generate combos
    matched_combos = [
        {
            "ccid": i,
            "narrative": f"{brandname.upper()} STORE #{i}",
            "mccid": 5812
        }
        for i in range(1, combo_count + 1)
    ]
    
    metadata = {
        "regex": f"^{brandname.upper()}.*",
        "mccids": [5812],
        "sector": "Food & Beverage"
    }
    
    # Review with empty MCC table
    result = review_matched_combos(
        brandid=brandid,
        brandname=brandname,
        metadata=metadata,
        matched_combos=matched_combos,
        mcc_table=[]  # Empty MCC table
    )
    
    # All combos must still be categorized
    total_decisions = (
        len(result["likely_valid"]) +
        len(result["likely_false_positive"]) +
        len(result["ambiguous"])
    )
    
    assert total_decisions == combo_count, \
        f"All {combo_count} combos must be categorized even with empty MCC table"
    assert result["total_matched"] == combo_count


@given(
    brandid=st.integers(min_value=1, max_value=10000),
    brandname=st.sampled_from(["Apple", "Shell", "Target", "Orange", "Mint"]),
    combo_count=st.integers(min_value=1, max_value=10)
)
def test_property_12_common_word_brands(brandid, brandname, combo_count):
    """
    Property 12 variant: Common word brands still get complete decisions.
    
    Brands with common word names (Apple, Shell, etc.) should still have
    all combos categorized, though they may have more ambiguous cases.
    """
    # Generate combos with mixed contexts
    matched_combos = []
    for i in range(1, combo_count + 1):
        if i % 3 == 0:
            # Business context
            narrative = f"{brandname.upper()} STORE #{i}"
        elif i % 3 == 1:
            # Contradictory context
            contradictory = {
                "Apple": "ORCHARD",
                "Shell": "SEAFOOD",
                "Target": "SHOOTING",
                "Orange": "FRUIT",
                "Mint": "HERB"
            }
            narrative = f"{brandname.upper()} {contradictory.get(brandname, 'MARKET')}"
        else:
            # Just brand name
            narrative = brandname.upper()
        
        matched_combos.append({
            "ccid": i,
            "narrative": narrative,
            "mccid": 5000 + i
        })
    
    mcc_table = [
        {"mccid": 5000 + i, "sector": "Retail", "mcc_desc": "Misc Retail"}
        for i in range(1, combo_count + 1)
    ]
    
    metadata = {
        "regex": f"^{brandname.upper()}.*",
        "mccids": [5000 + i for i in range(1, combo_count + 1)],
        "sector": "Retail"
    }
    
    result = review_matched_combos(
        brandid=brandid,
        brandname=brandname,
        metadata=metadata,
        matched_combos=matched_combos,
        mcc_table=mcc_table
    )
    
    # All combos must be categorized
    total_decisions = (
        len(result["likely_valid"]) +
        len(result["likely_false_positive"]) +
        len(result["ambiguous"])
    )
    
    assert total_decisions == combo_count, \
        f"All {combo_count} combos must be categorized for common word brand {brandname}"
    
    # Common word brands should have some ambiguous or excluded cases
    # (This is a soft assertion - not all runs will have them, but many should)
    if combo_count >= 3:
        # At least some combos should be flagged as issues
        assert (len(result["likely_false_positive"]) + len(result["ambiguous"])) > 0, \
            f"Common word brand {brandname} should have some ambiguous/excluded combos"


@given(
    brandid=st.integers(min_value=1, max_value=10000)
)
def test_property_12_single_combo(brandid):
    """
    Property 12 variant: Single combo edge case.
    
    Even with just one combo, it must receive a decision.
    """
    matched_combos = [
        {"ccid": 1, "narrative": "STARBUCKS STORE #123", "mccid": 5812}
    ]
    
    mcc_table = [
        {"mccid": 5812, "sector": "Food & Beverage", "mcc_desc": "Eating Places"}
    ]
    
    metadata = {
        "regex": "^STARBUCKS.*",
        "mccids": [5812],
        "sector": "Food & Beverage"
    }
    
    result = review_matched_combos(
        brandid=brandid,
        brandname="Starbucks",
        metadata=metadata,
        matched_combos=matched_combos,
        mcc_table=mcc_table
    )
    
    # Single combo must be categorized
    assert result["total_matched"] == 1
    total_decisions = (
        len(result["likely_valid"]) +
        len(result["likely_false_positive"]) +
        len(result["ambiguous"])
    )
    assert total_decisions == 1, "Single combo must receive a decision"
