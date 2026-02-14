# Quick Suite configuration for Brand Metadata Generator
# NOTE: Quick Suite is an AWS Bedrock AgentCore technology for agent-specific interfaces
# This is NOT Amazon QuickSight (a separate BI tool)

# Quick Suite is automatically available for AWS Bedrock AgentCore agents
# This configuration provides the integration points and Lambda functions

# Lambda function for feedback submission
resource "aws_lambda_function" "feedback_submission" {
  filename         = "${path.module}/../../../lambda_functions/feedback_submission.zip"
  function_name    = "brand-metagen-feedback-submission-${var.environment}"
  role            = aws_iam_role.quick_suite_lambda_role.arn
  handler         = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda_functions/feedback_submission.zip")
  runtime         = "python3.12"
  timeout         = 60

  environment {
    variables = {
      ENVIRONMENT           = var.environment
      S3_BUCKET            = var.s3_bucket_name
      DYNAMODB_TABLE       = var.dynamodb_table_name
      FEEDBACK_AGENT_ID    = var.feedback_processing_agent_id
    }
  }

  tags = var.common_tags
}

# Lambda function for feedback retrieval
resource "aws_lambda_function" "feedback_retrieval" {
  filename         = "${path.module}/../../../lambda_functions/feedback_retrieval.zip"
  function_name    = "brand-metagen-feedback-retrieval-${var.environment}"
  role            = aws_iam_role.quick_suite_lambda_role.arn
  handler         = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda_functions/feedback_retrieval.zip")
  runtime         = "python3.12"
  timeout         = 30

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      S3_BUCKET       = var.s3_bucket_name
      DYNAMODB_TABLE  = var.dynamodb_table_name
    }
  }

  tags = var.common_tags
}

# Lambda function for status updates
resource "aws_lambda_function" "status_updates" {
  filename         = "${path.module}/../../../lambda_functions/status_updates.zip"
  function_name    = "brand-metagen-status-updates-${var.environment}"
  role            = aws_iam_role.quick_suite_lambda_role.arn
  handler         = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda_functions/status_updates.zip")
  runtime         = "python3.12"
  timeout         = 30

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      S3_BUCKET       = var.s3_bucket_name
      DYNAMODB_TABLE  = var.dynamodb_table_name
      ATHENA_DATABASE = var.athena_database
    }
  }

  tags = var.common_tags
}

# Lambda function for brand data retrieval (for Quick Suite display)
resource "aws_lambda_function" "brand_data_retrieval" {
  filename         = "${path.module}/../../../lambda_functions/brand_data_retrieval.zip"
  function_name    = "brand-metagen-brand-data-${var.environment}"
  role            = aws_iam_role.quick_suite_lambda_role.arn
  handler         = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda_functions/brand_data_retrieval.zip")
  runtime         = "python3.12"
  timeout         = 30

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      S3_BUCKET       = var.s3_bucket_name
      ATHENA_DATABASE = var.athena_database
    }
  }

  tags = var.common_tags
}

# IAM role for Quick Suite Lambda functions
resource "aws_iam_role" "quick_suite_lambda_role" {
  name = "brand-metagen-quick-suite-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

# IAM policy for Quick Suite Lambda functions
resource "aws_iam_role_policy" "quick_suite_lambda_policy" {
  name = "brand-metagen-quick-suite-lambda-policy"
  role = aws_iam_role.quick_suite_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:UpdateItem"
        ]
        Resource = "arn:aws:dynamodb:${var.aws_region}:*:table/${var.dynamodb_table_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}:*:agent/*"
      }
    ]
  })
}

# API Gateway for Quick Suite integration
resource "aws_apigatewayv2_api" "quick_suite_api" {
  name          = "brand-metagen-quick-suite-${var.environment}"
  protocol_type = "HTTP"
  description   = "API for Quick Suite integration with Brand Metadata Generator"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["*"]
    max_age       = 300
  }

  tags = var.common_tags
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "quick_suite_api_stage" {
  api_id      = aws_apigatewayv2_api.quick_suite_api.id
  name        = var.environment
  auto_deploy = true

  tags = var.common_tags
}

