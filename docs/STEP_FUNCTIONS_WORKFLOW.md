# Step Functions Workflow Documentation

## Overview

The Brand Metadata Generator uses AWS Step Functions to orchestrate the multi-agent workflow. The state machine coordinates Lambda functions that invoke Bedrock AgentCore agents to process brands through evaluation, metadata generation, and classification.

## Workflow Architecture

### State Machine: `brand_metagen_workflow_{environment}`

The workflow consists of the following states:

1. **InitializeWorkflow** - Validates inputs and loads configuration
2. **InvokeOrchestrator** - Invokes the Orchestrator Agent to coordinate all phases
3. **CheckOrchestratorStatus** - Routes based on orchestrator completion status
4. **AggregateResults** - Collects and summarizes results from all brands
5. **HandlePartialCompletion** - Handles scenarios where some brands succeeded and some failed
6. **NotifyHumanReview** - Handles brands requiring human review
7. **HandleTimeout** - Handles orchestrator timeout scenarios
8. **WorkflowSucceeded** - Terminal success state
9. **WorkflowFailed** - Terminal failure state

## Lambda Functions

### 1. Workflow Initialization (`brand_metagen_workflow_init_{environment}`)

**Purpose**: Initialize workflow configuration and validate inputs

**Handler**: `lambda_functions/workflow_init/handler.py`

**Timeout**: 60 seconds

**Environment Variables**:
- `AWS_REGION`: AWS region (eu-west-1)
- `S3_BUCKET`: S3 bucket name
- `ATHENA_DATABASE`: Athena database name
- `ENVIRONMENT`: Environment (dev/staging/prod)

**Input**:
```json
{
  "config": {
    "confidence_threshold": 0.75,
    "max_iterations": 5,
    "batch_size": 10
  }
}
```

**Output**:
```json
{
  "statusCode": 200,
  "config": { ... },
  "state": {
    "workflow_id": "...",
    "status": "initialized"
  }
}
```

### 2. Orchestrator Invocation (`brand_metagen_orchestrator_invoke_{environment}`)

**Purpose**: Invoke the Orchestrator Agent to coordinate all workflow phases

**Handler**: `lambda_functions/orchestrator_invoke/handler.py`

**Timeout**: 900 seconds (15 minutes)

**Environment Variables**:
- `AWS_REGION`: AWS region (eu-west-1)
- `ORCHESTRATOR_AGENT_ID`: Bedrock Agent ID for orchestrator
- `ORCHESTRATOR_AGENT_ALIAS_ID`: Bedrock Agent alias ID
- `ENVIRONMENT`: Environment (dev/staging/prod)

**Input**:
```json
{
  "workflow_config": {
    "config": { ... },
    "state": { ... }
  }
}
```

**Output**:
```json
{
  "statusCode": 200,
  "status": "completed",
  "succeeded_brands": [1, 2, 3],
  "failed_brands": [],
  "brands_requiring_review": [],
  "summary": { ... }
}
```

### 3. Result Aggregation (`brand_metagen_result_aggregation_{environment}`)

**Purpose**: Aggregate results from all processed brands and generate summary report

**Handler**: `lambda_functions/result_aggregation/handler.py`

**Timeout**: 300 seconds (5 minutes)

**Environment Variables**:
- `AWS_REGION`: AWS region (eu-west-1)
- `S3_BUCKET`: S3 bucket name
- `ENVIRONMENT`: Environment (dev/staging/prod)

**Input**:
```json
{
  "orchestrator_result": { ... },
  "workflow_config": { ... }
}
```

**Output**:
```json
{
  "statusCode": 200,
  "summary": {
    "total_brands_processed": 10,
    "succeeded_brands": 9,
    "failed_brands": 1,
    "success_rate_percent": 90.0,
    "total_combos_matched": 1500,
    "total_combos_confirmed": 1350,
    "total_combos_excluded": 150
  },
  "report_location": "s3://..."
}
```

## Error Handling

### Retry Logic

All Lambda invocations include retry logic:
- **InitializeWorkflow**: 3 retries with exponential backoff (2x)
- **InvokeOrchestrator**: 2 retries with exponential backoff (2x)
- **AggregateResults**: 3 retries with exponential backoff (2x)

### Catch Blocks

Each state includes catch blocks to handle:
- `States.Timeout`: Specific timeout handling
- `States.TaskFailed`: Task-specific failures
- `States.ALL`: Catch-all for unexpected errors

### Timeout Configuration

- **InitializeWorkflow**: 60 seconds
- **InvokeOrchestrator**: 3600 seconds (1 hour) with 300-second heartbeat
- **AggregateResults**: 300 seconds

## Workflow Execution

### Starting a Workflow

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-west-1:ACCOUNT_ID:stateMachine:brand_metagen_workflow_dev \
  --input '{
    "config": {
      "confidence_threshold": 0.75,
      "max_iterations": 5,
      "batch_size": 10
    }
  }'
