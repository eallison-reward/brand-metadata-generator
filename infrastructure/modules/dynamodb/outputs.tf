# Outputs for DynamoDB module

output "table_names" {
  description = "Names of DynamoDB tables"
  value       = { for k, v in aws_dynamodb_table.agent_memory : k => v.name }
}

output "table_arns" {
  description = "ARNs of DynamoDB tables"
  value       = { for k, v in aws_dynamodb_table.agent_memory : k => v.arn }
}
