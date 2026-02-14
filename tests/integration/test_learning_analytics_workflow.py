"""
Integration tests for Learning Analytics workflow.

This module tests the complete learning analytics workflow including
trend analysis, accuracy metrics calculation, and report generation.

Note: These tests verify the workflow components work together correctly.
Full end-to-end testing with AWS services would require actual AWS infrastructure.
"""

import pytest
from unittest.mock import Mock, patch

from agents.learning_analytics import tools as la_tools


class TestFeedbackTrendAnalysis:
    """Test feedback trend analysis across brands."""

    def test_analyze_feedback_trends(self):
        """Test analyzing feedback trends with time range and filters."""
        result = la_tools.analyze_feedback_trends(
            time_range="last_30_days",
            filters={"brandid": 123}
        )
        
        assert isinstance(result, dict)
        assert "analysis_period" in result or "time_range" in result
        # Filters parameter is used internally but not returned in result
    
    def test_identify_common_issues(self):
        """Test identifying common issues with minimum frequency."""
        result = la_tools.identify_common_issues(min_frequency=2)
        
        assert isinstance(result, list)
        # In test environment without data, returns empty list
    
    def test_aggregate_feedback_by_category(self):
        """Test aggregating feedback by category."""
        result = la_tools.aggregate_feedback_by_category(time_range="last_30_days")
        
        assert isinstance(result, dict)


class TestAccuracyMetricsCalculation:
    """Test accuracy metrics calculation."""

    def test_calculate_accuracy_metrics(self):
        """Test calculating accuracy metrics for a brand."""
        result = la_tools.calculate_accuracy_metrics(brandid=123)
        
        assert isinstance(result, dict)
        assert "brandid" in result
        assert result["brandid"] == 123
    
    def test_calculate_improvement_rate(self):
        """Test calculating improvement rate over time."""
        result = la_tools.calculate_improvement_rate(
            brandid=123,
            time_range="last_30_days"
        )
        
        assert isinstance(result, float)
        assert result >= 0.0
    
    def test_calculate_system_wide_metrics(self):
        """Test calculating system-wide metrics."""
        result = la_tools.calculate_system_wide_metrics(time_range="last_30_days")
        
        assert isinstance(result, dict)
        assert "total_brands" in result


class TestReportGeneration:
    """Test report generation."""

    def test_generate_improvement_report(self):
        """Test generating improvement report."""
        result = la_tools.generate_improvement_report(time_range="monthly")
        
        assert isinstance(result, dict)
        assert "period" in result or "time_range" in result
        assert "report_generated_at" in result or "generated_at" in result
    
    def test_identify_problematic_brands(self):
        """Test identifying problematic brands."""
        result = la_tools.identify_problematic_brands(threshold=0.80)
        
        assert isinstance(result, list)
        # In test environment without data, returns empty list


class TestWalletHandlingAnalysis:
    """Test wallet handling effectiveness analysis."""

    def test_analyze_wallet_handling_effectiveness(self):
        """Test analyzing wallet handling effectiveness."""
        result = la_tools.analyze_wallet_handling_effectiveness()
        
        assert isinstance(result, dict)
        assert "detection_accuracy" in result or "wallet_feedback_count" in result


class TestSystemImprovementRecommendations:
    """Test system improvement recommendations."""

    def test_recommend_system_improvements(self):
        """Test generating system improvement recommendations."""
        result = la_tools.recommend_system_improvements()
        
        assert isinstance(result, list)
        # Returns list of recommendation strings


class TestLearningAnalyticsIntegration:
    """Test complete learning analytics workflow."""

    def test_complete_analytics_workflow(self):
        """Test complete analytics workflow from data to report.
        
        Workflow:
        1. Analyze feedback trends
        2. Calculate accuracy metrics
        3. Identify problematic brands
        4. Generate improvement report
        """
        # Step 1: Analyze feedback trends
        trends = la_tools.analyze_feedback_trends(
            time_range="last_30_days",
            filters={}
        )
        
        assert isinstance(trends, dict)
        
        # Step 2: Calculate accuracy metrics for a brand
        metrics = la_tools.calculate_accuracy_metrics(brandid=123)
        
        assert isinstance(metrics, dict)
        assert metrics["brandid"] == 123
        
        # Step 3: Identify problematic brands
        problematic = la_tools.identify_problematic_brands(threshold=0.80)
        
        assert isinstance(problematic, list)
        
        # Step 4: Generate improvement report
        report = la_tools.generate_improvement_report(time_range="monthly")
        
        assert isinstance(report, dict)
        assert "period" in report or "time_range" in report
    
    def test_workflow_with_different_time_ranges(self):
        """Test workflow with different time ranges."""
        # Test with different time ranges
        time_ranges = ["last_7_days", "last_30_days", "last_90_days"]
        
        for time_range in time_ranges:
            trends = la_tools.analyze_feedback_trends(
                time_range=time_range,
                filters={}
            )
            
            assert isinstance(trends, dict)
            # Check for either time_range or analysis_period
            assert "time_range" in trends or "analysis_period" in trends


class TestMetricsAggregation:
    """Test metrics aggregation across brands."""

    def test_system_wide_metrics_calculation(self):
        """Test calculating system-wide metrics."""
        result = la_tools.calculate_system_wide_metrics(time_range="last_30_days")
        
        assert isinstance(result, dict)
        assert "total_brands" in result
        assert "average_approval_rate" in result or "average_accuracy" in result
    
    def test_feedback_category_aggregation(self):
        """Test aggregating feedback by category."""
        result = la_tools.aggregate_feedback_by_category(time_range="last_30_days")
        
        assert isinstance(result, dict)
        # Returns category counts


class TestImprovementTracking:
    """Test improvement tracking over time."""

    def test_improvement_rate_calculation(self):
        """Test calculating improvement rate for a brand."""
        result = la_tools.calculate_improvement_rate(
            brandid=123,
            time_range="last_30_days"
        )
        
        assert isinstance(result, float)
        assert result >= 0.0
    
    def test_improvement_rate_different_time_ranges(self):
        """Test improvement rate with different time ranges."""
        time_ranges = ["last_7_days", "last_30_days", "last_90_days"]
        
        for time_range in time_ranges:
            result = la_tools.calculate_improvement_rate(
                brandid=123,
                time_range=time_range
            )
            
            assert isinstance(result, float)
            assert result >= 0.0
