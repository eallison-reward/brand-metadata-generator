# Design Document: Conversational Interface Agent

## Overview

The Conversational Interface Agent provides a natural language interface for the Brand Metadata Generator system. Built on AWS Bedrock AgentCore using the Strands API, this agent enables users to interact with the system through conversational commands rather than direct API calls or console operations.

The agent acts as a coordinator between the user and backend systems, translating natural language requests into specific tool invocations. It handles workflow management, data querying, feedback submission, and system monitoring through a unified conversational interface accessible via AWS Bedrock Console.

### Key Capabilities

- Start and monitor Step Functions workflows for brand processing
- Submit feedback on generated metadata with natural language descriptions
- Query brand metadata and system data without writing SQL
- Monitor system health and workflow statistics
- Retrieve brands awaiting human review
- Access data through both S3 JSON files and Athena tables

### Design Principles

1. **User-Centric**: Natural language interface that doesn't require technical knowledge
2. **Contextual**: Agent maintains conversation context and asks clarifying questions
3. **Resilient**: Graceful error handling with helpful feedback
4. **Secure**: Respects IAM permissions and follows least-privilege principles
5. **Observable**: All operations logged to CloudWatch for debugging and audit

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Bedrock Console                      │
│                    (User Interface)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Natural Language
                         │ Requests/Responses
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          Conversational Interface Agent (Bedrock)            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Agent Instruction Prompt                 │  │
│  │  - Parse user intent                                  │  │
│  │  - Select appropriate tools                           │  │
│  │  - Format responses conversationally                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   Tool Definitions                    │  │
│  │  - query_brands_to_check                             │  │
│  │  - start_workflow                                     │  │
│  │  - check_workflow_status                              │  │
│  │  - submit_feedback                                    │  │
│  │  - query_metadata                                     │  │
│  │  - execute_athena_query                               │  │
│  │  - list_escalations                                   │  │
│  │  - get_workflow_stats                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Lambda Invocations
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Tool Lambda Functions                     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Workflow   │  │   Athena     │  │   Feedback   │     │
│  │   Manager    │  │   Query      │  │   Submitter  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Metadata   │  │  Escalation  │  │   Stats      │     │
│  │   Retriever  │  │   Lister     │  │   Collector  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ AWS SDK Calls
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend Services                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │     Step     │  │    Athena    │  │      S3      │     │
│  │  Functions   │  │   Database   │  │    Bucket    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │     Glue     │  │  CloudWatch  │                        │
│  │   Catalog    │  │     Logs     │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **User Input**: User types natural language request in Bedrock Console
2. **Intent Parsing**: Agent analyzes request and determines required actions
3. **Tool Selection**: Agent selects appropriate tool(s) to fulfill request
4. **Tool Execution**: Lambda functions execute backend operations
5. **Response Formatting**: Agent formats results conversationally
6. **User Output**: Response displayed in Bedrock Console

### Data Flow

```
User Request → Agent → Tool Lambda → AWS Service → Data Store
                ↓                                      ↓
            Clarifying                            Query Results
            Questions                                  ↓
                ↓                                      ↓
            User Response ← Agent ← Tool Lambda ← Processing
```

## Components and Interfaces

### 1. Conversational Interface Agent

**Purpose**: Bedrock agent that processes natural language and coordinates tool execution

**Configuration**:
- Model: Claude 3 Sonnet (or latest available)
- Region: eu-west-1
- Temperature: 0.7 (balanced between creativity and consistency)
- Max tokens: 2048

**Instruction Prompt**:
```
You are a helpful assistant for the Brand Metadata Generator system. You help users:
- Start and monitor brand processing workflows
- Submit feedback on generated metadata
- Query brand data and system statistics
- Monitor system health

When users make requests:
1. Parse their intent carefully
2. Ask clarifying questions if needed
3. Use the appropriate tools to fulfill requests
4. Present results in a clear, conversational manner
5. Suggest next steps when appropriate

Be concise but friendly. If operations fail, explain what went wrong and suggest solutions.
```

