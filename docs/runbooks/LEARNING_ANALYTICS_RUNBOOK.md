# Learning Analytics Interpretation Runbook

This runbook provides guidance on interpreting learning analytics data from the Brand Metadata Generator system, enabling data-driven improvements to metadata quality and system performance.

## Overview

The Learning Analytics Agent analyzes feedback trends, calculates accuracy metrics, and generates improvement reports. This runbook helps operators understand these analytics and take appropriate actions.

## Table of Contents

1. [Analytics Overview](#analytics-overview)
2. [Key Metrics](#key-metrics)
3. [Report Interpretation](#report-interpretation)
4. [Trend Analysis](#trend-analysis)
5. [Action Planning](#action-planning)

## Analytics Overview

### Data Sources

The Learning Analytics Agent analyzes:
- Feedback submissions and history
- Iteration counts per brand
- Metadata versions and changes
- Approval/rejection rates
- Confidence scores over time
- Common error patterns

### Analytics Outputs

1. **Feedback Trend Reports**
   - Common issues across brands
   - Feedback categories and frequencies
   - Temporal trends

2. **Accuracy Metrics**
   - False positive/negative rates
   - Confidence score distributions
   - Improvement rates over iterations

3. **Improvement Reports**
   - Brands showing improvement
   - Problematic brands
   - Systematic issues

4. **Executive Summaries**
   - High-level KPIs
   - Trends and insights
   - Recommendations

## Key Metrics

### Metric 1: Approval Rate

**Definition**: Percentage of brands approved on first iteration

**Formula**: (Brands Approved on First Iteration / Total Brands Processed) × 100

**Interpretation**:
- **>80%**: Excellent - metadata quality is high
- **60-80%**: Good - acceptable quality with room for improvement
- **40-60%**: Fair - significant quality issues
- **<40%**: Poor - systematic problems requiring attention

**Actions**:
- **>80%**: Maintain current approach, document best practices
- **60-80%**: Analyze rejected brands for patterns, minor improvements
- **40-60%**: Major review of algorithms and data quality needed
- **<40%**: Escalate to engineering, consider process redesign

**Example Query**:
```bash
python scripts/get_approval_rate.py \
  --start-date 2026-02-01 \
  --end-date 2026-02-14
```

### Metric 2: Average Iterations Per Brand

**Definition**: Mean number of feedback iterations before approval

**Formula**: Sum(Iterations) / Count(Brands)

**Interpretation**:
- **1-2**: Excellent - minimal rework needed
- **2-4**: Good - reasonable iteration count
- **4-6**: Fair - excessive rework
- **>6**: Poor - systematic issues or poor feedback quality

**Actions**:
- **1-2**: Document successful patterns
- **2-4**: Analyze high-iteration brands for common issues
- **4-6**: Review feedback quality and agent instructions
- **>6**: Escalate, consider manual processing for problematic brands

**Example Query**:
```bash
python scripts/get_average_iterations.py \
  --start-date 2026-02-01 \
  --end-date 2026-02-14
```

### Metric 3: Escalation Rate

**Definition**: Percentage of brands escalated for manual review

**Formula**: (Escalated Brands / Total Brands) × 100

**Interpretation**:
- **<5%**: Excellent - automated processing working well
- **5-10%**: Good - acceptable escalation rate
- **10-20%**: Fair - high escalation rate
- **>20%**: Poor - automated processing not effective

**Actions**:
- **<5%**: Monitor for changes, maintain current approach
- **5-10%**: Analyze escalation reasons, minor improvements
- **10-20%**: Major review of escalation triggers and thresholds
- **>20%**: Escalate to engineering, consider process changes

**Example Query**:
```bash
python scripts/get_escalation_rate.py \
  --start-date 2026-02-01 \
  --end-date 2026-02-14
```

### Metric 4: Confidence Score Distribution

**Definition**: Distribution of confidence scores across brands

**Interpretation**:
- **High confidence (>0.8)**: Strong metadata quality
- **Medium confidence (0.6-0.8)**: Acceptable quality
- **Low confidence (<0.6)**: Questionable quality

**Target Distribution**:
- >70% of brands with confidence >0.8
- <10% of brands with confidence <0.6

**Actions**:
- If too many low confidence scores: Review data quality, improve algorithms
- If confidence scores don't correlate with approval: Recalibrate confidence calculation

**Example Query**:
```bash
python scripts/get_confidence_distribution.py \
  --start-date 2026-02-01 \
  --end-date 2026-02-14
```

### Metric 5: Improvement Rate

**Definition**: Percentage improvement in metadata quality per iteration

**Formula**: (Quality Score After - Quality Score Before) / Quality Score Before × 100

**Interpretation**:
- **>20%**: Excellent - feedback driving significant improvements
- **10-20%**: Good - steady improvements
- **5-10%**: Fair - marginal improvements
- **<5%**: Poor - feedback not effective

**Actions**:
- **>20%**: Document successful feedback patterns
- **10-20%**: Continue current approach
- **5-10%**: Review feedback quality and agent responsiveness
- **<5%**: Escalate, review feedback processing logic

**Example Query**:
```bash
python scripts/get_improvement_rate.py \
  --start-date 2026-02-01 \
  --end-date 2026-02-14
```

### Metric 6: False Positive Rate

**Definition**: Percentage of combos incorrectly matched to brand

**Formula**: (False Positive Combos / Total Matched Combos) × 100

**Interpretation**:
- **<5%**: Excellent - high precision
- **5-10%**: Good - acceptable precision
- **10-20%**: Fair - precision issues
- **>20%**: Poor - significant precision problems

**Actions**:
- **<5%**: Maintain current approach
- **5-10%**: Review regex patterns for over-matching
- **10-20%**: Major review of pattern generation
- **>20%**: Escalate, consider stricter matching rules

**Example Query**:
```bash
python scripts/get_false_positive_rate.py \
  --start-date 2026-02-01 \
  --end-date 2026-02-14
```

### Metric 7: False Negative Rate

**Definition**: Percentage of combos incorrectly excluded from brand

**Formula**: (False Negative Combos / Total Relevant Combos) × 100

**Interpretation**:
- **<5%**: Excellent - high recall
- **5-10%**: Good - acceptable recall
- **10-20%**: Fair - recall issues
- **>20%**: Poor - significant recall problems

**Actions**:
- **<5%**: Maintain current approach
- **5-10%**: Review regex patterns for under-matching
- **10-20%**: Major review of pattern generation
- **>20%**: Escalate, consider broader matching rules

**Example Query**:
```bash
python scripts/get_false_negative_rate.py \
  --start-date 2026-02-01 \
  --end-date 2026-02-14
```

## Report Interpretation

### Daily Report

**Purpose**: Monitor day-to-day operations

**Contents**:
- Brands processed today
- Approval rate
- Escalations
- Average iterations
- Top issues

**How to Read**:
```bash
# Generate daily report
python scripts/generate_daily_report.py --date 2026-02-14

# Example output:
# Daily Report - 2026-02-14
# ========================
# Brands Processed: 45
# Approval Rate: 73% (33/45)
# Escalations: 2 (4%)
# Average Iterations: 2.3
# 
# Top Issues:
# 1. Regex too broad (8 occurrences)
# 2. MCCID mismatch (5 occurrences)
# 3. Wallet text included (3 occurrences)
```

**Interpretation**:
- **Approval rate 73%**: Good, within acceptable range
- **Escalations 4%**: Excellent, below 5% target
- **Average iterations 2.3**: Good, reasonable rework
- **Top issues**: Focus on regex broadness

**Actions**:
- Review brands with "regex too broad" feedback
- Update agent instructions for regex generation
- Monitor tomorrow's metrics for improvement

### Weekly Report

**Purpose**: Identify trends and patterns

**Contents**:
- Week-over-week trends
- Cumulative metrics
- Brand-level analysis
- Feedback category breakdown
- Improvement trends

**How to Read**:
```bash
# Generate weekly report
python scripts/generate_weekly_report.py \
  --start-date 2026-02-08 \
  --end-date 2026-02-14

# Example output:
# Weekly Report - Week of 2026-02-08
# ===================================
# Brands Processed: 312
# Approval Rate: 71% (221/312)
# Trend: ↓ 3% from previous week
# 
# Escalations: 18 (6%)
# Trend: ↑ 2% from previous week
# 
# Average Iterations: 2.5
# Trend: ↑ 0.3 from previous week
# 
# Feedback Categories:
# - Regex issues: 45% (↑ 5%)
# - MCCID issues: 30% (→ 0%)
# - Wallet handling: 15% (↓ 3%)
# - Other: 10% (↓ 2%)
```

**Interpretation**:
- **Approval rate declining**: Concerning trend
- **Escalations increasing**: Needs attention
- **Iterations increasing**: Quality degrading
- **Regex issues increasing**: Systematic problem

**Actions**:
- Investigate regex generation algorithm
- Review recent changes to agents or data
- Analyze specific brands with regex issues
- Plan improvements for next week

### Monthly Report

**Purpose**: Strategic planning and improvement

**Contents**:
- Month-over-month trends
- Systematic issue analysis
- Improvement recommendations
- Resource allocation suggestions
- Success stories

**How to Read**:
```bash
# Generate monthly report
python scripts/generate_monthly_report.py --month 2026-02

# Example output:
# Monthly Report - February 2026
# ===============================
# Brands Processed: 1,245
# Approval Rate: 74% (921/1,245)
# Trend: ↑ 2% from January
# 
# Escalations: 68 (5.5%)
# Trend: ↓ 1% from January
# 
# Average Iterations: 2.4
# Trend: → 0.0 from January
# 
# Systematic Issues Identified:
# 1. Generic brand names (e.g., "Star", "Best")
#    - Affects 12% of brands
#    - Recommendation: Pre-processing to flag ambiguous names
# 
# 2. Payment wallet handling
#    - Affects 8% of brands
#    - Recommendation: Improve wallet detection algorithm
# 
# 3. Multi-sector brands
#    - Affects 5% of brands
#    - Recommendation: Support multiple sectors per brand
# 
# Success Stories:
# - Improved regex generation reduced false positives by 15%
# - New MCCID validation reduced mismatches by 20%
```

**Interpretation**:
- **Overall trends positive**: Approval rate up, escalations down
- **Systematic issues identified**: Clear improvement opportunities
- **Success stories**: Recent improvements working

**Actions**:
- Prioritize systematic issues for next month
- Allocate resources to top 3 issues
- Continue successful approaches
- Plan feature development

## Trend Analysis

### Identifying Trends

**Upward Trends (Positive)**:
- Increasing approval rates
- Decreasing escalation rates
- Decreasing average iterations
- Increasing confidence scores
- Decreasing false positive/negative rates

**Downward Trends (Negative)**:
- Decreasing approval rates
- Increasing escalation rates
- Increasing average iterations
- Decreasing confidence scores
- Increasing false positive/negative rates

**Stable Trends**:
- Metrics within acceptable ranges
- No significant changes
- Predictable patterns

### Trend Analysis Queries

**Approval Rate Trend**:
```bash
python scripts/analyze_trend.py \
  --metric approval_rate \
  --period 30 \
  --granularity daily
```

**Escalation Rate Trend**:
```bash
python scripts/analyze_trend.py \
  --metric escalation_rate \
  --period 30 \
  --granularity daily
```

**Iteration Count Trend**:
```bash
python scripts/analyze_trend.py \
  --metric average_iterations \
  --period 30 \
  --granularity daily
```

### Correlation Analysis

**Identify Correlations**:
```bash
# Correlation between confidence scores and approval rates
python scripts/analyze_correlation.py \
  --metric1 confidence_score \
  --metric2 approval_rate \
  --period 30

# Correlation between iteration count and escalation rate
python scripts/analyze_correlation.py \
  --metric1 average_iterations \
  --metric2 escalation_rate \
  --period 30
```

**Interpretation**:
- **Strong positive correlation (>0.7)**: Metrics move together
- **Strong negative correlation (<-0.7)**: Metrics move opposite
- **Weak correlation (-0.3 to 0.3)**: No clear relationship

## Action Planning

### Action Plan Template

**Issue**: [Describe the issue]

**Metrics Affected**:
- [Metric 1]: [Current value] (Target: [Target value])
- [Metric 2]: [Current value] (Target: [Target value])

**Root Cause**: [Analysis of root cause]

**Proposed Actions**:
1. [Action 1] - [Owner] - [Timeline]
2. [Action 2] - [Owner] - [Timeline]
3. [Action 3] - [Owner] - [Timeline]

**Success Criteria**:
- [Metric 1] improves to [Target value] by [Date]
- [Metric 2] improves to [Target value] by [Date]

**Monitoring Plan**:
- Daily: [What to monitor]
- Weekly: [What to review]
- Monthly: [What to assess]

### Example Action Plan

**Issue**: Declining approval rate (71% vs 80% target)

**Metrics Affected**:
- Approval Rate: 71% (Target: 80%)
- Average Iterations: 2.5 (Target: 2.0)
- Escalation Rate: 6% (Target: 5%)

**Root Cause**: Regex generation producing overly broad patterns, leading to false positives and rejections

**Proposed Actions**:
1. Update regex generation algorithm to use word boundaries - Engineering Team - 1 week
2. Add negative lookahead patterns for common false positives - Engineering Team - 1 week
3. Improve pattern validation to catch broad patterns - Engineering Team - 2 weeks
4. Update agent instructions with examples of good/bad patterns - Operations Team - 3 days

**Success Criteria**:
- Approval rate improves to 75% by end of week 1
- Approval rate improves to 80% by end of week 3
- Average iterations decreases to 2.2 by end of week 2
- Escalation rate decreases to 5% by end of week 3

**Monitoring Plan**:
- Daily: Track approval rate and regex-related feedback
- Weekly: Review improvement trends and adjust actions
- Monthly: Assess overall impact and document lessons learned

### Continuous Improvement Cycle

**1. Measure**:
- Collect metrics daily
- Generate reports weekly/monthly
- Identify trends and patterns

**2. Analyze**:
- Interpret metrics and reports
- Identify root causes
- Prioritize issues

**3. Plan**:
- Define improvement actions
- Set targets and timelines
- Assign owners

**4. Execute**:
- Implement improvements
- Monitor progress
- Adjust as needed

**5. Review**:
- Assess results
- Document lessons learned
- Update procedures

**6. Repeat**:
- Continue cycle
- Build on successes
- Address new issues

## Additional Resources

- [Feedback Processing Runbook](FEEDBACK_PROCESSING_RUNBOOK.md)
- [Escalation Procedures Runbook](ESCALATION_PROCEDURES_RUNBOOK.md)
- [Production Monitoring Setup](../PRODUCTION_MONITORING_SETUP.md)
- [Learning Analytics Agent](../../agents/learning_analytics/README.md)
- [Agent Deployment Guide](../AGENT_DEPLOYMENT_GUIDE.md)
