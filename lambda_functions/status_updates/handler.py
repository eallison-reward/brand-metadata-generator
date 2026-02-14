"""
Lambda function for real-time status updates for Quick Suite interface.

This function provides current processing status for all brands.
"""

import json
import os
import boto3
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Key, Attr

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
athena_client = boto3.client('athena', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
S3_BUCKET = os.environ.get('S3_BUCKET', 'brand-generator-rwrd-023-eu-west-1')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'brand-metadata-state')
ATHENA_DATABASE = os.environ.get('ATHENA_DATABASE', 'brand_metadata_generator_db')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle status update request from Quick Suite.
    
    Optional query parameters:
    - status_filter: str (e.g., "pending", "in_progress", "awaiting_review", "approved")
    - limit: int (default: 100)
    """
    try:
        # Extract query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        status_filter = query_params.get('status_filter')
        limit = int(query_params.get('limit', 100))
        
        # Get overall status summary
        status_summary = get_status_summary()
        
        # Get brands by status
        brands_by_status = get_brands_by_status(status_filter, limit)
        
        # Get recent activity
        recent_activity = get_recent_activity(limit=20)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status_summary': status_summary,
                'brands': brands_by_status,
                'recent_activity': recent_activity,
                'timestamp': get_current_timestamp()
            })
        }
    
    except Exception as e:
        print(f"Error retrieving status updates: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }


def get_status_summary() -> Dict[str, Any]:
    """Get overall status summary across all brands."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        # Scan for all brand statuses
        response = table.scan(
            FilterExpression=Attr('sk').eq('STATUS')
        )
        
        summary = {
            'total_brands': 0,
            'pending': 0,
            'in_progress': 0,
            'awaiting_review': 0,
            'processing_feedback': 0,
            'approved': 0,
            'failed': 0
        }
        
        for item in response.get('Items', []):
            status = item.get('status', 'pending')
            summary['total_brands'] += 1
            
            if status in summary:
                summary[status] += 1
            else:
                summary['pending'] += 1
        
        return summary
    
    except Exception as e:
        print(f"Error getting status summary: {str(e)}")
        return {
            'total_brands': 0,
            'pending': 0,
            'in_progress': 0,
            'awaiting_review': 0,
            'processing_feedback': 0,
            'approved': 0,
            'failed': 0
        }


def get_brands_by_status(status_filter: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get brands filtered by status."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        # Build filter expression
        if status_filter:
            filter_expression = Attr('sk').eq('STATUS') & Attr('status').eq(status_filter)
        else:
            filter_expression = Attr('sk').eq('STATUS')
        
        # Scan for brands
        response = table.scan(
            FilterExpression=filter_expression,
            Limit=limit
        )
        
        brands = []
        for item in response.get('Items', []):
            brandid = item.get('brandid')
            
            # Get brand details from S3
            brand_details = get_brand_details(brandid)
            
            brands.append({
                'brandid': brandid,
                'brandname': brand_details.get('brandname', f'Brand {brandid}'),
                'sector': brand_details.get('sector', 'Unknown'),
                'status': item.get('status', 'pending'),
                'metadata_version': item.get('metadata_version', 1),
                'confidence_score': brand_details.get('confidence_score'),
                'last_updated': item.get('timestamp'),
                'requires_review': brand_details.get('requires_review', False)
            })
        
        # Sort by last_updated descending
        brands.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
        
        return brands
    
    except Exception as e:
        print(f"Error getting brands by status: {str(e)}")
        return []


def get_brand_details(brandid: int) -> Dict[str, Any]:
    """Get brand details from S3 metadata."""
    try:
        s3_key = f"metadata/brand_{brandid}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        metadata = json.loads(response['Body'].read().decode('utf-8'))
        
        return {
            'brandname': metadata.get('brandname', f'Brand {brandid}'),
            'sector': metadata.get('sector', 'Unknown'),
            'confidence_score': metadata.get('metadata', {}).get('confidence_score'),
            'requires_review': metadata.get('metadata', {}).get('generation_metadata', {}).get('requires_review', False)
        }
    
    except s3_client.exceptions.NoSuchKey:
        return {
            'brandname': f'Brand {brandid}',
            'sector': 'Unknown',
            'confidence_score': None,
            'requires_review': False
        }
    except Exception as e:
        print(f"Error getting brand details for {brandid}: {str(e)}")
        return {
            'brandname': f'Brand {brandid}',
            'sector': 'Unknown',
            'confidence_score': None,
            'requires_review': False
        }


def get_recent_activity(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent activity across all brands."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        # Scan for recent feedback submissions
        response = table.scan(
            FilterExpression=Attr('sk').begins_with('FEEDBACK#'),
            Limit=limit
        )
        
        activities = []
        for item in response.get('Items', []):
            activities.append({
                'brandid': item.get('brandid'),
                'activity_type': 'feedback_submitted',
                'feedback_type': item.get('feedback_type'),
                'timestamp': item.get('timestamp'),
                'metadata_version': item.get('metadata_version')
            })
        
        # Sort by timestamp descending
        activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return activities[:limit]
    
    except Exception as e:
        print(f"Error getting recent activity: {str(e)}")
        return []


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

