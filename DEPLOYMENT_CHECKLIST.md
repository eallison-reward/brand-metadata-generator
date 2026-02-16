# AgentCore Deployment Checklist

**Date**: February 16, 2026  
**Objective**: Deploy all 9 workflow agents to AWS Bedrock AgentCore

---

## 📋 Pre-Deployment Checks

- [x] AgentCore CLI installed and accessible
- [x] AWS credentials configured
- [x] `.bedrock_agentcore.yaml` configuration file created
- [x] All agent handlers exist in `agents/` directory
- [x] Local deployment tested and working
- [ ] Deployment script error handling fixed
- [ ] Dockerfiles copied to all agent directories

---

## 🔧 Script Fixes

### Fix 1: Error Detection in deploy_agent_to_agentcore()
- [ ] Open `scripts/deploy_agentcore_agents.py`
- [ ] Locate `deploy_agent_to_agentcore()` function (around line 150)
- [ ] Add stderr error detection after subprocess.run()
- [ ] Add CodeBuild failure detection
- [ ] Test with single agent deployment
- [ ] Verify script stops on error

**Test Command**: `python scripts/deploy_agentcore_agents.py --env dev --agent orchestrator`

---

## 📦 Dockerfile Distribution

### Copy Dockerfiles to All Agents
- [ ] Run PowerShell script to copy Dockerfiles
- [ ] Verify Dockerfile exists in `.bedrock_agentcore/brand_metagen_data_transformation/`
- [ ] Verify Dockerfile exists in `.bedrock_agentcore/brand_metagen_evaluator/`
- [ ] Verify Dockerfile exists in `.bedrock_agentcore/brand_metagen_metadata_production/`
- [ ] Verify Dockerfile exists in `.bedrock_agentcore/brand_metagen_commercial_assessment/`
- [ ] Verify Dockerfile exists in `.bedrock_agentcore/brand_metagen_confirmation/`
- [ ] Verify Dockerfile exists in `.bedrock_agentcore/brand_metagen_tiebreaker/`
- [ ] Verify Dockerfile exists in `.bedrock_agentcore/brand_metagen_feedback_processing/`
- [ ] Verify Dockerfile exists in `.bedrock_agentcore/brand_metagen_learning_analytics/`

---

## 🚀 Agent Deployment

### Agent 1: orchestrator
- [x] Memory created: `brand_metagen_orchestrator_mem-LQjcHg2hLl`
- [x] IAM role created: `AmazonBedrockAgentCoreSDKRuntime-eu-west-1-2e18ac2b1e`
- [x] ECR repository created: `bedrock-agentcore-brand_metagen_orchestrator`
- [x] CodeBuild project created: `bedrock-agentcore-brand_metagen_orchestrator-builder`
- [ ] Container build successful
- [ ] Agent deployed to AgentCore runtime
- [ ] Agent appears in `agentcore status`

### Agent 2: data_transformation
- [x] Memory created: `brand_metagen_data_transformation_mem-g3GodA4GMi`
- [x] IAM role created: `AmazonBedrockAgentCoreSDKRuntime-eu-west-1-1e6cbd20ac`
- [x] ECR repository created: `bedrock-agentcore-brand_metagen_data_transformation`
- [ ] CodeBuild project created
- [ ] Container build successful
- [ ] Agent deployed to AgentCore runtime
- [ ] Agent appears in `agentcore status`

### Agent 3: evaluator
- [x] Memory created: `brand_metagen_evaluator_mem-1uMIwd2NSR`
- [x] IAM role created: `AmazonBedrockAgentCoreSDKRuntime-eu-west-1-2d9bc80181`
- [x] ECR repository created: `bedrock-agentcore-brand_metagen_evaluator`
- [ ] CodeBuild project created
- [ ] Container build successful
- [ ] Agent deployed to AgentCore runtime
- [ ] Agent appears in `agentcore status`

