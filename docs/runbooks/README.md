# Operational Runbooks

This directory contains operational runbooks for the Brand Metadata Generator system. These runbooks provide step-by-step procedures for common operational tasks, troubleshooting, and system management.

## Overview

The Brand Metadata Generator is a multi-agent system built on AWS Bedrock AgentCore that automatically generates brand metadata (regex patterns and MCCID lists) for transaction classification. The system includes human-in-the-loop feedback processing, learning analytics, and automated escalation procedures.

## Runbook Index

### 1. [Feedback Processing Runbook](FEEDBACK_PROCESSING_RUNBOOK.md)

**Purpose**: Manage the human-in-the-loop feedback workflow

**Contents**:
- Daily feedback review workflow
- Feedback best practices
- Iteration management
- Monitoring feedback processing
- Common issues and resolutions
- Escalation procedures
- Performance optimization

**When to Use**:
- Daily operations and feedback review
- Troubleshooting feedback processing issues
- Managing high iteration counts
- Optimizing feedback quality

### 2. [Escalation Procedures Runbook](ESCALATION_PROCEDURES_RUNBOOK.md)

**Purpose**: Handle brands that cannot be processed automatically

**Contents**:
- Escalation triggers (automatic and manual)
- Escalation levels (operational, engineering, product)
- Escalation process (identify, triage, investigate, resolve)
- Resolution procedures (manual metadata, data correction, brand splitting, algorithm updates)
- Escalation tracking and reporting

**When to Use**:
- Brand reaches iteration limit
- Processing failures occur
- Ambiguous brand names identified
- Systematic issues discovered
- Manual intervention required

### 3. [MCP Troubleshooting Runbook](MCP_TROUBLESHOOTING_RUNBOOK.md)

**Purpose**: Troubleshoot Model Context Protocol (MCP) integration issues

**Contents**:
- MCP architecture overview
- Common issues (server not starting, tool invocation failures, Athena query failures, slow response times, cache inconsistencies)
- Diagnostic procedures
- Resolution procedures
- Performance optimization

**When to Use**:
- Commercial Assessment Agent failures
- Brand validation issues
- MCP server errors
- Slow brand validation
- Cache problems

### 4. [Learning Analytics Runbook](LEARNING_ANALYTICS_RUNBOOK.md)

**Purpose**: Interpret learning analytics data and drive improvements

**Contents**:
- Analytics overview
- Key metrics (approval rate, average iterations, escalation rate, confidence scores, improvement rate, false positive/negative rates)
- Report interpretation (daily, weekly, monthly)
- Trend analysis
- Action planning

**When to Use**:
- Daily/weekly/monthly reporting
- Performance analysis
- Identifying improvement opportunities
- Strategic planning
- Measuring system effectiveness

## Quick Reference

### Daily Operations

**Morning Routine**:
1. Check CloudWatch dashboard for overnight alerts
2. Review Quick Suite for brands awaiting review
3. Process high-priority feedback
4. Check escalation queue

**Afternoon Routine**:
1. Review daily analytics report
2. Address any escalations
3. Monitor processing status
4. Update stakeholders on issues

**End of Day**:
1. Review day's metrics
2. Document any issues or learnings
3. Plan next day's priorities

### Weekly Operations

**Monday**:
1. Generate weekly analytics report
2. Review trends from previous week
3. Plan week's priorities
4. Update escalation status

**Friday**:
1. Review week's accomplishments
2. Close completed escalations
3. Document lessons learned
4. Prepare for next week

### Monthly Operations

**First Week**:
1. Generate monthly analytics report
2. Analyze trends and patterns
3. Identify systematic issues
4. Plan improvements

**Mid-Month**:
1. Review progress on improvements
2. Adjust plans as needed
3. Update documentation

**End of Month**:
1. Assess month's results
2. Document successes and challenges
3. Plan next month's priorities
4. Update stakeholders

## Common Scenarios

### Scenario 1: High Escalation Rate

**Symptoms**: Escalation rate >10%

**Runbooks to Use**:
1. [Learning Analytics Runbook](LEARNING_ANALYTICS_RUNBOOK.md) - Analyze escalation trends
2. [Escalation Procedures Runbook](ESCALATION_PROCEDURES_RUNBOOK.md) - Review escalation reasons
3. [Feedback Processing Runbook](FEEDBACK_PROCESSING_RUNBOOK.md) - Improve feedback quality

**Actions**:
- Analyze common escalation reasons
- Identify systematic issues
- Plan algorithm improvements
- Update agent instructions

### Scenario 2: Poor Metadata Quality

**Symptoms**: Low approval rate, high iteration counts

