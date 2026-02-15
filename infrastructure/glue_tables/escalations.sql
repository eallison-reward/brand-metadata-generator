-- Glue table definition for escalations
-- This table makes escalation records queryable via Athena
-- Schema matches the JSON structure stored in S3

CREATE EXTERNAL TABLE IF NOT EXISTS brand_metadata_generator_db.escalations (
  escalation_id STRING,
  brandid INT,
  brandname STRING,
  reason STRING,
  confidence_score DOUBLE,
  escalated_at TIMESTAMP,
  resolved_at TIMESTAMP,
  resolved_by STRING,
  resolution_notes STRING,
  status STRING,
  iteration INT,
  environment STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/escalations/'
TBLPROPERTIES (
  'has_encrypted_data'='false',
  'classification'='json'
);
