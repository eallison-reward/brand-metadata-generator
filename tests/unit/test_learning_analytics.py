"""
Unit Tests for Learning Analytics Agent

Tests the trend analysis, accuracy metrics calculation, and report generation
functionality of the Learning Analytics Agent.

Requirements: 16.7, 16.8, 16.13
"""

import pytest
from agents.learning_analytics import tools as la_tools


class TestAnalyzeFeedbackTrends:
    """Test feedback trend analysis functionality."""
    
    def test_analyze_trends_last_30_days(self):
        """Test analyzing trends for last 30 days."""
        result = la_tools.analyze_feedback_trends("last_30_days", {"min_feedback_count": 1})
        
        assert "analysis_period" in result
        assert "total_brands_processed" in result
        assert "brands_with_feedback" in result
        assert "common_issues" in result
        assert "accuracy_trends" in result
        assert "problematic_brands" in result
        assert "recommendations" in result
    
    def test_analyze_trends_last_month(self):
        """Test analyzing trends for last month."""
        result = la_tools.analyze_feedback_trends("last_month", {})
        
        assert result["total_brands_processed"] > 0
        assert isinstance(result["common_issues"], list)
        assert isinstance(result["recommendations"], list)
    
    def test_analyze_trends_with_min_feedback_filter(self):
        """Test trend analysis with minimum feedback count filter."""
        result = la_tools.analyze_feedback_trends("last_30_days", {"min_feedback_count": 5})
        
        # Should still return valid structure
        assert "common_issues" in result
        assert isinstance(result["common_issues"], list)
    
    def test_analyze_trends_accuracy_metrics(self):
        """Test that accuracy trends are included."""
        result = la_tools.analyze_feedback_trends("last_30_days", {})
        
        assert "accuracy_trends" in result
        assert "average_approval_rate" in result["accuracy_trends"]
        assert "average_iterations_per_brand" in result["accuracy_trends"]
        assert "improvement_rate" in result["accuracy_trends"]
    
    def test_analyze_trends_date_range_format(self):
        """Test that analysis period is properly formatted."""
        result = la_tools.analyze_feedback_trends("last_7_days", {})
        
        assert "to" in result["analysis_period"]
        # Should contain date format YYYY-MM-DD
        assert len(result["analysis_period"].split(" to ")) == 2


class TestIdentifyCommonIssues:
    """Test common issue identification."""
    
    def test_identify_issues_with_min_frequency(self):
        """Test identifying issues with minimum frequency."""
        result = la_tools.identify_common_issues(min_frequency=10)
        
        assert isinstance(result, list)
        # All issues should meet minimum frequency
        for issue in result:
            assert issue["frequency"] >= 10
    
    def test_identify_issues_structure(self):
        """Test that issues have proper structure."""
        result = la_tools.identify_common_issues(min_frequency=1)
        
        assert len(result) > 0
        for issue in result:
            assert "issue" in issue
            assert "frequency" in issue
            assert "percentage" in issue
            assert "example_brands" in issue
            assert "description" in issue
    
    def test_identify_issues_high_frequency_filter(self):
        """Test filtering with high minimum frequency."""
        result = la_tools.identify_common_issues(min_frequency=100)
        
        # Should return fewer issues
        assert isinstance(result, list)
        for issue in result:
            assert issue["frequency"] >= 100
    
    def test_identify_issues_zero_frequency(self):
        """Test with zero minimum frequency."""
        result = la_tools.identify_common_issues(min_frequency=0)
        
        # Should return all issues
        assert len(result) > 0


class TestCalculateAccuracyMetrics:
    """Test accuracy metrics calculation."""
    
    def test_calculate_metrics_basic(self):
        """Test basic accuracy metrics calculation."""
        result = la_tools.calculate_accuracy_metrics(123)
        
        assert result["brandid"] == 123
        assert "approval_rate" in result
        assert "false_positive_rate" in result
        assert "false_negative_rate" in result
        assert "iteration_count" in result
        assert "feedback_count" in result
        assert "last_updated" in result
    
    def test_calculate_metrics_rates_in_range(self):
        """Test that rates are between 0 and 1."""
        result = la_tools.calculate_accuracy_metrics(456)
        
        assert 0.0 <= result["approval_rate"] <= 1.0
        assert 0.0 <= result["false_positive_rate"] <= 1.0
        assert 0.0 <= result["false_negative_rate"] <= 1.0
    
    def test_calculate_metrics_iteration_count(self):
        """Test that iteration count is non-negative."""
        result = la_tools.calculate_accuracy_metrics(789)
        
        assert result["iteration_count"] >= 0
        assert result["feedback_count"] >= 0
    
    def test_calculate_metrics_timestamp_format(self):
        """Test that timestamp is in ISO format."""
        result = la_tools.calculate_accuracy_metrics(111)
        
        assert "T" in result["last_updated"]
        assert "Z" in result["last_updated"]


