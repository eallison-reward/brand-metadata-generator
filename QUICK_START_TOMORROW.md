# Quick Start Guide - Resume Work Tomorrow

**Date**: February 16, 2026  
**Task**: Complete AgentCore cloud deployment

---

## 🎯 3-Step Process

### Step 1: Fix Script (15 minutes)

**File**: `scripts/deploy_agentcore_agents.py`  
**Function**: `deploy_agent_to_agentcore()` around line 150

**Add this code after the subprocess.run() call**:

```python
# Check for error indicators in output even if exit code is 0
if result.stderr and ("error" in result.stderr.lower() or "failed" in result.stderr.lower()):
    print(f"   ❌ Deployment failed with errors in stderr")
    print(f"   Error: {result.stderr.strip()}")
    return False

# Check for CodeBuild failures
if "COMPLETED" in result.stdout and "FAILED" in result.stdout:
    print(f"   ❌ CodeBuild container build failed")
    print(f"   Output: {result.stdout.strip()}")
    return False
```

**Test**:
```bash
python scripts/deploy_agentcore_agents.py --env dev --agent orchestrator
```

---

### Step 2: Copy Dockerfiles (5 minutes)

**Run this PowerShell script**:

```powershell
$agents = @(
    "data_transformation",
    "evaluator", 
    "metadata_production",
    "commercial_assessment",
    "confirmation",
    "tiebreaker",
    "feedback_processing",
    "learning_analytics"
)

foreach ($agent in $agents) {
    $targetDir = ".bedrock_agentcore/brand_metagen_$agent"
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force
    }
    Copy-Item ".bedrock_agentcore/brand_metagen_orchestrator/Dockerfile" "$targetDir/Dockerfile"
    Write-Host "✅ Copied Dockerfile to $targetDir"
}
```

---

### Step 3: Deploy All Agents (30-60 minutes)

**Option A: Cloud Deployment** (if CodeBuild works)
```bash
python scripts/deploy_agentcore_agents.py --env dev
```

**Option B: Local Deployment** (if CodeBuild fails)
```bash
python scripts/deploy_agentcore_agents.py --env dev --local
```

**Verify**:
```bash
& "C:\Users\eda\AppData\Roaming\Python\Python314\Scripts\agentcore.exe" status
```

---

## 🔍 If CodeBuild Still Fails

### Check Logs
1. Go to: https://eu-west-1.console.aws.amazon.com/codesuite/codebuild/projects/bedrock-agentcore-brand_metagen_orchestrator-builder/history
2. Click latest build
3. Look for error message in logs

### Common Issues
- **ARM64 incompatibility**: Check requirements.txt packages
- **Docker build fails**: Test locally with `docker build -f .bedrock_agentcore/brand_metagen_orchestrator/Dockerfile .`
- **Timeout**: Increase CodeBuild timeout

### Alternative: Switch to Direct Deploy
Edit `.bedrock_agentcore.yaml` and change for all agents:
```yaml
deployment_type: direct_code_deploy  # Change from "container"
```

Then redeploy:
```bash
python scripts/deploy_agentcore_agents.py --env dev
```

---

## 📚 Full Documentation

- `AGENTCORE_DEPLOYMENT_BEST_PRACTICES.md` - Complete technical details
- `AGENTCORE_DEPLOYMENT_HANDOVER.md` - Status summary
- `docs/AGENT_ARCHITECTURE_CLARIFICATION.md` - Architecture explanation

---

## ✅ Success Criteria

You're done when:
- [ ] All 9 agents show in `agentcore status`
- [ ] No errors in deployment output
- [ ] Can invoke test agent successfully

---

**Estimated Time**: 1-2 hours total  
**Difficulty**: Medium (script fix is straightforward, CodeBuild may need investigation)
