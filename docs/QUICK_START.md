# Quick Start Guide

Get the Brand Metadata Generator up and running in 30 minutes.

## Prerequisites

- AWS account with Bedrock access in eu-west-1
- Python 3.9+
- Terraform 1.0+
- Git

## Step 1: Clone and Setup (5 minutes)

```bash
# Clone repository
git clone <your-repo-url>
cd brand-metadata-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure AWS (5 minutes)

```bash
# Configure AWS CLI
aws configure
# Enter your credentials
# Set region to: eu-west-1

# Verify access
aws sts get-caller-identity
aws bedrock list-foundation-models --region eu-west-1
```

## Step 3: Deploy Infrastructure (10 minutes)

```bash
# Navigate to dev environment
cd infrastructure/environments/dev

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply infrastructure
terraform apply
# Type 'yes' when prompted
```

This creates:
- S3 bucket: brand-generator-rwrd-023-eu-west-1
- Athena database: brand_metadata_generator_db
- Glue tables for brand, brand_to_check, combo, mcc
- IAM roles and policies
- DynamoDB tables for agent memory

## Step 4: Deploy Agents (10 minutes)

```bash
# Return to project root
cd ../../..

# Deploy all agents to dev
python infrastructure/deploy_agents.py --env dev
```

This deploys all 7 agents:
- orchestrator-agent-dev
- data_transformation-agent-dev
- evaluator-agent-dev
- metadata_production-agent-dev
- commercial_assessment-agent-dev
- confirmation-agent-dev
- tiebreaker-agent-dev

## Step 5: Load Test Data (Optional)

```bash
# Upload sample data to S3
aws s3 cp tests/fixtures/sample_brands.csv \
  s3://brand-generator-rwrd-023-eu-west-1/test-data/

# Create Athena tables from sample data
aws athena start-query-execution \
  --query-string "$(cat tests/fixtures/create_tables.sql)" \
  --result-configuration OutputLocation=s3://brand-generator-rwrd-023-eu-west-1/query-results/
```

## Step 6: Test the System

### Test Individual Agent

```bash
# Test orchestrator agent
agentcore invoke --alias dev \
  --agent-name orchestrator-agent-dev \
  '{"prompt": "Initialize workflow"}'
```

### Run Unit Tests

```bash
pytest tests/unit -v
```

### Run Integration Test

```bash
pytest tests/integration/test_workflow.py -v
```

## Step 7: Run Full Workflow

```bash
# Start Step Functions execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-west-1:ACCOUNT_ID:stateMachine:brand-metadata-generator-dev \
  --input '{
    "action": "start_workflow",
    "config": {
      "max_iterations": 5,
      "confidence_threshold": 0.75
    }
  }'

# Monitor execution
aws stepfunctions describe-execution \
  --execution-arn <execution-arn-from-above>
```

## Verify Results

```bash
# Check S3 for generated metadata
aws s3 ls s3://brand-generator-rwrd-023-eu-west-1/metadata/

# Download a sample result
aws s3 cp s3://brand-generator-rwrd-023-eu-west-1/metadata/brand_123.json .
cat brand_123.json
```

## Troubleshooting

### Agent Not Found

```bash
# List deployed agents
agentcore list

# Check specific agent
agentcore describe --agent-name orchestrator-agent-dev
```

### Permission Errors

```bash
# Verify IAM role
aws iam get-role --role-name AgentCoreExecutionRole

# Check attached policies
aws iam list-attached-role-policies --role-name AgentCoreExecutionRole
```

### Terraform Errors

```bash
# Check Terraform state
cd infrastructure/environments/dev
terraform show

# Refresh state
terraform refresh
```

## Next Steps

- Review [Architecture Documentation](../design.md)
- Explore [Agent Implementation Guide](deployment/agent_implementation.md)
- Set up [Monitoring Dashboard](deployment/monitoring_setup.md)
- Deploy to [Production](deployment/production_deployment.md)

## Clean Up (Optional)

To remove all resources:

```bash
# Destroy agents
for agent in orchestrator data_transformation evaluator metadata_production commercial_assessment confirmation tiebreaker; do
  agentcore delete --agent-name ${agent}-agent-dev
done

# Destroy infrastructure
cd infrastructure/environments/dev
terraform destroy
```

## Support

- Check [Troubleshooting Guide](deployment/troubleshooting.md)
- Review [FAQ](deployment/faq.md)
- Open an issue on GitHub
