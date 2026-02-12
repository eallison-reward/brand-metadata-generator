# Outputs for agents module

output "agent_execution_role_arn" {
  description = "ARN of the agent execution role"
  value       = aws_iam_role.agent_execution_role.arn
}

output "agent_execution_role_name" {
  description = "Name of the agent execution role"
  value       = aws_iam_role.agent_execution_role.name
}
