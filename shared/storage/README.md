# Storage Utilities

This module provides utilities for storing and retrieving data from S3 and Athena.

## Components

### S3Client

Basic S3 operations for reading and writing JSON files.

```python
from shared.storage import S3Client

s3_client = S3Client(
    bucket="brand-generator-rwrd-023-eu-west-1",
    region="eu-west-1"
)

# Write metadata
s3_client.write_metadata(brandid=123, metadata={"brandname": "Test"})

# Read metadata
metadata = s3_client.read_metadata(brandid=123)
```

### AthenaClient

Execute SQL queries against Athena database.

```python
from shared.storage import AthenaClient

athena_client = AthenaClient(
    database="brand_metadata_generator_db",
    region="eu-west-1"
)

# Execute query
results = athena_client.execute_query(
    "SELECT * FROM generated_metadata WHERE brandid = 123"
)

# Query table with filters
results = athena_client.query_table(
    table_name="generated_metadata",
    where="confidence_score < 0.5",
    limit=10
)
```

### DualStorageClient

**Recommended for all write operations** - Writes data to both S3 (as JSON) and Athena (via external tables) with transaction-like semantics.

```python
from shared.storage import DualStorageClient, DualStorageError

dual_storage = DualStorageClient(
    bucket="brand-generator-rwrd-023-eu-west-1",
    database="brand_metadata_generator_db",
    region="eu-west-1"
)

# Write metadata (writes to both S3 and Athena)
try:
    result = dual_storage.write_metadata(
        brandid=123,
        metadata={
            "brandname": "Test Brand",
            "regex": "test.*",
            "mccids": [5411, 5412],
            "confidence_score": 0.95
        }
    )
    print(f"Stored at: {result['s3_key']}")
except DualStorageError as e:
    print(f"Storage failed: {e}")

# Write feedback
result = dual_storage.write_feedback(
    brandid=123,
    feedback={
        "feedback_text": "The regex is incorrect",
        "category": "regex_correction"
    }
)
print(f"Feedback ID: {result['feedback_id']}")

# Write workflow execution
result = dual_storage.write_workflow_execution({
    "execution_arn": "arn:aws:states:eu-west-1:123456789012:execution:workflow:exec-123",
    "brandid": 123,
    "status": "SUCCEEDED",
    "duration_seconds": 45
})

# Write escalation
result = dual_storage.write_escalation({
    "brandid": 123,
    "brandname": "Test Brand",
    "reason": "Low confidence score",
    "confidence_score": 0.45
})
print(f"Escalation ID: {result['escalation_id']}")

# Read operations (reads from S3)
metadata = dual_storage.read_metadata(brandid=123)
feedback = dual_storage.read_feedback(brandid=123, feedback_id="uuid-123")
execution = dual_storage.read_workflow_execution(execution_id="exec-123")
escalation = dual_storage.read_escalation(brandid=123, escalation_id="esc-uuid")
```

## Dual Storage Features

### Transaction-like Semantics

The `DualStorageClient` implements rollback on failure:

1. Writes data to S3 first
2. Verifies Athena table is accessible
3. If verification fails, deletes the S3 object (rollback)

This ensures data consistency between S3 and Athena.

### Automatic Field Management

The dual storage client automatically adds required fields:

- **Metadata**: `brandid`, `generated_at`
- **Feedback**: `feedback_id`, `brandid`, `submitted_at`
- **Workflow Execution**: `start_time`
- **Escalation**: `escalation_id`, `escalated_at`, `status`

### Error Handling

```python
from shared.storage import DualStorageClient, DualStorageError

dual_storage = DualStorageClient()

try:
    result = dual_storage.write_metadata(brandid=123, metadata={...})
except DualStorageError as e:
    # Handle storage failure
    # If rollback also failed, manual cleanup may be required
    print(f"Error: {e}")
```

## Best Practices

1. **Use DualStorageClient for all writes** - Ensures data is available in both S3 and Athena
2. **Handle DualStorageError** - Always wrap write operations in try-except blocks
3. **Use read operations from DualStorageClient** - Provides consistent interface
4. **Query Athena for analytics** - Use AthenaClient for complex queries and aggregations
5. **Read from S3 for single records** - Faster than Athena for individual record retrieval

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  DualStorageClient                       │
│                                                          │
│  write_metadata()  ──┬──> S3Client.write_json()        │
│  write_feedback()    │                                   │
│  write_workflow()    └──> AthenaClient.execute_query()  │
│  write_escalation()       (verify table access)         │
│                                                          │
│  Rollback on failure: S3Client.delete_key()             │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    AWS Services                          │
│                                                          │
│  S3 Bucket: brand-generator-rwrd-023-eu-west-1          │
│  ├── metadata/brand_123.json                            │
│  ├── feedback/brand_123_uuid.json                       │
│  ├── workflow-executions/exec-123.json                  │
│  └── escalations/brand_123_uuid.json                    │
│                                                          │
│  Athena Database: brand_metadata_generator_db           │
│  ├── generated_metadata (external table → S3)           │
│  ├── feedback_history (external table → S3)             │
│  ├── workflow_executions (external table → S3)          │
│  └── escalations (external table → S3)                  │
└─────────────────────────────────────────────────────────┘
```

## Testing

Unit tests are available in `tests/unit/test_dual_storage.py`:

```bash
# Run dual storage tests
python -m pytest tests/unit/test_dual_storage.py -v

# Run with coverage
python -m pytest tests/unit/test_dual_storage.py --cov=shared.storage.dual_storage
```