### Agent 4: metadata_production
- [x] Memory created: `brand_metagen_metadata_production_mem-wazOj15oSC`
- [x] IAM role created: `AmazonBedrockAgentCoreSDKRuntime-eu-west-1-d928acba3b`
- [x] ECR repository created: `bedrock-agentcore-brand_metagen_metadata_production`
- [ ] CodeBuild project created
- [ ] Container build successful
- [ ] Agent deployed to AgentCore runtime
- [ ] Agent appears in `agentcore status`

### Agent 5: commercial_assessment
- [x] Memory created: `brand_metagen_commercial_assessment_mem-ICYBn2CgV3`
- [x] IAM role created: `AmazonBedrockAgentCoreSDKRuntime-eu-west-1-f6eaf0ca49`
- [x] ECR repository created: `bedrock-agentcore-brand_metagen_commercial_assessment`
- [ ] CodeBuild project created
- [ ] Container build successful
- [ ] Agent deployed to AgentCore runtime
- [ ] Agent appears in `agentcore status`

### Agent 6: confirmation
- [ ] Memory created
- [ ] IAM role created
- [ ] ECR repository created
- [ ] CodeBuild project created
- [ ] Container build successful
- [ ] Agent deployed to AgentCore runtime
- [ ] Agent appears in `agentcore status`

### Agent 7: tiebreaker
- [ ] Memory created
- [ ] IAM role created
- [ ] ECR repository created
- [ ] CodeBuild project created
- [ ] Container build successful
- [ ] Agent deployed to AgentCore runtime
- [ ] Agent appears in `agentcore status`

### Agent 8: feedback_processing
- [ ] Memory created
- [ ] IAM role created
- [ ] ECR repository created
- [ ] CodeBuild project created
- [ ] Container build successful
- [ ] Agent deployed to AgentCore runtime
- [ ] Agent appears in `agentcore status`

### Agent 9: learning_analytics
- [ ] Memory created
- [ ] IAM role created
- [ ] ECR repository created
- [ ] CodeBuild project created
- [ ] Container build successful
- [ ] Agent deployed to AgentCore runtime
- [ ] Agent appears in `agentcore status`

---

## ✅ Verification

### AgentCore Status Check
- [ ] Run: `agentcore status`
- [ ] Verify all 9 agents listed
- [ ] Check agent status is "ACTIVE" or "READY"

### Test Agent Invocation
- [ ] Invoke orchestrator agent with test payload
- [ ] Check CloudWatch logs for agent activity
- [ ] Verify agent responds correctly

### AWS Resources Verification
- [ ] All 9 memories exist in Bedrock AgentCore
- [ ] All 9 IAM roles exist
- [ ] All 9 ECR repositories exist
- [ ] All 9 CodeBuild projects exist (if using container deployment)

---

## 🐛 Troubleshooting

### If CodeBuild Fails
- [ ] Check CodeBuild logs in AWS Console
- [ ] Identify specific error message
- [ ] Test Docker build locally
- [ ] Consider switching to direct_code_deploy

### If Script Shows Errors
- [ ] Verify error handling code was added
- [ ] Check that script stops on first error
- [ ] Review error message for root cause

### If Agent Doesn't Appear in Status
- [ ] Check CloudWatch logs for deployment errors
- [ ] Verify IAM permissions
- [ ] Check agent configuration in `.bedrock_agentcore.yaml`

---

## 📊 Progress Tracking

**Total Agents**: 9  
**Completed**: 0  
**In Progress**: 5 (partial AWS resources)  
**Not Started**: 4

**Estimated Time Remaining**: 1.5-2 hours

---

## 🎯 Success Criteria

Deployment is successful when:
- [ ] All 9 agents appear in `agentcore status`
- [ ] No errors in deployment output
- [ ] Can invoke test agent successfully
- [ ] CloudWatch logs show agent activity

---

**Last Updated**: February 16, 2026  
**Next Update**: After completing deployment
