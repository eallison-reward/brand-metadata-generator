# AgentCore Deployment - Best Practices & Session Handover

**Date**: February 16, 2026  
**Status**: In Progress - Cloud Deployment Failing  
**Priority**: HIGH - Fix deployment script error handling and complete cloud deployment

---

## 🎯 IMMEDIATE ACTION ITEMS FOR NEXT SESSION

### 1. Fix Deployment Script Error Handling (CRITICAL)
**Problem**: Script shows errors but continues running instead of failing fast.

**Location**: `scripts/deploy_agentcore_agents.py`

**Required Changes**:
```python
# Add at the top of deploy_agent_to_agentcore() function:
def deploy_agent_to_agentcore(agent_name: str, env: str, dry_run: bool = False) -> bool:
    """Deploy a single agent to AgentCore using the CLI."""
    print(f"\n📝 Deploying {agent_name} to AgentCore...")
    
    try:
        # ... existing code ...
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,  # This will raise CalledProcessError on non-zero exit
            # ... rest of parameters ...
        )
        
        # ADD: Check for error indicators in output even if exit code is 0
        if result.stderr and ("error" in result.stderr.lower() or "failed" in result.stderr.lower()):
            print(f"   ❌ Deployment failed with errors in stderr")
            print(f"   Error: {result.stderr.strip()}")
            return False
        
        # ADD: Check for CodeBuild failures
        if "COMPLETED" in result.stdout and "FAILED" in result.stdout:
            print(f"   ❌ CodeBuild container build failed")
            print(f"   Output: {result.stdout.strip()}")
            return False
            
        print(f"   ✅ Agent deployed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Deployment failed: {e}")
        print(f"   Exit code: {e.returncode}")
        if e.stderr:
            print(f"   Error: {e.stderr.strip()}")
        if e.stdout:
            print(f"   Output: {e.stdout.strip()}")
        return False  # CRITICAL: Return False to stop execution
```

**Test Command**:
```bash
python scripts/deploy_agentcore_agents.py --env dev --agent orchestrator
```

### 2. Copy Dockerfiles to All Agent Directories
**Problem**: Only orchestrator has a Dockerfile. Other agents need it for container deployment.

**Working Dockerfile**: `.bedrock_agentcore/brand_metagen_orchestrator/Dockerfile`

**Commands to Run**:
```powershell
# Copy Dockerfile to all agent directories
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

### 3. Investigate CodeBuild Failure
**Problem**: Container builds fail in COMPLETED phase.

**Steps**:
1. Check CodeBuild logs in AWS Console:
   - URL: https://eu-west-1.console.aws.amazon.com/codesuite/codebuild/projects/bedrock-agentcore-brand_metagen_orchestrator-builder/history
   - Look for specific error messages in build logs

2. Common issues to check:
   - ARM64 compatibility of Python packages
   - Missing dependencies in requirements.txt
   - Docker build context issues
   - Network/timeout issues

3. If CodeBuild continues failing, consider alternative:
   ```bash
   # Change deployment_type in .bedrock_agentcore.yaml from "container" to "direct_code_deploy"
   # This deploys code directly without Docker container
   ```

---

## 📊 CURRENT STATE SUMMARY

### ✅ What's Working
- **Local Deployment**: Fully functional
  - Command: `python scripts/deploy_agentcore_agents.py --env dev --local`
  - Orchestrator agent tested and working at http://localhost:8080
  - Docker image builds successfully locally

- **Configuration**: Fully automated
  - No user prompts required
  - All 9 agents configured in `.bedrock_agentcore.yaml`
  - AgentCore CLI installed and accessible

- **AWS Resources**: Successfully created
  - Memory stores for 5 agents (orchestrator, data_transformation, evaluator, metadata_production, commercial_assessment)
  - IAM roles created
  - ECR repositories created
  - CodeBuild projects created

### ❌ What's Broken
- **Cloud Deployment**: CodeBuild container builds failing
  - Fails during COMPLETED phase
  - Script continues past errors instead of stopping
  - Root cause not yet identified

- **Missing Dockerfiles**: 6 agents missing Dockerfiles
  - Only orchestrator and brand_metagen_orchestrator have Dockerfiles
  - Need to copy to: data_transformation, evaluator, metadata_production, commercial_assessment, confirmation, tiebreaker, feedback_processing, learning_analytics

### ⚠️ Pending Tasks
- Fix deployment script error handling
- Copy Dockerfiles to all agents
- Investigate and fix CodeBuild failures
- Deploy all 9 agents to cloud
- Test agent connectivity and functionality
- Address conversational agent permissions issue (separate task)

---

## 🔧 TECHNICAL DETAILS

### AgentCore CLI Location
```
C:\Users\eda\AppData\Roaming\Python\Python314\Scripts\agentcore.exe
```

### Project Structure
```
brand_generator/
├── .bedrock_agentcore.yaml          # AgentCore configuration (all 9 agents)
├── scripts/
│   ├── deploy_agentcore_agents.py   # Main deployment script (NEEDS FIX)
│   ├── configure_agentcore.py       # Automated configuration generator
│   └── cleanup_incorrect_agents.py  # Cleanup script (already used)
├── agents/
│   ├── orchestrator/
│   │   └── agentcore_handler.py
│   ├── data_transformation/
│   │   └── agentcore_handler.py
│   └── ... (7 more agents)
└── .bedrock_agentcore/
    ├── brand_metagen_orchestrator/
    │   └── Dockerfile                # WORKING DOCKERFILE - COPY THIS
    └── ... (8 more agent directories - NEED DOCKERFILES)
