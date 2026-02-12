# Outputs for storage module

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.data_bucket.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.data_bucket.arn
}

output "athena_database_name" {
  description = "Name of the Athena database"
  value       = aws_glue_catalog_database.athena_database.name
}

output "athena_workgroup_name" {
  description = "Name of the Athena workgroup"
  value       = aws_athena_workgroup.main.name
}
