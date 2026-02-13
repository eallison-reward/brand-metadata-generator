# QuickSight Dashboard Setup Guide

This guide provides step-by-step instructions for setting up the AWS QuickSight dashboard for monitoring the Brand Metadata Generator system.

## Prerequisites

1. AWS QuickSight subscription (Enterprise or Standard edition)
2. QuickSight user account with appropriate permissions
3. Athena database `brand_metadata_generator_db` deployed and populated
4. IAM permissions to access Athena and S3

## Step 1: Enable QuickSight Access to Athena

1. Navigate to AWS QuickSight console
2. Click on your user icon (top right) → Manage QuickSight
3. Go to Security & permissions
4. Under QuickSight access to AWS services, click "Manage"
5. Enable:
   - Amazon Athena
   - Amazon S3
6. Select the S3 bucket: `brand-generator-rwrd-023-eu-west-1`
7. Click "Update"

## Step 2: Create Athena Data Source

1. In QuickSight, click "Datasets" in the left navigation
2. Click "New dataset"
3. Select "Athena" as the data source
4. Configure:
   - Data source name: `Brand Metadata Generator Athena`
   - Athena workgroup: `primary`
5. Click "Create data source"

## Step 3: Create Data Sets

### Data Set 1: Brand Processing Status

1. Click "New dataset" → Select the Athena data source
2. Choose "Use custom SQL"
3. Name: `Brand Processing Status`
4. SQL Query:
```sql
SELECT 
  brandid,
  brandname,
  processing_status,
  metadata_generated,
  combos_matched,
  combos_confirmed,
  combos_excluded,
  requires_human_review,
  confidence_score,
  last_updated
FROM brand_metadata_generator_db.brand
WHERE processing_status IS NOT NULL
ORDER BY last_updated DESC
```
5. Click "Confirm query"
6. Choose "Directly query your data"
7. Click "Visualize"

### Data Set 2: Combo Matching Statistics

1. Click "New dataset" → Select the Athena data source
2. Choose "Use custom SQL"
3. Name: `Combo Matching Statistics`
4. SQL Query:
```sql
SELECT 
  b.brandid,
  b.brandname,
  b.sector,
  COUNT(DISTINCT c.ccid) as total_combos,
  COUNT(DISTINCT CASE WHEN c.confirmed = true THEN c.ccid END) as confirmed_combos,
  COUNT(DISTINCT CASE WHEN c.excluded = true THEN c.ccid END) as excluded_combos,
  COUNT(DISTINCT CASE WHEN c.requires_review = true THEN c.ccid END) as review_required,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN c.confirmed = true THEN c.ccid END) / 
        NULLIF(COUNT(DISTINCT c.ccid), 0), 2) as confirmation_rate
FROM brand_metadata_generator_db.brand b
LEFT JOIN brand_metadata_generator_db.combo c ON b.brandid = c.brandid
GROUP BY b.brandid, b.brandname, b.sector
HAVING COUNT(DISTINCT c.ccid) > 0
```
5. Click "Confirm query"
6. Choose "Directly query your data"
7. Click "Visualize"

### Data Set 3: Tie Resolution Status

1. Click "New dataset" → Select the Athena data source
2. Choose "Use custom SQL"
3. Name: `Tie Resolution Status`
4. SQL Query:
```sql
SELECT 
  c.ccid,
  c.bankid,
  c.narrative,
  c.mccid,
  m.mcc_desc,
  c.matched_brands,
  c.resolution_status,
  c.selected_brandid,
  b.brandname as selected_brand,
  c.confidence_score,
  c.requires_human_review
FROM brand_metadata_generator_db.combo c
LEFT JOIN brand_metadata_generator_db.mcc m ON c.mccid = m.mccid
LEFT JOIN brand_metadata_generator_db.brand b ON c.selected_brandid = b.brandid
WHERE c.matched_brands > 1
ORDER BY c.requires_human_review DESC, c.confidence_score ASC
```
5. Click "Confirm query"
6. Choose "Directly query your data"
7. Click "Visualize"

### Data Set 4: Human Review Queue

1. Click "New dataset" → Select the Athena data source
2. Choose "Use custom SQL"
3. Name: `Human Review Queue`
4. SQL Query:
```sql
SELECT 
  b.brandid,
  b.brandname,
  b.sector,
  b.regex_pattern,
  b.mccid_list,
  c.ccid,
  c.narrative,
  c.mccid,
  m.mcc_desc,
  c.confidence_score,
  c.review_reason,
  c.flagged_at
FROM brand_metadata_generator_db.brand b
JOIN brand_metadata_generator_db.combo c ON b.brandid = c.brandid
LEFT JOIN brand_metadata_generator_db.mcc m ON c.mccid = m.mccid
WHERE c.requires_review = true OR b.requires_human_review = true
ORDER BY c.flagged_at DESC
```
5. Click "Confirm query"
6. Choose "Directly query your data"
7. Click "Visualize"

## Step 4: Create Dashboard Analysis

1. Click "Analyses" in the left navigation
2. Click "New analysis"
3. Select "Brand Processing Status" dataset
4. Click "Create analysis"

### Add Visualizations

#### 1. Brand Processing Overview (KPIs)

