# Tomorrow's Quick Start Guide

**Date**: February 17, 2026  
**Status**: Ready to test and deploy remaining agents  
**Estimated Time**: 2-3 hours

---

## 🎯 Today's Goal

Deploy and test all 9 AgentCore workflow agents using the working Strands pattern.

---

## 📖 Essential Reading (5 minutes)

1. **STRANDS_AGENTCORE_SUCCESS_HANDOVER.md** - What we achieved yesterday
2. **docs/STRANDS_AGENTCORE_DEPLOYMENT_GUIDE.md** - The complete pattern

---

## ✅ Pre-Flight Checklist

```bash
# 1. Verify orchestrator is still working
agentcore status

# 2. Check AWS credentials
aws sts get-caller-identity

# 3. Verify project location
cd "C:\Users\eda\OneDrive - SPORTS LOYALTY CARD LTD\Projects\Insight\brand_generator"
```

---

## 🚀 Step 1: Test Orchestrator (15 minutes)

### Start a workflow execution

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-west-1:536824473420:stateMachine:brand_metagen_workflow_dev \
  --input '{"brandid": 230}' \
  --region eu-west-1
```

### Monitor execution

```bash
# Get execution ARN from above output, then:
aws stepfunctions describe-execution \
  --execution-arn <execution-arn> \
  --region eu-west-1

# Check Lambda logs
python scripts/check_lambda_logs.py --function brand_metagen_orchestrator_invoke_dev --minutes 10

# Check AgentCore logs
aws logs tail /aws/bedrock-agentcore/runtimes/brand_metagen_orchestrator-VVTBH860nM-DEFAULT \
  --log-stream-name-prefix "2026/02/17/[runtime-logs]" \
  --since 10m \
  --region eu-west-1
```

### Expected Results

- ✅ Workflow runs for meaningful time (not instant)
- ✅ Lambda invokes agent successfully
- ✅ Agent processes request (check CloudWatch logs)
- ✅ No AttributeError or RuntimeClientError

---

## 🚀 Step 2: Deploy Remaining Agents (60-90 minutes)

### Option A: Deploy All at Once (Faster)

```bash
python scripts/deploy_agentcore_agents.py --env dev
```

### Option B: Deploy One at a Time (Safer)

```bash
# Deploy in order of dependency
python scripts/deploy_agentcore_agents.py --env dev --agent data_transformation
python scripts/deploy_agentcore_agents.py --env dev --agent evaluator
python scripts/deploy_agentcore_agents.py --env dev --agent metadata_production
python scripts/deploy_agentcore_agents.py --env dev --agent commercial_assessment
python scripts/deploy_agentcore_agents.py --env dev --agent confirmation
python scripts/deploy_agentcore_agents.py --env dev --agent tiebreaker
python scripts/deploy_agentcore_agents.py --env dev --agent feedback_processing
python scripts/deploy_agentcore_agents.py --env dev --agent learning_analytics
```

### After Each Deployment

```bash
# Verify agent status
agentcore status

# Check for "Ready" status for each agent
```

---

## 🚀 Step 3: End-to-End Test (30 minutes)

### Run complete workflow

```bash
# Start workflow for brand 230
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-west-1:536824473420:stateMachine:brand_metagen_workflow_dev \
  --input '{"brandid": 230}' \
  --region eu-west-1
```

### Verify results

```bash
# Check generated_metadata table
aws athena start-query-execution \
  --query-string "SELECT * FROM generated_metadata WHERE brandid = 230" \
  --query-execution-context Database=brand_metadata_generator_db \
  --result-configuration OutputLocation=s3://brand-generator-rwrd-023-eu-west-1/athena-results/ \
  --region eu-west-1

# Check S3 for metadata file
aws s3 ls s3://brand-generator-rwrd-023-eu-west-1/metadata/brand_230.json

# Check DynamoDB for status
aws dynamodb get-item \
  --table-name brand_processing_status_dev \
  --key '{"brandid": {"N": "230"}}' \
  --region eu-west-1
```

---

## 🐛 Troubleshooting

### Agent Won't Deploy

1. Check handler structure matches orchestrator pattern
2. Verify `bedrock-agentcore>=0.1.0` in requirements.txt
3. Check Dockerfile CMD uses script path not module

### Agent Fails at Runtime

1. Check CloudWatch logs for specific error
2. Verify using `agent()` not `agent.invoke()`
3. Ensure `@app.entrypoint` decorator is present

### Quick Reference

```bash
# View agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/<agent-name>-DEFAULT \
  --log-stream-name-prefix "2026/02/17/[runtime-logs]" \
  --since 10m \
  --region eu-west-1

# View Lambda logs
python scripts/check_lambda_logs.py --function <function-name> --minutes 10

# Check agent status
agentcore status
```

---

## 📋 Success Checklist

- [ ] Orchestrator agent tested successfully
- [ ] All 9 agents deployed to AgentCore
- [ ] All agents show "Ready" status
- [ ] End-to-end workflow completes
- [ ] Metadata generated and stored
- [ ] No errors in CloudWatch logs

---

## 🎯 If Things Go Wrong

1. **Don't panic** - We have working pattern documented
2. **Check the guide** - `docs/STRANDS_AGENTCORE_DEPLOYMENT_GUIDE.md`
3. **Compare to orchestrator** - `agents/orchestrator/agentcore_handler.py`
4. **Check logs** - CloudWatch has the answers

---

## 📞 Key Resources

- **Pattern Guide**: `docs/STRANDS_AGENTCORE_DEPLOYMENT_GUIDE.md`
- **Reference Implementation**: `agents/orchestrator/agentcore_handler.py`
- **Success Handover**: `STRANDS_AGENTCORE_SUCCESS_HANDOVER.md`
- **Strands Docs**: https://strandsagents.com/latest/documentation/

---

## ⏱️ Time Estimates

- Test orchestrator: 15 minutes
- Deploy 8 agents: 60-90 minutes
- End-to-end test: 30 minutes
- **Total**: 2-3 hours

---

**Good luck! You've got this! 🚀**

The hard part (figuring out the pattern) is done.  
Now it's just execution and testing.
