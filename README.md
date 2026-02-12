# Brand Metadata Generator

A multi-agent system for automatically generating classification metadata for retail brands using AWS Bedrock AgentCore.

## Overview

The Brand Metadata Generator processes over 3,000 retail brands to produce:
- Regular expression patterns for transaction narrative matching
- Lists of legitimate Merchant Category Codes (MCCIDs)
- Agent confirmation flags for complex cases
- Resolution of brand classification ties

The system uses 7 specialized AI agents orchestrated through AWS Step Functions to analyze transaction data, handle payment wallet complications, and ensure high-quality metadata through iterative refinement.

## Architecture

- **Agent Framework**: Strands API on AWS Bedrock AgentCore
- **Orchestration**: AWS Step Functions
- **Data Storage**: AWS S3 (brand-generator-rwrd-023-eu-west-1)
- **Data Querying**: AWS Athena (database: brand_metadata_generator_db)
- **Infrastructure**: Terraform for IaC
- **Region**: eu-west-1

## Agents

1. **Orchestrator Agent** - Coordinates workflow between all agents
2. **Data Transformation Agent** - Handles data ingestion, validation, and storage
3. **Evaluator Agent** - Assesses data quality and calculates confidence scores
4. **Metadata Production Agent** - Generates regex patterns and MCCID lists
5. **Commercial Assessment Agent** - Validates brand identity against real-world data
6. **Confirmation Agent** - Reviews matched combos to exclude false positives
7. **Tiebreaker Agent** - Resolves combos matching multiple brands

## Project Structure

```
brand-metadata-generator/
├── agents/                     # Agent implementations
│   ├── orchestrator/
│   ├── data_transformation/
│   ├── evaluator/
│   ├── metadata_production/
│   ├── commercial_assessment/
│   ├── confirmation/
│   └── tiebreaker/
├── shared/                     # Shared utilities
│   ├── storage/
│   ├── monitoring/
│   └── models/
├── infrastructure/             # Terraform configurations
│   ├── modules/
│   │   ├── agents/
│   │   ├── step_functions/
│   │   ├── storage/
│   │   └── monitoring/
│   └── environments/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── tests/                      # Test suites
│   ├── unit/
│   ├── integration/
│   └── property/
├── docs/                       # Documentation
│   └── deployment/
└── .kiro/                      # Kiro specs
    └── specs/
        └── brand-metadata-generator/
```

## Prerequisites

- Python 3.12+
- AWS CLI configured with appropriate credentials
- Terraform 1.0+
- AWS account with Bedrock access in eu-west-1

```bash
# Install Python dependencies
pip install bedrock-agentcore-starter-toolkit
pip install strands-agents strands-agents-tools
pip install boto3 pytest

# Configure AWS
aws configure
# Set region to eu-west-1
```

## Setup Instructions

### 1. Clone Repository

```bash
git clone <repository-url>
cd brand-metadata-generator
```

### 2. Set Up Python Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure AWS Infrastructure

```bash
cd infrastructure/environments/dev
terraform init
terraform plan
terraform apply
```

### 4. Deploy Agents

```bash
# Deploy all agents to dev environment
python infrastructure/deploy_agents.py --env dev
```

### 5. Run Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Property-based tests
pytest tests/property/
```

## Deployment

### Development Environment

```bash
cd infrastructure/environments/dev
terraform apply
python ../../deploy_agents.py --env dev
```

### Production Environment

```bash
cd infrastructure/environments/prod
terraform apply
python ../../deploy_agents.py --env prod
```

## Usage

### Invoke Workflow via Step Functions

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-west-1:ACCOUNT_ID:stateMachine:brand-metadata-generator \
  --input '{"action": "start_workflow", "config": {"max_iterations": 5}}'
```

### Monitor Progress

Access the Quick_Suite dashboard or check CloudWatch Logs:

```bash
aws logs tail /aws/bedrock/agentcore/orchestrator --follow
```

## Configuration

Key configuration parameters in `infrastructure/environments/<env>/terraform.tfvars`:

- `aws_region`: AWS region (must be eu-west-1)
- `s3_bucket`: S3 bucket name (brand-generator-rwrd-023-eu-west-1)
- `athena_database`: Athena database name (brand_metadata_generator_db)
- `confidence_threshold`: Minimum confidence score (default: 0.75)
- `max_iterations`: Maximum metadata generation iterations (default: 5)

## Troubleshooting

### Agent Not Responding

```bash
# Check agent status
agentcore describe --agent-name orchestrator-agent

# View logs
agentcore logs --agent-name orchestrator-agent --tail 100
```

### Workflow Failures

Check Step Functions execution history:

```bash
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>
```

### Data Issues

Verify Athena tables:

```bash
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM brand_metadata_generator_db.brand_to_check" \
  --result-configuration OutputLocation=s3://brand-generator-rwrd-023-eu-west-1/query-results/
```

## Documentation

- [Requirements](.kiro/specs/brand-metadata-generator/requirements.md)
- [Design](.kiro/specs/brand-metadata-generator/design.md)
- [Implementation Plan](.kiro/specs/brand-metadata-generator/tasks.md)
- [Deployment Best Practices](AGENTCORE_DEPLOYMENT_BEST_PRACTICES.md)

## Contributing

1. Create a feature branch from `main`
2. Make changes and add tests
3. Run test suite: `pytest tests/`
4. Submit pull request for review
5. Merge after approval

## License

[Your License Here]

## Contact

[Your Contact Information]