**IAM Role Permissions**:
- `lambda:InvokeFunction` on tool Lambda functions
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` for CloudWatch

### 2. Tool Lambda Functions

Each tool is implemented as a separate Lambda function for modularity and independent scaling.

#### Tool 1: query_brands_to_check

**Purpose**: Query the brands_to_check Athena table for brands to process

**Input Schema**:
```json
{
  "status": "string (optional)",
  "limit": "integer (optional, default: 10)"
}
```

**Output Schema**:
```json
{
  "brands": [
    {
      "brandid": "integer",
      "brandname": "string",
      "status": "string",
      "sector": "string"
    }
  ],
  "total_count": "integer"
}
```

**Implementation**:
- Uses AthenaClient to query brands_to_check table
- Filters by status if provided (e.g., "unprocessed")
- Returns paginated results with total count

#### Tool 2: start_workflow

**Purpose**: Start Step Functions workflow for brand processing

**Input Schema**:
```json
{
  "brandid": "integer or array of integers",
  "execution_name": "string (optional)"
}
```

**Output Schema**:
```json
{
  "executions": [
    {
      "brandid": "integer",
      "execution_arn": "string",
      "start_time": "string (ISO 8601)"
    }
  ],
  "success": "boolean"
}
```

**Implementation**:
- Uses boto3 Step Functions client
- Starts workflow with brand ID as input
- Generates unique execution name if not provided
- Returns execution ARN for status tracking

#### Tool 3: check_workflow_status

**Purpose**: Query Step Functions execution status

**Input Schema**:
```json
{
  "execution_arn": "string"
}
```

**Output Schema**:
```json
{
  "status": "string (RUNNING|SUCCEEDED|FAILED|TIMED_OUT|ABORTED)",
  "start_time": "string (ISO 8601)",
  "stop_time": "string (ISO 8601, optional)",
  "output": "object (optional)",
  "error": "string (optional)"
}
```

**Implementation**:
- Uses boto3 Step Functions client
- Calls describe_execution API
- Parses and returns execution details

#### Tool 4: submit_feedback

**Purpose**: Submit feedback to feedback processing system

**Input Schema**:
```json
{
  "brandid": "integer",
  "feedback_text": "string",
  "metadata_version": "integer (optional, default: latest)"
}
```

**Output Schema**:
```json
{
  "feedback_id": "string (UUID)",
  "stored": "boolean",
  "storage_location": "string (S3 key)"
}
```

**Implementation**:
- Uses feedback_processing agent tools
- Parses feedback using parse_feedback function
- Stores to S3 and feedback_history Athena table
- Returns confirmation with feedback ID

#### Tool 5: query_metadata

**Purpose**: Retrieve brand metadata from S3

**Input Schema**:
```json
{
  "brandid": "integer",
  "version": "string (optional, default: latest)"
}
```

**Output Schema**:
```json
{
  "brandid": "integer",
  "brandname": "string",
  "regex": "string",
  "mccids": ["integer"],
  "confidence_score": "float",
  "version": "integer",
  "generated_at": "string (ISO 8601)"
}
```

**Implementation**:
- Uses S3Client to retrieve metadata JSON
- Parses and returns structured data
- Returns null if metadata not found

#### Tool 6: execute_athena_query

**Purpose**: Execute parameterized Athena queries

**Input Schema**:
```json
{
  "query_type": "string (brands_by_confidence|brands_by_category|custom)",
  "parameters": "object (query-specific parameters)",
  "limit": "integer (optional, default: 10)"
}
```

**Output Schema**:
```json
{
  "results": ["array of objects"],
  "row_count": "integer",
  "execution_time_ms": "integer"
}
```

**Implementation**:
- Uses AthenaClient for query execution
- Supports predefined query templates
- Allows custom SQL for advanced users
- Returns paginated results

**Predefined Query Types**:
- `brands_by_confidence`: Query brands with confidence score in range
- `brands_by_category`: Query brands by sector/category
- `recent_workflows`: Query recent workflow executions
- `escalations_pending`: Query brands awaiting review

#### Tool 7: list_escalations

**Purpose**: List brands awaiting human review

**Input Schema**:
```json
{
  "limit": "integer (optional, default: 10)",
  "sort_by": "string (optional, default: timestamp)"
}
```

**Output Schema**:
```json
{
  "escalations": [
    {
      "brandid": "integer",
      "brandname": "string",
      "reason": "string",
      "confidence_score": "float",
      "escalated_at": "string (ISO 8601)"
    }
  ],
  "total_count": "integer"
}
```

**Implementation**:
- Queries escalations Athena table
- Filters for unresolved escalations
- Returns sorted list with details

#### Tool 8: get_workflow_stats

**Purpose**: Get workflow execution statistics

**Input Schema**:
```json
{
  "time_period": "string (last_hour|last_day|last_week)",
  "include_details": "boolean (optional, default: false)"
}
```

**Output Schema**:
```json
{
  "total_executions": "integer",
  "successful": "integer",
  "failed": "integer",
  "running": "integer",
  "success_rate": "float",
  "average_duration_seconds": "float",
  "brands_processed": "integer"
}
```

**Implementation**:
- Queries workflow_executions Athena table
- Aggregates statistics for time period
- Calculates success rate and averages

### 3. Glue Table Definitions

To make system outputs queryable, we create Glue tables for key data types.

#### Table: generated_metadata

**Purpose**: Queryable metadata generation results

**Schema**:
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS generated_metadata (
  brandid INT,
  brandname STRING,
  regex STRING,
  mccids ARRAY<INT>,
  confidence_score DOUBLE,
  version INT,
  generated_at TIMESTAMP,
  evaluator_issues ARRAY<STRING>,
  coverage_narratives_matched DOUBLE,
  coverage_false_positives DOUBLE
)
STORED AS JSON
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/metadata/'
```

