# Lambda module for Step Functions integration

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Lambda execution role
resource "aws_iam_role" "lambda_execution_role" {
  name               = "brand_metagen_lambda_execution_${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = merge(
    var.common_tags,
    {
      Name = "brand_metagen_lambda_execution_${var.environment}"
    }
  )
}

# Assume role policy for Lambda
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

# Lambda execution policy
resource "aws_iam_role_policy" "lambda_execution_policy" {
  name   = "brand_metagen_lambda_policy_${var.environment}"
  role   = aws_iam_role.lambda_execution_role.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

# Lambda permissions
data "aws_iam_policy_document" "lambda_permissions" {
  # CloudWatch Logs
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/brand_metagen_*"
    ]
  }

  # Bedrock Agent invocation
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeAgent"
    ]
    resources = ["*"]
  }

  # S3 permissions
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.s3_bucket_name}",
      "arn:aws:s3:::${var.s3_bucket_name}/*"
    ]
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Workflow initialization Lambda
resource "aws_lambda_function" "workflow_init" {
  function_name = "brand_metagen_workflow_init_${var.environment}"
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 256

  filename         = "${path.module}/../../../lambda_functions/workflow_init.zip"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda_functions/workflow_init.zip")

  environment {
    variables = {
      AWS_REGION      = var.aws_region
      S3_BUCKET       = var.s3_bucket_name
      ATHENA_DATABASE = var.athena_database
      ENVIRONMENT     = var.environment
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name = "brand_metagen_workflow_init_${var.environment}"
    }
  )
}

# Orchestrator invocation Lambda
resource "aws_lambda_function" "orchestrator_invoke" {
  function_name = "brand_metagen_orchestrator_invoke_${var.environment}"
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 900
  memory_size   = 512

  filename         = "${path.module}/../../../lambda_functions/orchestrator_invoke.zip"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda_functions/orchestrator_invoke.zip")

  environment {
    variables = {
      AWS_REGION                  = var.aws_region
      ORCHESTRATOR_AGENT_ID       = var.orchestrator_agent_id
      ORCHESTRATOR_AGENT_ALIAS_ID = var.orchestrator_agent_alias_id
      ENVIRONMENT                 = var.environment
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name = "brand_metagen_orchestrator_invoke_${var.environment}"
    }
  )
}

# Result aggregation Lambda
resource "aws_lambda_function" "result_aggregation" {
  function_name = "brand_metagen_result_aggregation_${var.environment}"
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300
  memory_size   = 512

  filename         = "${path.module}/../../../lambda_functions/result_aggregation.zip"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda_functions/result_aggregation.zip")

  environment {
    variables = {
      AWS_REGION  = var.aws_region
      S3_BUCKET   = var.s3_bucket_name
      ENVIRONMENT = var.environment
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name = "brand_metagen_result_aggregation_${var.environment}"
    }
  )
}

# CloudWatch log groups for Lambda functions
resource "aws_cloudwatch_log_group" "workflow_init_logs" {
  name              = "/aws/lambda/brand_metagen_workflow_init_${var.environment}"
  retention_in_days = 30

  tags = var.common_tags
}

resource "aws_cloudwatch_log_group" "orchestrator_invoke_logs" {
  name              = "/aws/lambda/brand_metagen_orchestrator_invoke_${var.environment}"
  retention_in_days = 30

  tags = var.common_tags
}

resource "aws_cloudwatch_log_group" "result_aggregation_logs" {
  name              = "/aws/lambda/brand_metagen_result_aggregation_${var.environment}"
  retention_in_days = 30

  tags = var.common_tags
}
