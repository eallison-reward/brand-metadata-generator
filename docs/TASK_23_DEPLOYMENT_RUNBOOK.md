# Task 23: Final System Testing and Deployment - Runbook

This runbook provides step-by-step instructions for completing Task 23: Final System Testing and Deployment.

## Overview

Task 23 consists of 4 subtasks:
- **23.1**: End-to-end testing with HITL
- **23.2**: Deploy all agents to production
- **23.3**: Configure production monitoring
- **23.4**: Create operational runbooks

## Prerequisites

Before starting Task 23, ensure:
- ✅ All previous tasks (1-22) are completed
- ✅ All tests pass (unit, integration, property-based)
- ✅ AWS credentials configured for eu-west-1
- ✅ Terraform installed (1.0+)
- ✅ Python 3.12+ installed
- ✅ boto3 and required dependencies installed

## Task 23.1: End-to-End Testing with HITL

### Objective
Test the complete workflow from ingestion to approval, including multiple feedback iterations, iteration limits, and escalation.

### Steps

#### 1. Verify Development Environment

```bash
# Verify infrastructure deployment
python scripts/verify_deployment.py --env dev --verbose

# Expected output: All verifications passed
```

If any verifications fail, fix the issues before proceeding.

#### 2. Deploy Agents to Dev (if not already deployed)

```bash
# Get agent execution role ARN from Terraform
cd infrastructure/environments/dev
terraform output agent_execution_role_arn

# Deploy all agents
cd ../..
python deploy_agents.py --env dev --role-arn <ROLE_ARN>

# Expected output: All agents deployed successfully
```

#### 3. Run End-to-End Test

```bash
# Run E2E test with HITL workflow
python scripts/e2e_test_with_hitl.py --env dev

# This will:
# - Verify infrastructure
# - Verify agent deployment
# - Set up test data
# - Execute workflow
# - Simulate human review
# - Verify feedback processing
# - Verify iteration tracking
# - Validate results
```

#### 4. Monitor Test Execution

While the test is running, monitor in AWS Console:

**CloudWatch Logs:**
```bash
# Tail orchestrator logs
aws logs tail /aws/bedrock/agentcore/brand_metagen_orchestrator_dev --follow

# Tail all agent logs
aws logs tail /aws/bedrock/agentcore/brand_metagen_* --follow --filter-pattern "ERROR"
```

**Step Functions:**
1. Navigate to AWS Console → Step Functions
2. Find execution: `e2e-test-<timestamp>`
3. Monitor execution progress
4. Review execution history

**CloudWatch Dashboard:**
1. Navigate to AWS Console → CloudWatch → Dashboards
2. Open `brand-metagen-dev` dashboard
3. Monitor metrics in real-time

#### 5. Verify Test Results

The E2E test script will output a summary:

```
Test Summary
============
Total tests: 8
Passed: 8
Failed: 0

  infrastructure: ✅ PASS
  agents: ✅ PASS
  test_data: ✅ PASS
  workflow_execution: ✅ PASS
  human_review: ✅ PASS
  feedback_processing: ✅ PASS
  iteration_tracking: ✅ PASS
  result_validation: ✅ PASS

🎉 All tests passed!
```

#### 6. Manual Verification (Optional)

For additional confidence, manually verify:

**Check S3 for Generated Metadata:**
```bash
aws s3 ls s3://brand-generator-rwrd-023-eu-west-1/metadata/dev/ --recursive
```

**Check DynamoDB for Workflow State:**
```bash
aws dynamodb scan \
  --table-name brand-metagen-workflow-state-dev \
  --max-items 5
```

**Query Athena for Test Data:**
```bash
aws athena start-query-execution \
  --query-string "SELECT * FROM brand_metadata_generator_db.brand_to_check WHERE brandid = 9999" \
  --result-configuration OutputLocation=s3://brand-generator-rwrd-023-eu-west-1/query-results/ \
  --query-execution-context Database=brand_metadata_generator_db
```

#### 7. Test Multiple Feedback Iterations

```bash
# Run test with multiple iterations
python scripts/e2e_test_with_hitl.py --env dev --iterations 3

# This will simulate 3 feedback cycles
```

#### 8. Test Iteration Limit and Escalation

Manually test the iteration limit:

