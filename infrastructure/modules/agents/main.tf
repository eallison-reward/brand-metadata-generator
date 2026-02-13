# Agent IAM roles and policies module

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Agent execution role
resource "aws_iam_role" "agent_execution_role" {
  name               = "brand_metagen_agent_execution_${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.agent_assume_role.json

  tags = merge(
    var.common_tags,
    {
      Name = "brand_metagen_agent_execution_${var.environment}"
    }
  )
}

# Assume role policy for Bedrock AgentCore
data "aws_iam_policy_document" "agent_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

# Agent execution policy
resource "aws_iam_role_policy" "agent_execution_policy" {
  name   = "brand_metagen_agent_policy_${var.environment}"
  role   = aws_iam_role.agent_execution_role.id
  policy = data.aws_iam_policy_document.agent_permissions.json
}

# Agent permissions
data "aws_iam_policy_document" "agent_permissions" {
  # Bedrock permissions
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeAgent"
    ]
    resources = ["*"]
  }

  # DynamoDB permissions for agent memory
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Scan"
    ]
    resources = [
      "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/brand_metagen_agent_memory_*"
    ]
  }

  # S3 permissions
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.s3_bucket_name}",
      "arn:aws:s3:::${var.s3_bucket_name}/*"
    ]
  }

  # Athena permissions
  statement {
    effect = "Allow"
    actions = [
      "athena:StartQueryExecution",
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:StopQueryExecution",
      "athena:GetWorkGroup"
    ]
    resources = [
      "arn:aws:athena:${var.aws_region}:${data.aws_caller_identity.current.account_id}:workgroup/*"
    ]
  }

  # Glue permissions for Athena
  statement {
    effect = "Allow"
    actions = [
      "glue:GetDatabase",
      "glue:GetTable",
      "glue:GetPartitions",
      "glue:GetPartition"
    ]
    resources = [
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:database/${var.athena_database}",
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.athena_database}/*"
    ]
  }

  # CloudWatch Logs permissions
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock/agentcore/brand_metagen_*"
    ]
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}
