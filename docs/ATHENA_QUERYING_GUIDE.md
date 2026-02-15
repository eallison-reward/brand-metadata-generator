# Athena Querying Guide for Brand Metadata Generator

## Overview

This guide explains how to query the brand metadata generator results using AWS Athena. The system stores both input data and processing results in S3, making them queryable through Athena external tables.

## Table Structure

### Input Tables (Source Data)

These tables contain the original data used for metadata generation:

#### `brand`
```sql
-- Brand master data
SELECT * FROM brand_metadata_generator_db.brand LIMIT 5;
```
- `brandid` (int): Unique brand identifier
- `brandname` (string): Brand name (e.g., "Starbucks")
- `sector` (string): Business sector (e.g., "Food & Beverage")

#### `brand_to_check`
```sql
-- Brands requiring metadata generation
SELECT * FROM brand_metadata_generator_db.brand_to_check LIMIT 5;
```
- `brandid` (int): Brand ID to process

#### `combo`
```sql
-- Transaction combo records
SELECT * FROM brand_metadata_generator_db.combo LIMIT 5;
```
- `ccid` (int): Combo ID (composite key with bankid)
- `bankid` (tinyint): Bank identifier (composite key with ccid)
- `mid` (string): Merchant ID
- `brandid` (int): Associated brand ID
- `mccid` (int): Merchant Category Code ID
- `narrative` (string): Transaction description

#### `mcc`
```sql
-- Merchant Category Codes
SELECT * FROM brand_metadata_generator_db.mcc LIMIT 5;
```
- `mccid` (int): MCC identifier
- `mcc_desc` (string): MCC description
- `sector` (string): Business sector

### Output Tables (Generated Results)

These tables contain the results from the brand metadata generation workflow:

#### `brand_metadata`
```sql
-- Generated brand metadata and combo classifications
SELECT * FROM brand_metadata_generator_db.brand_metadata LIMIT 5;
```
- `brandid` (int): Brand identifier
- `brandname` (string): Brand name
- `sector` (string): Business sector
- `regex_pattern` (string): Generated regex for narrative matching
- `mccids` (array<int>): List of valid MCCIDs for this brand
- `confidence_score` (double): Quality confidence (0.0-1.0)
- `total_matched` (int): Total combos that matched metadata
- `total_confirmed` (int): Combos confirmed by Confirmation Agent
- `total_excluded` (int): Combos excluded as false positives
- `exclusion_rate` (double): Percentage of matches excluded
- `processing_date` (string): When metadata was generated

#### `combo_classifications`
```sql
-- Individual combo classification results
SELECT * FROM brand_metadata_generator_db.combo_classifications LIMIT 5;
```
- `ccid` (int): Combo ID
- `bankid` (tinyint): Bank identifier
- `brandid` (int): Assigned brand ID
- `brandname` (string): Brand name
- `classification_type` (string): 'confirmed', 'excluded', 'tie_resolved'
- `exclusion_reason` (string): Why combo was excluded (if applicable)
- `tie_resolution` (string): How multi-brand match was resolved
- `processing_date` (string): When classification was made

## Common Query Patterns

### 1. Brand Performance Analysis

**Find brands with high confidence scores:**
```sql
SELECT 
    brandname,
    confidence_score,
    total_matched,
    total_confirmed,
    exclusion_rate
FROM brand_metadata_generator_db.brand_metadata 
WHERE confidence_score > 0.9
ORDER BY confidence_score DESC;
```

**Brands with high exclusion rates (potential false positives):**
```sql
SELECT 
    brandname,
    total_matched,
    total_excluded,
    exclusion_rate,
    regex_pattern
FROM brand_metadata_generator_db.brand_metadata 
WHERE exclusion_rate > 0.2
ORDER BY exclusion_rate DESC;
```

### 2. Combo Classification Analysis

**Find all confirmed combos for a specific brand:**
```sql
SELECT 
    cc.ccid,
    cc.bankid,
    c.narrative,
    c.mccid
FROM brand_metadata_generator_db.combo_classifications cc
JOIN brand_metadata_generator_db.combo c 
    ON cc.ccid = c.ccid AND cc.bankid = c.bankid
WHERE cc.brandname = 'Starbucks'
    AND cc.classification_type = 'confirmed';
```

**Most common exclusion reasons:**
```sql
SELECT 
    exclusion_reason,
    COUNT(*) as frequency,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM brand_metadata_generator_db.combo_classifications 
WHERE classification_type = 'excluded'
    AND exclusion_reason IS NOT NULL
GROUP BY exclusion_reason
ORDER BY frequency DESC;
```