1. Start a workflow execution
2. Submit feedback 10 times (max limit)
3. Verify escalation occurs on 11th iteration
4. Check escalation notification in CloudWatch Logs

#### 9. Mark Task 23.1 Complete

If all tests pass:
```bash
# Update task status in tasks.md
# Mark Task 23.1 as completed
```

---

## Task 23.2: Deploy All Agents to Production

### Objective
Deploy Feedback Processing Agent, Learning Analytics Agent, and update existing agents with MCP integration to production environment.

### Pre-Deployment Checklist

Before deploying to production:

- [ ] All tests pass in dev environment
- [ ] E2E test with HITL completed successfully
- [ ] Code reviewed and approved
- [ ] Change management approval obtained
- [ ] Stakeholders notified of deployment window
- [ ] Rollback plan documented and tested
- [ ] Backup of current production state taken

### Steps

#### 1. Deploy Production Infrastructure

```bash
cd infrastructure/environments/prod

# Initialize Terraform
terraform init

# Review plan carefully
terraform plan -out=tfplan

# Review the plan output thoroughly
# Verify:
# - S3 bucket: brand-generator-rwrd-023-eu-west-1
# - Athena database: brand_metadata_generator_db
# - Region: eu-west-1
# - All resource names include 'prod' suffix

# Apply infrastructure
terraform apply tfplan
```

Expected duration: 10-15 minutes

#### 2. Verify Production Infrastructure

```bash
# Run verification script
python scripts/verify_deployment.py --env prod --verbose

# All checks should pass
```

#### 3. Deploy Agents to Production

```bash
# Get agent execution role ARN
cd infrastructure/environments/prod
terraform output agent_execution_role_arn

# Deploy all agents
cd ../..
python deploy_agents.py --env prod --role-arn <ROLE_ARN>

# Expected output: All 9 agents deployed successfully
```

Agents deployed:
1. orchestrator
2. data_transformation
3. evaluator
4. metadata_production
5. commercial_assessment
6. confirmation
7. tiebreaker
8. feedback_processing (NEW)
9. learning_analytics (NEW)

#### 4. Verify Agent Deployment

```bash
# List all production agents
aws bedrock-agent list-agents --region eu-west-1 \
  --query "agentSummaries[?contains(agentName, 'prod')]"

# Verify each agent status is 'PREPARED'
```

#### 5. Test Agent Invocation

Test each agent individually:

```bash
# Test orchestrator
aws bedrock-agent-runtime invoke-agent \
  --agent-id <AGENT_ID> \
  --agent-alias-id <ALIAS_ID> \
  --session-id test-prod-$(date +%s) \
  --input-text '{"action": "test"}' \
  --region eu-west-1

# Repeat for other agents
```

#### 6. Deploy Lambda Functions

Lambda functions are deployed via Terraform, but verify:

```bash
# List Lambda functions
aws lambda list-functions --region eu-west-1 \
  --query "Functions[?contains(FunctionName, 'brand-metagen-prod')]"

# Test Lambda invocation
aws lambda invoke \
  --function-name brand-metagen-workflow-init-prod \
  --payload '{"test": true}' \
  --region eu-west-1 \
  response.json

cat response.json
```

#### 7. Update Step Functions State Machine

The state machine is deployed via Terraform, but verify:

```bash
# Describe state machine
aws stepfunctions describe-state-machine \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --region eu-west-1

# Verify definition includes all new phases:
# - WaitForFeedback
# - FeedbackProcessing
# - MetadataRegeneration
# - IterationCheck
# - Escalation
```

#### 8. Load Production Data

```bash
# Upload production data to S3
aws s3 sync data/production/ s3://brand-generator-rwrd-023-eu-west-1/input/

# Verify data upload
aws s3 ls s3://brand-generator-rwrd-023-eu-west-1/input/ --recursive

# Create Athena tables (if not already created)
# Run SQL scripts in infrastructure/sql/
```

#### 9. Run Smoke Test

```bash
# Start a small test execution
aws stepfunctions start-execution \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --name smoke-test-$(date +%s) \
  --input '{
    "action": "start_workflow",
    "config": {
      "max_iterations": 3,
      "batch_size": 10
    }
  }' \
  --region eu-west-1

# Monitor execution
aws stepfunctions describe-execution \
  --execution-arn <EXECUTION_ARN> \
  --region eu-west-1
```

