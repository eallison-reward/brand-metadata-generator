# DynamoDB module for agent memory

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# DynamoDB table for agent memory
resource "aws_dynamodb_table" "agent_memory" {
  for_each = toset(var.agent_names)

  name           = "${var.project_name}-agent-memory-${each.value}-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"
  range_key      = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  tags = merge(
    var.common_tags,
    {
      Name  = "${var.project_name}-agent-memory-${each.value}-${var.environment}"
      Agent = each.value
    }
  )
}
