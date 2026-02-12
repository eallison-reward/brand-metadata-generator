# Outputs for step_functions module

output "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = aws_sfn_state_machine.brand_metadata_workflow.arn
}

output "state_machine_name" {
  description = "Name of the Step Functions state machine"
  value       = aws_sfn_state_machine.brand_metadata_workflow.name
}

output "step_functions_role_arn" {
  description = "ARN of the Step Functions execution role"
  value       = aws_iam_role.step_functions_role.arn
}
