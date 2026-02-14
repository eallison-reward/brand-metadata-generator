# Production Monitoring Setup

This document describes the production monitoring configuration for the Brand Metadata Generator system.

## Overview

Production monitoring is fully configured with CloudWatch alarms, SNS notifications, and a comprehensive dashboard. All monitoring resources were deployed via Terraform to the `prod` environment.

## CloudWatch Dashboard

**Dashboard Name**: `brand-metagen-prod`

**Dashboard ARN**: `arn:aws:cloudwatch::536824473420:dashboard/brand-metagen-prod`

**Access URL**: https://eu-west-1.console.aws.amazon.com/cloudwatch/home?region=eu-west-1#dashboards:name=brand-metagen-prod

### Dashboard Widgets

The dashboard includes the following visualizations:

1. **Step Functions Workflow Metrics**
   - Workflow executions started
   - Workflow executions succeeded
   - Workflow executions failed
   - Average execution time

2. **Brand Processing Status**
   - Brands processed
   - Brands in progress
   - Brands pending
   - Brands failed

3. **Combo Matching Statistics**
   - Combos matched
   - Combos confirmed
   - Combos excluded (false positives)
   - Combos flagged for human review

4. **Tie Resolution Metrics**
   - Ties detected
   - Ties resolved
   - Ties flagged for human review

5. **Agent Invocation Counts**
   - Data Transformation invocations
   - Evaluator invocations
   - Metadata Production invocations
   - Confirmation invocations
   - Tiebreaker invocations

6. **Error Metrics**
   - Total agent errors
   - Validation errors
   - Retry attempts

7. **Recent Orchestrator Errors and Warnings**
   - Log insights query showing recent ERROR and WARN messages

8. **Recent Agent Errors (All Agents)**
   - Log insights query showing recent errors across all agents

## CloudWatch Alarms

Four production alarms are configured and actively monitoring the system:

### 1. Workflow Failures Alarm

**Alarm Name**: `brand-metagen-workflow-failures-prod`

**Metric**: `AWS/States` - `ExecutionsFailed`

**Threshold**: Greater than 0 failures in 5 minutes

**State**: OK

**Action**: Sends notification to SNS topic

**Purpose**: Alerts when any workflow execution fails

### 2. Agent Errors Alarm

**Alarm Name**: `brand-metagen-agent-errors-prod`

**Metric**: `BrandMetadataGenerator` - `AgentErrors`

**Threshold**: Greater than 10 errors in 10 minutes (2 evaluation periods of 5 minutes)

**State**: OK

**Action**: Sends notification to SNS topic

**Purpose**: Alerts when agent error rate exceeds acceptable threshold

### 3. Human Review Required Alarm

**Alarm Name**: `brand-metagen-human-review-required-prod`

**Metric**: `BrandMetadataGenerator` - `CombosFlaggedForReview`

**Threshold**: Greater than 50 combos flagged in 1 hour

**State**: OK

**Action**: Sends notification to SNS topic

**Purpose**: Alerts when many combos require human review, indicating potential systematic issues

### 4. Workflow Duration Alarm

**Alarm Name**: `brand-metagen-workflow-duration-prod`

**Metric**: `AWS/States` - `ExecutionTime`

**Threshold**: Greater than 900,000 milliseconds (15 minutes)

**State**: OK

**Action**: Sends notification to SNS topic

**Purpose**: Alerts when workflow execution time exceeds expected duration

## SNS Topic for Alerts

**Topic Name**: `brand-metadata-generator-alarms-prod`

**Topic ARN**: `arn:aws:sns:eu-west-1:536824473420:brand-metadata-generator-alarms-prod`

### Subscribing to Alerts

To receive email notifications when alarms trigger, subscribe email addresses to the SNS topic:

**Using the subscription script** (recommended):

```bash
# Edit scripts/subscribe_sns_alerts.py to add email addresses
# Then run the script
python scripts/subscribe_sns_alerts.py
```

**Using AWS CLI directly**:

```bash
# Subscribe an email address
aws sns subscribe \
  --topic-arn arn:aws:sns:eu-west-1:536824473420:brand-metadata-generator-alarms-prod \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region eu-west-1

# The email address will receive a confirmation email
# Click the confirmation link to activate the subscription
```

**Current Subscriptions**:
- `ed.allison@rewardinsight.com` - Pending confirmation (subscribed 2026-02-14)

### Managing Subscriptions

```bash
# List all subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:eu-west-1:536824473420:brand-metadata-generator-alarms-prod \
  --region eu-west-1

# Unsubscribe an email
aws sns unsubscribe \
  --subscription-arn <subscription-arn> \
  --region eu-west-1
```

## CloudWatch Log Groups

All agents and Lambda functions have dedicated log groups with 30-day retention:

### Agent Log Groups

- `/aws/bedrock/agentcore/brand-metagen-orchestrator-prod`
- `/aws/bedrock/agentcore/brand-metagen-data-transformation-prod`
- `/aws/bedrock/agentcore/brand-metagen-evaluator-prod`
- `/aws/bedrock/agentcore/brand-metagen-metadata-production-prod`
- `/aws/bedrock/agentcore/brand-metagen-commercial-assessment-prod`
- `/aws/bedrock/agentcore/brand-metagen-confirmation-prod`
- `/aws/bedrock/agentcore/brand-metagen-tiebreaker-prod`
- `/aws/bedrock/agentcore/brand-metagen-feedback-processing-prod`
- `/aws/bedrock/agentcore/brand-metagen-learning-analytics-prod`

### Lambda Function Log Groups

- `/aws/lambda/brand-metagen-workflow-init-prod`
- `/aws/lambda/brand-metagen-orchestrator-invoke-prod`
- `/aws/lambda/brand-metagen-result-aggregation-prod`