### 3. Cross-Reference Analysis

**Compare original brand assignments with new classifications:**
```sql
SELECT 
    c.brandid as original_brandid,
    b1.brandname as original_brand,
    cc.brandid as new_brandid,
    cc.brandname as new_brand,
    c.narrative,
    c.mccid
FROM brand_metadata_generator_db.combo c
JOIN brand_metadata_generator_db.brand b1 ON c.brandid = b1.brandid
JOIN brand_metadata_generator_db.combo_classifications cc 
    ON c.ccid = cc.ccid AND c.bankid = cc.bankid
WHERE c.brandid != cc.brandid
    AND cc.classification_type = 'confirmed'
LIMIT 100;
```

**Find combos that were reassigned between processing runs:**
```sql
SELECT 
    c1.ccid,
    c1.bankid,
    c1.brandname as previous_brand,
    c2.brandname as current_brand,
    c.narrative
FROM brand_metadata_generator_db.combo_classifications c1
JOIN brand_metadata_generator_db.combo_classifications c2 
    ON c1.ccid = c2.ccid AND c1.bankid = c2.bankid
JOIN brand_metadata_generator_db.combo c 
    ON c1.ccid = c.ccid AND c1.bankid = c.bankid
WHERE c1.processing_date < c2.processing_date
    AND c1.brandid != c2.brandid
    AND c1.classification_type = 'confirmed'
    AND c2.classification_type = 'confirmed';
```

### 4. Pattern Analysis

**Analyze regex patterns by sector:**
```sql
SELECT 
    sector,
    COUNT(*) as brand_count,
    AVG(confidence_score) as avg_confidence,
    AVG(exclusion_rate) as avg_exclusion_rate
FROM brand_metadata_generator_db.brand_metadata
GROUP BY sector
ORDER BY brand_count DESC;
```

**Find brands with similar regex patterns:**
```sql
SELECT 
    b1.brandname as brand1,
    b2.brandname as brand2,
    b1.regex_pattern,
    b2.regex_pattern
FROM brand_metadata_generator_db.brand_metadata b1
JOIN brand_metadata_generator_db.brand_metadata b2 
    ON b1.brandid < b2.brandid
WHERE LEVENSHTEIN_DISTANCE(b1.regex_pattern, b2.regex_pattern) < 5
    AND b1.brandname != b2.brandname;
```

### 5. Temporal Analysis

**Track improvements over time:**
```sql
SELECT 
    processing_date,
    COUNT(*) as brands_processed,
    AVG(confidence_score) as avg_confidence,
    AVG(exclusion_rate) as avg_exclusion_rate,
    SUM(total_confirmed) as total_combos_confirmed
FROM brand_metadata_generator_db.brand_metadata
GROUP BY processing_date
ORDER BY processing_date;
```

**Find brands that improved over multiple processing runs:**
```sql
WITH brand_improvements AS (
    SELECT 
        brandid,
        brandname,
        processing_date,
        confidence_score,
        LAG(confidence_score) OVER (PARTITION BY brandid ORDER BY processing_date) as prev_confidence
    FROM brand_metadata_generator_db.brand_metadata
)
SELECT 
    brandname,
    processing_date,
    prev_confidence,
    confidence_score,
    confidence_score - prev_confidence as improvement
FROM brand_improvements
WHERE prev_confidence IS NOT NULL
    AND confidence_score > prev_confidence
ORDER BY improvement DESC;
```

## Advanced Querying Techniques

### JSON Extraction (for raw S3 data)

If querying JSON files directly from S3:

```sql
-- Query metadata JSON files directly
SELECT 
    json_extract_scalar(data, '$.brandid') as brandid,
    json_extract_scalar(data, '$.brandname') as brandname,
    json_extract_scalar(data, '$.metadata.regex_pattern') as regex_pattern,
    json_extract(data, '$.metadata.mccids') as mccids,
    cast(json_extract_scalar(data, '$.metadata.confidence_score') as double) as confidence_score
FROM (
    SELECT json_parse(line) as data
    FROM s3_raw_metadata_table
)
WHERE json_extract_scalar(data, '$.brandid') IS NOT NULL;
```

### Array Operations

**Working with MCCID arrays:**
```sql
-- Find brands that use specific MCCIDs
SELECT 
    brandname,
    mccids,
    confidence_score
FROM brand_metadata_generator_db.brand_metadata
WHERE contains(mccids, 5812); -- 5812 = Eating Places, Restaurants

-- Count unique MCCIDs across all brands
SELECT 
    mccid,
    COUNT(*) as brand_count
FROM brand_metadata_generator_db.brand_metadata
CROSS JOIN UNNEST(mccids) as t(mccid)
GROUP BY mccid
ORDER BY brand_count DESC;
```