1. Click "Add" → "Add visual"
2. Select "KPI" visual type
3. Add fields:
   - Value: `brandid` (Count Distinct)
   - Trend: `last_updated`
4. Title: "Total Brands"
5. Repeat for:
   - "Brands Processed" (filter: `processing_status = 'completed'`)
   - "Brands In Progress" (filter: `processing_status = 'in_progress'`)
   - "Brands Pending" (filter: `processing_status = 'pending'`)

#### 2. Brand Processing Status Chart

1. Click "Add" → "Add visual"
2. Select "Donut chart" visual type
3. Add fields:
   - Group/Color: `processing_status`
   - Value: `brandid` (Count Distinct)
4. Title: "Brands by Processing Status"

#### 3. Brands Requiring Human Review

1. Click "Add" → "Add visual"
2. Select "Table" visual type
3. Add fields:
   - `brandid`
   - `brandname`
   - `processing_status`
   - `requires_human_review`
   - `confidence_score`
   - `last_updated`
4. Add filter: `requires_human_review = true`
5. Title: "Brands Flagged for Human Review"
6. Enable sorting by `last_updated` (descending)

#### 4. Combo Matching Statistics

1. Add the "Combo Matching Statistics" dataset to the analysis
2. Click "Add" → "Add visual"
3. Select "Horizontal bar chart" visual type
4. Add fields:
   - Y axis: `brandname`
   - Value: `total_combos`
   - Group/Color: Split by confirmed/excluded/review_required
5. Title: "Combo Matching Results by Brand"

#### 5. Confirmation Rate by Brand

1. Click "Add" → "Add visual"
2. Select "Horizontal bar chart" visual type
3. Add fields:
   - Y axis: `brandname`
   - Value: `confirmation_rate`
4. Title: "Combo Confirmation Rate (%)"
5. Sort by `confirmation_rate` (ascending) to show problematic brands first

#### 6. Tie Resolution Status

1. Add the "Tie Resolution Status" dataset to the analysis
2. Click "Add" → "Add visual"
3. Select "Table" visual type
4. Add fields:
   - `ccid`
   - `narrative`
   - `matched_brands`
   - `resolution_status`
   - `selected_brand`
   - `confidence_score`
   - `requires_human_review`
5. Title: "Tie Resolution Queue"
6. Enable drill-down on `ccid` to see full details

#### 7. Human Review Queue

1. Add the "Human Review Queue" dataset to the analysis
2. Click "Add" → "Add visual"
3. Select "Table" visual type
4. Add fields:
   - `brandname`
   - `narrative`
   - `mcc_desc`
   - `confidence_score`
   - `review_reason`
   - `flagged_at`
5. Title: "Combos Requiring Human Review"
6. Enable sorting by `flagged_at` (descending)

## Step 5: Publish Dashboard

1. Click "Share" in the top right
2. Click "Publish dashboard"
3. Dashboard name: `Brand Metadata Generator - ${ENVIRONMENT}`
4. Click "Publish dashboard"

## Step 6: Share with Operators

1. Click "Share" → "Share dashboard"
2. Add users or groups who need access
3. Set permissions:
   - Viewer: Can view dashboard only
   - Co-owner: Can edit dashboard
4. Click "Share"

## Step 7: Configure Auto-Refresh

1. In the dashboard, click the three dots (⋮) in the top right
2. Select "Schedule refresh"
3. Configure:
   - Frequency: Every 15 minutes (or as needed)
   - Time zone: UTC
4. Click "Save"

## Dashboard Usage

### Monitoring Brand Processing

- Check the KPIs at the top for overall progress
- Review the "Brands by Processing Status" chart for distribution
- Monitor the "Brands Flagged for Human Review" table for items needing attention

### Reviewing Combo Matches

- Use the "Combo Matching Results by Brand" chart to identify brands with many exclusions
- Check the "Combo Confirmation Rate" chart to find brands with low confirmation rates
- These may indicate issues with regex patterns or MCCID lists

### Handling Ties

- Review the "Tie Resolution Queue" table for combos matching multiple brands
- Sort by `confidence_score` to prioritize low-confidence ties
- Use drill-down to see full combo details

### Human Review Workflow

1. Open the "Combos Requiring Human Review" table
2. Review each combo's narrative and context
3. Make decisions in the application (approve/reject)
4. Refresh the dashboard to see updated status

## Troubleshooting

### Data Not Appearing

- Verify Athena database `brand_metadata_generator_db` exists and has data
- Check QuickSight permissions to access Athena and S3
- Verify the SQL queries run successfully in Athena console

### Slow Performance

- Consider using SPICE (QuickSight's in-memory engine) instead of direct query
- Add filters to limit data volume
- Optimize Athena queries with partitioning

### Access Denied Errors

- Verify QuickSight has permissions to access the S3 bucket
- Check IAM roles and policies
- Ensure Athena workgroup permissions are correct

## Additional Resources

- [AWS QuickSight Documentation](https://docs.aws.amazon.com/quicksight/)
- [Athena Integration Guide](https://docs.aws.amazon.com/quicksight/latest/user/create-a-data-set-athena.html)
- [QuickSight Best Practices](https://docs.aws.amazon.com/quicksight/latest/user/best-practices.html)
