# Strands + AgentCore Cheat Sheet

**Quick Reference for Deploying Strands Agents to AWS Bedrock AgentCore**

---

## ✅ The Working Pattern

### 1. requirements.txt
```txt
strands-agents
bedrock-agentcore>=0.1.0  # CRITICAL!
```

### 2. Agent Handler Structure
```python
from strands import Agent
from strands.tools import tool
from typing import Dict, Any
from bedrock_agentcore.runtime import BedrockAgentCoreApp  # CRITICAL!

# Define tools with @tool decorator
@tool
def my_tool(param: str) -> dict:
    return {"result": param}

# Create Strands agent
agent = Agent(
    name="MyAgent",
    system_prompt="You are a helpful agent",
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
    tools=[my_tool]
)

# Wrap with BedrockAgentCoreApp - CRITICAL!
app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """AgentCore entry point"""
    prompt = payload.get("prompt", "")
    
    # Use agent() not agent.invoke() - CRITICAL!
    response = agent(prompt)
    
    return {"result": str(response)}

# Legacy handler
def handler(event, context):
    return invoke(event)

# Enable script execution - CRITICAL!
if __name__ == "__main__":
    app.run()
```

### 3. Dockerfile
```dockerfile
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt requirements.txt
RUN uv pip install -r requirements.txt
RUN uv pip install aws-opentelemetry-distro==0.12.2

# Copy code
COPY . .

# Run as SCRIPT not module - CRITICAL!
CMD ["opentelemetry-instrument", "python", "agents/my_agent/agentcore_handler.py"]
```

---

## 🚫 Common Mistakes

| ❌ WRONG | ✅ RIGHT |
|---------|---------|
| `agent.invoke(prompt)` | `agent(prompt)` |
| No BedrockAgentCoreApp | `app = BedrockAgentCoreApp()` |
| `def handler(event, context)` | `@app.entrypoint def invoke(payload)` |
| `CMD ["python", "-m", "module"]` | `CMD ["python", "path/to/script.py"]` |
| Missing bedrock-agentcore | Add to requirements.txt |

---

## 🔧 Deployment Commands

```bash
# Deploy single agent
python scripts/deploy_agentcore_agents.py --env dev --agent orchestrator

# Deploy all agents
python scripts/deploy_agentcore_agents.py --env dev

# Check status
agentcore status

# View logs
aws logs tail /aws/bedrock-agentcore/runtimes/<agent-name>-DEFAULT \
  --log-stream-name-prefix "2026/02/17/[runtime-logs]" \
  --since 10m \
  --region eu-west-1
```

---

## 🐛 Troubleshooting

### Error: "AttributeError: 'Agent' object has no attribute 'invoke'"
**Fix**: Change `agent.invoke()` to `agent()`

### Error: "RuntimeClientError: An error occurred when starting the runtime"
**Fix**: Add BedrockAgentCoreApp wrapper and @app.entrypoint decorator

### Error: Module import warnings
**Fix**: Change Dockerfile CMD to run as script not module

### Agent shows "Ready" but fails when invoked
**Fix**: Check CloudWatch logs for actual error, likely missing wrapper or wrong API

---

## 📚 Quick Links

- **Full Guide**: `docs/STRANDS_AGENTCORE_DEPLOYMENT_GUIDE.md`
- **Reference Code**: `agents/orchestrator/agentcore_handler.py`
- **Strands Docs**: https://strandsagents.com/latest/documentation/

---

## ✅ Deployment Checklist

- [ ] Added `bedrock-agentcore>=0.1.0` to requirements.txt
- [ ] Imported `BedrockAgentCoreApp`
- [ ] Created `app = BedrockAgentCoreApp()` instance
- [ ] Wrapped handler with `@app.entrypoint`
- [ ] Changed function name to `invoke(payload)`
- [ ] Using `agent()` not `agent.invoke()`
- [ ] Added `if __name__ == "__main__": app.run()`
- [ ] Dockerfile CMD runs as script
- [ ] Deployed with deploy script
- [ ] Verified with `agentcore status`
- [ ] Tested invocation

---

**Keep this open while deploying agents!**
