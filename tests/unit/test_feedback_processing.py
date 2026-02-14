"""
Unit Tests for Feedback Processing Agent

Tests the feedback parsing, categorization, and refinement prompt generation
functionality of the Feedback Processing Agent.

Requirements: 14.2, 14.3, 14.4
"""

import pytest
from agents.feedback_processing import tools as fp_tools


class TestParseFeedback:
    """Test feedback parsing functionality."""
    
    def test_parse_feedback_basic(self):
        """Test basic feedback parsing."""
        feedback_text = "Too many false positives for Starbucks. Regex is matching Starburst candy."
        brandid = 123
        
        result = fp_tools.parse_feedback(feedback_text, brandid)
        
        assert result["brandid"] == 123
        assert result["feedback_text"] == feedback_text
        assert "feedback_id" in result
        assert "timestamp" in result
        assert len(result["issues_identified"]) > 0
        assert result["category"] in ["regex_too_broad", "general"]
    
    def test_parse_feedback_empty(self):
        """Test parsing empty feedback."""
        result = fp_tools.parse_feedback("", 123)
        
        assert result["brandid"] == 123
        assert result["feedback_text"] == ""
        assert "error" in result
        assert result["issues_identified"] == []
    
    def test_parse_feedback_with_combo_ids(self):
        """Test parsing feedback with combo IDs."""
        feedback_text = "Combo 12345 and combo 67890 are misclassified."
        
        result = fp_tools.parse_feedback(feedback_text, 123)
        
        assert 12345 in result["misclassified_combos"]
        assert 67890 in result["misclassified_combos"]
    
    def test_parse_feedback_wallet_issue(self):
        """Test parsing feedback about wallet handling."""
        feedback_text = "PayPal transactions are not being filtered correctly. SQ * prefix should be excluded."
        
        result = fp_tools.parse_feedback(feedback_text, 123)
        
        assert result["category"] == "wallet_handling"
        assert any("wallet" in issue.lower() for issue in result["issues_identified"])


class TestIdentifyMisclassifiedCombos:
    """Test combo ID extraction from feedback."""
    
    def test_identify_combos_with_combo_keyword(self):
        """Test extracting combo IDs with 'combo' keyword."""
        feedback = {"feedback_text": "Combo 12345 is wrong and combo 67890 too."}
        
        result = fp_tools.identify_misclassified_combos(feedback)
        
        assert 12345 in result
        assert 67890 in result
    
    def test_identify_combos_with_ccid_keyword(self):
        """Test extracting combo IDs with 'ccid' keyword."""
        feedback = {"feedback_text": "ccid 54321 should not match this brand."}
        
        result = fp_tools.identify_misclassified_combos(feedback)
        
        assert 54321 in result
    
    def test_identify_combos_with_id_keyword(self):
        """Test extracting combo IDs with 'ID' keyword."""
        feedback = {"feedback_text": "ID 11111 and ID 22222 are false positives."}
        
        result = fp_tools.identify_misclassified_combos(feedback)
        
        assert 11111 in result
        assert 22222 in result
    
    def test_identify_combos_standalone_numbers(self):
        """Test extracting standalone 4-6 digit numbers."""
        feedback = {"feedback_text": "The combos 9999 and 8888 don't belong here."}
        
        result = fp_tools.identify_misclassified_combos(feedback)
        
        assert 9999 in result
        assert 8888 in result
    
    def test_identify_combos_no_ids(self):
        """Test feedback with no combo IDs."""
        feedback = {"feedback_text": "The regex is too broad in general."}
        
        result = fp_tools.identify_misclassified_combos(feedback)
        
        assert result == []
    
    def test_identify_combos_deduplication(self):
        """Test that duplicate combo IDs are deduplicated."""
        feedback = {"feedback_text": "Combo 12345 and combo 12345 again."}
        
        result = fp_tools.identify_misclassified_combos(feedback)
        
        assert result == [12345]
    
    def test_identify_combos_empty_feedback(self):
        """Test with empty feedback."""
        feedback = {"feedback_text": ""}
        
        result = fp_tools.identify_misclassified_combos(feedback)
        
        assert result == []


