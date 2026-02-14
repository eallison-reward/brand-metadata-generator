"""
Learning Analytics Agent Tools

This module provides tools for the Learning Analytics Agent to analyze
historical feedback and track accuracy trends over time.

The Learning Analytics Agent:
- Aggregates feedback across all brands
- Identifies common issues (e.g., wallet handling problems, sector mismatches)
- Calculates accuracy metrics per brand (false positive rate, approval rate, iteration count)
- Tracks accuracy improvements over time
- Generates improvement recommendations for system-wide issues
- Produces reports for management showing trends and insights
- Identifies problematic brands requiring additional attention
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_feedback_trends(time_range: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify patterns across brands.
    
    Aggregates feedback data across all brands to identify common issues,
    trends, and patterns that indicate systematic problems.
    
    Args:
        time_range: Time period to analyze (e.g., "last_30_days", "last_month")
        filters: Optional filters including min_feedback_count, sectors, etc.
        
    Returns:
        Dictionary with trend analysis including:
        - analysis_period: Date range analyzed
        - total_brands_processed: Total number of brands
        - brands_with_feedback: Number of brands with feedback
        - common_issues: List of most frequent issues with counts
        - accuracy_trends: Overall accuracy metrics
        - problematic_brands: Brands needing attention
        - recommendations: System-wide improvement suggestions
    
    Requirements: 16.6, 16.11
    """
    logger.info(f"Analyzing feedback trends for {time_range}")
    
    # Parse time range
    end_date = datetime.utcnow()
    if time_range == "last_30_days":
        start_date = end_date - timedelta(days=30)
    elif time_range == "last_month":
        # Previous calendar month
        start_date = end_date.replace(day=1) - timedelta(days=1)
        start_date = start_date.replace(day=1)
    elif time_range == "last_7_days":
        start_date = end_date - timedelta(days=7)
    else:
        # Default to last 30 days
        start_date = end_date - timedelta(days=30)
    
    min_feedback_count = filters.get("min_feedback_count", 1)
    
    # In production, this would query DynamoDB and S3 for feedback data
    # For now, we'll return a structured response with placeholder data
    
    # Placeholder for actual data aggregation
    # feedback_records = query_feedback_from_dynamodb(start_date, end_date)
    # brand_metrics = aggregate_brand_metrics(feedback_records)
    
    # Simulate common issues analysis
    common_issues = identify_common_issues(min_frequency=min_feedback_count)
    
    return {
        "analysis_period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        "total_brands_processed": 3000,  # Placeholder
        "brands_with_feedback": 450,  # Placeholder
        "common_issues": common_issues,
        "accuracy_trends": {
            "average_approval_rate": 0.85,
            "average_iterations_per_brand": 1.8,
            "improvement_rate": 0.12  # 12% improvement over period
        },
        "problematic_brands": identify_problematic_brands(threshold=0.5),
        "recommendations": recommend_system_improvements()
    }


def identify_common_issues(min_frequency: int) -> List[Dict[str, Any]]:
    """
    Find systematic problems.
    
    Analyzes feedback across all brands to identify issues that occur
    frequently, indicating systematic problems in the system.
    
    Args:
        min_frequency: Minimum number of occurrences to be considered common
        
    Returns:
        List of common issues with frequency counts and examples
    
    Requirements: 16.6
    """
    logger.info(f"Identifying common issues with min frequency {min_frequency}")
    
    # In production, this would aggregate feedback categories from DynamoDB
    # For now, return structured placeholder data
    
    # Simulate issue aggregation
    issues = [
        {
            "issue": "regex_too_broad",
            "frequency": 120,
            "percentage": 26.7,
            "example_brands": [123, 456, 789],
            "description": "Regex patterns matching too many unrelated narratives"
        },
        {
            "issue": "wallet_text_not_excluded",
            "frequency": 85,
            "percentage": 18.9,
            "example_brands": [234, 567],
            "description": "Payment wallet prefixes not properly filtered"
        },
        {
            "issue": "mccid_mismatch",
            "frequency": 60,
            "percentage": 13.3,
            "example_brands": [345, 678],
            "description": "MCCID lists contain codes inconsistent with brand sector"
        },
        {
            "issue": "ambiguous_brand_name",
            "frequency": 45,
            "percentage": 10.0,
            "example_brands": [999, 888],
            "description": "Brand names are too generic and match multiple entities"
        },
        {
            "issue": "regex_too_narrow",
            "frequency": 35,
            "percentage": 7.8,
            "example_brands": [111, 222],
            "description": "Regex patterns missing legitimate narrative variations"
        }
    ]
    
    # Filter by minimum frequency
    filtered_issues = [issue for issue in issues if issue["frequency"] >= min_frequency]
    
    logger.info(f"Found {len(filtered_issues)} common issues")
    
    return filtered_issues


