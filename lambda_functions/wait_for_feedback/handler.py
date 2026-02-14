"""
Lambda function to wait for human feedback using Step Functions task token.

This function stores the task token and waits for feedback submission from Quick Suite.
The feedback submission Lambda will resume the workflow by sending the task token.
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'brand-metadata-state')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Store task token and wait for human feedback.
    
    Input:
    {
        "brands": [{"brandid": int, ...}],
        "task_token": str,
        "workflow_execution_arn": str
    }
    
    This function stores the task token in DynamoDB and returns immediately.
    The workflow will wait until the feedback submission Lambda sends the task token
    back to Step Functions using send_task_success or send_task_failure.
    """
    try:
        brands = event.get('brands', [])
        task_token = event.get('task_token')
        workflow_execution_arn = event.get('workflow_execution_arn')
        
        if not task_token:
            raise ValueError("task_token is required")
        
        # Store task token for each brand
        for brand in brands:
            brandid = brand.get('brandid')
            if brandid:
                store_task_token(brandid, task_token, workflow_execution_arn)
        
        # Store workflow-level task token
        store_workflow_task_token(workflow_execution_arn, task_token, brands)
        
        # This function returns immediately, but the Step Functions workflow
        # will wait until send_task_success is called with this task token
        return {
            'statusCode': 200,
            'message': 'Task token stored, waiting for feedback',
            'brands_count': len(brands)
        }
    
    except Exception as e:
        print(f"Error storing task token: {str(e)}")
        raise


def store_task_token(brandid: int, task_token: str, workflow_execution_arn: str) -> None:
    """Store task token for a brand in DynamoDB."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        table.put_item(
            Item={
                'pk': f"BRAND#{brandid}",
                'sk': 'TASK_TOKEN',
                'brandid': brandid,
                'task_token': task_token,
                'workflow_execution_arn': workflow_execution_arn,
                'status': 'waiting_for_feedback',
                'created_at': get_current_timestamp(),
                'ttl': int(datetime.utcnow().timestamp()) + (7 * 24 * 60 * 60)  # 7 days
            }
        )
    except Exception as e:
        print(f"Error storing task token for brand {brandid}: {str(e)}")
        raise


def store_workflow_task_token(workflow_execution_arn: str, task_token: str, brands: list) -> None:
    """Store workflow-level task token in DynamoDB."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        table.put_item(
            Item={
                'pk': 'WORKFLOW',
                'sk': f"TOKEN#{workflow_execution_arn}",
                'task_token': task_token,
                'workflow_execution_arn': workflow_execution_arn,
                'brands': [b.get('brandid') for b in brands],
                'status': 'waiting_for_feedback',
                'created_at': get_current_timestamp(),
                'ttl': int(datetime.utcnow().timestamp()) + (7 * 24 * 60 * 60)  # 7 days
            }
        )
    except Exception as e:
        print(f"Error storing workflow task token: {str(e)}")
        raise


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"

