# Conversational Interface Agent

The Conversational Interface Agent provides a natural language interface for interacting with the Brand Metadata Generator system through AWS Bedrock Console.

## Overview

This agent enables users to:
- Start and monitor brand processing workflows
- Submit feedback on generated metadata
- Query brand data and system statistics
- Monitor system health and escalations

## Architecture

The agent is built using AWS Bedrock AgentCore with the Strands API and consists of:

1. **Agent Handler** (`agentcore_handler.py`): Main agent implementation using Strands API
2. **Tool Definitions** (`tools.py`): Tool schemas and configurations for the agent
3. **Tool Lambda Functions**: 8 Lambda functions that implement backend operations

## Tool Lambda Functions

The agent uses the following Lambda functions as tools:

1. **query_brands_to_check**: Query brands_to_check Athena table
2. **start_workflow**: Start Step Functions workflows for brand processing
3. **check_workflow_status**: Query workflow execution status
4. **submit_feedback**: Submit feedback to feedback processing system
5. **query_metadata**: Retrieve brand metadata from S3
6. **execute_athena_query**: Execute parameterized Athena queries
7. **list_escalations**: List brands awaiting human review
8. **get_workflow_stats**: Get workflow execution statistics

## Directory Structure

```
agents/conversational_interface/
├── __init__.py
├── README.md
├── agentcore_handler.py    # Agent implementation
└── tools.py                 # Tool definitions

lambda_functions/
├── query_brands_to_check/
│   ├── __init__.py
│   └── handler.py
├── start_workflow/
│   ├── __init__.py
│   └── handler.py
├── check_workflow_status/
│   ├── __init__.py
│   └── handler.py
├── submit_feedback/
│   ├── __init__.py
│   └── handler.py
├── query_metadata/
│   ├── __init__.py
│   └── handler.py
├── execute_athena_query/
│   ├── __init__.py
│   └── handler.py
├── list_escalations/
│   ├── __init__.py
│   └── handler.py
└── get_workflow_stats/
    ├── __init__.py
    └── handler.py

shared/utils/
├── __init__.py
├── error_handler.py         # Error handling utilities
├── logger.py                # Logging utilities
└── base_handler.py          # Base class for Lambda handlers
```

## Shared Utilities

### Error Handler (`shared/utils/error_handler.py`)

Provides structured error handling with four error categories:
- **USER_INPUT**: Invalid parameters, ambiguous requests
- **BACKEND_SERVICE**: Step Functions failures, Athena errors, S3 issues
- **PERMISSION**: IAM permission denials
- **SYSTEM**: Timeouts, unexpected exceptions

Key classes:
- `ToolError`: Base exception class
- `UserInputError`, `BackendServiceError`, `PermissionError`, `SystemError`: Specific error types
- `handle_aws_error()`: Converts AWS SDK errors to ToolError instances
- `create_error_response()`: Creates standardized error responses

### Logger (`shared/utils/logger.py`)

Provides structured logging for CloudWatch:
- `setup_logger()`: Configure logger with consistent formatting
- `log_tool_execution()`: Log tool execution with structured data
- `ToolLogger`: Context manager for automatic execution logging

### Base Handler (`shared/utils/base_handler.py`)

Base classes for Lambda function handlers:
- `BaseToolHandler`: Standard handler with validation and error handling
- `RetryableToolHandler`: Handler with automatic retry logic

## Usage

### Implementing a Tool Lambda Function

```python
from shared.utils.base_handler import BaseToolHandler
from shared.utils.error_handler import UserInputError

class MyToolHandler(BaseToolHandler):
    def __init__(self):
        super().__init__("my_tool")
    
    def get_required_params(self):
        return ["param1", "param2"]
    
    def validate_parameters(self, parameters):
        self.validate_required_params(parameters)
        # Add custom validation
    
    def execute(self, parameters):
        # Implement tool logic
        result = do_something(parameters)
        return {"result": result}

# Lambda handler
handler = MyToolHandler()

def lambda_handler(event, context):
    return handler.handle(event, context)
```

### Request Format

All tool Lambda functions expect this format:

```json
{
  "tool_name": "my_tool",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  },
  "request_id": "uuid-string",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Response Format

Success response:

```json
{
  "success": true,
  "data": {
    "result": "..."
  },
  "request_id": "uuid-string",
  "timestamp": "2024-01-01T00:00:00Z",
  "execution_time_ms": 123
}
```

Error response:

```json
{
  "success": false,
  "error": {
    "type": "user_input",
    "message": "User-friendly error message",
    "details": "Technical details",
    "suggestion": "Actionable next step"
  },
  "request_id": "uuid-string",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Configuration

- **AWS Region**: eu-west-1
- **S3 Bucket**: brand-generator-rwrd-023-eu-west-1
- **Athena Database**: brand_metadata_generator_db
- **Python Version**: 3.12
- **Model**: Claude 3 Sonnet (via Bedrock)

## Deployment

See the deployment guide in `docs/AGENT_DEPLOYMENT_GUIDE.md` for instructions on deploying the agent and Lambda functions.

## Testing

Tests are organized by type:
- **Unit Tests**: `tests/unit/test_conversational_interface.py`
- **Property Tests**: `tests/property/test_conversational_interface_properties.py`
- **Integration Tests**: `tests/integration/test_conversational_interface_workflow.py`

Run tests with:
```bash
pytest tests/unit/test_conversational_interface.py
pytest tests/property/test_conversational_interface_properties.py
pytest tests/integration/test_conversational_interface_workflow.py
```

## Requirements

See `requirements.txt` for Python dependencies. Key dependencies:
- boto3 (AWS SDK)
- strands-api (Bedrock AgentCore)
- hypothesis (property-based testing)
