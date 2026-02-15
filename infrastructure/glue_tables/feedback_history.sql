-- Glue table definition for feedback_history
-- This table makes feedback submissions queryable via Athena
-- Schema matches the JSON structure stored in S3

CREATE EXTERNAL TABLE IF NOT EXISTS brand_metadata_generator_db.feedback_history (
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
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/feedback/'
TBLPROPERTIES (
  'has_encrypted_data'='false',
  'classification'='json'
);