```

### Agent List (9 Total)
1. orchestrator - ✅ Partially deployed (memory + IAM + ECR created, CodeBuild failing)
2. data_transformation - ✅ Partially deployed (memory + IAM + ECR created)
3. evaluator - ✅ Partially deployed (memory + IAM + ECR created)
4. metadata_production - ✅ Partially deployed (memory + IAM + ECR created)
5. commercial_assessment - ✅ Partially deployed (memory + IAM + ECR created)
6. confirmation - ⚠️ Not started
7. tiebreaker - ⚠️ Not started
8. feedback_processing - ⚠️ Not started
9. learning_analytics - ⚠️ Not started

### AWS Resources Created
```
Region: eu-west-1
Account: 536824473420

Memories:
- brand_metagen_orchestrator_mem-LQjcHg2hLl
- brand_metagen_data_transformation_mem-g3GodA4GMi
- brand_metagen_evaluator_mem-1uMIwd2NSR
- brand_metagen_metadata_production_mem-wazOj15oSC
- brand_metagen_commercial_assessment_mem-ICYBn2CgV3

IAM Roles:
- AmazonBedrockAgentCoreSDKRuntime-eu-west-1-2e18ac2b1e (orchestrator)
- AmazonBedrockAgentCoreSDKRuntime-eu-west-1-1e6cbd20ac (data_transformation)
- AmazonBedrockAgentCoreSDKRuntime-eu-west-1-2d9bc80181 (evaluator)
- AmazonBedrockAgentCoreSDKRuntime-eu-west-1-d928acba3b (metadata_production)
- AmazonBedrockAgentCoreSDKRuntime-eu-west-1-f6eaf0ca49 (commercial_assessment)

ECR Repositories:
- bedrock-agentcore-brand_metagen_orchestrator
- bedrock-agentcore-brand_metagen_data_transformation
- bedrock-agentcore-brand_metagen_evaluator
- bedrock-agentcore-brand_metagen_metadata_production
- bedrock-agentcore-brand_metagen_commercial_assessment

CodeBuild Projects:
- bedrock-agentcore-brand_metagen_orchestrator-builder (FAILING)
```

---

## 🚀 DEPLOYMENT COMMANDS

### Check Current Status
```bash
# Check AgentCore CLI status
& "C:\Users\eda\AppData\Roaming\Python\Python314\Scripts\agentcore.exe" status

# List configured agents
python scripts/configure_agentcore.py
```

### Local Deployment (WORKING - Use for Development)
```bash
# Deploy single agent locally
python scripts/deploy_agentcore_agents.py --env dev --agent orchestrator --local