def calculate_accuracy_metrics(brandid: int) -> Dict[str, Any]:
    """
    Measure classification accuracy.
    
    Calculates detailed accuracy metrics for a specific brand including
    false positive rate, false negative rate, approval rate, and iteration count.
    
    Args:
        brandid: Brand identifier
        
    Returns:
        Dictionary with accuracy metrics including:
        - approval_rate: Percentage of first-attempt approvals
        - false_positive_rate: Percentage of matched combos excluded
        - iteration_count: Number of regeneration cycles
        - feedback_count: Total feedback submissions
        - last_updated: Timestamp of last update
    
    Requirements: 16.7
    """
    logger.info(f"Calculating accuracy metrics for brand {brandid}")
    
    # In production, this would query DynamoDB for brand-specific metrics
    # For now, return structured placeholder data
    
    # Placeholder for actual metric calculation
    # feedback_history = retrieve_feedback_history(brandid)
    # metadata_versions = retrieve_metadata_versions(brandid)
    # classification_results = retrieve_classification_results(brandid)
    
    return {
        "brandid": brandid,
        "approval_rate": 0.75,  # Placeholder
        "false_positive_rate": 0.15,  # Placeholder
        "false_negative_rate": 0.10,  # Placeholder
        "iteration_count": 2,  # Placeholder
        "feedback_count": 3,  # Placeholder
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "confidence_score": 0.82  # Placeholder
    }


def calculate_improvement_rate(brandid: int, time_range: str) -> float:
    """
    Track accuracy changes.
    
    Calculates the rate of improvement in classification accuracy
    for a brand over a specified time period.
    
    Args:
        brandid: Brand identifier
        time_range: Time period to analyze
        
    Returns:
        Improvement rate as a float (e.g., 0.15 = 15% improvement)
    
    Requirements: 16.8
    """
    logger.info(f"Calculating improvement rate for brand {brandid} over {time_range}")
    
    # In production, this would compare metrics from start and end of period
    # For now, return placeholder value
    
    # Placeholder for actual calculation
    # initial_metrics = get_metrics_at_start_of_period(brandid, time_range)
    # current_metrics = get_current_metrics(brandid)
    # improvement = (current_metrics.approval_rate - initial_metrics.approval_rate) / initial_metrics.approval_rate
    
    return 0.15  # Placeholder: 15% improvement