class TestCalculateImprovementRate:
    """Test improvement rate calculation."""
    
    def test_calculate_improvement_rate_basic(self):
        """Test basic improvement rate calculation."""
        result = la_tools.calculate_improvement_rate(123, "last_30_days")
        
        assert isinstance(result, float)
    
    def test_calculate_improvement_rate_different_periods(self):
        """Test improvement rate for different time periods."""
        rate_30_days = la_tools.calculate_improvement_rate(123, "last_30_days")
        rate_month = la_tools.calculate_improvement_rate(123, "last_month")
        
        assert isinstance(rate_30_days, float)
        assert isinstance(rate_month, float)
    
    def test_calculate_improvement_rate_range(self):
        """Test that improvement rate is reasonable."""
        result = la_tools.calculate_improvement_rate(456, "last_30_days")
        
        # Should be between -1.0 and 1.0 (100% decrease to 100% increase)
        assert -1.0 <= result <= 1.0


class TestGenerateImprovementReport:
    """Test improvement report generation."""
    
    def test_generate_report_basic(self):
        """Test basic report generation."""
        result = la_tools.generate_improvement_report("last_month")
        
        assert "report_title" in result
        assert "period" in result
        assert "summary" in result
        assert "accuracy_improvement" in result
        assert "top_issues" in result
        assert "success_stories" in result
        assert "action_items" in result
        assert "generated_at" in result
    
    def test_generate_report_summary_structure(self):
        """Test that summary has proper structure."""
        result = la_tools.generate_improvement_report("last_month")
        
        summary = result["summary"]
        assert "brands_processed" in summary
        assert "brands_approved_first_attempt" in summary
        assert "brands_requiring_feedback" in summary
        assert "average_iterations" in summary
        assert "overall_approval_rate" in summary
    
    def test_generate_report_lists_not_empty(self):
        """Test that report lists contain data."""
        result = la_tools.generate_improvement_report("last_30_days")
        
        assert len(result["top_issues"]) > 0
        assert len(result["success_stories"]) > 0
        assert len(result["action_items"]) > 0
    
    def test_generate_report_timestamp(self):
        """Test that report has generation timestamp."""
        result = la_tools.generate_improvement_report("last_month")
        
        assert "generated_at" in result
        assert "T" in result["generated_at"]
        assert "Z" in result["generated_at"]


class TestIdentifyProblematicBrands:
    """Test problematic brand identification."""
    
    def test_identify_problematic_brands_basic(self):
        """Test basic problematic brand identification."""
        result = la_tools.identify_problematic_brands(threshold=0.5)
        
        assert isinstance(result, list)
        # All brands should be below threshold
        for brand in result:
            assert brand["approval_rate"] < 0.5
    
    def test_identify_problematic_brands_structure(self):
        """Test that problematic brands have proper structure."""
        result = la_tools.identify_problematic_brands(threshold=0.6)
        
        for brand in result:
            assert "brandid" in brand
            assert "brandname" in brand
            assert "feedback_count" in brand
            assert "approval_rate" in brand
            assert "iteration_count" in brand
            assert "issue" in brand
            assert "recommendation" in brand
    
    def test_identify_problematic_brands_high_threshold(self):
        """Test with high threshold."""
        result = la_tools.identify_problematic_brands(threshold=0.9)
        
        # Should return more brands
        assert isinstance(result, list)
    
    def test_identify_problematic_brands_low_threshold(self):
        """Test with low threshold."""
        result = la_tools.identify_problematic_brands(threshold=0.2)
        
        # Should return fewer brands
        assert isinstance(result, list)
        for brand in result:
            assert brand["approval_rate"] < 0.2