class TestAnalyzeFeedbackCategory:
    """Test feedback categorization."""
    
    def test_category_regex_too_broad(self):
        """Test categorizing regex too broad feedback."""
        feedback = {"feedback_text": "Too many false positives. Regex is too broad and matches unrelated brands."}
        
        result = fp_tools.analyze_feedback_category(feedback)
        
        assert result == "regex_too_broad"
    
    def test_category_regex_too_narrow(self):
        """Test categorizing regex too narrow feedback."""
        feedback = {"feedback_text": "Missing many legitimate transactions. Regex is too narrow and doesn't match variations."}
        
        result = fp_tools.analyze_feedback_category(feedback)
        
        assert result == "regex_too_narrow"
    
    def test_category_mccid_incorrect(self):
        """Test categorizing MCCID issue feedback."""
        feedback = {"feedback_text": "Wrong MCCID in the list. MCCID 7399 should not be included."}
        
        result = fp_tools.analyze_feedback_category(feedback)
        
        assert result == "mccid_incorrect"
    
    def test_category_wallet_handling(self):
        """Test categorizing wallet handling feedback."""
        feedback = {"feedback_text": "PayPal and Square transactions are causing issues. Wallet text not filtered."}
        
        result = fp_tools.analyze_feedback_category(feedback)
        
        assert result == "wallet_handling"
    
    def test_category_ambiguous_name(self):
        """Test categorizing ambiguous name feedback."""
        feedback = {"feedback_text": "Brand name is too generic and ambiguous. Matches multiple unrelated entities."}
        
        result = fp_tools.analyze_feedback_category(feedback)
        
        assert result == "ambiguous_name"
    
    def test_category_general(self):
        """Test categorizing general feedback."""
        feedback = {"feedback_text": "Please review this brand's classification."}
        
        result = fp_tools.analyze_feedback_category(feedback)
        
        assert result == "general"
    
    def test_category_empty_feedback(self):
        """Test with empty feedback."""
        feedback = {"feedback_text": ""}
        
        result = fp_tools.analyze_feedback_category(feedback)
        
        assert result == "unknown"
    
    def test_category_multiple_keywords(self):
        """Test with feedback containing multiple category keywords."""
        feedback = {"feedback_text": "Too broad regex and wrong MCCID. False positives everywhere."}
        
        result = fp_tools.analyze_feedback_category(feedback)
        
        # Should return the category with most keyword matches
        assert result in ["regex_too_broad", "mccid_incorrect"]


class TestGenerateRefinementPrompt:
    """Test refinement prompt generation."""
    
    def test_generate_prompt_regex_too_broad(self):
        """Test generating prompt for regex too broad feedback."""
        feedback = {
            "category": "regex_too_broad",
            "feedback_text": "Too many false positives. Matching Starburst candy.",
            "issues_identified": ["False positives detected"],
            "misclassified_combos": [12345]
        }
        current_metadata = {
            "regex": "^STARBUCKS.*",
            "mccids": [5812, 5814]
        }
        brand_data = {
            "brandname": "Starbucks"
        }
        
        result = fp_tools.generate_refinement_prompt(feedback, current_metadata, brand_data)
        
        assert "Starbucks" in result
        assert "^STARBUCKS.*" in result
        assert "false positives" in result.lower()
        assert "more specific" in result.lower()
        assert "12345" in result
    
    def test_generate_prompt_regex_too_narrow(self):
        """Test generating prompt for regex too narrow feedback."""
        feedback = {
            "category": "regex_too_narrow",
            "feedback_text": "Missing legitimate transactions.",
            "issues_identified": ["Missing patterns or narratives"],
            "misclassified_combos": []
        }
        current_metadata = {
            "regex": "^STARBUCKS\\s+#\\d+$",
            "mccids": [5812]
        }
        brand_data = {
            "brandname": "Starbucks"
        }
        
        result = fp_tools.generate_refinement_prompt(feedback, current_metadata, brand_data)
        
        assert "broaden" in result.lower() or "variations" in result.lower()
        assert "missing" in result.lower()
    
    def test_generate_prompt_mccid_incorrect(self):
        """Test generating prompt for MCCID issue feedback."""
        feedback = {
            "category": "mccid_incorrect",
            "feedback_text": "MCCID 7399 is wrong.",
            "issues_identified": ["MCCID classification issue"],
            "misclassified_combos": []
        }
        current_metadata = {
            "regex": "^STARBUCKS",
            "mccids": [5812, 7399]
        }
        brand_data = {
            "brandname": "Starbucks"
        }
        
        result = fp_tools.generate_refinement_prompt(feedback, current_metadata, brand_data)
        
        assert "mccid" in result.lower()
        assert "7399" in result
    
    def test_generate_prompt_wallet_handling(self):
        """Test generating prompt for wallet handling feedback."""
        feedback = {
            "category": "wallet_handling",
            "feedback_text": "PayPal prefix not excluded.",
            "issues_identified": ["Payment wallet handling issue"],
            "misclassified_combos": []
        }
        current_metadata = {
            "regex": "^PAYPAL.*STARBUCKS",
            "mccids": [5812, 7399]
        }
        brand_data = {
            "brandname": "Starbucks"
        }
        
        result = fp_tools.generate_refinement_prompt(feedback, current_metadata, brand_data)
        
        assert "wallet" in result.lower()
        assert "paypal" in result.lower() or "exclude" in result.lower()
    
    def test_generate_prompt_with_combo_ids(self):
        """Test prompt includes combo analysis guidance when IDs provided."""
        feedback = {
            "category": "regex_too_broad",
            "feedback_text": "False positives.",
            "issues_identified": ["False positives detected"],
            "misclassified_combos": [11111, 22222, 33333]
        }
        current_metadata = {
            "regex": "^BRAND",
            "mccids": [5812]
        }
        brand_data = {
            "brandname": "Brand"
        }
        
        result = fp_tools.generate_refinement_prompt(feedback, current_metadata, brand_data)
        
        assert "11111" in result
        assert "22222" in result
        assert "33333" in result
        assert "analyze" in result.lower() or "review" in result.lower()
    
    def test_generate_prompt_empty_feedback(self):
        """Test with empty feedback."""
        result = fp_tools.generate_refinement_prompt({}, {}, {})
        
        assert "No feedback" in result
    
    def test_generate_prompt_structure(self):
        """Test that prompt has proper structure."""
        feedback = {
            "category": "general",
            "feedback_text": "Please improve.",
            "issues_identified": ["General feedback"],
            "misclassified_combos": []
        }
        current_metadata = {
            "regex": "^TEST",
            "mccids": [1234]
        }
        brand_data = {
            "brandname": "TestBrand"
        }
        
        result = fp_tools.generate_refinement_prompt(feedback, current_metadata, brand_data)
        
        # Check for key sections
        assert "Current Metadata" in result
        assert "Human Feedback" in result
        assert "GUIDANCE" in result
        assert "REQUIREMENTS" in result