#### Table: feedback_history

**Purpose**: Queryable feedback submissions

**Schema**:
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS feedback_history (
  feedback_id STRING,
  brandid INT,
  metadata_version INT,
  feedback_text STRING,
  category STRING,
  issues_identified ARRAY<STRING>,
  misclassified_combos ARRAY<INT>,
  submitted_at TIMESTAMP,
  submitted_by STRING
)
STORED AS JSON
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/feedback/'
```

#### Table: workflow_executions

**Purpose**: Queryable workflow execution history

**Schema**:
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS workflow_executions (
  execution_arn STRING,
  brandid INT,
  status STRING,
  start_time TIMESTAMP,
  stop_time TIMESTAMP,
  duration_seconds INT,
  error_message STRING,
  input_data STRING,
  output_data STRING
)
STORED AS JSON
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/workflow-executions/'
```

#### Table: escalations

**Purpose**: Queryable escalation records

**Schema**:
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS escalations (
  escalation_id STRING,
  brandid INT,
  brandname STRING,
  reason STRING,
  confidence_score DOUBLE,
  escalated_at TIMESTAMP,
  resolved_at TIMESTAMP,
  resolved_by STRING,
  resolution_notes STRING,
  status STRING
)
STORED AS JSON
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/escalations/'
```

## Data Models

### Agent Tool Request/Response

All tool Lambda functions follow a consistent request/response pattern:

**Request Format**:
```python
{
    "tool_name": str,
    "parameters": dict,
    "request_id": str,  # For tracing
    "timestamp": str    # ISO 8601
}
```

**Response Format**:
```python
{
    "success": bool,
    "data": dict,       # Tool-specific response data
    "error": str,       # Present only if success=False
    "request_id": str,  # Echo from request
    "execution_time_ms": int
}
```

### Workflow Execution Input

**Format**:
```python
{
    "brandid": int,
    "execution_name": str,
    "config": {
        "max_iterations": int,
        "confidence_threshold": float,
        "enable_commercial_assessment": bool
    }
}
```

### Feedback Record

**Format**:
```python
{
    "feedback_id": str,      # UUID
    "brandid": int,
    "metadata_version": int,
    "feedback_text": str,
    "category": str,         # From FEEDBACK_CATEGORIES
    "issues_identified": List[str],
    "misclassified_combos": List[int],
    "submitted_at": str,     # ISO 8601
    "submitted_by": str      # User identifier
}
```

### Escalation Record

**Format**:
```python
{
    "escalation_id": str,    # UUID
    "brandid": int,
    "brandname": str,
    "reason": str,           # Why escalated
    "confidence_score": float,
    "metadata": dict,        # Current metadata
    "escalated_at": str,     # ISO 8601
    "status": str,           # pending|resolved|cancelled
    "resolved_at": str,      # ISO 8601 (optional)
    "resolved_by": str,      # User identifier (optional)
    "resolution_notes": str  # (optional)
}
```

### Query Result

**Format**:
```python
{
    "results": List[dict],   # Query rows
    "row_count": int,
    "columns": List[str],
    "execution_time_ms": int,
    "next_token": str        # For pagination (optional)
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Intent Parsing Accuracy

*For any* natural language request related to supported operations (workflow management, feedback submission, data querying, system monitoring), the agent should correctly identify the intent category and extract relevant parameters (brand IDs, time periods, query criteria).

**Validates: Requirements 1.1, 1.4**

### Property 2: Ambiguity Detection

*For any* ambiguous request (missing required parameters, unclear intent, multiple possible interpretations), the agent should ask clarifying questions rather than making assumptions or proceeding with incomplete information.

**Validates: Requirements 1.2**

### Property 3: Error Message Helpfulness

*For any* unfulfillable request or failed operation, the agent should provide a clear explanation of what went wrong and suggest actionable next steps or alternatives.

**Validates: Requirements 1.3, 2.5, 9.1, 9.2, 9.3, 9.4**

### Property 4: Multi-Step Coordination

*For any* request requiring multiple tool invocations, the agent should execute steps in the correct order, pass data between steps correctly, and provide progress updates at each stage.

**Validates: Requirements 1.5**

### Property 5: Brand Verification Before Workflow Start

*For any* brand ID provided for workflow initiation, the agent should verify the brand exists in the Brands_To_Check_Table before starting a Step_Functions_Workflow, and return an error if the brand is not found.

**Validates: Requirements 2.1, 2.2, 2.3**

### Property 6: Workflow Status Accuracy

*For any* workflow execution ARN, querying the status should return the current state (RUNNING, SUCCEEDED, FAILED, etc.) that matches the actual Step Functions execution state.

**Validates: Requirements 2.4**

### Property 7: Execution ARN Return

*For any* successfully started workflow, the agent should return a valid execution ARN that can be used to query the workflow status.

**Validates: Requirements 2.6**

### Property 8: Feedback Component Extraction

*For any* feedback text containing brand information and issue descriptions, the agent should correctly extract the brand ID (or resolve brand name to ID), feedback type category, and specific issues mentioned.

**Validates: Requirements 3.1, 3.3**

### Property 9: Feedback Submission Confirmation

*For any* valid feedback submission, the agent should send the feedback to the Feedback_Processing_System and return a confirmation with a unique feedback ID.

**Validates: Requirements 3.2**

### Property 10: Feedback Type Support

*For any* feedback categorized as regex corrections, category adjustments, or general comments, the agent should handle the feedback appropriately and route it to the correct processing logic.

**Validates: Requirements 3.4**

### Property 11: Feedback Submission Retry

*For any* feedback submission that fails on first attempt, the agent should retry exactly once before reporting a persistent error to the user.

**Validates: Requirements 3.5**

### Property 12: Metadata Retrieval and Formatting

*For any* brand ID with existing metadata, querying the metadata should retrieve the complete record from S3 and present it in a human-readable format with all key fields (regex, mccids, confidence score, etc.).

**Validates: Requirements 4.1**

### Property 13: Criteria-Based Querying

*For any* query criteria (confidence score range, category, processing status), the agent should execute the appropriate Athena query and return all matching brands.

**Validates: Requirements 4.2, 4.4**

### Property 14: Result Pagination

*For any* query returning more than 10 results, the agent should display the first 10 and offer to show more, allowing the user to page through results.

**Validates: Requirements 4.3**

### Property 15: Empty Result Handling

*For any* query that returns zero results, the agent should confirm the query parameters used and suggest ways to broaden the search.

**Validates: Requirements 4.5**

### Property 16: Health Status Reporting

*For any* system health check request, the agent should query recent workflow execution success rates and report overall health status with supporting metrics.

**Validates: Requirements 5.1**

### Property 17: Statistics Aggregation

*For any* statistics request with a time period (last hour, last day, last week), the agent should query the workflow_executions table, aggregate the data correctly, and return execution counts, success rates, and average durations.

**Validates: Requirements 5.2, 5.4**

### Property 18: Escalation Status Reporting

*For any* escalation status request, the agent should query the escalations table and return the count and details of brands awaiting human review.

**Validates: Requirements 5.3**

### Property 19: Proactive Issue Reporting

*For any* response when system health indicators show problems (success rate below threshold, high failure count, many escalations), the agent should proactively mention the issues in its response.

**Validates: Requirements 5.5**

### Property 20: Dual Storage Consistency

*For any* system output (metadata, feedback, workflow execution, escalation), the data should be stored as a JSON file in S3 and as a record in the corresponding Glue Catalog table with matching content.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

### Property 21: Schema Consistency

*For any* Glue Catalog table, the schema should match the structure of the JSON files stored in S3, ensuring that all JSON fields have corresponding table columns with compatible types.

**Validates: Requirements 6.5**

### Property 22: Tool Error Structure

*For any* tool execution failure, the tool should return a structured error response containing an error message, error type, and sufficient context for the agent to explain the issue to the user.

**Validates: Requirements 7.9**

### Property 23: CloudWatch Logging

*For any* tool execution (successful or failed), a log entry should be written to CloudWatch containing the tool name, input parameters, execution result, and timestamp.

**Validates: Requirements 9.5**

### Property 24: Permission Limitation Reporting

*For any* operation that fails due to insufficient IAM permissions, the agent should clearly report that the operation is not permitted and suggest contacting an administrator.

**Validates: Requirements 10.5**

## Error Handling

### Error Categories

The system handles four main categories of errors:

1. **User Input Errors**: Invalid parameters, ambiguous requests, unsupported operations
2. **Backend Service Errors**: Step Functions failures, Athena query errors, S3 access issues
3. **Permission Errors**: IAM permission denials, resource access restrictions
4. **System Errors**: Timeouts, service unavailability, unexpected exceptions

### Error Handling Strategy

**User Input Errors**:
- Validate input parameters before tool invocation
- Provide specific feedback about what is invalid
- Suggest corrections or alternatives
- Never proceed with invalid or ambiguous input

**Backend Service Errors**:
- Implement retry logic with exponential backoff (1 retry for most operations)
- Parse service error messages into user-friendly explanations
- Log full error details to CloudWatch for debugging
- Provide actionable suggestions (e.g., "check system status", "try again later")

**Permission Errors**:
- Detect IAM permission denials from AWS SDK exceptions
- Clearly communicate that the operation is not permitted
- Suggest contacting an administrator for access
- Log permission errors for security audit

**System Errors**:
- Implement timeouts for all backend operations (default: 30 seconds)
- Gracefully handle service unavailability
- Provide fallback responses when possible
- Log all unexpected exceptions with full stack traces

### Error Response Format

All tool Lambda functions return errors in a consistent format:

```python
{
    "success": False,
    "error": {
        "type": "string",  # user_input|backend_service|permission|system
        "message": "string",  # User-friendly error message
        "details": "string",  # Technical details for logging
        "suggestion": "string"  # Actionable next step
    },
    "request_id": "string",
    "timestamp": "string"
}
```

### Retry Logic

**Operations with retry**:
- Feedback submission: 1 retry with 2-second delay
- Athena queries: 1 retry with exponential backoff
- S3 operations: 1 retry with 1-second delay

**Operations without retry**:
- Step Functions workflow start (idempotent, no need to retry)
- Status queries (read-only, user can retry manually)

### Logging Strategy

All errors are logged to CloudWatch with:
- Error type and category
- Full error message and stack trace
- Request context (tool name, parameters, user)
- Timestamp and request ID for tracing

## Testing Strategy

### Dual Testing Approach

The Conversational Interface Agent requires both unit testing and property-based testing for comprehensive coverage:

**Unit Tests**: Focus on specific examples, edge cases, and integration points
- Test each tool Lambda function with known inputs
- Test error handling for specific failure scenarios
- Test agent instruction prompt with example conversations
- Test Glue table creation scripts
- Test IAM role permissions

**Property Tests**: Verify universal properties across all inputs
- Test intent parsing with randomly generated natural language requests
- Test error handling with randomly generated failure conditions
- Test data consistency between S3 and Athena with random data
- Test pagination with randomly sized result sets
- Test retry logic with randomly injected failures

### Property-Based Testing Configuration

- **Library**: Use `hypothesis` for Python Lambda functions
- **Iterations**: Minimum 100 iterations per property test
- **Tagging**: Each property test must reference its design document property
- **Tag Format**: `# Feature: conversational-interface-agent, Property N: [property text]`

### Unit Testing Focus Areas

1. **Tool Lambda Functions**:
   - Test each tool with valid inputs
   - Test input validation and error cases
   - Test AWS SDK integration (mocked)
   - Test response formatting

2. **Agent Integration**:
   - Test agent with example conversations
   - Test tool selection for different request types
   - Test multi-step coordination
   - Test error recovery

3. **Data Layer**:
   - Test Glue table schemas match JSON structures
   - Test S3 write operations
   - Test Athena query execution
   - Test data retrieval and formatting

4. **Error Handling**:
   - Test each error category with specific examples
   - Test retry logic with simulated failures
   - Test error message formatting
   - Test CloudWatch logging

### Integration Testing

Integration tests verify end-to-end flows:

1. **Workflow Management Flow**:
   - User requests brand processing
   - Agent queries brands_to_check table
   - Agent starts Step Functions workflow
   - Agent returns execution ARN
   - User checks workflow status
   - Agent queries and returns status

2. **Feedback Submission Flow**:
   - User provides feedback in natural language
   - Agent parses feedback and extracts components
   - Agent resolves brand name to ID
   - Agent submits to feedback processing system
   - Agent confirms submission with feedback ID
   - Verify feedback appears in S3 and Athena

3. **Data Querying Flow**:
   - User requests brands with low confidence
   - Agent executes Athena query
   - Agent formats and paginates results
   - User requests next page
   - Agent returns additional results

4. **System Monitoring Flow**:
   - User requests system health
   - Agent queries workflow statistics
   - Agent detects issues (if any)
   - Agent reports health with proactive issue mention
   - User requests escalation status
   - Agent returns escalation details

### Test Data Generation

For property-based testing, generate:

- **Natural Language Requests**: Use templates with random parameters
- **Brand IDs**: Random integers in valid range
- **Feedback Text**: Random combinations of feedback keywords and brand references
- **Query Criteria**: Random confidence scores, categories, time periods
- **Workflow Executions**: Random execution states and durations
- **Error Conditions**: Random error types and messages

### Mocking Strategy

Mock AWS services for unit and property tests:

- **Step Functions**: Mock `start_execution`, `describe_execution`
- **Athena**: Mock `start_query_execution`, `get_query_results`
- **S3**: Mock `put_object`, `get_object`
- **Glue**: Mock `create_table`, `get_table`
- **CloudWatch Logs**: Mock `put_log_events`

Use `moto` library for AWS service mocking in Python tests.

### Test Coverage Goals

- **Unit Test Coverage**: >80% line coverage for all Lambda functions
- **Property Test Coverage**: All 24 correctness properties implemented
- **Integration Test Coverage**: All 4 major flows tested end-to-end
- **Error Path Coverage**: All error categories tested with examples

### Continuous Testing

- Run unit tests on every commit
- Run property tests on every pull request
- Run integration tests before deployment
- Monitor test execution time and optimize slow tests
