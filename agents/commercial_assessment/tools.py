"""
Commercial Assessment Agent Tools

This module provides tools for the Commercial Assessment Agent to validate
brand names and sectors against real-world commercial identity.

The Commercial Assessment Agent:
- Verifies brand names correspond to real commercial entities
- Validates sector classification appropriateness
- Suggests alternative sectors when misclassification detected
- Provides validation results to Evaluator Agent
- Integrates with MCP servers (Crunchbase, Brand Registry) for external validation
- Implements caching to reduce API calls and improve performance
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# MCP integration flag (set to True when MCP is available)
MCP_AVAILABLE = False
try:
    # Try to import MCP client (if available)
    # This will be set up when MCP servers are configured
    MCP_AVAILABLE = os.path.exists(".kiro/settings/mcp.json")
except Exception:
    pass


# Cache for MCP responses (in-memory cache for demonstration)
# In production, this would use DynamoDB as specified in Requirement 15.10
_mcp_cache = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache TTL


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


def _get_cache_key(operation: str, **kwargs) -> str:
    """Generate cache key for MCP responses."""
    key_parts = [operation] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return ":".join(key_parts)


def _get_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached MCP response if not expired."""
    if cache_key in _mcp_cache:
        cached_data, timestamp = _mcp_cache[cache_key]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_TTL_SECONDS):
            logger.info(f"Cache hit for {cache_key}")
            return cached_data
        else:
            # Expired - remove from cache
            del _mcp_cache[cache_key]
    return None


def _save_to_cache(cache_key: str, data: Dict[str, Any]) -> None:
    """Save MCP response to cache."""
    _mcp_cache[cache_key] = (data, datetime.now())
    logger.info(f"Cached response for {cache_key}")


def _query_brand_registry_mcp(brandname: str) -> Optional[Dict[str, Any]]:
    """
    Query Brand Registry MCP server for brand information.
    
    Args:
        brandname: Brand name to search
        
    Returns:
        Brand information from MCP or None if unavailable
    
    Requirements: 15.1, 15.3
    """
    if not MCP_AVAILABLE:
        return None
    
    # Check cache first
    cache_key = _get_cache_key("brand_registry_search", brandname=brandname)
    cached_result = _get_from_cache(cache_key)
    if cached_result:
        return cached_result
    
    try:
        # In production, this would use the actual MCP client
        # For now, we'll simulate the MCP call
        logger.info(f"Querying Brand Registry MCP for: {brandname}")
        
        # Placeholder for actual MCP call
        # result = mcp_client.call_tool("brand-registry", "search_brands", {
        #     "query": brandname,
        #     "limit": 1
        # })
        
        # For now, return None to indicate MCP not yet fully integrated
        # This will be completed when MCP client is available
        result = None
        
        if result:
            _save_to_cache(cache_key, result)
        
        return result
    
    except Exception as e:
        logger.error(f"Error querying Brand Registry MCP: {str(e)}")
        return None


def _query_crunchbase_mcp(brandname: str) -> Optional[Dict[str, Any]]:
    """
    Query Crunchbase MCP server for company information.
    
    Args:
        brandname: Brand/company name to search
        
    Returns:
        Company information from Crunchbase or None if unavailable
    
    Requirements: 15.2, 15.3
    """
    if not MCP_AVAILABLE:
        return None
    
    # Check cache first
    cache_key = _get_cache_key("crunchbase_search", brandname=brandname)
    cached_result = _get_from_cache(cache_key)
    if cached_result:
        return cached_result
    
    try:
        # In production, this would use the actual MCP client
        logger.info(f"Querying Crunchbase MCP for: {brandname}")
        
        # Placeholder for actual MCP call
        # result = mcp_client.call_tool("crunchbase", "search_organizations", {
        #     "query": brandname
        # })
        
        # For now, return None to indicate MCP not yet fully integrated
        result = None
        
        if result:
            _save_to_cache(cache_key, result)
        
        return result
    
    except Exception as e:
        logger.error(f"Error querying Crunchbase MCP: {str(e)}")
        return None


