# Variables for DynamoDB module

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "brand-metadata-generator"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "agent_names" {
  description = "List of agent names for memory tables"
  type        = list(string)
  default = [
    "orchestrator-agent",
    "data-transformation-agent",
    "evaluator-agent",
    "metadata-production-agent"
  ]
}

variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery for DynamoDB tables"
  type        = bool
  default     = false
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