### Step Functions Log Group

- `/aws/states/brand-metagen-workflow-prod`

## Monitoring Best Practices

### Daily Monitoring Tasks

1. **Check Dashboard**: Review the CloudWatch dashboard daily for anomalies
2. **Review Alarms**: Ensure all alarms are in OK state
3. **Check Human Review Queue**: Monitor combos flagged for human review
4. **Review Error Logs**: Check recent errors in agent and Lambda logs

### Weekly Monitoring Tasks

1. **Analyze Trends**: Review weekly trends in brand processing and combo matching
2. **Review Metrics**: Analyze agent invocation patterns and error rates
3. **Capacity Planning**: Monitor execution times and resource utilization
4. **Feedback Analysis**: Review feedback processing metrics and iteration counts

### Monthly Monitoring Tasks

1. **Performance Review**: Analyze monthly performance metrics
2. **Cost Analysis**: Review CloudWatch costs and optimize log retention if needed
3. **Alarm Tuning**: Adjust alarm thresholds based on observed patterns
4. **Documentation Updates**: Update runbooks based on operational learnings

## Alarm Response Procedures

### Workflow Failures Alarm

**When triggered**: A workflow execution has failed

**Response steps**:
1. Check the Step Functions console for the failed execution
2. Review the execution history to identify the failing state
3. Check CloudWatch Logs for the failing agent or Lambda function
4. Identify the root cause (data issue, agent error, timeout, etc.)
5. Fix the issue and retry the workflow if appropriate
6. Document the incident and resolution

### Agent Errors Alarm

**When triggered**: Agent error rate exceeds 10 errors in 10 minutes

**Response steps**:
1. Check the CloudWatch dashboard for which agents are experiencing errors
2. Review agent logs for error details
3. Identify common error patterns (API limits, data validation, timeouts)
4. Check if errors are transient or systematic
5. Apply fixes (adjust retry logic, fix data issues, increase timeouts)
6. Monitor error rate to confirm resolution

### Human Review Required Alarm

**When triggered**: More than 50 combos flagged for human review in 1 hour

**Response steps**:
1. Check the Quick Suite dashboard for flagged combos
2. Identify common patterns in flagged combos
3. Determine if this indicates a systematic issue (bad metadata, data quality)
4. Review recent brand processing for problematic brands
5. Consider adjusting metadata generation or validation logic
6. Process flagged combos through human review workflow

### Workflow Duration Alarm

**When triggered**: Workflow execution time exceeds 15 minutes

**Response steps**:
1. Check the Step Functions console for slow executions
2. Identify which states are taking the most time
3. Review agent logs for performance issues
4. Check for data volume spikes or complex brands
5. Consider optimizing agent logic or increasing timeouts
6. Monitor execution times to confirm resolution

## Custom Metrics

The system publishes custom metrics to the `BrandMetadataGenerator` namespace:

### Brand Processing Metrics
- `BrandsProcessed` - Total brands successfully processed
- `BrandsInProgress` - Brands currently being processed
- `BrandsPending` - Brands waiting to be processed
- `BrandsFailed` - Brands that failed processing

### Combo Matching Metrics
- `CombosMatched` - Total combos matched to brands
- `CombosConfirmed` - Combos confirmed by Confirmation Agent
- `CombosExcluded` - Combos excluded as false positives
- `CombosFlaggedForReview` - Combos requiring human review

### Tie Resolution Metrics
- `TiesDetected` - Multi-brand matches detected
- `TiesResolved` - Ties successfully resolved
- `TiesFlaggedForReview` - Ties requiring human review

### Agent Invocation Metrics
- `DataTransformationInvocations` - Data Transformation Agent calls
- `EvaluatorInvocations` - Evaluator Agent calls
- `MetadataProductionInvocations` - Metadata Production Agent calls
- `ConfirmationInvocations` - Confirmation Agent calls
- `TiebreakerInvocations` - Tiebreaker Agent calls

### Error Metrics
- `AgentErrors` - Total agent errors
- `ValidationErrors` - Data validation errors
- `RetryAttempts` - Number of retry attempts

## Querying Logs with CloudWatch Insights

### Find Recent Errors

```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 50
```

### Find Slow Agent Invocations

```
fields @timestamp, @message, @duration
| filter @message like /Agent invocation completed/
| filter @duration > 30000
| sort @duration desc
| limit 20
```

### Count Errors by Agent

```
fields @logStream, @message
| filter @message like /ERROR/
| stats count() by @logStream
| sort count desc
```

### Find Validation Errors

```
fields @timestamp, @message
| filter @message like /validation/i and @message like /error/i
| sort @timestamp desc
| limit 50
```

## Additional Resources

- [AWS CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [AWS SNS Documentation](https://docs.aws.amazon.com/sns/)
- [CloudWatch Logs Insights Query Syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- `DEPLOYMENT_GUIDE.md` - Infrastructure deployment guide
- `AGENT_DEPLOYMENT_GUIDE.md` - Agent deployment guide
- `STEP_FUNCTIONS_WORKFLOW.md` - Workflow configuration

## Summary

Production monitoring is fully configured and operational:
- ✅ CloudWatch dashboard created and accessible
- ✅ Four CloudWatch alarms configured and monitoring
- ✅ SNS topic created for alert notifications
- ✅ Log groups configured with 30-day retention
- ✅ Custom metrics namespace configured

**Next Steps**:
1. Subscribe team email addresses to the SNS topic
2. Review alarm thresholds after initial production usage
3. Set up regular monitoring reviews (daily/weekly/monthly)
4. Document any alarm responses and resolutions
