# Quick Suite Setup Guide

This guide provides instructions for setting up Quick Suite for the Brand Metadata Generator human review interface.

## Important Note

**Quick Suite** is an AWS technology for agent-specific user interfaces in AWS Bedrock AgentCore environments. This is NOT Amazon QuickSight (a BI tool). See `QUICK_SUITE_VS_QUICKSIGHT.md` for clarification.

## Prerequisites

1. AWS Bedrock AgentCore agents deployed (see `AGENT_DEPLOYMENT_GUIDE.md`)
2. AWS account with Bedrock permissions
3. IAM permissions for Quick Suite access
4. Step Functions workflow deployed

## Overview

Quick Suite provides the human review interface for the Brand Metadata Generator system, enabling:
- Review of brand classification results
- Feedback submission on metadata quality
- Approval/rejection of brand metadata
- Real-time processing status monitoring
- Feedback history and iteration tracking

## Quick Suite Components

### 1. Brand Review Page

Displays classification results grouped by brand:
- Brand name and sector
- Generated regex pattern
- MCCID list
- Confidence score
- Sample matched narratives
- Sample excluded narratives
- Combo statistics

### 2. Feedback Input Forms

Allows humans to provide feedback:
- **General Feedback**: Free-text feedback on metadata quality
- **Specific Combo Flagging**: Flag individual combos as misclassified
- **Approve/Reject Buttons**: Quick approval or rejection actions

### 3. Feedback History View

Shows historical feedback for each brand:
- All previous feedback submissions
- Metadata version history
- Iteration count and trends
- Accuracy improvements over time

### 4. Real-time Status Updates

Displays current processing status:
- Brands in progress
- Brands awaiting review
- Feedback being processed
- Regeneration progress

## Setup Instructions

### Step 1: Enable Quick Suite for AgentCore

Quick Suite is automatically available for AWS Bedrock AgentCore agents. No separate enablement is required.

### Step 2: Configure Agent Access

Ensure your agents are configured to support Quick Suite interaction:

```python
# In agent deployment configuration
agent_config = {
    "agent_name": "metadata_production_agent",
    "enable_quick_suite": True,  # Enable Quick Suite interface
    "quick_suite_config": {
        "enable_human_review": True,
        "enable_feedback": True,
        "enable_status_updates": True
    }
}
```

### Step 3: Deploy Lambda Functions for Quick Suite Integration

Deploy the Lambda functions that support Quick Suite operations:

```bash
# Deploy feedback submission Lambda
cd lambda_functions/feedback_submission
terraform apply

# Deploy feedback retrieval Lambda
cd lambda_functions/feedback_retrieval
terraform apply

# Deploy status update Lambda
cd lambda_functions/status_updates
terraform apply
```

### Step 4: Configure Step Functions Integration

Update the Step Functions workflow to include human review phases:

```json
{
  "Comment": "Brand Metadata Generator with Human Review",
  "StartAt": "ProcessBrands",
  "States": {
    "ProcessBrands": {
      "Type": "Task",
      "Resource": "arn:aws:states:::bedrock:invokeAgent",
      "Next": "HumanReview"
    },
    "HumanReview": {
      "Type": "Task",
      "Resource": "arn:aws:states:::quick-suite:waitForHumanReview",
      "Parameters": {
        "AgentId.$": "$.agentId",
        "ReviewData.$": "$.classificationResults"
      },
      "Next": "ProcessFeedback"
    },
    "ProcessFeedback": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.feedback.action",
          "StringEquals": "approve",
          "Next": "StoreResults"
        },
        {
          "Variable": "$.feedback.action",
          "StringEquals": "reject",
          "Next": "RegenerateMetadata"
        }
      ]
    }
  }
}
```

### Step 5: Access Quick Suite Interface

1. Navigate to AWS Bedrock Console
2. Select "AgentCore" from the left menu
3. Click on "Quick Suite" tab
4. Select your agent (e.g., "metadata_production_agent")
5. The Quick Suite interface will load with your agent's data

## Using Quick Suite for Human Review

### Reviewing Brand Classifications

1. **Access Review Queue**:
   - Open Quick Suite interface
   - Navigate to "Brands Awaiting Review"
   - Select a brand to review

