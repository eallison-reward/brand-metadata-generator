"""
Lambda function to escalate brands that exceed iteration limit to management.

This function creates escalation tickets and sends notifications when brands
exceed the maximum iteration limit (10).
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any, List

# Initialize AWS clients
sns_client = boto3.client('sns', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
S3_BUCKET = os.environ.get('S3_BUCKET', 'brand-generator-rwrd-023-eu-west-1')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'brand-metadata-state')
ESCALATION_SNS_TOPIC = os.environ.get('ESCALATION_SNS_TOPIC')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Escalate brands to management review.
    
    Input:
    {
        "brands_rejected": [int],
        "iteration": int,
        "workflow_config": {...},
        "reason": str
    }
    
    Output:
    {
        "status": "success",
        "escalation_ticket": str,
        "notification_sent": bool
    }
    """
    try:
        brands_rejected = event.get('brands_rejected', [])
        iteration = event.get('iteration', 0)
        workflow_config = event.get('workflow_config', {})
        reason = event.get('reason', 'Unknown')
        
        if not brands_rejected:
            return {
                'statusCode': 200,
                'status': 'no_brands_to_escalate',
                'escalation_ticket': None,
                'notification_sent': False
            }
        
        # Create escalation ticket
        escalation_ticket = create_escalation_ticket(
            brands_rejected=brands_rejected,
            iteration=iteration,
            reason=reason
        )
        
        # Store escalation in DynamoDB
        store_escalation(escalation_ticket)
        
        # Send notification
        notification_sent = send_escalation_notification(escalation_ticket)
        
        return {
            'statusCode': 200,
            'status': 'success',
            'escalation_ticket': escalation_ticket['ticket_id'],
            'notification_sent': notification_sent
        }
    
    except Exception as e:
        print(f"Error escalating brands: {str(e)}")
        return {
            'statusCode': 500,
            'status': 'error',
            'error': str(e)
        }


def create_escalation_ticket(
    brands_rejected: List[int],
    iteration: int,
    reason: str
) -> Dict[str, Any]:
    """Create escalation ticket."""
    ticket_id = f"ESC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Get brand details
    brand_details = []
    for brandid in brands_rejected:
        details = get_brand_details(brandid)
        brand_details.append(details)
    
    ticket = {
        'ticket_id': ticket_id,
        'created_at': get_current_timestamp(),
        'status': 'open',
        'priority': 'high',
        'reason': reason,
        'iteration': iteration,
        'brands_count': len(brands_rejected),
        'brands': brand_details,
        'environment': ENVIRONMENT
    }
    
    return ticket


def get_brand_details(brandid: int) -> Dict[str, Any]:
    """Get brand details from S3."""
    try:
        s3_key = f"metadata/brand_{brandid}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        metadata = json.loads(response['Body'].read().decode('utf-8'))
        
        return {
            'brandid': brandid,
            'brandname': metadata.get('brandname', f'Brand {brandid}'),
            'sector': metadata.get('sector', 'Unknown'),
            'confidence_score': metadata.get('metadata', {}).get('confidence_score'),
            'issues': metadata.get('metadata', {}).get('generation_metadata', {}).get('issues_identified', [])
        }
    except Exception as e:
        print(f"Error getting brand details for {brandid}: {str(e)}")
        return {
            'brandid': brandid,
            'brandname': f'Brand {brandid}',
            'sector': 'Unknown'
        }


def store_escalation(ticket: Dict[str, Any]) -> None:
    """Store escalation ticket in DynamoDB."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        table.put_item(
            Item={
                'pk': 'ESCALATION',
                'sk': ticket['ticket_id'],
                **ticket,
                'ttl': int(datetime.utcnow().timestamp()) + (365 * 24 * 60 * 60)  # 1 year
            }
        )
    except Exception as e:
        print(f"Error storing escalation: {str(e)}")


def send_escalation_notification(ticket: Dict[str, Any]) -> bool:
    """Send escalation notification via SNS."""
    try:
        if not ESCALATION_SNS_TOPIC:
            print("No SNS topic configured for escalations")
            return False
        
        message = format_escalation_message(ticket)
        
        sns_client.publish(
            TopicArn=ESCALATION_SNS_TOPIC,
            Subject=f"Brand Metadata Generator Escalation: {ticket['ticket_id']}",
            Message=message
        )
        
        return True
    except Exception as e:
        print(f"Error sending escalation notification: {str(e)}")
        return False


def format_escalation_message(ticket: Dict[str, Any]) -> str:
    """Format escalation message for notification."""
    brands_list = "\n".join([
        f"  - Brand {b['brandid']}: {b['brandname']} ({b['sector']})"
        for b in ticket['brands']
    ])
    
    message = f"""
Brand Metadata Generator Escalation

Ticket ID: {ticket['ticket_id']}
Environment: {ticket['environment']}
Priority: {ticket['priority']}
Created: {ticket['created_at']}

Reason: {ticket['reason']}
Iteration: {ticket['iteration']}

Brands Requiring Management Review ({ticket['brands_count']}):
{brands_list}

Action Required:
These brands have exceeded the maximum iteration limit and require manual review and intervention.

Please review the brands in Quick Suite and provide guidance for resolution.
"""
    
    return message


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"