def generate_improvement_report(time_range: str) -> Dict[str, Any]:
    """
    Create management summary.
    
    Generates a comprehensive report for management showing accuracy trends,
    common issues, success stories, and action items.
    
    Args:
        time_range: Time period to report on
        
    Returns:
        Dictionary with report data including:
        - report_title: Report title
        - period: Time period covered
        - summary: Key statistics
        - accuracy_improvement: Overall improvement metric
        - top_issues: Most common problems
        - success_stories: Positive improvements
        - action_items: Recommended actions
    
    Requirements: 16.13
    """
    logger.info(f"Generating improvement report for {time_range}")
    
    # Parse time range for report title
    if time_range == "last_month":
        period = (datetime.utcnow() - timedelta(days=30)).strftime("%B %Y")
    else:
        period = time_range
    
    # In production, this would aggregate data from multiple sources
    # For now, return structured placeholder report
    
    return {
        "report_title": "Brand Metadata Generator - Performance Report",
        "period": period,
        "summary": {
            "brands_processed": 3000,
            "brands_approved_first_attempt": 2550,
            "brands_requiring_feedback": 450,
            "average_iterations": 1.8,
            "overall_approval_rate": 0.92
        },
        "accuracy_improvement": "+12% vs previous period",
        "top_issues": [
            "regex_too_broad (26.7%)",
            "wallet_handling (18.9%)",
            "mccid_mismatch (13.3%)"
        ],
        "success_stories": [
            "Wallet detection improved from 75% to 89% accuracy",
            "Average iterations reduced from 2.3 to 1.8",
            "First-attempt approval rate increased from 80% to 85%"
        ],
        "action_items": [
            "Focus on ambiguous brand names (Apple, Shell, etc.)",
            "Enhance wallet pattern detection for 'SQ *' prefix",
            "Review MCCID-sector mappings for retail brands",
            "Implement negative lookahead training for common false positives"
        ],
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


def identify_problematic_brands(threshold: float) -> List[Dict[str, Any]]:
    """
    Find brands needing attention.
    
    Identifies brands with low approval rates, high iteration counts,
    or frequent feedback that require additional attention.
    
    Args:
        threshold: Approval rate threshold below which brands are flagged
        
    Returns:
        List of problematic brands with details
    
    Requirements: 16.10
    """
    logger.info(f"Identifying problematic brands with threshold {threshold}")
    
    # In production, this would query DynamoDB for brands with low metrics
    # For now, return structured placeholder data
    
    problematic_brands = [
        {
            "brandid": 999,
            "brandname": "Apple",
            "feedback_count": 8,
            "approval_rate": 0.30,
            "iteration_count": 5,
            "issue": "Ambiguous name matches apple orchards and other unrelated entities",
            "recommendation": "Add sector-specific context to regex pattern"
        },
        {
            "brandid": 888,
            "brandname": "Shell",
            "feedback_count": 6,
            "approval_rate": 0.40,
            "iteration_count": 4,
            "issue": "Matches both Shell gas stations and Shell seafood restaurants",
            "recommendation": "Use MCCID filtering to distinguish between fuel and food sectors"
        },
        {
            "brandid": 777,
            "brandname": "Square",
            "feedback_count": 7,
            "approval_rate": 0.35,
            "iteration_count": 5,
            "issue": "Confusion between Square payment processor and Square retail stores",
            "recommendation": "Implement negative lookahead to exclude payment processor narratives"
        }
    ]
    
    # Filter by threshold
    filtered_brands = [b for b in problematic_brands if b["approval_rate"] < threshold]
    
    logger.info(f"Found {len(filtered_brands)} problematic brands")
    
    return filtered_brands


def analyze_wallet_handling_effectiveness() -> Dict[str, Any]:
    """
    Assess payment wallet detection accuracy.
    
    Analyzes how effectively the system detects and handles payment
    wallet complications across all brands.
    
    Args:
        None
        
    Returns:
        Dictionary with wallet handling metrics including:
        - detection_accuracy: Percentage of wallets correctly detected
        - exclusion_accuracy: Percentage of wallet text correctly excluded
        - common_wallet_types: Most frequent wallet types
        - improvement_suggestions: Recommendations for improvement
    
    Requirements: 16.11
    """
    logger.info("Analyzing wallet handling effectiveness")
    
    # In production, this would analyze wallet-related feedback and metrics
    # For now, return structured placeholder data
    
    return {
        "detection_accuracy": 0.89,  # 89% of wallet indicators detected
        "exclusion_accuracy": 0.85,  # 85% of wallet text properly excluded
        "common_wallet_types": {
            "PayPal": {"count": 450, "detection_rate": 0.92},
            "Square": {"count": 380, "detection_rate": 0.87},
            "PP *": {"count": 220, "detection_rate": 0.90},
            "SQ *": {"count": 180, "detection_rate": 0.83}
        },
        "improvement_suggestions": [
            "Improve detection of 'SQ *' prefix pattern (currently 83%)",
            "Add detection for emerging wallet patterns",
            "Enhance MCCID filtering for wallet-specific codes"
        ],
        "trend": "Improving - detection accuracy increased from 75% to 89% over last 3 months"
    }


def recommend_system_improvements() -> List[str]:
    """
    Generate actionable recommendations.
    
    Analyzes all feedback and metrics to generate specific, actionable
    recommendations for system-wide improvements.
    
    Args:
        None
        
    Returns:
        List of recommendation strings
    
    Requirements: 16.6
    """
    logger.info("Generating system improvement recommendations")
    
    # In production, this would analyze trends and patterns to generate recommendations
    # For now, return structured placeholder recommendations
    
    recommendations = [
        "Improve wallet detection to handle 'SQ *' prefix patterns (currently 83% accuracy)",
        "Add negative lookahead training for common false positives (Starburst vs Starbucks)",
        "Review brands with common words (Apple, Shell, Orange) for disambiguation strategies",
        "Implement sector-specific regex templates to improve initial generation accuracy",
        "Create a library of known false positive patterns to avoid in regex generation",
        "Enhance MCCID-sector validation to catch misclassifications earlier",
        "Add automated testing of regex patterns against known false positive examples",
        "Implement confidence score calibration based on historical accuracy data"
    ]
    
    return recommendations


def aggregate_feedback_by_category(time_range: str) -> Dict[str, int]:
    """
    Aggregate feedback counts by category.
    
    Helper function to count feedback occurrences by category
    over a specified time period.
    
    Args:
        time_range: Time period to analyze
        
    Returns:
        Dictionary mapping category names to counts
    """
    logger.info(f"Aggregating feedback by category for {time_range}")
    
    # In production, this would query DynamoDB
    # For now, return placeholder data
    
    return {
        "regex_too_broad": 120,
        "wallet_text_not_excluded": 85,
        "mccid_mismatch": 60,
        "ambiguous_brand_name": 45,
        "regex_too_narrow": 35,
        "general": 105
    }


def calculate_system_wide_metrics(time_range: str) -> Dict[str, Any]:
    """
    Calculate overall system performance metrics.
    
    Aggregates metrics across all brands to provide system-wide
    performance indicators.
    
    Args:
        time_range: Time period to analyze
        
    Returns:
        Dictionary with system-wide metrics
    """
    logger.info(f"Calculating system-wide metrics for {time_range}")
    
    # In production, this would aggregate from all brand metrics
    # For now, return placeholder data
    
    return {
        "total_brands": 3000,
        "brands_processed": 3000,
        "average_approval_rate": 0.85,
        "average_confidence_score": 0.82,
        "average_iterations": 1.8,
        "total_feedback_submissions": 450,
        "brands_requiring_escalation": 15,
        "processing_time_avg_seconds": 45.2
    }
