"""
Lambda function for feedback submission from Quick Suite interface.

This function receives feedback from humans through Quick Suite and processes it
using the Feedback Processing Agent.
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any

# Initialize AWS clients
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
S3_BUCKET = os.environ.get('S3_BUCKET', 'brand-generator-rwrd-023-eu-west-1')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'brand-metadata-state')
FEEDBACK_AGENT_ID = os.environ.get('FEEDBACK_AGENT_ID')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle feedback submission from Quick Suite.
    
    Expected event structure:
    {
        "body": {
            "brandid": int,
            "feedback_type": "general" | "specific_examples" | "approve" | "reject",
            "feedback_text": str,
            "misclassified_combos": [int],  # Optional
            "metadata_version": int
        }
    }
    """
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        brandid = body.get('brandid')
        feedback_type = body.get('feedback_type', 'general')
        feedback_text = body.get('feedback_text', '')
        misclassified_combos = body.get('misclassified_combos', [])
        metadata_version = body.get('metadata_version', 1)
        
        # Validate required fields
        if not brandid:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'brandid is required'})
            }
        
        if feedback_type not in ['general', 'specific_examples', 'approve', 'reject']:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid feedback_type'})
            }
        
        # Handle approve/reject actions
        if feedback_type == 'approve':
            result = handle_approval(brandid, metadata_version)
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(result)
            }
        
        if feedback_type == 'reject' and not feedback_text:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'feedback_text is required for rejection'})
            }
        
        # Retrieve current metadata from S3
        current_metadata = get_current_metadata(brandid)
        
        # Invoke Feedback Processing Agent
        feedback_result = invoke_feedback_processing_agent(
            brandid=brandid,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            misclassified_combos=misclassified_combos,
            metadata_version=metadata_version,
            current_metadata=current_metadata
        )
        
        # Store feedback submission record
        store_feedback_submission(
            brandid=brandid,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            misclassified_combos=misclassified_combos,
            metadata_version=metadata_version,
            processing_result=feedback_result
        )
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Feedback submitted successfully',
                'brandid': brandid,
                'feedback_processed': feedback_result.get('feedback_processed', False),
                'refinement_prompt': feedback_result.get('refinement_prompt', ''),
                'recommended_action': feedback_result.get('recommended_action', ''),
                'feedback_stored': True
            })
        }
    
    except Exception as e:
        print(f"Error processing feedback submission: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }


def get_current_metadata(brandid: int) -> Dict[str, Any]:
    """Retrieve current metadata for the brand from S3."""
    try:
        s3_key = f"metadata/brand_{brandid}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        metadata = json.loads(response['Body'].read().decode('utf-8'))
        return metadata
    except s3_client.exceptions.NoSuchKey:
        return {}
    except Exception as e:
        print(f"Error retrieving metadata for brand {brandid}: {str(e)}")
        return {}


def invoke_feedback_processing_agent(
    brandid: int,
    feedback_type: str,
    feedback_text: str,
    misclassified_combos: list,
    metadata_version: int,
    current_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke the Feedback Processing Agent to process the feedback."""
    try:
        # Prepare input for Feedback Processing Agent
        agent_input = {
            "action": "process_feedback",
            "brandid": brandid,
            "metadata_version": metadata_version,
            "feedback_type": feedback_type,
            "feedback_text": feedback_text,
            "misclassified_combos": misclassified_combos,
            "current_metadata": current_metadata
        }
        
        # Invoke agent (if FEEDBACK_AGENT_ID is configured)
        if FEEDBACK_AGENT_ID:
            response = bedrock_agent.invoke_agent(
                agentId=FEEDBACK_AGENT_ID,
                agentAliasId='TSTALIASID',  # Use appropriate alias
                sessionId=f"feedback-{brandid}-{datetime.utcnow().timestamp()}",
                inputText=json.dumps(agent_input)
            )
            
            # Parse agent response
            result = {}
            for event in response.get('completion', []):
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        result = json.loads(chunk['bytes'].decode('utf-8'))
            
            return result
        else:
            # Fallback: Return basic processing result
            return {
                'feedback_processed': True,
                'feedback_category': 'general',
                'refinement_prompt': f"Process feedback: {feedback_text}",
                'recommended_action': 'regenerate_metadata'
            }
    
    except Exception as e:
        print(f"Error invoking Feedback Processing Agent: {str(e)}")
        return {
            'feedback_processed': False,
            'error': str(e)
        }


def store_feedback_submission(
    brandid: int,
    feedback_type: str,
    feedback_text: str,
    misclassified_combos: list,
    metadata_version: int,
    processing_result: Dict[str, Any]
) -> None:
    """Store feedback submission record in DynamoDB."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        table.put_item(
            Item={
                'pk': f"BRAND#{brandid}",
                'sk': f"FEEDBACK#{timestamp}",
                'brandid': brandid,
                'feedback_type': feedback_type,
                'feedback_text': feedback_text,
                'misclassified_combos': misclassified_combos,
                'metadata_version': metadata_version,
                'processing_result': processing_result,
                'timestamp': timestamp,
                'ttl': int(datetime.utcnow().timestamp()) + (90 * 24 * 60 * 60)  # 90 days
            }
        )
    except Exception as e:
        print(f"Error storing feedback submission: {str(e)}")


def handle_approval(brandid: int, metadata_version: int) -> Dict[str, Any]:
    """Handle metadata approval action."""
    try:
        # Update brand status to approved
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        table.put_item(
            Item={
                'pk': f"BRAND#{brandid}",
                'sk': 'STATUS',
                'brandid': brandid,
                'status': 'approved',
                'metadata_version': metadata_version,
                'approved_at': timestamp,
                'ttl': int(datetime.utcnow().timestamp()) + (365 * 24 * 60 * 60)  # 1 year
            }
        )
        
        return {
            'message': 'Brand metadata approved successfully',
            'brandid': brandid,
            'status': 'approved',
            'metadata_version': metadata_version
        }
    except Exception as e:
        print(f"Error handling approval: {str(e)}")
        return {
            'error': str(e)
        }

