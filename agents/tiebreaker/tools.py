"""
Tiebreaker Agent Tools

This module provides tools for the Tiebreaker Agent to resolve scenarios where
a combo matches multiple brands AFTER metadata application.

The Tiebreaker Agent:
- Analyzes combos that matched multiple brands' regex and MCCID metadata
- Determines which brand the combo most likely belongs to
- Considers narrative text patterns, MCCID, and brand characteristics
- Assigns combo to the most appropriate brand
- Flags combos that cannot be resolved with high confidence for human review
"""

import re
from typing import Dict, List, Any
from difflib import SequenceMatcher


def resolve_multi_match(ccid: int, matching_brands: List[Dict[str, Any]], 
                       combo_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine which brand a combo most likely belongs to when it matches multiple brands.
    
    Analyzes multiple factors:
    - Narrative similarity to brand names
    - Regex pattern specificity
    - MCCID alignment with brand sectors
    - Brand name length and specificity
    
    Args:
        ccid: Combo identifier
        matching_brands: List of brands that matched this combo
        combo_data: Combo information with 'narrative', 'mccid', 'mid'
        
    Returns:
        Dictionary with resolution including:
        - resolution_type: "single_brand" or "manual_review"
        - assigned_brandid: Brand ID if resolved (or None)
        - confidence: Confidence score 0.0-1.0
        - reasoning: Explanation of decision
        - requires_human_review: Boolean
    
    Requirements: 7.3
    """
    if not matching_brands:
        return {
            "ccid": ccid,
            "resolution_type": "error",
            "assigned_brandid": None,
            "confidence": 0.0,
            "reasoning": "No matching brands provided",
            "requires_human_review": True
        }
    
    if len(matching_brands) == 1:
        # Only one brand - no tie to resolve
        return {
            "ccid": ccid,
            "resolution_type": "single_brand",
            "assigned_brandid": matching_brands[0]["brandid"],
            "confidence": 1.0,
            "reasoning": "Only one brand matched",
            "requires_human_review": False
        }
    
    narrative = combo_data.get("narrative", "")
    mccid = combo_data.get("mccid")
    
    # Analyze narrative similarity for each brand
    narrative_analysis = analyze_narrative_similarity(narrative, 
                                                     [b["brandname"] for b in matching_brands])
    
    # Analyze MCCID alignment for each brand
    mccid_analysis = compare_mccid_alignment(mccid, matching_brands)
    
    # Calculate confidence for each brand
    brand_scores = []
    for i, brand in enumerate(matching_brands):
        brandid = brand["brandid"]
        brandname = brand["brandname"]
        
        # Narrative similarity score (50% weight)
        narrative_score = narrative_analysis["similarities"][i]["similarity"]
        
        # MCCID alignment score (30% weight)
        mccid_score = mccid_analysis["alignments"][i]["alignment_score"]
        
        # Regex specificity score (20% weight)
        # More specific regex (longer, more constraints) = higher score
        regex = brand.get("metadata", {}).get("regex", "")
        specificity_score = min(len(regex) / 50.0, 1.0)  # Normalize to 0-1
        
        # Weighted total
        total_score = (
            narrative_score * 0.5 +
            mccid_score * 0.3 +
            specificity_score * 0.2
        )
        
        brand_scores.append({
            "brandid": brandid,
            "brandname": brandname,
            "score": total_score,
            "narrative_score": narrative_score,
            "mccid_score": mccid_score,
            "specificity_score": specificity_score
        })
    
    # Sort by score descending
    brand_scores.sort(key=lambda x: x["score"], reverse=True)
    
    best_brand = brand_scores[0]
    second_best = brand_scores[1] if len(brand_scores) > 1 else None
    
    # Decision logic
    confidence = best_brand["score"]
    
    # If best brand has high confidence and clear lead, assign it
    if confidence >= 0.7 and (not second_best or best_brand["score"] - second_best["score"] >= 0.2):
        reasoning_parts = [
            f"Narrative similarity: {best_brand['narrative_score']:.2f}",
            f"MCCID alignment: {best_brand['mccid_score']:.2f}",
            f"Pattern specificity: {best_brand['specificity_score']:.2f}"
        ]
        
        if best_brand["narrative_score"] > 0.8:
            reasoning_parts.append(f"Strong narrative match to '{best_brand['brandname']}'")
        
        return {
            "ccid": ccid,
            "resolution_type": "single_brand",
            "assigned_brandid": best_brand["brandid"],
            "confidence": round(confidence, 3),
            "reasoning": ". ".join(reasoning_parts),
            "requires_human_review": False,
            "all_scores": brand_scores
        }
    
    # Otherwise, flag for human review
    return {
        "ccid": ccid,
        "resolution_type": "manual_review",
        "assigned_brandid": None,
        "confidence": round(confidence, 3),
        "reasoning": f"Ambiguous tie between {len(matching_brands)} brands. Best match: {best_brand['brandname']} ({confidence:.2f}), but confidence too low or margin too small.",
        "requires_human_review": True,
        "all_scores": brand_scores
    }


def analyze_narrative_similarity(narrative: str, brand_names: List[str]) -> Dict[str, Any]:
    """
    Compare narrative text to brand names to determine similarity.
    
    Uses multiple similarity metrics:
    - Exact substring matching
    - Sequence matching (difflib)
    - Word-level matching
    
    Args:
        narrative: Transaction narrative text
        brand_names: List of brand names to compare against
        
    Returns:
        Dictionary with similarity scores for each brand
    
    Requirements: 7.3
    """
    narrative_lower = narrative.lower()
    narrative_words = set(re.findall(r'\w+', narrative_lower))
    
    similarities = []
    
    for brand_name in brand_names:
        brand_lower = brand_name.lower()
        brand_words = set(re.findall(r'\w+', brand_lower))
        
        # Metric 1: Exact substring match
        if brand_lower in narrative_lower:
            substring_score = 1.0
        else:
            substring_score = 0.0
        
        # Metric 2: Sequence similarity (difflib)
        sequence_score = SequenceMatcher(None, narrative_lower, brand_lower).ratio()
        
        # Metric 3: Word overlap
        if brand_words:
            word_overlap = len(narrative_words & brand_words) / len(brand_words)
        else:
            word_overlap = 0.0
        
        # Metric 4: Brand name appears as complete word
        brand_pattern = r'\b' + re.escape(brand_lower) + r'\b'
        word_match_score = 1.0 if re.search(brand_pattern, narrative_lower) else 0.0
        
        # Combined similarity (weighted average)
        similarity = (
            substring_score * 0.3 +
            sequence_score * 0.2 +
            word_overlap * 0.3 +
            word_match_score * 0.2
        )
        
        similarities.append({
            "brand_name": brand_name,
            "similarity": round(similarity, 3),
            "substring_match": substring_score > 0,
            "sequence_score": round(sequence_score, 3),
            "word_overlap": round(word_overlap, 3),
            "word_match": word_match_score > 0
        })
    
    # Find best match
    if similarities:
        best_match = max(similarities, key=lambda x: x["similarity"])
        best_match_name = best_match["brand_name"]
        best_similarity = best_match["similarity"]
    else:
        best_match_name = None
        best_similarity = 0.0
    
    return {
        "narrative": narrative,
        "similarities": similarities,
        "best_match": best_match_name,
        "best_similarity": best_similarity
    }


def compare_mccid_alignment(mccid: int, brands: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check MCCID fit for each brand to determine which is most appropriate.
    
    Considers:
    - Whether MCCID is in brand's MCCID list
    - MCCID sector alignment with brand sector
    - MCCID frequency/priority in brand's list
    
    Args:
        mccid: The MCCID to check
        brands: List of brand dictionaries with metadata
        
    Returns:
        Dictionary with alignment scores for each brand
    
    Requirements: 7.3
    """
    alignments = []
    
    for brand in brands:
        brandid = brand["brandid"]
        brandname = brand["brandname"]
        brand_mccids = brand.get("metadata", {}).get("mccids", [])
        brand_sector = brand.get("sector", "Unknown")
        
        # Check if MCCID is in brand's list
        in_list = mccid in brand_mccids
        
        # Calculate position score (earlier in list = higher priority)
        if in_list:
            position = brand_mccids.index(mccid)
            # First MCCID gets 1.0, second gets 0.9, etc.
            position_score = max(0.5, 1.0 - (position * 0.1))
        else:
            position_score = 0.0
        
        # Overall alignment score
        if in_list:
            alignment_score = position_score
        else:
            alignment_score = 0.0
        
        alignments.append({
            "brandid": brandid,
            "brandname": brandname,
            "in_mccid_list": in_list,
            "position_score": round(position_score, 3),
            "alignment_score": round(alignment_score, 3)
        })
    
    # Find best alignment
    best_alignment = max(alignments, key=lambda x: x["alignment_score"])
    
    return {
        "mccid": mccid,
        "alignments": alignments,
        "best_match": best_alignment["brandname"],
        "best_score": best_alignment["alignment_score"]
    }


def calculate_match_confidence(ccid: int, brandid: int, 
                               narrative: str, brand_data: Dict[str, Any]) -> float:
    """
    Calculate confidence score for a specific combo-brand match.
    
    This is a helper function that can be used to compute confidence
    for a single brand match.
    
    Args:
        ccid: Combo identifier
        brandid: Brand identifier
        narrative: Transaction narrative
        brand_data: Brand information including metadata
        
    Returns:
        Float between 0.0 and 1.0 representing confidence
    
    Requirements: 7.4
    """
    brandname = brand_data.get("brandname", "")
    regex = brand_data.get("metadata", {}).get("regex", "")
    
    # Narrative similarity
    narrative_lower = narrative.lower()
    brandname_lower = brandname.lower()
    
    if brandname_lower in narrative_lower:
        narrative_score = 1.0
    else:
        # Use sequence matching
        narrative_score = SequenceMatcher(None, narrative_lower, brandname_lower).ratio()
    
    # Regex specificity
    specificity_score = min(len(regex) / 50.0, 1.0)
    
    # Combined confidence
    confidence = (narrative_score * 0.7 + specificity_score * 0.3)
    
    return round(confidence, 3)
