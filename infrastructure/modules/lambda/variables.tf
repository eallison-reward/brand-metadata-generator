# Variables for Lambda module

variable "project_name" {
  description = "Name of the project"
  type        = string
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

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for metadata storage"
  type        = string
}

variable "athena_database" {
  description = "Name of the Athena database"
  type        = string
}

variable "orchestrator_agent_id" {
  description = "ID of the Orchestrator Bedrock Agent"
  type        = string
  default     = ""
}

variable "orchestrator_agent_alias_id" {
  description = "Alias ID of the Orchestrator Bedrock Agent"
  type        = string
  default     = "TSTALIASID"
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
