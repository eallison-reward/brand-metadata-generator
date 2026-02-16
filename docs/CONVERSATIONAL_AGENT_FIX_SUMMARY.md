# Conversational Agent Deployment Fix Summary

## Problem
The conversational interface agent was failing with "Access denied when calling Bedrock" errors when trying to invoke Claude 3.7 Sonnet model.

## Root Cause Analysis

### Issue 1: Incorrect Model Identifier Format
- **Problem**: Using direct model ID `anthropic.claude-3-7-sonnet-20250219-v1:0`
- **Error**: "Invocation of model ID with on-demand throughput isn't supported. Retry your request with the ID or ARN of an inference profile"
- **Solution**: Use inference profile ID `eu.anthropic.claude-3-7-sonnet-20250219-v1:0` instead

### Issue 2: Missing IAM Permissions
The custom IAM role `brand_metagen_agent_execution_dev` was missing critical permissions that AWS-managed roles have by default.

**Missing Actions:**
- `bedrock:GetInferenceProfile`
- `bedrock:GetFoundationModel`

**Missing Resources:**
- Inference profile ARN: `arn:aws:bedrock:eu-west-1:{account-id}:inference-profile/eu.anthropic.claude-3-7-sonnet-20250219-v1:0`
- Cross-region foundation model access: `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0`

## Solution Implemented

### 1. Updated IAM Permissions
Modified `scripts/update_agent_bedrock_permissions.py` to include:

```python
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockInvokeModel",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:GetInferenceProfile",      # NEW
                "bedrock:GetFoundationModel"        # NEW
            ],
            "Resource": [
                # Inference profile for Claude 3.7 Sonnet in EU region
                "arn:aws:bedrock:eu-west-1:{account-id}:inference-profile/eu.anthropic.claude-3-7-sonnet-20250219-v1:0",
                # Cross-region foundation model access
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0",
                # Fallback for other Claude models
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
            ]
        }
    ]
}
```

### 2. Updated Model Configuration
Modified `scripts/deploy_conversational_interface_agent.py`:

```python
# Before (WRONG)
AGENT_CONFIG = {
    "model": "anthropic.claude-3-7-sonnet-20250219-v1:0",  # Direct model ID
    ...
}

# After (CORRECT)
AGENT_CONFIG = {
    "model": "eu.anthropic.claude-3-7-sonnet-20250219-v1:0",  # Inference profile ID
    ...
}
```

## Verification

### Agent Configuration
- **Agent ID**: GZF9REHEAO
- **Agent Name**: brand_metagen_conversational_interface_dev
- **Model**: eu.anthropic.claude-3-7-sonnet-20250219-v1:0 (inference profile)
- **Execution Role**: arn:aws:iam::536824473420:role/brand_metagen_agent_execution_dev
- **Status**: PREPARED ✅

### Test Results
```bash
python scripts/test_conversational_agent.py --agent-id GZF9REHEAO --alias-id XWTFA4KL42
```

**Result**: ✅ SUCCESS
- Agent successfully invoked Claude 3.7 Sonnet
- Tool calls working correctly (query_brands_to_check)
- Natural language responses generated properly

## Key Learnings

1. **Inference Profiles vs Direct Model IDs**
   - Bedrock Agents require inference profile IDs, not direct model IDs
   - Format: `{region}.{provider}.{model-name}` (e.g., `eu.anthropic.claude-3-7-sonnet-20250219-v1:0`)
   - Direct model IDs only work with provisioned throughput

2. **IAM Permission Requirements**
   - `bedrock:InvokeModel` alone is insufficient
   - Must include `bedrock:GetInferenceProfile` and `bedrock:GetFoundationModel`
   - Resource ARNs must include both inference profile and foundation model

3. **AWS-Managed Roles**
   - AWS creates roles like `AmazonBedrockExecutionRoleForAgents_*` with correct permissions
   - These can be used as reference for custom role configuration
   - Managed policies: `AmazonBedrockAgentBedrockFoundationModelPolicy_*` and `AmazonBedrockAgentInferenceProfilesCrossRegionPolicy_*`

## Diagnostic Tools Created

1. **`scripts/inspect_working_agent.py`**
   - Inspects agent configuration
   - Shows model ID, execution role, action groups, aliases
   - Usage: `python scripts/inspect_working_agent.py --agent-id <AGENT_ID>`

2. **`scripts/check_agent_permissions.py`**
   - Checks IAM role permissions
   - Shows inline and managed policies
   - Identifies Bedrock-specific permissions
   - Usage: `python scripts/check_agent_permissions.py --role-name <ROLE_NAME>`

3. **`scripts/inspect_managed_policy.py`**
   - Inspects AWS-managed policy documents
   - Shows exact permissions and resources
   - Usage: `python scripts/inspect_managed_policy.py --policy-arn <POLICY_ARN>`

4. **`scripts/test_conversational_agent.py`**
   - Tests agent with natural language prompts
   - Streams responses in real-time
   - Usage: `python scripts/test_conversational_agent.py --agent-id <AGENT_ID> --alias-id <ALIAS_ID>`

## Deployment Commands

### Update IAM Permissions
```bash
python scripts/update_agent_bedrock_permissions.py --role-name brand_metagen_agent_execution_dev
```

### Deploy Agent
```bash
python scripts/deploy_conversational_interface_agent.py \
  --env dev \
  --role-arn arn:aws:iam::536824473420:role/brand_metagen_agent_execution_dev
```

### Test Agent
```bash
python scripts/test_conversational_agent.py \
  --agent-id GZF9REHEAO \
  --alias-id XWTFA4KL42 \
  --prompt "what brands are ready to be processed?"
```

## References

- AWS Bedrock Agents Documentation: https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- Inference Profiles: https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles.html
- IAM Permissions for Bedrock: https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html

## Status

✅ **RESOLVED** - Agent is now fully functional with correct model configuration and IAM permissions.
