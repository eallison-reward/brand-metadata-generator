# Specification Updates - Human-in-the-Loop and MCP Integration

## Management Requirements (February 2026)

### 1. MCP Integration for Commercial Assessment

**Requirement**: The Commercial Assessment agent should interact with MCP servers for market and retail brand information.

**Recommended MCP Servers**:

1. **Crunchbase MCP Server** (cyreslab-ai/crunchbase-mcp-server)
   - Company profiles and details
   - Funding information
   - Industry classifications
   - Executive/people data
   - GitHub: https://github.com/Cyreslab-AI/crunchbase-mcp-server

2. **Bright Data Crunchbase MCP**
   - Public company profiles
   - Industry data
   - Acquisition information
   - URL: https://brightdata.com/ai/mcp-server/crunchbase

3. **Custom Brand Data MCP Server** (to be built)
   - UK retail brand registry
   - Sector classifications
   - Brand aliases and variations
   - MCC-to-sector mappings

**Implementation Approach**:
- Configure MCP servers in `.kiro/settings/mcp.json`
- Commercial Assessment agent uses MCP tools to validate brands
- Fallback to web search if MCP data unavailable

### 2. Human-in-the-Loop (HITL) Feedback System

**Requirement**: After metadata generation and combo classification, humans must review results and provide feedback for iterative improvement.

**Workflow Changes**:

```
1. Generate Metadata (regex + MCCIDs)
2. Apply Metadata to Combos
3. Agent Classification (Confirmation + Tiebreaker)
4. → NEW: Human Review & Feedback ←
5. → NEW: Feedback Processing & Learning ←
6. → NEW: Metadata Refinement (if needed) ←
7. Store Final Results
```

**Human Feedback Types**:

1. **General Feedback**
   - "Too many false positives for Brand X"
   - "Regex is too broad"
   - "Missing common narrative patterns"

2. **Specific Examples**
   - "Combo 12345 should be Brand A, not Brand B"
   - "Combo 67890 is misclassified - narrative contains 'SHELL STATION' but assigned to wrong Shell brand"

3. **Approval/Rejection**
   - Approve all classifications for a brand
   - Reject and request regeneration with guidance

**Feedback Storage**:
- S3: `s3://brand-generator-rwrd-023-eu-west-1/feedback/`
- DynamoDB: Feedback history table with timestamps
- Format: JSON with brandid, feedback_type, text, examples, timestamp

### 3. Iterative Learning System

**Requirement**: System learns from feedback and improves accuracy over time.

**Learning Mechanisms**:

1. **Feedback-Driven Regeneration**
   - Parse human feedback to extract issues
   - Generate specific prompts for Metadata Production Agent
   - Regenerate regex/MCCIDs with feedback incorporated
   - Re-apply and re-classify

2. **Example-Based Learning**
   - Extract specific misclassified combos from feedback
   - Analyze patterns in misclassifications
   - Adjust regex to exclude false positives
   - Adjust MCCID lists based on patterns

3. **Confidence Adjustment**
   - Track feedback frequency per brand
   - Lower confidence scores for frequently corrected brands
   - Route low-confidence brands to human review earlier

4. **Historical Feedback Analysis**
   - Store all feedback with metadata versions
   - Analyze trends: which brands need most corrections
   - Identify systematic issues (e.g., wallet handling)
   - Generate reports for continuous improvement

**Iteration Tracking**:
```json
{
  "brandid": 123,
  "metadata_version": 3,
  "iterations": [
    {
      "version": 1,
      "timestamp": "2026-02-13T10:00:00Z",
      "regex": "^STARBUCKS.*",
      "mccids": [5812, 5814],
      "human_feedback": null
    },
    {
      "version": 2,
      "timestamp": "2026-02-13T14:30:00Z",
      "regex": "^STARBUCKS(?!.*HOTEL).*",
      "mccids": [5812],
      "human_feedback": "Too many false positives - matching Starbucks Hotel"
    },
    {
      "version": 3,
      "timestamp": "2026-02-13T16:00:00Z",
      "regex": "^(?:STARBUCKS|SBUX)\\s*(?!.*HOTEL)#?\\d*",
      "mccids": [5812],
      "human_feedback": "Approved"
    }
  ]
}
```

