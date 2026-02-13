"""
Metadata Production Agent Tools

This module provides tools for the Metadata Production Agent to generate
regex patterns and MCCID lists based on evaluator findings and feedback.

The Metadata Production Agent:
- Generates regex patterns for narrative matching
- Generates lists of legitimate MCCIDs for each brand
- Excludes payment wallet text from regex patterns
- Incorporates feedback for iterative refinement
- Validates pattern coverage against sample narratives
"""

import re
from typing import Dict, List, Any
from collections import Counter


# Known wallet-specific MCCIDs to exclude
WALLET_MCCIDS = {7399, 6012, 7299}

# Wallet text patterns to filter
WALLET_PATTERNS = [
    r'\bPAYPAL\s*\*?\s*',
    r'\bPP\s*\*\s*',
    r'\bSQ\s*\*\s*',
    r'\bSQUARE\s+'
]


def generate_regex(brandid: int, narratives: List[str], guidance: str = "") -> str:
    """
    Generate regex pattern for narrative matching.
    
    Analyzes narrative patterns to create a regex that matches brand-specific
    text while excluding wallet prefixes and minimizing false positives.
    
    Args:
        brandid: Brand identifier
        narratives: List of narrative strings to analyze
        guidance: Optional guidance from Evaluator Agent
        
    Returns:
        Regex pattern string
    
    Requirements: 2.1, 3.3
    """
    if not narratives:
        return ""
    
    # Extract common patterns from narratives
    # Remove wallet prefixes first
    cleaned_narratives = []
    for narrative in narratives:
        cleaned = narrative
        for pattern in WALLET_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        cleaned_narratives.append(cleaned.strip())
    
    # Find common words/tokens
    all_tokens = []
    for narrative in cleaned_narratives:
        # Split on whitespace and special characters
        tokens = re.findall(r'\b[A-Z][A-Z0-9]*\b', narrative.upper())
        all_tokens.extend(tokens)
    
    # Get most common tokens (likely brand name variations)
    token_counts = Counter(all_tokens)
    common_tokens = [token for token, count in token_counts.most_common(5) 
                    if count >= len(narratives) * 0.3]  # Appears in 30%+ of narratives
    
    if not common_tokens:
        # Fallback: use first word from most common narrative
        most_common_narrative = Counter(cleaned_narratives).most_common(1)[0][0]
        first_word = re.match(r'\b([A-Z][A-Z0-9]*)\b', most_common_narrative.upper())
        if first_word:
            common_tokens = [first_word.group(1)]
    
    # Build regex pattern
    if len(common_tokens) == 1:
        # Single brand name variant
        pattern = f"^{common_tokens[0]}"
    else:
        # Multiple variants - use alternation
        pattern = f"^(?:{'|'.join(common_tokens)})"
    
    # Add optional common suffixes (store numbers, etc.)
    pattern += r"(?:\s+#?\d+|\s+STORE|\s+STATION)?"
    
    return pattern


def generate_mccid_list(brandid: int, mccids: List[int], guidance: str = "") -> List[int]:
    """
    Generate list of legitimate MCCIDs for a brand.
    
    Filters out wallet-specific MCCIDs and returns deduplicated list
    of MCCIDs that represent the brand's actual business.
    
    Args:
        brandid: Brand identifier
        mccids: List of MCCID values from combo records
        guidance: Optional guidance from Evaluator Agent
        
    Returns:
        Filtered and deduplicated list of MCCIDs
    
    Requirements: 2.2
    """
    if not mccids:
        return []
    
    # Remove wallet-specific MCCIDs
    filtered_mccids = [mccid for mccid in mccids if mccid not in WALLET_MCCIDS]
    
    # Deduplicate and sort
    unique_mccids = sorted(list(set(filtered_mccids)))
    
    return unique_mccids


def filter_wallet_text(narratives: List[str], wallet_indicators: List[str]) -> List[str]:
    """
    Remove wallet text from narratives.
    
    Filters out payment wallet prefixes and indicators to reveal
    the actual brand name in narratives.
    
    Args:
        narratives: List of narrative strings
        wallet_indicators: List of wallet types detected (e.g., ["PAYPAL", "SQ"])
        
    Returns:
        List of cleaned narratives with wallet text removed
    
    Requirements: 3.3
    """
    if not narratives:
        return []
    
    cleaned_narratives = []
    for narrative in narratives:
        cleaned = narrative
        
        # Remove wallet patterns
        for pattern in WALLET_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        cleaned_narratives.append(cleaned.strip())
    
    return cleaned_narratives


def apply_disambiguation(regex: str, tie_guidance: Dict[str, Any]) -> str:
    """
    Refine regex pattern for tie resolution.
    
    Applies disambiguation guidance from Tiebreaker Agent to make
    regex more specific and avoid matching multiple brands.
    
    Args:
        regex: Current regex pattern
        tie_guidance: Guidance dictionary with disambiguation instructions
        
    Returns:
        Refined regex pattern
    
    Requirements: 7.3
    """
    if not regex or not tie_guidance:
        return regex
    
    refined_regex = regex
    
    # Apply specific disambiguation strategies
    strategy = tie_guidance.get("strategy", "")
    
    if strategy == "add_word_boundary":
        # Add word boundaries to prevent partial matches
        if not refined_regex.endswith(r"\b"):
            refined_regex += r"\b"
    
    elif strategy == "add_negative_lookahead":
        # Add negative lookahead to exclude specific patterns
        exclude_patterns = tie_guidance.get("exclude_patterns", [])
        if exclude_patterns:
            lookahead = "(?!" + "|".join(exclude_patterns) + ")"
            # Insert after start anchor
            if refined_regex.startswith("^"):
                refined_regex = "^" + lookahead + refined_regex[1:]
    
    elif strategy == "make_more_specific":
        # Add required suffix or pattern
        required_suffix = tie_guidance.get("required_suffix", "")
        if required_suffix:
            refined_regex += required_suffix
    
    return refined_regex


def validate_pattern_coverage(regex: str, narratives: List[str]) -> Dict[str, Any]:
    """
    Test regex against sample narratives.
    
    Validates that the regex pattern matches expected narratives
    and calculates coverage and false positive rates.
    
    Args:
        regex: Regex pattern to test
        narratives: Sample narratives to test against
        
    Returns:
        Dictionary with coverage statistics including:
        - narratives_matched: Percentage of narratives matched
        - match_count: Number of narratives matched
        - total_count: Total number of narratives tested
        - valid: Boolean indicating if pattern is valid
    
    Requirements: 2.5
    """
    if not regex:
        return {
            "valid": False,
            "error": "Empty regex pattern",
            "narratives_matched": 0.0,
            "match_count": 0,
            "total_count": len(narratives)
        }
    
    if not narratives:
        return {
            "valid": True,
            "narratives_matched": 0.0,
            "match_count": 0,
            "total_count": 0
        }
    
    try:
        # Compile regex
        pattern = re.compile(regex, re.IGNORECASE)
        
        # Test against narratives
        match_count = 0
        for narrative in narratives:
            if pattern.search(narrative):
                match_count += 1
        
        total_count = len(narratives)
        match_percentage = match_count / total_count if total_count > 0 else 0.0
        
        return {
            "valid": True,
            "narratives_matched": round(match_percentage, 3),
            "match_count": match_count,
            "total_count": total_count
        }
    
    except re.error as e:
        return {
            "valid": False,
            "error": f"Invalid regex pattern: {str(e)}",
            "narratives_matched": 0.0,
            "match_count": 0,
            "total_count": len(narratives)
        }