2. **Review Brand Details**:
   - Examine the generated regex pattern
   - Review the MCCID list
   - Check sample matched narratives
   - Verify excluded narratives
   - Review confidence score

3. **Make Decision**:
   - Click "Approve" if metadata is correct
   - Click "Reject" and provide feedback if incorrect
   - Click "Flag for Manual Review" if uncertain

### Providing Feedback

#### General Feedback

1. Click "Provide Feedback" button
2. Enter free-text feedback describing issues:
   ```
   Example: "Regex is too broad - matches Starbucks and Starburst candy. 
   Need to add word boundary or negative lookahead."
   ```
3. Click "Submit Feedback"

#### Specific Combo Flagging

1. Click "Flag Specific Combos" button
2. Enter combo IDs that are misclassified:
   ```
   Example: "Combo 12345 should not be Starbucks - it's Starburst candy"
   ```
3. Click "Submit"

### Viewing Feedback History

1. Select a brand from the review queue
2. Click "Feedback History" tab
3. View all previous feedback:
   - Feedback text
   - Metadata version at time of feedback
   - Iteration number
   - Timestamp
   - Actions taken

### Monitoring Processing Status

The Quick Suite interface shows real-time status:
- **In Progress**: Brands currently being processed
- **Awaiting Review**: Brands ready for human review
- **Processing Feedback**: Feedback being processed by agents
- **Regenerating**: Metadata being regenerated based on feedback
- **Completed**: Brands approved and finalized

## Quick Suite API Integration

### Feedback Submission API

Lambda function: `feedback_submission_handler`

```python
# Invoked by Quick Suite when user submits feedback
def lambda_handler(event, context):
    brandid = event['brandid']
    feedback_text = event['feedback']
    metadata_version = event['metadata_version']
    
    # Process feedback through Feedback Processing Agent
    result = invoke_feedback_processing_agent(
        brandid=brandid,
        feedback=feedback_text,
        metadata_version=metadata_version
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
```

### Feedback Retrieval API

Lambda function: `feedback_retrieval_handler`

```python
# Invoked by Quick Suite to display feedback history
def lambda_handler(event, context):
    brandid = event['brandid']
    
    # Retrieve feedback history from S3/DynamoDB
    history = retrieve_feedback_history(brandid)
    
    return {
        'statusCode': 200,
        'body': json.dumps(history)
    }
```

### Status Update API

Lambda function: `status_update_handler`

```python
# Invoked by Quick Suite to get real-time status
def lambda_handler(event, context):
    # Query current processing status
    status = get_processing_status()
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'in_progress': status['in_progress'],
            'awaiting_review': status['awaiting_review'],
            'processing_feedback': status['processing_feedback'],
            'completed': status['completed']
        })
    }
```

## Troubleshooting

### Quick Suite Interface Not Loading

- Verify agents are deployed to AWS Bedrock AgentCore
- Check IAM permissions for Quick Suite access
- Ensure `enable_quick_suite` is set to `True` in agent configuration

### Feedback Not Being Processed

- Check Lambda function logs for errors
- Verify Feedback Processing Agent is deployed
- Ensure Step Functions workflow includes feedback processing loop

### Status Updates Not Appearing

- Verify status update Lambda is deployed
- Check CloudWatch Logs for Lambda errors
- Ensure DynamoDB tables have correct permissions

## Best Practices

1. **Regular Monitoring**: Check Quick Suite interface regularly for brands awaiting review
2. **Detailed Feedback**: Provide specific, actionable feedback for better metadata regeneration
3. **Combo Flagging**: Flag specific misclassified combos to help agents learn patterns
4. **Iteration Tracking**: Monitor iteration counts to identify problematic brands
5. **Approval Workflow**: Establish clear criteria for approving/rejecting metadata

## Additional Resources

- AWS Bedrock AgentCore Documentation
- Quick Suite User Guide (AWS Bedrock)
- `AGENT_DEPLOYMENT_GUIDE.md` - Agent deployment instructions
- `STEP_FUNCTIONS_WORKFLOW.md` - Workflow configuration
- `QUICK_SUITE_VS_QUICKSIGHT.md` - Technology clarification