def _query_wikipedia_mcp(brandname: str) -> Optional[Dict[str, Any]]:
    """
    Query Wikipedia MCP server for brand/company information.
    
    Args:
        brandname: Brand/company name to search
        
    Returns:
        Brand information from Wikipedia or None if unavailable
    
    Requirements: 15.3, 15.4
    """
    if not MCP_AVAILABLE:
        return None
    
    # Check cache first
    cache_key = _get_cache_key("wikipedia_search", brandname=brandname)
    cached_result = _get_from_cache(cache_key)
    if cached_result:
        return cached_result
    
    try:
        logger.info(f"Querying Wikipedia MCP for: {brandname}")
        
        # Placeholder for actual MCP call
        # result = mcp_client.call_tool("wikipedia", "search", {
        #     "query": brandname
        # })
        
        # For now, return None to indicate MCP not yet fully integrated
        result = None
        
        if result:
            _save_to_cache(cache_key, result)
        
        return result
    
    except Exception as e:
        logger.error(f"Error querying Wikipedia MCP: {str(e)}")
        return None


def _query_brave_search_mcp(brandname: str) -> Optional[Dict[str, Any]]:
    """
    Query Brave Search MCP server for brand/company information.
    
    Args:
        brandname: Brand/company name to search
        
    Returns:
        Brand information from Brave Search or None if unavailable
    
    Requirements: 15.3, 15.4
    """
    if not MCP_AVAILABLE:
        return None
    
    # Check cache first
    cache_key = _get_cache_key("brave_search", brandname=brandname)
    cached_result = _get_from_cache(cache_key)
    if cached_result:
        return cached_result
    
    try:
        logger.info(f"Querying Brave Search MCP for: {brandname}")
        
        # Placeholder for actual MCP call
        # result = mcp_client.call_tool("brave-search", "brave_web_search", {
        #     "query": f"{brandname} company"
        # })
        
        # For now, return None to indicate MCP not yet fully integrated
        result = None
        
        if result:
            _save_to_cache(cache_key, result)
        
        return result
    
    except Exception as e:
        logger.error(f"Error querying Brave Search MCP: {str(e)}")
        return None


