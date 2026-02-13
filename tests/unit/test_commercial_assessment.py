"""
Unit Tests for Commercial Assessment Agent

Tests specific examples and edge cases for the Commercial Assessment Agent tools.
"""

import pytest
from agents.commercial_assessment.tools import (
    verify_brand_exists,
    validate_sector,
    suggest_alternative_sectors,
    get_brand_info
)


class TestVerifyBrandExists:
    """Test brand existence verification functionality."""
    
    def test_empty_brand_name(self):
        """Test handling of empty brand name."""
        result = verify_brand_exists("")
        
        assert result["exists"] is False
        assert result["confidence"] == 0.0
        assert "error" in result
    
    def test_known_brand_starbucks(self):
        """Test verification of known brand (Starbucks)."""
        result = verify_brand_exists("Starbucks")
        
        assert result["exists"] is True
        assert result["confidence"] > 0.9
        assert result["official_name"] == "Starbucks Corporation"
        assert result["primary_sector"] == "Food & Beverage"
    
    def test_known_brand_case_insensitive(self):
        """Test that brand verification is case-insensitive."""
        results = [
            verify_brand_exists("STARBUCKS"),
            verify_brand_exists("starbucks"),
            verify_brand_exists("StArBuCkS")
        ]
        
        for result in results:
            assert result["exists"] is True
            assert result["official_name"] == "Starbucks Corporation"
    
    def test_known_brand_with_whitespace(self):
        """Test brand verification with leading/trailing whitespace."""
        result = verify_brand_exists("  Starbucks  ")
        
        assert result["exists"] is True
        assert result["official_name"] == "Starbucks Corporation"
    
    def test_unknown_brand(self):
        """Test verification of unknown brand - should return web_search_required."""
        result = verify_brand_exists("XYZ Unknown Store")
        
        # Unknown brands now return None (requires web search) instead of False
        assert result["exists"] is None
        assert result["source"] == "web_search_required"
        assert "web_search_instructions" in result
        assert result["confidence"] == 0.5  # Neutral confidence until web search performed
        assert result["official_name"] is None
    
    def test_multiple_known_brands(self):
        """Test verification of multiple known brands."""
        brands = ["McDonald's", "Shell", "Tesco", "Amazon", "Apple"]
        
        for brand in brands:
            result = verify_brand_exists(brand)
            assert result["exists"] is True
            assert result["confidence"] > 0.9
            assert result["official_name"] is not None


class TestValidateSector:
    """Test sector validation functionality."""
    
    def test_empty_inputs(self):
        """Test handling of empty brand name or sector."""
        result1 = validate_sector("", "Retail")
        result2 = validate_sector("Starbucks", "")
        result3 = validate_sector("", "")
        
        for result in [result1, result2, result3]:
            assert result["sector_valid"] is False
            assert result["confidence"] == 0.0
    
    def test_valid_primary_sector(self):
        """Test validation with correct primary sector."""
        result = validate_sector("Starbucks", "Food & Beverage")
        
        assert result["sector_valid"] is True
        assert result["confidence"] > 0.9
        assert result["expected_sector"] == "Food & Beverage"
    
    def test_valid_alternative_sector(self):
        """Test validation with valid alternative sector."""
        result = validate_sector("Starbucks", "Retail")
        
        assert result["sector_valid"] is True
        assert result["confidence"] > 0.7
        assert "alternative" in result["reasoning"].lower()
    
    def test_invalid_sector(self):
        """Test validation with incorrect sector."""
        result = validate_sector("Starbucks", "Technology")
        
        assert result["sector_valid"] is False
        assert result["confidence"] < 0.5
        assert result["expected_sector"] == "Food & Beverage"
    
    def test_unknown_brand_with_keywords(self):
        """Test sector validation for unknown brand with sector keywords."""
        result = validate_sector("Joe's Coffee Shop", "Food & Beverage")
        
        # Should validate based on keywords
        assert result["sector_valid"] is True
        assert result["confidence"] > 0.5
        assert "keyword" in result["reasoning"].lower()
    
    def test_unknown_brand_without_keywords(self):
        """Test sector validation for unknown brand without keywords."""
        result = validate_sector("ABC Company", "Technology")
        
        # Cannot validate - unknown brand, no keywords
        assert result["sector_valid"] is None
        assert result["confidence"] < 0.5
    
    def test_case_insensitive_validation(self):
        """Test that sector validation is case-insensitive."""
        result = validate_sector("STARBUCKS", "Food & Beverage")
        
        assert result["sector_valid"] is True


