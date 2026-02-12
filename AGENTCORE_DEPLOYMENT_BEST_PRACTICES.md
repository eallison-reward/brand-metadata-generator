# AgentCore Deployment Best Practices

**Purpose**: Comprehensive guide for deploying AI agents using AWS Bedrock AgentCore  
**Audience**: Developers building multi-agent systems  
**Based on**: Production deployment of 5-agent forecasting system

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Agent Implementation Patterns](#agent-implementation-patterns)
5. [Memory Integration](#memory-integration)
6. [Deployment Process](#deployment-process)
7. [Testing Strategies](#testing-strategies)
8. [Multi-Agent Coordination](#multi-agent-coordination)
9. [IAM and Permissions](#iam-and-permissions)
10. [Troubleshooting](#troubleshooting)
11. [Cost Optimization](#cost-optimization)

---

## Quick Start

### Prerequisites

```bash
# Install required tools
pip install bedrock-agentcore-starter-toolkit
pip install strands-agents strands-agents-tools

# Configure AWS credentials
aws configure
# Set region to eu-west-1 (or your preferred region)
```

### Create Your First Agent (5 minutes)

```bash
# 1. Scaffold agent project
agentcore create --non-interactive \
  --project-name my_agent \
  --template basic \
  --agent-framework Strands \
  --model-provider Bedrock

cd my_agent

# 2. Test locally
agentcore dev

# In another terminal:
agentcore invoke --dev '{"prompt": "Hello!"}'

# 3. Deploy to AWS
agentcore configure --entrypoint src/main.py --non-interactive
agentcore launch

# 4. Test deployed agent
agentcore invoke '{"prompt": "Hello!"}'
```

---
## Project Structure

### Recommended Directory Layout

```
my-agent-system/
├── agents/
│   ├── orchestration/          # Main coordinator agent
│   │   ├── agentcore_handler.py
│   │   ├── models.py
│   │   ├── memory_manager.py
│   │   └── tools/
│   ├── predictive/             # Specialized agents
│   │   ├── agentcore_handler.py
│   │   ├── forecast_generator.py
│   │   └── tools/
│   └── insight/
│       ├── agentcore_handler.py
│       └── tools/
├── shared/
│   ├── storage/                # Shared data access
│   ├── monitoring/             # Logging and metrics
│   ├── auth/                   # Authentication
│   └── models/                 # Common data models
├── infrastructure/
│   ├── agentcore/              # Agent deployment scripts
│   ├── step_functions/         # Workflow orchestration
│   └── monitoring/             # CloudWatch dashboards
├── tests/
│   ├── unit/
│   └── integration/
└── docs/
```

### Key Principles

- **Separation of concerns**: Each agent has its own directory
- **Shared utilities**: Common code in `shared/` to avoid duplication
- **Infrastructure as code**: All deployment scripts version controlled
- **Test coverage**: Unit and integration tests for all agents

---

## Development Workflow

### Local Development

```bash
# 1. Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run agent locally
agentcore dev --entrypoint agents/orchestration/agentcore_handler.py

# 4. Test with sample input
agentcore invoke --dev '{
  "prompt": "Generate forecast for next quarter",
  "context": {"user_id": "test-user"}
}'
```

### Development Best Practices

1. **Use local mode first**: Test all changes locally before deploying
2. **Mock external dependencies**: Use mocks for S3, DynamoDB during local testing
3. **Version control everything**: Including deployment scripts and configs
4. **Use environment variables**: Never hardcode credentials or region-specific values

### Iterative Development Cycle

```bash
# Make changes to agent code
vim agents/orchestration/agentcore_handler.py

# Test locally
agentcore invoke --dev '{"prompt": "test"}'

# Run unit tests
pytest tests/unit/

# Deploy to dev environment
agentcore launch --alias dev

# Test deployed version
agentcore invoke --alias dev '{"prompt": "test"}'

# Promote to production
agentcore launch --alias prod
```

---

## Agent Implementation Patterns

### Handler Structure

```python
# agents/my_agent/agentcore_handler.py
from strands import Agent
from strands.tools import tool

# Initialize agent
agent = Agent(
    name="MyAgent",
    instructions="""You are a specialized agent that...""",
    model="anthropic.claude-3-5-sonnet-20241022-v2:0"
)

# Define tools
@tool
def my_tool(param: str) -> dict:
    """Tool description for the agent."""
    # Implementation
    return {"result": "success"}

# Register tools
agent.add_tools([my_tool])

# Handler function (required by AgentCore)
def handler(event, context):
    """AgentCore entry point."""
    prompt = event.get("prompt", "")
    
    # Invoke agent
    response = agent.invoke(prompt)
    
    return {
        "statusCode": 200,
        "body": response
    }
```

### Tool Design Patterns

**1. Simple Data Retrieval**
```python
@tool
def get_forecast_data(forecast_id: str) -> dict:
    """Retrieve forecast data by ID."""
    storage = ForecastStorage()
    return storage.get(forecast_id)
```

**2. Complex Operations with Error Handling**
```python
@tool
def generate_forecast(data: dict, method: str) -> dict:
    """Generate forecast using specified method."""
    try:
        generator = ForecastGenerator()
        result = generator.generate(data, method)
        return {"success": True, "forecast": result}
    except Exception as e:
        logger.error(f"Forecast generation failed: {e}")
        return {"success": False, "error": str(e)}
```

**3. Async Operations**
```python
@tool
def start_etl_job(job_config: dict) -> dict:
    """Start ETL job asynchronously."""
    job_id = etl_manager.start_job(job_config)
    return {
        "job_id": job_id,
        "status": "started",
        "check_status_with": "get_job_status"
    }
```

### Agent Communication Patterns

**Direct Invocation** (for synchronous operations):
```python
from strands import Agent

def invoke_sub_agent(prompt: str) -> str:
    """Invoke another agent directly."""
    sub_agent = Agent.from_arn("arn:aws:bedrock:...")
    response = sub_agent.invoke(prompt)
    return response
```

**Step Functions** (for complex workflows):
```python
import boto3

def start_workflow(input_data: dict) -> str:
    """Start Step Functions workflow."""
    sfn = boto3.client('stepfunctions')
    response = sfn.start_execution(
        stateMachineArn='arn:aws:states:...',
        input=json.dumps(input_data)
    )
    return response['executionArn']
```

---

## Memory Integration

### Setting Up Agent Memory

```bash
# 1. Create memory resource
agentcore memory create \
  --agent-name orchestration-agent \
  --memory-type dynamodb \
  --ttl-days 30

# 2. Verify memory configuration
agentcore memory describe --agent-name orchestration-agent
```

### Using Memory in Agents

```python
from strands import Agent

agent = Agent(
    name="OrchestrationAgent",
    instructions="You are an orchestration agent with memory...",
    memory_enabled=True,
    memory_config={
        "type": "dynamodb",
        "table_name": "agent-memory",
        "ttl_days": 30
    }
)

# Memory is automatically managed by Strands
# Agent will remember context across invocations
```

### Memory Patterns

**Session Memory** (short-term):
```python
# Automatically stored per session
agent.invoke("Remember that user prefers ARIMA method")
# Later in same session:
agent.invoke("What method does user prefer?")
# Agent responds: "ARIMA method"
```

**Persistent Memory** (long-term):
```python
@tool
def store_user_preference(user_id: str, preference: dict) -> dict:
    """Store user preference in persistent storage."""
    memory_manager = MemoryManager()
    memory_manager.store(
        key=f"user:{user_id}:preferences",
        value=preference,
        ttl_days=365
    )
    return {"stored": True}
```

---

## Deployment Process

### Pre-Deployment Checklist

- [ ] All tests passing locally
- [ ] Environment variables configured
- [ ] IAM roles and policies created
- [ ] Dependencies listed in requirements.txt
- [ ] Deployment scripts tested
- [ ] Monitoring and alarms configured

### Deployment Steps

**1. Configure Agent**
```bash
agentcore configure \
  --entrypoint agents/orchestration/agentcore_handler.py \
  --agent-name orchestration-agent \
  --model anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --timeout 300 \
  --memory-size 1024 \
  --non-interactive
```

**2. Deploy to Development**
```bash
agentcore launch --alias dev
```

**3. Test Deployed Agent**
```bash
agentcore invoke --alias dev '{
  "prompt": "Test deployment",
  "context": {"environment": "dev"}
}'
```

**4. Deploy to Production**
```bash
# Create production alias
agentcore launch --alias prod

# Update production with new version
agentcore update --alias prod --version 2
```

### Deployment Automation

**Python Deployment Script**:
```python
# infrastructure/deploy_agent.py
import subprocess
import sys

def deploy_agent(agent_name, alias="dev"):
    """Deploy agent to specified environment."""
    
    # Configure
    config_cmd = [
        "agentcore", "configure",
        "--entrypoint", f"agents/{agent_name}/agentcore_handler.py",
        "--agent-name", agent_name,
        "--non-interactive"
    ]
    subprocess.run(config_cmd, check=True)
    
    # Launch
    launch_cmd = ["agentcore", "launch", "--alias", alias]
    result = subprocess.run(launch_cmd, check=True, capture_output=True)
    
    print(f"✓ Deployed {agent_name} to {alias}")
    return result

if __name__ == "__main__":
    agent_name = sys.argv[1]
    alias = sys.argv[2] if len(sys.argv) > 2 else "dev"
    deploy_agent(agent_name, alias)
```

**PowerShell Deployment Script**:
```powershell
# infrastructure/deploy-agent.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$AgentName,
    
    [Parameter(Mandatory=$false)]
    [string]$Alias = "dev"
)

Write-Host "Deploying $AgentName to $Alias..."

# Configure
agentcore configure `
    --entrypoint "agents/$AgentName/agentcore_handler.py" `
    --agent-name $AgentName `
    --non-interactive

if ($LASTEXITCODE -ne 0) {
    Write-Error "Configuration failed"
    exit 1
}

# Launch
agentcore launch --alias $Alias

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Successfully deployed $AgentName to $Alias" -ForegroundColor Green
}
```

### Multi-Agent Deployment

```bash
# Deploy all agents in sequence
./infrastructure/deploy-all-agents.sh dev

# Or deploy specific agents
./infrastructure/deploy-agent.sh orchestration dev
./infrastructure/deploy-agent.sh predictive dev
./infrastructure/deploy-agent.sh insight dev
```

---

## Testing Strategies

### Unit Testing

```python
# tests/unit/test_forecast_generator.py
import pytest
from agents.predictive.forecast_generator import ForecastGenerator

def test_forecast_generation():
    """Test basic forecast generation."""
    generator = ForecastGenerator()
    data = {"values": [1, 2, 3, 4, 5]}
    
    result = generator.generate(data, method="arima")
    
    assert result["success"] is True
    assert "forecast" in result
    assert len(result["forecast"]) > 0

def test_forecast_with_invalid_data():
    """Test error handling with invalid data."""
    generator = ForecastGenerator()
    data = {"values": []}
    
    result = generator.generate(data, method="arima")
    
    assert result["success"] is False
    assert "error" in result
```

### Integration Testing

```python
# tests/integration/test_agent_workflow.py
import pytest
from strands import Agent

@pytest.fixture
def orchestration_agent():
    """Create orchestration agent for testing."""
    return Agent.from_arn(
        "arn:aws:bedrock:eu-west-1:123456789:agent/test-agent"
    )

def test_end_to_end_forecast(orchestration_agent):
    """Test complete forecast workflow."""
    prompt = "Generate forecast for product A, next 30 days"
    
    response = orchestration_agent.invoke(prompt)
    
    assert "forecast" in response.lower()
    assert "30 days" in response.lower()

def test_agent_memory_persistence(orchestration_agent):
    """Test that agent remembers context."""
    # First interaction
    orchestration_agent.invoke("My preferred method is ARIMA")
    
    # Second interaction
    response = orchestration_agent.invoke("What's my preferred method?")
    
    assert "arima" in response.lower()
```

### Load Testing

```python
# tests/performance/test_agent_load.py
import concurrent.futures
from strands import Agent

def invoke_agent(prompt):
    """Single agent invocation."""
    agent = Agent.from_arn("arn:aws:bedrock:...")
    return agent.invoke(prompt)

def test_concurrent_requests():
    """Test agent under concurrent load."""
    prompts = ["Test prompt"] * 50
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(invoke_agent, p) for p in prompts]
        results = [f.result() for f in futures]
    
    assert len(results) == 50
    assert all(r is not None for r in results)
```

---

## Multi-Agent Coordination

### Orchestration Patterns

**1. Sequential Execution**
```python
@tool
def execute_forecast_workflow(request: dict) -> dict:
    """Execute agents in sequence."""
    
    # Step 1: Data preparation
    data_agent = Agent.from_arn("arn:aws:bedrock:...data-agent")
    prepared_data = data_agent.invoke(f"Prepare data for {request}")
    
    # Step 2: Forecast generation
    forecast_agent = Agent.from_arn("arn:aws:bedrock:...forecast-agent")
    forecast = forecast_agent.invoke(f"Generate forecast: {prepared_data}")
    
    # Step 3: Analysis
    insight_agent = Agent.from_arn("arn:aws:bedrock:...insight-agent")
    insights = insight_agent.invoke(f"Analyze forecast: {forecast}")
    
    return {
        "data": prepared_data,
        "forecast": forecast,
        "insights": insights
    }
```

**2. Parallel Execution**
```python
import concurrent.futures

@tool
def execute_parallel_analysis(data: dict) -> dict:
    """Execute multiple agents in parallel."""
    
    agents = {
        "statistical": Agent.from_arn("arn:...statistical-agent"),
        "ml": Agent.from_arn("arn:...ml-agent"),
        "market": Agent.from_arn("arn:...market-agent")
    }
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            name: executor.submit(agent.invoke, f"Analyze: {data}")
            for name, agent in agents.items()
        }
        
        results = {
            name: future.result()
            for name, future in futures.items()
        }
    
    return results
```

**3. Step Functions Orchestration**
```json
{
  "Comment": "Multi-agent forecast workflow",
  "StartAt": "ValidateInput",
  "States": {
    "ValidateInput": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:validate",
      "Next": "InvokeDataAgent"
    },
    "InvokeDataAgent": {
      "Type": "Task",
      "Resource": "arn:aws:bedrock:...:agent/data-agent",
      "Next": "ParallelForecasting"
    },
    "ParallelForecasting": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "ARIMAForecast",
          "States": {
            "ARIMAForecast": {
              "Type": "Task",
              "Resource": "arn:aws:bedrock:...:agent/arima-agent",
              "End": true
            }
          }
        },
        {
          "StartAt": "MLForecast",
          "States": {
            "MLForecast": {
              "Type": "Task",
              "Resource": "arn:aws:bedrock:...:agent/ml-agent",
              "End": true
            }
          }
        }
      ],
      "Next": "AggregateResults"
    },
    "AggregateResults": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:aggregate",
      "End": true
    }
  }
}
```

### Communication Best Practices

1. **Use structured data**: Pass JSON between agents, not free text
2. **Include context**: Always pass relevant context (user_id, session_id, etc.)
3. **Handle failures gracefully**: Implement retry logic and fallbacks
4. **Log all interactions**: Track agent-to-agent communication for debugging

---

## IAM and Permissions

### Required IAM Policies

**Agent Execution Role**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeAgent"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/agent-memory-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-agent-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

**Deployment Role**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:CreateAgent",
        "bedrock:UpdateAgent",
        "bedrock:DeleteAgent",
        "bedrock:GetAgent"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::*:role/AgentCore*"
    }
  ]
}
```

