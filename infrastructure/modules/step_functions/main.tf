# Step Functions module for workflow orchestration

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Step Functions execution role
resource "aws_iam_role" "step_functions_role" {
  name               = "brand_metagen_step_functions_${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.step_functions_assume_role.json

  tags = merge(
    var.common_tags,
    {
      Name = "brand_metagen_step_functions_${var.environment}"
    }
  )
}

# Assume role policy for Step Functions
data "aws_iam_policy_document" "step_functions_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

# Step Functions execution policy
resource "aws_iam_role_policy" "step_functions_policy" {
  name   = "brand_metagen_step_functions_policy_${var.environment}"
  role   = aws_iam_role.step_functions_role.id
  policy = data.aws_iam_policy_document.step_functions_permissions.json
}

# Step Functions permissions
data "aws_iam_policy_document" "step_functions_permissions" {
  # Lambda invocation
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = [
      "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:brand_metagen_*"
    ]
  }

  # Bedrock agent invocation
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeAgent"
    ]
    resources = ["*"]
  }

  # CloudWatch Logs
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups"
    ]
    resources = ["*"]
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Step Functions state machine
resource "aws_sfn_state_machine" "brand_metadata_workflow" {
  name     = "brand_metagen_workflow_${var.environment}"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../workflows/brand_metadata_workflow.json", {
    aws_region  = var.aws_region
    account_id  = data.aws_caller_identity.current.account_id
    environment = var.environment
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = var.common_tags
}

# CloudWatch log group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions_logs" {
  name              = "/aws/vendedlogs/states/brand_metagen_workflow_${var.environment}"
  retention_in_days = 30

  tags = var.common_tags
}
