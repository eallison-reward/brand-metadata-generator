# Agent Architecture Clarification

## Overview

This document clarifies the correct deployment architecture for the Brand Metadata Generator agents and explains why the previous deployment approach was incorrect.

## Correct Architecture

### AgentCore Agents (Workflow Processing)
These agents use the **Strands API** and should be deployed to **AWS Bedrock AgentCore runtime**:

- `orchestrator` - Coordinates all workflow phases
- `data_transformation` - Handles data ingestion and validation  
- `evaluator` - Evaluates brand quality and generates prompts
- `metadata_production` - Generates regex patterns and MCCID lists
- `commercial_assessment` - Validates brand existence and sectors
- `confirmation` - Reviews matched combos to exclude false positives
- `tiebreaker` - Resolves combos matching multiple brands
- `feedback_processing` - Processes human feedback for refinement
- `learning_analytics` - Analyzes feedback trends and accuracy metrics

**Deployment**: Use `scripts/deploy_agentcore_agents.py`

### Bedrock Agent (User Interface)
This agent provides natural language interface and should be deployed as a **Bedrock Agent**:

- `conversational_interface` - Natural language interface for users

**Deployment**: Use `scripts/deploy_conversational_interface_agent.py`

## Previous Incorrect Approach

The `infrastructure/deploy_agents.py` script was **incorrectly** deploying Strands-based agents as Bedrock Agents instead of to AgentCore runtime. This caused:

1. **Runtime Mismatch**: Strands API agents deployed to wrong runtime
2. **Tool Integration Issues**: AgentCore tools not properly accessible
3. **Performance Problems**: Agents not optimized for their intended runtime
4. **Architectural Confusion**: Mixed deployment patterns

## Correct Deployment Commands

### Development Environment
```bash
# Deploy infrastructure
cd infrastructure/environments/dev
terraform apply

# Deploy workflow agents to AgentCore
cd ../../..
python scripts/deploy_agentcore_agents.py --env dev

# Deploy conversational interface to Bedrock Agents
python scripts/deploy_conversational_interface_agent.py --env dev --role-arn $(terraform -chdir=infrastructure/environments/dev output -raw agent_execution_role_arn)
```

### Production Environment
```bash
# Deploy infrastructure
cd infrastructure/environments/prod
terraform apply

# Deploy workflow agents to AgentCore
cd ../../..
python scripts/deploy_agentcore_agents.py --env prod

# Deploy conversational interface to Bedrock Agents
python scripts/deploy_conversational_interface_agent.py --env prod --role-arn $(terraform -chdir=infrastructure/environments/prod output -raw agent_execution_role_arn)
```

## Verification

### Check AgentCore Agents
```bash
# List all deployed AgentCore agents
agentcore list

# Check specific agent status
agentcore describe --agent-name brand-metagen-orchestrator-dev

# View agent logs
agentcore logs --agent-name brand-metagen-orchestrator-dev --tail 100
```

### Check Bedrock Agent
```bash
# List Bedrock agents
aws bedrock-agent list-agents --region eu-west-1

# Check conversational interface agent
aws bedrock-agent get-agent --agent-id <agent-id> --region eu-west-1
```

## Key Differences

| Aspect | AgentCore Runtime | Bedrock Agents |
|--------|------------------|----------------|
| **API** | Strands API | Bedrock Agent API |
| **Use Case** | Workflow processing | User interaction |
| **Tools** | Python functions with @tool decorator | Lambda functions |
| **Deployment** | AgentCore CLI | AWS SDK/CLI |
| **Invocation** | Direct agent calls | Through Bedrock runtime |
| **Logging** | `/aws/bedrock/agentcore/` | `/aws/bedrock/agents/` |

## Migration Steps

If you have agents deployed incorrectly:

1. **Delete incorrect Bedrock Agents**:
   ```bash
   # List and delete incorrectly deployed agents
   aws bedrock-agent list-agents --region eu-west-1
   aws bedrock-agent delete-agent --agent-id <agent-id> --region eu-west-1
   ```

2. **Deploy to correct runtimes**:
   ```bash
   # Deploy workflow agents to AgentCore
   python scripts/deploy_agentcore_agents.py --env dev
   
   # Deploy conversational agent to Bedrock
   python scripts/deploy_conversational_interface_agent.py --env dev
   ```

3. **Update any hardcoded references** to use correct agent invocation patterns

## Benefits of Correct Architecture

1. **Performance**: Agents run in their optimized runtime environments
2. **Scalability**: AgentCore handles workflow processing efficiently
3. **Maintainability**: Clear separation of concerns
4. **Cost Optimization**: Right-sized resources for each agent type
5. **Tool Integration**: Proper access to runtime-specific capabilities

## Conclusion

The correct architecture separates workflow processing (AgentCore) from user interaction (Bedrock Agents), ensuring each agent runs in its optimal environment with proper tool access and performance characteristics.