class TestStoreFeedback:
    """Test feedback storage functionality."""
    
    def test_store_feedback_success(self):
        """Test successful feedback storage."""
        feedback = {
            "feedback_id": "test-123",
            "timestamp": "2024-02-15T10:00:00Z",
            "category": "regex_too_broad",
            "feedback_text": "Too broad",
            "issues_identified": ["False positives"],
            "misclassified_combos": [12345]
        }
        
        result = fp_tools.store_feedback(123, feedback, 2)
        
        assert result["feedback_stored"] is True
        assert "storage_location" in result
        assert "brand_123" in result["storage_location"]
        assert "v2" in result["storage_location"]
        assert result["feedback_id"] == "test-123"
    
    def test_store_feedback_empty(self):
        """Test storing empty feedback."""
        result = fp_tools.store_feedback(123, {}, 1)
        
        assert result["feedback_stored"] is False
        assert "error" in result
    
    def test_store_feedback_s3_key_format(self):
        """Test S3 key format is correct."""
        feedback = {
            "feedback_id": "abc-def-123",
            "timestamp": "2024-02-15T10:00:00Z",
            "category": "general",
            "feedback_text": "Test",
            "issues_identified": [],
            "misclassified_combos": []
        }
        
        result = fp_tools.store_feedback(456, feedback, 3)
        
        assert "brand_456_v3_abc-def-123.json" in result["storage_location"]
        assert "s3://brand-generator-rwrd-023-eu-west-1/feedback/" in result["storage_location"]


class TestRetrieveFeedbackHistory:
    """Test feedback history retrieval."""
    
    def test_retrieve_feedback_history_empty(self):
        """Test retrieving feedback history for brand with no feedback."""
        result = fp_tools.retrieve_feedback_history(999)
        
        # Should return empty list (no feedback yet)
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_retrieve_feedback_history_returns_list(self):
        """Test that function returns a list."""
        result = fp_tools.retrieve_feedback_history(123)
        
        assert isinstance(result, list)


class TestExtractIssues:
    """Test issue extraction from feedback text."""
    
    def test_extract_false_positive_issue(self):
        """Test extracting false positive issue."""
        issues = fp_tools._extract_issues("Too many false positives in the results.")
        
        assert "False positives detected" in issues
    
    def test_extract_missing_pattern_issue(self):
        """Test extracting missing pattern issue."""
        issues = fp_tools._extract_issues("The regex is missing some legitimate transactions.")
        
        assert "Missing patterns or narratives" in issues
    
    def test_extract_wallet_issue(self):
        """Test extracting wallet handling issue."""
        issues = fp_tools._extract_issues("PayPal transactions are not filtered correctly.")
        
        assert "Payment wallet handling issue" in issues
    
    def test_extract_mccid_issue(self):
        """Test extracting MCCID issue."""
        issues = fp_tools._extract_issues("The MCCID list contains incorrect codes.")
        
        assert "MCCID classification issue" in issues
    
    def test_extract_ambiguity_issue(self):
        """Test extracting ambiguity issue."""
        issues = fp_tools._extract_issues("Brand name is too generic and ambiguous.")
        
        assert "Ambiguous brand name" in issues
    
    def test_extract_multiple_issues(self):
        """Test extracting multiple issues."""
        issues = fp_tools._extract_issues("False positives and missing patterns. Also MCCID is wrong.")
        
        assert len(issues) >= 2
        assert "False positives detected" in issues
        assert "Missing patterns or narratives" in issues or "MCCID classification issue" in issues
    
    def test_extract_no_specific_issues(self):
        """Test with general feedback."""
        issues = fp_tools._extract_issues("Please review this brand.")
        
        assert issues == ["General feedback"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
