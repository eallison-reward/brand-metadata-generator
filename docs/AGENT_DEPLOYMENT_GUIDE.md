# Agent Deployment Guide

This guide provides step-by-step instructions for deploying all agents to AWS Bedrock AgentCore.

## Prerequisites

1. **AWS Account**: Access to AWS account with Bedrock permissions
2. **AWS CLI**: Configured with appropriate credentials
3. **Python 3.12+**: Installed on your system
4. **Terraform**: Infrastructure deployed (IAM roles, S3, Athena, DynamoDB)
5. **boto3**: AWS SDK for Python (`pip install boto3`)

## Pre-Deployment Checklist

- [ ] Terraform infrastructure deployed to target environment
- [ ] Agent execution IAM role created
- [ ] S3 bucket created (brand-generator-rwrd-023-eu-west-1)
- [ ] Athena database created (brand_metadata_generator_db)
- [ ] DynamoDB tables created for agent memory
- [ ] AWS credentials configured for eu-west-1 region

## Deployment Steps

### Step 1: Get Agent Execution Role ARN

From your Terraform deployment:

```bash
cd infrastructure/environments/dev
terraform output agent_execution_role_arn
```

Save this ARN - you'll need it for deployment.

### Step 2: Deploy All Agents

From the project root:

```bash
cd infrastructure
python deploy_agents.py \
  --env dev \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/brand_metagen_agent_execution_dev
```

This will deploy all 7 agents:
1. orchestrator
2. data_transformation
3. evaluator
4. metadata_production
5. commercial_assessment
6. confirmation
7. tiebreaker

### Step 3: Deploy Single Agent (Optional)

To deploy or update a specific agent:

```bash
python deploy_agents.py \
  --env dev \
  --agent orchestrator \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/brand_metagen_agent_execution_dev
```

### Step 4: Dry Run (Recommended First)

Test deployment without making changes:

```bash
python deploy_agents.py \
  --env dev \
  --dry-run \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/brand_metagen_agent_execution_dev
```

## Verification

### 1. Verify Agent Creation in AWS Console

1. Navigate to AWS Bedrock console
2. Go to "Agents" section
3. Verify all 7 agents are listed with status "PREPARED"
4. Check agent names follow pattern: `brand_metagen_{agent_name}_dev`

### 2. Verify Agent Aliases

Each agent should have an alias matching the environment name (e.g., "dev").

### 3. Test Agent Invocation

Test the orchestrator agent:

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id AGENT_ID \
  --agent-alias-id ALIAS_ID \
  --session-id test-session-123 \
  --input-text '{"action": "test"}' \
  --region eu-west-1
```

## Agent Configuration

### Agent Names

All agents follow the naming convention:
```
brand_metagen_{agent_name}_{environment}
```

Examples:
- `brand_metagen_orchestrator_dev`
- `brand_metagen_evaluator_dev`
- `brand_metagen_metadata_production_dev`

### Models

All agents use:
```
anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Timeouts

- **orchestrator**: 600 seconds (10 minutes)
- **data_transformation**: 900 seconds (15 minutes)
- **evaluator**: 300 seconds (5 minutes)
- **metadata_production**: 300 seconds (5 minutes)
- **commercial_assessment**: 180 seconds (3 minutes)
- **confirmation**: 300 seconds (5 minutes)
- **tiebreaker**: 180 seconds (3 minutes)

### Memory Configuration

All agents use DynamoDB for memory with:
- TTL: 30 days
- Table pattern: `brand_metagen_agent_memory_{agent_name}_{environment}`

## Troubleshooting

### Issue: "Agent already exists"

The deployment script handles this automatically by updating the existing agent. No action needed.

### Issue: "Permission denied"

Verify:
1. AWS credentials are configured correctly
2. IAM user/role has Bedrock permissions
3. Agent execution role ARN is correct

Required permissions:
- `bedrock:CreateAgent`
- `bedrock:UpdateAgent`
- `bedrock:PrepareAgent`
- `bedrock:CreateAgentAlias`
- `bedrock:UpdateAgentAlias`
- `bedrock:ListAgents`
- `bedrock:ListAgentAliases`
- `iam:PassRole` (for agent execution role)

### Issue: "Agent preparation failed"

Check:
1. Agent execution role has correct permissions
2. Agent execution role trust policy allows bedrock.amazonaws.com
3. CloudWatch Logs for detailed error messages

### Issue: "Instructions file not found"

Ensure all instruction files exist in `infrastructure/prompts/`:
- `orchestrator_instructions.md`
- `data_transformation_instructions.md`
- `evaluator_instructions.md`
- `metadata_production_instructions.md`
- `commercial_assessment_instructions.md`
- `confirmation_instructions.md`
- `tiebreaker_instructions.md`

## Post-Deployment

### 1. Update Lambda Environment Variables

Update the orchestrator invocation Lambda with agent IDs:

```bash
aws lambda update-function-configuration \
  --function-name brand_metagen_orchestrator_invoke_dev \
  --environment Variables="{
    ORCHESTRATOR_AGENT_ID=AGENT_ID,
    ORCHESTRATOR_AGENT_ALIAS_ID=ALIAS_ID
  }" \
  --region eu-west-1
```

### 2. Test End-to-End Workflow

Invoke the Step Functions workflow:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-west-1:ACCOUNT_ID:stateMachine:brand_metagen_workflow_dev \
  --input '{"config": {"max_iterations": 5}}' \
  --region eu-west-1
```

### 3. Monitor CloudWatch Logs

Check logs for each agent:
```
/aws/bedrock/agentcore/brand_metagen_{agent_name}_dev
```

## Updating Agents

To update an agent after code changes:

1. Update the agent code in `agents/{agent_name}/`
2. Update instructions in `infrastructure/prompts/{agent_name}_instructions.md`
3. Run deployment script:

```bash
python deploy_agents.py \
  --env dev \
  --agent {agent_name} \
  --role-arn ARN
```

The script will automatically update the existing agent.

## Deployment to Other Environments

### Staging

```bash
python deploy_agents.py \
  --env staging \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/brand_metagen_agent_execution_staging
```

### Production

```bash
python deploy_agents.py \
  --env prod \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/brand_metagen_agent_execution_prod
```

## Rollback

If deployment fails or causes issues:

1. Identify the previous working agent version
2. Redeploy using the previous code/instructions
3. Or delete the agent and redeploy:

```bash
aws bedrock-agent delete-agent \
  --agent-id AGENT_ID \
  --region eu-west-1
```

Then redeploy using the deployment script.

## Best Practices

1. **Always test in dev first**: Never deploy directly to production
2. **Use dry-run**: Test deployment script with `--dry-run` flag
3. **Deploy one agent at a time**: For critical updates, deploy incrementally
4. **Monitor logs**: Watch CloudWatch Logs during and after deployment
5. **Version control**: Tag releases in Git before production deployment
6. **Backup**: Keep previous working versions of agent code
7. **Test thoroughly**: Run integration tests after deployment

## Support

For deployment issues:
1. Check CloudWatch Logs for detailed error messages
2. Verify IAM permissions
3. Ensure Terraform infrastructure is deployed correctly
4. Review agent code for syntax errors
5. Consult AWS Bedrock documentation

## Next Steps

After successful deployment:
1. Run integration tests (Task 13)
2. Set up monitoring dashboards
3. Configure CloudWatch alarms
4. Document agent IDs and aliases
5. Update runbooks with deployment details
