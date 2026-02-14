# Variables for prod environment

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "brand-metadata-generator"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region - MUST be eu-west-1"
  type        = string
  default     = "eu-west-1"

  validation {
    condition     = var.aws_region == "eu-west-1"
    error_message = "AWS region must be eu-west-1 as per project requirements."
  }
}

variable "s3_bucket_name" {
  description = "S3 bucket name - MUST be brand-generator-rwrd-023-eu-west-1"
  type        = string
  default     = "brand-generator-rwrd-023-eu-west-1"

  validation {
    condition     = var.s3_bucket_name == "brand-generator-rwrd-023-eu-west-1"
    error_message = "S3 bucket must be brand-generator-rwrd-023-eu-west-1 as per project requirements."
  }
}

variable "athena_database" {
  description = "Athena database name - MUST be brand_metadata_generator_db"
  type        = string
  default     = "brand_metadata_generator_db"

  validation {
    condition     = var.athena_database == "brand_metadata_generator_db"
    error_message = "Athena database must be brand_metadata_generator_db as per project requirements."
  }
}

variable "agent_names" {
  description = "List of agent names"
  type        = list(string)
  default = [
    "orchestrator-agent",
    "data-transformation-agent",
    "evaluator-agent",
    "metadata-production-agent",
    "commercial-assessment-agent",
    "confirmation-agent",
    "tiebreaker-agent",
    "feedback-processing-agent",
    "learning-analytics-agent"
  ]
}
