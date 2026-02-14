# Escalation Procedures Runbook

This runbook defines escalation procedures for the Brand Metadata Generator system, covering when to escalate, how to escalate, and how to resolve escalated issues.

## Overview

Escalation occurs when automated processing cannot successfully generate acceptable brand metadata within defined limits. This runbook provides clear procedures for handling escalations efficiently and effectively.

## Table of Contents

1. [Escalation Triggers](#escalation-triggers)
2. [Escalation Levels](#escalation-levels)
3. [Escalation Process](#escalation-process)
4. [Resolution Procedures](#resolution-procedures)
5. [Escalation Tracking and Reporting](#escalation-tracking-and-reporting)

## Escalation Triggers

### Automatic Escalation Triggers

The system automatically escalates brands when:

1. **Iteration Limit Reached**
   - Brand reaches 10 feedback iterations
   - Indicates metadata cannot be improved through feedback
   - Most common escalation trigger

2. **Consecutive Processing Failures**
   - 3 consecutive failures in feedback processing
   - Indicates technical or data issues
   - Requires immediate attention

3. **Critical Data Quality Issues**
   - Missing required data fields
   - Invalid data formats
   - Referential integrity violations

4. **System Errors**
   - Agent invocation failures
   - Timeout errors
   - Infrastructure issues

### Manual Escalation Criteria

Operators should manually escalate when:

1. **Ambiguous Brand Names**
   - Brand name matches multiple real-world brands
   - Example: "Star" could be Star Market, Star Burger, Star Coffee
   - Requires human judgment

2. **Insufficient Data**
   - Too few combo records (<5)
   - Narratives too generic or inconsistent
   - Cannot generate reliable metadata

3. **Complex Business Rules**
   - Special handling required
   - Industry-specific rules needed
   - Regulatory or compliance considerations

4. **Data Quality Concerns**
   - Suspected data corruption
   - Inconsistent or contradictory data
   - Requires data investigation

5. **Low Confidence Scores**
   - Confidence score <0.5 after multiple iterations
   - High uncertainty in classification
   - Risk of incorrect metadata

## Escalation Levels

### Level 1: Operational Escalation

**Scope**: Technical issues, standard data quality problems

**Handled By**: Operations team, data analysts

**Response Time**: 24 hours

**Examples**:
- Iteration limit reached
- Standard data quality issues
- Common ambiguous brand names
- Processing failures

**Resolution**: 
- Manual metadata creation
- Data correction
- Standard troubleshooting

### Level 2: Engineering Escalation

**Scope**: System bugs, performance issues, algorithm problems

**Handled By**: Engineering team

**Response Time**: 48 hours

**Examples**:
- Agent logic errors
- Performance degradation
- Systematic processing failures
- Infrastructure issues

**Resolution**:
- Bug fixes
- Algorithm improvements
- Infrastructure scaling
- Agent instruction updates

### Level 3: Product Escalation

**Scope**: Feature gaps, systematic issues, business rule changes

**Handled By**: Product team, business stakeholders

**Response Time**: 1 week

**Examples**:
- Missing features for edge cases
- Systematic data quality issues
- New business requirements
- Compliance or legal issues

**Resolution**:
- Feature development
- Business rule changes
- Process improvements
- Data source changes

## Escalation Process

### Step 1: Identify Escalation

**Automatic Escalations**:
- System creates escalation record automatically
- SNS notification sent to escalation email list
- Escalation appears in Quick Suite dashboard

**Manual Escalations**:
```bash
# Create manual escalation
python scripts/create_escalation.py \
  --brandid 12345 \
  --reason "Ambiguous brand name" \
  --level 1 \
  --details "Brand name 'Star' matches Star Market, Star Burger, and Star Coffee. Requires manual review to determine correct brand." \
  --assigned-to "data-team@rewardinsight.com"
```

### Step 2: Triage and Assignment

**Triage Checklist**:
- [ ] Review escalation reason
- [ ] Check iteration history
- [ ] Review all feedback provided
- [ ] Examine data quality
- [ ] Determine escalation level
- [ ] Assign to appropriate team

**Assignment**:
```bash
# Assign escalation
python scripts/assign_escalation.py \
  --escalation-id ESC-2026-001 \
  --assigned-to "ed.allison@rewardinsight.com" \
  --level 1
```

**Notification**:
- Email sent to assigned person
- Escalation added to their queue
- SLA timer starts

### Step 3: Investigation

**Investigation Steps**:

1. **Review Brand Data**
```bash
# Get brand details
python scripts/get_brand_details.py --brandid 12345

# Review combo records
python scripts/get_combo_records.py --brandid 12345

# Check narrative samples
python scripts/get_narratives.py --brandid 12345 --limit 50
```

2. **Review Iteration History**
```bash
# Get all iterations
python scripts/get_iteration_history.py --brandid 12345

# Review feedback provided
python scripts/get_feedback_history.py --brandid 12345

# Check metadata versions
python scripts/get_metadata_versions.py --brandid 12345
```

3. **Analyze Root Cause**
- Why did automated processing fail?
- Is this a data issue or algorithm issue?
- Is this a one-off or systematic problem?
- Can this be prevented in the future?

4. **Document Findings**
```bash
# Add investigation notes
python scripts/add_escalation_notes.py \
  --escalation-id ESC-2026-001 \
  --notes "Root cause: Brand name 'Star' is too generic. Data shows mix of Star Market (grocery) and Star Burger (restaurant). MCCIDs confirm two distinct brands. Recommend splitting into two brand records."
```

### Step 4: Resolution

**Resolution Options**:

1. **Manual Metadata Creation**
   - Create metadata manually
   - Upload to S3
   - Mark brand as manually processed

```bash
# Create manual metadata
python scripts/create_manual_metadata.py \
  --brandid 12345 \
  --regex "\\bStar\\s+Market\\b" \
  --mccids "5411,5499" \
  --notes "Manually created for Star Market grocery stores"

# Upload metadata
python scripts/upload_metadata.py \
  --brandid 12345 \
  --metadata-file manual_metadata_12345.json \
  --manual true
```

2. **Data Correction**
   - Fix data quality issues
   - Update source data
   - Reprocess brand

```bash
# Update brand data
python scripts/update_brand_data.py \
  --brandid 12345 \
  --field brand_name \
  --value "Star Market" \
  --reason "Disambiguate from Star Burger"

# Reprocess brand
python scripts/reprocess_brand.py --brandid 12345
```

3. **Brand Splitting**
   - Split ambiguous brand into multiple brands
   - Create separate metadata for each
   - Update combo assignments

```bash
# Split brand
python scripts/split_brand.py \
  --brandid 12345 \
  --new-brands "Star Market,Star Burger" \
  --split-criteria "mccid" \
  --criteria-values "5411:Star Market,5812:Star Burger"
```

4. **Algorithm Update**
   - Update agent instructions
   - Improve processing logic
   - Deploy changes

```bash
# Update agent instructions
# Edit infrastructure/prompts/metadata_production_instructions.md
# Add guidance for handling generic brand names

# Redeploy agent
python infrastructure/deploy_agents.py \
  --agent metadata_production \
  --environment prod
```

5. **Escalate to Higher Level**
   - If resolution requires engineering or product changes
   - Document requirements
   - Create tickets

```bash
# Escalate to Level 2
python scripts/escalate_level.py \
  --escalation-id ESC-2026-001 \
  --new-level 2 \
  --reason "Requires algorithm changes to handle generic brand names systematically"
```

### Step 5: Verification

**Verification Steps**:

1. **Test Resolution**
```bash
# For manual metadata
python scripts/test_metadata.py \
  --brandid 12345 \
  --metadata-file manual_metadata_12345.json

# For reprocessed brands
python scripts/verify_reprocessing.py --brandid 12345
```

2. **Review Results**
- Check metadata quality
- Verify combo matching
- Confirm no false positives/negatives
- Validate confidence scores

3. **Get Approval**
- Submit for human review if needed
- Get stakeholder sign-off
- Document approval

### Step 6: Close Escalation

**Closure Checklist**:
- [ ] Resolution implemented
- [ ] Results verified
- [ ] Approval obtained
- [ ] Documentation updated
- [ ] Lessons learned documented
- [ ] Preventive measures identified

**Close Escalation**:
```bash
# Close escalation
python scripts/close_escalation.py \
  --escalation-id ESC-2026-001 \
  --resolution "Manual metadata created for Star Market. Brand split into Star Market (grocery) and Star Burger (restaurant)." \
  --preventive-measures "Updated agent instructions to flag generic brand names for manual review. Added pre-processing check for ambiguous names." \
  --lessons-learned "Generic brand names require special handling. Consider maintaining list of known ambiguous names."
```

**Notification**:
- Email sent to stakeholders
- Escalation removed from active queue
- Metrics updated

## Resolution Procedures

### Procedure 1: Manual Metadata Creation

**When to Use**:
- Automated processing cannot generate acceptable metadata
- Quick resolution needed
- One-off edge case

**Steps**:

1. **Analyze Brand Data**
```bash
python scripts/analyze_brand.py --brandid 12345
```

2. **Create Regex Pattern**
   - Review narrative samples
   - Identify common patterns
   - Test regex against samples
   - Ensure no false positives

3. **Create MCCID List**
   - Review MCCID distribution
   - Exclude wallet-specific MCCIDs
   - Verify alignment with brand sector

4. **Create Metadata File**
```json
{
  "brandid": 12345,
  "brand_name": "Star Market",
  "regex": "\\bStar\\s+Market\\b",
  "mccids": ["5411", "5499"],
  "sector": "Retail",
  "confidence": 0.95,
  "manual": true,
  "created_by": "ed.allison@rewardinsight.com",
  "created_date": "2026-02-14",
  "notes": "Manually created due to ambiguous brand name"
}
```

5. **Upload and Verify**
```bash
python scripts/upload_metadata.py \
  --brandid 12345 \
  --metadata-file manual_metadata_12345.json

python scripts/verify_metadata.py --brandid 12345
```

### Procedure 2: Data Correction

**When to Use**:
- Data quality issues identified
- Incorrect source data
- Missing required fields

**Steps**:

1. **Identify Data Issues**
```bash
python scripts/validate_brand_data.py --brandid 12345
```

2. **Determine Correction**
   - What needs to be fixed?
   - Where is the source data?
   - Who can authorize changes?

3. **Update Data**
```bash
# Update in source system (Athena/Glue)
python scripts/update_source_data.py \
  --table brand \
  --brandid 12345 \
  --updates '{"brand_name": "Star Market", "sector": "Retail"}'
```

4. **Reprocess Brand**
```bash
python scripts/reprocess_brand.py --brandid 12345
```

5. **Verify Results**
```bash
python scripts/verify_reprocessing.py --brandid 12345
```

### Procedure 3: Brand Splitting

**When to Use**:
- Single brand ID represents multiple real-world brands
- Ambiguous brand name
- Mixed data from different brands

**Steps**:

1. **Analyze Brand Data**
```bash
python scripts/analyze_brand_for_split.py --brandid 12345
```

2. **Determine Split Criteria**
   - MCCID-based split (different business types)
   - Narrative-based split (different name patterns)
   - Geographic split (different locations)

3. **Create New Brand Records**
```bash
python scripts/create_brand.py \
  --brand-name "Star Market" \
  --sector "Retail" \
  --parent-brandid 12345

python scripts/create_brand.py \
  --brand-name "Star Burger" \
  --sector "Food & Beverage" \
  --parent-brandid 12345
```

4. **Reassign Combos**
```bash
python scripts/reassign_combos.py \
  --source-brandid 12345 \
  --target-brandid 12346 \
  --criteria "mccid IN ('5411', '5499')"

python scripts/reassign_combos.py \
  --source-brandid 12345 \
  --target-brandid 12347 \
  --criteria "mccid IN ('5812', '5814')"
```

5. **Process New Brands**
```bash
python scripts/process_brand.py --brandid 12346
python scripts/process_brand.py --brandid 12347
```

6. **Deactivate Original Brand**
```bash
python scripts/deactivate_brand.py \
  --brandid 12345 \
  --reason "Split into Star Market (12346) and Star Burger (12347)"
```

### Procedure 4: Algorithm Update

**When to Use**:
- Systematic issue affecting multiple brands
- Agent logic needs improvement
- New edge case handling required

**Steps**:

1. **Document Issue**
   - What is the systematic problem?
   - How many brands affected?
   - What is the desired behavior?

2. **Update Agent Instructions**
```bash
# Edit agent instruction file
vim infrastructure/prompts/metadata_production_instructions.md

# Add new guidance or examples
# Update edge case handling
# Clarify ambiguous instructions
```

3. **Test Changes**
```bash
# Test with affected brands
python scripts/test_agent_update.py \
  --agent metadata_production \
  --test-brandids "12345,12346,12347" \
  --instructions-file infrastructure/prompts/metadata_production_instructions.md
```

4. **Deploy Update**
```bash
# Deploy to dev first
python infrastructure/deploy_agents.py \
  --agent metadata_production \
  --environment dev

# Test in dev
python scripts/test_agent.py \
  --agent metadata_production \
  --environment dev

# Deploy to prod
python infrastructure/deploy_agents.py \
  --agent metadata_production \
  --environment prod
```

5. **Reprocess Affected Brands**
```bash
python scripts/reprocess_brands.py \
  --brandids "12345,12346,12347" \
  --reason "Algorithm update for generic brand names"
```

## Escalation Tracking and Reporting

### Escalation Dashboard

**Quick Suite Dashboard**:
- Active escalations count
- Escalations by level
- Average resolution time
- Escalation trends

**CloudWatch Dashboard**:
- Metric: `BrandsEscalated`
- Metric: `EscalationResolutionTime`
- Metric: `EscalationsByReason`

### Escalation Reports

**Daily Report**:
```bash
python scripts/escalation_report.py \
  --report-type daily \
  --date 2026-02-14 \
  --output daily_escalation_report.pdf
```

**Weekly Report**:
```bash
python scripts/escalation_report.py \
  --report-type weekly \
  --start-date 2026-02-08 \
  --end-date 2026-02-14 \
  --output weekly_escalation_report.pdf
```

**Monthly Report**:
```bash
python scripts/escalation_report.py \
  --report-type monthly \
  --month 2026-02 \
  --output monthly_escalation_report.pdf
```

### Key Metrics

**Escalation Rate**:
- Formula: (Escalated Brands / Total Brands) × 100
- Target: <5%
- Alert: >10%

**Average Resolution Time**:
- Level 1: Target <24 hours
- Level 2: Target <48 hours
- Level 3: Target <1 week

**Escalation Reasons**:
- Track most common reasons
- Identify systematic issues
- Prioritize improvements

**Resolution Methods**:
- Manual metadata: %
- Data correction: %
- Brand splitting: %
- Algorithm update: %

### Continuous Improvement

**Monthly Review**:
- Analyze escalation trends
- Identify systematic issues
- Prioritize improvements
- Update procedures

**Quarterly Planning**:
- Set escalation rate targets
- Plan algorithm improvements
- Allocate resources
- Update training materials

## Additional Resources

- [Feedback Processing Runbook](FEEDBACK_PROCESSING_RUNBOOK.md)
- [Production Monitoring Setup](PRODUCTION_MONITORING_SETUP.md)
- [Learning Analytics Runbook](LEARNING_ANALYTICS_RUNBOOK.md)
- [Agent Deployment Guide](AGENT_DEPLOYMENT_GUIDE.md)
- [MCP Troubleshooting Guide](MCP_TROUBLESHOOTING_RUNBOOK.md)