class TestAnalyzeWalletHandlingEffectiveness:
    """Test wallet handling effectiveness analysis."""
    
    def test_analyze_wallet_handling_basic(self):
        """Test basic wallet handling analysis."""
        result = la_tools.analyze_wallet_handling_effectiveness()
        
        assert "detection_accuracy" in result
        assert "exclusion_accuracy" in result
        assert "common_wallet_types" in result
        assert "improvement_suggestions" in result
        assert "trend" in result
    
    def test_analyze_wallet_handling_accuracy_range(self):
        """Test that accuracy values are in valid range."""
        result = la_tools.analyze_wallet_handling_effectiveness()
        
        assert 0.0 <= result["detection_accuracy"] <= 1.0
        assert 0.0 <= result["exclusion_accuracy"] <= 1.0
    
    def test_analyze_wallet_handling_wallet_types(self):
        """Test that common wallet types are included."""
        result = la_tools.analyze_wallet_handling_effectiveness()
        
        wallet_types = result["common_wallet_types"]
        assert isinstance(wallet_types, dict)
        assert len(wallet_types) > 0
        
        # Check structure of wallet type data
        for wallet_type, data in wallet_types.items():
            assert "count" in data
            assert "detection_rate" in data
    
    def test_analyze_wallet_handling_suggestions(self):
        """Test that improvement suggestions are provided."""
        result = la_tools.analyze_wallet_handling_effectiveness()
        
        assert isinstance(result["improvement_suggestions"], list)
        assert len(result["improvement_suggestions"]) > 0


class TestRecommendSystemImprovements:
    """Test system improvement recommendations."""
    
    def test_recommend_improvements_basic(self):
        """Test basic recommendation generation."""
        result = la_tools.recommend_system_improvements()
        
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_recommend_improvements_are_strings(self):
        """Test that recommendations are strings."""
        result = la_tools.recommend_system_improvements()
        
        for recommendation in result:
            assert isinstance(recommendation, str)
            assert len(recommendation) > 0
    
    def test_recommend_improvements_actionable(self):
        """Test that recommendations are actionable."""
        result = la_tools.recommend_system_improvements()
        
        # Recommendations should contain action verbs
        action_verbs = ["improve", "add", "enhance", "implement", "review", "create"]
        
        for recommendation in result:
            recommendation_lower = recommendation.lower()
            has_action_verb = any(verb in recommendation_lower for verb in action_verbs)
            assert has_action_verb, f"Recommendation should be actionable: {recommendation}"


class TestAggregateFeedbackByCategory:
    """Test feedback aggregation by category."""
    
    def test_aggregate_feedback_basic(self):
        """Test basic feedback aggregation."""
        result = la_tools.aggregate_feedback_by_category("last_30_days")
        
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_aggregate_feedback_categories(self):
        """Test that expected categories are present."""
        result = la_tools.aggregate_feedback_by_category("last_month")
        
        expected_categories = [
            "regex_too_broad",
            "regex_too_narrow",
            "wallet_text_not_excluded",
            "mccid_mismatch",
            "ambiguous_brand_name"
        ]
        
        for category in expected_categories:
            assert category in result
    
    def test_aggregate_feedback_counts(self):
        """Test that counts are non-negative."""
        result = la_tools.aggregate_feedback_by_category("last_7_days")
        
        for category, count in result.items():
            assert count >= 0


class TestCalculateSystemWideMetrics:
    """Test system-wide metrics calculation."""
    
    def test_calculate_system_metrics_basic(self):
        """Test basic system-wide metrics calculation."""
        result = la_tools.calculate_system_wide_metrics("last_30_days")
        
        assert "total_brands" in result
        assert "brands_processed" in result
        assert "average_approval_rate" in result
        assert "average_confidence_score" in result
        assert "average_iterations" in result
        assert "total_feedback_submissions" in result
    
    def test_calculate_system_metrics_rates(self):
        """Test that rates are in valid range."""
        result = la_tools.calculate_system_wide_metrics("last_month")
        
        assert 0.0 <= result["average_approval_rate"] <= 1.0
        assert 0.0 <= result["average_confidence_score"] <= 1.0
    
    def test_calculate_system_metrics_counts(self):
        """Test that counts are non-negative."""
        result = la_tools.calculate_system_wide_metrics("last_7_days")
        
        assert result["total_brands"] >= 0
        assert result["brands_processed"] >= 0
        assert result["total_feedback_submissions"] >= 0
        assert result["brands_requiring_escalation"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
