"""
Commercial Assessment Agent Tools

This module provides tools for the Commercial Assessment Agent to validate
brand names and sectors against real-world commercial identity.

The Commercial Assessment Agent:
- Verifies brand names correspond to real commercial entities
- Validates sector classification appropriateness
- Suggests alternative sectors when misclassification detected
- Provides validation results to Evaluator Agent

Note: This implementation provides basic validation logic. Full MCP integration
for external brand databases (Crunchbase, custom brand registry) will be added
in Task 17.
"""

from typing import Dict, List, Any


# Known sector mappings for common retail categories
SECTOR_KEYWORDS = {
    "Food & Beverage": ["restaurant", "cafe", "coffee", "food", "beverage", "dining", "pizza", "burger"],
    "Retail": ["store", "shop", "retail", "mart", "market", "boutique", "outlet"],
    "Fuel": ["gas", "fuel", "petrol", "station", "shell", "bp", "exxon"],
    "Services": ["service", "repair", "cleaning", "consulting", "professional"],
    "Entertainment": ["cinema", "theater", "entertainment", "gaming", "arcade"],
    "Travel": ["hotel", "airline", "travel", "booking", "accommodation"],
    "Technology": ["tech", "software", "computer", "electronics", "digital"],
    "Healthcare": ["health", "medical", "pharmacy", "clinic", "hospital"],
    "Financial": ["bank", "finance", "insurance", "investment", "credit"]
}


# Known major brands for validation (subset for demonstration)
# In production, this would be replaced by MCP queries to external databases
KNOWN_BRANDS = {
    "starbucks": {
        "official_name": "Starbucks Corporation",
        "primary_sector": "Food & Beverage",
        "alternative_sectors": ["Retail"],
        "confidence": 0.98
    },
    "mcdonalds": {
        "official_name": "McDonald's Corporation",
        "primary_sector": "Food & Beverage",
        "alternative_sectors": [],
        "confidence": 0.98
    },
    "mcdonald's": {  # Handle apostrophe variant
        "official_name": "McDonald's Corporation",
        "primary_sector": "Food & Beverage",
        "alternative_sectors": [],
        "confidence": 0.98
    },
    "shell": {
        "official_name": "Shell plc",
        "primary_sector": "Fuel",
        "alternative_sectors": ["Retail"],
        "confidence": 0.95
    },
    "tesco": {
        "official_name": "Tesco PLC",
        "primary_sector": "Retail",
        "alternative_sectors": ["Food & Beverage"],
        "confidence": 0.97
    },
    "amazon": {
        "official_name": "Amazon.com, Inc.",
        "primary_sector": "Retail",
        "alternative_sectors": ["Technology"],
        "confidence": 0.99
    },
    "apple": {
        "official_name": "Apple Inc.",
        "primary_sector": "Technology",
        "alternative_sectors": ["Retail"],
        "confidence": 0.99
    },
    "walmart": {
        "official_name": "Walmart Inc.",
        "primary_sector": "Retail",
        "alternative_sectors": [],
        "confidence": 0.98
    },
    "bp": {
        "official_name": "BP plc",
        "primary_sector": "Fuel",
        "alternative_sectors": [],
        "confidence": 0.96
    }
}


def verify_brand_exists(brandname: str) -> Dict[str, Any]:
    """
    Check if brand corresponds to a real commercial entity.
    
    This function validates whether a brand name matches a known commercial
    entity. In the current implementation, it checks against a known brands
    database. In Task 17, this will be enhanced with MCP integration to query
    external databases like Crunchbase.
    
    Args:
        brandname: Brand name to validate
        
    Returns:
        Dictionary with validation results including:
        - exists: Boolean indicating if brand is recognized
        - confidence: Float between 0.0 and 1.0
        - official_name: Official company name (if found)
        - source: Data source used for validation
    
    Requirements: 5.3
    """
    if not brandname:
        return {
            "exists": False,
            "confidence": 0.0,
            "official_name": None,
            "source": "internal",
            "error": "Empty brand name provided"
        }
    
    # Normalize brand name for lookup
    normalized_name = brandname.lower().strip()
    
    # Check against known brands database
    if normalized_name in KNOWN_BRANDS:
        brand_info = KNOWN_BRANDS[normalized_name]
        return {
            "exists": True,
            "confidence": brand_info["confidence"],
            "official_name": brand_info["official_name"],
            "primary_sector": brand_info["primary_sector"],
            "alternative_sectors": brand_info["alternative_sectors"],
            "source": "internal"
        }
    
    # Brand not found in known database
    # In production with MCP, this would trigger external API queries
    return {
        "exists": False,
        "confidence": 0.3,  # Low confidence when not found
        "official_name": None,
        "source": "internal",
        "note": "Brand not found in known database. MCP integration (Task 17) will enable external validation."
    }


