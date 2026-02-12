# Infrastructure as Code

This directory contains Terraform configurations for deploying the Brand Metadata Generator infrastructure to AWS.

## Structure

```
infrastructure/
├── modules/              # Reusable Terraform modules
│   ├── agents/          # IAM roles and policies for agents
│   ├── storage/         # S3, Athena, and Glue resources
│   ├── dynamodb/        # DynamoDB tables for agent memory
│   ├── step_functions/  # Step Functions state machine
│   └── monitoring/      # CloudWatch dashboards and alarms
├── environments/        # Environment-specific configurations
│   ├── dev/            # Development environment
│   ├── staging/        # Staging environment
│   └── prod/           # Production environment
└── deploy_agents.py    # Script to deploy agents to AgentCore
```

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- AWS account with permissions to create:
  - S3 buckets
  - IAM roles and policies
  - DynamoDB tables
  - Glue databases and tables
  - Athena workgroups
  - Step Functions state machines
  - CloudWatch resources

## Quick Start

### 1. Initialize Terraform

```bash
cd infrastructure/environments/dev
terraform init
```

### 2. Review Plan

```bash
terraform plan
```

### 3. Apply Configuration

```bash
terraform apply
```

Type `yes` when prompted to create the resources.

### 4. View Outputs

```bash
terraform output
```

## Modules

### Storage Module

Creates:
- S3 bucket: `brand-generator-rwrd-023-eu-west-1`
- Athena database: `brand_metadata_generator_db`
- Glue tables: `brand`, `brand_to_check`, `combo`, `mcc`
- Athena workgroup for query execution

### Agents Module

Creates:
- IAM execution role for agents
- Policies for Bedrock, S3, Athena, DynamoDB, and CloudWatch access

### DynamoDB Module

Creates:
- DynamoDB tables for agent memory (one per agent)
- TTL configuration for automatic data expiration
- Optional point-in-time recovery (enabled in prod)

### Step Functions Module

Creates:
- Step Functions state machine for workflow orchestration
- IAM execution role for Step Functions
- CloudWatch log group for execution logs

### Monitoring Module

Creates:
- CloudWatch log groups for each agent
- CloudWatch dashboard for metrics visualization
- CloudWatch alarms for workflow failures
- Optional SNS topic for alarm notifications

## Environment Configuration

### Development (dev)

- Point-in-time recovery: Disabled
- SNS alarms: Disabled
- Log retention: 30 days

### Staging (staging)

- Point-in-time recovery: Enabled
- SNS alarms: Enabled
- Log retention: 60 days

### Production (prod)

- Point-in-time recovery: Enabled
- SNS alarms: Enabled
- Log retention: 90 days
- Additional monitoring and alerting

## Variables

Key variables (defined in `variables.tf`):

- `aws_region`: AWS region (MUST be `eu-west-1`)
- `s3_bucket_name`: S3 bucket name (MUST be `brand-generator-rwrd-023-eu-west-1`)
- `athena_database`: Athena database name (MUST be `brand_metadata_generator_db`)
- `agent_names`: List of agent names for resource creation

## Outputs

After applying, Terraform outputs:

- S3 bucket name and ARN
- Athena database and workgroup names
- Agent execution role ARN
- Step Functions state machine ARN
- DynamoDB table names
- CloudWatch dashboard name

## State Management

### Local State (Default)

By default, Terraform state is stored locally in `terraform.tfstate`.

### Remote State (Recommended for Teams)

To use remote state with S3:

1. Create S3 bucket for state:
```bash
aws s3 mb s3://brand-metadata-generator-terraform-state --region eu-west-1
```

2. Create DynamoDB table for state locking:
```bash
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-1
```

3. Uncomment backend configuration in `main.tf`:
```hcl
backend "s3" {
  bucket         = "brand-metadata-generator-terraform-state"
  key            = "dev/terraform.tfstate"
  region         = "eu-west-1"
  encrypt        = true
  dynamodb_table = "terraform-state-lock"
}
```

4. Re-initialize Terraform:
```bash
terraform init -migrate-state
```

## Deployment Workflow

### Initial Deployment

```bash
# 1. Deploy infrastructure
cd infrastructure/environments/dev
terraform init
terraform apply

# 2. Deploy agents
cd ../../..
python infrastructure/deploy_agents.py --env dev

# 3. Verify deployment
aws bedrock list-agents --region eu-west-1
```

### Updates

```bash
# Update infrastructure
cd infrastructure/environments/dev
terraform plan
terraform apply

# Update specific agent
python infrastructure/deploy_agents.py --env dev --agent orchestrator
```

### Destroy

```bash
# Delete agents first
for agent in orchestrator data_transformation evaluator metadata_production commercial_assessment confirmation tiebreaker; do
  agentcore delete --agent-name ${agent}-agent-dev
done

# Then destroy infrastructure
cd infrastructure/environments/dev
terraform destroy
```

## Troubleshooting

### Permission Errors

Ensure your AWS credentials have sufficient permissions:
```bash
aws sts get-caller-identity
aws iam get-user
```

### State Lock Issues

If state is locked:
```bash
# Force unlock (use with caution)
terraform force-unlock <LOCK_ID>
```

### Resource Already Exists

If resources already exist:
```bash
# Import existing resource
terraform import module.storage.aws_s3_bucket.data_bucket brand-generator-rwrd-023-eu-west-1
```

## Best Practices

1. Always run `terraform plan` before `apply`
2. Use workspaces or separate state files for environments
3. Enable remote state for team collaboration
4. Tag all resources appropriately
5. Use variables for environment-specific values
6. Review and approve changes in pull requests
7. Keep Terraform version consistent across team

## Security

- IAM roles follow least-privilege principle
- S3 buckets have encryption enabled
- Public access is blocked on S3 buckets
- CloudWatch logs are retained for audit
- Sensitive values should use AWS Secrets Manager (not implemented yet)

## Cost Optimization

- DynamoDB uses on-demand billing
- S3 lifecycle policies can be added for old data
- CloudWatch log retention is configurable
- Athena charges per query - optimize queries
- Consider reserved capacity for production

## Support

For issues or questions:
- Check Terraform documentation: https://www.terraform.io/docs
- Review AWS provider docs: https://registry.terraform.io/providers/hashicorp/aws
- Open an issue in the project repository
