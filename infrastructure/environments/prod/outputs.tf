# Outputs for prod environment

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = module.storage.s3_bucket_name
}

output "athena_database_name" {
  description = "Name of the Athena database"
  value       = module.storage.athena_database_name
}

output "athena_workgroup_name" {
  description = "Name of the Athena workgroup"
  value       = module.storage.athena_workgroup_name
}

output "agent_execution_role_arn" {
  description = "ARN of the agent execution role"
  value       = module.agents.agent_execution_role_arn
}

output "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = module.step_functions.state_machine_arn
}

output "dynamodb_table_names" {
  description = "Names of DynamoDB tables for agent memory"
  value       = module.dynamodb.table_names
}

output "cloudwatch_dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = module.monitoring.dashboard_name
}