def validate_sector(brandname: str, sector: str) -> Dict[str, Any]:
    """
    Verify sector classification appropriateness for a brand.
    
    Validates whether the assigned sector is appropriate for the given brand
    by checking against known brand information and sector keywords.
    
    Args:
        brandname: Brand name
        sector: Assigned sector classification
        
    Returns:
        Dictionary with validation results including:
        - sector_valid: Boolean indicating if sector is appropriate
        - confidence: Float between 0.0 and 1.0
        - expected_sector: Recommended sector (if different)
        - reasoning: Explanation of validation result
    
    Requirements: 5.4
    """
    if not brandname or not sector:
        return {
            "sector_valid": False,
            "confidence": 0.0,
            "expected_sector": None,
            "reasoning": "Missing brand name or sector"
        }
    
    # Normalize inputs
    normalized_name = brandname.lower().strip()
    
    # Check if brand is known
    if normalized_name in KNOWN_BRANDS:
        brand_info = KNOWN_BRANDS[normalized_name]
        primary_sector = brand_info["primary_sector"]
        alternative_sectors = brand_info["alternative_sectors"]
        
        # Check if provided sector matches primary or alternative sectors
        if sector == primary_sector:
            return {
                "sector_valid": True,
                "confidence": 0.95,
                "expected_sector": primary_sector,
                "reasoning": f"Sector matches primary sector for {brand_info['official_name']}"
            }
        elif sector in alternative_sectors:
            return {
                "sector_valid": True,
                "confidence": 0.80,
                "expected_sector": sector,
                "reasoning": f"Sector is valid alternative for {brand_info['official_name']}"
            }
        else:
            return {
                "sector_valid": False,
                "confidence": 0.40,
                "expected_sector": primary_sector,
                "reasoning": f"Sector mismatch. Expected '{primary_sector}' but got '{sector}'"
            }
    
    # Brand not in known database - use keyword-based validation
    # Check if brand name contains sector-related keywords
    brand_lower = brandname.lower()
    sector_keywords = SECTOR_KEYWORDS.get(sector, [])
    
    keyword_matches = sum(1 for keyword in sector_keywords if keyword in brand_lower)
    
    if keyword_matches > 0:
        return {
            "sector_valid": True,
            "confidence": 0.60,  # Lower confidence for keyword-based validation
            "expected_sector": sector,
            "reasoning": f"Brand name contains sector-related keywords ({keyword_matches} matches)"
        }
    
    # No validation possible
    return {
        "sector_valid": None,  # Unknown
        "confidence": 0.30,
        "expected_sector": None,
        "reasoning": "Brand not in known database. Cannot validate sector. MCP integration (Task 17) will improve validation."
    }


def suggest_alternative_sectors(brandname: str, current_sector: str) -> List[str]:
    """
    Recommend alternative sector classifications for a brand.
    
    Suggests other sectors that might be appropriate for the brand based on
    known information and keyword analysis.
    
    Args:
        brandname: Brand name
        current_sector: Currently assigned sector
        
    Returns:
        List of alternative sector names, ordered by relevance
    
    Requirements: 5.4
    """
    if not brandname:
        return []
    
    # Normalize brand name
    normalized_name = brandname.lower().strip()
    
    # Check if brand is known
    if normalized_name in KNOWN_BRANDS:
        brand_info = KNOWN_BRANDS[normalized_name]
        alternatives = brand_info["alternative_sectors"].copy()
        
        # Add primary sector if current sector is different
        if current_sector != brand_info["primary_sector"]:
            alternatives.insert(0, brand_info["primary_sector"])
        
        return alternatives
    
    # Brand not known - suggest based on keywords in brand name
    brand_lower = brandname.lower()
    suggestions = []
    
    for sector, keywords in SECTOR_KEYWORDS.items():
        if sector == current_sector:
            continue  # Skip current sector
        
        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword in brand_lower)
        if matches > 0:
            suggestions.append((sector, matches))
    
    # Sort by number of matches (descending)
    suggestions.sort(key=lambda x: x[1], reverse=True)
    
    # Return sector names only
    return [sector for sector, _ in suggestions[:3]]  # Top 3 suggestions


def get_brand_info(brandname: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive commercial information about a brand.
    
    Aggregates all available information about a brand including official name,
    sector, validation confidence, and data sources.
    
    Args:
        brandname: Brand name to look up
        
    Returns:
        Dictionary with complete brand information including:
        - exists: Boolean
        - official_name: Official company name
        - primary_sector: Main business sector
        - alternative_sectors: Other applicable sectors
        - confidence: Validation confidence score
        - source: Data source
    
    Requirements: 5.3, 5.4
    """
    if not brandname:
        return {
            "exists": False,
            "error": "Empty brand name provided"
        }
    
    # Get existence validation
    existence_result = verify_brand_exists(brandname)
    
    if not existence_result.get("exists"):
        return {
            "exists": False,
            "brandname": brandname,
            "confidence": existence_result.get("confidence", 0.0),
            "source": existence_result.get("source", "internal"),
            "note": existence_result.get("note", "Brand not found")
        }
    
    # Brand exists - return full information
    return {
        "exists": True,
        "brandname": brandname,
        "official_name": existence_result.get("official_name"),
        "primary_sector": existence_result.get("primary_sector"),
        "alternative_sectors": existence_result.get("alternative_sectors", []),
        "confidence": existence_result.get("confidence"),
        "source": existence_result.get("source")
    }
