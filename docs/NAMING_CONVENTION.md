# AWS Resource Naming Convention

## Overview

All AWS resources created for the Brand Metadata Generator system follow a consistent naming convention using the prefix `brand_metagen_` to ensure clear identification and avoid naming conflicts.

## Naming Rules

### Resources WITH the `brand_metagen_` prefix:

1. **Lambda Functions**: `brand_metagen_<function_name>_<environment>`
   - Example: `brand_metagen_orchestrator_invoke_dev`
   - Example: `brand_metagen_workflow_init_prod`

2. **Step Functions State Machines**: `brand_metagen_workflow_<environment>`
   - Example: `brand_metagen_workflow_dev`
   - Example: `brand_metagen_workflow_prod`

3. **DynamoDB Tables**: `brand_metagen_<table_purpose>_<details>_<environment>`
   - Example: `brand_metagen_agent_memory_orchestrator_dev`
   - Example: `brand_metagen_agent_memory_evaluator_prod`
   - Example: `brand_metagen_feedback_history_dev`

4. **IAM Roles**: `brand_metagen_<role_purpose>_<environment>`
   - Example: `brand_metagen_agent_execution_dev`
   - Example: `brand_metagen_step_functions_prod`
   - Example: `brand_metagen_lambda_execution_dev`

5. **IAM Policies**: `brand_metagen_<policy_purpose>_<environment>`
   - Example: `brand_metagen_agent_policy_dev`
   - Example: `brand_metagen_step_functions_policy_prod`

6. **CloudWatch Log Groups**: `/aws/<service>/brand_metagen_<resource_name>_<environment>`
   - Example: `/aws/lambda/brand_metagen_orchestrator_invoke_dev`
   - Example: `/aws/vendedlogs/states/brand_metagen_workflow_dev`
   - Example: `/aws/bedrock/agentcore/brand_metagen_orchestrator_dev`

7. **CloudWatch Alarms**: `brand_metagen_<alarm_purpose>_<environment>`
   - Example: `brand_metagen_workflow_failures_dev`
   - Example: `brand_metagen_agent_errors_prod`

8. **CloudWatch Dashboards**: `brand_metagen_<dashboard_name>_<environment>`
   - Example: `brand_metagen_monitoring_dev`
   - Example: `brand_metagen_agent_metrics_prod`

### Resources WITHOUT the `brand_metagen_` prefix:

1. **S3 Bucket**: `brand-generator-rwrd-023-eu-west-1`
   - Fixed name, already established

2. **Athena Database**: `brand_metadata_generator_db`
   - Fixed name, already established

3. **Athena Tables**: Use their defined names
   - `brand`
   - `brand_to_check`
   - `combo`
   - `mcc`

4. **Glue Catalog Database**: `brand_metadata_generator_db`
   - Matches Athena database name

5. **Bedrock Agents**: Agent names can use descriptive names
   - Example: `orchestrator`, `evaluator`, `metadata_production`
   - These are internal identifiers, not AWS resource names

## Environment Suffixes

All resources include an environment suffix:
- `dev` - Development environment
- `staging` - Staging environment
- `prod` - Production environment

## Examples by Service

### Lambda Functions
```
brand_metagen_orchestrator_invoke_dev
brand_metagen_workflow_init_dev
brand_metagen_result_aggregation_dev
brand_metagen_feedback_submit_prod
```

### Step Functions
```
brand_metagen_workflow_dev
brand_metagen_workflow_prod
```

### DynamoDB Tables
```
brand_metagen_agent_memory_orchestrator_dev
brand_metagen_agent_memory_evaluator_dev
brand_metagen_agent_memory_metadata_production_dev
brand_metagen_feedback_history_dev
```

### IAM Roles
```
brand_metagen_agent_execution_dev
brand_metagen_step_functions_dev
brand_metagen_lambda_execution_dev
```

### CloudWatch Resources
```
/aws/lambda/brand_metagen_orchestrator_invoke_dev
/aws/vendedlogs/states/brand_metagen_workflow_dev
/aws/bedrock/agentcore/brand_metagen_orchestrator_dev

brand_metagen_workflow_failures_dev
brand_metagen_agent_errors_dev
brand_metagen_monitoring_dev
```

## Rationale

1. **Clarity**: The `brand_metagen_` prefix immediately identifies resources belonging to this system
2. **Consistency**: All resources follow the same pattern
3. **Searchability**: Easy to find all related resources in AWS console or CLI
4. **Separation**: Clear distinction from other projects in the same AWS account
5. **Automation**: Predictable naming enables scripting and automation
6. **Cost Tracking**: Enables cost allocation by resource prefix

## Implementation

This naming convention is enforced through:
1. Terraform variable defaults
2. Infrastructure module configurations
3. Deployment scripts
4. Code review requirements

## References

- Requirements Document: Requirement 11.15
- Terraform Modules: `infrastructure/modules/`
- Deployment Scripts: `infrastructure/deploy_agents.py`
