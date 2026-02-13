"""
Confirmation Agent Tools

This module provides tools for the Confirmation Agent to review combos matched
to brands AFTER metadata application and exclude ambiguous matches.

The Confirmation Agent:
- Reviews combos that matched a brand's regex and MCCID metadata
- Identifies false positives where common words match unrelated combos
- Excludes combos with low confidence of belonging to the brand
- Handles ambiguous brand names (e.g., "Apple" matching both Apple Inc. and apple orchards)
- Provides final confirmation on which combos truly belong to each brand
"""

import re
from typing import Dict, List, Any


def review_matched_combos(brandid: int, brandname: str, metadata: Dict[str, Any],
                         matched_combos: List[Dict[str, Any]], 
                         mcc_table: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Review combos that matched a brand's regex and MCCID metadata.
    
    Evaluates each matched combo to determine if it truly belongs to the brand
    or is a false positive. Considers:
    - Narrative context and brand name usage
    - MCCID alignment with brand sector
    - Common word ambiguity (e.g., "Apple" could be fruit or tech company)
    - Pattern specificity
    
    Args:
        brandid: Brand identifier
        brandname: Brand name
        metadata: Brand metadata with 'regex' and 'mccids' fields
        matched_combos: List of combo records that matched the metadata
        mcc_table: List of MCC records for sector validation
        
    Returns:
        Dictionary with review results including:
        - total_matched: Total combos reviewed
        - likely_valid: Combos that appear to belong to brand
        - likely_false_positive: Combos that appear to be false matches
        - ambiguous: Combos requiring human review
        - analysis: Detailed analysis per combo
    
    Requirements: 6.5
    """
    if not matched_combos:
        return {
            "brandid": brandid,
            "brandname": brandname,
            "total_matched": 0,
            "likely_valid": [],
            "likely_false_positive": [],
            "ambiguous": [],
            "analysis": []
        }
    
    # Create MCC lookup
    mcc_lookup = {mcc["mccid"]: mcc for mcc in mcc_table}
    brand_sector = metadata.get("sector", "Unknown")
    
    # Analyze each combo
    likely_valid = []
    likely_false_positive = []
    ambiguous = []
    analysis = []
    
    for combo in matched_combos:
        ccid = combo.get("ccid")
        narrative = combo.get("narrative", "")
        mccid = combo.get("mccid")
        
        # Get MCC info
        mcc_info = mcc_lookup.get(mccid, {})
        mcc_sector = mcc_info.get("sector", "Unknown")
        mcc_desc = mcc_info.get("mcc_desc", "Unknown")
        
        # Analyze combo
        combo_analysis = _analyze_combo_match(
            brandname, narrative, mccid, mcc_sector, 
            mcc_desc, brand_sector
        )
        
        combo_analysis["ccid"] = ccid
        combo_analysis["narrative"] = narrative
        combo_analysis["mccid"] = mccid
        
        analysis.append(combo_analysis)
        
        # Categorize based on confidence
        if combo_analysis["confidence"] >= 0.8:
            likely_valid.append(ccid)
        elif combo_analysis["confidence"] <= 0.4:
            likely_false_positive.append(ccid)
        else:
            ambiguous.append(ccid)
    
    return {
        "brandid": brandid,
        "brandname": brandname,
        "total_matched": len(matched_combos),
        "likely_valid": likely_valid,
        "likely_false_positive": likely_false_positive,
        "ambiguous": ambiguous,
        "analysis": analysis
    }


def _analyze_combo_match(brandname: str, narrative: str, mccid: int,
                        mcc_sector: str, mcc_desc: str, 
                        brand_sector: str) -> Dict[str, Any]:
    """
    Analyze a single combo match to determine confidence.
    
    Internal helper function that evaluates multiple factors:
    - Brand name context in narrative
    - MCCID sector alignment
    - Ambiguous word detection
    - Pattern specificity
    """
    confidence_factors = []
    confidence_score = 0.5  # Start neutral
    
    # Factor 1: Sector alignment (30% weight)
    if mcc_sector == brand_sector:
        confidence_score += 0.3
        confidence_factors.append("MCCID sector matches brand sector")
    elif mcc_sector != "Unknown":
        confidence_score -= 0.2
        confidence_factors.append(f"MCCID sector mismatch: {mcc_sector} vs {brand_sector}")
    
    # Factor 2: Brand name context (40% weight)
    # Check if brand name appears with business context indicators
    business_indicators = [
        r'\b(STORE|SHOP|MARKET|STATION|CAFE|RESTAURANT|INC|LTD|LLC|CORP)\b',
        r'#\d+',  # Store number
        r'\d{3,}',  # Long numbers (often store IDs)
        r'\.(COM|NET|ORG|CO\.UK|IO)\b',  # Domain extensions
        r'\b(PRIME|PLUS|PRO|PREMIUM)\b',  # Service tiers
    ]
    
    has_business_context = any(
        re.search(pattern, narrative, re.IGNORECASE) 
        for pattern in business_indicators
    )
    
    if has_business_context:
        confidence_score += 0.2
        confidence_factors.append("Business context indicators present")
    
    # Check for brand name specificity
    brandname_lower = brandname.lower()
    narrative_lower = narrative.lower()
    
    # If brand name is very short or common word, be more cautious
    common_words = {
        'apple', 'shell', 'target', 'amazon', 'orange', 'mint',
        'square', 'circle', 'star', 'sun', 'moon', 'crown'
    }
    
    if brandname_lower in common_words:
        # Need strong context for common words
        if has_business_context:
            confidence_score += 0.1
            confidence_factors.append("Common word but has business context")
        else:
            confidence_score -= 0.3
            confidence_factors.append("Common word without business context - likely false positive")
    else:
        # Specific brand name
        confidence_score += 0.1
        confidence_factors.append("Specific brand name")
    
    # Factor 3: Narrative length and detail (10% weight)
    if len(narrative) > 20:
        confidence_score += 0.05
        confidence_factors.append("Detailed narrative")
    elif len(narrative) < 10:
        confidence_score -= 0.05
        confidence_factors.append("Very short narrative")
    
    # Factor 4: Check for contradictory terms (20% weight)
    # e.g., "APPLE ORCHARD" when brand is Apple Inc.
    contradictory_patterns = {
        'apple': [r'\b(ORCHARD|FARM|FRUIT|PRODUCE|MARKET)\b'],
        'shell': [r'\b(BEACH|SEAFOOD|FISH|OCEAN)\b'],
        'target': [r'\b(SHOOTING|RANGE|PRACTICE)\b'],
        'amazon': [r'\b(RIVER|RAINFOREST|JUNGLE)\b'],
    }
    
    if brandname_lower in contradictory_patterns:
        for pattern in contradictory_patterns[brandname_lower]:
            if re.search(pattern, narrative, re.IGNORECASE):
                confidence_score -= 0.4
                confidence_factors.append(f"Contradictory term detected - likely different entity")
                break
    
    # Ensure score stays in valid range
    confidence_score = max(0.0, min(1.0, confidence_score))
    
    # Determine recommendation
    if confidence_score >= 0.8:
        recommendation = "confirm"
    elif confidence_score <= 0.4:
        recommendation = "exclude"
    else:
        recommendation = "human_review"
    
    return {
        "confidence": round(confidence_score, 3),
        "recommendation": recommendation,
        "factors": confidence_factors,
        "mcc_desc": mcc_desc
    }


def confirm_combo(ccid: int, brandid: int, reason: str = "") -> Dict[str, Any]:
    """
    Confirm that a combo belongs to the brand.
    
    Args:
        ccid: Combo identifier
        brandid: Brand identifier
        reason: Optional explanation for confirmation
        
    Returns:
        Dictionary with confirmation result
    
    Requirements: 6.5
    """
    return {
        "action": "confirm",
        "ccid": ccid,
        "brandid": brandid,
        "reason": reason or "Combo confirmed to belong to brand",
        "timestamp": "2026-02-13T00:00:00Z"
    }


def exclude_combo(ccid: int, brandid: int, reason: str) -> Dict[str, Any]:
    """
    Exclude a combo from the brand (false positive).
    
    Args:
        ccid: Combo identifier
        brandid: Brand identifier
        reason: Explanation for exclusion (required)
        
    Returns:
        Dictionary with exclusion result
    
    Requirements: 6.5
    """
    if not reason:
        reason = "Combo excluded as false positive"
    
    return {
        "action": "exclude",
        "ccid": ccid,
        "brandid": brandid,
        "reason": reason,
        "timestamp": "2026-02-13T00:00:00Z"
    }


def flag_for_human_review(ccid: int, brandid: int, reason: str) -> Dict[str, Any]:
    """
    Flag a combo for human review due to ambiguity.
    
    Args:
        ccid: Combo identifier
        brandid: Brand identifier
        reason: Explanation for why human review is needed
        
    Returns:
        Dictionary with flagging result
    
    Requirements: 6.5
    """
    if not reason:
        reason = "Ambiguous match requiring human judgment"
    
    return {
        "action": "flag_for_review",
        "ccid": ccid,
        "brandid": brandid,
        "reason": reason,
        "requires_human_review": True,
        "timestamp": "2026-02-13T00:00:00Z"
    }
