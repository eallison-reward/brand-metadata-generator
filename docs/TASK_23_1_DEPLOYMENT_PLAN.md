# Task 23.1: End-to-End Testing with HITL - Deployment Plan

## Current Status

Based on verification (2026-02-14):

### ✅ Already Deployed
- S3 bucket: `brand-generator-rwrd-023-eu-west-1` (eu-west-1)
- Athena database: `brand_metadata_generator_db`
- Athena tables: brand, brand_to_check, combo, mcc

### ❌ Needs Deployment
- DynamoDB tables (agent memory)
- IAM roles (agent execution, Step Functions execution)
- Lambda functions (7 functions)
- Step Functions state machine
- Bedrock AgentCore agents (9 agents using Strands API)
- CloudWatch dashboards and alarms

## Deployment Steps

### Step 1: Deploy Infrastructure with Terraform

```bash
# Navigate to dev environment
cd infrastructure/environments/dev

# Review what will be created
terraform plan

# Apply infrastructure
terraform apply

# Expected resources:
# - 9 DynamoDB tables (agent memory)
# - 2 IAM roles (agent execution, Step Functions)
# - 7 Lambda functions
# - 1 Step Functions state machine
# - CloudWatch log groups
# - CloudWatch dashboard
# - CloudWatch alarms
```

**Duration:** 10-15 minutes

### Step 2: Deploy Strands API Agents to Bedrock AgentCore

The agents are built using the Strands API and need to be deployed to AWS Bedrock AgentCore runtime.

```bash
# Get agent execution role ARN from Terraform
cd infrastructure/environments/dev
terraform output agent_execution_role_arn

# Deploy all 9 agents
cd ../../..
python infrastructure/deploy_agents.py --env dev --role-arn <ROLE_ARN>
```

**Agents to deploy:**
1. orchestrator - Coordinates workflow
2. data_transformation - Data ingestion and validation
3. evaluator - Quality assessment
4. metadata_production - Regex and MCCID generation
5. commercial_assessment - Brand validation via MCP
6. confirmation - False positive detection
7. tiebreaker - Multi-match resolution
8. feedback_processing - Human feedback processing
9. learning_analytics - Trend analysis and metrics

**Duration:** 15-20 minutes (agents need to be prepared)

### Step 3: Verify Deployment

```bash
# Run verification script
python scripts/verify_deployment.py --env dev --verbose

# Expected: All checks pass (27/27)
```

### Step 4: Run End-to-End Test

```bash
# Run E2E test with HITL workflow
python scripts/e2e_test_with_hitl.py --env dev

# This will:
# 1. Verify infrastructure ✅
# 2. Verify agents ✅
# 3. Set up test data ✅
# 4. Execute workflow ✅
# 5. Simulate human review ✅
# 6. Verify feedback processing ✅
# 7. Verify iteration tracking ✅
# 8. Validate results ✅
```

**Duration:** 20-30 minutes

### Step 5: Manual Testing

After automated tests pass, manually test:

1. **Submit real feedback via Quick Suite interface**
2. **Test multiple feedback iterations (3-5 cycles)**
3. **Test iteration limit (10 iterations)**
4. **Verify escalation occurs on 11th iteration**
5. **Test tie resolution workflow**
6. **Test confirmation workflow**

### Step 6: Mark Task Complete

If all tests pass:
- Update `.kiro/specs/brand-metadata-generator/tasks.md`
- Mark Task 23.1 as completed

## Important Notes

### Strands API Agents on Bedrock AgentCore

The agents are implemented using the **Strands API** framework and deployed to **AWS Bedrock AgentCore runtime**. This means:

- Each agent has a handler function in `agents/{agent_name}/agentcore_handler.py`
- Agents use Strands decorators (`@agent`, `@tool`)
- Agents are deployed using the `deploy_agents.py` script
- Agents run on AWS Bedrock infrastructure
- Agents use Claude 3.5 Sonnet model
- Agents have DynamoDB memory for conversation state

### Agent Handler Structure

Each agent follows this pattern:

```python
from strands import Agent

# Create agent
agent = Agent(
    name="agent_name",
    instructions="Agent instructions...",
    model="anthropic.claude-3-5-sonnet-20241022-v2:0"
)

# Register tools
@agent.tool
def tool_name(param: str) -> dict:
    """Tool description."""
    # Tool implementation
    return result

# Handler for AgentCore
def handler(event, context):
    """AgentCore handler function."""
    return agent.handle_agentcore_event(event, context)
```

### Deployment Script

The `infrastructure/deploy_agents.py` script:
- Uses boto3 to interact with Bedrock Agent API
- Creates or updates agents
- Prepares agents (compiles and validates)
- Creates agent aliases
- Configures agent memory (DynamoDB)
- Sets timeouts and model configuration

### Testing Approach

The E2E test (`scripts/e2e_test_with_hitl.py`):
- Creates test brand data
- Starts Step Functions workflow
- Monitors execution progress
- Simulates human feedback submission
- Verifies feedback processing
- Validates iteration tracking
- Checks final metadata generation

## Troubleshooting

### Issue: Terraform Apply Fails

**Solution:**
- Check AWS credentials: `aws sts get-caller-identity`
- Verify region is eu-west-1: `aws configure get region`
- Check IAM permissions for Terraform user
- Review Terraform error messages

### Issue: Agent Deployment Fails

**Solution:**
- Verify IAM role exists: `terraform output agent_execution_role_arn`
- Check Bedrock service is available in eu-west-1
- Verify agent handler code has no syntax errors
- Check CloudWatch Logs for detailed errors

### Issue: E2E Test Fails

**Solution:**
- Check Step Functions execution in AWS Console
- Review CloudWatch Logs for agent errors
- Verify test data was uploaded to S3
- Check DynamoDB tables for workflow state

### Issue: Agents Not Responding

**Solution:**
- Verify agent status: `aws bedrock-agent list-agents`
- Check agent is in 'PREPARED' status
- Review agent CloudWatch Logs
- Test agent invocation directly

## Cost Considerations

Running Task 23.1 will incur AWS costs:

- **Bedrock AgentCore:** ~$0.03 per 1K input tokens, ~$0.015 per 1K output tokens
- **DynamoDB:** On-demand pricing, minimal for testing
- **Lambda:** Free tier covers testing
- **Step Functions:** $0.025 per 1K state transitions
- **S3:** Minimal storage costs
- **CloudWatch:** Free tier covers testing

**Estimated cost for E2E test:** $5-10

## Timeline

- **Step 1 (Terraform):** 15 minutes
- **Step 2 (Agent deployment):** 20 minutes
- **Step 3 (Verification):** 5 minutes
- **Step 4 (E2E test):** 30 minutes
- **Step 5 (Manual testing):** 60 minutes

**Total:** ~2 hours

## Success Criteria

Task 23.1 is complete when:
- ✅ All infrastructure deployed via Terraform
- ✅ All 9 agents deployed to Bedrock AgentCore
- ✅ Verification script passes (27/27 checks)
- ✅ E2E test passes (8/8 tests)
- ✅ Manual testing confirms HITL workflow works
- ✅ Multiple feedback iterations tested
- ✅ Iteration limit and escalation tested
- ✅ All agents working together correctly

## Next Steps

After Task 23.1 completes:
- **Task 23.2:** Deploy to production
- **Task 23.3:** Configure production monitoring
- **Task 23.4:** Create operational runbooks

---

**Ready to proceed?** Run the deployment steps above to complete Task 23.1.