```

### Monitoring Execution

```bash
# Get execution status
aws stepfunctions describe-execution \
  --execution-arn EXECUTION_ARN

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn EXECUTION_ARN
```

### CloudWatch Logs

Logs are available in:
- `/aws/vendedlogs/states/brand_metagen_workflow_{environment}` - Step Functions execution logs
- `/aws/lambda/brand_metagen_workflow_init_{environment}` - Initialization Lambda logs
- `/aws/lambda/brand_metagen_orchestrator_invoke_{environment}` - Orchestrator Lambda logs
- `/aws/lambda/brand_metagen_result_aggregation_{environment}` - Aggregation Lambda logs

## Deployment

### Prerequisites

1. Package Lambda functions:
```bash
# Linux/Mac
./scripts/package_lambdas.sh

# Windows
.\scripts\package_lambdas.ps1
```

2. Deploy infrastructure with Terraform:
```bash
cd infrastructure/environments/dev
terraform init
terraform plan
terraform apply
```

### Lambda Deployment

Lambda functions are deployed via Terraform using ZIP files:
- `lambda_functions/workflow_init.zip`
- `lambda_functions/orchestrator_invoke.zip`
- `lambda_functions/result_aggregation.zip`

### State Machine Deployment

The state machine definition is deployed via Terraform using the template file:
- `infrastructure/workflows/brand_metadata_workflow.json`

## Configuration

### Workflow Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `confidence_threshold` | float | 0.75 | Minimum confidence score for automatic approval |
| `max_iterations` | int | 5 | Maximum metadata regeneration iterations |
| `batch_size` | int | 10 | Number of brands to process in parallel |
| `enable_confirmation` | bool | true | Enable Confirmation Agent review |
| `enable_tiebreaker` | bool | true | Enable Tiebreaker Agent for multi-matches |

### Environment Variables

All Lambda functions require:
- `AWS_REGION`: Must be `eu-west-1`
- `ENVIRONMENT`: Environment name (dev/staging/prod)

Additional function-specific variables are documented above.

## Terraform Resources

### Step Functions Module

Location: `infrastructure/modules/step_functions/`

Resources created:
- `aws_sfn_state_machine.brand_metadata_workflow` - State machine
- `aws_iam_role.step_functions_role` - Execution role
- `aws_iam_role_policy.step_functions_policy` - Execution policy
- `aws_cloudwatch_log_group.step_functions_logs` - Log group

### Lambda Module

Location: `infrastructure/modules/lambda/`

Resources created:
- `aws_lambda_function.workflow_init` - Initialization function
- `aws_lambda_function.orchestrator_invoke` - Orchestrator invocation function
- `aws_lambda_function.result_aggregation` - Result aggregation function
- `aws_iam_role.lambda_execution_role` - Execution role
- `aws_iam_role_policy.lambda_execution_policy` - Execution policy
- `aws_cloudwatch_log_group.*_logs` - Log groups for each function

## Naming Convention

All resources follow the `brand_metagen_` prefix convention:
- State machine: `brand_metagen_workflow_{environment}`
- Lambda functions: `brand_metagen_{function_name}_{environment}`
- IAM roles: `brand_metagen_{role_purpose}_{environment}`
- Log groups: `/aws/{service}/brand_metagen_{resource}_{environment}`

## Integration with Agents

The workflow integrates with Bedrock AgentCore agents:

1. **Orchestrator Agent**: Coordinates all workflow phases
2. **Data Transformation Agent**: Handles data ingestion and validation
3. **Evaluator Agent**: Evaluates brand quality and generates prompts
4. **Metadata Production Agent**: Generates regex patterns and MCCID lists
5. **Confirmation Agent**: Reviews matches for false positives
6. **Tiebreaker Agent**: Resolves multi-brand matches
7. **Commercial Assessment Agent**: Validates brand existence and sector

The Orchestrator Agent is invoked by the `orchestrator_invoke` Lambda function and coordinates all other agents internally.

## Troubleshooting

### Common Issues

1. **Lambda Timeout**: Increase timeout in Terraform configuration
2. **Permission Errors**: Verify IAM roles have correct permissions
3. **Agent Not Found**: Ensure `ORCHESTRATOR_AGENT_ID` is set correctly
4. **S3 Access Denied**: Verify Lambda role has S3 permissions

### Debug Steps

1. Check CloudWatch Logs for detailed error messages
2. Review Step Functions execution history
3. Verify environment variables are set correctly
4. Test Lambda functions individually using AWS Console
5. Verify Bedrock Agent is deployed and accessible

## Future Enhancements

Planned improvements for the workflow:
- Parallel brand processing using Map state
- Human-in-the-loop feedback integration
- Learning analytics integration
- Dynamic timeout adjustment based on brand complexity
- Workflow pause/resume capability
