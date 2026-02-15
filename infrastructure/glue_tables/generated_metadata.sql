-- Glue table definition for generated_metadata
-- This table makes brand metadata queryable via Athena
-- Schema matches the JSON structure stored in S3

CREATE EXTERNAL TABLE IF NOT EXISTS brand_metadata_generator_db.generated_metadata (
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
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://brand-generator-rwrd-023-eu-west-1/metadata/'
TBLPROPERTIES (
  'has_encrypted_data'='false',
  'classification'='json'
);
