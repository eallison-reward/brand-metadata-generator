# MCP Troubleshooting Runbook

This runbook provides troubleshooting procedures for Model Context Protocol (MCP) integration in the Brand Metadata Generator system, specifically for the Commercial Assessment Agent's brand validation capabilities.

## Overview

The Commercial Assessment Agent uses MCP servers to validate brand existence and sector classification:
- **Brand Registry MCP Server**: Custom server querying Athena database
- **Crunchbase MCP Server** (optional): External brand validation

This runbook covers common MCP issues and their resolutions.

## Table of Contents

1. [MCP Architecture](#mcp-architecture)
2. [Common Issues](#common-issues)
3. [Diagnostic Procedures](#diagnostic-procedures)
4. [Resolution Procedures](#resolution-procedures)
5. [Performance Optimization](#performance-optimization)

## MCP Architecture

### Components

1. **Brand Registry MCP Server**
   - Location: `mcp_servers/brand_registry/server.py`
   - Protocol: stdio
   - Database: Athena (brand_metadata_generator_db)
   - Tools: `search_brands`, `get_brand_info`, `validate_sector`

2. **Commercial Assessment Agent**
   - Uses MCP tools for brand validation
   - Caches responses in DynamoDB
   - Falls back to web search if MCP fails

3. **MCP Configuration**
   - File: `.kiro/settings/mcp.json`
   - Defines server command and arguments
   - Environment variables for credentials

### Data Flow

```
Commercial Assessment Agent
  ↓
MCP Client (in agent)
  ↓
Brand Registry MCP Server
  ↓
Athena Database
  ↓
Glue Tables (brand, brand_to_check)
```

## Common Issues

### Issue 1: MCP Server Not Starting

**Symptoms**:
- Agent cannot invoke MCP tools
- Error: "MCP server not available"
- Commercial assessment fails

**Causes**:
- Python environment issues
- Missing dependencies
- Configuration errors
- Permission issues

**Diagnosis**:
```bash
# Test MCP server manually
cd mcp_servers/brand_registry
python server.py

# Check Python environment
python --version  # Should be 3.12+
pip list | grep mcp

# Check configuration
cat .kiro/settings/mcp.json
```

**Resolution**:

1. **Install Dependencies**
```bash
cd mcp_servers/brand_registry
pip install -r requirements.txt
```

2. **Verify Configuration**
```json
{
  "mcpServers": {
    "brand-registry": {
      "command": "python",
      "args": ["mcp_servers/brand_registry/server.py"],
      "env": {
        "AWS_REGION": "eu-west-1",
        "ATHENA_DATABASE": "brand_metadata_generator_db"
      }
    }
  }
}
```

3. **Test Server**
```bash
python scripts/test_mcp_connection.py
```

4. **Check Logs**
```bash
# MCP server logs
tail -f mcp_servers/brand_registry/mcp_server.log

# Agent logs
aws logs tail /aws/bedrock/agentcore/brand-metagen-commercial-assessment-prod \
  --follow \
  --region eu-west-1
```

### Issue 2: MCP Tool Invocation Failures

**Symptoms**:
- MCP server running but tool calls fail
- Error: "Tool not found"
- Error: "Invalid arguments"

**Causes**:
- Tool name mismatch
- Invalid arguments
- Schema validation errors
- Server-side errors

**Diagnosis**:
```bash
# Test specific tool
python scripts/test_mcp_tool.py \
  --server brand-registry \
  --tool search_brands \
  --args '{"query": "Starbucks"}'

# Check tool schema
python scripts/get_mcp_tools.py --server brand-registry
```

**Resolution**:

1. **Verify Tool Names**
```python
# Available tools
- search_brands
- get_brand_info
- validate_sector
```

2. **Check Arguments**
```python
# search_brands
{
  "query": "string",      # Required
  "sector": "string",     # Optional
  "limit": "integer"      # Optional, default 10
}

# get_brand_info
{
  "brandid": "integer"    # Required
}

# validate_sector
{
  "brandid": "integer",   # Required
  "sector": "string"      # Required
}
```

3. **Test Tool Directly**
```bash
# Test search_brands
python -c "
from mcp_servers.brand_registry.server import search_brands
result = search_brands({'query': 'Starbucks'})
print(result)
"
```

4. **Check Server Logs**
```bash
tail -f mcp_servers/brand_registry/mcp_server.log | grep ERROR
```

### Issue 3: Athena Query Failures

**Symptoms**:
- MCP tools return empty results
- Error: "Query execution failed"
- Timeout errors

**Causes**:
- Athena permissions issues
- Query syntax errors
- Table not found
- Workgroup issues

**Diagnosis**:
```bash
# Test Athena connection
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM brand" \
  --query-execution-context Database=brand_metadata_generator_db \
  --result-configuration OutputLocation=s3://brand-generator-rwrd-023-eu-west-1/athena-results/ \
  --region eu-west-1

# Check query status
aws athena get-query-execution \
  --query-execution-id <execution-id> \
  --region eu-west-1

# Test from Python
python -c "
import boto3
client = boto3.client('athena', region_name='eu-west-1')
response = client.start_query_execution(
    QueryString='SELECT COUNT(*) FROM brand',
    QueryExecutionContext={'Database': 'brand_metadata_generator_db'},
    ResultConfiguration={'OutputLocation': 's3://brand-generator-rwrd-023-eu-west-1/athena-results/'}
)
print(response)
"
```

**Resolution**:

1. **Verify IAM Permissions**
```bash
# Check agent execution role
aws iam get-role \
  --role-name brand_metagen_agent_execution_prod \
  --region eu-west-1

# Verify Athena permissions
aws iam get-role-policy \
  --role-name brand_metagen_agent_execution_prod \
  --policy-name brand_metagen_agent_policy \
  --region eu-west-1
```

2. **Test Athena Queries**
```bash
# Test brand table
python scripts/test_athena_query.py \
  --query "SELECT * FROM brand LIMIT 10"

# Test brand_to_check table
python scripts/test_athena_query.py \
  --query "SELECT * FROM brand_to_check LIMIT 10"
```

3. **Check Table Schemas**
```bash
aws glue get-table \
  --database-name brand_metadata_generator_db \
  --name brand \
  --region eu-west-1

aws glue get-table \
  --database-name brand_metadata_generator_db \
  --name brand_to_check \
  --region eu-west-1
```

4. **Verify S3 Access**
```bash
# Check S3 bucket access
aws s3 ls s3://brand-generator-rwrd-023-eu-west-1/

# Check Athena results location
aws s3 ls s3://brand-generator-rwrd-023-eu-west-1/athena-results/
```

### Issue 4: Slow MCP Response Times

**Symptoms**:
- MCP tool calls take >5 seconds
- Agent timeouts
- Poor user experience

**Causes**:
- Slow Athena queries
- Large result sets
- No caching
- Network latency

**Diagnosis**:
```bash
# Measure query time
time python scripts/test_mcp_tool.py \
  --server brand-registry \
  --tool search_brands \
  --args '{"query": "Starbucks"}'

# Check Athena query execution time
aws athena get-query-execution \
  --query-execution-id <execution-id> \
  --query 'QueryExecution.Statistics.TotalExecutionTimeInMillis' \
  --region eu-west-1

# Check cache hit rate
python scripts/check_mcp_cache.py
```

**Resolution**:

1. **Optimize Athena Queries**
```sql
-- Add WHERE clauses to limit data scanned
SELECT * FROM brand 
WHERE LOWER(brand_name) LIKE LOWER('%Starbucks%')
LIMIT 10;

-- Use partitioning if available
SELECT * FROM brand 
WHERE partition_key = 'value'
AND LOWER(brand_name) LIKE LOWER('%Starbucks%');
```

2. **Enable Caching**
```python
# Verify cache configuration in agent
# Check DynamoDB cache table
aws dynamodb describe-table \
  --table-name brand_metagen_mcp_cache_prod \
  --region eu-west-1

# Check cache entries
aws dynamodb scan \
  --table-name brand_metagen_mcp_cache_prod \
  --limit 10 \
  --region eu-west-1
```

3. **Adjust Timeouts**
```python
# In agent configuration
mcp_config = {
    "timeout": 10,  # Increase from 5 to 10 seconds
    "retry_attempts": 3,
    "cache_ttl": 3600  # 1 hour
}
```

4. **Monitor Performance**
```bash
# CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace BrandMetadataGenerator \
  --metric-name MCPResponseTime \
  --start-time 2026-02-14T00:00:00Z \
  --end-time 2026-02-14T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum \
  --region eu-west-1
```

### Issue 5: Cache Inconsistencies

**Symptoms**:
- Stale data returned
- Recent updates not reflected
- Inconsistent results

**Causes**:
- Long cache TTL
- Cache not invalidated on updates
- Clock skew

**Diagnosis**:
```bash
# Check cache entries
python scripts/inspect_mcp_cache.py \
  --key "search_brands:Starbucks"

# Check cache age
python scripts/check_cache_age.py

# Compare cached vs fresh data
python scripts/compare_cache_fresh.py \
  --query "Starbucks"
```

**Resolution**:

1. **Adjust Cache TTL**
```python
# Reduce TTL for frequently changing data
cache_config = {
    "ttl": 1800,  # 30 minutes instead of 1 hour
    "max_entries": 1000
}
```

2. **Invalidate Cache**
```bash
# Clear specific cache entry
python scripts/invalidate_cache.py \
  --key "search_brands:Starbucks"

# Clear all cache
python scripts/clear_mcp_cache.py --confirm
```

3. **Implement Cache Invalidation**
```python
# On data updates, invalidate related cache entries
def update_brand_data(brandid, updates):
    # Update data
    update_database(brandid, updates)
    
    # Invalidate cache
    invalidate_cache(f"get_brand_info:{brandid}")
    invalidate_cache(f"search_brands:*")  # Wildcard invalidation
```

## Diagnostic Procedures

### Procedure 1: End-to-End MCP Test

**Purpose**: Verify complete MCP pipeline

**Steps**:
```bash
# 1. Test MCP server
python scripts/test_mcp_connection.py

# 2. Test each tool
python scripts/test_mcp_tool.py \
  --server brand-registry \
  --tool search_brands \
  --args '{"query": "Starbucks"}'

python scripts/test_mcp_tool.py \
  --server brand-registry \
  --tool get_brand_info \
  --args '{"brandid": 12345}'

python scripts/test_mcp_tool.py \
  --server brand-registry \
  --tool validate_sector \
  --args '{"brandid": 12345, "sector": "Food & Beverage"}'

# 3. Test from agent
python scripts/test_agent_mcp.py \
  --agent commercial_assessment \
  --test-case brand_validation

# 4. Check logs
aws logs tail /aws/bedrock/agentcore/brand-metagen-commercial-assessment-prod \
  --follow \
  --region eu-west-1
```

### Procedure 2: Performance Profiling

**Purpose**: Identify performance bottlenecks

**Steps**:
```bash
# 1. Profile MCP tool execution
python scripts/profile_mcp_tool.py \
  --server brand-registry \
  --tool search_brands \
  --args '{"query": "Starbucks"}' \
  --iterations 100

# 2. Profile Athena queries
python scripts/profile_athena_queries.py \
  --queries queries.sql

# 3. Analyze results
python scripts/analyze_mcp_performance.py \
  --profile-data profile_results.json

# 4. Generate report
python scripts/generate_performance_report.py \
  --output mcp_performance_report.pdf
```

### Procedure 3: Cache Analysis

**Purpose**: Analyze cache effectiveness

**Steps**:
```bash
# 1. Get cache statistics
python scripts/get_cache_stats.py

# 2. Analyze cache hit rate
python scripts/analyze_cache_hits.py \
  --start-date 2026-02-01 \
  --end-date 2026-02-14

# 3. Identify frequently accessed keys
python scripts/get_top_cache_keys.py --limit 50

# 4. Identify stale entries
python scripts/find_stale_cache.py --age-threshold 3600
```

## Resolution Procedures

### Procedure 1: Restart MCP Server

**When to Use**: Server unresponsive or crashed

**Steps**:
```bash
# 1. Stop server (if running)
pkill -f "brand_registry/server.py"

# 2. Clear any locks
rm -f mcp_servers/brand_registry/.lock

# 3. Start server
cd mcp_servers/brand_registry
python server.py &

# 4. Verify startup
python scripts/test_mcp_connection.py

# 5. Check logs
tail -f mcp_servers/brand_registry/mcp_server.log
```

### Procedure 2: Rebuild MCP Cache

**When to Use**: Cache corrupted or inconsistent

**Steps**:
```bash
# 1. Backup current cache
python scripts/backup_mcp_cache.py \
  --output mcp_cache_backup_$(date +%Y%m%d).json

# 2. Clear cache
python scripts/clear_mcp_cache.py --confirm

# 3. Warm cache with common queries
python scripts/warm_mcp_cache.py \
  --queries common_queries.txt

# 4. Verify cache
python scripts/verify_mcp_cache.py
```

### Procedure 3: Update MCP Server

**When to Use**: Bug fixes or feature updates

**Steps**:
```bash
# 1. Test changes in dev
cd mcp_servers/brand_registry
git pull origin main

# 2. Run tests
pytest tests/

# 3. Deploy to dev
python scripts/deploy_mcp_server.py --environment dev

# 4. Test in dev
python scripts/test_mcp_integration.py --environment dev

# 5. Deploy to prod
python scripts/deploy_mcp_server.py --environment prod

# 6. Monitor
aws logs tail /aws/bedrock/agentcore/brand-metagen-commercial-assessment-prod \
  --follow \
  --region eu-west-1
```

## Performance Optimization

### Optimization 1: Query Optimization

**Strategies**:
1. Add indexes to Athena tables
2. Use partitioning for large tables
3. Limit result set sizes
4. Use EXPLAIN to analyze queries

**Example**:
```sql
-- Before
SELECT * FROM brand WHERE brand_name LIKE '%Starbucks%';

-- After
SELECT brandid, brand_name, sector 
FROM brand 
WHERE LOWER(brand_name) LIKE LOWER('%Starbucks%')
LIMIT 10;
```

### Optimization 2: Caching Strategy

**Strategies**:
1. Cache frequently accessed data
2. Use appropriate TTL values
3. Implement cache warming
4. Monitor cache hit rates

**Configuration**:
```python
cache_config = {
    # Frequently accessed, rarely changes
    "get_brand_info": {"ttl": 3600},  # 1 hour
    
    # Frequently accessed, changes occasionally
    "search_brands": {"ttl": 1800},   # 30 minutes
    
    # Less frequently accessed
    "validate_sector": {"ttl": 7200}  # 2 hours
}
```

### Optimization 3: Connection Pooling

**Strategies**:
1. Reuse Athena connections
2. Implement connection pooling
3. Manage connection lifecycle

**Example**:
```python
# Connection pool
from shared.storage.athena_client import AthenaClient

# Reuse client instance
athena_client = AthenaClient(region='eu-west-1')

# Use for multiple queries
result1 = athena_client.execute_query(query1)
result2 = athena_client.execute_query(query2)
```

## Additional Resources

- [MCP Setup Guide](../MCP_SETUP_GUIDE.md)
- [Brand Registry MCP Server README](../../mcp_servers/brand_registry/README.md)
- [Commercial Assessment Agent](../../agents/commercial_assessment/README.md)
- [Athena Client Documentation](../../shared/storage/athena_client.py)
- [Production Monitoring Setup](../PRODUCTION_MONITORING_SETUP.md)
