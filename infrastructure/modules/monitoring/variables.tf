# Variables for monitoring module

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "brand-metadata-generator"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "agent_names" {
  description = "List of agent names for log groups"
  type        = list(string)
  default = [
    "orchestrator",
    "data-transformation",
    "evaluator",
    "metadata-production",
    "commercial-assessment",
    "confirmation",
    "tiebreaker"
  ]
}

variable "lambda_function_names" {
  description = "List of Lambda function names for log groups"
  type        = list(string)
  default = [
    "workflow-init",
    "orchestrator-invoke",
    "result-aggregation"
  ]
}

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

variable "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  type        = string
}

variable "create_sns_topic" {
  description = "Whether to create SNS topic for alarms"
  type        = bool
  default     = false
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "enable_quicksight" {
  description = "Whether to enable QuickSight dashboard resources"
  type        = bool
  default     = false
}

variable "quicksight_principal_arn" {
  description = "ARN of the QuickSight principal (user or group) for permissions"
  type        = string
  default     = ""
}

variable "s3_bucket_name" {
  description = "S3 bucket name for data storage"
  type        = string
}

variable "athena_database" {
  description = "Athena database name"
  type        = string
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for workflow state"
  type        = string
  default     = ""
}

variable "feedback_processing_agent_id" {
  description = "Feedback Processing Agent ID"
  type        = string
  default     = ""
}