## New Components Required

### 1. Human Review Interface (Quick_Suite Dashboard)

**Features**:
- Display classified combos grouped by brand
- Show regex pattern and MCCIDs used
- Highlight low-confidence classifications
- Text input for general feedback
- Ability to flag specific combos as misclassified
- Approve/Reject buttons per brand
- View feedback history

### 2. Feedback Processing Agent (NEW)

**Purpose**: Parse and process human feedback to generate actionable improvements.

**Responsibilities**:
- Parse natural language feedback
- Extract specific combo IDs mentioned
- Identify feedback categories (regex too broad, missing patterns, wrong MCCIDs)
- Generate structured prompts for Metadata Production Agent
- Track feedback patterns across brands

**Tools**:
- `parse_feedback(feedback_text: str) -> dict`: Extract structured data
- `identify_misclassified_combos(feedback: dict) -> list`: Find specific examples
- `generate_refinement_prompt(feedback: dict, current_metadata: dict) -> str`: Create guidance
- `store_feedback(brandid: int, feedback: dict) -> dict`: Persist to S3/DynamoDB

### 3. Learning Analytics Agent (NEW)

**Purpose**: Analyze historical feedback to identify systematic improvements.

**Responsibilities**:
- Aggregate feedback across all brands
- Identify common issues (e.g., wallet handling problems)
- Generate improvement recommendations
- Track accuracy metrics over time
- Produce reports for management

**Tools**:
- `analyze_feedback_trends(time_range: str) -> dict`: Identify patterns
- `calculate_accuracy_metrics(brandid: int) -> dict`: Measure improvement
- `generate_improvement_report() -> dict`: Create summary
- `identify_problematic_brands() -> list`: Find brands needing attention

## Updated Workflow

### Phase 1-3: (Unchanged)
- Data ingestion
- Brand evaluation
- Metadata generation

### Phase 4: Combo Classification (UPDATED)
1. Apply metadata to all combos
2. Identify multi-brand matches (ties)
3. Tiebreaker agent resolves ties
4. Confirmation agent reviews matches
5. **NEW: Store preliminary results for human review**

### Phase 5: Human Review (NEW)
1. Display results in Quick_Suite dashboard
2. Human reviews classifications per brand
3. Human provides feedback:
   - General text feedback
   - Specific misclassified combo examples
   - Approve or reject classifications
4. Store feedback in S3 and DynamoDB

### Phase 6: Feedback Processing & Learning (NEW)
1. Feedback Processing Agent parses feedback
2. If rejected or issues identified:
   - Generate refinement prompts
   - Invoke Metadata Production Agent to regenerate
   - Re-apply metadata to combos
   - Re-run classification agents
   - Return to Phase 5 (human review)
3. If approved:
   - Store final results
   - Update learning analytics
   - Proceed to completion

### Phase 7: Storage & Analytics (UPDATED)
1. Store final approved results
2. Learning Analytics Agent updates metrics
3. Generate improvement reports
4. Update dashboard with accuracy trends

