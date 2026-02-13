# Brand Metadata Generator - Deployment Guide

This guide provides comprehensive instructions for deploying the Brand Metadata Generator system to AWS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Infrastructure Deployment](#infrastructure-deployment)
4. [Agent Deployment](#agent-deployment)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Required Tools

- **Python 3.12+**: Required for agent code and deployment scripts
- **Terraform 1.0+**: Infrastructure as Code tool
- **AWS CLI 2.x**: AWS command-line interface
- **AgentCore CLI**: Bedrock AgentCore command-line tool
- **Git**: Version control

### AWS Account Requirements

- AWS account with appropriate permissions
- Access to AWS Bedrock in eu-west-1 region
- IAM permissions for:
  - S3 (bucket creation and management)
  - Athena (database and table creation)
  - Glue (catalog management)
  - DynamoDB (table creation)
  - Lambda (function deployment)
  - Step Functions (state machine creation)
  - IAM (role and policy management)
  - CloudWatch (logs and metrics)
  - Bedrock (agent creation and invocation)

### Installation

```bash
# Install Python dependencies
pip install -e .
pip install bedrock-agentcore-starter-toolkit

# Verify installations
python --version  # Should be 3.12+
terraform --version  # Should be 1.0+
aws --version  # Should be 2.x
agentcore --version

# Configure AWS CLI
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: eu-west-1
# Default output format: json
```

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd brand-metadata-generator
```

### 2. Create Python Virtual Environment

```bash
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 3. Configure Environment Variables

Create a `.env` file for environment-specific configuration:

```bash
# .env file (DO NOT commit to Git)
AWS_REGION=eu-west-1
AWS_ACCOUNT_ID=<your-account-id>
ENVIRONMENT=dev  # or staging, prod
S3_BUCKET=brand-generator-rwrd-023-eu-west-1
ATHENA_DATABASE=brand_metadata_generator_db
```

### 4. Verify AWS Credentials

```bash
# Test AWS access
aws sts get-caller-identity

# Verify region
aws configure get region  # Should output: eu-west-1
```

## Infrastructure Deployment

### Development Environment

#### Step 1: Initialize Terraform

```bash
cd infrastructure/environments/dev
terraform init
```

This will:
- Download required Terraform providers
- Initialize the backend (if configured)
- Prepare the working directory

#### Step 2: Review Terraform Plan

```bash
terraform plan -out=tfplan
```

Review the planned changes carefully. Verify:
- S3 bucket name: `brand-generator-rwrd-023-eu-west-1`
- Athena database: `brand_metadata_generator_db`
- All resources use `brand-metagen-` prefix
- Region is `eu-west-1`

#### Step 3: Apply Infrastructure

```bash
terraform apply tfplan
```

This will create:
- S3 bucket for data storage
- Athena database and tables (brand, brand_to_check, combo, mcc)
- DynamoDB tables for agent memory
- IAM roles and policies
- Lambda functions
- Step Functions state machine
- CloudWatch log groups and dashboards
- CloudWatch alarms

Expected duration: 5-10 minutes

#### Step 4: Verify Infrastructure

```bash
# Verify S3 bucket
aws s3 ls s3://brand-generator-rwrd-023-eu-west-1/

# Verify Athena database
aws athena list-databases --catalog-name AwsDataCatalog \
  --query "DatabaseList[?Name=='brand_metadata_generator_db']"

# Verify DynamoDB tables
aws dynamodb list-tables --query "TableNames[?contains(@, 'brand-metagen')]"

# Verify Step Functions state machine
aws stepfunctions list-state-machines \
  --query "stateMachines[?contains(name, 'brand-metagen')]"
```

### Staging Environment

```bash
cd infrastructure/environments/staging
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Production Environment

```bash
cd infrastructure/environments/prod

# Initialize with backend for state management
terraform init

# Review plan carefully
terraform plan -out=tfplan

# Apply with approval
terraform apply tfplan
```

**Important**: Production deployments should:
- Use remote state backend (S3 + DynamoDB)
- Enable point-in-time recovery for DynamoDB
- Enable versioning on S3 bucket
- Configure SNS topics for alarms
- Require manual approval

## Agent Deployment

### Using Deployment Script

The easiest way to deploy all agents is using the deployment script:

```bash
cd infrastructure
python deploy_agents.py --env dev
```

This script will:
1. Deploy all 7 agents to AWS Bedrock AgentCore
2. Configure agent memory with DynamoDB
3. Set up agent instructions and tools
4. Verify agent creation

### Manual Agent Deployment

If you need to deploy agents individually:

#### Step 1: Deploy Orchestrator Agent

```bash
agentcore create \
  --agent-name brand-metagen-orchestrator-dev \
  --model anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --instructions-file infrastructure/prompts/orchestrator_instructions.md \
  --handler agents.orchestrator.agentcore_handler:handler \
  --memory-type dynamodb \
  --memory-config table_name=brand-metagen-orchestrator-memory-dev \
  --timeout 300
```

#### Step 2: Deploy Data Transformation Agent

```bash
agentcore create \
  --agent-name brand-metagen-data-transformation-dev \
  --model anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --instructions-file infrastructure/prompts/data_transformation_instructions.md \
  --handler agents.data_transformation.agentcore_handler:handler \
  --memory-type dynamodb \
  --memory-config table_name=brand-metagen-data-transformation-memory-dev \
  --timeout 300
```

#### Step 3: Deploy Remaining Agents

Repeat for:
- Evaluator Agent
- Metadata Production Agent
- Commercial Assessment Agent
- Confirmation Agent
- Tiebreaker Agent

See [Agent Deployment Guide](AGENT_DEPLOYMENT_GUIDE.md) for detailed instructions for each agent.

### Verify Agent Deployment

```bash
# List all agents
agentcore list

# Describe specific agent
agentcore describe --agent-name brand-metagen-orchestrator-dev

# Test agent invocation
agentcore invoke \
  --agent-name brand-metagen-orchestrator-dev \
  --input '{"action": "test", "message": "Hello"}'
```

## Data Preparation

### Load Initial Data

Before running the workflow, load data into Athena tables:

#### 1. Upload Data to S3

```bash
# Upload brand data
aws s3 cp data/brands.csv s3://brand-generator-rwrd-023-eu-west-1/input/brands/

# Upload combo data
aws s3 cp data/combos.csv s3://brand-generator-rwrd-023-eu-west-1/input/combos/

# Upload MCC data
aws s3 cp data/mcc.csv s3://brand-generator-rwrd-023-eu-west-1/input/mcc/
```

#### 2. Create Athena Tables

```sql
-- Create brand_to_check table
CREATE EXTERNAL TABLE IF NOT EXISTS brand_metadata_generator_db.brand_to_check (
  brandid INT,
  brandname STRING,
  sector STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/input/brands/';

-- Create combo table
CREATE EXTERNAL TABLE IF NOT EXISTS brand_metadata_generator_db.combo (
  ccid INT,
  bankid INT,
  narrative STRING,
  mccid INT
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/input/combos/';

-- Create mcc table
CREATE EXTERNAL TABLE IF NOT EXISTS brand_metadata_generator_db.mcc (
  mccid INT,
  mcc_desc STRING,
  sector STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/input/mcc/';
```

#### 3. Verify Data Load

```bash
# Query brand count
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM brand_metadata_generator_db.brand_to_check" \
  --result-configuration OutputLocation=s3://brand-generator-rwrd-023-eu-west-1/query-results/ \
  --query-execution-context Database=brand_metadata_generator_db

# Query combo count
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM brand_metadata_generator_db.combo" \
  --result-configuration OutputLocation=s3://brand-generator-rwrd-023-eu-west-1/query-results/ \
  --query-execution-context Database=brand_metadata_generator_db
```

## Verification

### 1. Infrastructure Verification

```bash
# Run verification script
python scripts/verify_deployment.py --env dev
```

This script checks:
- S3 bucket exists and is accessible
- Athena database and tables exist
- DynamoDB tables exist
- Lambda functions are deployed
- Step Functions state machine exists
- IAM roles have correct permissions
- CloudWatch log groups exist

### 2. Agent Verification

```bash
# Test each agent
for agent in orchestrator data-transformation evaluator metadata-production commercial-assessment confirmation tiebreaker; do
  echo "Testing $agent..."
  agentcore invoke --agent-name brand-metagen-$agent-dev --input '{"action": "test"}'
done
```

### 3. End-to-End Test

```bash
# Start a test workflow execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-west-1:ACCOUNT_ID:stateMachine:brand-metagen-workflow-dev \
  --name test-execution-$(date +%s) \
  --input '{
    "action": "start_workflow",
    "config": {
      "max_iterations": 1,
      "batch_size": 10
    }
  }'

# Monitor execution
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>
```

### 4. Run Test Suite

```bash
# Run all tests
pytest

# Run integration tests
pytest tests/integration/ -v

# Verify test coverage
pytest --cov=agents --cov=shared --cov-report=term-missing
```

## Monitoring Setup

### CloudWatch Dashboard

The CloudWatch dashboard is automatically created by Terraform. Access it at:
- AWS Console → CloudWatch → Dashboards → `brand-metagen-dev`

### QuickSight Dashboard

Follow the [QuickSight Dashboard Setup Guide](QUICKSIGHT_DASHBOARD_SETUP.md) to create the business monitoring dashboard.

### Alarms

Verify alarms are configured:

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix brand-metagen
```

Configure SNS notifications for production:

```bash
# Create SNS topic
aws sns create-topic --name brand-metagen-alarms-prod

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:eu-west-1:ACCOUNT_ID:brand-metagen-alarms-prod \
  --protocol email \
  --notification-endpoint ops-team@example.com
```

## Troubleshooting

### Terraform Errors

#### Error: S3 Bucket Already Exists

```bash
# Import existing bucket
terraform import module.storage.aws_s3_bucket.main brand-generator-rwrd-023-eu-west-1
```

#### Error: Insufficient Permissions

Verify IAM permissions:
```bash
aws iam get-user
aws iam list-attached-user-policies --user-name <your-username>
```

### Agent Deployment Errors

#### Error: Agent Already Exists

```bash
# Delete existing agent
agentcore delete --agent-name brand-metagen-orchestrator-dev

# Redeploy
python infrastructure/deploy_agents.py --env dev
```

#### Error: Handler Not Found

Verify Python package is installed:
```bash
pip install -e .
python -c "from agents.orchestrator.agentcore_handler import handler; print('OK')"
```

### Workflow Execution Errors

#### Check Step Functions Logs

```bash
aws stepfunctions get-execution-history \
  --execution-arn <execution-arn> \
  --max-results 100
```

#### Check Agent Logs

```bash
aws logs tail /aws/bedrock/agentcore/brand-metagen-orchestrator-dev \
  --follow \
  --filter-pattern "ERROR"
```

## Rollback Procedures

### Rollback Infrastructure

```bash
cd infrastructure/environments/dev

# Destroy specific resources
terraform destroy -target=module.step_functions

# Full rollback
terraform destroy
```

### Rollback Agents

```bash
# Delete all agents
for agent in orchestrator data-transformation evaluator metadata-production commercial-assessment confirmation tiebreaker; do
  agentcore delete --agent-name brand-metagen-$agent-dev
done
```

### Restore from Backup

```bash
# Restore DynamoDB table
aws dynamodb restore-table-from-backup \
  --target-table-name brand-metagen-orchestrator-memory-dev \
  --backup-arn <backup-arn>

# Restore S3 data
aws s3 sync s3://brand-generator-rwrd-023-eu-west-1-backup/ \
  s3://brand-generator-rwrd-023-eu-west-1/
```

## Production Deployment Checklist

Before deploying to production:

- [ ] All tests pass (unit, integration, property-based)
- [ ] Infrastructure deployed and verified in staging
- [ ] Agents deployed and tested in staging
- [ ] End-to-end workflow tested in staging
- [ ] Monitoring dashboards configured
- [ ] Alarms configured with SNS notifications
- [ ] Backup and disaster recovery plan in place
- [ ] Rollback procedures documented and tested
- [ ] Security review completed
- [ ] Performance testing completed
- [ ] Documentation updated
- [ ] Stakeholders notified of deployment window
- [ ] Change management approval obtained

## Post-Deployment

### 1. Verify Production Deployment

```bash
# Run verification script
python scripts/verify_deployment.py --env prod

# Test workflow
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-west-1:ACCOUNT_ID:stateMachine:brand-metagen-workflow-prod \
  --input '{"action": "start_workflow", "config": {"batch_size": 10}}'
```

### 2. Monitor Initial Runs

- Watch CloudWatch dashboard for first 24 hours
- Review error rates and alarm triggers
- Check QuickSight dashboard for business metrics
- Verify data quality in output

### 3. Document Deployment

- Record deployment date and version
- Document any issues encountered
- Update runbooks with lessons learned
- Share deployment summary with team

## Support

For deployment issues:
- Check [Troubleshooting](#troubleshooting) section
- Review CloudWatch logs
- Consult [AGENTCORE_DEPLOYMENT_BEST_PRACTICES.md](../AGENTCORE_DEPLOYMENT_BEST_PRACTICES.md)
- Contact DevOps team

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Step Functions Best Practices](https://docs.aws.amazon.com/step-functions/latest/dg/best-practices.html)
