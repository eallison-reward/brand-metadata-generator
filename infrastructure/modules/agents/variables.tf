# Variables for agents module

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

variable "s3_bucket_name" {
  description = "S3 bucket name for data storage"
  type        = string
}

variable "athena_database" {
  description = "Athena database name"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
