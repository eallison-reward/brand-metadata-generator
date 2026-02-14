# Main Terraform configuration for prod environment

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration for state storage
  # Uncomment and configure after creating S3 bucket for state
  # backend "s3" {
  #   bucket         = "brand-metadata-generator-terraform-state"
  #   key            = "prod/terraform.tfstate"
  #   region         = "eu-west-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

# AWS Provider
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Local variables
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Storage module (S3, Athena, Glue)
module "storage" {
  source = "../../modules/storage"

  project_name    = var.project_name
  environment     = var.environment
  s3_bucket_name  = var.s3_bucket_name
  athena_database = var.athena_database
  common_tags     = local.common_tags
}

# DynamoDB module (Agent memory)
module "dynamodb" {
  source = "../../modules/dynamodb"

  project_name                  = var.project_name
  environment                   = var.environment
  agent_names                   = var.agent_names
  enable_point_in_time_recovery = true # Enabled for prod
  common_tags                   = local.common_tags
}

# Agents module (IAM roles and policies)
module "agents" {
  source = "../../modules/agents"

  project_name    = var.project_name
  environment     = var.environment
  aws_region      = var.aws_region
  s3_bucket_name  = module.storage.s3_bucket_name
  athena_database = module.storage.athena_database_name
  common_tags     = local.common_tags
}

# Step Functions module
module "step_functions" {
  source = "../../modules/step_functions"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  common_tags  = local.common_tags
}

# Monitoring module
module "monitoring" {
  source = "../../modules/monitoring"

  project_name                 = var.project_name
  environment                  = var.environment
  aws_region                   = var.aws_region
  agent_names                  = var.agent_names
  state_machine_arn            = module.step_functions.state_machine_arn
  create_sns_topic             = true # Enabled for prod
  s3_bucket_name               = module.storage.s3_bucket_name
  athena_database              = module.storage.athena_database_name
  dynamodb_table_name          = "brand-metagen-workflow-state-${var.environment}"
  feedback_processing_agent_id = "" # Will be populated after agent deployment
  common_tags                  = local.common_tags
}