### Security Best Practices

1. **Principle of least privilege**: Grant only necessary permissions
2. **Use resource-specific ARNs**: Avoid wildcards when possible
3. **Enable CloudTrail**: Log all API calls for audit
4. **Rotate credentials**: Use temporary credentials, rotate regularly
5. **Encrypt data**: Use KMS for sensitive data encryption

---

## Troubleshooting

### Common Issues

**1. Agent Not Responding**
```bash
# Check agent status
agentcore describe --agent-name my-agent

# View recent logs
agentcore logs --agent-name my-agent --tail 100

# Test with simple prompt
agentcore invoke '{"prompt": "hello"}'
```

**2. Memory Not Persisting**
```bash
# Verify memory configuration
agentcore memory describe --agent-name my-agent

# Check DynamoDB table
aws dynamodb describe-table --table-name agent-memory-my-agent

# Test memory manually
agentcore invoke '{"prompt": "Remember: test value 123"}'
agentcore invoke '{"prompt": "What did I ask you to remember?"}'
```

**3. Tool Execution Failures**
```python
# Add detailed logging to tools
import logging
logger = logging.getLogger(__name__)

@tool
def my_tool(param: str) -> dict:
    """Tool with detailed logging."""
    logger.info(f"Tool invoked with param: {param}")
    try:
        result = perform_operation(param)
        logger.info(f"Tool succeeded: {result}")
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Tool failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

**4. Timeout Issues**
```bash
# Increase agent timeout
agentcore configure \
  --agent-name my-agent \
  --timeout 600 \
  --non-interactive