**Runbooks to Use**:
1. [Learning Analytics Runbook](LEARNING_ANALYTICS_RUNBOOK.md) - Analyze quality metrics
2. [Feedback Processing Runbook](FEEDBACK_PROCESSING_RUNBOOK.md) - Review feedback patterns
3. [Escalation Procedures Runbook](ESCALATION_PROCEDURES_RUNBOOK.md) - Escalate systematic issues

**Actions**:
- Review feedback for common issues
- Analyze false positive/negative rates
- Update metadata generation algorithms
- Improve data quality

### Scenario 3: MCP Failures

**Symptoms**: Commercial Assessment Agent errors, brand validation failures

**Runbooks to Use**:
1. [MCP Troubleshooting Runbook](MCP_TROUBLESHOOTING_RUNBOOK.md) - Diagnose and resolve MCP issues
2. [Escalation Procedures Runbook](ESCALATION_PROCEDURES_RUNBOOK.md) - Escalate if needed

**Actions**:
- Test MCP server connectivity
- Check Athena permissions
- Verify cache functionality
- Restart MCP server if needed

### Scenario 4: Slow Processing

**Symptoms**: Long processing times, timeouts

**Runbooks to Use**:
1. [Feedback Processing Runbook](FEEDBACK_PROCESSING_RUNBOOK.md) - Optimize feedback processing
2. [MCP Troubleshooting Runbook](MCP_TROUBLESHOOTING_RUNBOOK.md) - Optimize MCP performance
3. [Learning Analytics Runbook](LEARNING_ANALYTICS_RUNBOOK.md) - Analyze performance trends

**Actions**:
- Profile slow operations
- Optimize Athena queries
- Improve caching
- Scale infrastructure if needed

## Emergency Procedures

### System Down

**Immediate Actions**:
1. Check CloudWatch alarms
2. Review Step Functions executions
3. Check agent status in Bedrock console
4. Review Lambda function errors
5. Escalate to engineering if needed

**Communication**:
- Notify stakeholders via email
- Update status page
- Provide regular updates

### Data Corruption

**Immediate Actions**:
1. Stop processing
2. Backup current data
3. Identify scope of corruption
4. Restore from backup if needed
5. Investigate root cause

**Communication**:
- Notify stakeholders immediately
- Document incident
- Provide recovery timeline

### Security Incident

**Immediate Actions**:
1. Follow security incident response plan
2. Isolate affected systems
3. Notify security team
4. Preserve evidence
5. Investigate and remediate

**Communication**:
- Follow security communication protocols
- Notify affected parties as required
- Document incident thoroughly

## Support Contacts

### Operations Team
- **Email**: operations@rewardinsight.com
- **Slack**: #brand-metadata-ops
- **On-Call**: [On-call rotation]

### Engineering Team
- **Email**: engineering@rewardinsight.com
- **Slack**: #brand-metadata-eng
- **Escalation**: [Engineering manager]

### Product Team
- **Email**: product@rewardinsight.com
- **Slack**: #brand-metadata-product
- **Escalation**: [Product manager]

### AWS Support
- **Support Level**: Enterprise
- **Case Creation**: AWS Console or CLI
- **Priority**: Based on severity

## Additional Resources

### Documentation
- [Production Monitoring Setup](../PRODUCTION_MONITORING_SETUP.md)
- [Agent Deployment Guide](../AGENT_DEPLOYMENT_GUIDE.md)
- [Quick Suite Setup Guide](../QUICK_SUITE_SETUP.md)
- [MCP Setup Guide](../MCP_SETUP_GUIDE.md)
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)

### Code Repositories
- **Main Repository**: [GitHub URL]
- **Infrastructure**: `infrastructure/`
- **Agents**: `agents/`
- **Scripts**: `scripts/`

### Monitoring and Dashboards
- **CloudWatch Dashboard**: brand-metagen-prod
- **Quick Suite**: AWS Bedrock Console → AgentCore → Quick Suite
- **Logs**: CloudWatch Logs (see monitoring setup)

### Training Materials
- [System Overview Presentation](../training/system_overview.pdf)
- [Feedback Best Practices](../training/feedback_best_practices.pdf)
- [Escalation Training](../training/escalation_training.pdf)

## Runbook Maintenance

### Review Schedule
- **Quarterly**: Review all runbooks for accuracy
- **After Incidents**: Update based on lessons learned
- **After Changes**: Update when system changes

### Update Process
1. Identify needed updates
2. Draft changes
3. Review with team
4. Test procedures
5. Update documentation
6. Communicate changes

### Version Control
- All runbooks are version controlled in Git
- Changes require pull request and review
- Major changes require approval from operations lead

## Feedback

Have suggestions for improving these runbooks? Contact the operations team or submit a pull request.

**Last Updated**: 2026-02-14
**Version**: 1.0
**Maintained By**: Operations Team