#### 10. Mark Task 23.2 Complete

If deployment successful:
```bash
# Update task status in tasks.md
# Mark Task 23.2 as completed
```

---

## Task 23.3: Configure Production Monitoring

### Objective
Set up CloudWatch alarms, SNS notifications, and production dashboard.

### Steps

#### 1. Create SNS Topic for Alarms

```bash
# Create SNS topic
aws sns create-topic \
  --name brand-metagen-alarms-prod \
  --region eu-west-1

# Subscribe email addresses
aws sns subscribe \
  --topic-arn arn:aws:sns:eu-west-1:<ACCOUNT_ID>:brand-metagen-alarms-prod \
  --protocol email \
  --notification-endpoint ops-team@example.com \
  --region eu-west-1

# Confirm subscription via email
```

#### 2. Configure CloudWatch Alarms

Alarms are created via Terraform, but verify:

```bash
# List alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix brand-metagen-prod \
  --region eu-west-1

# Expected alarms:
# - WorkflowExecutionFailures
# - AgentInvocationErrors
# - HighErrorRate
# - LongRunningExecutions
# - FeedbackQueueBacklog
```

#### 3. Update Alarm Actions

```bash
# Update each alarm to send to SNS topic
aws cloudwatch put-metric-alarm \
  --alarm-name brand-metagen-prod-workflow-failures \
  --alarm-actions arn:aws:sns:eu-west-1:<ACCOUNT_ID>:brand-metagen-alarms-prod \
  --region eu-west-1

# Repeat for all alarms
```

#### 4. Configure CloudWatch Dashboard

```bash
# Verify dashboard exists
aws cloudwatch get-dashboard \
  --dashboard-name brand-metagen-prod \
  --region eu-west-1

# Dashboard should include:
# - Workflow execution metrics
# - Agent invocation counts
# - Error rates
# - Feedback processing metrics
# - Iteration counts
# - Escalation counts
```

#### 5. Set Up Log Insights Queries

Create saved queries in CloudWatch Logs Insights:

**Query 1: Agent Errors**
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

**Query 2: Workflow Executions**
```
fields @timestamp, executionArn, status
| filter @message like /Execution/
| stats count() by status
```

**Query 3: Feedback Processing**
```
fields @timestamp, brandid, feedback_type
| filter @message like /Feedback/
| stats count() by feedback_type
```

#### 6. Configure Quick Suite Dashboard

Follow [Quick Suite Setup Guide](QUICK_SUITE_SETUP.md) for production:

1. Navigate to AWS Bedrock Console
2. Configure Quick Suite for production agents
3. Set up brand review interface
4. Configure feedback submission forms
5. Test interface with sample data

#### 7. Set Up Monitoring Runbook

Create monitoring runbook at `docs/MONITORING_RUNBOOK.md`:

- How to access dashboards
- How to interpret metrics
- How to respond to alarms
- Escalation procedures
- Contact information

#### 8. Test Alarm Notifications

```bash
# Trigger test alarm
aws cloudwatch set-alarm-state \
  --alarm-name brand-metagen-prod-workflow-failures \
  --state-value ALARM \
  --state-reason "Testing alarm notification" \
  --region eu-west-1

# Verify email notification received
```

#### 9. Mark Task 23.3 Complete

If monitoring configured:
```bash
# Update task status in tasks.md
# Mark Task 23.3 as completed
```

---

## Task 23.4: Create Operational Runbooks

### Objective
Document procedures for feedback processing, escalation, MCP troubleshooting, and learning analytics interpretation.

### Steps

#### 1. Create Feedback Processing Runbook

Create `docs/FEEDBACK_PROCESSING_RUNBOOK.md`:

**Contents:**
- How to access feedback queue
- How to review feedback submissions
- How to trigger feedback processing
- How to monitor feedback processing progress
- How to handle feedback processing failures
- Escalation procedures

#### 2. Create Escalation Runbook

Create `docs/ESCALATION_RUNBOOK.md`:

**Contents:**
- When escalation occurs (iteration limit exceeded)
- How to identify escalated brands
- How to review escalated cases
- How to manually resolve escalations
- How to update metadata manually
- How to resume workflow after escalation