def web_search_brand(brandname: str) -> Dict[str, Any]:
    """
    Search the web for brand information using AWS Bedrock AgentCore Browser.
    
    This function is designed to be called by the Strands Agent, which has access
    to the AgentCore Browser tool. The agent will use the browser to:
    1. Search for the brand's official website
    2. Search for Wikipedia page
    3. Analyze search results to determine legitimacy
    
    This is a placeholder function that returns instructions for the agent.
    The actual web search is performed by the agent using its browser tool.
    
    Args:
        brandname: Brand name to search
        
    Returns:
        Dictionary with search instructions for the agent
    
    Requirements: 15.6
    """
    logger.info(f"Web search requested for brand: {brandname}")
    
    return {
        "action": "web_search_required",
        "brandname": brandname,
        "instructions": {
            "searches_to_perform": [
                f"{brandname} official website",
                f"{brandname} Wikipedia",
                f"{brandname} company information"
            ],
            "analysis_criteria": {
                "high_confidence": "Official website + Wikipedia page found",
                "medium_high_confidence": "Official website found only",
                "medium_confidence": "Multiple credible online mentions",
                "low_confidence": "Limited online presence",
                "very_low_confidence": "No credible online presence"
            },
            "confidence_scores": {
                "website_and_wikipedia": 0.85,
                "website_only": 0.75,
                "multiple_mentions": 0.60,
                "limited_presence": 0.40,
                "no_presence": 0.20
            }
        },
        "note": "Agent should use browser tool to perform these searches and analyze results"
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
    entity. It uses a multi-tier approach:
    1. Query Brand Registry MCP server (internal database)
    2. Query Wikipedia MCP server (free external validation)
    3. Query Brave Search MCP server (free tier)
    4. Query Crunchbase MCP server (external validation - disabled by default)
    5. Fall back to web search if MCP unavailable
    6. Use internal known brands database as last resort
    
    Args:
        brandname: Brand name to validate
        
    Returns:
        Dictionary with validation results including:
        - exists: Boolean indicating if brand is recognized
        - confidence: Float between 0.0 and 1.0
        - official_name: Official company name (if found)
        - source: Data source used for validation
    
    Requirements: 5.3, 15.3, 15.4, 15.5, 15.6
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
    
    # Tier 1: Try Brand Registry MCP (internal database)
    logger.info(f"Validating brand: {brandname}")
    
    try:
        brand_registry_result = _query_brand_registry_mcp(brandname)
        
        if brand_registry_result and brand_registry_result.get("success"):
            brands = brand_registry_result.get("brands", [])
            if brands:
                brand = brands[0]
                logger.info(f"Brand found in Brand Registry MCP: {brand}")
                return {
                    "exists": True,
                    "confidence": 0.95,
                    "official_name": brand.get("brandname"),
                    "primary_sector": brand.get("sector"),
                    "source": "brand_registry_mcp"
                }
    except Exception as e:
        logger.error(f"Error querying Brand Registry MCP: {str(e)}")
        # Continue to next tier
    
    # Tier 2: Try Wikipedia MCP (free external validation)
    try:
        wikipedia_result = _query_wikipedia_mcp(brandname)
        
        if wikipedia_result and wikipedia_result.get("success"):
            pages = wikipedia_result.get("pages", [])
            if pages:
                page = pages[0]
                logger.info(f"Brand found in Wikipedia MCP: {page}")
                return {
                    "exists": True,
                    "confidence": 0.88,
                    "official_name": page.get("title"),
                    "primary_sector": page.get("category"),
                    "source": "wikipedia_mcp"
                }
    except Exception as e:
        logger.error(f"Error querying Wikipedia MCP: {str(e)}")
        # Continue to next tier
    
    # Tier 3: Try Brave Search MCP (free tier)
    try:
        brave_result = _query_brave_search_mcp(brandname)
        
        if brave_result and brave_result.get("success"):
            results = brave_result.get("web", {}).get("results", [])
            if results:
                result = results[0]
                logger.info(f"Brand found in Brave Search MCP: {result}")
                return {
                    "exists": True,
                    "confidence": 0.82,
                    "official_name": result.get("title"),
                    "source": "brave_search_mcp"
                }
    except Exception as e:
        logger.error(f"Error querying Brave Search MCP: {str(e)}")
        # Continue to next tier
    
    # Tier 4: Try Crunchbase MCP (external validation - disabled by default)
    try:
        crunchbase_result = _query_crunchbase_mcp(brandname)
        
        if crunchbase_result and crunchbase_result.get("success"):
            organizations = crunchbase_result.get("organizations", [])
            if organizations:
                org = organizations[0]
                logger.info(f"Brand found in Crunchbase MCP: {org}")
                return {
                    "exists": True,
                    "confidence": 0.90,
                    "official_name": org.get("name"),
                    "primary_sector": org.get("primary_role"),
                    "source": "crunchbase_mcp"
                }
    except Exception as e:
        logger.error(f"Error querying Crunchbase MCP: {str(e)}")
        # Continue to next tier
    
    # Tier 6: Check against known brands database (internal fallback)
    if normalized_name in KNOWN_BRANDS:
        brand_info = KNOWN_BRANDS[normalized_name]
        logger.info(f"Brand found in internal database: {brand_info}")
        return {
            "exists": True,
            "confidence": brand_info["confidence"],
            "official_name": brand_info["official_name"],
            "primary_sector": brand_info["primary_sector"],
            "alternative_sectors": brand_info["alternative_sectors"],
            "source": "internal"
        }
    
    # Tier 7: Request agent to perform web search
    # The agent has access to AWS Bedrock AgentCore Browser tool
    # which can search the web and analyze results
    try:
        web_search_instructions = web_search_brand(brandname)
        logger.info(f"Requesting agent web search for: {brandname}")
        
        # Return instructions for the agent to perform web search
        # The agent will use its browser tool to search and analyze
        return {
            "exists": None,  # Unknown - requires web search
            "confidence": 0.5,
            "official_name": None,
            "source": "web_search_required",
            "web_search_instructions": web_search_instructions,
            "note": "Agent should use browser tool to search for this brand and determine legitimacy"
        }
    except Exception as e:
        logger.error(f"Error preparing web search instructions: {str(e)}")
        # Continue to final fallback
    
    # Final fallback: Brand not found in any source
    logger.warning(f"Brand not found: {brandname}")
    return {
        "exists": False,
        "confidence": 0.3,  # Low confidence when not found
        "official_name": None,
        "source": "none",
        "note": "Brand not found in any data source"
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
