-- Glue table definition for workflow_executions
-- This table makes workflow execution history queryable via Athena
-- Schema matches the JSON structure stored in S3

CREATE EXTERNAL TABLE IF NOT EXISTS brand_metadata_generator_db.workflow_executions (
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
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/workflow-executions/'
TBLPROPERTIES (
  'has_encrypted_data'='false',
  'classification'='json'
);
