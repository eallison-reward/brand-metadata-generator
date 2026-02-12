# Outputs for monitoring module

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "log_group_names" {
  description = "Names of CloudWatch log groups"
  value       = { for k, v in aws_cloudwatch_log_group.agent_logs : k => v.name }
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alarms (if created)"
  value       = var.create_sns_topic ? aws_sns_topic.alarms[0].arn : null
}