## MCP Configuration

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "crunchbase": {
      "command": "npx",
      "args": ["-y", "@cyreslab-ai/crunchbase-mcp-server"],
      "env": {
        "CRUNCHBASE_API_KEY": "${CRUNCHBASE_API_KEY}"
      },
      "disabled": false,
      "autoApprove": [
        "search_companies",
        "get_company",
        "get_company_funding"
      ]
    },
    "brand-registry": {
      "command": "python",
      "args": ["-m", "brand_registry_mcp.server"],
      "env": {
        "BRAND_REGISTRY_DB": "brand_metadata_generator_db"
      },
      "disabled": false,
      "autoApprove": [
        "search_brands",
        "get_brand_info",
        "validate_sector"
      ]
    }
  }
}
```

## Updated Requirements

### New Requirement 14: Human-in-the-Loop Feedback

**User Story**: As a quality assurance specialist, I want to review classified combos and provide feedback, so that the system learns and improves accuracy over time.

**Acceptance Criteria**:
1. WHEN metadata is applied to combos, THE System SHALL store preliminary results for human review
2. WHEN a human reviews results, THE System SHALL display combos grouped by brand with classification details
3. WHEN a human provides feedback, THE System SHALL store feedback with timestamp and brandid
4. WHEN feedback indicates issues, THE System SHALL invoke Feedback Processing Agent
5. WHEN feedback is processed, THE System SHALL regenerate metadata and re-classify combos
6. THE System SHALL support both general text feedback and specific combo examples
7. THE System SHALL track all feedback iterations with version history

### New Requirement 15: MCP Integration for Brand Validation

**User Story**: As a commercial assessment agent, I want to query external brand databases via MCP, so that brand validation is accurate and up-to-date.

**Acceptance Criteria**:
1. THE Commercial Assessment Agent SHALL connect to Crunchbase MCP server
2. WHEN validating a brand, THE Agent SHALL query MCP for company information
3. WHEN MCP data is available, THE Agent SHALL use it for sector validation
4. WHEN MCP data is unavailable, THE Agent SHALL fall back to web search
5. THE System SHALL configure MCP servers in .kiro/settings/mcp.json
6. THE System SHALL log all MCP interactions for audit

### New Requirement 16: Iterative Learning and Improvement

**User Story**: As a system operator, I want the system to learn from feedback and improve over time, so that classification accuracy increases with use.

**Acceptance Criteria**:
1. THE System SHALL store all feedback with metadata version history
2. THE Learning Analytics Agent SHALL analyze feedback trends
3. WHEN patterns are identified, THE System SHALL generate improvement recommendations
4. THE System SHALL track accuracy metrics per brand over time
5. THE System SHALL produce reports showing improvement trends
6. THE System SHALL adjust confidence scores based on feedback frequency
7. THE System SHALL limit iterations to 10 per brand before escalating to management

## Updated Tasks

### New Task 5.4: Integrate MCP Servers
- Configure Crunchbase MCP server
- Test MCP connectivity
- Implement fallback logic
- Add MCP tool usage to Commercial Assessment Agent

### New Task 17: Feedback Processing Agent
- Implement feedback parsing tools
- Create refinement prompt generation
- Implement feedback storage
- Write unit and property tests

### New Task 18: Learning Analytics Agent
- Implement trend analysis tools
- Create accuracy metrics calculation
- Implement report generation
- Write unit tests

### New Task 19: Human Review Interface
- Extend Quick_Suite dashboard for review
- Add feedback input forms
- Implement approve/reject workflow
- Add feedback history view

### New Task 20: Updated Workflow Integration
- Modify Step Functions to include human review phase
- Add feedback processing loop
- Implement iteration limits
- Update monitoring for new phases

## Benefits

1. **Improved Accuracy**: Human feedback directly improves metadata quality
2. **Continuous Learning**: System gets better with use
3. **Transparency**: Full audit trail of all changes and feedback
4. **Flexibility**: Handles both general and specific feedback
5. **Scalability**: Automated learning reduces manual intervention over time
6. **External Validation**: MCP integration provides authoritative brand data
7. **Compliance**: Full tracking for regulatory requirements

## Next Steps

1. Review and approve these updates
2. Update requirements.md with new requirements 14-16
3. Update design.md with new agents and workflow
4. Update tasks.md with new tasks 17-20
5. Implement MCP configuration
6. Build Feedback Processing Agent
7. Build Learning Analytics Agent
8. Extend Quick_Suite dashboard
9. Update Step Functions workflow
10. Test end-to-end with feedback loop
