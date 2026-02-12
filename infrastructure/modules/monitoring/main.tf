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

  name              = "/aws/bedrock/agentcore/${each.value}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.common_tags,
    {
      Name  = "${each.value}-logs"
      Agent = each.value
    }
  )
}

# CloudWatch dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/States", "ExecutionsStarted", { stat = "Sum", label = "Workflow Executions Started" }],
            [".", "ExecutionsSucceeded", { stat = "Sum", label = "Workflow Executions Succeeded" }],
            [".", "ExecutionsFailed", { stat = "Sum", label = "Workflow Executions Failed" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Step Functions Executions"
        }
      },
      {
        type = "log"
        properties = {
          query  = "SOURCE '/aws/bedrock/agentcore/orchestrator-${var.environment}' | fields @timestamp, @message | sort @timestamp desc | limit 20"
          region = var.aws_region
          title  = "Recent Orchestrator Logs"
        }
      }
    ]
  })
}

# Alarm for workflow failures
resource "aws_cloudwatch_metric_alarm" "workflow_failures" {
  alarm_name          = "${var.project_name}-workflow-failures-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alert when workflow executions fail"
  treat_missing_data  = "notBreaching"

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