agentcore update --agent-name my-agent
```

### Debugging Techniques

**Enable Verbose Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In agent handler
logger = logging.getLogger(__name__)
logger.debug(f"Received event: {event}")
logger.debug(f"Agent response: {response}")
```

**Use Local Testing**:
```bash
# Test locally with detailed output
agentcore invoke --dev --verbose '{
  "prompt": "test",
  "debug": true
}'
```

**Monitor CloudWatch Metrics**:
```bash
# View agent invocation metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=AgentName,Value=my-agent \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

---

## Cost Optimization

### Cost Factors

1. **Model invocations**: Charged per input/output token
2. **Agent runtime**: Lambda execution time
3. **Memory storage**: DynamoDB storage and throughput
4. **Data transfer**: S3 and inter-service data transfer

### Optimization Strategies

**1. Optimize Prompts**
```python
# Bad: Verbose prompt
prompt = """
You are a forecasting agent. Please analyze the following data
and generate a comprehensive forecast with detailed explanations
for each data point...
"""

# Good: Concise prompt
prompt = "Generate forecast for: {data}. Include: predictions, confidence."
```

**2. Use Caching**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_forecast_data(forecast_id: str) -> dict:
    """Cache frequently accessed data."""
    return storage.get(forecast_id)
```

**3. Batch Operations**
```python
@tool
def batch_forecast(items: list) -> dict:
    """Process multiple items in single invocation."""
    results = []
    for item in items:
        result = generate_forecast(item)
        results.append(result)
    return {"results": results}
```

