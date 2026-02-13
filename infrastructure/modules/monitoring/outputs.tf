# Outputs for monitoring module

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "agent_log_group_names" {
  description = "Names of CloudWatch log groups for agents"
  value       = { for k, v in aws_cloudwatch_log_group.agent_logs : k => v.name }
}

output "lambda_log_group_names" {
  description = "Names of CloudWatch log groups for Lambda functions"
  value       = { for k, v in aws_cloudwatch_log_group.lambda_logs : k => v.name }
}

output "step_functions_log_group_name" {
  description = "Name of CloudWatch log group for Step Functions"
  value       = aws_cloudwatch_log_group.step_functions_logs.name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alarms (if created)"
  value       = var.create_sns_topic ? aws_sns_topic.alarms[0].arn : null
}

output "alarm_names" {
  description = "Names of CloudWatch alarms"
  value = [
    aws_cloudwatch_metric_alarm.workflow_failures.alarm_name,
    aws_cloudwatch_metric_alarm.agent_errors.alarm_name,
    aws_cloudwatch_metric_alarm.human_review_required.alarm_name,
    aws_cloudwatch_metric_alarm.workflow_duration.alarm_name
  ]
}
