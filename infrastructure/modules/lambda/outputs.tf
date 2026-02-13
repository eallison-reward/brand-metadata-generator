# Outputs for Lambda module

output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution_role.arn
}

output "workflow_init_function_arn" {
  description = "ARN of the workflow initialization Lambda function"
  value       = aws_lambda_function.workflow_init.arn
}

output "workflow_init_function_name" {
  description = "Name of the workflow initialization Lambda function"
  value       = aws_lambda_function.workflow_init.function_name
}

output "orchestrator_invoke_function_arn" {
  description = "ARN of the orchestrator invocation Lambda function"
  value       = aws_lambda_function.orchestrator_invoke.arn
}

output "orchestrator_invoke_function_name" {
  description = "Name of the orchestrator invocation Lambda function"
  value       = aws_lambda_function.orchestrator_invoke.function_name
}

output "result_aggregation_function_arn" {
  description = "ARN of the result aggregation Lambda function"
  value       = aws_lambda_function.result_aggregation.arn
}

output "result_aggregation_function_name" {
  description = "Name of the result aggregation Lambda function"
  value       = aws_lambda_function.result_aggregation.function_name
}