### Window Functions

**Ranking and percentiles:**
```sql
-- Rank brands by confidence score within each sector
SELECT 
    brandname,
    sector,
    confidence_score,
    RANK() OVER (PARTITION BY sector ORDER BY confidence_score DESC) as sector_rank,
    PERCENT_RANK() OVER (ORDER BY confidence_score) as confidence_percentile
FROM brand_metadata_generator_db.brand_metadata
ORDER BY sector, sector_rank;
```

## Performance Optimization

### Partitioning

For large datasets, partition tables by processing date:

```sql
-- Create partitioned table for better performance
CREATE EXTERNAL TABLE brand_metadata_partitioned (
    brandid int,
    brandname string,
    confidence_score double,
    -- ... other columns
)
PARTITIONED BY (
    processing_date string
)
STORED AS PARQUET
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/partitioned-metadata/';

-- Query specific date range efficiently
SELECT * FROM brand_metadata_partitioned 
WHERE processing_date >= '2024-01-01' 
    AND processing_date < '2024-02-01';
```

### Query Optimization Tips

1. **Use column pruning**: Only select columns you need
2. **Filter early**: Apply WHERE clauses before JOINs when possible
3. **Use appropriate data types**: Cast strings to numbers for numeric operations
4. **Leverage partitioning**: Always include partition columns in WHERE clauses
5. **Use LIMIT**: For exploratory queries, use LIMIT to reduce costs

## Cost Management

**Estimate query costs:**
```sql
-- Check data scanned by previous queries
SELECT 
    query_id,
    query,
    data_scanned_in_bytes / 1024 / 1024 / 1024 as data_scanned_gb,
    execution_time_in_millis / 1000 as execution_time_seconds
FROM information_schema.query_history
WHERE creation_time > current_timestamp - interval '1' day
ORDER BY data_scanned_in_bytes DESC;
```

**Optimize for cost:**
- Use columnar formats (Parquet) for better compression
- Partition large tables by date
- Use appropriate WHERE clauses to limit data scanned
- Consider using views for commonly used complex queries

## Integration with Applications

### Using the Conversational Agent

The conversational interface agent provides a natural language interface to these queries:

```
"Show me brands with confidence scores above 0.9"
"Find combos that were excluded for brand Starbucks"
"What are the most common exclusion reasons?"
"Show me brands that improved over time"
```

### Programmatic Access

Use the `execute_athena_query` tool in Lambda functions:

```python
from shared.storage import AthenaClient

athena_client = AthenaClient(
    database="brand_metadata_generator_db",
    region="eu-west-1"
)

# Execute custom query
results = athena_client.execute_query("""
    SELECT brandname, confidence_score 
    FROM brand_metadata 
    WHERE confidence_score > 0.9
    ORDER BY confidence_score DESC
""")

# Use predefined query templates
results = athena_client.query_table(
    table_name="brand_metadata",
    where="exclusion_rate > 0.2",
    order_by="exclusion_rate DESC",
    limit=10
)
```

## Troubleshooting

### Common Issues

1. **Table not found**: Ensure Glue tables are created and S3 data exists
2. **Permission denied**: Check IAM permissions for Athena and S3
3. **Query timeout**: Optimize query or increase timeout settings
4. **High costs**: Use partitioning and column pruning

### Diagnostic Queries

```sql
-- Check table existence
SHOW TABLES IN brand_metadata_generator_db;

-- Check table schema
DESCRIBE brand_metadata_generator_db.brand_metadata;

-- Check data availability
SELECT COUNT(*) FROM brand_metadata_generator_db.brand_metadata;

-- Check recent processing dates
SELECT DISTINCT processing_date 
FROM brand_metadata_generator_db.brand_metadata 
ORDER BY processing_date DESC;
```

## Next Steps

1. **Create missing tables**: Run the table creation scripts for output tables
2. **Set up partitioning**: Implement date-based partitioning for large datasets
3. **Create views**: Build commonly used query patterns as views
4. **Set up monitoring**: Track query performance and costs
5. **Build dashboards**: Connect to BI tools for visualization

For more information, see:
- [Storage README](../shared/storage/README.md) - Storage utilities and APIs
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Infrastructure setup
- [MCP Troubleshooting](docs/runbooks/MCP_TROUBLESHOOTING_RUNBOOK.md) - Query troubleshooting