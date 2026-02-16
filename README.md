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
5. **Commercial Assessment Agent** - Validates brand identity against real-world data via MCP
6. **Confirmation Agent** - Reviews matched combos to exclude false positives
7. **Tiebreaker Agent** - Resolves combos matching multiple brands
8. **Feedback Processing Agent** - Parses human feedback and generates refinement prompts
9. **Learning Analytics Agent** - Analyzes trends and tracks accuracy improvements

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
- AgentCore CLI installed

### Install Dependencies

```bash
# Install Python dependencies
pip install -e .

# Install development dependencies
pip install pytest pytest-cov hypothesis black flake8 mypy

# Install AgentCore CLI (for agent deployment)
pip install bedrock-agentcore-starter-toolkit

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

# Deploy workflow agents to AgentCore
cd ../../..
python scripts/deploy_agentcore_agents.py --env dev

# Deploy conversational interface agent to Bedrock Agents  
python scripts/deploy_conversational_interface_agent.py --env dev --role-arn $(terraform -chdir=infrastructure/environments/dev output -raw agent_execution_role_arn)
```

### 4. Deploy Agents

```bash
# Deploy all agents to dev environment
python infrastructure/deploy_agents.py --env dev
```

### 5. Run Tests

```bash
# Run all tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Property-based tests only
pytest tests/property/ -v

# Run with coverage
pytest --cov=agents --cov=shared --cov-report=html

# Run specific test file
pytest tests/unit/test_orchestrator.py -v
```

### Test Coverage

The project includes comprehensive test coverage:
- **177 unit tests**: Test individual functions and components
- **34 property-based tests**: Validate universal correctness properties
- **26 integration tests**: Test end-to-end workflows

All tests must pass before deployment to production.

## Deployment

### Development Environment

```bash
cd infrastructure/environments/dev
terraform apply

# Deploy workflow agents to AgentCore
cd ../../..
python scripts/deploy_agentcore_agents.py --env dev

# Deploy conversational interface agent to Bedrock Agents
python scripts/deploy_conversational_interface_agent.py --env dev --role-arn $(terraform -chdir=infrastructure/environments/dev output -raw agent_execution_role_arn)
```

### Production Environment

```bash
cd infrastructure/environments/prod
terraform apply

# Deploy workflow agents to AgentCore
cd ../../..
python scripts/deploy_agentcore_agents.py --env prod

# Deploy conversational interface agent to Bedrock Agents
python scripts/deploy_conversational_interface_agent.py --env prod --role-arn $(terraform -chdir=infrastructure/environments/prod output -raw agent_execution_role_arn)
```

## Usage

### Starting the Workflow

The workflow can be triggered via AWS Step Functions:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-west-1:ACCOUNT_ID:stateMachine:brand-metagen-workflow-dev \
  --input '{
    "action": "start_workflow",
    "config": {
      "max_iterations": 5,
      "confidence_threshold": 0.75,
      "batch_size": 100
    }
  }'
```

### Monitoring Progress

#### CloudWatch Dashboard

Access the CloudWatch dashboard for real-time metrics:
- Navigate to CloudWatch → Dashboards → `brand-metagen-dev`
- View workflow execution metrics, brand processing status, and agent invocations

#### Quick Suite Interface

For agent-specific monitoring and human review:
1. Navigate to AWS Bedrock Console
2. Select "AgentCore" → "Quick Suite"
3. View brand classification results, provide feedback, and approve/reject metadata

**NOTE**: Quick Suite is an AWS Bedrock AgentCore technology for agent interfaces. This is NOT Amazon QuickSight (a BI tool). See [Quick Suite vs QuickSight](docs/QUICK_SUITE_VS_QUICKSIGHT.md) for clarification.

See [Quick Suite Setup Guide](docs/QUICK_SUITE_SETUP.md) for detailed instructions.

#### CloudWatch Logs

Tail agent logs in real-time:

```bash
# Orchestrator logs
aws logs tail /aws/bedrock/agentcore/brand-metagen-orchestrator-dev --follow

# All agent logs
aws logs tail /aws/bedrock/agentcore/brand-metagen-* --follow

# Filter for errors
aws logs tail /aws/bedrock/agentcore/brand-metagen-* --follow --filter-pattern "ERROR"
```

### Workflow Phases

1. **Initialization**: Load configuration and prepare data
2. **Data Transformation**: Ingest and validate brand data from Athena
3. **Evaluation**: Assess data quality and detect payment wallets
4. **Metadata Production**: Generate regex patterns and MCCID lists
5. **Confirmation**: Review matched combos and exclude false positives
6. **Tie Resolution**: Handle combos matching multiple brands
7. **Result Aggregation**: Store final metadata in S3

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

- [Requirements](.kiro/specs/brand-metadata-generator/requirements.md) - Detailed system requirements and acceptance criteria
- [Design](.kiro/specs/brand-metadata-generator/design.md) - System architecture and design decisions
- [Implementation Plan](.kiro/specs/brand-metadata-generator/tasks.md) - Task breakdown and progress tracking
- [Agent Deployment Guide](docs/AGENT_DEPLOYMENT_GUIDE.md) - Step-by-step agent deployment instructions
- [Step Functions Workflow](docs/STEP_FUNCTIONS_WORKFLOW.md) - Workflow state machine documentation
- [Quick Suite Setup](docs/QUICK_SUITE_SETUP.md) - Human review interface configuration guide
- [Quick Suite vs QuickSight](docs/QUICK_SUITE_VS_QUICKSIGHT.md) - Important technology distinction
- [Deployment Best Practices](AGENTCORE_DEPLOYMENT_BEST_PRACTICES.md) - AgentCore deployment guidelines
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute to the project

## Key Features

### Intelligent Metadata Generation

- **Pattern Recognition**: Analyzes transaction narratives to generate precise regex patterns
- **MCCID Filtering**: Identifies legitimate merchant category codes while excluding wallet-specific codes
- **Wallet Detection**: Automatically detects and handles payment wallet transactions (PayPal, Square, etc.)
- **Iterative Refinement**: Supports up to 5 iterations with feedback-driven improvements

### Quality Assurance

- **Confidence Scoring**: Calculates confidence scores (0.0-1.0) for all generated metadata
- **False Positive Detection**: Identifies and excludes ambiguous matches (e.g., "Apple" fruit vs Apple Inc.)
- **Tie Resolution**: Resolves combos matching multiple brands using narrative similarity and MCCID alignment
- **Human Review Flagging**: Automatically flags low-confidence cases for human review

### Monitoring and Observability

- **CloudWatch Integration**: Real-time metrics for workflow execution, agent invocations, and errors
- **QuickSight Dashboards**: Business-level monitoring of brand processing and combo matching
- **Comprehensive Logging**: Detailed logs for all agent activities and decisions
- **Automated Alarms**: Alerts for workflow failures, high error rates, and review queue buildup

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