# Deploy all agents locally
python scripts/deploy_agentcore_agents.py --env dev --local
```

### Cloud Deployment (BROKEN - Needs Fix)
```bash
# Deploy single agent to cloud
python scripts/deploy_agentcore_agents.py --env dev --agent orchestrator

# Deploy all agents to cloud (after fixing script)
python scripts/deploy_agentcore_agents.py --env dev
```

### Verification Commands
```bash
# Check agent status
& "C:\Users\eda\AppData\Roaming\Python\Python314\Scripts\agentcore.exe" status

# Test local agent
curl http://localhost:8080/health

# Check AWS resources
aws bedrock-agentcore list-memories --region eu-west-1
aws ecr describe-repositories --region eu-west-1 | findstr bedrock-agentcore
aws codebuild list-projects --region eu-west-1 | findstr bedrock-agentcore
```

---

## 🐛 KNOWN ISSUES & SOLUTIONS

### Issue 1: Script Continues Past Errors
**Symptom**: Deployment script shows errors but keeps running.

**Root Cause**: Insufficient error checking in subprocess calls.

**Solution**: Add error detection for:
- Non-zero exit codes (already handled by `check=True`)
- Error messages in stderr even with exit code 0
- CodeBuild failure indicators in stdout
- Return False immediately on any error

### Issue 2: CodeBuild Container Build Fails
**Symptom**: Build reaches COMPLETED phase but fails.

**Possible Causes**:
1. ARM64 package incompatibility
2. Missing dependencies
3. Docker build context issues
4. Network/timeout issues

**Solutions to Try**:
1. Check CodeBuild logs for specific error
2. Test Docker build locally: `docker build -f .bedrock_agentcore/brand_metagen_orchestrator/Dockerfile .`
3. Simplify Dockerfile (use basic Python image instead of UV)
4. Change to direct_code_deploy instead of container deployment

### Issue 3: Missing Dockerfiles
**Symptom**: Only 2 agents have Dockerfiles.

**Solution**: Copy working Dockerfile to all agent directories (see commands above).

---

## 📝 ARCHITECTURE NOTES

### Correct Architecture (Implemented)
- **Workflow Agents** (9 agents) → AgentCore Runtime (Strands API)
- **Conversational Agent** (1 agent) → Bedrock Agents (separate deployment)

### Previous Incorrect Architecture (Fixed)
- All agents were deployed to Bedrock Agents instead of AgentCore
- Cleanup completed: 5 incorrectly deployed agents removed

### Key Files
- `scripts/deploy_agentcore_agents.py` - Main deployment script
- `scripts/configure_agentcore.py` - Configuration generator
- `.bedrock_agentcore.yaml` - AgentCore configuration
- `.bedrock_agentcore/brand_metagen_orchestrator/Dockerfile` - Working Dockerfile template
- `docs/AGENT_ARCHITECTURE_CLARIFICATION.md` - Architecture documentation

---

## 🎓 LESSONS LEARNED

1. **Error Handling**: Always check both exit codes AND output content for errors
2. **Fail Fast**: Stop execution immediately on first error to save time
3. **Dockerfiles**: All agents need Dockerfiles for container deployment
4. **Local First**: Test locally before cloud deployment
5. **Automation**: Eliminate all interactive prompts to avoid user confusion
6. **Documentation**: Keep comprehensive handover docs for session continuity

---

## 📞 NEXT SESSION CHECKLIST

- [ ] Fix deployment script error handling (add error detection)
- [ ] Copy Dockerfiles to all 8 remaining agent directories
- [ ] Test deployment script with single agent
- [ ] Check CodeBuild logs for failure details
- [ ] Decide: Fix CodeBuild OR switch to direct_code_deploy
- [ ] Deploy all 9 agents to cloud
- [ ] Verify agent connectivity with `agentcore status`
- [ ] Test agent invocation
- [ ] Address conversational agent permissions (separate task)

---

**Last Updated**: February 16, 2026  
**Session Status**: Paused - Ready to resume with clear action items  
**Estimated Time to Complete**: 2-3 hours (assuming CodeBuild issue is straightforward)