class TestSuggestAlternativeSectors:
    """Test alternative sector suggestion functionality."""
    
    def test_empty_brand_name(self):
        """Test handling of empty brand name."""
        result = suggest_alternative_sectors("", "Retail")
        
        assert result == []
    
    def test_known_brand_suggestions(self):
        """Test suggestions for known brand."""
        result = suggest_alternative_sectors("Starbucks", "Technology")
        
        # Should suggest Food & Beverage (primary) and Retail (alternative)
        assert len(result) > 0
        assert "Food & Beverage" in result
    
    def test_known_brand_with_correct_sector(self):
        """Test suggestions when current sector is correct."""
        result = suggest_alternative_sectors("Starbucks", "Food & Beverage")
        
        # Should suggest alternative sectors only
        assert "Food & Beverage" not in result or len(result) == 0
    
    def test_unknown_brand_with_keywords(self):
        """Test suggestions for unknown brand with sector keywords."""
        result = suggest_alternative_sectors("Joe's Gas Station", "Retail")
        
        # Should suggest Fuel based on "gas" and "station" keywords
        assert len(result) > 0
        # Fuel should be suggested
        assert "Fuel" in result
    
    def test_unknown_brand_without_keywords(self):
        """Test suggestions for unknown brand without keywords."""
        result = suggest_alternative_sectors("ABC Company", "Services")
        
        # May return empty or generic suggestions
        assert isinstance(result, list)
    
    def test_suggestions_ordered_by_relevance(self):
        """Test that suggestions are ordered by relevance."""
        result = suggest_alternative_sectors("Tech Software Store", "Services")
        
        # Should suggest Technology and Retail based on keywords
        assert len(result) > 0
        # Technology should be high priority due to "tech" and "software"
        if "Technology" in result:
            assert result.index("Technology") < len(result) - 1 or len(result) == 1
    
    def test_max_three_suggestions(self):
        """Test that at most 3 suggestions are returned."""
        result = suggest_alternative_sectors("Food Coffee Restaurant Shop", "Services")
        
        assert len(result) <= 3


class TestGetBrandInfo:
    """Test comprehensive brand information retrieval."""
    
    def test_empty_brand_name(self):
        """Test handling of empty brand name."""
        result = get_brand_info("")
        
        assert result["exists"] is False
        assert "error" in result
    
    def test_known_brand_complete_info(self):
        """Test retrieval of complete information for known brand."""
        result = get_brand_info("Starbucks")
        
        assert result["exists"] is True
        assert result["official_name"] == "Starbucks Corporation"
        assert result["primary_sector"] == "Food & Beverage"
        assert isinstance(result["alternative_sectors"], list)
        assert result["confidence"] > 0.9
        assert "source" in result
    
    def test_unknown_brand_info(self):
        """Test retrieval for unknown brand - should return web_search_required."""
        result = get_brand_info("XYZ Unknown Store")
        
        # Unknown brands now return exists=None with web_search_required
        assert result["exists"] is None or result["exists"] is False
        assert result["confidence"] <= 0.5
        assert "note" in result or "source" in result
    
    def test_multiple_brands_info(self):
        """Test retrieval for multiple brands."""
        brands = ["McDonald's", "Shell", "Amazon"]
        
        for brand in brands:
            result = get_brand_info(brand)
            assert result["exists"] is True
            assert result["official_name"] is not None
            assert result["primary_sector"] is not None
    
    def test_brand_info_includes_all_fields(self):
        """Test that brand info includes all expected fields."""
        result = get_brand_info("Apple")
        
        assert "exists" in result
        assert "brandname" in result
        assert "official_name" in result
        assert "primary_sector" in result
        assert "alternative_sectors" in result
        assert "confidence" in result
        assert "source" in result
    
    def test_case_insensitive_info_retrieval(self):
        """Test that info retrieval is case-insensitive."""
        result1 = get_brand_info("APPLE")
        result2 = get_brand_info("apple")
        result3 = get_brand_info("Apple")
        
        for result in [result1, result2, result3]:
            assert result["exists"] is True
            assert result["official_name"] == "Apple Inc."


class TestIntegration:
    """Test integration between different tools."""
    
    def test_validation_workflow(self):
        """Test complete validation workflow for a brand."""
        brandname = "Starbucks"
        sector = "Technology"  # Incorrect sector
        
        # Step 1: Verify brand exists
        exists_result = verify_brand_exists(brandname)
        assert exists_result["exists"] is True
        
        # Step 2: Validate sector
        sector_result = validate_sector(brandname, sector)
        assert sector_result["sector_valid"] is False
        
        # Step 3: Get alternative suggestions
        alternatives = suggest_alternative_sectors(brandname, sector)
        assert len(alternatives) > 0
        assert "Food & Beverage" in alternatives
        
        # Step 4: Get complete brand info
        info = get_brand_info(brandname)
        assert info["primary_sector"] == "Food & Beverage"
    
    def test_unknown_brand_workflow(self):
        """Test workflow for unknown brand - should return web_search_required."""
        brandname = "Unknown Brand XYZ"
        sector = "Retail"
        
        # Verify brand - should return web_search_required
        exists_result = verify_brand_exists(brandname)
        assert exists_result["exists"] is None  # Unknown until web search performed
        assert exists_result["source"] == "web_search_required"
        
        # Get brand info
        info = get_brand_info(brandname)
        assert info["exists"] is False
        
        # Sector validation should be uncertain
        sector_result = validate_sector(brandname, sector)
        assert sector_result["sector_valid"] is None or sector_result["confidence"] < 0.5
