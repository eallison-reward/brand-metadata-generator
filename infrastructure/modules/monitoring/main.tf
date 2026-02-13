# Monitoring module - CloudWatch dashboards and alarms

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# CloudWatch log groups for agents
resource "aws_cloudwatch_log_group" "agent_logs" {
  for_each = toset(var.agent_names)

  name              = "/aws/bedrock/agentcore/brand-metagen-${each.value}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.common_tags,
    {
      Name  = "brand-metagen-${each.value}-logs"
      Agent = each.value
    }
  )
}

# CloudWatch log group for Lambda functions
resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = toset(var.lambda_function_names)

  name              = "/aws/lambda/brand-metagen-${each.value}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.common_tags,
    {
      Name     = "brand-metagen-${each.value}-logs"
      Function = each.value
    }
  )
}

# CloudWatch log group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions_logs" {
  name              = "/aws/states/brand-metagen-workflow-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.common_tags,
    {
      Name = "brand-metagen-workflow-logs"
    }
  )
}

# CloudWatch dashboard for brand metadata generator
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "brand-metagen-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Workflow execution metrics
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/States", "ExecutionsStarted", { stat = "Sum", label = "Workflow Executions Started" }],
            [".", "ExecutionsSucceeded", { stat = "Sum", label = "Workflow Executions Succeeded" }],
            [".", "ExecutionsFailed", { stat = "Sum", label = "Workflow Executions Failed" }],
            [".", "ExecutionTime", { stat = "Average", label = "Average Execution Time (ms)" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Step Functions Workflow Metrics"
          yAxis = {
            left = {
              label = "Count"
            }
          }
        }
      },
      # Brand processing status
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["BrandMetadataGenerator", "BrandsProcessed", { stat = "Sum", label = "Brands Processed" }],
            [".", "BrandsInProgress", { stat = "Average", label = "Brands In Progress" }],
            [".", "BrandsPending", { stat = "Average", label = "Brands Pending" }],
            [".", "BrandsFailed", { stat = "Sum", label = "Brands Failed" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Brand Processing Status"
          yAxis = {
            left = {
              label = "Count"
            }
          }
        }
      },
      # Combo matching statistics
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["BrandMetadataGenerator", "CombosMatched", { stat = "Sum", label = "Combos Matched" }],
            [".", "CombosConfirmed", { stat = "Sum", label = "Combos Confirmed" }],
            [".", "CombosExcluded", { stat = "Sum", label = "Combos Excluded (False Positives)" }],
            [".", "CombosFlaggedForReview", { stat = "Sum", label = "Combos Flagged for Human Review" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Combo Matching Statistics"
          yAxis = {
            left = {
              label = "Count"
            }
          }
        }
      },
      # Tie resolution metrics
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["BrandMetadataGenerator", "TiesDetected", { stat = "Sum", label = "Ties Detected" }],
            [".", "TiesResolved", { stat = "Sum", label = "Ties Resolved" }],
            [".", "TiesFlaggedForReview", { stat = "Sum", label = "Ties Flagged for Human Review" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Tie Resolution Metrics"
          yAxis = {
            left = {
              label = "Count"
            }
          }
        }
      },
      # Agent invocation metrics
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["BrandMetadataGenerator", "DataTransformationInvocations", { stat = "Sum", label = "Data Transformation" }],
            [".", "EvaluatorInvocations", { stat = "Sum", label = "Evaluator" }],
            [".", "MetadataProductionInvocations", { stat = "Sum", label = "Metadata Production" }],
            [".", "ConfirmationInvocations", { stat = "Sum", label = "Confirmation" }],
            [".", "TiebreakerInvocations", { stat = "Sum", label = "Tiebreaker" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Agent Invocation Counts"
          yAxis = {
            left = {
              label = "Count"
            }
          }
        }
      },
      # Agent errors
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["BrandMetadataGenerator", "AgentErrors", { stat = "Sum", label = "Total Agent Errors" }],
            [".", "ValidationErrors", { stat = "Sum", label = "Validation Errors" }],
            [".", "RetryAttempts", { stat = "Sum", label = "Retry Attempts" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Error Metrics"
          yAxis = {
            left = {
              label = "Count"
            }
          }
        }
      },
      # Recent orchestrator logs
      {
        type   = "log"
        x      = 0
        y      = 18
        width  = 12
        height = 6
        properties = {
          query  = "SOURCE '/aws/bedrock/agentcore/brand-metagen-orchestrator-${var.environment}' | fields @timestamp, @message | filter @message like /ERROR/ or @message like /WARN/ | sort @timestamp desc | limit 20"
          region = var.aws_region
          title  = "Recent Orchestrator Errors and Warnings"
        }
      },
      # Recent agent errors
      {
        type   = "log"
        x      = 12
        y      = 18
        width  = 12
        height = 6
        properties = {
          query  = "SOURCE '/aws/bedrock/agentcore/brand-metagen-*' | fields @timestamp, @logStream, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
          region = var.aws_region
          title  = "Recent Agent Errors (All Agents)"
        }
      }
    ]
  })
}

# Alarm for workflow failures
resource "aws_cloudwatch_metric_alarm" "workflow_failures" {
  alarm_name          = "brand-metagen-workflow-failures-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alert when workflow executions fail"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.create_sns_topic ? [aws_sns_topic.alarms[0].arn] : []

  dimensions = {
    StateMachineArn = var.state_machine_arn
  }

  tags = var.common_tags
}

# Alarm for high agent error rate
resource "aws_cloudwatch_metric_alarm" "agent_errors" {
  alarm_name          = "brand-metagen-agent-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "AgentErrors"
  namespace           = "BrandMetadataGenerator"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert when agent error count exceeds threshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.create_sns_topic ? [aws_sns_topic.alarms[0].arn] : []

  tags = var.common_tags
}

# Alarm for brands requiring human review
resource "aws_cloudwatch_metric_alarm" "human_review_required" {
  alarm_name          = "brand-metagen-human-review-required-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CombosFlaggedForReview"
  namespace           = "BrandMetadataGenerator"
  period              = 3600
  statistic           = "Sum"
  threshold           = 50
  alarm_description   = "Alert when many combos are flagged for human review"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.create_sns_topic ? [aws_sns_topic.alarms[0].arn] : []

  tags = var.common_tags
}

# Alarm for workflow execution time
resource "aws_cloudwatch_metric_alarm" "workflow_duration" {
  alarm_name          = "brand-metagen-workflow-duration-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionTime"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Average"
  threshold           = 900000 # 15 minutes in milliseconds
  alarm_description   = "Alert when workflow execution time exceeds 15 minutes"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.create_sns_topic ? [aws_sns_topic.alarms[0].arn] : []

  dimensions = {
    StateMachineArn = var.state_machine_arn
  }

  tags = var.common_tags
}

# SNS topic for alarms (optional)
resource "aws_sns_topic" "alarms" {
  count = var.create_sns_topic ? 1 : 0

  name = "${var.project_name}-alarms-${var.environment}"

  tags = var.common_tags
}
