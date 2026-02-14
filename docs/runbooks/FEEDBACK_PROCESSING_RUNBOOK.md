# Feedback Processing Runbook

This runbook provides operational procedures for managing the human-in-the-loop feedback processing workflow in the Brand Metadata Generator system.

## Overview

The feedback processing workflow allows human reviewers to provide feedback on brand metadata quality, triggering automatic regeneration and re-classification. This runbook covers normal operations, troubleshooting, and escalation procedures.

## Table of Contents

1. [Normal Operations](#normal-operations)
2. [Monitoring Feedback Processing](#monitoring-feedback-processing)
3. [Common Issues and Resolutions](#common-issues-and-resolutions)
4. [Escalation Procedures](#escalation-procedures)
5. [Performance Optimization](#performance-optimization)

## Normal Operations

### Daily Feedback Review Workflow

**Frequency**: Daily (or as needed based on alert volume)

**Steps**:

1. **Access Quick Suite Dashboard**
   - Navigate to AWS Bedrock Console
   - Select AgentCore → Quick Suite
   - Open Brand Metadata Generator dashboard

2. **Review Pending Brands**
   - Check "Brands Awaiting Review" queue
   - Prioritize by:
     - High-volume brands (many combos)
     - Low confidence scores (<0.7)
     - Brands with previous feedback iterations

3. **Review Brand Metadata**
   - Examine generated regex pattern
   - Review MCCID list
   - Check sample matched narratives
   - Verify excluded narratives
   - Review confidence score

4. **Provide Feedback**
   - **If metadata is correct**: Click "Approve"
   - **If metadata needs improvement**: Click "Reject" and provide detailed feedback
   - **If uncertain**: Click "Flag for Manual Review"

5. **Monitor Regeneration**
   - Track feedback processing status
   - Verify metadata regeneration completes
   - Review updated metadata when ready

### Feedback Best Practices

**Effective Feedback Examples**:

```
Good: "Regex is too broad - matches both 'Starbucks Coffee' and 'Starburst Candy'. 
Add word boundary after 'Starbucks' or use negative lookahead for 'burst'."

Good: "MCCID 5812 (Eating Places) should be excluded - all combos with this MCCID 
are actually 'Star Burger' not 'Starbucks'."

Good: "Combo 12345, 12346, 12347 are misclassified - these are 'Star Market' 
grocery stores, not Starbucks."
```

**Ineffective Feedback Examples**:

```
Bad: "This is wrong"
Bad: "Fix the regex"
Bad: "Too many false positives"
```

**Feedback Guidelines**:
- Be specific about what's wrong
- Provide examples (combo IDs, narratives)
- Suggest corrections when possible
- Reference specific patterns or MCCIDs
- Explain why something is incorrect

### Iteration Management

**Iteration Limits**:
- Maximum 10 feedback iterations per brand
- After 10 iterations, brand is escalated for manual review

**Monitoring Iterations**:
- Check iteration count in Quick Suite dashboard
- Brands approaching limit (8-9 iterations) require priority attention
- High iteration counts indicate systematic issues

**When to Stop Iterating**:
- Metadata is "good enough" (not perfect)
- Diminishing returns on improvements
- Approaching iteration limit
- Systematic data quality issues identified

## Monitoring Feedback Processing

### Key Metrics to Monitor

**CloudWatch Dashboard**: `brand-metagen-prod`

1. **Feedback Processing Rate**
   - Metric: `FeedbackProcessingInvocations`
   - Normal: 5-20 per day
   - Alert: >50 per day (indicates quality issues)

2. **Iteration Counts**
   - Metric: `AverageIterationsPerBrand`
   - Normal: 1-3 iterations
   - Alert: >5 iterations (indicates difficult brands)

3. **Escalation Rate**
   - Metric: `BrandsEscalated`
   - Normal: <5% of brands
   - Alert: >10% of brands (systematic issues)

4. **Feedback Processing Duration**
   - Metric: `FeedbackProcessingDuration`
   - Normal: 2-5 minutes
   - Alert: >10 minutes (performance issues)

### CloudWatch Logs

**Feedback Processing Agent Logs**:
```
Log Group: /aws/bedrock/agentcore/brand-metagen-feedback-processing-prod
```

**Useful Log Queries**:

```
# Find recent feedback processing
fields @timestamp, @message
| filter @message like /Feedback processed/
| sort @timestamp desc
| limit 20

# Find feedback parsing errors
fields @timestamp, @message
| filter @message like /ERROR/ and @message like /parse/
| sort @timestamp desc
| limit 50

# Find high iteration brands
fields @timestamp, @message
| filter @message like /iteration/
| parse @message /iteration (?<iter>\d+)/
| filter iter > 5
| sort @timestamp desc
```

### Quick Suite API Monitoring

**API Gateway Metrics**:
- Endpoint: Check CloudWatch → API Gateway → brand-metagen-quick-suite-prod
- Monitor: Request count, latency, 4xx/5xx errors

**Lambda Function Metrics**:
- `brand-metagen-feedback-submission-prod`: Monitor invocations, errors, duration
- `brand-metagen-feedback-retrieval-prod`: Monitor invocations, errors
- `brand-metagen-status-updates-prod`: Monitor invocations, errors

## Common Issues and Resolutions

### Issue 1: Feedback Not Being Processed

**Symptoms**:
- Feedback submitted but status remains "Awaiting Review"
- No regeneration occurring
- Feedback Processing Agent not invoked

**Diagnosis**:
```bash
# Check Step Functions execution
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:eu-west-1:536824473420:stateMachine:brand_metagen_workflow_prod \
  --status-filter RUNNING \
  --region eu-west-1

# Check Feedback Processing Agent logs
aws logs tail /aws/bedrock/agentcore/brand-metagen-feedback-processing-prod \
  --follow \
  --region eu-west-1
```

**Resolution**:
1. Verify Step Functions workflow is running
2. Check Lambda function `feedback-submission` for errors
3. Verify Feedback Processing Agent is in PREPARED state
4. Check IAM permissions for agent invocation
5. Retry feedback submission if needed

### Issue 2: Infinite Feedback Loop

**Symptoms**:
- Same brand repeatedly returning to review
- Iteration count not incrementing
- Metadata not changing between iterations

**Diagnosis**:
```bash
# Check iteration count in DynamoDB
aws dynamodb get-item \
  --table-name brand-metagen-workflow-state-prod \
  --key '{"brandid": {"N": "12345"}}' \
  --region eu-west-1

# Check feedback history in S3
aws s3 ls s3://brand-generator-rwrd-023-eu-west-1/feedback/brandid=12345/ \
  --recursive
```

**Resolution**:
1. Verify iteration counter is incrementing in DynamoDB
2. Check feedback processing logic for bugs
3. Manually increment iteration count if stuck
4. Escalate brand if loop persists

### Issue 3: Poor Metadata Quality After Feedback

**Symptoms**:
- Metadata doesn't improve after feedback
- Same issues persist across iterations
- Feedback not being applied correctly

**Diagnosis**:
```bash
# Check feedback parsing
aws logs filter-log-events \
  --log-group-name /aws/bedrock/agentcore/brand-metagen-feedback-processing-prod \
  --filter-pattern "brandid=12345" \
  --region eu-west-1

# Check metadata production with feedback
aws logs filter-log-events \
  --log-group-name /aws/bedrock/agentcore/brand-metagen-metadata-production-prod \
  --filter-pattern "brandid=12345" \
  --region eu-west-1
```

**Resolution**:
1. Review feedback text for clarity and specificity
2. Check if Feedback Processing Agent correctly parsed feedback
3. Verify refinement prompt generation
4. Check if Metadata Production Agent received feedback context
5. Provide more specific feedback with examples
6. Consider manual metadata creation if automated approach fails

### Issue 4: High Escalation Rate

**Symptoms**:
- Many brands reaching 10 iteration limit
- Escalation alarm triggering frequently
- Low approval rate

**Diagnosis**:
```bash
# Query escalated brands
aws dynamodb scan \
  --table-name brand-metagen-workflow-state-prod \
  --filter-expression "iteration_count >= :limit" \
  --expression-attribute-values '{":limit": {"N": "10"}}' \
  --region eu-west-1

# Analyze common patterns
python scripts/analyze_escalations.py
```

**Resolution**:
1. Identify common patterns in escalated brands
2. Review data quality issues (ambiguous names, poor narratives)
3. Adjust metadata generation algorithms
4. Update agent instructions for common issues
5. Consider pre-processing data to improve quality
6. Document systematic issues for product team

### Issue 5: Slow Feedback Processing

**Symptoms**:
- Feedback processing takes >10 minutes
- Timeout errors in Lambda functions
- Users experiencing delays

**Diagnosis**:
```bash
# Check Lambda duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=brand-metagen-feedback-submission-prod \
  --start-time 2026-02-14T00:00:00Z \
  --end-time 2026-02-14T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum \
  --region eu-west-1

# Check agent invocation time
aws logs filter-log-events \
  --log-group-name /aws/bedrock/agentcore/brand-metagen-feedback-processing-prod \
  --filter-pattern "duration" \
  --region eu-west-1
```

**Resolution**:
1. Increase Lambda timeout if needed (current: 60s)
2. Optimize agent prompts to reduce token usage
3. Check for API throttling or rate limits
4. Consider async processing for large brands
5. Review agent model selection (faster models if needed)

## Escalation Procedures

### When to Escalate

**Automatic Escalation Triggers**:
- Brand reaches 10 feedback iterations
- Feedback processing fails 3 consecutive times
- Critical data quality issues identified
- System errors preventing processing

**Manual Escalation Criteria**:
- Ambiguous brand name (multiple possible brands)
- Insufficient data for classification
- Complex business rules required
- Legal or compliance concerns

### Escalation Process

**Step 1: Document the Issue**
```bash
# Create escalation record
python scripts/create_escalation.py \
  --brandid 12345 \
  --reason "Reached iteration limit" \
  --details "Brand name 'Star' matches multiple brands"
```

**Step 2: Notify Stakeholders**
- Email sent automatically via SNS topic
- Include: Brand ID, reason, iteration history, feedback summary

**Step 3: Manual Review**
- Assign to data analyst or domain expert
- Review all feedback and iterations
- Determine root cause

**Step 4: Resolution**
- Create manual metadata if needed
- Update data quality rules
- Document lessons learned
- Update agent instructions if systematic issue

**Step 5: Close Escalation**
```bash
# Mark escalation as resolved
python scripts/resolve_escalation.py \
  --brandid 12345 \
  --resolution "Manual metadata created" \
  --metadata-file manual_metadata_12345.json
```

### Escalation Tracking

**DynamoDB Table**: `brand-metagen-escalations-prod`

**Fields**:
- `brandid`: Brand identifier
- `escalation_date`: When escalated
- `reason`: Escalation reason
- `iteration_count`: Number of iterations attempted
- `feedback_history`: All feedback provided
- `status`: OPEN, IN_PROGRESS, RESOLVED
- `assigned_to`: Person handling escalation
- `resolution`: How it was resolved
- `resolution_date`: When resolved

**Reporting**:
```bash
# Generate escalation report
python scripts/escalation_report.py \
  --start-date 2026-02-01 \
  --end-date 2026-02-14 \
  --output escalation_report.pdf
```

## Performance Optimization

### Reducing Iteration Counts

**Strategies**:
1. **Improve Initial Metadata Quality**
   - Better data preparation
   - Enhanced pattern analysis
   - More sophisticated regex generation

2. **Better Feedback Parsing**
   - Train Feedback Processing Agent on examples
   - Improve natural language understanding
   - Extract specific corrections more accurately

3. **Smarter Metadata Production**
   - Learn from previous feedback
   - Apply common corrections automatically
   - Use feedback patterns across brands

4. **Pre-emptive Quality Checks**
   - Validate metadata before human review
   - Catch common issues automatically
   - Reduce obvious errors

### Reducing Escalation Rate

**Strategies**:
1. **Data Quality Improvements**
   - Clean ambiguous brand names
   - Enrich narrative data
   - Improve MCCID accuracy

2. **Agent Instruction Updates**
   - Document common issues
   - Provide more examples
   - Clarify edge cases

3. **Automated Pre-processing**
   - Identify problematic brands early
   - Apply special handling rules
   - Flag for human review proactively

4. **Feedback Quality**
   - Train reviewers on effective feedback
   - Provide feedback templates
   - Show examples of good feedback

### Monitoring Performance Trends

**Weekly Review**:
- Average iterations per brand
- Escalation rate
- Feedback processing duration
- Approval rate on first iteration

**Monthly Analysis**:
- Identify systematic issues
- Track improvement trends
- Adjust thresholds and limits
- Update agent instructions

## Additional Resources

- [Production Monitoring Setup](PRODUCTION_MONITORING_SETUP.md)
- [Escalation Procedures Runbook](ESCALATION_PROCEDURES_RUNBOOK.md)
- [Learning Analytics Interpretation Guide](LEARNING_ANALYTICS_RUNBOOK.md)
- [Quick Suite Setup Guide](QUICK_SUITE_SETUP.md)
- [Agent Deployment Guide](AGENT_DEPLOYMENT_GUIDE.md)
