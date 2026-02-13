"""
Evaluator Agent Tools

This module provides tools for the Evaluator Agent to assess data quality,
identify issues, and calculate confidence scores for brand metadata generation.

The Evaluator Agent:
- Analyzes narrative patterns for consistency
- Detects payment wallet indicators (PAYPAL, PP, SQ, SQUARE)
- Assesses MCCID consistency with brand sector
- Calculates confidence scores
- Generates production prompts for Metadata Production Agent
"""

import re
from typing import Dict, List, Any
from collections import Counter
import statistics


def analyze_narratives(brandid: int, combos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze narrative patterns for consistency across combo records.
    
    Calculates metrics like:
    - Unique narrative patterns
    - Pattern frequency distribution
    - Narrative variance (coefficient of variation)
    - Common prefixes and suffixes
    
    Args:
        brandid: Brand identifier
        combos: List of combo records with 'narrative' field
        
    Returns:
        Dictionary with analysis results including:
        - pattern_count: Number of unique narrative patterns
        - variance_score: Coefficient of variation (0.0 = consistent, 1.0+ = highly variable)
        - common_patterns: Most frequent narrative patterns
        - consistency_level: "high", "medium", or "low"
    
    Requirements: 4.1, 4.3
    """
    if not combos:
        return {
            "brandid": brandid,
            "pattern_count": 0,
            "variance_score": 0.0,
            "common_patterns": [],
            "consistency_level": "unknown",
            "error": "No combos provided"
        }
    
    # Extract narratives
    narratives = [combo.get("narrative", "") for combo in combos if combo.get("narrative")]
    
    if not narratives:
        return {
            "brandid": brandid,
            "pattern_count": 0,
            "variance_score": 0.0,
            "common_patterns": [],
            "consistency_level": "unknown",
            "error": "No narratives found in combos"
        }
    
    # Count unique patterns
    pattern_counter = Counter(narratives)
    unique_patterns = len(pattern_counter)
    total_narratives = len(narratives)
    
    # Calculate variance (coefficient of variation)
    # Higher CV = more variance = less consistency
    frequencies = list(pattern_counter.values())
    if len(frequencies) > 1:
        mean_freq = statistics.mean(frequencies)
        stdev_freq = statistics.stdev(frequencies)
        variance_score = stdev_freq / mean_freq if mean_freq > 0 else 0.0
    else:
        variance_score = 0.0  # Only one pattern = perfect consistency
    
    # Get most common patterns (top 5)
    common_patterns = [
        {"pattern": pattern, "count": count, "percentage": count / total_narratives}
        for pattern, count in pattern_counter.most_common(5)
    ]
    
    # Determine consistency level
    # Low variance (< 0.5) = high consistency
    # Medium variance (0.5 - 1.5) = medium consistency
    # High variance (> 1.5) = low consistency
    if variance_score < 0.5:
        consistency_level = "high"
    elif variance_score < 1.5:
        consistency_level = "medium"
    else:
        consistency_level = "low"
    
    return {
        "brandid": brandid,
        "pattern_count": unique_patterns,
        "total_narratives": total_narratives,
        "variance_score": round(variance_score, 3),
        "common_patterns": common_patterns,
        "consistency_level": consistency_level
    }


def detect_payment_wallets(narratives: List[str]) -> Dict[str, Any]:
    """
    Identify payment wallet indicators in narratives.
    
    Detects case-insensitive patterns:
    - PAYPAL
    - PP (as prefix: "PP *")
    - SQ (as prefix: "SQ *")
    - SQUARE
    
    Args:
        narratives: List of narrative strings to analyze
        
    Returns:
        Dictionary with detection results including:
        - wallet_detected: Boolean indicating if any wallets found
        - wallet_indicators: List of detected wallet types
        - affected_count: Number of narratives with wallet indicators
        - affected_percentage: Percentage of narratives affected
        - affected_indices: Indices of affected narratives
    
    Requirements: 3.1, 3.2
    """
    if not narratives:
        return {
            "wallet_detected": False,
            "wallet_indicators": [],
            "affected_count": 0,
            "affected_percentage": 0.0,
            "affected_indices": []
        }
    
    # Wallet patterns (case-insensitive)
    wallet_patterns = {
        "PAYPAL": re.compile(r'\bPAYPAL\b', re.IGNORECASE),
        "PP": re.compile(r'\bPP\s*\*', re.IGNORECASE),
        "SQ": re.compile(r'\bSQ\s*\*', re.IGNORECASE),
        "SQUARE": re.compile(r'\bSQUARE\b', re.IGNORECASE)
    }
    
    wallet_indicators = set()
    affected_indices = []
    
    for idx, narrative in enumerate(narratives):
        if not narrative:
            continue
            
        for wallet_type, pattern in wallet_patterns.items():
            if pattern.search(narrative):
                wallet_indicators.add(wallet_type)
                affected_indices.append(idx)
                break  # Count each narrative only once
    
    affected_count = len(affected_indices)
    total_count = len(narratives)
    affected_percentage = (affected_count / total_count) if total_count > 0 else 0.0
    
    return {
        "wallet_detected": len(wallet_indicators) > 0,
        "wallet_indicators": sorted(list(wallet_indicators)),
        "affected_count": affected_count,
        "affected_percentage": round(affected_percentage, 3),
        "affected_indices": affected_indices
    }


def assess_mccid_consistency(brandid: int, mccids: List[int], sector: str, 
                            mcc_table: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check MCCID alignment with brand sector.
    
    Analyzes whether the MCCIDs associated with a brand are consistent
    with the brand's sector classification.
    
    Args:
        brandid: Brand identifier
        mccids: List of MCCID values associated with the brand
        sector: Brand's sector classification
        mcc_table: List of MCC records with 'mccid' and 'sector' fields
        
    Returns:
        Dictionary with consistency assessment including:
        - consistent: Boolean indicating overall consistency
        - matching_sector_count: Number of MCCIDs matching brand sector
        - mismatched_mccids: List of MCCIDs with different sectors
        - consistency_percentage: Percentage of MCCIDs matching sector
        - wallet_specific_mccids: MCCIDs likely from payment wallets
    
    Requirements: 4.2, 4.4, 3.4
    """
    if not mccids:
        return {
            "brandid": brandid,
            "consistent": True,
            "matching_sector_count": 0,
            "mismatched_mccids": [],
            "consistency_percentage": 1.0,
            "wallet_specific_mccids": [],
            "error": "No MCCIDs provided"
        }
    
    # Create MCC lookup dictionary
    mcc_lookup = {mcc["mccid"]: mcc.get("sector", "Unknown") for mcc in mcc_table}
    
    # Known wallet-specific MCCIDs
    # 7399 = Business Services (Square, PayPal often use this)
    # 6012 = Financial Institutions (PayPal)
    # 7299 = Miscellaneous Personal Services
    wallet_mccids = {7399, 6012, 7299}
    
    matching_count = 0
    mismatched = []
    wallet_specific = []
    
    for mccid in mccids:
        mcc_sector = mcc_lookup.get(mccid, "Unknown")
        
        # Check if wallet-specific
        if mccid in wallet_mccids:
            wallet_specific.append({
                "mccid": mccid,
                "sector": mcc_sector,
                "reason": "Common payment wallet MCCID"
            })
        
        # Check sector alignment
        if mcc_sector == sector:
            matching_count += 1
        elif mcc_sector != "Unknown":
            mismatched.append({
                "mccid": mccid,
                "expected_sector": sector,
                "actual_sector": mcc_sector
            })
    
    total_count = len(mccids)
    consistency_percentage = (matching_count / total_count) if total_count > 0 else 0.0
    
    # Consider consistent if >50% of MCCIDs match sector
    consistent = consistency_percentage > 0.5
    
    return {
        "brandid": brandid,
        "consistent": consistent,
        "matching_sector_count": matching_count,
        "total_mccids": total_count,
        "mismatched_mccids": mismatched,
        "consistency_percentage": round(consistency_percentage, 3),
        "wallet_specific_mccids": wallet_specific
    }


def calculate_confidence_score(analysis_results: Dict[str, Any]) -> float:
    """
    Calculate confidence score based on data quality metrics.
    
    Combines multiple factors:
    - Narrative consistency (40% weight)
    - MCCID consistency (30% weight)
    - Wallet impact (20% weight)
    - Commercial validation (10% weight)
    
    Args:
        analysis_results: Dictionary containing:
            - narrative_analysis: Results from analyze_narratives
            - wallet_detection: Results from detect_payment_wallets
            - mccid_consistency: Results from assess_mccid_consistency
            - commercial_validation: Optional results from commercial assessment
            
    Returns:
        Float between 0.0 and 1.0 representing confidence score
    
    Requirements: 4.6
    """
    # Extract components
    narrative_analysis = analysis_results.get("narrative_analysis", {})
    wallet_detection = analysis_results.get("wallet_detection", {})
    mccid_consistency = analysis_results.get("mccid_consistency", {})
    commercial_validation = analysis_results.get("commercial_validation", {})
    
    # Narrative consistency score (40% weight)
    # High consistency = high score, low consistency = low score
    consistency_level = narrative_analysis.get("consistency_level", "unknown")
    if consistency_level == "high":
        narrative_score = 1.0
    elif consistency_level == "medium":
        narrative_score = 0.6
    elif consistency_level == "low":
        narrative_score = 0.3
    else:
        narrative_score = 0.5  # Unknown
    
    # MCCID consistency score (30% weight)
    mccid_score = mccid_consistency.get("consistency_percentage", 0.5)
    
    # Wallet impact score (20% weight)
    # Less wallet contamination = higher score
    wallet_percentage = wallet_detection.get("affected_percentage", 0.0)
    if wallet_percentage < 0.2:
        wallet_score = 1.0  # Minimal wallet impact
    elif wallet_percentage < 0.5:
        wallet_score = 0.7  # Moderate wallet impact
    else:
        wallet_score = 0.4  # High wallet impact
    
    # Commercial validation score (10% weight)
    commercial_confidence = commercial_validation.get("confidence", 0.8)
    
    # Weighted average
    confidence_score = (
        narrative_score * 0.4 +
        mccid_score * 0.3 +
        wallet_score * 0.2 +
        commercial_confidence * 0.1
    )
    
    # Ensure score is between 0.0 and 1.0
    confidence_score = max(0.0, min(1.0, confidence_score))
    
    return round(confidence_score, 3)


def generate_production_prompt(brandid: int, brandname: str, issues: List[Dict[str, Any]], 
                               wallet_info: Dict[str, Any]) -> str:
    """
    Generate guidance prompt for Metadata Production Agent.
    
    Creates specific instructions based on identified issues to help
    the Metadata Production Agent generate accurate regex and MCCID lists.
    
    Args:
        brandid: Brand identifier
        brandname: Brand name
        issues: List of identified issues from evaluation
        wallet_info: Wallet detection results
        
    Returns:
        String containing detailed guidance for metadata production
    
    Requirements: 4.5, 3.5
    """
    prompt_parts = [
        f"Generate metadata for Brand {brandid}: {brandname}",
        ""
    ]
    
    # Wallet handling guidance
    if wallet_info.get("wallet_detected", False):
        wallet_indicators = wallet_info.get("wallet_indicators", [])
        affected_percentage = wallet_info.get("affected_percentage", 0.0)
        
        prompt_parts.append("PAYMENT WALLET DETECTED:")
        prompt_parts.append(f"- Wallet types: {', '.join(wallet_indicators)}")
        prompt_parts.append(f"- Affected narratives: {affected_percentage:.1%}")
        
        if affected_percentage < 0.2:
            prompt_parts.append("- Strategy: Focus on clean narratives, ignore wallet patterns")
        elif affected_percentage < 0.5:
            prompt_parts.append("- Strategy: Generate regex that matches both clean and wallet-prefixed narratives")
            prompt_parts.append("- Use optional non-capturing groups for wallet prefixes")
        else:
            prompt_parts.append("- Strategy: Generate regex excluding wallet prefixes")
            prompt_parts.append("- Focus on brand name after wallet text")
        
        prompt_parts.append("")
    
    # Issue-specific guidance
    if issues:
        prompt_parts.append("IDENTIFIED ISSUES:")
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            description = issue.get("description", "")
            
            if issue_type == "payment_wallet":
                prompt_parts.append(f"- {description}")
                prompt_parts.append("  Action: Exclude wallet-specific MCCIDs from legitimate list")
            
            elif issue_type == "mccid_mismatch":
                prompt_parts.append(f"- {description}")
                prompt_parts.append("  Action: Review MCCID list, prioritize sector-aligned MCCIDs")
            
            elif issue_type == "narrative_inconsistency":
                prompt_parts.append(f"- {description}")
                prompt_parts.append("  Action: Generate flexible regex to capture pattern variations")
            
            else:
                prompt_parts.append(f"- {description}")
        
        prompt_parts.append("")
    
    # General guidance
    prompt_parts.append("REQUIREMENTS:")
    prompt_parts.append("- Regex must match brand name variations")
    prompt_parts.append("- Regex should be specific enough to avoid false positives")
    prompt_parts.append("- MCCID list should include only legitimate business MCCIDs")
    prompt_parts.append("- Exclude wallet-specific MCCIDs (7399, 6012, 7299)")
    prompt_parts.append("- Test regex against sample narratives for coverage")
    
    return "\n".join(prompt_parts)


def detect_ties(brandid: int, combos: List[Dict[str, Any]], 
                all_brand_metadata: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Identify combos that match multiple brands (ties).
    
    This is a preliminary tie detection based on narrative/MCCID patterns.
    Full tie resolution happens after metadata is applied to all combos.
    
    Args:
        brandid: Current brand identifier
        combos: List of combo records for this brand
        all_brand_metadata: Dictionary of all brands' metadata (if available)
        
    Returns:
        Dictionary with tie detection results including:
        - ties_detected: Boolean indicating if ties found
        - potential_ties: List of combos that might match multiple brands
        - tie_count: Number of potential ties
    
    Requirements: 7.1
    """
    # This is a placeholder for preliminary tie detection
    # Full tie detection happens in Phase 3 after all metadata is generated
    # and applied to combos
    
    return {
        "brandid": brandid,
        "ties_detected": False,
        "potential_ties": [],
        "tie_count": 0,
        "note": "Full tie detection occurs after metadata application in Phase 3"
    }