#### 3. Create MCP Troubleshooting Runbook

Create `docs/MCP_TROUBLESHOOTING_RUNBOOK.md`:

**Contents:**
- MCP server connectivity issues
- Brand Registry MCP errors
- Crunchbase MCP errors
- Cache invalidation procedures
- Fallback mechanism verification
- How to test MCP connectivity

#### 4. Create Learning Analytics Runbook

Create `docs/LEARNING_ANALYTICS_RUNBOOK.md`:

**Contents:**
- How to access learning analytics reports
- How to interpret accuracy metrics
- How to identify problematic brands
- How to analyze feedback trends
- How to track system improvements
- How to generate executive summaries

#### 5. Create Incident Response Runbook

Create `docs/INCIDENT_RESPONSE_RUNBOOK.md`:

**Contents:**
- Severity levels and definitions
- Incident detection and alerting
- Initial response procedures
- Investigation steps
- Resolution procedures
- Post-incident review process

#### 6. Create Maintenance Runbook

Create `docs/MAINTENANCE_RUNBOOK.md`:

**Contents:**
- Regular maintenance tasks
- Database cleanup procedures
- Log retention policies
- Backup and restore procedures
- Agent redeployment procedures
- Infrastructure updates

#### 7. Update Main Documentation

Update `README.md` and `docs/DEPLOYMENT_GUIDE.md` with:
- Links to all runbooks
- Production deployment notes
- Monitoring setup instructions
- Operational procedures

#### 8. Review and Approve Runbooks

- [ ] Technical review by development team
- [ ] Operations review by ops team
- [ ] Security review
- [ ] Management approval

#### 9. Mark Task 23.4 Complete

If all runbooks created and approved:
```bash
# Update task status in tasks.md
# Mark Task 23.4 as completed
```

---

## Task 23: Final Verification

After completing all subtasks (23.1-23.4):

### Final Checklist

- [ ] Task 23.1: E2E test with HITL passed
- [ ] Task 23.2: All agents deployed to production
- [ ] Task 23.3: Production monitoring configured
- [ ] Task 23.4: All operational runbooks created

### Production Readiness Verification

```bash
# Run full verification
python scripts/verify_deployment.py --env prod --verbose

# Run production smoke test
python scripts/e2e_test_with_hitl.py --env prod --skip-deploy

# Verify monitoring
# - Check CloudWatch dashboard
# - Verify alarms are active
# - Test SNS notifications

# Verify documentation
# - All runbooks created
# - README updated
# - Deployment guide updated
```

### Mark Task 23 Complete

If all subtasks complete and verification passes:
```bash
# Update task status in tasks.md
# Mark Task 23 as completed
```

---

## Rollback Procedures

If issues occur during deployment:

### Rollback Infrastructure

```bash
cd infrastructure/environments/prod

# Destroy specific resources
terraform destroy -target=module.step_functions

# Or full rollback
terraform destroy
```

### Rollback Agents

```bash
# Delete all production agents
for agent in orchestrator data_transformation evaluator metadata_production commercial_assessment confirmation tiebreaker feedback_processing learning_analytics; do
  aws bedrock-agent delete-agent \
    --agent-id <AGENT_ID> \
    --region eu-west-1
done
```

### Restore from Backup

```bash
# Restore DynamoDB tables
aws dynamodb restore-table-from-backup \
  --target-table-name brand-metagen-workflow-state-prod \
  --backup-arn <BACKUP_ARN> \
  --region eu-west-1

# Restore S3 data
aws s3 sync s3://brand-generator-rwrd-023-eu-west-1-backup/ \
  s3://brand-generator-rwrd-023-eu-west-1/
```

---

## Support and Escalation

For issues during Task 23:

1. Check CloudWatch Logs for errors
2. Review relevant runbook
3. Consult deployment guide
4. Contact DevOps team
5. Escalate to management if critical

## Success Criteria

Task 23 is complete when:
- ✅ E2E test with HITL passes in dev
- ✅ All agents deployed to production
- ✅ Production monitoring configured and tested
- ✅ All operational runbooks created and approved
- ✅ Production smoke test passes
- ✅ Stakeholders notified of successful deployment

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-14  
**Owner:** Development Team