**4. Set Memory TTL**
```python
# Configure memory with appropriate TTL
memory_config = {
    "type": "dynamodb",
    "ttl_days": 7  # Auto-delete old data
}
```

**5. Monitor and Alert**
```python
# infrastructure/monitoring/cost_alerts.py
import boto3

def create_cost_alarm(agent_name, threshold_usd):
    """Create CloudWatch alarm for cost threshold."""
    cloudwatch = boto3.client('cloudwatch')
    
    cloudwatch.put_metric_alarm(
        AlarmName=f'{agent_name}-cost-alarm',
        MetricName='EstimatedCharges',
        Namespace='AWS/Billing',
        Statistic='Maximum',
        Period=86400,  # 24 hours
        EvaluationPeriods=1,
        Threshold=threshold_usd,
        ComparisonOperator='GreaterThanThreshold',
        AlarmActions=['arn:aws:sns:...']
    )
```

### Cost Monitoring

```bash
# View cost breakdown
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# Track agent-specific costs (use tags)
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://cost-filter.json
```

---

## Additional Resources

### Documentation
- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Strands SDK Documentation](https://github.com/awslabs/strands)
- [AgentCore Starter Toolkit](https://github.com/awslabs/bedrock-agentcore-starter-toolkit)

### Example Projects
- Production forecasting system (this project)
- Multi-agent customer service system
- Data analysis pipeline with agents

### Community
- AWS Bedrock Community Forum
- GitHub Discussions
- Stack Overflow (tag: aws-bedrock)

---

**Document Version**: 1.0  
**Last Updated**: February 2026  
**Maintained By**: Production Forecasting Team