# API Gateway integration for feedback submission
resource "aws_apigatewayv2_integration" "feedback_submission" {
  api_id           = aws_apigatewayv2_api.quick_suite_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.feedback_submission.invoke_arn
}

# API Gateway route for feedback submission
resource "aws_apigatewayv2_route" "feedback_submission" {
  api_id    = aws_apigatewayv2_api.quick_suite_api.id
  route_key = "POST /feedback"
  target    = "integrations/${aws_apigatewayv2_integration.feedback_submission.id}"
}

# Lambda permission for API Gateway (feedback submission)
resource "aws_lambda_permission" "feedback_submission_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.feedback_submission.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.quick_suite_api.execution_arn}/*/*"
}

# API Gateway integration for feedback retrieval
resource "aws_apigatewayv2_integration" "feedback_retrieval" {
  api_id           = aws_apigatewayv2_api.quick_suite_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.feedback_retrieval.invoke_arn
}

# API Gateway route for feedback retrieval
resource "aws_apigatewayv2_route" "feedback_retrieval" {
  api_id    = aws_apigatewayv2_api.quick_suite_api.id
  route_key = "GET /feedback/{brandid}"
  target    = "integrations/${aws_apigatewayv2_integration.feedback_retrieval.id}"
}

# Lambda permission for API Gateway (feedback retrieval)
resource "aws_lambda_permission" "feedback_retrieval_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.feedback_retrieval.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.quick_suite_api.execution_arn}/*/*"
}

# API Gateway integration for status updates
resource "aws_apigatewayv2_integration" "status_updates" {
  api_id           = aws_apigatewayv2_api.quick_suite_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.status_updates.invoke_arn
}

# API Gateway route for status updates
resource "aws_apigatewayv2_route" "status_updates" {
  api_id    = aws_apigatewayv2_api.quick_suite_api.id
  route_key = "GET /status"
  target    = "integrations/${aws_apigatewayv2_integration.status_updates.id}"
}

# Lambda permission for API Gateway (status updates)
resource "aws_lambda_permission" "status_updates_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status_updates.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.quick_suite_api.execution_arn}/*/*"
}

# API Gateway integration for brand data retrieval
resource "aws_apigatewayv2_integration" "brand_data_retrieval" {
  api_id           = aws_apigatewayv2_api.quick_suite_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.brand_data_retrieval.invoke_arn
}

# API Gateway route for brand data retrieval
resource "aws_apigatewayv2_route" "brand_data_retrieval" {
  api_id    = aws_apigatewayv2_api.quick_suite_api.id
  route_key = "GET /brands/{brandid}"
  target    = "integrations/${aws_apigatewayv2_integration.brand_data_retrieval.id}"
}

# Lambda permission for API Gateway (brand data retrieval)
resource "aws_lambda_permission" "brand_data_retrieval_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.brand_data_retrieval.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.quick_suite_api.execution_arn}/*/*"
}

# Outputs
output "quick_suite_api_endpoint" {
  description = "API Gateway endpoint for Quick Suite integration"
  value       = aws_apigatewayv2_api.quick_suite_api.api_endpoint
}

output "feedback_submission_lambda_arn" {
  description = "ARN of feedback submission Lambda function"
  value       = aws_lambda_function.feedback_submission.arn
}

output "feedback_retrieval_lambda_arn" {
  description = "ARN of feedback retrieval Lambda function"
  value       = aws_lambda_function.feedback_retrieval.arn
}

output "status_updates_lambda_arn" {
  description = "ARN of status updates Lambda function"
  value       = aws_lambda_function.status_updates.arn
}

output "brand_data_retrieval_lambda_arn" {
  description = "ARN of brand data retrieval Lambda function"
  value       = aws_lambda_function.brand_data_retrieval.arn
}

